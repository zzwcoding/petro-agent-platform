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
from datetime import date
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.tool_matching as tool_matching
from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
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
    ToolContext,
    ToolRegistry,
    dump_from_store,
    ledger_facts,
    normalize_metric_name,
    resolve_metric_slot,
)

# 台账投影真源同产线一路（快照→读面→dump_from_store——V2-82c 术语锚扩展的 dump 源）。
LEDGER_DUMP = dump_from_store(
    InMemoryKnowledgeStore(question_array_snapshot(), today=date(2026, 10, 8))
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
                "ledger_notes": f"{subtask_id}｜已绑定｜近 30 天",
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


# 本块自有的**唯一**上限类常量（`constants.RETRY_CAP_SAME_REJECTION`＝同形拒因熔断参数，行为 9，
# 2026-10-17 EB3 D4.3）。它不是轮上限：**轮上限值只归 `state.Budget`**（真源双指），本参数只判
# 「同形重试几次即熔断」——名单就此一项，多一个即 FAIL（防上限面悄悄再立第二套）。
_OWN_CAP_CONSTANTS = {"RETRY_CAP_SAME_REJECTION"}


def test_no_limit_literals_only_sources_cited() -> None:
    """限额数值零字面量（「与闸的挂钩表」限额行）：只引真源双指，本块不自立**轮**上限。

    行为 9（2026-10-17 EB3 D4.3 改判）：**轮**上限仍只引真源双指、本块零字面量；熔断是本块自持的
    **一个自有参数**（同形重试次数），故断言面＝「自有上限常量**恰** `_OWN_CAP_CONSTANTS`」＋
    「真源双指在场」＋「零『与整数比较』的裸限额形」。
    """
    source = _source_text()
    assert "R-K-72" in source and "§06-A" in source, "限额真源双指指针不在场"
    assert "非轮预算" in source, "自有熔断参数未与轮预算划界（行为 9 的口径说明不在场）"

    own_caps = {
        node.targets[0].id
        for _, tree in _trees()
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and any(
            key in node.targets[0].id.upper()
            for key in ("MAX", "MIN", "CAP", "LIMIT", "ROUNDS", "BUDGET")
        )
    }
    assert own_caps == _OWN_CAP_CONSTANTS, (
        f"本块自有的上限类常量面漂移（期望恰 {sorted(_OWN_CAP_CONSTANTS)}）：{sorted(own_caps)}"
    )

    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for operand in (node.left, *node.comparators):
                    is_number = (
                        isinstance(operand, ast.Constant)
                        and isinstance(operand.value, (int, float))
                        and not isinstance(operand.value, bool)
                    )
                    assert not is_number, f"{path.name}:{node.lineno} 裸限额字面比较"


# 共享写面七字段（真源＝`bookkeeping` 行为 1 的六字段＋行为 8 的合同标记字段；全局闸
# `test_v2_bookkeeping.py::no_direct_state_write_in_phases` 的扫描面即此七项）——本块**零写**。
_SHARED_WRITE_FIELDS = frozenset(
    {
        "messages",
        "steps",
        "process_notes",
        "notices",
        "dialogue",
        "next_intent",
        "contracts_appended",
    }
)
# 本块登记的直写例外（拒因回炉的轮计数与回喂面）——`bookkeeping` 包根**无**这两字段的写口，
# 同款直写先例＝澄清相位（`clarification/core.py::_record_rejection`）与执行相位
# （`execution/core.py` 的拒因回喂点）。例外须在 `specs/tool_matching.md` 审计节登记。
_STATE_WRITE_EXCEPTIONS = frozenset({"rounds", "decision_error"})
# 就地改列表的方法（写操作——`state.steps.append(...)` 形；同全局闸口径）。
_MUTATING_METHODS = frozenset(
    {
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "sort",
        "reverse",
        "update",
        "setdefault",
    }
)


def _state_field_of(node: ast.expr) -> str | None:
    """该表达式是否直指 `state.<字段>`（取下标形 `state.notices[0]` 的基座也算）。"""
    if isinstance(node, ast.Subscript):
        return _state_field_of(node.value)
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "state"
    ):
        return node.attr
    return None


def _state_write_targets(tree: ast.Module) -> list[tuple[int, str]]:
    """`state.<字段>` 写点（赋值三形＋`del`＋就地改列表调用＋下标写——同全局闸 `_write_sites`
    的写点形状面）。"""
    sites: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = list(node.targets)
        else:
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _MUTATING_METHODS
            ):
                field = _state_field_of(node.func.value)
                if field is not None:
                    sites.append((node.lineno, field))
            continue
        for target in targets:
            field = _state_field_of(target)
            if field is not None:
                sites.append((node.lineno, field))
    return sites


def test_no_direct_state_write_in_tool_matching() -> None:
    """相位不直写**共享写面七字段**（唯一写口归 `bookkeeping`）；两字段例外须逐条登记。

    口径（2026-10-17 EB3 D4.3）：本块零写七共享字段；**登记例外**＝`rounds`／`decision_error`
    ——拒因回炉的轮计数与回喂面，`bookkeeping` 包根无其写口，同款直写先例在澄清／执行两相位；
    全局闸的扫描面即七字段，两字段本不在其内。例外之外**任何** `state.<字段>` 直写即 FAIL。
    """
    seen: set[str] = set()
    for path, tree in _trees():
        for line, field in _state_write_targets(tree):
            seen.add(field)
            assert field in _STATE_WRITE_EXCEPTIONS, (
                f"{path.name}:{line} 直写状态字段 {field}（未登记例外——共享写面归簿记写口）"
            )
    assert seen.isdisjoint(_SHARED_WRITE_FIELDS), (
        f"直写共享写面七字段：{sorted(seen & _SHARED_WRITE_FIELDS)}"
    )

    # 探测器非空转：共享写面字段的直写必被咬（伪造写点）
    forged = ast.parse(
        "def _x(state):\n"
        "    state.notices.append({'type': 't'})\n"
        "    state.next_intent = 'answer'\n"
    )
    assert {field for _, field in _state_write_targets(forged)} == {"notices", "next_intent"}
    assert not {field for _, field in _state_write_targets(forged)} <= _STATE_WRITE_EXCEPTIONS


# ── 本批（L3-02 检索透传断点修复）：need 原样透传 ＋ 确定性锚注入 ─────────────────


def _knowledge_plan(need: Mapping[str, Any]) -> ToolPlan:
    return _plan(_run(_state(), _emission([_knowledge_match(retrieval_need=need)]))[0])


def test_retrieval_need_passthrough_keeps_family_hints() -> None:
    """病灶 A 主修：模型发的 `family_hints` 随定案载荷原样到达（旧实现只重建 question／
    anchors 两键）。

    证据源 `docs/runtime-refactor/ladder/L3/02-完井液在二开钻进段与三开-summary.md`：真机 02 号题
    模型发三键，引擎侧只剩两键（族配额退化成每族 1 席、gold 章被裁）。
    """
    match = _knowledge_plan(
        {
            "question": "W-111 井完井报告记载的投产初期日产油",
            "anchors": ["W-111"],
            "family_hints": ["completion"],
        }
    ).matches[0]
    assert match.retrieval_need == {
        "question": "W-111 井完井报告记载的投产初期日产油",
        "anchors": ["W-111"],
        "family_hints": ["completion"],
    }
    # 下投影面同源零漂移（`as_payload` 即 `state.tool_matches` 载荷形状）
    assert match.as_payload()["retrieval_need"] == match.retrieval_need


async def test_retrieval_need_reaches_engine_with_family_hints() -> None:
    """到达性（V2 侧·同 V1 `test_v2_react_loop.py:181` 断言形）：定案载荷逐字进 `doc_retrieve`
    args → 引擎侧 `RetrievalNeed` 收到族提示（旧实现在此为空——断裂指纹）。"""
    match = _knowledge_plan(
        {"question": "W-111 井完井报告记载的投产初期日产油", "family_hints": ["completion"]}
    ).matches[0]
    retrieval = FakeRetrievalEngine()
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(), query=FakeQueryEngine(), retrieval=retrieval
    )
    result = await registry.call(
        DOC_RETRIEVE,
        dict(match.retrieval_need or {}),
        ToolContext(actor="dev-user", budget=4),
    )
    assert result.status == "ok"
    assert retrieval.needs[0].family_hints == ("completion",)
    assert retrieval.needs[0].anchors == ("W-111",)  # 题面实体锚同路到达


def test_retrieval_need_anchors_only_legacy_form_unchanged() -> None:
    """旧形回归（anchors-only）：缺 `family_hints` 照旧通过——不拒、不造键、不加键。"""
    need = {"question": "报告所载内容问句（检索式）", "anchors": ["锚点词"]}
    assert _knowledge_plan(need).matches[0].retrieval_need == need


def test_deterministic_anchors_injected_and_never_overwritten() -> None:
    """修 2①：题面实体确定性补锚（模型不填也填）＋模型自填锚不被覆盖（注入项在前、去重续后）。"""
    filled = _knowledge_plan({"question": "渤中 34-5 油田三季度注采比是多少？"}).matches[0]
    assert filled.retrieval_need == {
        "question": "渤中 34-5 油田三季度注采比是多少？",
        "anchors": ["渤中34-5油田", "34-5"],
    }

    merged = _knowledge_plan(
        {"question": "W-11 井生产套管的尺寸与下深是多少？", "anchors": ["Y-21"]}
    ).matches[0]
    assert merged.retrieval_need["anchors"] == ["W-11", "Y-21"]

    dedup = _knowledge_plan(
        {"question": "W-11 井生产套管的尺寸与下深是多少？", "anchors": ["W-11"]}
    ).matches[0]
    assert dedup.retrieval_need["anchors"] == ["W-11"]


def test_deterministic_anchors_silent_on_entity_free_question() -> None:
    """修 2②：零实体题面零注入（不误伤半边）——模型锚原样在、无锚键＝空锚。"""
    kept = _knowledge_plan(
        {"question": "近 7 天各井日产液量是多少？", "anchors": ["日产液量"]}
    ).matches[0]
    assert kept.retrieval_need == {
        "question": "近 7 天各井日产液量是多少？",
        "anchors": ["日产液量"],
    }
    assert _knowledge_plan({"question": "完井液密度 二开 三开"}).matches[0].retrieval_need == {
        "question": "完井液密度 二开 三开",
        "anchors": [],
    }


def test_term_anchors_injected_from_ledger_dump() -> None:
    """V2-82c：`state.ledger_dump` 由本块下传入锚注入——题面命中台账术语/指标名即术语锚入载荷。

    同题两态对照：dump 缺位（未接线态）＝零扩展（既有语义逐字不变），dump 在场＝词条全部
    词面形续在实体锚后（术语加权入 `_keyword_leg` 查询文本，引擎侧零改动）。"""
    content = _emission(
        [_knowledge_match(retrieval_need={"question": "Y-41 井的检泵周期是多少天？"})]
    )
    unwired = _plan(_run(_state(), content)[0]).matches[0]
    assert unwired.retrieval_need["anchors"] == ["Y-41"]  # dump 缺位＝零扩展

    wired_state = _state()
    wired_state.ledger_dump = LEDGER_DUMP
    wired = _plan(_run(wired_state, content)[0]).matches[0]
    assert wired.retrieval_need["anchors"] == ["Y-41", "检泵周期"]


def test_anchor_injection_trace_in_determination_payload() -> None:
    """修 2③留痕：注入项随定案载荷承载（返回值 → `state.tool_matches` 执行输入面），模型原话零改写。

    成功路径**零补记步**（规格「不降级与静默禁令」旁注：信号由返回值承载，同 `caliber_key`
    口径）——注入留痕面＝定案载荷与模型原话可对照，不新增步／notice。
    """
    state = _state()
    content = _emission(
        [_knowledge_match(retrieval_need={"question": "W-11 井生产套管的尺寸与下深是多少？"})]
    )
    match = _plan(_run(state, content)[0]).matches[0]
    assert match.retrieval_need["anchors"] == ["W-11"]  # 定案载荷载注入项
    emitted = json.loads(state.messages[-1]["content"])["matches"][0]["retrieval_need"]
    assert emitted == {"question": "W-11 井生产套管的尺寸与下深是多少？"}  # 原话零改写＝可对照
    assert len(state.steps) == 1  # 唯一一条＝call_model 的模型调用步（零补记步）


# ── 行为 9（2026-10-17 EB3 D4.3）：同形拒因熔断 → 触界收敛 → 收敛让位形 ─────────────


_MALFORMED_EMISSION = "这不是 JSON 对象（无左花括号——只有解释文字）"


def _repeat(state: RunState, contents: Sequence[str]) -> tuple[list[Any], ScriptedCompleter]:
    """同面替身注入 → 逐轮调 `match`（每轮换一条剧本应答）→ 复位；返回（结果列，替身）。"""
    scripted = ScriptedCompleter({"decision": list(contents)})
    previous = set_completer(scripted)
    try:
        results = [match(state) for _ in contents]
    finally:
        set_completer(previous)
    return results, scripted


def _notice_types(state: RunState) -> list[str]:
    return [str(entry.get("type")) for entry in state.notices if isinstance(entry, Mapping)]


def test_same_shape_rejection_fuses_to_convergence_within_three_calls() -> None:
    """行为 9｜同形 malformed 连发 → 第 3 次熔断：模型调用恰 3、显式触界、收敛落地、非 failed。

    熔断判据＝同形拒因（`kind` ＋ 逐字拒文）既有次数 ≥ 2（`RETRY_CAP_SAME_REJECTION`）——
    故三次**逐字相同**的拒因即熔断；触界＝显式把 `rounds` 顶到 `Budget.rounds`（自环不经澄清
    入口，轮数闸原本到不了），落地六键全归 `bookkeeping.converge`。
    """
    state = _state()
    results, scripted = _repeat(state, [_MALFORMED_EMISSION] * 3)

    assert scripted.counts() == {"decision": 3}, "熔断前模型调用数须恰 3（第 3 次同形即熔断）"
    assert all(isinstance(result, ToolMatchRejection) for result in results)
    kinds = [result.reasons[0].kind for result in results]
    assert kinds == [KIND_MALFORMED] * 3, kinds

    # 显式触界：rounds 顶到预算，check_limits 的 rounds 键必命中
    assert state.rounds >= state.budget.rounds
    assert state.budget_hit == ["rounds"]  # 显式触界：唯一命中项＝轮数键
    assert state.status == "completed"  # 非 failed：收敛收口，不零交付
    assert state.next_intent == "answer"
    assert "budget_converged" in _notice_types(state)
    # 收敛注记的 gates 如实（命中项名＝state 侧七限额键名）
    converged = [
        entry for entry in state.notices if isinstance(entry, Mapping)
        and entry.get("type") == "budget_converged"
    ][-1]
    assert converged["gates"] == ["rounds"]
    # 熔断留痕：一条过程档案注记 ＋ 一条熔断步（拒因同源）
    assert any(
        isinstance(entry, Mapping) and "熔断" in str(entry.get("title"))
        for entry in state.process_notes
    )
    fuse_steps = [
        step
        for step in state.steps
        if isinstance(step, Mapping) and "熔断" in str(step.get("title"))
    ]
    assert len(fuse_steps) == 1
    assert fuse_steps[0]["status"] == "failed"
    assert fuse_steps[0]["payload"]["rejection"]["kind"] == KIND_MALFORMED


def test_converged_entry_yields_letgo_plan_without_model_call() -> None:
    """行为 9｜收敛让位形：触界后入口零模型调用、零定案（交下游「无支可执行 → 作答收口」）。"""
    state = _state()
    _repeat(state, [_MALFORMED_EMISSION] * 3)
    calls_before = len(state.steps)

    scripted = ScriptedCompleter({"decision": [_MALFORMED_EMISSION]})
    previous = set_completer(scripted)
    try:
        outcome = match(state)
    finally:
        set_completer(previous)

    assert isinstance(outcome, ToolPlan)
    assert outcome.converged is True
    assert outcome.matches == []
    assert scripted.calls == [], "收敛让位形不得再调模型"
    assert len(state.steps) == calls_before, "收敛让位形零补记步"
    assert all(step.get("title") != "工具匹配发射被拒" for step in state.steps)

    # 零依赖：让位形先于「取问题组」——上游缺组也不影响收口（fail-closed 只守正常路径）
    state.question_group = None
    assert match(state) == ToolPlan(matches=[], converged=True)
    assert scripted.calls == []


def test_rejection_history_feeds_decision_error_verbatim() -> None:
    """行为 9① ②｜占轮 ＋ 拒因回喂：逐字拒文落 `decision_error`（增量条渲染面）且逐轮回喂。"""
    state = _state()
    first = _rejection(_run(state, _emission([_data_match("s9")]))[0])
    assert state.rounds == 1, "拒因回炉须占一轮"
    assert state.decision_error == first.reasons[0].reason

    # 回炉轮：增量条携拒因回喂行（前缀延伸、不改写前文）
    head = list(state.messages)
    second = _rejection(_run(state, _MALFORMED_EMISSION)[0])
    assert state.rounds == 2, "两次拒因＝两轮"
    assert state.decision_error == second.reasons[0].reason  # 回喂面随轮更新
    assert state.messages[: len(head)] == head
    instruction = state.messages[-2]  # 本轮增量条（user）在模型应答（assistant）之前
    assert instruction["role"] == "user"
    assert first.reasons[0].reason in instruction["content"], "上一轮拒因未逐字回喂"


def test_distinct_shapes_do_not_fuse_before_cap() -> None:
    """行为 9｜异形拒因不提前熔断：两种形各一次＝未触界（首形再来一次才到阈值）。"""
    state = _state()
    results = [_rejection(_run(state, _emission([_data_match("s9")]))[0])]
    results.append(_rejection(_run(state, _MALFORMED_EMISSION)[0]))
    kinds = [item.reasons[0].kind for item in results]
    assert kinds == [KIND_UNKNOWN_ID, KIND_MALFORMED], kinds
    assert state.budget_hit == [], "异形两次未到同形阈值，不得提前熔断"
    assert state.status == "running"
    assert state.rounds == 2


def test_convergence_answer_carries_materials_and_zero_type_notice() -> None:
    """行为 9｜带材料收敛：已获材料逐条入收敛正文（同 `bookkeeping.converge` 单一材料面）。"""
    state = _state()
    state.observations = [
        {"seq": 1, "content": "井 A 检泵周期 412 天", "source_id": "material-1"},
        {"seq": 2, "content": "井 B 检泵周期 298 天", "source_id": "material-2"},
    ]
    _repeat(state, [_MALFORMED_EMISSION] * 3)
    assert state.answer.startswith("（预算触界收敛——rounds")
    assert "已取得材料 2 条" in state.answer
    assert "material-1" in state.answer and "material-2" in state.answer
    assert "井 A 检泵周期 412 天" in state.answer
    assert state.draft_kind == "direct"


def test_tool_plan_two_shapes_mutually_exclusive() -> None:
    """行为 9｜`ToolPlan` 两形互斥：定案非空／让位必空＋标记真（越界构造即拒）。"""
    assert ToolPlan(matches=[], converged=True).converged is True
    with pytest.raises(ValueError):
        ToolPlan(matches=[])
    with pytest.raises(ValueError):
        ToolPlan(
            matches=[
                SubtaskMatch(
                    id="s1",
                    tool="data_query",
                    chain=DATA_CHAIN,
                    plan={"metric_slot": "日产油量", "ranking": False},
                    retrieval_need=None,
                    caliber_key="",
                    mention_mode=MENTION_EXECUTED,
                )
            ],
            converged=True,
        )
