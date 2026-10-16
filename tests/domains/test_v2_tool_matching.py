"""RT-W4-03 tool_matching 验收——`specs/tool_matching.md`「验收测试」表 15 行逐行落测（1:1 同名）。

15 行对应（规格表 `specs/tool_matching.md:124–:138` 原序、标识逐字）：
- 行 1 `exactly_one_match_per_subtask`：子问题恰配一条；漏配 → 判失败带结构化拒因；
- 行 2 `duplicate_or_unknown_id_rejected`：多配／编号对不上 → 判失败；
- 行 3 `tool_name_closed_world`：工具名不在注册表名单 → 判失败（闭世界）；
- 行 4 `required_by_chain`：`chain="data"` 缺 `plan`／`chain="knowledge"` 缺 `retrieval_need`
  → 判失败；
- 行 5 `metric_slot_not_english_column`：`metric_slot` 空或呈英文列名形（判定形＝ASCII
  标识符形）→ 判失败；
- 行 6 `ranking_direction_paired`：`ranking` 与 `direction` 同现约束；
- 行 7 `legacy_name_normalized_before_query`：旧名经账本归一后才出数（出数只认现行口径）；
- 行 8 `parse_rejection_str_to_tool_match_rejection_consumer_side`：解析拒文（parsing `str`）→
  `ToolMatchRejection` 结构化转换归本块（机械适配、零语义判断——行为 11）；
- 行 9 `descriptor_covers_three_parts`：每个工具描述含「何时用／不能做什么／参数示例」三项
  （经 tools seam）；
- 行 10 `no_lexicon_or_regex_in_tool_matching`：程序只对账、不替模型选工具（AST 扫描本模块）；
- 行 11 `rejection_signal_present`：失败与拒因的机读信号在场（step payload ＋ notice）；
- 行 12 `boundary_enum_out_of_range`：【边界集】`chain`／`direction` 越界取值 → 判失败；
- 行 13 `retention_normalize`：【保留集】名归一闸行为不变（本块）；
- 行 14 `retention_pushdown`：【保留集】聚合下推行为不变（归属 `execution`）；
- 行 15 `mention_mode_closed_world`：`SubtaskMatch.mention_mode` 取值闭世界越界即拒。

本票另三条自有面（非规格表行）：
- `pin31_mention_mode_produced_with_caliber_key`：pin-31 判断产出面（「提及 vs 执行」结论与
  `caliber_key` 由模型在配工具那次调用**同批产出**）；
- `no_bypass_model_call_single_point`：「无旁路」行为断言（模型调用只经 `bookkeeping.call_model`）；
- `public_surface_single_entry`＋链面两条：本块公开面＝规格「接口定义」节名单、单入口 `match`、
  链只追加（pin-22）＋相位合同一次性（pin-24）。

真源：`specs/tool_matching.md`（已定稿）／卡 `specs/modules.md` `## tool_matching`；
逐字拒文逐字稿载体＝`appv2/runtime/subtask.py`（本票照抄，偏离即停报）。
"""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import appv2.runtimev2.tool_matching as tool_matching
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.parsing import QuestionGroup, Subtask, parse_tool_match
from appv2.runtimev2.state import RunState
from appv2.runtimev2.tool_matching import (
    DATA_CHAIN,
    DIRECTIONS,
    KIND_DUPLICATE,
    KIND_ENUM_OUT_OF_RANGE,
    KIND_MALFORMED,
    KIND_MISSING_REQUIRED,
    KIND_MISSING_SUBTASK,
    KIND_UNKNOWN_ID,
    KNOWLEDGE_CHAIN,
    MATCH_REASON_KINDS,
    MENTION_EXECUTED,
    MENTION_MENTIONED_ONLY,
    MENTION_MODES,
    SubtaskMatch,
    ToolMatchRejection,
    ToolPlan,
    match,
)
from appv2.tools import (
    DATA_QUERY,
    DOC_RETRIEVE,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    ToolRegistry,
    ledger_facts,
    normalize_metric_name,
    resolve_metric_slot,
)

_TOOL_MATCHING_DIR = Path(tool_matching.__file__).parent
_V1_SUBTASK = Path("appv2/runtime/subtask.py")  # 逐字拒文载体（迁移前快照）
_PARSING_PARSERS = Path("appv2/runtimev2/parsing/parsers.py")  # 匹配面解析单点（拒文产出面）
_THREE_PARTS = ("何时用", "不能做什么", "参数示例")


# ── fixture：状态、发射文本与同面模型替身 ──────────────────────────────────────


def _group_payload(ids: Sequence[str]) -> dict[str, Any]:
    return {
        "subtasks": [
            {
                "id": subtask_id,
                "question": f"{subtask_id} 子问题原句",
                "ledger_notes": f"{subtask_id}｜在册可出数｜近 30 天",
                "chain": DATA_CHAIN,
            }
            for subtask_id in ids
        ]
    }


def _state(*, ids: Sequence[str] = ("s1",)) -> RunState:
    return RunState(
        run_id="run-toolmatch",
        actor="dev-user",
        question="原题",
        question_group=_group_payload(ids),
    )


def _emission(matches: Sequence[Mapping[str, Any]]) -> str:
    """匹配轮发射文本（`{"matches": […]}`——模型原话形）。"""
    return json.dumps({"matches": list(matches)}, ensure_ascii=False)


def _data_match(
    subtask_id: str = "s1",
    *,
    tool: str = DATA_QUERY,
    mention_mode: str = MENTION_EXECUTED,
    plan: Mapping[str, Any] | None = None,
    caliber_key: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": subtask_id,
        "chain": DATA_CHAIN,
        "tool": tool,
        "mention_mode": mention_mode,
        "plan": {"metric_slot": "日产油量", "ranking": False} if plan is None else dict(plan),
    }
    if caliber_key is not None:
        body["caliber_key"] = caliber_key
    return body


def _knowledge_match(
    subtask_id: str = "s1",
    *,
    tool: str = DOC_RETRIEVE,
    mention_mode: str = MENTION_EXECUTED,
    retrieval_need: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": subtask_id,
        "chain": KNOWLEDGE_CHAIN,
        "tool": tool,
        "mention_mode": mention_mode,
        "retrieval_need": {"question": f"{subtask_id} 子问题原句"}
        if retrieval_need is None
        else dict(retrieval_need),
    }


def _run(state: RunState, content: str) -> tuple[Any, ScriptedCompleter]:
    """同面替身注入（`set_completer` 显式缝）→ 调 `match` → 复位；返回（结果，替身）。"""
    scripted = ScriptedCompleter({"decision": [content]})
    previous = set_completer(scripted)
    try:
        result = match(state)
    finally:
        set_completer(previous)
    assert scripted.calls, "模型调用未发生（本块须经 bookkeeping.call_model 发起）"
    return result, scripted


def _rejection(result: Any) -> ToolMatchRejection:
    assert isinstance(result, ToolMatchRejection), f"预期结构化拒因，实为 {_show(result)}"
    return result


def _plan(result: Any) -> ToolPlan:
    assert isinstance(result, ToolPlan), f"预期 ToolPlan，实为 {_show(result)}"
    return result


def _show(result: Any) -> str:
    if isinstance(result, ToolMatchRejection):
        return (
            "ToolMatchRejection["
            + "；".join(f"{reason.kind}：{reason.reason}" for reason in result.reasons)
            + "]"
        )
    return type(result).__name__


def _registry() -> ToolRegistry:
    """tools seam 上的工具目录（假引擎 adapter——卡「Seam 与测试」节）。"""
    return ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )


# ── 行 1：子问题恰配一条 ───────────────────────────────────────────────────────


def test_exactly_one_match_per_subtask() -> None:
    """行 1｜恰配一条：条数＝子问题条数、编号一一对上；漏配 → 判失败带结构化拒因。"""
    state = _state(ids=("s1", "s2"))
    plan = _plan(_run(state, _emission([_data_match("s1"), _knowledge_match("s2")]))[0])
    assert [item.id for item in plan.matches] == ["s1", "s2"]
    assert [item.chain for item in plan.matches] == [DATA_CHAIN, KNOWLEDGE_CHAIN]
    assert len(plan.matches) == len(state.question_group["subtasks"])

    state = _state(ids=("s1", "s2"))
    rejection = _rejection(_run(state, _emission([_data_match("s1")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_SUBTASK]
    assert rejection.reasons[0].reason == (
        "matches 覆盖缺口（组内子问题缺匹配：['s2']）——每子问题恰一条"
    )

    state = _state(ids=("s1",))
    rejection = _rejection(_run(state, _emission([]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_SUBTASK]
    assert rejection.reasons[0].reason == "缺 matches（非空数组——组内每个子问题恰一条）"


# ── 行 2：多配／编号对不上 ─────────────────────────────────────────────────────


def test_duplicate_or_unknown_id_rejected() -> None:
    """行 2｜多配（id 重复）与编号对不上（id 不在问题组内）→ 判失败，拒文逐字。"""
    state = _state(ids=("s1", "s2"))
    rejection = _rejection(_run(state, _emission([_data_match("s1"), _knowledge_match("s1")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_DUPLICATE]
    assert rejection.reasons[0].reason == "matches id 重复：'s1'（每子问题恰一条匹配）"

    state = _state(ids=("s1", "s2"))
    rejection = _rejection(_run(state, _emission([_data_match("s9")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_UNKNOWN_ID]
    assert rejection.reasons[0].reason == ("matches id 's9' 不在问题组内（闭合世界：['s1', 's2']）")


# ── 行 3：工具名闭世界（注册表名单） ───────────────────────────────────────────


def test_tool_name_closed_world() -> None:
    """行 3｜工具名不在注册表名单 → 判失败（闭世界）。

    名单真源＝tools 公开面（`descriptors()`——卡「Seam: 工具目录」）；两条链各自的唯一工具
    都在册，名单外与「在册但不对链」的名字一律拒。
    """
    catalog = {descriptor.name for descriptor in _registry().descriptors()}
    assert {DATA_QUERY, DOC_RETRIEVE} <= catalog

    state = _state()
    rejection = _rejection(_run(state, _emission([_data_match(tool="sql_exec")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_ENUM_OUT_OF_RANGE]
    assert rejection.reasons[0].reason == ("matches s1 chain/tool 不一致（data 链须配 data_query）")

    assert "semantic_query" in catalog
    state = _state()
    rejection = _rejection(_run(state, _emission([_data_match(tool="semantic_query")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_ENUM_OUT_OF_RANGE]
    assert rejection.reasons[0].reason == ("matches s1 chain/tool 不一致（data 链须配 data_query）")

    state = _state()
    plan = _plan(_run(state, _emission([_data_match()]))[0])
    assert plan.matches[0].tool == DATA_QUERY
    assert plan.matches[0].tool in catalog


# ── 行 4：按链必填 ────────────────────────────────────────────────────────────


def test_required_by_chain() -> None:
    """行 4｜`chain="data"` 缺 `plan`／`chain="knowledge"` 缺 `retrieval_need` → 判失败。"""
    body = _data_match()
    del body["plan"]
    rejection = _rejection(_run(_state(), _emission([body]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
    assert rejection.reasons[0].reason == ("matches s1 data 链缺 plan（data_query 计划草案对象）")

    body = _knowledge_match()
    del body["retrieval_need"]
    rejection = _rejection(_run(_state(), _emission([body]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
    assert rejection.reasons[0].reason == ("matches s1 knowledge 链缺 retrieval_need（参数对象）")

    rejection = _rejection(_run(_state(), _emission([_knowledge_match(retrieval_need={})]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
    assert rejection.reasons[0].reason == "matches s1 retrieval_need 缺 question（必填非空）"


# ── 行 5：metric_slot 空／英文列名形 ───────────────────────────────────────────


def test_metric_slot_not_english_column() -> None:
    """行 5｜`metric_slot` 为空或呈英文列名形态 → 判失败。

    判定形（Owner 2026-10-15 拍板 B 案，行为 4）：值整体呈 ASCII 标识符形——首字符
    `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬。**只判形状、不判语义**。
    """
    rejection = _rejection(
        _run(_state(), _emission([_data_match(plan={"metric_slot": "", "ranking": False})]))[0]
    )
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
    assert rejection.reasons[0].reason == "matches s1 plan 缺 metric_slot（必填非空）"

    for column_form in ("oil_pressure", "WELL_NAME", "a1_b", "x"):
        state = _state()
        rejection = _rejection(
            _run(
                state,
                _emission([_data_match(plan={"metric_slot": column_form, "ranking": False})]),
            )[0]
        )
        assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
        assert "metric_slot" in rejection.reasons[0].reason
        assert column_form in rejection.reasons[0].reason

    # 非 ASCII 标识符形（现行口径名／数值打头／下划线打头）放行——只咬形态、不咬语义
    for slot in ("日产油量", "1.3 节含水率", "_oil"):
        state = _state()
        plan = _plan(
            _run(
                state,
                _emission([_data_match(plan={"metric_slot": slot, "ranking": False})]),
            )[0]
        )
        assert plan.matches[0].plan is not None
        assert plan.matches[0].plan["metric_slot"] == slot


# ── 行 6：ranking 与 direction 同现 ───────────────────────────────────────────


def test_ranking_direction_paired() -> None:
    """行 6｜`ranking` 必填布尔且与 `direction` 同现（行为 4；逐字稿 `walk/11` §一）。"""
    for plan in (
        {"metric_slot": "日产油量"},
        {"metric_slot": "日产油量", "ranking": "true"},
        {"metric_slot": "日产油量", "ranking": True},
    ):
        rejection = _rejection(_run(_state(), _emission([_data_match(plan=plan)]))[0])
        assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
        assert "ranking" in rejection.reasons[0].reason

    for plan in (
        {"metric_slot": "日产油量", "ranking": False},
        {"metric_slot": "日产油量", "ranking": True, "direction": "desc"},
        {"metric_slot": "日产油量", "ranking": True, "direction": "asc"},
    ):
        result = _run(_state(), _emission([_data_match(plan=plan)]))[0]
        assert isinstance(result, ToolPlan), _show(result)


# ── 行 7：出数只认现行口径 ────────────────────────────────────────────────────


def test_legacy_name_normalized_before_query() -> None:
    """行 7｜旧名经账本归一后才出数（出数只认现行口径——行为 7）。

    本块零改写：`plan`／`caliber_key` 逐字段原样透传（送到查询引擎的就是模型用账本归一后的
    现行名）；alias↔canonical 的「结构映射」单点在 tools 面（本块不建第二份）。
    """
    plan_body = {"metric_slot": "日产液量", "ranking": False, "window_label": "近 30 天"}
    result = _plan(
        _run(
            _state(),
            _emission([_data_match(plan=plan_body, caliber_key="caliber-liquid")]),
        )[0]
    )
    assert result.matches[0].plan == plan_body  # 逐字段原样（零改写、零归一）
    assert result.matches[0].caliber_key == "caliber-liquid"

    # 结构映射单点在 tools 面（别名→规范名）——本块只承载结论
    facts = ledger_facts(
        {
            "metrics": [{"slot": "日产液量", "name": "日产液量", "binding_state": "bound"}],
            "aliases": {"日产液": "日产液量"},
        }
    )
    assert resolve_metric_slot(facts, "日产液") == "日产液量"

    source = _source_text()
    assert "normalize_metric_name" not in source
    assert "resolve_metric_slot" not in source


# ── 行 8：解析拒文 → 结构化拒因（消费方） ──────────────────────────────────────


def _parsing_group(*ids: str) -> QuestionGroup:
    return QuestionGroup(
        subtasks=tuple(
            Subtask(id=subtask_id, question=f"{subtask_id} 子问题原句", ledger_notes="注释")
            for subtask_id in ids
        )
    )


def test_parse_rejection_str_to_tool_match_rejection_consumer_side() -> None:
    """行 8｜parsing 的 `str` 拒文 → `ToolMatchRejection` 机械适配（行为 11）。

    机械适配两件：`str` **逐字**进 `reason` 字段（与解析块自己返回的那串逐字相等）＋映射拒因
    枚举；零语义判断、零改写。用例覆盖解析面各拒因家族（六类映射面）。
    """
    group = _parsing_group("s1", "s2")
    bodies: list[tuple[Any, str]] = [
        ("not-json", KIND_MALFORMED),
        (_emission([]), KIND_MISSING_SUBTASK),
        (_emission([_data_match("s1")]), KIND_MISSING_SUBTASK),
        (_emission([_data_match("s1"), _data_match("s1")]), KIND_DUPLICATE),
        (_emission([_data_match("s9")]), KIND_UNKNOWN_ID),
        (_emission(["支不是对象"]), KIND_MALFORMED),
        (_emission([{"id": "s1", "chain": DATA_CHAIN, "tool": DATA_QUERY}]), KIND_MISSING_REQUIRED),
        (_emission([_data_match("s1", tool="semantic_query")]), KIND_ENUM_OUT_OF_RANGE),
    ]
    seen: set[str] = set()
    for content, expected_kind in bodies:
        raw = parse_tool_match(content, group)
        assert isinstance(raw, str) and raw, "用例须先被解析块拒（本行口径）"
        state = _state(ids=("s1", "s2"))
        rejection = _rejection(_run(state, content)[0])
        assert len(rejection.reasons) == 1
        assert rejection.reasons[0].reason == raw  # 逐字进 reason 字段
        assert rejection.reasons[0].kind == expected_kind
        seen.add(rejection.reasons[0].kind)

    assert seen <= MATCH_REASON_KINDS
    assert len(seen) >= 5, f"映射面覆盖不足：{sorted(seen)}"


# ── 行 9：工具描述三件套（经 tools seam） ──────────────────────────────────────


def test_descriptor_covers_three_parts() -> None:
    """行 9｜每个工具 `description` 含「何时用／不能做什么／参数示例」三项（经 tools seam 测）。"""
    descriptors = _registry().descriptors()
    assert descriptors, "工具目录为空——seam 未接通"
    for descriptor in descriptors:
        for part in _THREE_PARTS:
            assert part in descriptor.description, f"{descriptor.name} 描述缺「{part}」"


# ── 行 10：程序只对账、不替模型选工具 ─────────────────────────────────────────


_BANNED_STR_METHODS = {
    "startswith",
    "endswith",
    "lower",
    "upper",
    "casefold",
    "split",
    "partition",
    "count",
}


def _sources() -> list[Path]:
    return sorted(_TOOL_MATCHING_DIR.glob("*.py"))


def _source_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _sources())


def _trees() -> list[tuple[Path, ast.Module]]:
    return [(path, ast.parse(path.read_text(encoding="utf-8"))) for path in _sources()]


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表形判据探测（字面集合含汉字串即词表形——伪造树可咬）。"""
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
    return violations


def _picked_tool_literals(tree: ast.Module) -> list[str]:
    """「程序替模型选工具」探测：`SubtaskMatch(...)` 调用把 `tool`／`chain` 写成字面量。"""
    picked: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "SubtaskMatch"
        ):
            for keyword in node.keywords:
                if keyword.arg in ("tool", "chain") and isinstance(keyword.value, ast.Constant):
                    picked.append(f"L{node.lineno} 字面选择 {keyword.arg}")
    return picked


def test_no_lexicon_or_regex_in_tool_matching() -> None:
    """行 10｜程序只对账、不替模型选工具（AST 扫描本模块；豁免面＝结构归一／形态处理）。"""
    trees = _trees()
    assert trees, "扫描面为空"
    for path, tree in trees:
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "re" not in imported and "regex" not in imported, f"{path.name} 引入正则面"
        assert not any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "re"
            for node in ast.walk(tree)
        ), f"{path.name} 使用 re.*"
        assert _lexicon_violations(tree) == [], f"{path.name}: {_lexicon_violations(tree)}"
        assert _picked_tool_literals(tree) == [], f"{path.name}: {_picked_tool_literals(tree)}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in _BANNED_STR_METHODS, (
                    f"{path.name}:{node.lineno} 词面判方法 {node.func.attr}"
                )

    # 拒因映射表＝逐字稿派生（键是解析面拒文原句的子串），不是自撰词表
    carriers = (
        _V1_SUBTASK.read_text(encoding="utf-8"),
        _PARSING_PARSERS.read_text(encoding="utf-8"),
    )
    marks = dict(tool_matching.REJECTION_KIND_BY_MARK)
    assert marks, "拒因映射表为空"
    for mark in marks:
        assert any(mark in carrier for carrier in carriers), f"映射键自撰：{mark!r}"
        assert marks[mark] in MATCH_REASON_KINDS

    # 探测器非空转：伪造词表／字面择器即被咬
    assert _lexicon_violations(ast.parse('WORDS = ["提及", "执行"]\n')) != []
    assert (
        _picked_tool_literals(ast.parse('SubtaskMatch(id="s1", tool="data_query", chain="data")\n'))
        != []
    )


# ── 行 11：机读信号（step payload ＋ notice） ──────────────────────────────────


def test_rejection_signal_present() -> None:
    """行 11｜失败与拒因的机读信号在场：step payload 拒因字段 ＋ notice（类型取自事件闭世界）。"""
    from appv2.runtimev2.transport import NOTICE_TYPES

    state = _state(ids=("s1", "s2"))
    rejection = _rejection(_run(state, _emission([_data_match("s1")]))[0])

    steps = [step for step in state.steps if isinstance(step, Mapping)]
    payloads = [
        step["payload"]
        for step in steps
        if isinstance(step.get("payload"), Mapping) and step["payload"].get("phase") == "toolmatch"
    ]
    assert payloads, "拒因步 payload 缺（机读信号不在场）"
    rejection_payload = payloads[-1]["rejection"]
    assert rejection_payload["kind"] == rejection.reasons[0].kind
    assert rejection_payload["reason"] == rejection.reasons[0].reason
    assert [step["status"] for step in steps].count("failed") == 1
    # 同一次调用的步记录不重复记（模型调用步由 bookkeeping.call_model 单点记账）
    assert len(steps) == 2, [step.get("title") for step in steps]

    assert state.notices, "notice 缺（机读信号不在场）"
    last = state.notices[-1]
    assert last["type"] in NOTICE_TYPES
    assert last["type"] == "decision_rejected"
    assert rejection.reasons[0].reason in last["content"]

    # 成功路径：零补记步（唯一一条＝call_model 的模型调用步）
    state = _state()
    _plan(_run(state, _emission([_data_match()]))[0])
    assert len(state.steps) == 1
    assert state.steps[0]["manifest"] is not None


# ── 行 12：【边界集】枚举越界 ──────────────────────────────────────────────────


def test_boundary_enum_out_of_range() -> None:
    """行 12｜【边界集】`chain`／`direction` 越界取值 → 判失败（拒文逐字）。"""
    body = _data_match()
    body["chain"] = "tabular"
    rejection = _rejection(_run(_state(), _emission([body]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_ENUM_OUT_OF_RANGE]
    assert rejection.reasons[0].reason == "matches s1 chain 越界（data/knowledge）：'tabular'"

    rejection = _rejection(
        _run(
            _state(),
            _emission(
                [_data_match(plan={"metric_slot": "日产油量", "ranking": True, "direction": "up"})]
            ),
        )[0]
    )
    assert [reason.kind for reason in rejection.reasons] == [KIND_ENUM_OUT_OF_RANGE]
    assert "direction" in rejection.reasons[0].reason
    assert "up" in rejection.reasons[0].reason

    assert DIRECTIONS == frozenset({"asc", "desc"})


# ── 行 13：【保留集】名归一闸行为不变 ──────────────────────────────────────────


def test_retention_normalize() -> None:
    """行 13｜【保留集】名归一闸行为不变（本块只消费、不复制）。

    归一与扫描单点＝tools 面（`normalize_metric_name`／`resolve_metric_slot`——删装饰符号＋
    token 包含匹配，V2-41／A-P3b-44）；本块零归一实现（行 10 的扫描面另钉一次）。
    """
    assert normalize_metric_name("☆注采比 β") == "注采比 β"
    assert normalize_metric_name("★产量完成率") == "产量完成率"
    assert normalize_metric_name("  A  B ") == "a b"

    facts = ledger_facts(
        {
            "metrics": [{"slot": "注采比", "name": "注采比", "binding_state": "bound"}],
            "aliases": {"注入采出比": "注采比"},
        }
    )
    assert resolve_metric_slot(facts, "注采比") == "注采比"  # 精确段
    assert resolve_metric_slot(facts, "注入采出比") == "注采比"  # 别名段
    assert resolve_metric_slot(facts, "不在台账") is None  # 全未命中不猜

    # 名归一段：删装饰符号＋token 包含匹配（查询 token 集 ⊆ 台账名 token 集即命中）
    decorated = ledger_facts(
        {"metrics": [{"slot": "☆注采比 β", "name": "☆注采比 β", "binding_state": "bound"}]}
    )
    assert resolve_metric_slot(decorated, "注采比") == "☆注采比 β"

    assert "def normalize_metric_name" not in _source_text()


# ── 行 14：【保留集】聚合下推行为不变 ──────────────────────────────────────────


def test_retention_pushdown() -> None:
    """行 14｜【保留集】聚合下推行为不变（归属 `execution`）——本块只搬运、不改写。

    聚合下推的实现（整窗 SUM 库内算）在查询引擎／`execution` 面；本块**零聚合逻辑**，
    `plan` 逐字段原样进下游，且对账面仍认得该字段（不因重写而丢）。
    """
    plan_body = {
        "metric_slot": "日产油量",
        "ranking": False,
        "aggregate": True,
        "window_label": "近 30 天",
    }
    result = _plan(_run(_state(), _emission([_data_match(plan=plan_body)]))[0])
    assert result.matches[0].plan == plan_body
    assert result.matches[0].plan["aggregate"] is True

    schema = next(
        descriptor.args_schema
        for descriptor in _registry().descriptors()
        if descriptor.name == DATA_QUERY
    )
    assert "aggregate" in schema["properties"]["plan_draft"]["properties"]

    assert "sum(" not in _source_text().lower()


# ── 行 15：mention_mode 闭世界 ────────────────────────────────────────────────


def test_mention_mode_closed_world() -> None:
    """行 15｜`SubtaskMatch.mention_mode` 取值闭世界（`executed`／`mentioned_only`）越界即拒。

    越界取值与缺该字段都判失败（不猜、不取默认——规格 `:75`）——**把守面＝消费方对账**
    （`_violation_of`，见上两支）；形状类纯装载（P-05 单点归位，2026-10-16）。
    """
    assert MENTION_MODES == frozenset({MENTION_EXECUTED, MENTION_MENTIONED_ONLY})

    rejection = _rejection(_run(_state(), _emission([_data_match(mention_mode="maybe")]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_ENUM_OUT_OF_RANGE]
    assert "mention_mode" in rejection.reasons[0].reason
    assert "maybe" in rejection.reasons[0].reason

    body = _data_match()
    del body["mention_mode"]
    rejection = _rejection(_run(_state(), _emission([body]))[0])
    assert [reason.kind for reason in rejection.reasons] == [KIND_MISSING_REQUIRED]
    assert "mention_mode" in rejection.reasons[0].reason

    for value in (MENTION_EXECUTED, MENTION_MENTIONED_ONLY):
        plan = _plan(_run(_state(), _emission([_data_match(mention_mode=value)]))[0])
        assert plan.matches[0].mention_mode == value

    # 形状单点归位（P-05）：本块导出的 `SubtaskMatch` 即 `parsing` 的物理定义点（消费面不重定义，
    # `specs/parsing.md` 行为 12）——类体只定形状、零自查，越界把守全在消费面对账（上两支）。
    assert SubtaskMatch.__module__ == "appv2.runtimev2.parsing.models"
    assert "mention_mode" in SubtaskMatch.__dataclass_fields__


# ── pin-31：判断产出面（与 caliber_key 同批产出） ──────────────────────────────


def test_pin31_mention_mode_produced_with_caliber_key() -> None:
    """pin-31 判断产出面｜「提及 vs 执行」结论与 `caliber_key` 由模型在配工具那次调用**同批产出**。

    分派面不在本块（挂 `preconditions` 判定序第 1 位）——本块只保证两个结论随本次 `ToolPlan`
    一起产出且互不丢。
    """
    state = _state(ids=("s1", "s2"))
    plan, scripted = _run(
        state,
        _emission(
            [
                _data_match("s1", mention_mode=MENTION_MENTIONED_ONLY, caliber_key="old-name"),
                _data_match("s2", mention_mode=MENTION_EXECUTED, caliber_key="canonical"),
            ]
        ),
    )
    assert [(item.mention_mode, item.caliber_key) for item in _plan(plan).matches] == [
        (MENTION_MENTIONED_ONLY, "old-name"),
        (MENTION_EXECUTED, "canonical"),
    ]
    assert [caller for caller, _messages in scripted.calls] == ["decision"]


# ── 「无旁路」＋公开面＋链面 ──────────────────────────────────────────────────


def test_no_bypass_model_call_single_point() -> None:
    """「无旁路」行为断言：模型调用只经 `bookkeeping.call_model`（单点发起，R7 出口面）。

    两证：① 跑完后状态里恰一条带 Manifest 的调用步（该步只由 `call_model` 记）；
    ② 本块源码零直引模型出口（`gateway_adapter`／`appv2.infra.llm_client`）。
    """
    state = _state()
    _plan(_run(state, _emission([_data_match()]))[0])
    manifests = [step for step in state.steps if step["manifest"] is not None]
    assert len(manifests) == 1
    assert manifests[0]["payload"]["caller"] == "decision"
    assert manifests[0]["payload"]["run_id"] == state.run_id

    for path, tree in _trees():
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        for module in imported:
            assert not module.startswith("appv2.runtimev2.gateway_adapter"), path.name
            assert not module.startswith("appv2.infra.llm_client"), path.name


def test_public_surface_single_entry() -> None:
    """公开面＝规格「接口定义」节名单＋闭世界常量；相位单入口 `match`。"""
    assert callable(match)
    assert match.__module__ == "appv2.runtimev2.tool_matching.matching"
    expected = {
        "DATA_CHAIN",
        "DIRECTIONS",
        "KIND_DUPLICATE",
        "KIND_ENUM_OUT_OF_RANGE",
        "KIND_MALFORMED",
        "KIND_MISSING_REQUIRED",
        "KIND_MISSING_SUBTASK",
        "KIND_UNKNOWN_ID",
        "KNOWLEDGE_CHAIN",
        "MATCH_REASON_KINDS",
        "MENTION_EXECUTED",
        "MENTION_MODES",
        "MENTION_MENTIONED_ONLY",
        "MODEL_CALLER",
        "PHASE",
        "REJECTION_KIND_BY_MARK",
        "MatchReason",
        "RetrievalNeed",
        "SubtaskMatch",
        "ToolMatchRejection",
        "ToolPlan",
        "match",
    }
    assert set(tool_matching.__all__) == expected


def test_round_chain_append_only_and_contract_once() -> None:
    """链尾只追加（pin-22）＋相位合同一次性（pin-24）：首入包一次、回炉只追加增量条。"""
    state = _state()
    _plan(_run(state, _emission([_data_match()]))[0])
    assert [message["role"] for message in state.messages] == ["user", "assistant"]
    assert state.contracts_appended == ["toolmatch"]
    head = list(state.messages)

    state.decision_error = "上次拒因"
    _rejection(_run(state, _emission([_data_match("s9")]))[0])
    assert state.messages[: len(head)] == head  # 前缀单增不改写
    assert len(state.messages) == len(head) + 2
    assert state.contracts_appended == ["toolmatch"]  # 幂等：合同不重发
    assert "上次拒因" not in state.messages[0]["content"]  # 首入包不重发
    assert "上次拒因" in state.messages[2]["content"]  # 增量条携拒因回喂行


def test_no_limit_literals_only_sources_cited() -> None:
    """限额数值零字面量（「与闸的挂钩表」限额行）：只引真源双指，本块不自立上限。

    行为 9 的取舍＝熔断暂不加（靠轮数闸兜底）——判定与计数归 `state`／`orchestration`，本块
    **不计数、不判轮**；源码零上限常量、零「与整数比较」的裸上限形，且真源双指在场。
    """
    source = _source_text()
    assert "R-K-72" in source and "§06-A" in source, "限额真源双指指针不在场"

    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                assert not any(
                    key in node.targets[0].id.upper()
                    for key in ("MAX", "MIN", "CAP", "LIMIT", "ROUNDS", "BUDGET")
                ), f"{path.name}:{node.lineno} 自立上限常量 {node.targets[0].id}"
            if isinstance(node, ast.Compare):
                for operand in (node.left, *node.comparators):
                    is_number = (
                        isinstance(operand, ast.Constant)
                        and isinstance(operand.value, (int, float))
                        and not isinstance(operand.value, bool)
                    )
                    assert not is_number, f"{path.name}:{node.lineno} 裸限额字面比较"


def test_no_direct_state_write_in_tool_matching() -> None:
    """相位不直写状态（唯一写口归 `bookkeeping`）：本块源码零 `state.<字段>` 赋值。"""
    for path, tree in _trees():
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            for target in targets:
                assert not (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "state"
                ), f"{path.name}:{node.lineno} 直写状态"
