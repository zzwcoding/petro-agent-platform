"""derivatives wiki 测试共享夹具：sqlite 底座＋真实 KbService＋桩 LLM（永不触网）。

- StubCompleter：按 caller 脚本应答（kb.ingest.* / wiki.gen）——wiki.gen 应答
  携带结束哨兵（截断纪律：缺哨兵视为未完）。
- FakeSemantics：台账读面桩（词表供挂接；无账不挂的降级面直接不注入）。
- 装配：KbService＋DerivativesService 共用同一 sqlite 库；IngestCompleted/
  FragmentRevised 订阅照 main.py lifespan 接线（B9 缝真跑）。
"""

from collections.abc import AsyncIterator
from datetime import date
from typing import Any

import pytest

from app.domains.derivatives import DerivativesService
from app.domains.derivatives.domain import WIKI_END_MARKER
from app.domains.derivatives.store import ensure_derivatives_tables
from app.domains.kb import KbService
from app.domains.kb.store import ensure_kb_tables
from app.infra.db import ConnectionManager, DatabaseSpec
from app.infra.eventbus import InMemoryEventBus
from tests.domains.kb.conftest import FakeObjectStorage, StubCompleter, wait_until

# wiki 生成桩应答（自由 markdown 零固定节＋[[claim:]] 内嵌＋哨兵收尾）。
WIKI_STUB_ANSWER = (
    "## 概述\n\n"
    "本报告为 N-02 井完井报告：井别采油，2019-06-15 投产[[claim:f1]]，"
    "综合含水率 30%。[[claim:f1]]\n\n"
    "## 完井段\n\n"
    "完井段详见参数表，防砂方式筛管完井。[[claim:f999]]\n"
    f"{WIKI_END_MARKER}\n"
)


class FakeSemantics:
    """台账读面桩：list_terms/list_metrics 返回最小行投影（挂接词表）。"""

    def __init__(
        self,
        terms: list[dict[str, Any]] | None = None,
        metrics: list[dict[str, Any]] | None = None,
    ) -> None:
        self._terms = terms or []
        self._metrics = metrics or []

    async def list_terms(self, **kw: Any) -> Any:
        return _Page([_Row(t) for t in self._terms])

    async def list_metrics(self, **kw: Any) -> Any:
        return _Page([_Row(m) for m in self._metrics])


class _Row:
    def __init__(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)


class _Page:
    def __init__(self, items: list[_Row]) -> None:
        self.items = items


GLOSSARY_TERMS = [
    {
        "id": 7,
        "term": "递减增油",
        "type": "术语",
        "def_": "见指标 10",
        "status": "有效（待联席裁决）",
        "owner": "采油工艺所",
        # term 卡 expires_display 派生入参（M-09③——sem_term 行双轨字段；
        # 2027-03-31＝B4 合同 w2 演示卡同值）
        "status_key": "有效（待联席裁决）",
        "expires_at": date(2027, 3, 31),
    }
]
GLOSSARY_METRICS = [
    {
        "id": 5,
        "slot_name": "综合含水率",
        "name": "★ 综合含水率",
        "def_": "Q_w ÷（Q_o＋Q_w）× 100%",
        "grain": "月",
        "unit": "%",
        "status": ["生效中"],
        "owner": "开发室",
        "source": "A.2 日产计量＋A.6 化验",
    }
]

DEMO_TEXT = (
    "N-02 井完井报告\n1 基本情况\nN-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，"
    "井别采油（EW），2019-06-15 投产。\n2 完井段\n完井段详见参数表，"
    "防砂方式筛管完井。\n"
)


@pytest.fixture
async def wiki_db(tmp_path: Any) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "wiki.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())
    await ensure_derivatives_tables(manager.engine())
    yield manager
    await manager.dispose()


@pytest.fixture
async def wiki_env(
    wiki_db: ConnectionManager,
) -> AsyncIterator[tuple[KbService, DerivativesService, FakeObjectStorage,
                         StubCompleter, InMemoryEventBus]]:
    """kb＋derivatives 装配（事件订阅照 main.py lifespan——B9 缝真跑）。"""
    storage = FakeObjectStorage()
    completer = StubCompleter(
        answers={
            "kb.ingest.summary": "本报告为 N-02 井完井报告，2019-06-15 投产。",
            "kb.ingest.questions": "N-02 井是什么时候投产的？\nN-02 井在哪个平台？",
            "wiki.gen": WIKI_STUB_ANSWER,
        },
        default="应答",
    )
    bus = InMemoryEventBus()
    kb = KbService(wiki_db, completer, storage, eventbus=bus)
    derivatives = DerivativesService(
        wiki_db,
        completer,
        kb,
        FakeSemantics(GLOSSARY_TERMS, GLOSSARY_METRICS),
    )
    await bus.subscribe("IngestCompleted", derivatives.on_ingest_completed)
    await bus.subscribe("FragmentRevised", derivatives.on_fragment_revised)
    yield kb, derivatives, storage, completer, bus


@pytest.fixture
async def kb(
    wiki_env: tuple[KbService, DerivativesService, FakeObjectStorage,
                    StubCompleter, InMemoryEventBus],
) -> KbService:
    return wiki_env[0]


@pytest.fixture
async def derivatives(
    wiki_env: tuple[KbService, DerivativesService, FakeObjectStorage,
                    StubCompleter, InMemoryEventBus],
) -> DerivativesService:
    return wiki_env[1]


@pytest.fixture
async def storage(
    wiki_env: tuple[KbService, DerivativesService, FakeObjectStorage,
                    StubCompleter, InMemoryEventBus],
) -> FakeObjectStorage:
    return wiki_env[2]


async def make_report(
    kb: KbService, storage: FakeObjectStorage, *, lib_config: dict[str, Any] | None = None
) -> tuple[str, str, str]:
    """建库（可调配置）→受理→直传→confirm→等五步 done。

    返回 (lib_id, report_id, task_id)——report_id 由台账 keyword 反查
    （confirm 回执无报告号；tag 保证唯一）。
    """
    tag = f"wikitest{abs(hash(lib_config_key(lib_config))) % 100000}"
    lib = await kb.create_library(f"完井报告库{tag}", "completion", "aqiang · 平台运维")
    if lib_config is not None:
        await kb.save_library_config(
            lib.lib_id,
            switches={k: bool(lib_config.get(k)) for k in
                      ("semantic", "keyword", "wiki", "graph")},
            mode="smart",
            add_summary=bool(lib_config.get("add_summary", True)),
            add_questions=bool(lib_config.get("add_questions", True)),
            status=None,
            actor_who="aqiang · 平台运维",
        )
    demo = DEMO_TEXT
    receipt = await kb.upload_init(f"{tag}.txt", len(demo.encode()), lib.lib_id,
                                   "xiaoli · 地质/质检")
    key = receipt.put_url.split("/put/")[-1]  # 桩凭证 URL → 对象 key（直传模拟）
    await storage.put(key, demo.encode())
    confirm = await kb.upload_confirm(receipt.upload_id, "xiaoli · 地质/质检")
    await wait_until(lambda: _task_done(kb, confirm.task_id))
    reports = await kb.list_reports(keyword=tag)
    assert reports, "台账反查报告失败"
    return lib.lib_id, reports[0].id, confirm.task_id


def lib_config_key(config: dict[str, Any] | None) -> str:
    return str(sorted((config or {}).items()))


async def _task_done(kb: KbService, task_id: str) -> bool:
    progress = await kb.ingest_task(task_id)
    return progress.state in ("done", "failed", "stuck")

