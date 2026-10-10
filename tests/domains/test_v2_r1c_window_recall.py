"""V2-46 R1c 缺位回捞钉测（族 B 三层组合之「够得着」——P-045 开发拍）。

票面任务三条逐条落测：
- 缺位名单进模型面：送窗截断发生时（window_note 载「缺位来源」段——
  build_window_note 单点措辞），缺位来源名单以**非 notice 类观察**
  （locator.kind=window_miss——「检索窗注记」：未进窗名单＋原因）进上下文；
  notice 过滤机制本身零改动（window_note notice 通道原样、notice 类观察仍
  不进模型面）；历史轮随消息簿记收窄（ADR-0006 机制——无新增收窄面）。
- 合同补回捞白场（CLARIFY_CONTRACT 追加段逐字稿 char 相等——施工基准）。
- 每子问题限一次：批量相位缺位首遇＝开回捞门（子问题转回炉面 failed——拒因
  携检索窗注记，clarify 回炉重发带 anchors 的 knowledge 链检索）；回捞已用尽
  （同 id 或同参指纹在簿——V2-37 簿记同向）＝直答如实终局（不环）。

红线钉：无缺位段零漂移（零 window_miss 观察）；轮预算无余门不开（ok 原形）；
notice 过滤面与消息历史簿记主干零改动。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.retrieval import RetrievalBundle, RetrievalNeed
from appv2.runtime import Budget, RunStore
from appv2.runtime.context import ContextBuilder
from appv2.runtime.guide import CLARIFY_CONTRACT
from appv2.runtime.state import RunState
from appv2.tools.handlers import _bundle_to_result
from tests.domains.test_v2_agent_loop import (
    QueueQueryEngine,
    make_runtime,
)
from tests.domains.test_v2_four_phase import (
    LEDGER_DUMP,
    UNDERSTAND_MULTI,
    _run_question,
)
from tests.domains.test_v2_react_loop import _fragment_obs, _rows_outcome

# ---------- 钉一：回捞白场逐字稿（合同追加段——票面施工基准 char 相等） ----------

# 逐字稿载体＝dispatch/pending/P-045.md 追加段引用块（三行，逐字含换行）。
RECALL_CLAUSE = (
    "回捞白场：当「检索窗注记」载有未进窗来源且本问题组相关报告/章节在列——\n"
    "可经回炉对该子问题重发带 anchors（报告名/章节锚）的 knowledge 链检索，\n"
    "每子问题限一次（消耗一轮，不挂起不占 ask）。"
)
# P-039 附 2 追加段结尾（既有措辞零删改的对照锚——追加不得插入既有段）。
_P039_TAIL = "＝窗双 null 发射，由引擎缺参反问兜底（三选一合法形，拍板⑥）——两分支不得混淆。"


def test_clarify_contract_recall_clause_verbatim() -> None:
    """CLARIFY_CONTRACT 尾部＝票面回捞白场逐字稿（char 相等）；P-039 附 2 段零删改。"""
    assert CLARIFY_CONTRACT.endswith(RECALL_CLAUSE)
    assert _P039_TAIL in CLARIFY_CONTRACT
    # 追加不插入：既有段在前、逐字稿在后。
    assert CLARIFY_CONTRACT.index(_P039_TAIL) < CLARIFY_CONTRACT.index(RECALL_CLAUSE)


# ---------- 钉二：观察面（window_miss 非 notice 观察——handlers 单点） ----------


def test_bundle_to_result_emits_window_miss_observation() -> None:
    """缺位名单在场→window_miss 观察进观察列（名单＋原因）；window_note notice 通道原样。"""
    result = _bundle_to_result(
        RetrievalBundle(
            observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-x")],
            window_note=(
                "召回 2 支/送窗 1 支；已召回未送窗 1 支"
                "；缺位来源（预算未及）：《Y-21井完井工程报告》"
                "；题眼锚保底席位：《W-111 井完井报告》"
            ),
        )
    )
    kinds = [obs.locator["kind"] for obs in result.observations]
    assert kinds.count("notice") == 1  # window_note notice 通道原样（机制零改动）
    miss = [obs for obs in result.observations if obs.locator["kind"] == "window_miss"]
    assert len(miss) == 1
    assert miss[0].content.startswith("检索窗注记：")
    # 名单＋原因段逐字在场（build_window_note 单点措辞）。
    assert "缺位来源（预算未及）：《Y-21井完井工程报告》" in miss[0].content
    # 名单段之外不携带：召回/送窗数字面仍走 notice 通道；扩席实录段不入注记。
    assert "召回 2 支" not in miss[0].content
    assert "题眼锚保底席位" not in miss[0].content


def test_bundle_to_result_without_missing_has_no_window_miss() -> None:
    """无缺位段→零 window_miss 观察（旧观察列形零漂移）。"""
    result = _bundle_to_result(
        RetrievalBundle(
            observations=[_fragment_obs("片段。", "frag-y")],
            window_note="召回 1 支/送窗 1 支",
        )
    )
    assert all(obs.locator["kind"] != "window_miss" for obs in result.observations)


# ---------- 钉三：模型面可见（ContextBuilder——window_miss 进材料、notice 仍滤） ----------


def test_window_miss_reaches_model_face_and_notice_still_filtered() -> None:
    """window_miss 观察进模型面材料；notice 类观察照旧被滤（过滤面零改动）。"""
    miss = {
        "index": 1,
        "content": "检索窗注记：缺位来源（预算未及）：《Y-21井完井工程报告》",
        "source": "检索供给窗声明（缺位名单）",
        "source_id": "window_miss",
        "locator": {"kind": "window_miss"},
    }
    note = {
        "index": 2,
        "content": "召回 2 支/送窗 1 支",
        "source": "检索供给窗声明（截断显式）",
        "source_id": "window_note",
        "locator": {"kind": "notice", "notice_type": "window_note"},
    }
    state = RunState(run_id="run-r1c", question="q", observations=[miss, note])
    compiled = ContextBuilder().compile(state, step="decision", instruction="任务")
    material = compiled.messages[-1]["content"]
    assert "缺位来源（预算未及）：《Y-21井完井工程报告》" in material  # 模型面可见
    assert "window_miss" in compiled.manifest.source_type  # Manifest 来源行随行
    assert "召回 2 支/送窗 1 支" not in material  # notice 过滤面不动


# ---------- 钉四/五：回捞端到端（四相位真跑——回炉→anchors 重检→进窗／不环） ----------

# 缺位目标报告名带题眼 token（W-22）——通过 recall_relevant 相关面（合同条件
# 「本问题组相关报告/章节在列」的确定性机读）；反例见「名单无关门不开」钉。
_RECALL_TARGET = "W-22井检泵作业与杆断分析月报"


class QueueRetrievalEngine:
    """剧本化按次出列检索（首支缺位→回捞支——回捞端到端的被控源；needs 全捕获）。"""

    def __init__(self, bundles: Sequence[RetrievalBundle]) -> None:
        self._queue = list(bundles)
        self.needs: list[RetrievalNeed] = []
        self.retrieve_calls = 0

    async def retrieve(self, need: RetrievalNeed) -> RetrievalBundle:
        self.retrieve_calls += 1
        self.needs.append(need)
        if len(self._queue) > 1:
            return self._queue.pop(0)
        return self._queue[0]


def _clarify(subtasks: list[dict[str, Any]]) -> str:
    return json.dumps(
        {"action": "decompose", "question_group": {"subtasks": subtasks}},
        ensure_ascii=False,
    )


_S1 = {
    "id": "s1",
    "question": "W-22 井杆断的根因是什么？",
    "ledger_notes": "文档所载——knowledge 链（台账无此口径）",
    "chain": "knowledge",
    "tool": "doc_retrieve",
}


def _match(need: dict[str, Any]) -> str:
    return json.dumps(
        {"matches": [
            {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
             "retrieval_need": need},
        ]},
        ensure_ascii=False,
    )


_NEED_R1 = {"question": "W-22 井杆断根因", "family_hints": ["monthly"]}
_NEED_R2_ANCHORED = {
    "question": "W-22 井杆断根因",
    "anchors": [_RECALL_TARGET, "4.1"],
    "family_hints": ["monthly"],
}

_BUNDLE_MISS = RetrievalBundle(
    observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-near")],
    window_note=(
        "召回 2 支/送窗 1 支；已召回未送窗 1 支"
        f"；缺位来源（预算未及）：《{_RECALL_TARGET}》"
    ),
)
_BUNDLE_SEATED = RetrievalBundle(
    observations=[_fragment_obs("根因：杆管偏磨（4.1 节）。", "frag-target")],
    window_note="召回 1 支/送窗 1 支",
)
_BUNDLE_MISS_AGAIN = RetrievalBundle(
    observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-near-2")],
    window_note=(
        "召回 1 支/送窗 1 支"
        "；缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》"
    ),
)
# 名单与题面无表面关联的缺位形（缺位报告不含题眼 token「W-22」——门不开反例）。
_BUNDLE_MISS_IRRELEVANT = RetrievalBundle(
    observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-near-3")],
    window_note=(
        "召回 2 支/送窗 1 支"
        "；缺位来源（预算未及）：《Y-21井完井工程报告》"
    ),
)
_SUMMARY_RECALL = "W-22 杆断根因：杆管偏磨 [2]。"
_SUMMARY_HONEST = "W-22 杆断根因：材料未载明，仅有邻近检泵周期 215 天 [1]。"


async def _run_recall_case(
    tmp_path: Path,
    *,
    bundles: Sequence[RetrievalBundle],
    second_need: dict[str, Any],
    summary: str,
    budget: Budget | None = None,
) -> tuple[list[Any], Any, Any, QueueRetrievalEngine]:
    """回捞端到端标准剧本：clar1→match1（无锚）→clar2（回炉）→match2（第二参）。"""
    retrieval = QueueRetrievalEngine(list(bundles))
    script = {
        "v2.runtime.understand": [UNDERSTAND_MULTI],
        "v2.runtime.decision": [
            _clarify([dict(_S1)]),
            _match(dict(_NEED_R1)),
            _clarify([dict(_S1)]),  # 回炉轮：只分解失败子集（剧本同形）
            _match(dict(second_need)),
        ],
        "v2.runtime.answer": [summary],
    }
    runtime, completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=script,
        budget=budget,
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
        retrieval=retrieval,
    )
    events = await _run_question(runtime, "W-22 井杆断的根因（回捞端到端）")
    return events, completer, db, retrieval


def _batch_execute_payloads(steps: list[Any]) -> list[dict[str, Any]]:
    return [
        dict(s.payload or {})
        for s in steps
        if s.step_type == "execute" and (s.payload or {}).get("subtask_id")
    ]


def _reentry_notices(events: list[Any]) -> list[dict[str, Any]]:
    return [
        e.data
        for e in events
        if e.event == "notice" and e.data.get("type") == "window_miss_reentry"
    ]


async def test_recall_end_to_end_target_seated(tmp_path: Path) -> None:
    """缺位含目标→回炉→anchors 重检→目标进窗出数（回捞白场端到端钉）。"""
    events, _completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_SEATED],
        second_need=_NEED_R2_ANCHORED,
        summary=_SUMMARY_RECALL,
    )
    try:
        assert events[-1].event == "verdict"
        assert events[-1].data["status"] == "completed"
        # 回捞门机读帧在场（window_miss_reentry notice——触发帧证据面）。
        reentry = _reentry_notices(events)
        assert len(reentry) == 1
        assert "s1" in reentry[0]["content"]
        # 恰两次检索：首支缺位→回炉→带 anchors 重检（目标进窗）。
        assert retrieval.retrieve_calls == 2
        # V2-50 ①anchors 确定性注入：首支模型未填锚——问句实体词 W-22 代码注入
        # （注入钉行为变化：旧形断言 anchors == ()，随 V2-50 注入面语义更新）。
        assert retrieval.needs[0].anchors == ("W-22",)
        # 注入项在前不可清空，模型锚增补续后（模型可增补不可清空钉）。
        assert retrieval.needs[1].anchors == ("W-22", _RECALL_TARGET, "4.1")
        steps = await RunStore(db).list_steps(events[-1].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok", "ok"]
        # 首支缺位步携检索窗注记（step payload 证据面）。
        assert "缺位来源（预算未及）" in str(payloads[0].get("window_miss", ""))
        assert "window_miss" not in str(payloads[1].get("window_miss", ""))
        # 零挂起零 ask（回捞白场——不挂起不占 ask）。
        assert not [e for e in events if e.event == "ask"]
    finally:
        await db.dispose()


async def test_refurnace_instruction_carries_window_note(tmp_path: Path) -> None:
    """回炉面拒因携检索窗注记原文＋白场 hint——clarify 回炉指令可见（模型面接线）。"""
    events, completer, db, _retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_SEATED],
        second_need=_NEED_R2_ANCHORED,
        summary=_SUMMARY_RECALL,
    )
    try:
        assert events[-1].data["status"] == "completed"
        calls = completer.messages_of("v2.runtime.decision")
        assert len(calls) == 4  # clar1→match1→clar2（回炉）→match2（带锚重发）
        furnace_context = "".join(str(m.get("content", "")) for m in calls[2])
        assert "回炉：只分解以下失败/缺失子问题" in furnace_context
        assert f"缺位来源（预算未及）：《{_RECALL_TARGET}》" in furnace_context
        assert "缺位回捞白场" in furnace_context
    finally:
        await db.dispose()


async def test_second_miss_answers_honestly_without_loop(tmp_path: Path) -> None:
    """回捞重发同参再次缺位→直答如实终局（不环——恰两次检索、门只开一次）。"""
    events, completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_MISS_AGAIN],
        second_need=dict(_NEED_R1),  # 同参重发（同指纹——V2-37 簿记同向）
        summary=_SUMMARY_HONEST,
    )
    try:
        assert events[-1].event == "verdict"
        assert events[-1].data["status"] == "completed"
        assert retrieval.retrieve_calls == 2  # 恰两次——不环
        assert len(_reentry_notices(events)) == 1  # 门只开一次
        steps = await RunStore(db).list_steps(events[-1].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok", "ok"]
        # 汇总合同消费终局注记：子问题结果清单带「回捞已用尽」直答标记。
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert answer_calls
        summary_context = "".join(str(m.get("content", "")) for m in answer_calls[0])
        assert "缺位回捞已用尽" in summary_context
    finally:
        await db.dispose()


async def test_no_round_budget_left_keeps_plain_ok(tmp_path: Path) -> None:
    """轮预算无余（回炉轮无处安放）＝门不开：ok 原形、零回炉、零 window_miss 门帧。"""
    events, _completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS],
        second_need=dict(_NEED_R1),
        summary=_SUMMARY_HONEST,
        budget=Budget(max_rounds=1),
    )
    try:
        assert events[-1].event == "verdict"
        assert events[-1].data["status"] == "completed"
        assert not _reentry_notices(events)  # 门不开
        assert retrieval.retrieve_calls == 1  # 恰一次检索
        steps = await RunStore(db).list_steps(events[-1].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
    finally:
        await db.dispose()


async def test_irrelevant_missing_list_keeps_door_shut(tmp_path: Path) -> None:
    """名单与题面无表面关联（缺位报告不含题眼 token）＝门不开：ok 原形零回炉。

    合同条件「本问题组相关报告/章节在列」的确定性机读（recall_relevant）——
    机器不为噪声名单消耗回炉轮（注记可见性不受影响：window_miss 观察照常进
    模型面材料）。"""
    events, completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS_IRRELEVANT],
        second_need=dict(_NEED_R1),
        summary=_SUMMARY_HONEST,
    )
    try:
        assert events[-1].event == "verdict"
        assert events[-1].data["status"] == "completed"
        assert not _reentry_notices(events)  # 门不开
        assert retrieval.retrieve_calls == 1  # 恰一次检索（零回捞）
        steps = await RunStore(db).list_steps(events[-1].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
        assert "缺位来源" in str(payloads[0].get("window_miss", ""))  # 注记照常随行
        # 汇总材料面可见注记（模型面不受门影响）。
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert answer_calls
        summary_context = "".join(str(m.get("content", "")) for m in answer_calls[0])
        assert "缺位来源（预算未及）：《Y-21井完井工程报告》" in summary_context
    finally:
        await db.dispose()
