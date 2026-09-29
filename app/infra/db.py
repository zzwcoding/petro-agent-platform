"""infra.db —— Petro-Agent 统一数据表连接层（全平台唯一 DB 出口）。

定位与边界（specs/api/99-数据库与连接层设计.md §4.1/§4.2；specs/api/98 §4/§6）：
- B3：任何模块禁止绕过本模块直连数据库驱动（psycopg/金仓驱动只在此 import）。
- B16：本模块禁止 import app.domains / app.api（依赖单向向下）。
- 双库：开发 PostgreSQL / 生产金仓（金仓 ≈ PostgreSQL 方言，00 §11）——
  驱动差异收敛在 DRIVER_REGISTRY 一处；金仓驱动落位批只改注册表。
- 角色路由：primary（平台主库）/ replica（只读副本，预留，回落 primary）/
  midplatform（中台源 8 表只读——映射卡取行与质检扫描，强制只读）。
- 审计分工：本层只做慢查询与 SQL 计时钩子（工程观测）；业务审计四元组
  一律经 security.audit 与各聚合内嵌留痕（B12/R10），本层不写业务表。
- 测试替身：消费方只依赖 ConnectionManager 与 Repository 基类；
  单测以 FakeConnectionManager（内存库/假会话）注入构造函数。

ORM 声明：SQLAlchemy 2.0 定型（ADR-0003 裁决 3）——Mapped[]/select()/
begin_nested() 2.0 风格编写；接缝仍在 ConnectionManager（引擎/会话工厂，
供测试替身与部署配置注入）；领域层不得出现本模块之外的任何驱动符号。

与 99 §4.2 雏形的差异（现实约束，语义不改动——差异登记见
tickets/phase0/README.md P0-03）：
- **异步化**：雏形为同步 create_engine/Session；本仓依赖定型
  sqlalchemy[asyncio]+asyncpg（ADR-0003 裁决 3「异步面与生态」理由），
  落 create_async_engine/AsyncSession/async_sessionmaker——三个公开面
  session()/transaction()/readonly()、嵌套 SAVEPOINT、只读双保险、
  慢查询钩子、行级注入点、健康检查的语义逐条保持。
- **驱动注册表**：postgresql → postgresql+asyncpg（雏形写 psycopg；
  仅注册表键值改动，结构不动）。
- **只读兜底按方言门控**：DB 级第二保险＝只读会话工厂的方言连接特性
  postgresql_readonly（每事务 BEGIN READ ONLY，PG/金仓近似方言生效；
  SQLite 单测底座无此特性则忽略，靠意图级 flush 守卫恒挂兜住）。
  注意：曾试过「连接级 SET default_transaction_read_only」方案，集成
  实测两宗罪——①asyncpg 方言每事务显式 BEGIN READ WRITE 会覆盖 GUC，
  单靠它拦不住 Core 直写；②该裸 SET 与 postgresql_readonly 特性并存时
  反而把后者弄失效（probe 实证，2026-09-29）——故 GUC 方案整体退役。
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import URL, Select, event, func, select, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.types import Text, TypeDecorator

LOGGER = logging.getLogger("infra.db")

DatabaseRole = Literal["primary", "replica", "midplatform"]

# 双驱动适配 seam：金仓驱动名在驱动落位批补齐（占位不改结构）。
# 金仓兼容模式在 initdb 期一次性固化（00 §11）；方言近似验证是实施批义务。
DRIVER_REGISTRY: dict[str, str] = {
    # 差异注：99 雏形为 postgresql+psycopg；本仓依赖定型 asyncpg（异步）。
    "postgresql": "postgresql+asyncpg",
    # placeholder —— 金仓 KingbaseES ≈ PostgreSQL 方言（00 §11）；
    # 官方驱动落位批只改本注册表（结构不动）。
    "kingbase": "kingbase+kb",
    # 单测底座（99 §4.1 测试替身策略的内存/文件库落点）——非生产角色驱动。
    "sqlite": "sqlite+aiosqlite",
}

# 支持连接级只读兜底语句（SET default_transaction_read_only）的方言——
# SQLite（单测底座）不认识该语句，跳过装配；意图级守卫（readonly()）恒挂。
_READONLY_CAPABLE_DRIVERS = frozenset({"postgresql", "kingbase"})


@dataclass(frozen=True)
class DatabaseSpec:
    """单个数据库角色的连接规格（config/database.yaml 装载，infra.config 供给）。"""

    name: str
    role: DatabaseRole
    driver: str                    # DRIVER_REGISTRY 的 key
    host: str
    port: int
    database: str
    user: str
    password: str                  # 部署配置注入；SM4 字段级加密见 EncryptedField
    pool_size: int = 10
    max_overflow: int = 5
    pool_recycle_seconds: int = 1800
    slow_query_ms: int = 800       # 慢查询阈值（工程日志，非业务审计）
    readonly: bool = False         # midplatform/replica 恒 True

    def url(self) -> URL:
        prefix = DRIVER_REGISTRY.get(self.driver)
        if prefix is None:
            raise ValueError(f"未登记的数据库驱动: {self.driver!r}")
        # URL.create 负责账号/密码特殊字符转义——禁止手工拼 URL 字符串。
        # 空字段归一为 None：SQLite 单测底座（无账号/host）URL 不被空串污染。
        return URL.create(
            drivername=prefix,
            username=self.user or None,
            password=self.password or None,
            host=self.host or None,
            port=self.port or None,
            database=self.database or None,
        )


class EncryptedField(TypeDecorator[str]):
    """SM4 字段加密列类型（seam）。

    真实加解密由 infra.crypto 注入（构造参数传 encrypt/decrypt 回调），
    本类不 import 国密实现——D3「密文存储在服务端」；字段清单真源落
    security.security_crypto_field。零依赖缺省实现仅用于类型占位。
    """

    impl = Text
    cache_ok = True

    def __init__(
        self,
        encrypt: Callable[[str], str] = lambda s: s,
        decrypt: Callable[[str], str] = lambda s: s,
    ) -> None:
        super().__init__()
        self._encrypt = encrypt
        self._decrypt = decrypt

    def process_bind_param(self, value: str | None, _dialect: Any) -> str | None:
        return None if value is None else self._encrypt(value)

    def process_result_value(self, value: str | None, _dialect: Any) -> str | None:
        return None if value is None else self._decrypt(value)


@dataclass
class Page[T]:
    """分页信封——R3：total＝筛选后、counts 由调用方按全局计数另行装配。"""

    items: list[T]
    total: int
    page: int
    page_size: int


class ReadOnlyViolation(RuntimeError):
    """只读角色上发生写意图（flush/execute 非查询）时抛出。"""


class ConnectionManager:
    """连接池与会话/事务的唯一出口（每数据库角色一个异步引擎）。

    用法（领域仓储内；异步版——await 语义）：
        async with db.session() as session:            # 自动提交/回滚的轻会话
            ...
        async with db.transaction() as session:        # 显式事务；支持嵌套 SAVEPOINT
            async with db.transaction(session) as sp:  # 内层＝SAVEPOINT
                ...
        async with db.readonly() as session:           # replica/midplatform 只读
            ...
    """

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._engines: dict[DatabaseRole, AsyncEngine] = {}
        self._sessions: dict[DatabaseRole, async_sessionmaker[AsyncSession]] = {}
        self._readonly_sessions: dict[DatabaseRole, async_sessionmaker[AsyncSession]] = {}
        self._specs: dict[DatabaseRole, DatabaseSpec] = {}
        for spec in specs:
            engine = create_async_engine(
                spec.url(),
                pool_size=spec.pool_size,
                max_overflow=spec.max_overflow,
                pool_recycle=spec.pool_recycle_seconds,
                pool_pre_ping=True,
            )
            # SQLAlchemy 2.1：异步事件未实现，同步监听挂 sync_engine
            # （引擎级事件在 greenlet 语境下对异步执行同样生效）。
            self._attach_observers(engine.sync_engine, spec)
            self._attach_readonly_enforcement(engine.sync_engine, spec)
            self._engines[spec.role] = engine
            self._sessions[spec.role] = async_sessionmaker(
                bind=engine, expire_on_commit=False
            )
            # 只读会话工厂：方言连接特性 postgresql_readonly（每次 BEGIN READ ONLY）。
            # 连接级 GUC（_attach_readonly_enforcement）会被 asyncpg 方言的显式
            # BEGIN READ WRITE 覆盖——事务只读必须走这条（见 readonly() 注）。
            self._readonly_sessions[spec.role] = async_sessionmaker(
                bind=engine,
                expire_on_commit=False,
                execution_options={"postgresql_readonly": True},
            )
            self._specs[spec.role] = spec

    # ---------- 观测钩子（慢查询/计时；不写业务审计表） ----------

    def _attach_observers(self, engine: Engine, spec: DatabaseSpec) -> None:
        state: dict[Connection, float] = {}

        def before(conn: Connection, _cursor: Any, _stmt: Any, *_a: Any) -> None:
            state[conn] = time.monotonic()

        def after(conn: Connection, _cursor: Any, statement: Any, *_a: Any) -> None:
            started = state.pop(conn, None)
            if started is None:
                return
            elapsed_ms = (time.monotonic() - started) * 1000
            if elapsed_ms >= spec.slow_query_ms:
                LOGGER.warning(
                    "slow query on %s (%.0f ms): %s",
                    spec.role,
                    elapsed_ms,
                    str(statement)[:300],
                )

        def on_error(context: Any) -> None:
            # 失败语句不触发 after_cursor_execute——计时状态在此回收（防泄漏）。
            conn = getattr(context, "sqlalchemy_connection", None)
            if conn is not None:
                state.pop(conn, None)

        event.listen(engine, "before_cursor_execute", before)
        event.listen(engine, "after_cursor_execute", after)
        event.listen(engine, "handle_error", on_error)

    def _attach_readonly_enforcement(self, engine: Engine, spec: DatabaseSpec) -> None:
        """DB 级只读兜底装配（readonly 角色）——已收编进只读会话工厂。

        真正的 DB 级第二保险＝readonly() 用 `self._readonly_sessions[target]`
        （execution_options: postgresql_readonly=True，每事务 BEGIN READ ONLY，
        拦绕过 ORM 的 Core 直写）。本方法保留方法名作装配位：曾在 connect
        事件挂 `SET default_transaction_read_only`，集成实测与该特性相克
        （见模块 docstring 差异注），GUC 方案退役——留注释防回归。
        方言门控语义不变：非 PG 系方言靠意图级 flush 守卫（readonly() 恒挂）。
        """
        if not spec.readonly or spec.driver not in _READONLY_CAPABLE_DRIVERS:
            return
        # （有意留空——GUC 方案退役，见 docstring；勿在此重挂连接级 SET。）

    # ---------- 会话与事务 ----------

    def _assert_writable(self, role: DatabaseRole) -> None:
        if self._specs[role].readonly:
            raise ReadOnlyViolation(f"数据库角色 {role!r} 为只读，禁止写会话")

    @asynccontextmanager
    async def session(self, role: DatabaseRole = "primary") -> AsyncIterator[AsyncSession]:
        """轻会话：块结束即 commit（异常回滚）。写角色前置只读校验。"""
        self._assert_writable(role)
        session = self._sessions[role]()
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def transaction(
        self, role_or_session: DatabaseRole | AsyncSession = "primary"
    ) -> AsyncIterator[AsyncSession]:
        """显式事务；传入已开启 Session 时降级为 SAVEPOINT（嵌套支持）。

        governance 批准事务（C2 端点 7：状态/版本/汇入/留痕/审计同事务、
        生效后副作用补偿）即以外层 transaction + 内层 SAVEPOINT 表达。
        """
        if isinstance(role_or_session, AsyncSession):
            outer = role_or_session
            nested = await outer.begin_nested()  # SAVEPOINT
            try:
                yield outer
                await nested.commit()
            except BaseException:
                await nested.rollback()
                raise
            return
        role = role_or_session
        self._assert_writable(role)
        session = self._sessions[role]()
        try:
            async with session.begin():
                yield session
        finally:
            await session.close()

    @asynccontextmanager
    async def readonly(self, role: DatabaseRole = "primary") -> AsyncIterator[AsyncSession]:
        """只读会话：路由到 replica（未配置回落 primary），恒挂只读守卫。

        守卫按**意图**挂（进入 readonly() 语境即拦 flush）——不按目标角色
        spec.readonly 判（primary 未配 replica 的回落情形同样要拦）。

        双保险的 DB 级兜底＝只读会话工厂的方言连接特性 `postgresql_readonly`
        （每个事务 BEGIN READ ONLY，拦绕过 ORM 的 Core 直写）——连接级
        `SET default_transaction_read_only` 方案已退役（与该特性相克且被
        方言 BEGIN 覆盖，见模块 docstring 差异注与 _attach_readonly_enforcement）。
        """
        target = self.resolve_read_role(role)
        session = self._readonly_sessions[target]()
        spec = self._specs[target]

        def guard(_session: Any, flush_context: Any, _instances: Any) -> None:
            raise ReadOnlyViolation(f"只读会话（{spec.role}）禁止 flush")

        # SQLAlchemy 2.1：Session 事件挂 sync_session（异步事件未实现）。
        event.listen(session.sync_session, "before_flush", guard)
        try:
            yield session
        finally:
            await session.close()

    def resolve_read_role(self, role: DatabaseRole = "primary") -> DatabaseRole:
        """读路由解析：primary 有 replica 配置时读走 replica（预留 seam）。"""
        if role == "primary" and "replica" in self._engines:
            return "replica"
        return role

    # ---------- 行级权限注入点（与 D3 row_filter 衔接） ----------

    @staticmethod
    def with_row_filter(stmt: Select[Any], predicates: Sequence[Any]) -> Select[Any]:
        """把 mandatory filter 谓词 AND 进查询装配（原样语句不可达执行器）。

        谓词由 security.row_filter() 产出、调用方注入——本层不 import
        security（B16），只提供装配执行点；「无权的数据查不出来，不是
        打码」的物理落点（00 §9.3）。
        """
        for predicate in predicates:
            stmt = stmt.where(predicate)
        return stmt

    # ---------- 健康检查（D5 四灯之库灯——本进程配置的引擎） ----------

    async def check_health(self) -> dict[str, str]:
        lights: dict[str, str] = {}
        for role, engine in self._engines.items():
            try:
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                lights[role] = "up"
            except Exception:
                LOGGER.exception("health check failed: %s", role)
                lights[role] = "down"
        return lights

    async def dispose(self) -> None:
        for engine in self._engines.values():
            await engine.dispose()


class Repository[ModelT]:
    """领域仓储基类：读写通用（会话经 ConnectionManager 取得）。

    归属裁决（B16 优先于经典依赖倒置）：仓储接口与实现都放各模块包内
    （app/domains/<m>/store.py），仅依赖本基类与 ConnectionManager——
    infra 不反向 import 领域 Protocol（出入登记见 99 册 §5 出入 12）。
    """

    model: type[ModelT]

    def __init__(self, db: ConnectionManager, role: DatabaseRole = "primary") -> None:
        self._db = db
        self._role = role

    async def get(self, session: AsyncSession, id_: str) -> ModelT | None:
        return await session.get(self.model, id_)

    def add(self, session: AsyncSession, entity: ModelT) -> ModelT:
        session.add(entity)
        return entity

    async def delete(self, session: AsyncSession, entity: ModelT) -> None:
        await session.delete(entity)


class ReadOnlyRepository[ModelT](Repository[ModelT]):
    """只读仓储基类：读路由解析（replica 预留）+ 分页助手（R3 信封语义）。

    会话由查询方法经 db.readonly(self._read_role) 按需开启——只读守卫
    在该会话上生效；写意图在本基类无出口（不暴露 add/delete 的会话编排）。
    """

    def __init__(self, db: ConnectionManager, role: DatabaseRole = "primary") -> None:
        super().__init__(db, role)
        self._read_role: DatabaseRole = db.resolve_read_role(role)

    async def paginate(
        self,
        session: AsyncSession,
        stmt: Select[Any],
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[ModelT]:
        """分页查询助手：total＝当前筛选条件下总数（R3 裁决值）。

        counts（全局计数）由调用方对同表另行 count 装配——信封形状
        归接口层公共件（98 §7.2 R3 接线责任落点）。
        """
        page = max(page, 1)
        page_size = max(page_size, 1)
        total = await session.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        result = await session.execute(
            stmt.offset((page - 1) * page_size).limit(page_size)
        )
        rows = result.scalars().all()
        return Page(
            items=list(rows), total=int(total or 0), page=page, page_size=page_size
        )
