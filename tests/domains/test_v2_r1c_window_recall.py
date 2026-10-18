"""V2-46 R1c 缺位回捞钉测（族 B 三层组合之「够得着」——P-045 开发拍）。

**V2-91 改判登记（2026-10-18）**：per-round 缺位名单**停发**——该名单按单轮
检索算，与实际「多子问题并集＋材料选择」后的送窗不一致（模型会照它说「某来源
未纳入」而该来源实已在窗）。`doc_retrieve` 不再产出 `locator.kind=window_miss`
的「检索窗注记（缺位名单）」独立观察；名单不进模型材料、不进引擎注记，只落
审计机读面（handlers 模块日志）。本文件按新行为改判：

- 观察面：带缺位段的 window_note → **零** window_miss 独立观察；window_note
  主段（计数＋差额段）逐字照旧走 notice 通道；notice 过滤面零改动。
- 模型面：缺位名单不进模型材料（render_materials）与引擎注记段
  （`answering.degradation.engine_notes`）。
- 回捞端到端：名单停发后 runtime 侧消费点（`graph.py` 的 `miss_obs` 取法——
  本票边界红线外，未删代码）恒取不到信号 → 回捞门**恒不开**：恰一次检索、
  零回炉轮、零 `window_miss_reentry` notice、step payload 无 `window_miss` 键。
  （V2-46 R1c 回捞机制随观察停发而失效＝本票的既知后果，登记在票面回报。）

合同面（CLARIFY_CONTRACT 回捞白场追加段）本票零改，逐字稿钉照旧。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.retrieval import RetrievalBundle, RetrievalNeed
from appv2.runtime import Budget, RunStore
from appv2.runtime.context import render_materials
from appv2.runtime.guide import CLARIFY_CONTRACT
from appv2.runtimev2.answering.degradation import engine_notes
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


# ---------- 钉二：观察面（V2-91 停发 window_miss 独立观察——handlers 单点） ----------


def test_bundle_to_result_stops_window_miss_observation() -> None:
    """未纳入名单在场→**零** window_miss 独立观察；window_note 主段 notice 通道原样。

    V2-91：缺位名单不再作为独立观察进观察列（原 V2-46 R1c 形停发）；主段（计数
    ＋差额段＋保席段）逐字照旧走 notice 通道，仅缺位名单段不随 notice 进模型面。
    """
    result = _bundle_to_result(
        RetrievalBundle(
            observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-x")],
            window_note=(
                "共检索到 2 条材料，1 条用进了答案"
                "；另有 1 条已找到但未用进答案（受送入答案的数量限制）"
                "；以下来源因数量限制未纳入：《Y-21井完井工程报告》"
                "；以下条目因直接命中提问关键词获得保留：《W-111 井完井报告》"
            ),
        )
    )
    kinds = [obs.locator["kind"] for obs in result.observations]
    assert kinds.count("notice") == 1  # window_note notice 通道原样（机制零改动）
    assert all(kind != "window_miss" for kind in kinds)  # 停发：零缺位独立观察
    assert not [
        obs for obs in result.observations if obs.content.startswith("检索窗注记")
    ]
    notice = next(
        obs for obs in result.observations if obs.locator["kind"] == "notice"
    )
    # 主段逐字（含差额段）＋保席段在场；缺位名单段不入 notice 正文。
    assert notice.content == (
        "共检索到 2 条材料，1 条用进了答案"
        "；另有 1 条已找到但未用进答案（受送入答案的数量限制）"
        "；以下条目因直接命中提问关键词获得保留：《W-111 井完井报告》"
    )
    assert "以下来源因数量限制未纳入" not in notice.content


def test_bundle_to_result_without_missing_has_no_window_miss() -> None:
    """无未纳入段→观察列形零漂移（零 window_miss；notice 正文＝window_note 原文）。"""
    result = _bundle_to_result(
        RetrievalBundle(
            observations=[_fragment_obs("片段。", "frag-y")],
            window_note="共检索到 1 条材料，1 条用进了答案",
        )
    )
    assert all(obs.locator["kind"] != "window_miss" for obs in result.observations)
    notice = next(
        obs for obs in result.observations if obs.locator["kind"] == "notice"
    )
    assert notice.content == "共检索到 1 条材料，1 条用进了答案"


# ---------- 钉三：模型面（V2-91——缺位名单不进材料／引擎注记；notice 仍滤） ----------


def test_missing_list_absent_from_model_face_and_notice_still_filtered() -> None:
    """缺位名单不进模型材料、不进引擎注记；notice 类观察照旧被滤（过滤面零改动）。

    V2-91 改判：原「window_miss 观察进模型面材料」形停发——名单停发后模型面
    只剩 window_note 主段（计数），经引擎注记段照常入窗（如实区分「没有」与
    「没送」）；未纳入来源名不出现在任何模型面。
    """
    note = {
        "index": 1,
        "content": "共检索到 2 条材料，1 条用进了答案",
        "source": "检索供给窗声明（截断显式）",
        "source_id": "window_note",
        "locator": {"kind": "notice", "notice_type": "window_note"},
    }
    text, meta = render_materials([note], max_observations=24)
    assert "共检索到 2 条材料，1 条用进了答案" not in text  # notice 过滤面不动
    assert meta == {
        "material_truncated": False, "material_rendered": 0, "material_total": 0,
    }  # notice 不计材料（元数据面同源）
    assert engine_notes([note]) == ["共检索到 2 条材料，1 条用进了答案"]  # 主段照常入窗
    assert "以下来源因数量限制未纳入" not in "\n".join(engine_notes([note]))


# ---------- 钉四/五：端到端（四相位真跑——V2-91 停发后门恒不开／零回炉） ----------

# 原 V2-46 R1c 缺位目标报告名（带题眼 token W-22——`recall_relevant` 相关面样本）；
# V2-91 停发后该词面门无在场调用者，剧本留用为「名单在场也不开门」的回归样本。
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
        "共检索到 2 条材料，1 条用进了答案；另有 1 条已找到但未用进答案（受送入答案的数量限制）"
        f"；以下来源因数量限制未纳入：《{_RECALL_TARGET}》"
    ),
)
_BUNDLE_SEATED = RetrievalBundle(
    observations=[_fragment_obs("根因：杆管偏磨（4.1 节）。", "frag-target")],
    window_note="共检索到 1 条材料，1 条用进了答案",
)
_BUNDLE_MISS_AGAIN = RetrievalBundle(
    observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-near-2")],
    window_note=(
        "共检索到 1 条材料，1 条用进了答案"
        "；以下来源因数量限制未纳入：《渤中34-8油田一季度注采调整与生产运行分析》"
    ),
)
# 名单与题面无表面关联的缺位形（缺位报告不含题眼 token「W-22」——门不开反例）。
_BUNDLE_MISS_IRRELEVANT = RetrievalBundle(
    observations=[_fragment_obs("邻近可得：W-22 检泵周期 215 天。", "frag-near-3")],
    window_note=(
        "共检索到 2 条材料，1 条用进了答案"
        "；以下来源因数量限制未纳入：《Y-21井完井工程报告》"
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


async def test_missing_list_no_reentry_end_to_end(tmp_path: Path) -> None:
    """V2-91 停发后：缺位名单无信号→回捞门恒不开（恰一次检索、零回炉、零门帧）。"""
    events, _completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_SEATED],
        second_need=_NEED_R2_ANCHORED,
        summary=_SUMMARY_RECALL,
    )
    try:
        assert events[-1].event == "blackbox"  # V2-54 黑匣子＝收口末事件
        assert events[-2].event == "verdict"
        assert events[-2].data["status"] == "completed"
        assert not _reentry_notices(events)  # 停发：零 window_miss_reentry 门帧
        assert retrieval.retrieve_calls == 1  # 恰一次检索（零回捞轮）
        # V2-50 ①anchors 确定性注入：模型未填锚——问句实体词 W-22 代码注入。
        assert retrieval.needs[0].anchors == ("W-22",)
        steps = await RunStore(db).list_steps(events[-2].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
        assert "window_miss" not in payloads[0]  # step payload 无缺位注记键（停发）
        # 零挂起零 ask。
        assert not [e for e in events if e.event == "ask"]
    finally:
        await db.dispose()


async def test_no_refurnace_instruction_without_missing_signal(tmp_path: Path) -> None:
    """V2-91 停发后：零回炉轮——决策恰 2 次（clar1→match1），无回炉指令面。"""
    events, completer, db, _retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_SEATED],
        second_need=_NEED_R2_ANCHORED,
        summary=_SUMMARY_RECALL,
    )
    try:
        assert events[-2].data["status"] == "completed"
        calls = completer.messages_of("v2.runtime.decision")
        assert len(calls) == 2  # clar1→match1（无回炉轮）
        decision_context = "".join(
            str(m.get("content", "")) for call in calls for m in call
        )
        assert "回炉：只分解以下失败/缺失子问题" not in decision_context
        assert "以下来源因数量限制未纳入" not in decision_context
    finally:
        await db.dispose()


async def test_second_miss_answers_honestly_without_loop(tmp_path: Path) -> None:
    """V2-91 停发后：二次缺位形同判——恰一次检索、零门帧、零「回捞已用尽」标记。"""
    events, completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS, _BUNDLE_MISS_AGAIN],
        second_need=dict(_NEED_R1),  # 同参重发形（原回捞簿记同向面——停发后无门）
        summary=_SUMMARY_HONEST,
    )
    try:
        assert events[-1].event == "blackbox"  # V2-54 黑匣子＝收口末事件
        assert events[-2].event == "verdict"
        assert events[-2].data["status"] == "completed"
        assert retrieval.retrieve_calls == 1  # 恰一次——无回捞环
        assert not _reentry_notices(events)
        steps = await RunStore(db).list_steps(events[-2].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
        # 汇总合同消费面：回捞轮不存在——终局注记不带「回捞已用尽」标记。
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert answer_calls
        summary_context = "".join(str(m.get("content", "")) for m in answer_calls[0])
        assert "缺位回捞已用尽" not in summary_context
    finally:
        await db.dispose()


async def test_no_round_budget_left_keeps_plain_ok(tmp_path: Path) -> None:
    """V2-91 停发后：门恒不开（与轮预算无关）——ok 原形、恰一次检索、零门帧。"""
    events, _completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS],
        second_need=dict(_NEED_R1),
        summary=_SUMMARY_HONEST,
        budget=Budget(max_rounds=1),
    )
    try:
        assert events[-1].event == "blackbox"  # V2-54 黑匣子＝收口末事件
        assert events[-2].event == "verdict"
        assert events[-2].data["status"] == "completed"
        assert not _reentry_notices(events)  # 门不开
        assert retrieval.retrieve_calls == 1  # 恰一次检索
        steps = await RunStore(db).list_steps(events[-2].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
    finally:
        await db.dispose()


async def test_irrelevant_missing_list_keeps_door_shut(tmp_path: Path) -> None:
    """V2-91 停发后：名单无关形与相关形同判——门恒不开；名单不进模型面。

    原 V2-46 R1c 的 `recall_relevant` 词面门（合同条件「本问题组相关报告/章节
    在列」的确定性机读）随名单停发而无在场调用者；本钉改为回归停发行为——
    名单既不进 step payload 也不进模型面（审计面＝handlers 模块日志留痕）。
    """
    events, completer, db, retrieval = await _run_recall_case(
        tmp_path,
        bundles=[_BUNDLE_MISS_IRRELEVANT],
        second_need=dict(_NEED_R1),
        summary=_SUMMARY_HONEST,
    )
    try:
        assert events[-1].event == "blackbox"  # V2-54 黑匣子＝收口末事件
        assert events[-2].event == "verdict"
        assert events[-2].data["status"] == "completed"
        assert not _reentry_notices(events)  # 门不开
        assert retrieval.retrieve_calls == 1  # 恰一次检索（零回捞）
        steps = await RunStore(db).list_steps(events[-2].data["run_id"])
        payloads = _batch_execute_payloads(steps)
        assert [p["status"] for p in payloads] == ["ok"]
        assert "window_miss" not in payloads[0]  # 停发：step payload 无缺位注记键
        # 模型面零缺位名单（材料面＋引擎注记面同判——审计面照留）。
        answer_calls = completer.messages_of("v2.runtime.answer")
        assert answer_calls
        summary_context = "".join(str(m.get("content", "")) for m in answer_calls[0])
        assert "以下来源因数量限制未纳入" not in summary_context
    finally:
        await db.dispose()
