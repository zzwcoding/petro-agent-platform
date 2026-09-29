"""infra.eventbus —— 领域事件总线接缝（98 §4 adapter 行；ADR-0003 裁决 11）。

合同真源（只读引用，不复制正文）：
- specs/api/98-模块划分与分层.md §4 `infra.eventbus` 行：领域事件发布/订阅；
  实现选型＝Redis Streams 当通道＋`infra_outbox` 表兜底（批准事务副作用
  ③④⑤经 outbox 保投递，25 领域事件语义不变）；§8 领域事件一览（25 名——
  本票只立总线缝，不实现任何具体事件的发布方/订阅方）。
- specs/api/99-数据库与连接层设计.md §6-4：`infra_outbox` 为 infra 技术表
  （不归 14 模块域），表结构随接线批落册——册上未落结构，本票按标准 outbox
  模式落（见 OutboxRow docstring），结构登记于 tickets/phase0/README.md P0-08。

本票范围（tickets/phase0/README.md P0-08 预留件）：
- `EventBus` 协议 + `InMemoryEventBus`（测试底座：发布-订阅 + 订阅异常隔离
  ——单订阅者异常记日志不外抛，不中断其余订阅者；可靠性语义归 outbox 承载）；
- `RedisStreamEventBus` 骨架：构造不连网，首用探活——Redis 未起显式抛
  `EventBusConfigError`（配置错误），**不静默降级内存实现**（防「以为发了
  其实没发」）；Stream 接线（XADD/消费组/缓冲 MAXLEN）属后续接线批。
- `infra_outbox` 表 + `OutboxStore`（同事务登记/待投递扫描/投递回执）。

边界：B3（DB 只经 infra.db）、B14（时间只经 infra.clock）、B16（infra 不
import domains/api）、B1（本模块不 import fastapi/starlette）。
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast
from uuid import uuid4

from redis.asyncio import Redis
from sqlalchemy import BigInteger, Index, Integer, String, Table, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infra.clock import now
from app.infra.db import Base, ConnectionManager

LOGGER = logging.getLogger("infra.eventbus")

# ---- 事件本体（98 §8 事件名为 name 的合法值域——本票不收编校验，接线批挂） ----


@dataclass(frozen=True)
class DomainEvent:
    """领域事件（信封最小形）：名＋载荷＋发生时刻＋聚合标识。

    载荷形状归各事件合同（98 §8 语义列/合同锚），总线不解释、不收编。
    """

    event_id: str
    name: str
    payload: Mapping[str, Any]
    occurred_at: datetime
    aggregate: str | None = None  # "<聚合类型>:<聚合id>"（如 kb_report:rpt-1）


def make_event(
    name: str, payload: Mapping[str, Any], *, aggregate: str | None = None
) -> DomainEvent:
    """事件工厂：盖 infra.clock 时戳（B14）＋生成机器 event_id；载荷防御性拷贝。"""
    return DomainEvent(
        event_id=uuid4().hex,
        name=name,
        payload=dict(payload),
        occurred_at=now(),
        aggregate=aggregate,
    )


# 订阅处理器：同步或异步（返回 awaitable 即被 await）；异常一律被隔离（见下）。
EventHandler = Callable[[DomainEvent], Any]
# 订阅回执：退订 thunk（幂等，重复调用无害）。
Subscription = Callable[[], None]


class EventBus(Protocol):
    """领域事件发布/订阅缝（98 §4 eventbus 行——换实现不动调用方）。"""

    async def publish(self, event: DomainEvent) -> None:
        """向该事件名的全部订阅者派发（异常隔离语义见各实现）。"""
        ...

    async def subscribe(self, event_name: str, handler: EventHandler) -> Subscription:
        """登记订阅者，返回退订 thunk。"""
        ...


class InMemoryEventBus:
    """进程内发布-订阅（测试底座；P0-08 验收线＝本实现发布-订阅测试过）。

    派发语义：按订阅登记序逐个调用；**订阅异常隔离**——单订阅者异常记日志
    （infra.eventbus），不中断其余订阅者、不向发布方抛出。跨进程/跨事务的
    可靠投递不归内存实现承载（走 outbox——ADR-0003 裁决 11）；多进程部署
    亦不可用本实现（进程边界即失效）。

    `published` 观测窗仅供测试断言与调试（无界列表，勿在生产常驻使用）。
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._published: list[DomainEvent] = []

    async def subscribe(self, event_name: str, handler: EventHandler) -> Subscription:
        handlers = self._handlers.setdefault(event_name, [])
        handlers.append(handler)

        def unsubscribe() -> None:
            try:
                handlers.remove(handler)
            except ValueError:
                pass  # 幂等：已退订再退订无害

        return unsubscribe

    async def publish(self, event: DomainEvent) -> None:
        self._published.append(event)
        # tuple() 快照：派发中途退订/新订不影响本轮（派发序＝登记序）。
        for handler in tuple(self._handlers.get(event.name, ())):
            try:
                result = handler(event)
                if result is not None:
                    await result
            except Exception:
                LOGGER.exception(
                    "eventbus 订阅者处理异常（已隔离，不中断其余订阅者）: "
                    "event=%s event_id=%s",
                    event.name,
                    event.event_id,
                )

    @property
    def published(self) -> tuple[DomainEvent, ...]:
        """观测窗：本总线已发布的事件序（测试断言用）。"""
        return tuple(self._published)


# ---- Redis Streams 通道（骨架——缝后接线批补全） ----


class EventBusConfigError(RuntimeError):
    """事件总线配置/依赖错误（Redis 未起、URL 缺失）——显式报错，禁静默降级。"""


def _default_client_factory(url: str) -> Redis:
    return Redis.from_url(url)


class RedisStreamEventBus:
    """Redis Streams 通道骨架（ADR-0003 裁决 11 的实现选型；本票只立缝）。

    - 构造**不连网**（lazy）：首次 publish/subscribe 经 client_factory 建连
      并 ping 探活——探活失败抛 `EventBusConfigError`（显式配置错误，不静默
      降级 InMemoryEventBus：测试底座与生产通道必须显式二选一）。
    - client_factory 是测试缝：单测注入假客户端，测试不依赖活 Redis。
    - Stream 接线（XADD/消费组/事件缓冲 MAXLEN≈200 帧——00 §6.2）属后续
      接线批：探活通过即抛 NotImplementedError，不提供半实现。
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        *,
        client_factory: Callable[[str], Redis] | None = None,
    ) -> None:
        self._url = url
        self._client_factory: Callable[[str], Redis] = (
            client_factory or _default_client_factory
        )
        self._client: Redis | None = None

    async def _ensure_client(self) -> Redis:
        try:
            if self._client is None:
                self._client = self._client_factory(self._url)
            await self._client.ping()
        except Exception as exc:
            raise EventBusConfigError(
                f"eventbus 的 Redis 未就绪（{self._url}）：{exc}——"
                "显式配置错误，不静默降级；先 docker compose up -d redis，"
                "或显式改用 InMemoryEventBus（仅限测试/单进程演示）"
            ) from exc
        return self._client

    async def publish(self, event: DomainEvent) -> None:
        await self._ensure_client()
        raise NotImplementedError(
            "Redis Streams 通道接线（XADD/消费组）属后续接线批（ADR-0003 裁决 11）"
            "——本票只立缝与探活"
        )

    async def subscribe(self, event_name: str, handler: EventHandler) -> Subscription:
        await self._ensure_client()
        raise NotImplementedError(
            "Redis Streams 消费组接线属后续接线批（ADR-0003 裁决 11）——本票只立缝与探活"
        )


# ---- infra_outbox（事务性 outbox 表——99 §6-4 infra 技术表） ----


class OutboxRow(Base):
    """infra_outbox —— 事务性 outbox（发布方模块写、中继投递；99 §6-4）。

    99 册未落结构（「表结构随接线批落本册」）——本票按标准 outbox 模式落，
    逐列登记于 tickets/phase0/README.md P0-08 差异清单：
      id bigserial（注册序＝投递序）· aggregate（<聚合类型>:<聚合id>）·
      event_type（98 §8 事件名）· payload jsonb · occurred_at（infra.clock
      东八区 naive，B14）· published_at nullable（NULL=待投递，中继回执回写）
      ＋ 基线列 created_at/updated_at（P0-04 审计表惯例）
      ＋ idx (published_at, id)（待投递扫描序——pending 按 id 升序补发）。
    """

    __tablename__ = "infra_outbox"
    __table_args__ = (Index("ix_infra_outbox_pending", "published_at", "id"),)

    # bigserial（PG/金仓）；sqlite 单测底座回落 Integer（rowid 别名才自增）。
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer(), "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    aggregate: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=now, nullable=False)


class OutboxStore:
    """outbox 仓储：同事务登记 / 待投递扫描 / 投递回执。

    「同事务」语义（批准事务副作用③④⑤保投递的物理落点）：发布方在自己
    的事务会话里 `add_in(session, row)`——outbox 行与聚合变更同 commit，
    防「库写了、事件没写」；总线 publish 与 outbox 登记的编排属接线批。
    """

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    @staticmethod
    def row_for(event: DomainEvent) -> OutboxRow:
        """事件 → outbox 行（aggregate 缺省落事件名——保持列非空约束简单）。"""
        return OutboxRow(
            aggregate=event.aggregate or event.name,
            event_type=event.name,
            payload=dict(event.payload),
            occurred_at=event.occurred_at,
        )

    async def add_in(self, session: AsyncSession, row: OutboxRow) -> OutboxRow:
        """在调用方事务会话内登记（同 commit/同回滚——保投递的正确用法）。"""
        session.add(row)
        await session.flush()
        return row

    async def add(self, row: OutboxRow) -> OutboxRow:
        """独立轻会话登记（非事务耦合场景；事务场景一律走 add_in）。"""
        async with self._db.session() as session:
            session.add(row)
            await session.flush()
        return row

    async def pending(self, *, limit: int = 100) -> list[OutboxRow]:
        """待投递行（published_at IS NULL），按 id 升序＝发生序（中继消费序）。"""
        async with self._db.readonly() as session:
            rows = (
                (
                    await session.execute(
                        select(OutboxRow)
                        .where(OutboxRow.published_at.is_(None))
                        .order_by(OutboxRow.id.asc())
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        return list(rows)

    async def mark_published(self, row_id: int, *, at: datetime | None = None) -> bool:
        """投递回执：回写 published_at（幂等——已回执行返回 False 不重复盖写）。"""
        stamped = at or now()
        async with self._db.session() as session:
            row = await session.get(OutboxRow, row_id)
            if row is None or row.published_at is not None:
                return False
            row.published_at = stamped
            row.updated_at = stamped
            await session.flush()
            return True


async def ensure_outbox_table(engine: AsyncEngine) -> None:
    """建表函数（幂等 checkfirst，P0-04 惯例）——与 Alembic 并行存活，
    切换迁移属各域/接线批票（P0-08 票面：本票不切换）。"""
    table = cast(Table, OutboxRow.__table__)  # __table__ 静态型宽于 DDL 面（同 gateway store）
    async with engine.begin() as conn:
        await conn.run_sync(table.create, checkfirst=True)
