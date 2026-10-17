"""parsing 块验收（RT-W2-05a：骨架＋三面解析器族核心簇＋本块 pin 相关两行）。

票面对象＝`specs/parsing.md`「验收测试」表第 **1–13** 行（-05a 逐字，用例标识与规格列逐字一致、
`#` 保留规格表行序）；本件同时落「测试网钉」pin-06 **器材面**用例（规格表第 20／21 行的指纹四件
——-05a「织网义务」节第②条落网点；pin-06 行为面在 `specs/execution.md` 行为 13，本块零触发面）。

pin-04（发射 JSON 不进答案面）／pin-13（起草回声=0）经逐条核实**不落本块**——本件不设第三面
对账，反向保证＝行 1–3（理解面严格解析，旧降级通道零可达）。

拒因文本真源＝迁移前 `appv2/runtime/subtask.py`（L179-L290 澄清面／L318-L375 匹配面／L82-L110
带定位）；`args` 非对象拒文＝`appv2/runtime/graph.py` L616 字面。规格表第 14–19、22–28 行
（拒因逐字 golden／带定位／提取单点／引号自修／载荷定型类两行／共用件单点／数字单点／三条元面／
边界集／保留集）＝**已由 `RT-W2-05b-parsing.md` 落地**（规格表第 14–19／22–28 行，本件下半段）。
第 20／21 行（pin-06 器材面两式）已按 -05a 票面「验收」第二条＋「织网义务」第②条在本件落名并
全绿——-05b 只复核在场、**未对同一标识再定义一次**（两处同名用例＝两处真源漂移）。
"""

from __future__ import annotations

import ast
import inspect
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from appv2.runtimev2 import parsing
from appv2.runtimev2.parsing import (
    BUDGET_REJECT_MARK,
    CHAIN_DATA,
    CHAIN_KINDS,
    CHAIN_KNOWLEDGE,
    CLARIFY_ACTIONS,
    CLARIFY_DISCOVER,
    CLARIFY_FINALIZE,
    ROUTE_DIRECT,
    ROUTE_FULL,
    ClarifyEmission,
    Direct,
    QuestionGroup,
    Subtask,
    SubtaskMatch,
    Understanding,
    discover_fingerprint,
    emission_fingerprints,
    extract_plan_json,
    is_same_param_replay,
    json_syntax_feedback,
    parse_question_group,
    parse_tool_match,
    parse_understanding,
    parse_with_quote_repair,
    payload_fingerprint,
    repair_inner_quotes,
    understanding_schema_feedback,
)

_MAX_DISCOVERS = 2
_MAX_SUBTASKS = 4  # 数值真源＝walk/09 §七 Q-C／eng/00 F-14「子问题 ≤4」（state 承载键待落定）
_ACTION_SCOPE = "/".join(sorted(CLARIFY_ACTIONS))


def _emit(
    payload: dict[str, Any],
    *,
    max_discovers: int = _MAX_DISCOVERS,
    max_subtasks: int = _MAX_SUBTASKS,
    discover_budget_left: int | None = None,
) -> ClarifyEmission | str:
    """澄清面发射解析（注入制限额参数——签名无裸默认值，用例侧自带真源值）。"""
    return parse_question_group(
        json.dumps(payload, ensure_ascii=False),
        max_discovers=max_discovers,
        discover_budget_left=discover_budget_left,
        max_subtasks=max_subtasks,
    )


def _decompose(*subtasks: dict[str, Any]) -> dict[str, Any]:
    return {"action": "decompose", "question_group": {"subtasks": list(subtasks)}}


def _subtask(subtask_id: str, **overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": subtask_id,
        "question": f"问 {subtask_id}",
        "ledger_notes": f"注 {subtask_id}",
    }
    item.update(overrides)
    return item


def _match(subtask_id: str, **overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": subtask_id,
        "chain": CHAIN_DATA,
        "tool": "data_query",
        "plan": {"metric_slot": "日产油量"},
    }
    item.update(overrides)
    return item


def _group(*ids: str) -> QuestionGroup:
    return QuestionGroup(
        subtasks=tuple(
            Subtask(id=item, question=f"问 {item}", ledger_notes=f"注 {item}") for item in ids
        )
    )


def _match_text(*matches: dict[str, Any]) -> str:
    return json.dumps({"matches": list(matches)}, ensure_ascii=False)


def _emission_of(payload: dict[str, Any], **kwargs: Any) -> ClarifyEmission:
    emission = _emit(payload, **kwargs)
    assert isinstance(emission, ClarifyEmission), emission
    return emission


# ── 行 1–3：理解面（统一 JSON 严格解析，V2 定案）────────────────────────────────


def test_understanding_json_two_forms() -> None:
    """行 1｜合法 JSON 两形落对，互斥单出口（`specs/parsing.md` 行为 1）。"""
    full_text = json.dumps(
        {
            "route": "full",
            "text": "渤海油田日产油量怎么算",
            "metric_candidates": ["日产油量", "含水率"],
        },
        ensure_ascii=False,
    )
    full = parse_understanding(full_text)
    assert isinstance(full, Understanding)
    assert not isinstance(full, Direct)
    assert full.route == ROUTE_FULL
    assert full.text == "渤海油田日产油量怎么算"
    assert full.metric_candidates == ["日产油量", "含水率"]

    direct_text = json.dumps({"route": "direct", "text": "谢谢，再见"}, ensure_ascii=False)
    direct = parse_understanding(direct_text)
    assert isinstance(direct, Direct)
    assert not isinstance(direct, Understanding)
    assert direct.route == ROUTE_DIRECT
    assert direct.text == "谢谢，再见"
    assert not hasattr(direct, "metric_candidates")  # 两形字段集不互相冒充


def test_understanding_malformed_none_no_fallback() -> None:
    """行 2｜缺必填字段／类型不符／`route` 越界 → `None`（不猜、不取默认、不降级）。"""
    samples = [
        json.dumps({"text": "缺 route"}, ensure_ascii=False),
        json.dumps({"route": "unset", "text": "route 越界"}, ensure_ascii=False),
        json.dumps({"route": "full", "metric_candidates": ["日产油量"]}, ensure_ascii=False),
        json.dumps({"route": "direct"}),
        json.dumps({"route": "full", "text": 42, "metric_candidates": []}),
        json.dumps({"route": "direct", "text": ["列表不是文本"]}, ensure_ascii=False),
        json.dumps({"route": "full", "text": "缺候选键"}),  # 不取默认空表
        json.dumps({"route": "full", "text": "候选形错", "metric_candidates": "日产油量"}),
        json.dumps({"route": "full", "text": "候选项类型不符", "metric_candidates": [1, 2]}),
        "不是 JSON",
        "[1, 2]",
    ]
    for sample in samples:
        assert parse_understanding(sample) is None, sample


def test_understanding_two_line_retired() -> None:
    """行 3｜两行式与「直接回答：」通道样本不再受理（旧降级提取零可达）。"""
    assert parse_understanding("理解：渤海油田日产油量\n指标候选：日产油量、含水率") is None
    assert parse_understanding("直接回答：你好，我是采油助手") is None
    assert parse_understanding('先说明\n{"route": "direct", "text": "散文包裹产"}') is None
    assert parse_understanding('```json\n{"route": "direct", "text": "围栏产"}\n```') is None


def test_understanding_schema_feedback_reasons() -> None:
    """行 3 补（2026-10-16 补·流水 67）｜理解面拒因诊断面逐支落对＋与解析面同判（共用内核）。

    逐支：非合法 JSON／顶层非对象／缺必填字段（`route`／`text`／`metric_candidates`）／类型不符
    （`text`／`metric_candidates` 两形／候选元素）／`route` 越界（含大小写变形——闭世界严判）；
    **合格 → 空串**（无病不产拒因）；**同判不漂移**：全样本上「`parse_understanding` 返 `None`
    ↔ 拒因非空」恒等价（两形读同一判据序——禁手写替代纪律的机检面）。
    """
    # 逐支拒因（字面＝本块机器拒因原文；违规即红）
    route_out_of_world = "`route` 取值越界（闭世界仅「full」｜「direct」）"
    cases: tuple[tuple[str, str], ...] = (
        ("不是 JSON", "应答不是合法 JSON"),
        ("[1, 2]", "应答顶层不是 JSON 对象"),
        (json.dumps({"text": "缺 route"}, ensure_ascii=False), "缺必填字段 `route`"),
        (json.dumps({"route": "full", "text": "x"}), "缺必填字段 `metric_candidates`"),
        (json.dumps({"route": "direct"}), "缺必填字段 `text`"),
        (json.dumps({"route": "full", "text": 42, "metric_candidates": []}),
         "字段类型不符：`text` 须为字符串"),
        (json.dumps({"route": "full", "text": "x", "metric_candidates": "日产油量"}),
         "字段类型不符：`metric_candidates` 须为字符串数组"),
        (json.dumps({"route": "full", "text": "x", "metric_candidates": [1, 2]}),
         "字段类型不符：`metric_candidates` 的元素须为字符串"),
        (json.dumps({"route": "unset", "text": "x"}), route_out_of_world),
        (json.dumps({"route": "FULL", "text": "x"}), route_out_of_world),
        (json.dumps({"route": None, "text": "x"}), route_out_of_world),
    )
    for sample, expected in cases:
        assert understanding_schema_feedback(sample) == expected, sample
        assert parse_understanding(sample) is None, sample

    # 合格形 → 空串（无病不产拒因）；两形互斥单出口照旧
    for sample in (
        json.dumps({"route": "full", "text": "问日产油量", "metric_candidates": ["日产油量"]},
                   ensure_ascii=False),
        json.dumps({"route": "full", "text": "判断题", "metric_candidates": []},
                   ensure_ascii=False),
        json.dumps({"route": "direct", "text": "不客气"}, ensure_ascii=False),
    ):
        assert understanding_schema_feedback(sample) == "", sample
        assert parse_understanding(sample) is not None, sample

    # 同判不漂移（共用判定内核）：全样本闭世界对照——两形必同一条判据序
    samples = [*[sample for sample, _ in cases], *[
        json.dumps({"route": "full", "text": "问", "metric_candidates": ["日产油量"]},
                   ensure_ascii=False),
        json.dumps({"route": "direct", "text": "谢谢"}),
        "理解：两行式\n指标候选：日产油量",
        "",
    ]]
    for sample in samples:
        assert (parse_understanding(sample) is None) == bool(
            understanding_schema_feedback(sample)
        ), sample

    # 拒因恒非空串（不合格形不说空话——回喂载荷的【拒因】段不得空转）
    for sample, _expected in cases:
        assert understanding_schema_feedback(sample)


# ── 行 4–11：澄清面（四动作闭世界＋分派）────────────────────────────────────────


def test_clarify_actions_closed_world() -> None:
    """行 4｜四动作闭世界各形落对（`specs/parsing.md` 行为 2）。"""
    discover = _emission_of(
        {
            "action": "discover",
            "discovers": [{"tool": "台账查询", "args": {"oilfield": "BZ"}}],
            "thought": "先看台账",
        }
    )
    assert discover.kind == CLARIFY_DISCOVER
    assert discover.discovers == ({"tool": "台账查询", "args": {"oilfield": "BZ"}},)
    assert discover.thought == "先看台账"

    decompose = _emission_of(_decompose(_subtask("s1")))
    assert decompose.kind == "decompose"
    assert isinstance(decompose.group, QuestionGroup)
    assert [item.id for item in decompose.group.subtasks] == ["s1"]

    ask = _emission_of(
        {
            "action": "ask",
            "ask": {"prompt": "先看哪个油田？", "options": ["BZ", "QHD"]},
            "note": "口径未定",
        }
    )
    assert ask.kind == "ask"
    assert ask.ask_prompt == "先看哪个油田？"
    assert ask.ask_options == ("BZ", "QHD")
    assert ask.note == "口径未定"
    assert ask.as_payload()["ask"] == {"prompt": "先看哪个油田？", "options": ["BZ", "QHD"]}

    finalize = _emission_of({"action": "finalize", "thought": "材料足够", "未知键": "静默忽略"})
    assert finalize.kind == CLARIFY_FINALIZE
    assert finalize.as_payload() == {"action": "finalize", "thought": "材料足够"}

    assert CLARIFY_ACTIONS == frozenset({"discover", "decompose", "ask", "finalize"})
    assert CHAIN_KINDS == frozenset({CHAIN_DATA, CHAIN_KNOWLEDGE})


def test_clarify_action_out_of_range_rejected() -> None:
    """行 5｜`action` 越界／缺失 → 拒因正文（原文逐字）。"""
    assert (
        _emit({"action": "summarize"}) == f"action 缺失或越界（{_ACTION_SCOPE} 四值）：'summarize'"
    )
    assert _emit({"thought": "忘了写 action"}) == (
        f"action 缺失或越界（{_ACTION_SCOPE} 四值）：None"
    )
    # 不可哈希形＝拒（V1 裸抛 TypeError 已收口为三态返回——差异点②）
    assert _emit({"action": {"name": "decompose"}}) == (
        f"action 缺失或越界（{_ACTION_SCOPE} 四值）：{{'name': 'decompose'}}"
    )
    assert (
        _emit({"action": ["discover"]})
        == f"action 缺失或越界（{_ACTION_SCOPE} 四值）：['discover']"
    )


def test_question_group_schema_rejections() -> None:
    """行 6｜支条数上限／支非对象／缺 `question`／`id` 重复 → 逐条拒。"""
    at_limit = _emission_of(_decompose(*(_subtask(f"s{i}") for i in range(_MAX_SUBTASKS))))
    assert len(at_limit.group.subtasks) == _MAX_SUBTASKS  # type: ignore[union-attr]
    over_limit = _emit(_decompose(*(_subtask(f"s{i}") for i in range(_MAX_SUBTASKS + 1))))
    assert over_limit == f"subtasks 超出上限（≤{_MAX_SUBTASKS} 个——Owner 认可值）"

    assert _emit(_decompose(_subtask("s1"), "s2")) == (
        "subtasks 支须为对象（{id/question/ledger_notes/...}）"
    )
    assert _emit(_decompose({"question": "问", "ledger_notes": "注"})) == (
        "subtasks 支缺 id（组内唯一标识）"
    )
    assert _emit(_decompose(_subtask("s1"), _subtask("s1"))) == "subtasks id 重复：'s1'"
    assert _emit(_decompose(_subtask("s1", question="   "))) == (
        "subtasks s1 缺 question（子问题原文）"
    )
    assert _emit({"action": "decompose"}) == "decompose 缺 question_group 对象"
    assert _emit({"action": "decompose", "question_group": {}}) == (
        "question_group 缺 subtasks（非空数组）"
    )
    assert _emit({"action": "decompose", "question_group": {"subtasks": []}}) == (
        "question_group 缺 subtasks（非空数组）"
    )


def test_ledger_notes_required() -> None:
    """行 7｜缺 `ledger_notes` → 拒（台账注释必带机检点）。"""
    expected = (
        "subtasks s1 缺 ledger_notes（台账注释必带——从词典层逐字转抄："
        "〈精确指标 slot 名〉〈绑定态〉〈锚定窗〉）"
    )
    bare = {"id": "s1", "question": "问 s1"}  # 缺键形
    assert _emit(_decompose(bare)) == expected
    for overrides in ({"ledger_notes": ""}, {"ledger_notes": "  "}, {"ledger_notes": None}):
        assert _emit(_decompose(_subtask("s1", **overrides))) == expected
    assert _emission_of(_decompose(_subtask("s1"))).group is not None


def test_question_group_chain_closed_world() -> None:
    """行 8｜`chain` 非空越界 → 拒；支内 `tool` 键＝未知键静默丢弃；本层不做链-工具一致性。"""
    assert _emit(_decompose(_subtask("s1", chain="stat"))) == (
        "subtasks s1 chain 越界（data/knowledge）：'stat'"
    )
    for chain in (CHAIN_DATA, CHAIN_KNOWLEDGE, ""):
        emission = _emission_of(_decompose(_subtask("s1", chain=chain)))
        assert emission.group is not None
        assert emission.group.subtasks[0].chain == chain

    # `tool` 键＝未知键静默丢弃（Owner 裁决 #10：tool 归匹配相位产出）
    dropped = _emission_of(_decompose(_subtask("s1", chain=CHAIN_DATA, tool="doc_retrieve")))
    assert dropped.group is not None
    subtask = dropped.group.subtasks[0]
    assert not hasattr(subtask, "tool")
    assert "tool" not in subtask.as_payload()

    # 本层不做链-工具一致性：data 链配 doc_retrieve 照样受理（一致性闸在匹配面）
    assert isinstance(
        _emit(_decompose(_subtask("s1", chain=CHAIN_DATA, tool="doc_retrieve"))), ClarifyEmission
    )
    assert isinstance(_emit(_decompose(_subtask("s1", chain=CHAIN_KNOWLEDGE))), ClarifyEmission)


def test_discover_shape_and_budget_rejections() -> None:
    """行 9｜非空数组／单次上限／全 run 预算（前缀「发现预算」）／支缺 `tool`／
    `args` 非对象 → 逐条拒。"""
    assert _emit({"action": "discover"}) == "action=discover 缺 discovers（非空数组）"
    assert _emit({"action": "discover", "discovers": []}) == (
        "action=discover 缺 discovers（非空数组）"
    )
    over_limit = _emit(
        {"action": "discover", "discovers": [{"tool": "t1"}, {"tool": "t2"}, {"tool": "t3"}]}
    )
    assert over_limit == f"discovers 超出单次上限（≤{_MAX_DISCOVERS} 支）"

    budget = _emit(
        {"action": "discover", "discovers": [{"tool": "t1"}, {"tool": "t2"}]},
        discover_budget_left=1,
    )
    assert isinstance(budget, str)
    assert budget.startswith(BUDGET_REJECT_MARK)  # 机读甄别面恰一值
    assert budget == (
        f"{BUDGET_REJECT_MARK}已尽（全 run ≤10，剩余 1 支）——台账全量已在上下文，"
        "禁止继续敲门：产出 decompose 问题组或 ask 反问"
    )
    assert isinstance(
        _emit(
            {"action": "discover", "discovers": [{"tool": "t1"}, {"tool": "t2"}]},
            discover_budget_left=2,
        ),
        ClarifyEmission,
    )

    assert _emit({"action": "discover", "discovers": [{"args": {}}]}) == (
        "discovers 支缺 tool（{'tool': 名, 'args': {...}}）"
    )
    assert _emit({"action": "discover", "discovers": [{"tool": "台账查询", "args": "油井"}]}) == (
        "发现工具 台账查询 的 args 须为对象"
    )
    assert _emit({"action": "discover", "discovers": [{"tool": "台账查询", "args": ["油井"]}]}) == (
        "发现工具 台账查询 的 args 须为对象"
    )
    for falsy in ({}, [], "", 0, None):  # 假值归一空对象（V1 事实面——非对象仅真值形拒）
        assert _emission_of(
            {"action": "discover", "discovers": [{"tool": "台账查询", "args": falsy}]}
        ).discovers == ({"tool": "台账查询", "args": {}},)

    defaulted = _emission_of({"action": "discover", "discovers": [{"tool": "台账查询"}]})
    assert defaulted.discovers == ({"tool": "台账查询", "args": {}},)


def test_ask_shape_rejections() -> None:
    """行 10｜缺 `ask` 对象／`prompt` 空／`options` 个数越界 → 拒；重复选项照样过。"""
    boundary = "ask 缺 options 或个数越界（2~4 个选项）"
    assert _emit({"action": "ask"}) == "action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）"
    assert _emit({"action": "ask", "ask": "不是对象"}) == (
        "action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）"
    )
    assert _emit({"action": "ask", "ask": {}}) == "ask 缺 prompt（问用户什么必填）"
    assert _emit({"action": "ask", "ask": {"prompt": "   ", "options": ["BZ", "QHD"]}}) == (
        "ask 缺 prompt（问用户什么必填）"
    )
    assert (
        _emit({"action": "ask", "ask": {"prompt": "先看哪个？", "options": "BZ/QHD"}}) == boundary
    )
    assert _emit({"action": "ask", "ask": {"prompt": "先看哪个？", "options": None}}) == boundary
    assert (
        _emit({"action": "ask", "ask": {"prompt": "先看哪个？", "options": ["只有一个"]}})
        == boundary
    )
    assert (
        _emit(
            {"action": "ask", "ask": {"prompt": "先看哪个？", "options": ["A", "B", "C", "D", "E"]}}
        )
        == boundary
    )

    repeated = _emission_of(
        {"action": "ask", "ask": {"prompt": "先看哪个？", "options": ["BZ", "BZ", " QHD ", "  "]}}
    )
    assert repeated.ask_options == ("BZ", "BZ", "QHD")  # 不去重；空白项丢弃


def test_finalize_passthrough() -> None:
    """行 11｜`finalize` 支零载荷直通（不读载荷）。"""
    emission = _emission_of(
        {
            "action": "finalize",
            "question_group": "垃圾载荷",
            "discovers": "垃圾载荷",
            "ask": 42,
            "thought": "材料足够",
            "note": "辅助材料够用",
        }
    )
    assert emission.kind == CLARIFY_FINALIZE
    assert emission.group is None
    assert emission.discovers == ()
    assert emission.ask_prompt == ""
    assert emission.ask_options == ()
    assert emission.as_payload() == {
        "action": "finalize",
        "thought": "材料足够",
        "note": "辅助材料够用",
    }


# ── 行 12–13：匹配面（闭合世界对账）────────────────────────────────────────────


def test_matches_exactly_one_per_subtask() -> None:
    """行 12｜恰配一条全过 → tuple（顺序＝发射顺序）；缺／多／未知／重复 id → 逐条拒。"""
    group = _group("s1", "s2")
    matches = parse_tool_match(
        _match_text(
            _match(
                "s2",
                chain=CHAIN_KNOWLEDGE,
                tool="doc_retrieve",
                plan=None,
                retrieval_need={"question": "检索 s2"},
            ),
            _match("s1"),
        ),
        group,
    )
    assert isinstance(matches, tuple)
    assert all(isinstance(item, SubtaskMatch) for item in matches)
    assert [item.id for item in matches] == ["s2", "s1"]  # 顺序＝发射顺序，不回排组序

    assert parse_tool_match(_match_text(_match("s1")), group) == (
        "matches 覆盖缺口（组内子问题缺匹配：['s2']）——每子问题恰一条"
    )
    assert parse_tool_match(_match_text(_match("s1"), _match("s2"), _match("s9")), group) == (
        "matches id 's9' 不在问题组内（闭合世界：['s1', 's2']）"
    )
    assert parse_tool_match(_match_text(_match("s1"), _match("s1")), group) == (
        "matches id 重复：'s1'（每子问题恰一条匹配）"
    )
    assert parse_tool_match(json.dumps({}), group) == "缺 matches（非空数组——组内每个子问题恰一条）"
    assert parse_tool_match(json.dumps({"matches": []}), group) == (
        "缺 matches（非空数组——组内每个子问题恰一条）"
    )
    assert parse_tool_match(json.dumps({"matches": ["s1"]}), group) == (
        "matches 支须为对象（{id/chain/tool/plan|retrieval_need}）"
    )
    assert parse_tool_match(_match_text({"chain": CHAIN_DATA, "tool": "data_query"}), group) == (
        "matches 支缺 id"
    )


def test_matches_chain_tool_consistency() -> None:
    """行 13｜`chain` 闭世界／chain-tool 一致性／按链必填 → 逐条拒。"""
    group = _group("s1")

    def only(match: dict[str, Any]) -> tuple[SubtaskMatch, ...] | str:
        return parse_tool_match(_match_text(match), group)

    assert only(_match("s1", chain="stat", tool="stat")) == (
        "matches s1 chain 越界（data/knowledge）：'stat'"
    )
    assert only(_match("s1", tool="doc_retrieve")) == (
        "matches s1 chain/tool 不一致（data 链须配 data_query）"
    )
    assert only({"id": "s1", "chain": CHAIN_DATA, "plan": {"metric_slot": "日产油量"}}) == (
        "matches s1 缺 tool"
    )
    assert only({"id": "s1", "chain": CHAIN_DATA, "tool": "data_query"}) == (
        "matches s1 data 链缺 plan（data_query 计划草案对象）"
    )
    assert only(_match("s1", plan={"metric_slot": "   "})) == (
        "matches s1 plan 缺 metric_slot（必填非空）"
    )
    assert only({"id": "s1", "chain": CHAIN_KNOWLEDGE, "tool": "doc_retrieve"}) == (
        "matches s1 knowledge 链缺 retrieval_need（参数对象）"
    )
    assert (
        only(
            {
                "id": "s1",
                "chain": CHAIN_KNOWLEDGE,
                "tool": "doc_retrieve",
                "retrieval_need": {"question": "  "},
            }
        )
        == "matches s1 retrieval_need 缺 question（必填非空）"
    )

    data_ok = only(
        _match("s1", plan={"metric_slot": "日产油量", "ranking": "desc"}, caliber_key=" 场景词 ")
    )
    assert isinstance(data_ok, tuple)
    assert data_ok[0].plan == {"metric_slot": "日产油量", "ranking": "desc"}
    assert data_ok[0].caliber_key == "场景词"  # str().strip() 归一后装载
    assert data_ok[0].retrieval_need is None

    knowledge_ok = only(
        {
            "id": "s1",
            "chain": CHAIN_KNOWLEDGE,
            "tool": "doc_retrieve",
            "retrieval_need": {"question": "检索 s1"},
        }
    )
    assert isinstance(knowledge_ok, tuple)
    assert knowledge_ok[0].retrieval_need == {"question": "检索 s1"}
    assert knowledge_ok[0].plan is None


# ── pin-31 上游面：`mention_mode` 端到端投影（2026-10-16 断供修复）────────────────


def test_matches_mention_mode_loaded_and_projected() -> None:
    """pin-31 上游面｜发射条目带 `mention_mode` 键 → `SubtaskMatch` **原样载入**；缺键＝空串
    缺省；投影（`as_payload`）真值才出键——「提及 vs 执行」结论到得了消费面（端到端上半段）。

    值照抄不判语义、不做归一（parsing 纯解析——闭世界把守归消费面 `preconditions` fail-closed）。
    """
    group = _group("s1", "s2")
    loaded = parse_tool_match(
        _match_text(
            _match("s1", mention_mode="mentioned_only"),
            _match("s2", mention_mode="executed"),
        ),
        group,
    )
    assert isinstance(loaded, tuple)
    assert [item.mention_mode for item in loaded] == ["mentioned_only", "executed"]
    assert [item.as_payload()["mention_mode"] for item in loaded] == [
        "mentioned_only",
        "executed",
    ]  # 投影面：带键（非空）照抄进 state.tool_matches

    # 缺键＝空串缺省（不猜、不取默认——把守归消费面）；投影里空值键不出现
    bare = parse_tool_match(_match_text(_match("s1"), _match("s2")), group)
    assert isinstance(bare, tuple)
    assert [item.mention_mode for item in bare] == ["", ""]
    assert all("mention_mode" not in item.as_payload() for item in bare)

    # 原样载入：值照抄不归一（前后留白照抄——越界值归消费面判，本层零语义）
    padded = parse_tool_match(
        _match_text(_match("s1", mention_mode=" mentioned_only "), _match("s2")), group
    )
    assert isinstance(padded, tuple)
    assert padded[0].mention_mode == " mentioned_only "
    assert padded[0].as_payload()["mention_mode"] == " mentioned_only "


def test_matches_mention_mode_non_string_rejected() -> None:
    """pin-31 上游面｜`mention_mode` 发射值非字符串形 → 拒因正文（枚举越界族句式，逐字照
    `tool_matching` 对账面同款——`specs/tool_matching.md` 拒因六类表「枚举越界」族）。

    只判形（`isinstance(…, str)`）、不判语义——字符串值一律原样装载（含越界值，归消费面拒）。
    """
    group = _group("s1")
    for value in (42, ["executed"], {"mode": "mentioned_only"}, True, None):
        assert parse_tool_match(_match_text(_match("s1", mention_mode=value)), group) == (
            f"matches s1 mention_mode 越界（executed/mentioned_only）：{value!r}"
        )

    # 非字符串拒＝fail-fast 于该支（同支其余字段合规也拒——不静默降级成缺省空串）
    off_world = parse_tool_match(_match_text(_match("s1", mention_mode="maybe")), group)
    assert isinstance(off_world, tuple)
    assert off_world[0].mention_mode == "maybe"  # 字符串越界值照抄（把守归消费面）


# ── pin-06 器材面（规格表第 20／21 行：指纹四件）───────────────────────────────


def test_fingerprints_deterministic_per_branch() -> None:
    """行 20｜指纹器材：两跑同串（确定性）；按支拆算单支单形／两支两值。"""
    plan = {"metric_slot": "日产油量", "ranking": "desc"}
    need = {"question": "检索 s1"}

    assert payload_fingerprint({"b": 1, "a": "渤海"}) == '{"a":"渤海","b":1}'  # 键序归一＋不转义
    assert payload_fingerprint(plan) == payload_fingerprint(
        {"ranking": "desc", "metric_slot": "日产油量"}
    )
    assert payload_fingerprint(plan) == payload_fingerprint(plan)
    assert discover_fingerprint("台账查询", {"oilfield": "BZ"}) == discover_fingerprint(
        "台账查询", {"oilfield": "BZ"}
    )
    assert discover_fingerprint("台账查询", {"oilfield": "BZ"}) == json.dumps(
        {"tool": "台账查询", "args": {"oilfield": "BZ"}}, sort_keys=True, ensure_ascii=False
    )

    plan_only = emission_fingerprints(plan, None)
    need_only = emission_fingerprints(None, need)
    assert plan_only == (payload_fingerprint({"plan": plan, "retrieval_need": None}),)
    assert need_only == (payload_fingerprint({"plan": None, "retrieval_need": need}),)
    assert plan_only != need_only  # 单支单形——整形与实录对齐面
    assert emission_fingerprints(plan, need) == (plan_only[0], need_only[0])  # plan 支在前
    assert emission_fingerprints(None, None) == ()


def test_same_param_replay_three_cases() -> None:
    """行 21｜同参判定三支（全在→拦／新参→放行／零支→放行）。"""
    plan = {"metric_slot": "日产油量"}
    need = {"question": "检索 s1"}
    plan_fingerprint = payload_fingerprint({"plan": plan, "retrieval_need": None})
    need_fingerprint = payload_fingerprint({"plan": None, "retrieval_need": need})

    assert is_same_param_replay(emission_fingerprints(plan, None), [plan_fingerprint]) is True
    assert (
        is_same_param_replay(
            emission_fingerprints({"metric_slot": "含水率"}, None), [plan_fingerprint]
        )
        is False
    )
    assert is_same_param_replay(emission_fingerprints(None, None), [plan_fingerprint]) is False
    assert (
        is_same_param_replay(
            emission_fingerprints(plan, need), [plan_fingerprint, need_fingerprint]
        )
        is True
    )
    assert is_same_param_replay(emission_fingerprints(plan, need), [plan_fingerprint]) is False


# ── 骨架与族名单落位（-05a 验收第三条）────────────────────────────────────────


def test_parsing_family_public_surface() -> None:
    """骨架与族名单落位：三面解析器族＋共用件族四件＋载荷定型类＋指纹器材齐（规格 :39-:80）。"""
    family = (
        "parse_understanding",
        "parse_question_group",
        "parse_tool_match",
        "extract_plan_json",
        "json_syntax_feedback",
        "repair_inner_quotes",
        "parse_with_quote_repair",
        "payload_fingerprint",
        "discover_fingerprint",
        "emission_fingerprints",
        "is_same_param_replay",
        "Understanding",
        "Direct",
        "Subtask",
        "QuestionGroup",
        "ClarifyEmission",
        "SubtaskMatch",
    )
    for name in family:
        assert name in parsing.__all__, name
        assert callable(getattr(parsing, name)), name

    # 返回三态闭世界：定型载荷｜拒因正文（str）｜None；拒因恒非空
    assert parse_understanding("垃圾") is None
    malformed = parse_question_group(
        "垃圾", max_discovers=_MAX_DISCOVERS, max_subtasks=_MAX_SUBTASKS
    )
    assert isinstance(malformed, str) and malformed
    assert isinstance(parse_tool_match("垃圾", _group("s1")), str)
    assert isinstance(
        parse_question_group(
            json.dumps({"action": "finalize"}),
            max_discovers=_MAX_DISCOVERS,
            max_subtasks=_MAX_SUBTASKS,
        ),
        ClarifyEmission,
    )

    # 注入制：限额参数无裸默认值（差异点③）；本块源码零裸上限常量
    signature = inspect.signature(parse_question_group)
    assert signature.parameters["max_discovers"].default is inspect.Parameter.empty
    assert signature.parameters["max_subtasks"].default is inspect.Parameter.empty
    assert signature.parameters["discover_budget_left"].default is None
    assert not hasattr(parsing, "MAX_SUBTASKS_CONTRACT")
    assert not hasattr(parsing, "MAX_DISCOVERS_PER_ROUND")


# ══════════════════════════════════════════════════════════════════════════════
# RT-W2-05b：规格表第 14–19／22–28 行（行 20／21 已在 -05a 落——本件不重定义）
# ══════════════════════════════════════════════════════════════════════════════

_PARSING_DIR = Path(parsing.__file__).parent
_RUNTIMEV2_DIR = _PARSING_DIR.parent
_V1_SUBTASK = Path("appv2/runtime/subtask.py")  # 拒因逐字稿载体（迁移前快照）
_V1_GRAPH = Path("appv2/runtime/graph.py")  # `args` 非对象拒文真源（L616）
_PHASE_DIRS = ("understanding", "clarification", "tool_matching")
_CLARIFY_UNPARSABLE = "澄清发射不可解析——只输出一个 JSON"
_TOOLMATCH_UNPARSABLE = "工具匹配不可解析——只输出一个 JSON"


def _parsing_sources() -> list[tuple[Path, ast.Module]]:
    """parsing 包全部源码树（元面断言的扫描面）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_PARSING_DIR.glob("*.py"))
    ]


def _text_sources(root: Path) -> list[tuple[Path, str]]:
    return [(path, path.read_text(encoding="utf-8")) for path in sorted(root.rglob("*.py"))]


def _runtimev2_sources() -> list[tuple[Path, ast.Module]]:
    """runtimev2 全树源码（形状定义点／共用件单点的全包扫描面）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_RUNTIMEV2_DIR.rglob("*.py"))
    ]


def _spec_class_fields(spec_text: str, class_name: str) -> set[str]:
    """规格接口定义节的类体字段名（`class X:` 行至首个空行——逐行取注解名）。"""
    lines = spec_text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith(f"class {class_name}:")
    )
    fields: set[str] = set()
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            break
        if stripped.startswith("#"):
            continue
        name = stripped.split(":", 1)[0].strip()
        if name.isidentifier():
            fields.add(name)
    return fields


def _feature_files(sources: list[tuple[Path, str]], feature: str) -> list[str]:
    """特征子串命中的文件清单（源码文本级——单点／零副本探测器）。"""
    return [path.as_posix() for path, text in sources if feature in text]


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _class_defs(sources: list[tuple[Path, ast.Module]]) -> dict[str, list[str]]:
    """类定义点清点（形状单点断言——含非 dataclass 形定义）。"""
    found: dict[str, list[str]] = {}
    for path, tree in sources:
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                found.setdefault(node.name, []).append(path.as_posix())
    return found


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表／语义判据探测器（行 24——伪造树可咬）。

    形态处理豁免面＝闭世界成员判定（常量名）／字符串归一／字符扫描（ASCII 结构字符集）；
    载荷 dict 字面量不在判据面（形状投影，非候选词集合）。
    """
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            for item in node.elts:
                if (
                    isinstance(item, ast.Constant)
                    and isinstance(item.value, str)
                    and _has_cjk(item.value)
                ):
                    violations.append(f"L{node.lineno} 字面集合含汉字串（词表形）")
        if isinstance(node, ast.Compare) and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
        ):
            for operand in (node.left, *node.comparators):
                if (
                    isinstance(operand, ast.Constant)
                    and isinstance(operand.value, str)
                    and _has_cjk(operand.value)
                ):
                    violations.append(f"L{node.lineno} 汉字串成员判据")
    return violations


def _bare_limits(tree: ast.Module) -> dict[int, tuple[int, ...]]:
    """与 `len(...)` 同比较的整数字面量（裸上限字面探测器，行 23——伪造树可咬）。"""
    found: dict[int, tuple[int, ...]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        operands = [node.left, *node.comparators]
        if not any(
            isinstance(item, ast.Call)
            and isinstance(item.func, ast.Name)
            and item.func.id == "len"
            for item in operands
        ):
            continue
        ints = tuple(
            item.value
            for item in operands
            if isinstance(item, ast.Constant)
            and isinstance(item.value, int)
            and not isinstance(item.value, bool)
        )
        if ints:
            found[node.lineno] = ints
    return found


def _emit_text(text: str, *, budget: int | None = None) -> ClarifyEmission | str:
    """澄清面解析（原件文本直入——带定位／提取单点／括号失衡形用例面）。"""
    return parse_question_group(
        text,
        max_discovers=_MAX_DISCOVERS,
        discover_budget_left=budget,
        max_subtasks=_MAX_SUBTASKS,
    )


def _frozen(value: Any) -> Any:
    """定型载荷的投影形（两跑逐字相等比对件）。"""
    if isinstance(value, tuple):
        return tuple(_frozen(item) for item in value)
    if hasattr(value, "as_payload"):
        return (type(value).__name__, value.as_payload())
    return value


# ── 行 14：拒因原文逐字迁移（golden＝迁移前 `appv2/runtime/subtask.py` 快照）────


def test_rejection_texts_verbatim_from_v1() -> None:
    """行 14｜拒因原文逐字迁移（golden＝迁移前 `appv2/runtime/subtask.py` 快照逐字比对；
    预算前缀「发现预算」在场）。"""
    v1_source = _V1_SUBTASK.read_text(encoding="utf-8")
    group = _group("s1", "s2")
    cases: list[tuple[str, Any, str, str]] = [
        # （用例，实跑值，golden＝迁移前逐字，骨架＝golden 在 V1 源码中逐字出现的片段）
        (
            "澄清面 fallback＋无花括号提示（L240＋L88-L89）",
            _emit_text("不是 JSON"),
            _CLARIFY_UNPARSABLE + "——输出中没有任何以左花括号起始的 JSON 对象"
            "（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）",
            _CLARIFY_UNPARSABLE,
        ),
        (
            "action 越界（L244）",
            _emit({"action": "summarize"}),
            "action 缺失或越界（ask/decompose/discover/finalize 四值）：'summarize'",
            "action 缺失或越界（",
        ),
        (
            "discover 缺 discovers（L254）",
            _emit({"action": "discover"}),
            "action=discover 缺 discovers（非空数组）",
            "action=discover 缺 discovers（非空数组）",
        ),
        (
            "discovers 超单次上限（L256）",
            _emit({"action": "discover", "discovers": [{"tool": t} for t in ("t1", "t2", "t3")]}),
            "discovers 超出单次上限（≤2 支）",
            "discovers 超出单次上限（≤",
        ),
        (
            "发现预算（L258-L261）",
            _emit(
                {"action": "discover", "discovers": [{"tool": "t1"}, {"tool": "t2"}]},
                discover_budget_left=1,
            ),
            "发现预算已尽（全 run ≤10，剩余 1 支）——台账全量已在上下文，"
            "禁止继续敲门：产出 decompose 问题组或 ask 反问",
            "已尽（全 run ≤10，剩余 ",
        ),
        (
            "discovers 支缺 tool（L265）",
            _emit({"action": "discover", "discovers": [{"args": {}}]}),
            "discovers 支缺 tool（{'tool': 名, 'args': {...}}）",
            "discovers 支缺 tool（{'tool': 名, 'args': {...}}）",
        ),
        (
            "缺 question_group 对象（L182）",
            _emit({"action": "decompose"}),
            "decompose 缺 question_group 对象",
            "decompose 缺 question_group 对象",
        ),
        (
            "question_group 缺 subtasks（L185）",
            _emit({"action": "decompose", "question_group": {"subtasks": []}}),
            "question_group 缺 subtasks（非空数组）",
            "question_group 缺 subtasks（非空数组）",
        ),
        (
            "subtasks 超上限（L187）",
            _emit(_decompose(*(_subtask(f"s{i}") for i in range(_MAX_SUBTASKS + 1)))),
            "subtasks 超出上限（≤4 个——Owner 认可值）",
            "subtasks 超出上限（≤",
        ),
        (
            "支非对象（L192）",
            _emit(_decompose(_subtask("s1"), "s2")),
            "subtasks 支须为对象（{id/question/ledger_notes/...}）",
            "subtasks 支须为对象（{id/question/ledger_notes/...}）",
        ),
        (
            "支缺 id（L197）",
            _emit(_decompose({"question": "问", "ledger_notes": "注"})),
            "subtasks 支缺 id（组内唯一标识）",
            "subtasks 支缺 id（组内唯一标识）",
        ),
        (
            "支 id 重复（L199）",
            _emit(_decompose(_subtask("s1"), _subtask("s1"))),
            "subtasks id 重复：'s1'",
            "subtasks id 重复：",
        ),
        (
            "支缺 question（L201）",
            _emit(_decompose(_subtask("s1", question="   "))),
            "subtasks s1 缺 question（子问题原文）",
            "缺 question（子问题原文）",
        ),
        (
            "支缺 ledger_notes（L203-L206）",
            _emit(_decompose(_subtask("s1", ledger_notes=" "))),
            "subtasks s1 缺 ledger_notes（台账注释必带——从词典层逐字转抄："
            "〈精确指标 slot 名〉〈绑定态〉〈锚定窗〉）",
            "缺 ledger_notes（台账注释必带——从词典层",
        ),
        (
            "chain 越界（L209）",
            _emit(_decompose(_subtask("s1", chain="stat"))),
            "subtasks s1 chain 越界（data/knowledge）：'stat'",
            "chain 越界（",
        ),
        (
            "缺 ask 对象（L278）",
            _emit({"action": "ask"}),
            "action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）",
            "action=ask 缺 ask 对象（{'prompt': …, 'options': […]}）",
        ),
        (
            "ask 缺 prompt（L287）",
            _emit({"action": "ask", "ask": {"prompt": "   ", "options": ["BZ", "QHD"]}}),
            "ask 缺 prompt（问用户什么必填）",
            "ask 缺 prompt（问用户什么必填）",
        ),
        (
            "ask options 越界（L289）",
            _emit({"action": "ask", "ask": {"prompt": "先看哪个？", "options": ["BZ"]}}),
            "ask 缺 options 或个数越界（2~4 个选项）",
            "ask 缺 options 或个数越界（2~4 个选项）",
        ),
        (
            "匹配面 fallback＋无花括号提示（L322＋L88-L89）",
            parse_tool_match("不是 JSON", group),
            _TOOLMATCH_UNPARSABLE + "——输出中没有任何以左花括号起始的 JSON 对象"
            "（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）",
            _TOOLMATCH_UNPARSABLE,
        ),
        (
            "缺 matches（L325）",
            parse_tool_match(json.dumps({}), group),
            "缺 matches（非空数组——组内每个子问题恰一条）",
            "缺 matches（非空数组——组内每个子问题恰一条）",
        ),
        (
            "matches 支非对象（L332）",
            parse_tool_match(json.dumps({"matches": ["s1"]}), group),
            "matches 支须为对象（{id/chain/tool/plan|retrieval_need}）",
            "matches 支须为对象（{id/chain/tool/plan|retrieval_need}）",
        ),
        (
            "matches 支缺 id（L335）",
            parse_tool_match(_match_text({"chain": CHAIN_DATA, "tool": "data_query"}), group),
            "matches 支缺 id",
            "matches 支缺 id",
        ),
        (
            "id 不在问题组内（L337）",
            parse_tool_match(_match_text(_match("s9")), group),
            "matches id 's9' 不在问题组内（闭合世界：['s1', 's2']）",
            "不在问题组内（闭合世界：",
        ),
        (
            "id 重复（L339）",
            parse_tool_match(_match_text(_match("s1"), _match("s1")), group),
            "matches id 重复：'s1'（每子问题恰一条匹配）",
            "（每子问题恰一条匹配）",
        ),
        (
            "chain 越界（L342）",
            parse_tool_match(_match_text(_match("s1", chain="stat", tool="stat")), group),
            "matches s1 chain 越界（data/knowledge）：'stat'",
            "chain 越界（{'/'.join(sorted(CHAIN_KINDS))}）：",
        ),
        (
            "缺 tool（L345）",
            parse_tool_match(
                _match_text({"id": "s1", "chain": CHAIN_DATA, "plan": {"metric_slot": "m"}}), group
            ),
            "matches s1 缺 tool",
            "缺 tool（{'tool': 名, 'args': {...}}）",
        ),
        (
            "chain/tool 不一致（L347）",
            parse_tool_match(_match_text(_match("s1", tool="doc_retrieve")), group),
            "matches s1 chain/tool 不一致（data 链须配 data_query）",
            "chain/tool 不一致（",
        ),
        (
            "data 链缺 plan（L353）",
            parse_tool_match(
                _match_text({"id": "s1", "chain": CHAIN_DATA, "tool": "data_query"}), group
            ),
            "matches s1 data 链缺 plan（data_query 计划草案对象）",
            "data 链缺 plan（data_query 计划草案对象）",
        ),
        (
            "plan 缺 metric_slot（L355）",
            parse_tool_match(_match_text(_match("s1", plan={"metric_slot": "   "})), group),
            "matches s1 plan 缺 metric_slot（必填非空）",
            "plan 缺 metric_slot（必填非空）",
        ),
        (
            "knowledge 链缺 retrieval_need（L360）",
            parse_tool_match(
                _match_text({"id": "s1", "chain": CHAIN_KNOWLEDGE, "tool": "doc_retrieve"}), group
            ),
            "matches s1 knowledge 链缺 retrieval_need（参数对象）",
            "knowledge 链缺 retrieval_need（参数对象）",
        ),
        (
            "retrieval_need 缺 question（L362）",
            parse_tool_match(
                _match_text(
                    {
                        "id": "s1",
                        "chain": CHAIN_KNOWLEDGE,
                        "tool": "doc_retrieve",
                        "retrieval_need": {"question": "  "},
                    }
                ),
                group,
            ),
            "matches s1 retrieval_need 缺 question（必填非空）",
            "retrieval_need 缺 question（必填非空）",
        ),
        (
            "覆盖缺口（L374）",
            parse_tool_match(_match_text(_match("s1")), group),
            "matches 覆盖缺口（组内子问题缺匹配：['s2']）——每子问题恰一条",
            "matches 覆盖缺口（组内子问题缺匹配：",
        ),
    ]

    for label, actual, golden, skeleton in cases:
        assert isinstance(actual, str), f"{label}：分支未落拒因正文（三态闭世界）"
        assert actual == golden, label
        assert skeleton in v1_source, f"{label}：golden 不在迁移前快照内（快照非发明）"
    assert all(case[2] for case in cases), "金标面出现空拒文——拒因正文恒非空"

    # 机读甄别面恰一值：前缀「发现预算」（载体 L58）
    assert BUDGET_REJECT_MARK == "发现预算"
    assert 'BUDGET_REJECT_MARK = "发现预算"' in v1_source

    # 差异点⑥（已声明）：V1 `subtask.tool` 越界分支随 Owner 裁决 #10 退场——V1 字面在场、V2 面零命中
    assert "tool 越界" in v1_source
    assert _feature_files(_text_sources(_PARSING_DIR), "tool 越界") == []

    # 差异点②（已声明）：`args` 非对象＝拒（V1 此形裸抛 TypeError——无 V1 快照）；拒文＝
    # graph.py L616 逐字
    assert _emit({"action": "discover", "discovers": [{"tool": "台账查询", "args": "油井"}]}) == (
        "发现工具 台账查询 的 args 须为对象"
    )
    assert "的 args 须为对象" in _V1_GRAPH.read_text(encoding="utf-8")


# ── 行 15：拒因带定位（坏点字符序＋前后窗／无花括号提示／失衡退裸 fallback）────


def test_rejection_feedback_locus() -> None:
    """行 15｜拒因带定位：坏点字符序＋前后窗在场；无花括号专门提示；括号失衡形退裸 fallback。"""
    # ① 无左花括号形：逐字专门提示（L88-L89）
    assert json_syntax_feedback("只有解释文字，没有 JSON 外壳", _CLARIFY_UNPARSABLE) == (
        _CLARIFY_UNPARSABLE + "——输出中没有任何以左花括号起始的 JSON 对象"
        "（检查是否漏了 JSON 外壳、只输出了围栏或解释文字）"
    )
    # ② 语法坏点形：异常消息＋绝对坏点字符序＋坏点前后窗原文＋逐字修复指令（L104-L108 全段照抄）
    for prefix in ("", "先说两句废话。 " * 6):
        content = prefix + (
            '{"action": "ask", "ask": {"prompt": "先看哪个？", "options": ["BZ", "QHD"],}}'
        )
        start = content.index("{")
        try:
            json.loads(content[start:])
        except json.JSONDecodeError as exc:
            bad = start + exc.pos  # 绝对坏点字符序（exc.pos 相对片段）
            window = content[max(0, bad - 40) : bad + 40]  # 坏点前后窗（窗宽 40）
            message = exc.msg
        else:  # pragma: no cover - 样本必为坏点形
            raise AssertionError("样本须为语法坏点形")
        expected = (
            f"{_CLARIFY_UNPARSABLE}——JSON 语法错误：{message}（约第 {bad} 字符）。"
            "常见原因：少写右括号或方括号、尾逗号、引号未闭合。"
            f"你上次输出坏点附近原文：「{window}」"
            "——只修正语法错误，结构与其余内容照旧，重新输出一个 JSON。"
        )
        assert json_syntax_feedback(content, _CLARIFY_UNPARSABLE) == expected
        assert _emit_text(content) == expected  # 发射面实测同源（澄清面）
        assert window and f"约第 {bad} 字符" in expected and f"「{window}」" in expected

    # ③ 括号始终不平衡（截断形）→ 退裸 fallback（零定位——V1 事实面 D-L1a-03，本块不自行裁量）
    truncated = '{"action": "ask", "ask": {"prompt": "先看哪个？"'
    assert json_syntax_feedback(truncated, _CLARIFY_UNPARSABLE) == _CLARIFY_UNPARSABLE
    assert _emit_text(truncated) == _CLARIFY_UNPARSABLE
    assert parse_tool_match(truncated, _group("s1")) == _TOOLMATCH_UNPARSABLE
    assert "任何以左花括号" not in _CLARIFY_UNPARSABLE  # 零定位＝裸 fallback（无定位段）


# ── 行 16：提取单点＝首个花括号平衡块 ─────────────────────────────────────────


def test_extract_first_balanced_block() -> None:
    """行 16｜提取单点：首平衡块／首块坏不续扫／顶层非对象 → `None`。"""
    assert extract_plan_json('前言 {"a": 1} 尾巴 {"b": 2}') == {"a": 1}  # 只读首块
    assert extract_plan_json('```json\n{"a": 1}\n```') == {"a": 1}  # 围栏产／散文包裹产同路
    assert extract_plan_json('{"bad": } {"good": 1}') is None  # 首块坏不续扫（不救次块）
    assert extract_plan_json('{"a": {"b": 1}}') == {"a": {"b": 1}}  # 深度归零处切片交 JSON 解析
    assert extract_plan_json('{"a": {"b": "}"}}') is None  # 花括号计数非串态感知（V1 事实面）
    assert extract_plan_json('{"a": 1') is None  # 未平衡
    assert extract_plan_json("[1, 2, 3]") is None  # 顶层非对象（无左花括号形）
    assert extract_plan_json("没有任何 JSON 对象") is None
    assert extract_plan_json("") is None

    # 两发射面共用同一件（单点——围栏／散文包裹同路）
    assert isinstance(_emit_text('前言 {"action": "finalize"} 尾巴'), ClarifyEmission)
    cloaked = f'前言 {_match_text(_match("s1"))} 尾巴'
    assert isinstance(parse_tool_match(cloaked, _group("s1")), tuple)


# ── 行 17：引号自修四形＋修后全文可解析＋受理编排两形 ─────────────────────────


def test_quote_repair_four_forms() -> None:
    """行 17｜引号自修四形（转义不误伤／值内引号受理／无病不修／修后仍失败）＋修后全文可解析。"""
    # ① 转义不误伤（串内 `\` 连带后一字符原样带过）
    escaped = '{"a": "他说 \\"你好\\" 了", "b": "值内"引号"}'
    repaired = repair_inner_quotes(escaped)
    assert repaired is not None
    assert '\\"你好\\"' in repaired  # 合法转义零改动
    assert json.loads(repaired) == {"a": '他说 "你好" 了', "b": "值内「引号"}
    # ② 值内引号受理（开「闭」按出现次序交替）＋修后全文可解析
    inner = '{"q": "他说"你好"了"}'
    fixed = repair_inner_quotes(inner)
    assert fixed == '{"q": "他说「你好」了"}'
    assert json.loads(fixed) == {"q": "他说「你好」了"}  # 修后全文可解析
    # ③ 无病不修 → None
    assert repair_inner_quotes('{"a": 1}') is None
    assert repair_inner_quotes('{"a": "他说 \\"你好\\" 了"}') is None
    # ④ 修后仍失败（结构伤——引号修不了括号）→ None
    assert repair_inner_quotes('{"q": "他说"你好"了') is None
    assert repair_inner_quotes("不是 JSON") is None

    # 受理编排（本块②族末件单点）：解析拒→自修一次→重解析→首拒因保留＋受理标志
    broken = (
        '{"action": "ask", "ask": {"prompt": "先看哪个油田？答 "BZ" 还是 "QHD"？",'
        ' "options": ["BZ", "QHD"]}}'
    )
    result, repaired_flag = parse_with_quote_repair(_emit_text, broken)
    assert repaired_flag is True
    assert isinstance(result, ClarifyEmission)
    assert result.ask_prompt == "先看哪个油田？答 「BZ」 还是 「QHD」？"

    unfixable = '{"action": "discover", "discovers": [{"tool": "台账查询"}]'
    first, second_flag = parse_with_quote_repair(_emit_text, unfixable)
    assert second_flag is False
    assert first == _emit_text(unfixable)  # 首拒因保留（既有 V2-57 定位回喂零改动）
    assert first == _CLARIFY_UNPARSABLE

    # 解析件本体不使用提取件／自修件（接口⑤）：统一 JSON 严格解析直落 None——
    # 引号自修的**受理编排归消费方相位**（2026-10-17 EB5a：理解相位 `_read_and_parse` 经
    # `parse_with_quote_repair` 受理，与本件同族单点；`parse_understanding` 本体仍不调）
    parsers_path = _PARSING_DIR / "parsers.py"
    parsers_text = parsers_path.read_text(encoding="utf-8")
    parsers_tree = next(tree for path, tree in _parsing_sources() if path == parsers_path)
    understanding_def = next(
        node
        for node in parsers_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "parse_understanding"
    )
    understanding_body = ast.get_source_segment(parsers_text, understanding_def)
    assert understanding_body is not None
    for helper in (
        "extract_plan_json",
        "json_syntax_feedback",
        "repair_inner_quotes",
        "parse_with_quote_repair",
    ):
        assert helper not in understanding_body, f"理解面调用了共用件：{helper}"


# ── 行 18／19：载荷定型类字段表与形状单点 ─────────────────────────────────────


def test_payload_types_field_tables() -> None:
    """行 18｜载荷定型类：字段集与投影键形（`as_payload`）逐字；空值键不出现；
    `ask` 段开闸单点。"""
    assert tuple(Subtask.__dataclass_fields__) == ("id", "question", "ledger_notes", "chain")
    assert "tool" not in Subtask.__dataclass_fields__  # 差异点⑥：`tool` 退场（Owner 裁决 #10）
    assert tuple(QuestionGroup.__dataclass_fields__) == ("subtasks",)
    assert tuple(ClarifyEmission.__dataclass_fields__) == (
        "kind",
        "group",
        "discovers",
        "ask_prompt",
        "ask_options",
        "thought",
        "note",
    )
    assert tuple(SubtaskMatch.__dataclass_fields__) == (
        "id",
        "chain",
        "tool",
        "plan",
        "retrieval_need",
        "caliber_key",
        "mention_mode",
    )
    assert tuple(Understanding.__dataclass_fields__) == ("text", "metric_candidates", "route")
    assert tuple(Direct.__dataclass_fields__) == ("text", "route")
    for cls in (Understanding, Direct, Subtask, QuestionGroup, ClarifyEmission, SubtaskMatch):
        assert cls.__dataclass_params__.frozen is True, cls.__name__  # 全 frozen
        assert cls.__slots__ == tuple(cls.__dataclass_fields__), cls.__name__  # 全 slots

    # 投影规则逐字：恒带键照抄、空值键不出现
    bare_subtask = Subtask(id="s1", question="问", ledger_notes="注")
    assert bare_subtask.as_payload() == {"id": "s1", "question": "问", "ledger_notes": "注"}
    assert "chain" not in bare_subtask.as_payload()
    chained = Subtask(id="s1", question="问", ledger_notes="注", chain=CHAIN_DATA)
    assert chained.as_payload() == {
        "id": "s1",
        "question": "问",
        "ledger_notes": "注",
        "chain": "data",
    }
    assert QuestionGroup(subtasks=(bare_subtask,)).as_payload() == {
        "subtasks": [{"id": "s1", "question": "问", "ledger_notes": "注"}]
    }  # 恒单键形

    match_base = {"id": "s1", "chain": CHAIN_DATA, "tool": "data_query"}
    assert SubtaskMatch(id="s1", chain=CHAIN_DATA, tool="data_query").as_payload() == match_base
    with_plan = SubtaskMatch(
        id="s1", chain=CHAIN_DATA, tool="data_query", plan={"metric_slot": "m"}
    ).as_payload()
    assert with_plan == {**match_base, "plan": {"metric_slot": "m"}}  # 非 None 才出键
    with_all = SubtaskMatch(
        id="s1",
        chain=CHAIN_KNOWLEDGE,
        tool="doc_retrieve",
        retrieval_need={"question": "检索"},
        caliber_key="场景词",
    ).as_payload()
    assert with_all == {
        "id": "s1",
        "chain": "knowledge",
        "tool": "doc_retrieve",
        "retrieval_need": {"question": "检索"},
        "caliber_key": "场景词",  # 真值才出键
    }
    assert set(match_base) == {"id", "chain", "tool"}

    # ClarifyEmission：恒 `action`＋thought／note 真值才出＋group 非 None 才出＋discovers 非空才出
    assert ClarifyEmission(kind="finalize").as_payload() == {"action": "finalize"}
    assert ClarifyEmission(kind="finalize", thought="够", note="注").as_payload() == {
        "action": "finalize",
        "thought": "够",
        "note": "注",
    }
    assert ClarifyEmission(kind="decompose", group=_group("s1")).as_payload() == {
        "action": "decompose",
        "question_group": {
            "subtasks": [{"id": "s1", "question": "问 s1", "ledger_notes": "注 s1"}]
        },
    }
    assert ClarifyEmission(
        kind="discover", discovers=({"tool": "台账查询", "args": {}},)
    ).as_payload() == {"action": "discover", "discovers": [{"tool": "台账查询", "args": {}}]}

    # `ask` 段以 `ask_prompt` 真假单点开闸（`ask_options` 单有值静默消失——V1 事实面 D-L1a-04）
    assert ClarifyEmission(kind="ask", ask_options=("BZ", "QHD")).as_payload() == {"action": "ask"}
    assert ClarifyEmission(kind="ask", ask_prompt="先看哪个？").as_payload() == {
        "action": "ask",
        "ask": {"prompt": "先看哪个？", "options": []},
    }
    asked = ClarifyEmission(kind="ask", ask_prompt="先看哪个？", ask_options=("BZ", "QHD"))
    assert asked.as_payload() == {
        "action": "ask",
        "ask": {"prompt": "先看哪个？", "options": ["BZ", "QHD"]},
    }
    # 实跑投影（四动作 payload 键形逐字——消费方 schema 断言面）
    assert _emission_of({"action": "finalize", "未知键": "静默忽略"}).as_payload() == {
        "action": "finalize"
    }


def test_understanding_payload_shape_single_source() -> None:
    """行 19｜载荷类五类形状与行为 11（及 `understanding` 所列集合）相等；本块无第二处形状定义
    （AST／集合比较）。"""
    shaped = {
        "Understanding": {"text", "metric_candidates", "route"},
        "Direct": {"text", "route"},
        "Subtask": {"id", "question", "ledger_notes", "chain"},
        "QuestionGroup": {"subtasks"},
        "SubtaskMatch": {
            "id",
            "chain",
            "tool",
            "plan",
            "retrieval_need",
            "caliber_key",
            "mention_mode",
        },
    }
    for name, fields in shaped.items():
        assert set(getattr(parsing, name).__dataclass_fields__) == fields, name

    # `Understanding`／`Direct` 字段集以 `specs/understanding.md` 接口定义为准（逐类对读）
    understanding_spec = Path("specs/understanding.md").read_text(encoding="utf-8")
    for name in ("Understanding", "Direct"):
        assert _spec_class_fields(understanding_spec, name) == shaped[name], name

    # 五类物理定义点＝本块（runtimev2 面内恰一处——消费面不重定义）
    defs = _class_defs(_runtimev2_sources())
    models = (_PARSING_DIR / "models.py").as_posix()
    for name in shaped:
        assert defs.get(name) == [models], f"{name} 形状定义点不唯一：{defs.get(name)}"
        assert getattr(parsing, name).__module__ == "appv2.runtimev2.parsing.models", name

    # 探测器非空转：伪造第二处形状定义即被咬
    forged = [(Path("forged.py"), ast.parse("class Subtask:\n    pass\n"))]
    assert _class_defs(forged)["Subtask"] == ["forged.py"]


# ── 行 22：共用件（含受理编排）单点 ───────────────────────────────────────────

_HELPER_FEATURES: dict[str, str] = {
    "extract_plan_json": "for position in range(start, len(content)):",
    "json_syntax_feedback": "你上次输出坏点附近原文",
    "repair_inner_quotes": "inner_open = not inner_open",
    "parse_with_quote_repair": "repair_inner_quotes(content)",
}


def test_shared_helpers_single_source() -> None:
    """行 22｜共用件（含受理编排）单点：特征子串在 `understanding`／`clarification`／
    `tool_matching` 块源码零命中（零副本）。"""
    phase_sources = [
        item for name in _PHASE_DIRS for item in _text_sources(_RUNTIMEV2_DIR / name)
    ]
    assert phase_sources, "相位块扫描面为空——扫不到源码即失去看守意义"
    outside = [
        item
        for item in _text_sources(_RUNTIMEV2_DIR)
        if item[0].parent != _PARSING_DIR and _PARSING_DIR not in item[0].parents
    ]
    assert outside, "runtimev2 面（parsing 外）扫描面为空"
    for helper, feature in _HELPER_FEATURES.items():
        assert feature in (_PARSING_DIR / "helpers.py").read_text(encoding="utf-8"), helper
        assert _feature_files(phase_sources, feature) == [], f"{helper} 相位块副本残留"
        assert _feature_files(outside, feature) == [], f"{helper} runtimev2 面副本残留"
        hosts = [
            path.as_posix()
            for path, text in _text_sources(_RUNTIMEV2_DIR)
            if f"def {helper}(" in text
        ]
        expected_host = (_PARSING_DIR / "helpers.py").as_posix()
        assert hosts == [expected_host], f"{helper} 定义点不唯一：{hosts}"
        assert getattr(parsing, helper).__module__ == "appv2.runtimev2.parsing.helpers", helper

    # 探测器非空转：伪造相位块源码，特征在场即被咬
    forged = (Path("understanding/forged.py"), "for position in range(start, len(content)):")
    assert _feature_files([forged], _HELPER_FEATURES["extract_plan_json"]) == [
        "understanding/forged.py"
    ]


# ── 行 23：数字与上限单点（注入制）────────────────────────────────────────────


def test_limits_from_state_constants() -> None:
    """行 23｜数字单点：签名无裸默认值（注入制）；注入参数取值来源逐参可指 `state` 键或登记项；
    裸字面扫描（豁免面＝迁移拒文与 `ask` 边界字面）。"""
    signature = inspect.signature(parse_question_group)
    assert list(signature.parameters) == [
        "text",
        "max_discovers",
        "discover_budget_left",
        "max_subtasks",
    ]
    assert signature.parameters["max_discovers"].default is inspect.Parameter.empty
    assert signature.parameters["max_subtasks"].default is inspect.Parameter.empty
    # V2 定案签名逐字：`discover_budget_left` 缺省 `None`＝无预算闸形（非裸上限值）
    assert signature.parameters["discover_budget_left"].default is None
    for name in ("max_discovers", "discover_budget_left", "max_subtasks"):
        assert signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY, name

    # 取值来源逐参可指（源码注记＋真源锚）：`max_discovers`→state「轮内发现」键；
    # `discover_budget_left`→「全 run 发现」键；`max_subtasks`→登记项
    # （walk/09 §七 Q-C／eng/00 F-14，state 承载键未落定＝风险 7⑤）
    parsing_text = " ".join(
        " ".join(text.split()) for _, text in _text_sources(_PARSING_DIR)
    )  # 空白归一（注记跨行折行不影响真源锚在场判）
    state_spec = Path("specs/state.md").read_text(encoding="utf-8")
    for anchor in ("轮内发现", "全 run 发现"):
        assert anchor in parsing_text, anchor
        assert anchor in state_spec, anchor
    for anchor in ("walk/09", "F-14"):
        assert anchor in parsing_text, anchor

    # 裸上限字面扫描：与 `len(...)` 同比较的整数字面量恰一处＝`ask` 边界（2／4——风险 7② 豁免面）
    bare = {
        path.name: found
        for path, tree in _parsing_sources()
        if (found := _bare_limits(tree))
    }
    assert sorted(bare) == ["parsers.py"], bare
    assert list(bare["parsers.py"].values()) == [(2, 4)], bare

    # 模块级无 `MAX_` 裸常量（限额随注入制退场——差异点③；包根亦无）
    assert [
        node.targets[0].id
        for _, tree in _parsing_sources()
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id.startswith("MAX")
    ] == []
    assert not hasattr(parsing, "MAX_SUBTASKS_CONTRACT")

    # 探测器非空转：伪造裸上限比较即被咬
    assert _bare_limits(ast.parse("if len(items) > 7:\n    pass\n")) == {1: (7,)}


# ── 行 24：程序侧无词表／正则语义判断 ─────────────────────────────────────────

_BANNED_STR_METHODS = {
    "startswith",
    "endswith",
    "lower",
    "upper",
    "casefold",
    "split",
    "partition",
    "format_map",
    "count",
}


def test_no_lexicon_or_regex_in_parsing() -> None:
    """行 24｜程序侧无词表／正则语义判断（AST；豁免面＝形态处理）。"""
    sources = _parsing_sources()
    assert sources
    for path, tree in sources:
        modules = _imported_modules(tree)
        assert "re" not in modules and "regex" not in modules, f"{path.name} 引入正则面"
        assert not any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "re"
            for node in ast.walk(tree)
        ), f"{path.name} 使用 re.*"
        assert _lexicon_violations(tree) == [], f"{path.name}: {_lexicon_violations(tree)}"
        for node in ast.walk(tree):
            # 成员判据面＝闭世界常量／结构字符集（ASCII 字符扫描与存在性豁免面）
            if isinstance(node, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
            ):
                for operand in (node.left, *node.comparators):
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                        where = f"{path.name}:{node.lineno}"
                        assert operand.value.isascii(), f"{where} 非结构字符集判据"
            # 词面判方法（前缀／后缀／大小写折叠／切分）零使用——判定清单＝结构判
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in _BANNED_STR_METHODS, (
                    f"{path.name}:{node.lineno} 词面判方法 {node.func.attr}"
                )

    # 探测器非空转：伪造词表／汉字成员判据／词面判方法即被咬
    assert _lexicon_violations(ast.parse('WORDS = ["提及", "执行"]\n')) != []
    assert _lexicon_violations(ast.parse('if word in "提及执行":\n    pass\n')) != []
    forged_call = ast.parse('text.startswith("理解：")\n')
    assert any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and node.func.attr in _BANNED_STR_METHODS
        for node in ast.walk(forged_call)
    )


# ── 行 25：确定性纯函数（零 IO／模型／时钟／随机／事件／状态写）────────────────

_FORBIDDEN_MODULES = {
    "os",
    "io",
    "sys",
    "time",
    "datetime",
    "random",
    "asyncio",
    "logging",
    "socket",
    "subprocess",
    "shutil",
    "tempfile",
    "pathlib",
    "uuid",
    "secrets",
}
_FORBIDDEN_CALLS = {"open", "print", "input", "exec", "eval", "compile", "__import__"}
_FORBIDDEN_ATTR_CALLS = {
    ("time", "time"),
    ("time", "monotonic"),
    ("datetime", "now"),
    ("random", "random"),
    ("os", "urandom"),
    ("uuid", "uuid4"),
}


def test_parsing_pure_deterministic() -> None:
    """行 25｜确定性纯函数：两跑逐字相等；零 IO／模型／时钟／随机／事件／状态写（AST）。"""
    probes: list[tuple[str, Callable[[], Any]]] = [
        (
            "理解面",
            lambda: parse_understanding(
                json.dumps(
                    {"route": "full", "text": "问", "metric_candidates": ["日产油量"]},
                    ensure_ascii=False,
                )
            ),
        ),
        ("澄清面", lambda: _emit(_decompose(_subtask("s1", chain=CHAIN_DATA)))),
        ("匹配面", lambda: parse_tool_match(_match_text(_match("s1")), _group("s1"))),
        ("提取件", lambda: extract_plan_json('{"a": 1}')),
        ("带定位件", lambda: json_syntax_feedback("坏", "F")),
        ("自修件", lambda: repair_inner_quotes('{"q": "他说"你好"了"}')),
        (
            "指纹件",
            lambda: emission_fingerprints({"metric_slot": "日产油量"}, {"question": "检索"}),
        ),
    ]
    for label, probe in probes:
        assert repr(_frozen(probe())) == repr(_frozen(probe())), label  # 两跑逐字相等

    for path, tree in _parsing_sources():
        modules = _imported_modules(tree)
        assert not (modules & _FORBIDDEN_MODULES), f"{path.name} 引入 IO／时钟／随机面"
        assert "appv2.infra.llm_client" not in modules, f"{path.name} 直引 llm_client"
        assert "appv2.runtimev2.gateway_adapter" not in modules, f"{path.name} 引 gateway_adapter"
        assert "state" not in modules, f"{path.name} 引 state（本块唯一接触＝注入面形状，零写入）"
        assert not any(
            isinstance(node, (ast.Await, ast.AsyncFunctionDef)) for node in ast.walk(tree)
        ), f"{path.name} 异步面"
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                assert node.func.id not in _FORBIDDEN_CALLS, f"{path.name}:{node.lineno}"
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    assert (node.func.value.id, node.func.attr) not in _FORBIDDEN_ATTR_CALLS, (
                        f"{path.name}:{node.lineno}"
                    )
                assert node.func.attr not in {"emit", "publish", "append_message", "write"}, (
                    f"{path.name}:{node.lineno} 事件／写面调用"
                )

    # 探测器非空转：伪造 IO／时钟／事件面即被咬
    forged_io = ast.parse("import random\nvalue = random.random()\n")
    assert _imported_modules(forged_io) & _FORBIDDEN_MODULES
    forged_open = ast.parse('handle = open("f")\n')
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FORBIDDEN_CALLS
        for node in ast.walk(forged_open)
    )


# ── 行 26：import 面只许 `state` ──────────────────────────────────────────────

_ALLOWED_STDLIB_IMPORTS = {"json", "typing", "dataclasses", "collections.abc"}
_V2_BLOCKS = (
    "understanding",
    "clarification",
    "tool_matching",
    "preconditions",
    "execution",
    "answering",
    "verification",
    "orchestration",
    "bookkeeping",
    "prompts",
    "context",
    "transport",
    "persistence",
    "gateway_adapter",
    "gate",
)


def test_imports_state_only() -> None:
    """行 26｜import 面只许 `state`（AST 扫描——R3 半覆盖面的降维补位）。"""
    for path, tree in _parsing_sources():
        for module in _imported_modules(tree):
            if module == "appv2.runtimev2.state" or module.startswith("appv2.runtimev2.state."):
                continue
            assert module in _ALLOWED_STDLIB_IMPORTS or module.startswith(
                "appv2.runtimev2.parsing"
            ), f"{path.name} 越界 import：{module}"
        # 禁引旧码／引擎／供应商／上层（R5／R6／R7 的 AST 补位）
        text = path.read_text(encoding="utf-8")
        banned_roots = (
            "appv2.runtime.",
            "appv2.infra",
            "appv2.tools",
            "appv2.api",
            "appv2.domains",
        )
        for forbidden in banned_roots:
            assert forbidden not in text, f"{path.name} 命中禁引面：{forbidden}"

    # 禁引公共层其余块（R3 未覆盖半面——AST 降维；`state` 为唯一许可面）
    for block in _V2_BLOCKS:
        assert _feature_files(
            _text_sources(_PARSING_DIR), f"appv2.runtimev2.{block}"
        ) == [], f"parsing 引公共层其余块：{block}"

    # 探测器非空转：伪造越界 import 即被咬
    forged = ast.parse("from appv2.runtimev2.bookkeeping import append_message")
    assert "appv2.runtimev2.bookkeeping" in _imported_modules(forged)


# ── 行 27／28：边界集与保留集 ─────────────────────────────────────────────────


def test_boundary_missing_overlimit_quote_duplicate() -> None:
    """行 27｜【边界集】缺字段／超限／引号异常／重复 `id`／括号失衡截断 → 各落拒因正文或 `None`。"""
    # 缺字段：理解面 → None；澄清面／匹配面 → 拒因正文
    assert parse_understanding(json.dumps({"route": "full", "metric_candidates": []})) is None
    assert _emit(_decompose({"id": "s1", "question": "问"})) == (
        "subtasks s1 缺 ledger_notes（台账注释必带——从词典层逐字转抄："
        "〈精确指标 slot 名〉〈绑定态〉〈锚定窗〉）"
    )
    idless = parse_tool_match(
        _match_text({"chain": CHAIN_DATA, "tool": "data_query"}), _group("s1")
    )
    assert idless == "matches 支缺 id"
    # 超限：单次上限／全 run 预算／子问题上限
    over_single = _emit(
        {"action": "discover", "discovers": [{"tool": t} for t in ("t1", "t2", "t3")]}
    )
    assert over_single == f"discovers 超出单次上限（≤{_MAX_DISCOVERS} 支）"
    over_budget = _emit(
        {"action": "discover", "discovers": [{"tool": "t1"}, {"tool": "t2"}]},
        discover_budget_left=1,
    )
    assert isinstance(over_budget, str) and over_budget.startswith(BUDGET_REJECT_MARK)
    over_subtasks = _emit(_decompose(*(_subtask(f"s{i}") for i in range(_MAX_SUBTASKS + 1))))
    assert isinstance(over_subtasks, str) and over_subtasks.startswith("subtasks 超出上限")
    # 引号异常：不静默——拒因正文（带定位）在场（自修受理面见行 17／行 22）
    quote_broken = (
        '{"action": "ask", "ask": {"prompt": "看哪个"油田"？", "options": ["BZ", "QHD"]}}'
    )
    feedback = _emit_text(quote_broken)
    assert isinstance(feedback, str)
    assert feedback.startswith(_CLARIFY_UNPARSABLE + "——JSON 语法错误：")
    assert "重新输出一个 JSON。" in feedback
    # 重复 `id`：问题组支／匹配支各拒（拒因原文逐字——行为 17）
    assert _emit(_decompose(_subtask("s1"), _subtask("s1"))) == "subtasks id 重复：'s1'"
    assert parse_tool_match(_match_text(_match("s1"), _match("s1")), _group("s1")) == (
        "matches id 重复：'s1'（每子问题恰一条匹配）"
    )
    # 括号失衡截断 → 提取面 None／带定位面裸 fallback（零定位）
    assert extract_plan_json('{"action": "ask"') is None
    assert _emit_text('{"action": "ask"') == _CLARIFY_UNPARSABLE
    # JSON 重复键形＝真源未裁落点（风险 7⑥）——本块不自行加严，样本行为如实记录（取后者）
    duplicated = _emit_text('{"action": "ask", "action": "finalize", "thought": "t"}')
    assert isinstance(duplicated, ClarifyEmission)
    assert duplicated.kind == "finalize"
    assert json.loads('{"action": "ask", "action": "finalize"}') == {"action": "finalize"}


def test_retention_normal_parses_unchanged() -> None:
    """行 28｜【保留集】常规三面文本解析不受边界分支影响；消费方既有 schema 断言不因迁移改形
    回归。"""
    # 理解面两形（常规样本）
    full = parse_understanding(
        json.dumps(
            {"route": "full", "text": "渤海油田日产油量怎么算", "metric_candidates": ["日产油量"]},
            ensure_ascii=False,
        )
    )
    assert full == Understanding(
        text="渤海油田日产油量怎么算", metric_candidates=["日产油量"], route=ROUTE_FULL
    )
    direct = parse_understanding(
        json.dumps({"route": "direct", "text": "谢谢，再见"}, ensure_ascii=False)
    )
    assert direct == Direct(text="谢谢，再见", route=ROUTE_DIRECT)

    # 澄清面四动作：payload 键形逐字（消费方 schema 断言面不改形）
    assert _emission_of(_decompose(_subtask("s1", chain=CHAIN_DATA))).as_payload() == {
        "action": "decompose",
        "question_group": {
            "subtasks": [
                {"id": "s1", "question": "问 s1", "ledger_notes": "注 s1", "chain": "data"}
            ]
        },
    }
    discovered = _emission_of({"action": "discover", "discovers": [{"tool": "台账查询"}]})
    assert discovered.as_payload() == {
        "action": "discover",
        "discovers": [{"tool": "台账查询", "args": {}}],
    }
    assert _emission_of(
        {"action": "ask", "ask": {"prompt": "先看哪个油田？", "options": ["BZ", "QHD"]}}
    ).as_payload() == {
        "action": "ask",
        "ask": {"prompt": "先看哪个油田？", "options": ["BZ", "QHD"]},
    }
    assert _emission_of({"action": "finalize", "thought": "材料足够"}).as_payload() == {
        "action": "finalize",
        "thought": "材料足够",
    }

    # 匹配面：全配 → tuple（顺序＝发射顺序）＋投影逐字
    matches = parse_tool_match(
        _match_text(
            _match(
                "s2",
                chain=CHAIN_KNOWLEDGE,
                tool="doc_retrieve",
                plan=None,
                retrieval_need={"question": "检索 s2"},
                caliber_key=" 场景词 ",
            ),
            _match("s1"),
        ),
        _group("s1", "s2"),
    )
    assert isinstance(matches, tuple)
    assert [item.as_payload() for item in matches] == [
        {
            "id": "s2",
            "chain": "knowledge",
            "tool": "doc_retrieve",
            "retrieval_need": {"question": "检索 s2"},
            "caliber_key": "场景词",
        },
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {"metric_slot": "日产油量"}},
    ]

    # 常规解析不受边界分支影响：同一样本跑两遍（边界集用例不改变常规路径结果）
    assert _frozen(parse_tool_match(_match_text(_match("s1")), _group("s1"))) == _frozen(
        parse_tool_match(_match_text(_match("s1")), _group("s1"))
    )
    assert _frozen(_emit(_decompose(_subtask("s1")))) == _frozen(_emit(_decompose(_subtask("s1"))))
