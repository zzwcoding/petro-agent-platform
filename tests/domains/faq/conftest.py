"""faq 测试共享夹具：sqlite 底座＋假对象存储＋桩 LLM＋桩向量/读缝（永不触网）。

- FakeObjectStorage：内存字典（put_bytes/presign_get/get_bytes）——B3-8 导入
  暂存与导出全库件的 MinIO 往返断言用。
- StubCompleter：按 caller 脚本应答（faq.scan.mine/faq.candidate.draft/
  faq.draft.from_refs/faq.ledger_merged.suggestion）。
- StubEmbedder：可控向量缝——embed_map 命中的文本用注入向量（cosine 可精确
  到 1.0/0.0 判 dup），未命中回落 LocalHashEmbedder。
- RecordingAudit：B12 写口捕获（LedgerMerged 联动留痕断言用）。
"""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.domains.faq import FaqService
from app.domains.faq.store import ensure_faq_tables, seed_demo_if_empty
from app.domains.gateway import Completion
from app.domains.kb.domain import LocalHashEmbedder
from app.domains.security.domain import AuditRow
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import InMemoryEventBus


class FakeObjectStorage:
    """内存对象存储（对象落桶即记 bytes——导出/导入往返断言用）。"""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.signed: list[str] = []

    async def put_bytes(self, key: str, data: bytes) -> None:
        self.objects[key] = data

    async def presign_put(self, key: str, *, ttl_seconds: int = 1800) -> str:
        self.signed.append(key)
        return f"https://minio.test/put/{key}"

    async def presign_get(self, key: str, *, ttl_seconds: int = 3600) -> str:
        self.signed.append(key)
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
        self, answers: dict[str, str | Exception] | None = None, default: str = "应答"
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


class StubEmbedder:
    """可控向量缝：embed_map 命中即用注入向量，未命中回落本地确定性向量。"""

    def __init__(self, embed_map: dict[str, list[float]] | None = None) -> None:
        self.embed_map = embed_map or {}
        self._fallback = LocalHashEmbedder()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self.embed_map]
        fallback = await self._fallback.embed(missing) if missing else []
        out: dict[str, list[float]] = {}
        for t in texts:
            if t in self.embed_map:
                out[t] = self.embed_map[t]
        filled = iter(fallback)
        return [out.get(t) or next(filled) for t in texts]


class RecordingAudit:
    """B12 写口捕获（audit 行留存断言）。"""

    def __init__(self) -> None:
        self.rows: list[AuditRow] = []

    async def audit(self, row: AuditRow, *, session: Any = None) -> None:
        self.rows.append(row)


def same_vector() -> list[float]:
    return [1.0, 0.0, 0.0]


def other_vector() -> list[float]:
    return [0.0, 1.0, 0.0]


@pytest.fixture
async def faq_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "faq.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_faq_tables(manager.engine())
    await seed_demo_if_empty(manager.engine())  # 演示种子（九条问答＋四簇候选）
    yield manager
    await manager.dispose()


@pytest.fixture
async def audit() -> RecordingAudit:
    return RecordingAudit()


def make_service(
    db: ConnectionManager,
    completer: StubCompleter,
    storage: FakeObjectStorage,
    *,
    embedder: StubEmbedder | None = None,
    eventbus: InMemoryEventBus | None = None,
    audit: RecordingAudit | None = None,
    ledger_loader: Any = None,
    slice_loader: Any = None,
    ontology_names_loader: Any = None,
    kb_corpus_loader: Any = None,
    step_seconds: float = 0.0,
    session_loader: Any = None,
) -> FaqService:
    """组装 FaqService（显式参数注入——各测试按需给缝）。"""
    return FaqService(
        db,
        completer,
        storage,
        embedder=embedder,
        eventbus=eventbus,
        audit=audit,
        ledger_loader=ledger_loader,
        slice_loader=slice_loader,
        ontology_names_loader=ontology_names_loader,
        kb_corpus_loader=kb_corpus_loader,
        session_loader=session_loader,
        step_seconds=step_seconds,
    )
