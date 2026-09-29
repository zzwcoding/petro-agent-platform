"""infra.eventbus 单元测试——发布-订阅（内存）/订阅异常隔离/Redis 缝探活/outbox 仓储。

P0-08 验收线（tickets/phase0/README.md）：事件发布-订阅**内存实现**测试过。
Redis 通道测试不依赖活 Redis（本机未拉起——compose redis 服务不属测试前置）：
client_factory 注入假客户端，构造不连网、首用探活的语义机械可断言。
outbox 仓储单测落 SQLite 底座（JSONB→JSON variant，infra.db 测试替身策略）；
真库 jsonb 断言见 test_eventbus_outbox_pg.py（PG 集成，无 TEST_DATABASE_URL 即 skip）。
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.infra.clock import freeze
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import (
    DomainEvent,
    EventBusConfigError,
    InMemoryEventBus,
    OutboxRow,
    OutboxStore,
    RedisStreamEventBus,
    ensure_outbox_table,
    make_event,
)

# ---------- InMemoryEventBus：发布-订阅 ----------


async def test_publish_delivers_to_subscribers_of_same_event_only() -> None:
    """同事件名订阅者按登记序全收；异名订阅者不收（98 §4 发布/订阅语义）。"""
    bus = InMemoryEventBus()
    seen: list[str] = []
    other: list[DomainEvent] = []

    async def first(e: DomainEvent) -> None:
        seen.append(f"first:{e.payload['x']}")

    async def second(e: DomainEvent) -> None:
        seen.append(f"second:{e.payload['x']}")

    def sync_other(e: DomainEvent) -> None:
        other.append(e)

    await bus.subscribe("IngestCompleted", first)
    await bus.subscribe("IngestCompleted", second)
    await bus.subscribe("RunFinished", sync_other)

    event = make_event("IngestCompleted", {"x": 1}, aggregate="kb_report:rpt-1")
    await bus.publish(event)

    assert seen == ["first:1", "second:1"]  # 派发序＝登记序；同步/异步处理器同权
    assert other == []  # 异名事件不串投
    assert bus.published == (event,)  # 观测窗留痕（信封原样）


async def test_make_event_stamps_clock_and_copies_payload() -> None:
    """工厂盖 infra.clock 时戳（B14）＋event_id 唯一；载荷防御性拷贝。"""
    at = datetime(2026, 9, 29, 10, 0, 0)
    payload = {"k": "v"}
    with freeze(at):
        a = make_event("RunFinished", payload)
        b = make_event("RunFinished", payload)
    assert a.occurred_at == at and b.occurred_at == at
    assert a.event_id != b.event_id
    payload["k"] = " mutated"
    assert a.payload == {"k": "v"}  # 拷贝语义：外部改动不回灌


async def test_subscriber_exception_is_isolated() -> None:
    """订阅异常隔离：单个订阅者抛错被吞（记日志），其余订阅者照常收到、发布方不抛。"""
    bus = InMemoryEventBus()
    received: list[str] = []

    async def broken(_e: DomainEvent) -> None:
        raise RuntimeError("订阅者内部炸了")

    async def healthy(e: DomainEvent) -> None:
        received.append(e.event_id)

    await bus.subscribe("RunFinished", broken)
    await bus.subscribe("RunFinished", healthy)

    event = make_event("RunFinished", {"run_id": "run-1"})
    await bus.publish(event)  # 不抛——隔离语义（P0-08 票面验收点）

    assert received == [event.event_id]  # 后位订阅者未受牵连


async def test_unsubscribe_thunk_is_idempotent() -> None:
    """退订 thunk 幂等：退订后不再收；重复退订无害。"""
    bus = InMemoryEventBus()
    seen: list[DomainEvent] = []
    unsub = await bus.subscribe("RunFailed", seen.append)

    await bus.publish(make_event("RunFailed", {}))
    assert len(seen) == 1

    unsub()
    unsub()  # 二次退订不抛
    await bus.publish(make_event("RunFailed", {}))
    assert len(seen) == 1


# ---------- RedisStreamEventBus：骨架缝（构造不连网 + 首用探活） ----------


def _failing_factory(url: str):
    def factory(_url: str) -> object:
        raise ConnectionError(f"connection refused: {_url}")

    return factory


async def test_redis_bus_lazy_construct_without_network() -> None:
    """构造不连网：client_factory 未被调用即无网络副作用（lazy 语义）。"""
    calls: list[str] = []

    def factory(url: str) -> object:
        calls.append(url)
        raise AssertionError("构造期不应触达工厂")

    RedisStreamEventBus("redis://localhost:6379/0", client_factory=factory)
    assert calls == []


async def test_redis_bus_publish_down_raises_config_error() -> None:
    """Redis 未起 → EventBusConfigError 显式配置错误，不静默降级（票面验收点）。"""

    def factory(_url: str) -> object:
        raise ConnectionError("connection refused")

    bus = RedisStreamEventBus("redis://localhost:6379/0", client_factory=factory)
    with pytest.raises(EventBusConfigError) as exc_info:
        await bus.publish(make_event("RunFinished", {}))
    assert "Redis 未就绪" in str(exc_info.value)


async def test_redis_bus_subscribe_down_raises_config_error() -> None:
    """subscribe 同走探活缝（消费组接线前的活体检查同语义）。"""

    def factory(_url: str) -> object:
        raise ConnectionError("connection refused")

    bus = RedisStreamEventBus("redis://localhost:6379/0", client_factory=factory)
    with pytest.raises(EventBusConfigError):
        await bus.subscribe("RunFinished", lambda e: None)


async def test_redis_bus_after_ping_is_explicit_not_implemented() -> None:
    """探活通过 → 显式 NotImplementedError（接线批未到，不提供半实现）。"""

    class FakeRedis:
        def __init__(self) -> None:
            self.pinged = False

        async def ping(self) -> bool:
            self.pinged = True
            return True

    fake = FakeRedis()
    bus = RedisStreamEventBus("redis://localhost:6379/0", client_factory=lambda _u: fake)  # type: ignore[arg-type]

    with pytest.raises(NotImplementedError):
        await bus.publish(make_event("RunFinished", {}))
    assert fake.pinged  # 探活先于缝界拒绝


# ---------- OutboxStore（SQLite 底座；真库 jsonb 见 PG 集成） ----------


@pytest.fixture
async def outbox_db(tmp_path) -> ConnectionManager:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "outbox.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_outbox_table(manager.engine())  # 幂等建表（P0-04 惯例）
    return manager


async def test_outbox_pending_scan_and_mark_published(outbox_db: ConnectionManager) -> None:
    """登记→待投递扫描（id 升序）→回执→不再待投递；回执幂等。"""
    store = OutboxStore(outbox_db)
    first = store.row_for(
        make_event("IngestCompleted", {"lib": "lib-1"}, aggregate="kb_report:rpt-1")
    )
    second = store.row_for(make_event("TicketApproved", {"ticket": "#CFG-01"}))

    await store.add(first)
    await store.add(second)

    pending = await store.pending()
    assert [r.event_type for r in pending] == ["IngestCompleted", "TicketApproved"]  # id 升序
    assert pending[0].aggregate == "kb_report:rpt-1"
    assert pending[0].published_at is None

    assert await store.mark_published(pending[0].id) is True
    rest = await store.pending()
    assert [r.event_type for r in rest] == ["TicketApproved"]  # 已回执行出队
    assert await store.mark_published(pending[0].id) is False  # 幂等：不重复盖写


async def test_outbox_add_in_shares_caller_transaction(outbox_db: ConnectionManager) -> None:
    """add_in 落在调用方会话：事务内同会话可见、随外层事务一起 commit（保投递语义）。"""
    store = OutboxStore(outbox_db)
    row = store.row_for(make_event("ProposalApproved", {"proposal": "#PP-0394"}))
    async with outbox_db.transaction() as session:
        await store.add_in(session, row)  # type: ignore[arg-type]
        in_txn = (await session.execute(select(OutboxRow))).scalars().all()
        assert [r.event_type for r in in_txn] == ["ProposalApproved"]  # 同会话即写即见
    assert [r.event_type for r in await store.pending()] == ["ProposalApproved"]  # commit 后可见
