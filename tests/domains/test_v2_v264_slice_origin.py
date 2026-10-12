"""V2-64 切片本体标签与材料出处装配——材料带出处＋多来源规则＋入库标签回写。

真源头（Owner 2026-10-12 拍板）：Q16 族1（分油田只答一半 10 题）／族3（错域锚定 3 ❌）
同根——答案轮材料标签只有 `[n]（report）正文`（C-正2 逐条计数：《》×0），模型分不清
每支材料出自哪份报告/哪个油田，把「另一个油田」误判成「同一油田的另一个季度」。

三件（全装配，零代码闸）：①入库抽取实体回写切片 well；②材料渲染带出处（trust｜报告名｜
本体标签）；③多来源规则去「不一致」前提（三处逐字稿）。
"""

from __future__ import annotations

from typing import Any

from appv2.retrieval.domain import FragmentRecord, Observation
from appv2.retrieval.engine import RetrievalEngine
from appv2.runtime.context import SYSTEM_PROMPT, ContextBuilder
from appv2.runtime.state import RunState

# ---------- 罐头 ----------

def _fragment_obs(index: int, tag: str, *, well: str | None = None) -> dict[str, Any]:
    obs: dict[str, Any] = {
        "index": index,
        "source": f"《{tag}》",
        "source_id": f"f{index}",
        "locator": {"kind": "fragment"},
        "trust": "report",
        "content": f"{tag} 正文若干内容",
    }
    if well is not None:
        obs["well"] = well
    return obs


def _ledger_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "source": "sem_metric#202",
        "source_id": "sem_metric#202",
        "locator": {"kind": "metric"},
        "trust": "ledger",
        "content": "抽油机时率（%）：状态 生效中",
    }


def _state(observations: list[dict[str, Any]]) -> RunState:
    return RunState(question="本井射孔参数", observations=observations)


def _render(state: RunState) -> str:
    ctx = ContextBuilder().compile(state, step="answer", instruction="起草答案")
    return str(ctx.messages[-1]["content"])


# ---------- T1 材料渲染带报告名出处（治「分不清」） ----------

def test_t1_material_carries_report_origin() -> None:
    out = _render(_state([_fragment_obs(1, "A-W11井完井工程报告")]))
    assert "[1]（report｜《A-W11井完井工程报告》）" in out


# ---------- T2 带本体标签（报告名＋well 两段） ----------

def test_t2_material_carries_ontology_tag() -> None:
    obs = [
        _fragment_obs(1, "A-W11井完井工程报告", well="W-11井·渤中34-5油田"),
        _fragment_obs(2, "Y-21井完井工程报告", well="Y-21井·渤中34-8油田"),
    ]
    out = _render(_state(obs))
    assert "[1]（report｜《A-W11井完井工程报告》｜W-11井·渤中34-5油田）" in out
    assert "[2]（report｜《Y-21井完井工程报告》｜Y-21井·渤中34-8油田）" in out


# ---------- T3 well 缺省退化（图开关关/未抽取——零漂移） ----------

def test_t3_missing_well_degrades_to_trust_origin() -> None:
    out = _render(_state([_fragment_obs(1, "B-月报")]))
    assert "[1]（report｜《B-月报》）" in out
    assert "[1]（report｜《B-月报》｜）" not in out  # 空段不留分隔符


# ---------- T4 台账卡（kind=metric）带出处不炸 ----------

def test_t4_ledger_card_renders_with_origin() -> None:
    out = _render(_state([_ledger_obs(1)]))
    assert "[1]（ledger｜sem_metric#202）" in out


# ---------- T5 多来源规则三处字面在场（旧「不一致」形退场） ----------

def test_t5_multi_source_rule_widened_in_three_places() -> None:
    from appv2.runtime.graph import _ANSWER_INSTRUCTION
    from appv2.runtime.orientation import _ANSWER_REQUIREMENTS

    for text in (SYSTEM_PROMPT, _ANSWER_REQUIREMENTS, _ANSWER_INSTRUCTION):
        assert "材料含多个来源（不同报告／油田／井）时逐个来源分别作答" in text
    # 旧「不一致」前提不再作为唯一触发条件
    assert "多来源不一致时逐源列明" not in SYSTEM_PROMPT
    assert "多来源不一致逐源列明" not in _ANSWER_REQUIREMENTS
    assert "多来源不一致时逐源列明" not in _ANSWER_INSTRUCTION


# ---------- T6 FragmentRecord→Observation well 透传 ----------

def test_t6_fragment_well_passthrough_to_observation() -> None:
    frag = FragmentRecord(
        fragment_id="f1",
        report_id="rpt-1",
        report="《A-W11井完井工程报告》",
        section="章节 03",
        library_id="lib-1",
        library="完井报告类",
        family="completion",
        text="射孔参数正文",
        well="W-11井·渤中34-5油田",
    )
    engine = RetrievalEngine(library=_NullLibrary(), embedder=_NullEmbedder())
    obs: Observation = engine._fragment_observation(  # 缝单测：只消费 fragment/score/leg
        _HitLike(frag, 1.0, "vector")
    )
    assert obs.well == "W-11井·渤中34-5油田"
    assert obs.report == "《A-W11井完井工程报告》"


class _HitLike:
    """engine 命中元组替身（_fragment_observation 只消费 fragment/score/leg）。"""

    def __init__(self, fragment: FragmentRecord, score: float, leg: str) -> None:
        self.fragment = fragment
        self.score = score
        self.leg = leg


class _NullLibrary:
    async def fragments(self) -> list[FragmentRecord]:
        return []


class _NullEmbedder:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] for _ in texts]


# ---------- T7 入库侧标签抽取（确定性，零模型） ----------

def test_t7_slice_well_tag_from_gated_edges() -> None:
    from app.domains.derivatives.service import _slice_well_tag

    class _Edge:
        def __init__(self, f: str, ft: str, t: str, tt: str) -> None:
            self.from_, self.from_type, self.to, self.to_type = f, ft, t, tt

    edges = [
        _Edge("W-11井", "井", "渤中34-5油田", "油田"),
        _Edge("W-11井", "井", "CEP-C平台", "平台"),
        _Edge("13-3/8″技术套管", "设备", "W-11井井筒", "井筒"),  # 非定位性类型——不入
    ]
    assert _slice_well_tag(edges) == "W-11井·渤中34-5油田·CEP-C平台"
    assert _slice_well_tag([]) == ""


# ---------- T8 FragmentStore.set_well 单行 UPDATE（sqlite） ----------

def test_t8_set_well_single_update(tmp_path: Any) -> None:
    import asyncio

    from sqlalchemy import text

    from app.domains.kb.store import FragmentStore
    from appv2.infra.db import ConnectionManager, DatabaseSpec

    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "kb.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )

    async def _run() -> None:
        manager = ConnectionManager([spec])
        async with manager.session() as session:
            await session.execute(text(
                "CREATE TABLE kb_fragment ("
                "id TEXT PRIMARY KEY, report_id TEXT, type TEXT, section TEXT,"
                "well TEXT, hit_text TEXT, current_version INTEGER,"
                "is_parent_only INTEGER, embedding TEXT,"
                "created_at TIMESTAMP, updated_at TIMESTAMP)"
            ))
            await session.execute(text(
                "INSERT INTO kb_fragment (id, well, current_version, is_parent_only) "
                "VALUES ('f1', NULL, 1, 0)"
            ))
        store = FragmentStore(manager)
        await store.set_well("f1", "W-11井·渤中34-5油田")
        await store.set_well("f9", "缺行静默")  # 行不存在不炸
        async with manager.readonly() as session:
            row = (await session.execute(
                text("SELECT well FROM kb_fragment WHERE id='f1'")
            )).scalar_one()
        assert row == "W-11井·渤中34-5油田"
        await manager.dispose()

    asyncio.run(_run())
