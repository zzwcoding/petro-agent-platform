"""parsing 块验收（RT-W2-05a：骨架＋三面解析器族核心簇＋本块 pin 相关两行）。

票面对象＝`specs/parsing.md`「验收测试」表第 **1–13** 行（-05a 逐字，用例标识与规格列逐字一致、
`#` 保留规格表行序）；本件同时落「测试网钉」pin-06 **器材面**用例（规格表第 20／21 行的指纹四件
——-05a「织网义务」节第②条落网点；pin-06 行为面在 `specs/execution.md` 行为 13，本块零触发面）。

pin-04（发射 JSON 不进答案面）／pin-13（起草回声=0）经逐条核实**不落本块**——本件不设第三面
对账，反向保证＝行 1–3（理解面严格解析，旧降级通道零可达）。

拒因文本真源＝迁移前 `appv2/runtime/subtask.py`（L179-L290 澄清面／L318-L375 匹配面／L82-L110
带定位）；`args` 非对象拒文＝`appv2/runtime/graph.py` L616 字面。规格表第 14–19、22–28 行
（拒因逐字 golden／带定位／提取单点／引号自修／载荷定型类两行／共用件单点／数字单点／三条元面／
边界集／保留集）归 `RT-W2-05b-parsing.md`——本件不预占其用例标识；**第 20／21 行**（pin-06
器材面两式）已按 -05a 票面「验收」第二条＋「织网义务」第②条在本件落名并全绿，-05b 复核在场
即可、勿对同一标识再定义一次（两处同名用例＝两处真源漂移）。
"""

from __future__ import annotations

import inspect
import json
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
    is_same_param_replay,
    parse_question_group,
    parse_tool_match,
    parse_understanding,
    payload_fingerprint,
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
