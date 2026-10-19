"""V2-119 子问题覆盖信号验收（程序确定性检测 → 作答上下文显式提示）。

票面＝`tickets/v2/V2-119-子问题覆盖信号.md`（含「Kimi 评审修正」节）。验收四条：①`B-正6`／
`NQ-M8` 形离线复现：零支撑子问题在作答上下文出现提示行、且作答步 payload 有 `subtask_coverage`；
②材料充分题**不出现**提示行（零误报）；③提示行不改材料、不改 explore 决策（模型自决）；④全量闸绿
（跑批面在回报）。

判据面（零语义、纯形态）：逐子问题取「其锚／术语／数值记号」三 kind（同 `answer_anchors` 的装配
序 `subject`／`term`／`number`），按**分层**判其在渲染窗内是否出现（强锚→弱锚→数字锚，首个非空
kind 定论——同 `context._anchor_score` 的分层加权序）：锚／术语面两侧同规＝`normalize_anchor_text`
（跨形包含——核验归属审同规）＋锚面另引 `appv2.text_tokens.boundary_hit`；数字面＝
`appv2.text_tokens.num_token_hit`（V2-100 D-a 单点，依赖自由）。

两形离线复现的题面／窗口取自 EB11 归因（`eval/suite-147/results/EB11-归因.md` §S1／§S2）：
`NQ-M8`＝题眼 `Y-41` 而窗内只有 34-5 月报（`W-41` 顶替——注意数字记号 `41` 在 `W-41` 上**全等
命中**，故分层判据是本票的判据本体）；`B-正6`＝34-8 侧近三年数据在窗内零支撑（窗内只有 34-5
月报的同名指标值）。
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from appv2.runtimev2.answering import (
    PAYLOAD_SUBTASK_COVERAGE_KEY,
    subtask_coverage,
)
from appv2.runtimev2.answering import constants as answering_constants
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.prompts import (
    ANSWER_COVERAGE_HEAD,
    ANSWER_COVERAGE_LINE,
    CONTRACT_CONSTANT_FAMILIES,
    answer_coverage_section,
    answer_system_contract,
    assemble_answer_prompt,
)
from appv2.runtimev2.state import INTENT_EXPLORE, INTENT_VERIFY, RunState
from appv2.runtimev2.transport import EventBus
from appv2.text_tokens import num_token_hit

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIMEV2_DIR = _REPO_ROOT / "appv2" / "runtimev2"

_MODEL_CALLER = "answer"

# `NQ-M8` 题面逐字（`eval/results/Q12M-跑批结果.jsonl` 行 8／
# `eval/results/tools/suites_q6.py:40`）。
_NQ_M8_QUESTION = (
    '判断并纠正这句话："Y-41 井本月抽油杆在第 41 根处断裂躺井，并于当月完成了螺旋气锚加装。"'
    "这句话有哪几处与报告不符？逐一纠正，并给出 Y-41 井在报告中的真实状态（所属清单、预警类型、"
    "首次发现时间、当前安排），以及本月真正实施气锚加装的井号。"
)
# `B-正6` 题面逐字（`eval/answers/B-题目与答案.md:44`）＋34-8 侧子问题（归因 §S1：
# 窗内只有 34-5 月报）。
_B_ZHENG6_SUBTASK = "渤中34-8 油田近三年 8 月平均检泵周期的变化趋势"
_B_ZHENG6_SUBTASK_34_5 = "渤中34-5 油田近三年 8 月平均检泵周期的变化趋势"
_SOURCE_34_5 = "《B-渤中34-5油田躺井治理与检泵作业月报-202608》"

# 作答上下文段头（材料段真源＝`context.render_materials`；本处只作定位字面面）。
_MATERIALS_HEAD = "\n观察材料：\n"
_SUBTASK_LIST_HEAD = "子问题结果清单："
_COVERAGE_HEAD = "子问题覆盖表："


def _obs(
    index: int,
    kind: str,
    *,
    content: str,
    source: str,
    well: str = "",
) -> dict[str, Any]:
    """观察 fixture（材料面字段形：`index`／`locator.kind`／`content`／出处／井标签）。"""
    return {
        "index": index,
        "locator": {"kind": kind},
        "content": content,
        "source": source,
        "well": well,
        "source_id": "",
        "version": None,
    }


def _window_34_5() -> list[dict[str, Any]]:
    """34-5 月报窗口（`NQ-M8`／`B-正6` 两形的**错源**窗——`Y-41`／`渤中34-8` 零命中）。"""
    return [
        _obs(
            1,
            "fragment",
            content="W-41 井光杆密封盒刺漏，2026 年 8 月完成检泵作业 1 井次",
            source=_SOURCE_34_5,
            well="W-41",
        ),
        _obs(
            2,
            "fragment",
            content="2026 年 8 月平均检泵周期 415 天，近三年同期对比 386→415→428 天",
            source=_SOURCE_34_5,
        ),
    ]


def _window_34_8() -> list[dict[str, Any]]:
    """34-8 月报窗口（`B-正6` 的**正源**窗——材料充分形）。"""
    return [
        _obs(
            1,
            "fragment",
            content="Y-41 井 2027-01-06 泵效 52%，平均检泵周期 396 天",
            source="《B-渤中34-8油田躺井治理与检泵作业月报-202701》",
            well="Y-41",
        ),
    ]


def _state(**overrides: Any) -> RunState:
    values: dict[str, Any] = {
        "run_id": "run-v119",
        "question": "渤中34-8 油田近三年 8 月平均检泵周期的变化趋势？",
        "actor": "laowang",
    }
    values.update(overrides)
    return RunState(**values)


@dataclass
class _Session:
    """一次作答相位会话（剧本化 completer ＋ per-run 总线）。"""

    bus: EventBus
    completer: ScriptedCompleter
    supplements: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def _phase(*replies: str) -> Any:
    """剧本化 completer（同面替身，离线零触网）＋ per-run 总线。"""
    completer = ScriptedCompleter({_MODEL_CALLER: list(replies)})
    previous = set_completer(completer)
    try:
        yield _Session(bus=EventBus(), completer=completer)
    finally:
        set_completer(previous)


def _call(state: RunState, session: _Session) -> Any:
    from appv2.runtimev2.answering import answer

    return answer(state, bus=session.bus, supplements=session.supplements)


def _draft_payloads(state: RunState) -> list[dict[str, Any]]:
    """起草步 payload（按 `phase == "draft"` 筛——模型调用步无该键，天然排除）。"""
    found: list[dict[str, Any]] = []
    for step in state.steps:
        payload = step.get("payload")
        if isinstance(payload, Mapping) and payload.get("phase") == "draft":
            found.append(dict(payload))
    return found


def _user_message(state: RunState) -> str:
    """最后一条 user 消息的**动态段**（V2-134：规章段并入同条 ⇒ 剥去规章前缀；覆盖表落动态段）。"""
    users = [row for row in state.messages if row.get("role") == "user"]
    assert users, "作答轮 user 消息缺席"
    content = str(users[-1]["content"])
    return content.replace(answer_system_contract(), "", 1).lstrip("\n")


def _line_for(subtask_id: str) -> str:
    return ANSWER_COVERAGE_LINE.format(id=subtask_id)


# ---------- 1 检测（程序、零语义）：两形零支撑 ＋ 分层判据 ----------


def test_subtask_coverage_nq_m8_shape_zero_support() -> None:
    """`NQ-M8` 形：题眼 `Y-41` 在 34-5 窗口零命中 ⇒ 零支撑；数字记号 `41` 的窗内全等命中不得顶替。

    归因 §S2：`NQ-M8` 真答案窗 `Y-39`／`Y-41`／`2027-01-06` 零命中，窗内均为 34-5 月报
    （模型以 `W-41` 顶替）。**分层判据是本票判据本体**：`41`（「第 41 根」）在窗内 `W-41` 上
    全等命中（全等边界字符集不含连字符），若不以强锚层定论即误判「有支撑」。
    """
    window_rows = _window_34_5()
    subtasks = [{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}]
    assert subtask_coverage(subtasks, _render(window_rows), subjects=("Y-41",)) == {"s1": False}
    # 分层面（反证）：强锚缺席但数字面命中 ⇒ 无强锚时才由数字锚定论
    assert subtask_coverage(subtasks, _render(window_rows)) == {"s1": True}
    assert num_token_hit(_render(window_rows), "41") is True


def test_subtask_coverage_b_zheng6_shape_zero_support() -> None:
    """`B-正6` 形：34-8 侧子问题在「只有 34-5 月报」的窗内零支撑；正源窗内＝有支撑。

    跨形面：题面「渤中34-8 油田」（名字与「油田」间有空格）与 `state.subjects` 的归一形
    「渤中34-8油田」不同形——两侧同规＝`normalize_anchor_text`（核验归属审同规）。
    """
    window_34_5 = _render(_window_34_5())
    window_34_8 = _render(_window_34_8())
    subtasks = [
        {"id": "s1", "question": _B_ZHENG6_SUBTASK, "status": "ok"},
        {"id": "s2", "question": _B_ZHENG6_SUBTASK_34_5, "status": "ok"},
    ]
    subjects = ("渤中34-8油田", "渤中34-5油田")
    terms = ("平均检泵周期",)
    assert subtask_coverage(
        subtasks, window_34_5, subjects=subjects, terms=terms
    ) == {"s1": False, "s2": True}
    assert subtask_coverage(
        subtasks, window_34_8, subjects=subjects, terms=terms
    ) == {"s1": True, "s2": False}


def test_subtask_coverage_no_tokens_no_false_positive() -> None:
    """零记号子问题／空子问题列＝「有支撑」（无据可判＝不提示——零误报面）。"""
    assert subtask_coverage([], "任何窗口") == {}
    assert subtask_coverage([{"id": "s1", "question": ""}], "窗口") == {"s1": True}
    assert subtask_coverage([{"id": "", "question": "有题无号"}], "窗口") == {}


# ---------- 2 端到端：两形提示行在场 ＋ payload 机读键 ----------


async def test_answer_nq_m8_shape_prompt_line_and_payload() -> None:
    """`NQ-M8` 形离线复现：作答上下文出现提示行，且 payload 有 `subtask_coverage`。"""
    state = _state(
        question=_NQ_M8_QUESTION,
        subjects=("Y-41",),
        observations=_window_34_5(),
        subtask_results=[{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}],
    )
    with _phase("W-41 井 2026 年 8 月完成检泵作业[1]。") as session:
        _call(state, session)
    message = _user_message(state)
    assert _COVERAGE_HEAD in message
    assert _line_for("s1") in message
    payload = _draft_payloads(state)[0]
    assert payload[PAYLOAD_SUBTASK_COVERAGE_KEY] == {"s1": False}


async def test_answer_b_zheng6_shape_prompt_line_and_payload() -> None:
    """`B-正6` 形离线复现：34-8 侧零支撑子问题出提示行；34-5 侧（有支撑）不出行。"""
    state = _state(
        question="近三年 8 月平均检泵周期的变化趋势？",
        subjects=("渤中34-8油田", "渤中34-5油田"),
        terms=("平均检泵周期",),
        observations=_window_34_5(),
        subtask_results=[
            {"id": "s1", "question": _B_ZHENG6_SUBTASK, "status": "ok"},
            {"id": "s2", "question": _B_ZHENG6_SUBTASK_34_5, "status": "ok"},
        ],
    )
    with _phase("34-5 油田近三年 8 月平均检泵周期 386→415→428 天[2]。") as session:
        _call(state, session)
    message = _user_message(state)
    assert _line_for("s1") in message
    assert _line_for("s2") not in message
    payload = _draft_payloads(state)[0]
    assert payload[PAYLOAD_SUBTASK_COVERAGE_KEY] == {"s1": False, "s2": True}


async def test_answer_sufficient_material_no_line() -> None:
    """材料充分题**零提示**（验收②零误报）：覆盖表段整段缺席、payload 全 True。"""
    state = _state(
        question="渤中34-8 油田 2027-01 平均检泵周期？",
        subjects=("渤中34-8油田",),
        terms=("平均检泵周期",),
        observations=_window_34_8(),
        subtask_results=[{"id": "s1", "question": _B_ZHENG6_SUBTASK, "status": "ok"}],
    )
    with _phase("Y-41 井平均检泵周期 396 天[1]。") as session:
        _call(state, session)
    message = _user_message(state)
    assert _COVERAGE_HEAD not in message
    assert "无支撑" not in message
    payload = _draft_payloads(state)[0]
    assert payload[PAYLOAD_SUBTASK_COVERAGE_KEY] == {"s1": True}


# ---------- 3 段位与不改面（验收③：不改材料、不替模型决定） ----------


async def test_answer_coverage_section_placement_before_materials() -> None:
    """覆盖表落 user 动态段：**清单后、材料前**（Kimi 评审修正 3——与 V2-120「第一步·先核」
    逐字对齐）。"""
    state = _state(
        question=_NQ_M8_QUESTION,
        subjects=("Y-41",),
        observations=_window_34_5(),
        subtask_results=[{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}],
    )
    with _phase("照材料作答[1]。") as session:
        _call(state, session)
    message = _user_message(state)
    assert message.index(_SUBTASK_LIST_HEAD) < message.index(_COVERAGE_HEAD)
    assert message.index(_COVERAGE_HEAD) < message.index(_MATERIALS_HEAD)
    assert message.index(_line_for("s1")) < message.index(_MATERIALS_HEAD)


async def test_answer_coverage_does_not_change_materials_or_explore_decision() -> None:
    """提示行**不改材料**（材料段与 `render_materials` 产物逐字相等）、**不替模型决定** explore。

    模型自决面：零支撑在场时模型给正常作答 ⇒ 意图仍 `verify`（程序零 explore 决策）；模型给
    `explore` 形 ⇒ 照既有第二出口走 `explore`（V2-96——覆盖信号不改判据）。
    """
    from appv2.runtimev2.context import render_materials

    observations = _window_34_5()
    state = _state(
        question=_NQ_M8_QUESTION,
        subjects=("Y-41",),
        observations=observations,
        subtask_results=[{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}],
    )
    materials_text, _meta = render_materials(observations, max_observations=24)
    with _phase("照材料作答[1]。") as session:
        _call(state, session)
    assert materials_text in _user_message(state)
    assert state.next_intent == INTENT_VERIFY

    explore_reply = (
        '{"action":"explore","reason":"缺 34-8 侧近三年数据",'
        '"requests":[{"tool":"doc_retrieve","query":"渤中34-8 近三年 平均检泵周期"}]}'
    )
    state2 = _state(
        question=_NQ_M8_QUESTION,
        subjects=("Y-41",),
        observations=observations,
        subtask_results=[{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}],
    )
    with _phase(explore_reply) as session:
        _call(state2, session)
    assert state2.next_intent == INTENT_EXPLORE
    assert state2.pending_explore is not None


async def test_answer_coverage_recomputed_after_window_grows() -> None:
    """覆盖信号随窗**重算**（非冻结）：再探并入正源材料后，同一子问题翻为有支撑、提示行消失。"""
    state = _state(
        question=_NQ_M8_QUESTION,
        subjects=("Y-41",),
        observations=_window_34_5(),
        subtask_results=[{"id": "s1", "question": _NQ_M8_QUESTION, "status": "ok"}],
    )
    explore_reply = (
        '{"action":"explore","reason":"缺 34-8 侧正源材料",'
        '"requests":[{"tool":"doc_retrieve","query":"Y-41 井 检泵周期"}]}'
    )
    with _phase(explore_reply) as session:
        _call(state, session)
    assert _draft_payloads(state)[0][PAYLOAD_SUBTASK_COVERAGE_KEY] == {"s1": False}

    # 再探并入正源材料（新观察续排 `[n]`）→ 重入起草段：覆盖表按**新窗**重算
    grown = _window_34_8() + _window_34_5()
    for position, row in enumerate(grown, start=1):
        row["index"] = position
    state.observations = grown
    state.pending_explore = None
    with _phase("Y-41 井 2027-01-06 泵效 52%[1]。") as session:
        _call(state, session)
    assert "无支撑" not in _user_message(state)
    assert _draft_payloads(state)[-1][PAYLOAD_SUBTASK_COVERAGE_KEY] == {"s1": True}


async def test_answer_coverage_payload_present_without_subtasks() -> None:
    """additive 键恒在场（无子问题＝空表）；无子问题＝零提示行（不空转出段头）。"""
    state = _state(question="照材料作答？", observations=_window_34_5())
    with _phase("照材料作答[1]。") as session:
        _call(state, session)
    payload = _draft_payloads(state)[0]
    assert payload[PAYLOAD_SUBTASK_COVERAGE_KEY] == {}
    assert _COVERAGE_HEAD not in _user_message(state)


def _render(observations: list[dict[str, Any]]) -> str:
    """渲染窗文本（`context.render_materials` 产物——检测判据面＝模型实见窗）。"""
    from appv2.runtimev2.context import render_materials

    text, _meta = render_materials(observations, max_observations=24)
    return text


# ---------- 4 常量单点（Kimi 评审修正 1／2） ----------


def test_answer_coverage_line_verbatim_and_single_source() -> None:
    """提示行逐字（票面 §施工基准）＋`ANSWER_COVERAGE_*` 单点命名（runtimev2 面恰一处字面定义）。

    **Kimi 评审修正 1** 的「禁两套常量名」面：段头与提示行两件都落 `prompts.answer_round`
    （动态段渲染面——先例 `_QUESTION_ANCHOR`〔携槽〕／`_SUBTASK_LIST_HEAD`〔段头〕），全仓各恰
    一处定义、零 `COVERAGE_LINE` 别名（机读面＝本测试）。**偏离登记**：两件**不入**
    `CONTRACT_CONSTANT_FAMILIES` 族并集——①族单源判据要求成员首行 ≥12 字（段头 7 字不可入族）；
    ②pin-24 要求合同常量无槽（本行携 `{id}` 槽）——两件同属动态段文本，非合同文本。
    """
    assert ANSWER_COVERAGE_LINE == (
        "子问题 {id} 在本次材料中无支撑：可 explore 补充检索，或如实说明未覆盖。"
    )
    assert ANSWER_COVERAGE_HEAD == "子问题覆盖表："
    assert "ANSWER_COVERAGE_LINE" not in CONTRACT_CONSTANT_FAMILIES["answer_draft"]
    assert "COVERAGE_LINE" not in vars(answering_constants)
    # 单源：runtimev2 面内恰一处字面定义（消费方零字面副本）
    feature = "子问题 {id} 在本次材料中无支撑"
    holders = sorted(
        path.name
        for path in _RUNTIMEV2_DIR.rglob("*.py")
        if feature in path.read_text(encoding="utf-8")
    )
    assert holders == ["answer_round.py"], f"提示行模板出现多处以字面定义：{holders}"
    # 段头单点（动态段段头族——同「子问题结果清单：」先例）
    assert answer_coverage_section({}) == ""
    assert answer_coverage_section({"s1": True}) == ""
    assert answer_coverage_section({"s1": False}) == _COVERAGE_HEAD + "\n" + _line_for("s1")
    assert assemble_answer_prompt(_state()) == assemble_answer_prompt(_state(), coverage={})


def test_answer_coverage_payload_key_single_source() -> None:
    """`subtask_coverage` 键名单点＝`answering.constants`（additive——无子问题时亦在场）。"""
    assert PAYLOAD_SUBTASK_COVERAGE_KEY == "subtask_coverage"
    assert (
        answering_constants.PAYLOAD_SUBTASK_COVERAGE_KEY == PAYLOAD_SUBTASK_COVERAGE_KEY
    )
