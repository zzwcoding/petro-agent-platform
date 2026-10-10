"""V2-48 族 A 起草面塌方治理——JSON 通道隔离＋citation 落账＋verify 引标剥除钉测。

Q14 归因族 A（起草面交付塌方 ❌6＋⚠1）三层修向（票面验收五钉）：

- 泄漏钉：finalize/ask 发射围栏进答案面→确定性剥离→交付（NQ-D10/数-闸2 形
  红→绿）——纯围栏零余量→同相位重试一次→交付重试草稿；有余量→剥离后直接
  交付（零重试）；发射围栏在任何路径下不得进答案面。
- 零草稿重试钉：同相位零产出→重试一次→交付（NQ-M3 形——「（模型未产出草稿
  ——如实收口。）」由重试救回；重试恰一次，ScriptedCompleter 计数钉）。
- 再泄钉：重试仍泄漏/零产出→如实收口注记（泄漏文本零进答案面）。
- citation 落账钉：答案面 [n] ↔ citation 帧同步（悬空形清零——答案有 [n] 而
  citation 帧零支的 ⚠20 宽口径形收口；引用块仍收 verdict.cited 支撑集——R9
  「无支撑引标不收进引用集」语义不变）。
- verify 剥除钉：核验步改写面无裸 JSON 段（发射围栏/裸发射对象在 verify_draft
  入口剥除——纵深防御第二层）。

剧本沿 test_v2_agent_verify 同款装配（ScriptedCompleter 三 caller 桶——answer
桶队列耗尽＝AssertionError，恰是「重试恰一次」的机读钉）。
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    AskRequest,
    RunEvent,
    RunStore,
)
from appv2.runtime.graph import verify_draft
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)

# NQ-D10 形（Q14 最纯样本）：答案面仅 38 字发射围栏零交付。
_FINALIZE_FENCE = '```json\n{\n  "action": "finalize"\n}\n```'
_ASK_FENCE = '```json\n{"action": "ask", "ask": {"prompt": "口径?", "options": ["A", "B"]}}\n```'
# 数-闸2 形：相位提示原文回声＋行内裸发射 JSON。
_PROMPT_ECHO = (
    "s1【相位①·业务澄清】只输出一个 JSON 对象（可围栏）："
    '{"action":"finalize"}'
)
_REAL_DRAFT = "N-01 井 2025-09-01 日产油量 21.16 吨[1]。"


def _rows_outcome() -> QueryOutcome:
    """单行 agg 结果＋血缘卡（两支观察——[1]=agg_row、[2]=lineage 载承）。"""
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )


def _windowed_script(answers: Sequence[str]) -> dict[str, Sequence[str]]:
    return {
        "v2.runtime.understand": ["理解：问日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": [
            '{"action": "execute", "task_type": "data", '
            '"plan": {"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}',
            '{"thought": "材料已足够", "action": "finalize"}',
        ],
        "v2.runtime.answer": list(answers),
    }


def _notices(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


def _citations(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "citation"]


async def _ask_and_get_answer(
    tmp_path: Path, script: dict[str, Sequence[str]]
) -> tuple[str, list[RunEvent], Any, Any]:
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script
    )
    store = RunStore(db)
    handle = await runtime.ask(
        AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
    )
    events = await drain(handle)
    run = await store.get_run(handle.run_id)
    assert run is not None and run.status == "completed"
    return run.answer or "", events, completer, db


# ---------- 泄漏钉：finalize 围栏进答案面→剥离→重试交付（NQ-D10 形红→绿） ----------


async def test_finalize_fence_leak_stripped_retry_delivers(tmp_path: Path) -> None:
    answer, events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([_FINALIZE_FENCE, _REAL_DRAFT])
    )
    try:
        # 剥离后零余量→同相位重试一次→交付重试草稿。
        assert "21.16 吨[1]" in answer
        # 发射围栏零进答案面（JSON 通道隔离不变量）。
        assert "```" not in answer
        assert '"action"' not in answer and '"finalize"' not in answer
        # 重试恰一次（answer 桶两次调用——ScriptedCompleter 计数机读）。
        assert completer.counts()["v2.runtime.answer"] == 2
        # 剥离机读信号在场（帧级判分锚）。
        assert any(n.get("type") == "emission_strip" for n in _notices(events))
    finally:
        await db.dispose()


async def test_ask_fence_leak_also_isolated(tmp_path: Path) -> None:
    # ask 发射围栏同辖（finalize/ask 双通道——票面①）。
    answer, _events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([_ASK_FENCE, _REAL_DRAFT])
    )
    try:
        assert "21.16 吨[1]" in answer
        assert '"action"' not in answer and '"ask"' not in answer.replace('"action"', "")
        assert "```" not in answer
        assert completer.counts()["v2.runtime.answer"] == 2
    finally:
        await db.dispose()


async def test_prompt_echo_emission_line_stripped(tmp_path: Path) -> None:
    # 数-闸2 形：相位提示原文回声＋行内裸发射 JSON——整行剥除→零余量→重试交付。
    answer, _events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([_PROMPT_ECHO, _REAL_DRAFT])
    )
    try:
        assert "21.16 吨[1]" in answer
        assert '"action"' not in answer
        assert "相位①" not in answer  # 回声行整行剥除——提示原文不进答案面
        assert completer.counts()["v2.runtime.answer"] == 2
    finally:
        await db.dispose()


async def test_partial_leak_stripped_without_retry(tmp_path: Path) -> None:
    # 系统-届满形：正文＋尾部围栏——剥离后有余量→直接交付（零重试）。
    leaky = _REAL_DRAFT + "\n\n" + _FINALIZE_FENCE
    answer, _events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([leaky])
    )
    try:
        assert "21.16 吨[1]" in answer
        assert "```" not in answer and '"action"' not in answer
        assert completer.counts()["v2.runtime.answer"] == 1  # 有余量不烧重试
    finally:
        await db.dispose()


# ---------- 零草稿重试钉：同相位零产出→重试一次→交付（NQ-M3 形） ----------


async def test_zero_draft_retry_once_delivers(tmp_path: Path) -> None:
    answer, _events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script(["", _REAL_DRAFT])
    )
    try:
        assert "21.16 吨[1]" in answer
        assert "未产出草稿" not in answer  # 重试救回——不再零交付收口
        assert completer.counts()["v2.runtime.answer"] == 2  # 重试恰一次
    finally:
        await db.dispose()


async def test_zero_draft_twice_honest_closing(tmp_path: Path) -> None:
    # 两拍皆零——如实收口注记（既有 NQ-M3 话术保持）。
    answer, _events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script(["", ""])
    )
    try:
        assert "（模型未产出草稿——如实收口。）" in answer
        assert completer.counts()["v2.runtime.answer"] == 2
    finally:
        await db.dispose()


# ---------- 再泄钉：重试仍泄漏→如实收口注记（泄漏文本零进答案面） ----------


async def test_retry_releak_honest_closing_note(tmp_path: Path) -> None:
    answer, events, completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([_FINALIZE_FENCE, _FINALIZE_FENCE])
    )
    try:
        assert "如实收口" in answer
        assert "```" not in answer and '"action"' not in answer  # 泄漏零进答案面
        assert completer.counts()["v2.runtime.answer"] == 2  # 重试恰一次不环
        assert any(n.get("type") == "emission_strip" for n in _notices(events))
    finally:
        await db.dispose()


# ---------- citation 落账钉：答案面 [n] ↔ citation 帧同步（悬空形清零） ----------


async def test_citation_frames_sync_with_answer_marks(tmp_path: Path) -> None:
    # 行 1 支撑（[1] 收进 verdict.cited）；行 2 无据改写——改写行保留的悬空 [2]
    #（D-诱1/A-正2 形：答案有 [n] 而 citation 帧零支）由落账清零：帧集＝答案面
    # 合法 [n] ∪ cited。引用块仍只列支撑集（R9「无支撑引标不收进引用集」不变）。
    draft = _REAL_DRAFT + "\n全油田 86 口井昨日均超产 50 吨[2]。"
    answer, events, _completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([draft])
    )
    try:
        assert "未找到（材料未披露）" in answer  # 行 2 无据改写（INV-1 不变）
        assert "[2]" in answer  # 改写行保留 [n]——悬空形在案
        marks = {1, 2}  # 答案面合法 [n]（两支观察在场）
        frames = sorted(int(c["index"]) for c in _citations(events))
        assert frames == sorted(marks), f"citation 帧未同步答案面 [n]：{frames}"
        # 引用块仍收支撑集 [1]（R9 语义不变——悬空 [2] 不进引用块）。
        closing = answer.split("引用：")[-1]
        assert "[1]" in closing and "[2]" not in closing
    finally:
        await db.dispose()


async def test_citation_frames_cover_dangling_marks_when_cited_empty(tmp_path: Path) -> None:
    # 全行改写形（Q14 ⚠20 宽口径最窄样本）：cited=∅ 而答案面有合法 [n]——
    # 修前帧零支（悬空），修后逐 [n] 落账。
    draft = "全油田 86 口井昨日均超产 50 吨[2]。"
    answer, events, _completer, db = await _ask_and_get_answer(
        tmp_path, _windowed_script([draft])
    )
    try:
        assert "未找到（材料未披露）" in answer
        frames = sorted(int(c["index"]) for c in _citations(events))
        assert frames == [2], f"悬空 [2] 未落账：{frames}"
    finally:
        await db.dispose()


# ---------- verify 剥除钉：改写面无裸 JSON 段 ----------


def _agg_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "content": "井号=N-01；区块=渤南；日期=2025-09-01；日产油量（吨）=21.16",
        "source": "agg.fct_daily_metering",
        "source_id": "N-01@2025-09-01",
        "version": None,
        "freshness": "",
        "scope": "agg",
        "locator": {"kind": "agg_row", "table": "agg.fct_daily_metering",
                    "well_id": "N-01"},
    }


def test_verify_draft_strips_bare_json_segments() -> None:
    # NQ-D10 形直灌 verify（纵深防御第二层——起草面漏剥由核验层兜底）。
    draft = (
        "```json\n{\n  \"action\": \"finalize\"\n}\n```\n"
        '{"action": "finalize"}\n'
        + _REAL_DRAFT
    )
    text, rewritten, cited, split = verify_draft(draft, [_agg_obs(1)])
    assert "```" not in text
    assert '"action"' not in text
    assert "21.16 吨[1]" in text  # 有据断言行不受剥除影响
    assert rewritten == 0 and cited == [1] and split is False


def test_verify_draft_non_emission_json_kept() -> None:
    # 非发射形 JSON（无 action 键）不辖剥除——域外内容零误伤。
    draft = "口径数据 {\"metric\": \"日产油量\", \"unit\": \"吨\"} 仅为示例。\n" + _REAL_DRAFT
    text, _rewritten, _cited, _split = verify_draft(draft, [_agg_obs(1)])
    assert '"metric"' in text  # 非发射 JSON 原样保留（剥除只辖发射形）
    assert "21.16 吨[1]" in text
