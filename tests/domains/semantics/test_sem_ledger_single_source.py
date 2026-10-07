"""B5-01 台账种子单一真源——同名双行防回归闸（sqlite 单测底座，全程可跑）。

Owner 2026-10-07 拍板案 A：同步器为唯一写入真源，0019 迁移转历史基线
（migrations/versions/20261005_0019_sem_ledger_seed.py 头注已标注；upgrade/
downgrade 语义与种子行不动——Alembic 历史不可改写）。本闸机检四件事：
- 同 domain 同名行唯一：同步器（唯一写入路径）写出的 sem_term/sem_metric
  逐名唯一——复现 semantics.term_dedup_manual 双行场景不再发生；
- 双通道同名重叠封顶：0019 历史基线种子与同步器种子的同名交集必须恰为
  已裁决并回的六条术语——任何一侧再增重叠名（同域同名）即本闸红；
- 并回保真：六条 def 与各自 GLS-PETRO 锚权威定义逐字一致（0019 头注列的
  T1 审查项「种子与本体权威定义逐字对照」在同步器通道机检化），并回前
  C1 简写不在场；
- 并回只搬定义文字：expires_at 等 C1 现值字段并回前后不动（票面红线）。
0019 模块经 importlib 文件位装载（仅读种子常量做对账，不执行 upgrade/
downgrade——PG 真迁移执行见 test_sem_seed_0019_pg.py）。
"""

from __future__ import annotations

import importlib.util
from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.security.domain import resolve_actor
from app.domains.semantics import domain as sem_domain
from app.domains.semantics.service import SemanticsService
from app.domains.semantics.store import SemMetric, SemTerm, ensure_semantics_tables
from app.infra.db import ConnectionManager, DatabaseSpec

_REPO = Path(__file__).resolve().parents[3]
_MIGRATION_0019 = _REPO / "migrations" / "versions" / "20261005_0019_sem_ledger_seed.py"
_GLS_PETRO = _REPO / "ontology" / "petro" / "glossary-model.yaml"

# B5-01 裁决并回的六条术语（0019 术语 211~216 与同步器 #2/#3/#4/#5/#7/#8 同名）。
_MERGED_NAMES = frozenset({"躺井", "剔检产量", "有效产量", "时率", "递减增油", "存水率"})

# 并回前后对照（前＝C1 现值简写，后＝GLS 权威全文）——防回退到简写的钉子。
_PRE_MERGE_DEFS: dict[str, str] = {
    "剔检产量": "剔除检修井口径",
    "有效产量": "需修饰词消歧（开井日历 / 剔检）",
    "躺井": "作业区口语",
    "时率": "见指标 14",
    "递减增油": "见指标 10（含口径争议注记）",
    "存水率": "注入水留存地层比例（物质平衡用）",
}

# 并回不动的 C1 演示有效期（票面红线：只搬定义文字，expires_at 不动）。
_C1_EXPIRES_AT: dict[str, date | None] = {
    "剔检产量": date(2027, 12, 31),
    "有效产量": date(2027, 6, 30),
    "躺井": date(2026, 12, 31),
    "时率": date(2027, 6, 30),
    "递减增油": date(2027, 3, 31),
    "存水率": None,  # 长期
}


class _NullAudit:
    """B12 审计替身（本闸不审内容——只满足服务构造缝）。"""

    async def audit(self, row: Any, *, session: Any = None) -> None:
        return None


def _load_0019_module() -> Any:
    """0019 版本文件位装载（同 test_sem_seed_0019_pg.py 手法）——只读常量。"""
    spec = importlib.util.spec_from_file_location("m0019_sem_ledger_seed_b5", _MIGRATION_0019)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _gls_petro_entries() -> dict[str, dict[str, Any]]:
    """GLS-PETRO 词条（键＝元素锚 id——种子 ontology_refs 的对账域）。"""
    raw = _GLS_PETRO.read_text(encoding="utf-8")
    return {str(e["id"]): e for e in yaml.safe_load(raw)["terms"]}


def _gls_petro_defs_by_term() -> dict[str, str]:
    """GLS-PETRO 权威定义（键＝术语名——petro GLS 的 term 字段全表唯一）。"""
    raw = _GLS_PETRO.read_text(encoding="utf-8")
    return {str(e["term"]): str(e["definition"]) for e in yaml.safe_load(raw)["terms"]}


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[ConnectionManager]:
    spec = DatabaseSpec(
        name="primary",
        role="primary",
        driver="sqlite",
        host="",
        port=0,
        database=str(tmp_path / "semantics-single-source.db"),
        user="",
        password="",
        pool_size=2,
        max_overflow=1,
    )
    manager = ConnectionManager([spec])
    engine = create_async_engine(spec.url())
    await ensure_semantics_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


# ---------- ① 同 domain 同名行唯一（同步器写出面） ----------


async def test_synchronizer_writes_name_unique_ledger(db: ConnectionManager) -> None:
    """唯一写入路径写出的台账逐名唯一——六条并回术语各恰一行。"""
    service = SemanticsService(db, _NullAudit())
    await service.sync_from_ontology_repo("mr#b5-01", resolve_actor(None))
    async with db.readonly() as session:
        terms = (await session.execute(select(SemTerm))).scalars().all()
        metrics = (await session.execute(select(SemMetric))).scalars().all()
    term_names = [str(row.term) for row in terms]
    metric_names = [str(row.name) for row in metrics]
    # 同 domain 同名行唯一（semantics.term_dedup_manual 场景不再发生）
    assert len(term_names) == len(set(term_names)) == 11
    assert len(metric_names) == len(set(metric_names)) == 15
    assert _MERGED_NAMES <= set(term_names)


# ---------- ② 双通道同名重叠封顶（常量级对账——不执行迁移） ----------


def test_dual_channel_name_overlap_capped_at_adjudicated_six() -> None:
    """0019 历史基线 × 同步器种子：术语同名交集恰为六条裁决词，指标名/slot 零交集。

    任何一侧再增同域同名行（双行场景复现的前兆）本闸即红；id 段位隔离
    （0019 头注设计：bohai 占 200+，同步器 petro 占 1+）一并机检。
    """
    m0019 = _load_0019_module()
    migration_terms = {str(row[1]) for row in m0019._TERM_SEEDS}
    migration_metric_names = {str(row[1]) for row in m0019._METRIC_SEEDS}
    migration_metric_slots = {str(row[2]) for row in m0019._METRIC_SEEDS}
    seed_terms = {str(s.payload["term"]) for s in sem_domain.TERM_SEEDS}
    seed_metric_names = {str(s.payload["name"]) for s in sem_domain.METRIC_SEEDS}
    seed_metric_slots = {
        sem_domain.metric_slot_name(str(s.payload["name"])) for s in sem_domain.METRIC_SEEDS
    }
    assert seed_terms & migration_terms == set(_MERGED_NAMES)  # 封顶＝恰六条
    assert seed_metric_names & migration_metric_names == set()
    assert seed_metric_slots & migration_metric_slots == set()
    assert all(1 <= int(s.row_id) <= 11 for s in sem_domain.TERM_SEEDS)
    assert all(1 <= int(s.row_id) <= 15 for s in sem_domain.METRIC_SEEDS)
    assert all(int(row[0]) >= 201 for row in m0019._METRIC_SEEDS)
    assert all(int(row[0]) >= 211 for row in m0019._TERM_SEEDS)


# ---------- ③ 并回保真：def 与 GLS-PETRO 锚逐字对齐 ----------


def test_merged_defs_verbatim_against_gls_petro() -> None:
    """六条并回 def 与各自 GLS-PETRO 权威定义逐字一致；并回前 C1 简写不在场。"""
    entries = _gls_petro_entries()
    merged = [s for s in sem_domain.TERM_SEEDS if str(s.payload["term"]) in _MERGED_NAMES]
    assert {str(s.payload["term"]) for s in merged} == set(_MERGED_NAMES)
    for seed in merged:
        entry = entries[seed.ontology_refs[0]]
        assert str(seed.payload["def"]) == str(entry["definition"])  # T1 逐字对照
        assert str(seed.payload["def"]) != _PRE_MERGE_DEFS[str(seed.payload["term"])]


def test_c1_demo_fields_untouched_by_merge_back() -> None:
    """并回只搬定义文字——expires_at/type/status/owner 保持并回前取值。"""
    entries = _gls_petro_entries()
    m0019 = _load_0019_module()
    migration_type_by_name = {str(row[1]): str(row[2]) for row in m0019._TERM_SEEDS}
    by_name = {str(s.payload["term"]): s for s in sem_domain.TERM_SEEDS}
    for name in _MERGED_NAMES:
        seed = by_name[name]
        entry = entries[seed.ontology_refs[0]]
        assert seed.payload["expires_at"] == _C1_EXPIRES_AT[name]  # C1 演示值不动
        assert str(seed.payload["type"]) == migration_type_by_name[name]  # 展示拼装不变
        assert str(seed.payload["status"]) == str(entry["status"])
        assert str(seed.payload["owner"]) == str(entry["owner"])


# ---------- ④ 同步器落库面（sqlite）：六行带 GLS 全文 ----------


async def test_synced_merged_rows_carry_gls_full_text(db: ConnectionManager) -> None:
    """同步器投影落库后，六条术语行 def＝GLS 权威全文（非 C1 简写）。"""
    service = SemanticsService(db, _NullAudit())
    await service.sync_from_ontology_repo("mr#b5-01", resolve_actor(None))
    defs_by_term = _gls_petro_defs_by_term()
    async with db.readonly() as session:
        rows = (await session.execute(select(SemTerm))).scalars().all()
    by_term = {str(row.term): row for row in rows}
    for name in _MERGED_NAMES:
        assert by_term[name].def_ == defs_by_term[name]
