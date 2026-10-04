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
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import Text, TypeDecorator

LOGGER = logging.getLogger("infra.db")


class Base(DeclarativeBase):
    """全平台 ORM 声明基座（P0-04 起）：各域模型共用一个 MetaData。

    放 infra 的理由：B3「全平台唯一 DB 出口」的自然延伸——metadata 归一后
    P0-08 Alembic 迁移分组才有单一 autogenerate 源，跨域外键共一张关系图。
    模型文件仍归各域包（app/domains/<m>/store.py，99 §4.3 归属裁决），
    本基座不反向 import 任何域（B16 不变）。
    """

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


class MidplatformRouteError(RuntimeError):
    """midplatform 只读路由启动校验不过（缺配置/规格未只读/写探针未被拒）时抛出。

    M-01：对齐 Owner 方针「生产缺依赖拒绝启动」，反数据面静默降级病灶——
    缺依赖宁可拒启动，不做静默回落。
    """


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
            self._engines[spec.role] = engine
            self._sessions[spec.role] = async_sessionmaker(
                bind=engine, expire_on_commit=False
            )
            # 只读会话工厂：方言连接特性 postgresql_readonly（每次 BEGIN READ ONLY）。
            # 连接级 GUC（SET default_transaction_read_only）会被 asyncpg 方言的
            # 显式 BEGIN READ WRITE 覆盖——事务只读必须走这条（见 readonly() 注；
            # 曾试连接级方案，集成实测与该特性相克，GUC 方案整体退役勿重挂）。
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
        （每个事务 BEGIN READ ONLY，拦绕过 ORM 的 Core 直写）——曾试在 connect
        事件挂连接级 `SET default_transaction_read_only`，集成实测与该特性相克
        且被方言 BEGIN 覆盖（见模块 docstring 差异注），GUC 方案整体退役，
        勿重挂连接级 SET。方言门控：非 PG 系方言（SQLite 单测底座等）由
        SQLAlchemy 忽略该连接特性，只读靠上面的意图级 flush 守卫恒挂兜住。
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

    def engine(self, role: DatabaseRole = "primary") -> AsyncEngine:
        """引擎定位（DDL 运维口：P0-08 前建表函数经此拿 primary 引擎，幂等 checkfirst）。"""
        return self._engines[role]

    # ---------- 行级权限注入点（与 D3 row_filter 衔接） ----------

    @staticmethod
    def with_row_filter(stmt: Select[Any], predicates: Sequence[Any]) -> Select[Any]:
        """把 mandatory filter 谓词 AND 进查询装配（原样语句不可达执行器）。

        谓词由 security.row_filter() 产出、调用方注入——本层不 import
        security（B16），只提供装配执行点；「无权的数据查不出来，不是
        打码」的物理落点（00 §9.3）。

        M-01 起谓词生产侧的预埋缝＝模块级 with_row_filter(actor, table)
        （RowDomainScope 装配物）——消费方两步照 99 §4.2 流程组合，本冻结
        形状不改。
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

    # ---------- midplatform 只读路由启动校验（M-01——缺依赖拒绝启动） ----------

    async def verify_midplatform_route(self) -> None:
        """midplatform 只读路由启动期校验（M-01）——任一步不过即抛 MidplatformRouteError。

        对齐 Owner 方针「生产缺依赖拒绝启动」、反数据面静默降级病灶：
        ①缺 midplatform 配置→显式报错（不静默回落 primary、不留哑连接）；
        ②规格未声明 readonly→报错（99 §4.1 强制只读不靠自觉）；③连接可达性
        ＋只读验证——写探针（CREATE TEMP TABLE）必须被拒才放行：探针触 DP-03
        账号级 default_transaction_read_only=on 兜底（data-plane 仓
        migrations/midplatform_readonly.sql）；探针意外成功＝账号未证实只读，
        拒绝启动。接线约定：组合根（lifespan）装配 ConnectionManager 后调用
        本方法——main.py 接线随消费票（M-02）带上，本票只交校验语义与测试。
        """
        spec = self._specs.get("midplatform")
        if spec is None:
            raise MidplatformRouteError(
                "midplatform 只读路由未配置（config/database.yaml 缺 midplatform 段）"
                "——拒绝启动（生产缺依赖拒绝启动，禁静默降级）"
            )
        if not spec.readonly:
            raise MidplatformRouteError(
                "midplatform 规格未声明 readonly=true——拒绝启动（99 §4.1 强制只读）"
            )
        engine = self._engines["midplatform"]
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))  # 可达性探活
                try:
                    await conn.execute(
                        text("CREATE TEMP TABLE _midplatform_write_probe (id integer)")
                    )
                except Exception:
                    LOGGER.info("midplatform 只读验证通过：写探针被拒（%s）", spec.name)
                    return
                raise MidplatformRouteError(
                    "midplatform 写探针未被拒——账号未证实只读"
                    "（核对 DP-03 data-plane/migrations/midplatform_readonly.sql："
                    "SELECT-only 授权＋default_transaction_read_only=on）——拒绝启动"
                )
        except MidplatformRouteError:
            raise
        except Exception as exc:
            raise MidplatformRouteError(f"midplatform 连接不可达：{exc}") from exc

    async def dispose(self) -> None:
        for engine in self._engines.values():
            await engine.dispose()


# ---------- 行级权限预埋装配器（M-01——99 §2.0②/§4.2 消费缝，形状冻结） ----------


@dataclass(frozen=True)
class RowDomainScope:
    """with_row_filter(actor, table) 的返回装配物（形状冻结——真分权只换实现不换签名）。

    predicates＝AND 进查询的 mandatory filter 谓词（00 §9.3「WHERE 由权限层
    拼接，不靠模型自觉」）；元组形状不假设谓词落于本表列——join 感知（问数链
    fct_daily_metering 挂 dim_well 侧谓词，DP-04 审查输入）由谓词自带 join/
    子查询表达。预埋期恒空元组（＝WHERE 恒真/不加）。
    """

    actor: str
    table: str
    predicates: tuple[Any, ...] = ()


def with_row_filter(actor: str, table: str) -> RowDomainScope:
    """行级权限预埋装配器（M-01）——「无权的数据查不出来，不是打码」的谓词生产缝。

    形状冻结（docstring 引 99 §4.2）：本函数＝行级注入点的谓词生产侧预埋，
    物理装配执行点仍是 ConnectionManager.with_row_filter(stmt, predicates)
    ——99 §4.2 冻结形状原样不改。预埋期语义：全员管理员→数据域＝全量，
    谓词恒空（WHERE 恒真/不加）；真分权批只换本函数实现（判值源
    security_row_domain_grant——谓词产出归 security 域，B16 禁本层 import），
    本签名与 RowDomainScope 形状不动。A2 井档案/问数链在此缝消费：

        scope = with_row_filter(actor, "raw.well_info")
        stmt = ConnectionManager.with_row_filter(stmt, scope.predicates)
    """
    return RowDomainScope(actor=actor, table=table, predicates=())


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

    @staticmethod
    async def paginate[RowT](
        session: AsyncSession,
        stmt: Select[Any],
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[RowT]:
        """分页查询助手（R3 信封）：total＝当前筛选条件下总数。

        staticmethod——不绑定实例：不继承本基类的仓储（如 B12 append-only
        的 audit_log 仓储）同样复用本实现，count 子查询＋offset/limit 全仓
        单源。counts（全局计数）由调用方对同表另行 count 装配——信封形状
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
