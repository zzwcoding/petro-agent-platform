"""kb 测试共享夹具：sqlite 底座＋假对象存储＋桩 LLM（永不触网——P0 先例红线）。

- FakeObjectStorage：内存字典；presign_put 仅登记待传 key（不落内容——
  「对象已落桶」由测试显式 put 模拟客户端直传，未 put 即 confirm 409 判据）。
- StubCompleter：按 caller 脚本应答（kb.route/kb.ingest.summary/kb.ingest.questions）。
  chunk 步自 DE-05 起不查 LLM（同文同切——章节边界恒纯规则图），旧
  kb.ingest.structure caller 已退役，本夹具无需为其脚本应答；需要脚本化富化
  应答的用例见 test_kb_structure_map.py 自带 ScriptedCompleter。
"""

from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from app.domains.gateway import Completion
from app.domains.kb import KbService
from app.domains.kb.store import ensure_kb_tables
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import InMemoryEventBus


class FakeObjectStorage:
    """内存对象存储（桶语义从简：key 全局唯一即可）。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.signed: list[str] = []

    async def put(self, key: str, data: bytes) -> None:
        self.objects[key] = data

    async def presign_put(self, key: str, *, ttl_seconds: int = 1800) -> str:
        self.signed.append(key)
        return f"https://minio.test/put/{key}"

    async def presign_get(self, key: str, *, ttl_seconds: int = 3600) -> str:
        return f"https://minio.test/get/{key}"

    async def exists(self, key: str) -> bool:
        return key in self.objects

    async def get_bytes(self, key: str) -> bytes:
        if key not in self.objects:
            raise KeyError(key)
        return self.objects[key]


class StubCompleter:
    """桩 LLM：按 caller 出脚本应答；记录调用序（B6 断言用）。"""

    def __init__(
        self,
        answers: dict[str, str | Exception] | None = None,
        default: str = "应答",
    ) -> None:
        self.answers = answers or {}
        self.default = default
        self.calls: list[tuple[str, str]] = []

    async def complete(
        self, alias: str, messages: list[dict[str, str]], *, caller: str, **params: Any
    ) -> Completion:
        content = messages[-1]["content"]
        self.calls.append((caller, content))
        answer: str | Exception = self.answers.get(caller, self.default)
        if isinstance(answer, Exception):
            raise answer
        return Completion(
            content=answer,
            prompt_tokens=10,
            completion_tokens=5,
            usage_estimated=False,
            call_id="call-stub",
            cost_yuan=0.0001,
            fallback=False,
            served_alias=alias,
        )


async def wait_until(predicate: Callable[[], Any], *, deadline_s: float = 5.0) -> None:
    """轮询等待（管线任务体为 asyncio task——demo 量级亚秒完成）。"""
    import asyncio
    import time

    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if await predicate():
            return
        await asyncio.sleep(0.02)
    raise TimeoutError("条件等待超时")


@pytest.fixture
async def kb_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "kb.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())  # 幂等建表（P0-04 惯例）
    yield manager
    await manager.dispose()


@pytest.fixture
async def kb_service(
    kb_db: ConnectionManager,
) -> AsyncIterator[tuple[KbService, FakeObjectStorage, StubCompleter, InMemoryEventBus]]:
    storage = FakeObjectStorage()
    completer = StubCompleter(
        answers={
            "kb.ingest.summary": "本报告为 N-02 井（渤中28-1-N2）完井报告，2019-06-15 投产。",
            "kb.ingest.questions": "N-02 井是什么时候投产的？\nN-02 井在哪个平台？",
            "kb.route": (
                '{"mode": "existing", "lib_name": "完井报告库", '
                '"reason": "完井话题", "confidence": 0.9}'
            ),
        }
    )
    bus = InMemoryEventBus()
    service = KbService(kb_db, completer, storage, eventbus=bus)
    yield service, storage, completer, bus


DEMO_TEXT = (
    "N-02 井完井报告\n"
    "1 基本情况\n"
    "N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），"
    "2019-06-15 投产，当前状态生产中。\n"
    "2 完井段\n"
    "完井段详见射孔与防砂参数表，防砂方式筛管完井。\n"
)
