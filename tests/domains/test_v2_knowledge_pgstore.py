"""V2-19 knowledge 生产读面——PgKnowledgeStore 行为测试（specs/modules.md
knowledge 卡外部依赖「PG sem_* 表（只读）」的落位件验收）。

装配：sqlite 测试底座（infra.db DatabaseSpec driver=sqlite——V2 runtime 测试
同款）手建 sem_* 四表（DDL 投影读面消费列；jsonb→TEXT 承载——PG 侧 asyncpg
对 jsonb 同样回 str，投影层 json.loads 单点归一），行值**程序化誊自问数组
台账态快照**（question_array_snapshot——fixture 真源单点，零业务发明）。

判定核心＝**证据逐字段全等**（Evidence 冻结 dataclass eq）：同一行值下
PgKnowledgeStore（sem_* 表直读）与 InMemoryKnowledgeStore（fixture 快照）
产出的 Evidence 必须逐字段一致——生产读面行为对齐的机器证明；台账差行
（PG 现行行多于快照，如 sem_relation 6~10 行）不进本测（对齐锚＝同一行集）。

覆盖：指标精确命中（bound）／别名归一（source 注记）／在册未绑定／届满
术语／families 三族／浏览态全集／INV-2 只读（返回容器副本＋零写出口）。
全程同步缝（bridge 无运行环时本线程直跑——测试零事件循环要求）。
"""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.knowledge import (
    InMemoryKnowledgeStore,
    PgKnowledgeStore,
    SemanticQuery,
    question_array_snapshot,
)

TODAY = date(2026, 10, 8)


def _spec(main_db: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(main_db), user="", password="", pool_size=2, max_overflow=1,
    )


_SEM_DDL = (
    """CREATE TABLE sem_metric (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, slot_name TEXT NOT NULL,
        def TEXT NOT NULL, grain TEXT NOT NULL, unit TEXT NOT NULL,
        status TEXT NOT NULL, dispute TEXT, version INTEGER NOT NULL,
        calibers TEXT NOT NULL, default_caliber TEXT)""",
    """CREATE TABLE sem_term (
        id INTEGER PRIMARY KEY, term TEXT NOT NULL, type TEXT NOT NULL,
        def TEXT NOT NULL, status TEXT NOT NULL, status_key TEXT NOT NULL,
        version INTEGER NOT NULL, expires_at DATE)""",
    """CREATE TABLE sem_object (
        id INTEGER PRIMARY KEY, obj TEXT NOT NULL, attr TEXT,
        status TEXT NOT NULL, version INTEGER)""",
    """CREATE TABLE sem_relation (
        id INTEGER PRIMARY KEY, rel TEXT NOT NULL, read TEXT NOT NULL)""",
)


async def _seed(db: ConnectionManager) -> None:
    """sem_* 四表建表＋问数组台账态快照程序化誊入（行值零改动）。"""
    snapshot = question_array_snapshot()
    async with db.session() as session:
        for ddl in _SEM_DDL:
            await session.execute(text(ddl))
        for row in snapshot.metrics:
            await session.execute(
                text(
                    "INSERT INTO sem_metric (id, name, slot_name, def, grain, unit,"
                    " status, dispute, version, calibers, default_caliber)"
                    " VALUES (:id, :name, :slot_name, :def_, :grain, :unit, :status,"
                    " :dispute, :version, :calibers, :default_caliber)"
                ),
                {
                    "id": row.id, "name": row.name, "slot_name": row.slot_name,
                    "def_": row.def_, "grain": row.grain, "unit": row.unit,
                    "status": json.dumps(list(row.status)), "dispute": row.dispute,
                    "version": row.version,
                    "calibers": json.dumps([dict(c) for c in row.calibers]),
                    "default_caliber": row.default_caliber,
                },
            )
        for row in snapshot.terms:
            await session.execute(
                text(
                    "INSERT INTO sem_term (id, term, type, def, status, status_key,"
                    " version, expires_at)"
                    " VALUES (:id, :term, :type, :def_, :status, :status_key,"
                    " :version, :expires_at)"
                ),
                {
                    "id": row.id, "term": row.term, "type": row.type, "def_": row.def_,
                    "status": row.status, "status_key": row.status_key,
                    "version": row.version,
                    "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                },
            )
        for row in snapshot.objects:
            await session.execute(
                text(
                    "INSERT INTO sem_object (id, obj, attr, status, version)"
                    " VALUES (:id, :obj, :attr, :status, :version)"
                ),
                {"id": row.id, "obj": row.obj, "attr": row.attr,
                 "status": row.status, "version": row.version},
            )
        for row in snapshot.relations:
            await session.execute(
                text("INSERT INTO sem_relation (id, rel, read) VALUES (:id, :rel, :read)"),
                {"id": row.id, "rel": row.rel, "read": row.read},
            )


@pytest.fixture
async def pg_store(tmp_path: Path) -> PgKnowledgeStore:
    db = ConnectionManager([_spec(tmp_path / "sem.db")])
    try:
        await _seed(db)
        yield PgKnowledgeStore([_spec(tmp_path / "sem.db")], today=TODAY)
    finally:
        await db.dispose()


def _memory() -> InMemoryKnowledgeStore:
    return InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)


# ---------- 证据逐字段全等（生产行为对齐的机器证明） ----------


def test_metric_exact_hit_parity(pg_store: PgKnowledgeStore) -> None:
    """指标精确命中：Evidence 逐字段全等＋binding_state=bound＋source=sem_metric#201。"""
    actual = pg_store.metric_by_name("日产油量")
    assert actual == _memory().metric_by_name("日产油量")
    assert actual is not None
    assert actual.binding_state == "bound"
    assert actual.source == "sem_metric#201"
    assert actual.scope == "日/井"


def test_alias_canonicalize_parity(pg_store: PgKnowledgeStore) -> None:
    """别名归一命中：source 带「经别名归一」注记——术语与指标两落点逐字段全等。"""
    assert pg_store.evidence(SemanticQuery(text="CEP-D 井口平台")) == (
        _memory().evidence(SemanticQuery(text="CEP-D 井口平台"))
    )
    metric = pg_store.metric_by_name("日产液")
    assert metric is not None and "经别名归一（日产液→日产液量）" in metric.source
    assert metric == _memory().metric_by_name("日产液")


def test_unbound_flagged_parity(pg_store: PgKnowledgeStore) -> None:
    """在册未绑定指标（含水率/配产量）：binding_state=unbound——降级依据如实。"""
    for slot in ("含水率", "配产量"):
        actual = pg_store.metric_by_name(slot)
        assert actual is not None and actual.binding_state == "unbound"
        assert actual == _memory().metric_by_name(slot)


def test_expired_flagged_parity(pg_store: PgKnowledgeStore) -> None:
    """届满术语（日产液 #11）：expired＋届满日期展示串——漂移标注如实。"""
    hits = pg_store.evidence(SemanticQuery(text="日产液"))
    assert hits == _memory().evidence(SemanticQuery(text="日产液"))
    term = next(h for h in hits if h.kind == "term")
    assert term.binding_state == "expired"
    assert term.freshness == "2026-06-30（已届满）"


def test_families_complete_parity(pg_store: PgKnowledgeStore) -> None:
    """families 三族标注＋relation group 透传——副本语义逐键全等。"""
    actual = pg_store.families()
    assert actual == _memory().families()
    assert {"completion", "monthly", "dynamic"} <= {g for group in actual.values() for g in group}


def test_browse_parity(pg_store: PgKnowledgeStore) -> None:
    """浏览态（空 text）：五类全要素——逐条全等（按要素身份排序比对：
    生产行序＝行 id 序；fixture 快照构建序为题册排列——序不属证据语义）。"""
    key = lambda ev: (ev.kind, ev.element_id)  # noqa: E731 - 比对键单点
    actual = sorted(pg_store.evidence(SemanticQuery(text="")), key=key)
    expected = sorted(_memory().evidence(SemanticQuery(text="")), key=key)
    assert actual == expected


# ---------- INV-2 只读纪律 ----------


def test_inv2_readonly(pg_store: PgKnowledgeStore) -> None:
    """只读：返回容器一律副本＋读面零写出口（INV-2）。"""
    aliases = pg_store.aliases()
    aliases["污染键"] = "污染值"
    assert "污染键" not in pg_store.aliases()
    families = pg_store.families()
    families["污染键"] = ["污染组"]
    assert "污染键" not in pg_store.families()
    rows = pg_store.evidence(SemanticQuery(text=""))
    rows.clear()
    assert pg_store.evidence(SemanticQuery(text=""))
    forbidden = ("add", "insert", "save", "update", "delete", "upsert", "write")
    assert not [name for name in dir(pg_store) if name.lower() in forbidden]
