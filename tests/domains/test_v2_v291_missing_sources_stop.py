"""V2-91 停发 per-round 缺位名单钉测（消除与实投窗自相矛盾）。

票面三钉（逐条机检）：
- `::no_missing_sources_observation`：桩检索返回带 missing 的 window_note →
  observations 里**无**「检索窗注记（缺位名单）」独立观察（零
  `locator.kind=window_miss`）；window_note 主段计数观察仍在（notice 通道原样）。
- `::window_note_counts_unchanged`：recalled/sent 主段逐字不变（含差额段）——
  仅摘除缺位名单段，其余段逐字照旧。
- `::missing_sources_kept_in_audit`：missing 名单仍可在审计机读面（本模块日志）
  取到（审计不丢）。

附钉（票面施工基准第二条）：缺位名单**不进模型材料、不进引擎注记**——名单按
单轮检索算，与实际「多子问题并集＋材料选择」后的送窗不一致（模型会照它说
「某来源未纳入」而该来源实际在窗内）。「按实投窗重算的缺位名单」登记为后续
能力（不在本票恢复）。
"""

from __future__ import annotations

import logging
from typing import Any

from appv2.retrieval import RetrievalBundle
from appv2.runtimev2.answering.degradation import engine_notes
from appv2.runtimev2.context.materials import render_materials
from appv2.tools.handlers import _bundle_to_result
from tests.domains.test_v2_react_loop import _fragment_obs

_MISSING = "《Y-21井完井工程报告》"
_MISSING_MARK = "以下来源因数量限制未纳入"
# 逐字稿＝build_window_note 组装形（V2-82e 用户语措辞）：主段＋差额段＋缺位段＋保席段。
_FULL_NOTE = (
    "共检索到 2 条材料，1 条用进了答案"
    "；另有 1 条已找到但未用进答案（受送入答案的数量限制）"
    f"；{_MISSING_MARK}：{_MISSING}"
    "；以下条目因直接命中提问关键词获得保留：《W-111 井完井报告》"
)
# 停发后的 notice 正文（主段＋差额段＋保席段逐字，仅缺位名单段摘除）。
_MAIN_NOTE = (
    "共检索到 2 条材料，1 条用进了答案"
    "；另有 1 条已找到但未用进答案（受送入答案的数量限制）"
    "；以下条目因直接命中提问关键词获得保留：《W-111 井完井报告》"
)


def _result() -> Any:
    return _bundle_to_result(
        RetrievalBundle(
            observations=[_fragment_obs("邻近可得：W-111 观察井 21.4 MPa。", "frag-v291")],
            window_note=_FULL_NOTE,
        )
    )


def _notice_of(result: Any) -> Any:
    notes = [obs for obs in result.observations if obs.locator["kind"] == "notice"]
    assert len(notes) == 1
    return notes[0]


def _obs_dicts(result: Any) -> list[dict[str, Any]]:
    return [
        {
            "index": offset,
            "content": obs.content,
            "source": obs.source,
            "source_id": obs.source_id,
            "locator": dict(obs.locator),
        }
        for offset, obs in enumerate(result.observations, start=1)
    ]


# ---------- 钉一：零「检索窗注记（缺位名单）」独立观察 ----------


def test_no_missing_sources_observation() -> None:
    """带 missing 的 window_note → 零 window_miss 独立观察；主段计数观察仍在。"""
    result = _result()
    assert all(obs.locator["kind"] != "window_miss" for obs in result.observations)
    assert not [
        obs for obs in result.observations if obs.content.startswith("检索窗注记")
    ]
    notice = _notice_of(result)
    assert notice.locator["notice_type"] == "window_note"
    assert "共检索到 2 条材料，1 条用进了答案" in notice.content


# ---------- 钉二：window_note 主段逐字不变（含差额段） ----------


def test_window_note_counts_unchanged() -> None:
    """recalled/sent 主段（含差额段）逐字不变——仅缺位名单段摘除。"""
    notice = _notice_of(_result())
    assert notice.content == _MAIN_NOTE
    assert _MISSING_MARK not in notice.content
    assert _MISSING not in notice.content


def test_missing_segment_stripped_when_last() -> None:
    """缺位段在串尾（无后继段）→ 连同前导「；」摘除，主段逐字留。"""
    result = _bundle_to_result(
        RetrievalBundle(
            observations=[],
            window_note=f"共检索到 2 条材料，1 条用进了答案；{_MISSING_MARK}：{_MISSING}",
        )
    )
    assert _notice_of(result).content == "共检索到 2 条材料，1 条用进了答案"


# ---------- 钉三：名单仍在审计机读面（审计不丢） ----------

def test_missing_sources_kept_in_audit(caplog: Any) -> None:
    """missing 名单仍可在审计机读面（本模块日志）取到。"""
    with caplog.at_level(logging.INFO, logger="appv2.tools.handlers"):
        _result()
    audit = "\n".join(record.getMessage() for record in caplog.records)
    assert _MISSING_MARK in audit
    assert _MISSING in audit


# ---------- 附钉：名单不进模型材料、不进引擎注记 ----------


def test_missing_list_absent_from_model_face() -> None:
    """缺位名单既不进模型材料、也不进引擎注记；主段计数经引擎注记照常入窗。"""
    rows = _obs_dicts(_result())
    material_text, _meta = render_materials(rows, max_observations=24)
    assert _MISSING_MARK not in material_text
    assert _MISSING not in material_text
    notes_text = "\n".join(engine_notes(rows))
    assert _MISSING_MARK not in notes_text
    assert _MISSING not in notes_text
    assert "共检索到 2 条材料，1 条用进了答案" in notes_text
