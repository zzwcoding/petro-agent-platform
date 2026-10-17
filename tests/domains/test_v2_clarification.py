"""clarification 块验收（`RT-W4-02a`：-A 半面 15 行 ＋ 本块三条 pin；`RT-W4-02b`：-B 半面 7 行）。

票面对象＝`specs/clarification.md`「验收测试」表逐行转抄（`#` 列保留规格表行序、不重编；测试
标识与规格列逐字一致）。-A 票 15 行＝行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20；
-B 票 7 行＝行序 7／8／9／10／15／21／22（反问卡生产簇：时机分派形／默认窗注记／口径歧义／
合并一卡；覆盖自证归模型；子问题无依赖；【边界集】【保留集】各一行）。

-B 半面的验收面＝**分派形**与**机读信号**，不是判断本身：时机三条（「能否确定／是否需反问」）与
覆盖自证均在模型侧产出（`walk/裁决表.md` 项目级裁决 #13），程序只按结论分派、只校格式——
故本票用例断言「问句原文零读点」「零自造反问」「零依赖字段」，不断言程序判语义。

测试网钉（本票 3 行，`specs/clarification.md` 挂钩表 :151–:153）：

- `pin-05`（P0）＝`finalize` 合法性闸：零实质观察（非 notice）不得判「材料足够」直答收口 →
  `::finalize_requires_substantive_observation`；
- `pin-15`（P1）＝连续澄清反问到顶 → 截断＋带已取得材料如实直答；挂起不计轮、恢复重置轮预算 →
  `::ask_cap_truncate_with_material` ＋ `::waiting_not_counted_resume_resets`；
- `pin-07`（P1）＝定稿打回理由三段带路（前置判定指路→空手清单→兜底 `doc_retrieve` 指引）→
  `::finalize_rejection_three_segment_guidance`。

Seam（卡面 Adapter）＝`gateway_adapter` 的剧本化 completer（`ScriptedCompleter`）经 `set_completer`
注入；模型调用一律经 `bookkeeping.call_model` 单点发起。
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import appv2.runtimev2.clarification.constants as clarification_constants
import appv2.runtimev2.prompts.decision_round as decision_round
from appv2.runtimev2.clarification import clarify
from appv2.runtimev2.clarification.constants import (
    GUIDANCE_FALLBACK,
    GUIDANCE_PRECONDITION,
    MAX_SUBTASKS,
    NO_LEDGER_HIT_ROW_SHELL,
    NO_MATERIAL_SHELL,
    NOTE_SLOT_NO_HIT,
    NOTICE_DECISION_NOTE,
    PAYLOAD_ASK_FRAME,
    PAYLOAD_CAPPED,
    PAYLOAD_REJECTION,
    PAYLOAD_RESUME,
    REASON_ACTION_OUT_OF_WORLD,
    REASON_CHAIN_OUT_OF_WORLD,
    REASON_CODES,
    REASON_FINALIZE_ZERO_OBSERVATION,
    REASON_LEDGER_NOTES_EMPTY,
    REASON_LEDGER_NOTES_SLOT_MISMATCH,
    REASON_NO_REDISCOVER,
    REASON_REJECTION_GUIDANCE,
    REASON_SCHEMA_INVALID,
    REASON_SUBTASK_COUNT_OUT_OF_RANGE,
    VOLATILE_KEYS,
)
from appv2.runtimev2.clarification.core import code_of_rejection
from appv2.runtimev2.clarification.guidance import rejection_guidance
from appv2.runtimev2.clarification.models import (
    ClarifyAsk,
    ClarifyFinal,
    ClarifyRejection,
)
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.parsing import (
    ClarifyEmission,
    Subtask,
    discover_fingerprint,
    parse_question_group,
)
from appv2.runtimev2.preconditions.constants import (
    NOTE_CHAIN_SWITCH_REENTRY as ENGINE_REENTRY_NOTE,
)
from appv2.runtimev2.prompts import (
    PHASE_CLARIFY,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    assemble_decision_increment,
    render_ledger_resident_block,
)
from appv2.runtimev2.state import (
    ASK_CAP,
    INTENT_ANSWER,
    INTENT_DECISION,
    INTENT_DISCOVER,
    INTENT_TOOLMATCH,
    MAX_DISCOVERS_PER_RUN,
    MAX_ROUNDS,
    Budget,
    RunState,
)
from appv2.tools import HIT_RULE_CHAIN_SWITCH, HIT_RULE_UNREGISTERED_METRIC

# ══════════════════════════════════════════════════════════════════════════════
# fixture 与探测器（状态投影／发射文本／剧本化 completer／源码扫描）
# ══════════════════════════════════════════════════════════════════════════════

_CLARIFY_DIR = Path(clarification_constants.__file__).parent

# 台账条目原文（注入块渲染的源面——`ledger_notes` 段一「槽位」取自投影结构名的同源面）
_METRIC_VALUE = "产液量：日井口产液量，单位立方米，属日度生产指标"
_METRIC_ROW: dict[str, Any] = {
    "slot": "产液量",
    "name": "产液量",
    "binding_state": "bound",
    "calibers": [],
    "default_caliber": None,
    "value": _METRIC_VALUE,
    "source_id": "sem.metric.产液量",
    "version": "v1",
}
_TERM_ROW: dict[str, Any] = {
    "term": "日产液量",
    "banned": False,
    "freshness": "2026-10-01 有效",
    "value": "日产液量（2026-10-01 有效）",
    "source_id": "sem.term.日产液量",
}
_OBJECT_ROW: dict[str, Any] = {"obj": "A7 井", "value": "A7 井", "source_id": "sem.object.A7"}
# 真机台账对象名（`appv2/knowledge/snapshot.py` 对象行 10 条含「油田」——探针已核；N-01
# 真机形 `油田｜未绑定｜2026-09-16~2026-10-16` 的槽位面）
_OILFIELD_ROW: dict[str, Any] = {
    "obj": "油田",
    "value": "油田（草案）：§5 未列属性",
    "source_id": "sem.object.油田",
}
# 三段槽位对账合法形（形＝`槽位｜绑定态｜窗`；段一 ∈ 名录、段二 ∈ 闭世界、段三＝锚定窗）
_NOTE_SLOT = "产液量"
_NOTE = f"{_NOTE_SLOT}｜未绑定｜2026-09-16~2026-10-16"
_NOTE_WINDOW_UNRESOLVED = f"{_NOTE_SLOT}｜已绑定｜窗未定"


def _dump(
    *,
    metrics: Sequence[Mapping[str, Any]] | None = None,
    terms: Sequence[Mapping[str, Any]] | None = None,
    objects: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """台账投影 fixture（形＝`appv2/tools/ledger.py` dump schema 的渲染消费面）。"""
    metric_rows = (
        [dict(_METRIC_ROW)] if metrics is None else [dict(row) for row in metrics]
    )
    object_rows = (
        [dict(_OBJECT_ROW), dict(_OILFIELD_ROW)]
        if objects is None
        else [dict(row) for row in objects]
    )
    return {
        "metrics": metric_rows,
        "terms": [dict(row) for row in (terms or [])],
        "objects": object_rows,
        "relations": [],
        "families": [],
        "aliases": {},
        "families_map": {},
        "cards": [],
    }


def _state(**overrides: Any) -> RunState:
    fields: dict[str, Any] = {
        "run_id": "run-clarify-1",
        "question": "A7 井近三天的产液量是多少？",
        "understanding": "问 A7 井近三天产液量",
        "ledger_dump": _dump(),
    }
    fields.update(overrides)
    return RunState(**fields)


def _real_ledger_dump() -> dict[str, Any]:
    """真机台账投影（问数组台账态快照——同名录用例的机取源；非 fixture 自证面）。"""
    from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
    from appv2.tools.ledger import dump_from_store

    return dict(dump_from_store(InMemoryKnowledgeStore(question_array_snapshot())))


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _subtask(
    sid: str = "s1",
    *,
    ledger_notes: str = _NOTE,
    chain: str = "data",
    question: str = "查 A7 井近三天产液量",
) -> dict[str, Any]:
    return {"id": sid, "question": question, "ledger_notes": ledger_notes, "chain": chain}


def _decompose(*subtasks: Mapping[str, Any]) -> str:
    rows = [dict(subtask) for subtask in subtasks]
    return _json({"action": "decompose", "question_group": {"subtasks": rows}})


def _ask(
    prompt: str = "「正常」想跟哪个标准比？",
    options: Sequence[str] = ("对比计划产量", "对比上月同期"),
) -> str:
    return _json({"action": "ask", "ask": {"prompt": prompt, "options": list(options)}})


def _discover(tool: str = "semantic_query", args: Mapping[str, Any] | None = None) -> str:
    branch = {"tool": tool, "args": dict(args or {"text": "产液量"})}
    return _json({"action": "discover", "discovers": [branch]})


def _finalize() -> str:
    return _json({"action": "finalize"})


def _material_observation(content: str = "A7 井 2026-10-14 产液量 120 立方米") -> dict[str, Any]:
    """实质观察（台账条目卡／检索片段形；`locator.kind` 非 notice）。"""
    return {
        "content": content,
        "source": "台账",
        "source_id": "sem.metric.产液量",
        "locator": {"kind": "ledger"},
    }


def _notice_observation() -> dict[str, Any]:
    """空手探查的未命中通知观察（**不算实质材料**——finalize 闸的过滤面）。"""
    return {
        "content": "未命中台账条目",
        "source": "库",
        "locator": {"kind": "notice", "notice_type": "no_hit"},
    }


@contextmanager
def _scripted(*replies: str) -> Iterator[ScriptedCompleter]:
    """剧本化 completer 注入（`decision` 桶——本相位唯一模型调用桶）。"""
    completer = ScriptedCompleter({"decision": list(replies)})
    previous = set_completer(completer)
    try:
        yield completer
    finally:
        set_completer(previous)


def _parse(content: str, *, state: RunState | None = None) -> ClarifyEmission | str:
    """相位同参注入面（隔离对读件：解析拒文逐字比对用）。"""
    probe = state if state is not None else _state()
    return parse_question_group(
        content,
        max_discovers=int(probe.budget.discovers_per_round),
        discover_budget_left=int(probe.budget.discovers_per_run) - int(probe.discover_used),
        max_subtasks=MAX_SUBTASKS,
    )


def _step_payloads(state: RunState) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []
    for step in state.steps:
        payload = step.get("payload")
        if isinstance(payload, Mapping):
            payloads.append(payload)
    return payloads


def _last_step_payload(state: RunState) -> Mapping[str, Any]:
    return _step_payloads(state)[-1]


def _resume_readings(state: RunState) -> Mapping[str, Any]:
    """恢复支落的易变量读数（行为 13 的机读信号面）。"""
    for payload in _step_payloads(state):
        if PAYLOAD_RESUME in payload:
            readings = payload.get("volatile")
            assert isinstance(readings, Mapping), payload
            return readings
    raise AssertionError("恢复支未落易变量读数——行为 13 的重取面无机读信号")


def _clarification_sources() -> list[tuple[Path, ast.Module]]:
    """本块全部源码树（元面断言的扫描面）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_CLARIFY_DIR.glob("*.py"))
    ]


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


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


def _wordface_calls(tree: ast.Module) -> list[str]:
    """词面判方法调用（前缀／后缀／大小写折叠／切分／计数）——词表形判据探测器。"""
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _BANNED_STR_METHODS:
                found.append(f"L{node.lineno} {node.func.attr}")
    return found


def _cjk_membership_judgements(tree: ast.Module) -> list[str]:
    """汉字串成员判据（`x in "提及执行"` 形）——语义词表探测器。"""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if not any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops):
            continue
        for operand in (node.left, *node.comparators):
            if (
                isinstance(operand, ast.Constant)
                and isinstance(operand.value, str)
                and _has_cjk(operand.value)
            ):
                found.append(f"L{node.lineno} 汉字串成员判据")
    return found


def _cjk_collection_literals(tree: ast.Module) -> list[str]:
    """汉字串集合字面量（词表形）——逻辑面零字面表（表只在常量单点）。"""
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        for item in node.elts:
            if (
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and _has_cjk(item.value)
            ):
                found.append(f"L{node.lineno} 字面集合含汉字串")
    return found


def _limit_literal_hits(tree: ast.Module, banned: frozenset[int]) -> dict[int, tuple[int, ...]]:
    """裸限额字面探测器（整数常量 ∈ 限额数值集——限额数值零复制的机检面）。"""
    found: dict[int, tuple[int, ...]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if not isinstance(node.value, bool) and node.value in banned:
                found.setdefault(node.lineno, ())
                found[node.lineno] = (*found[node.lineno], node.value)
    return found


_LIMIT_VALUES = frozenset({MAX_ROUNDS, MAX_DISCOVERS_PER_RUN, ASK_CAP})


def _module_level_definitions(tree: ast.Module, name: str) -> int:
    """模块级赋值定义点计数（单点断言用）。"""
    total = 0
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            total += 1
    return total


# ══════════════════════════════════════════════════════════════════════════════
# 票面对象 15 行（规格表行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20）
# ══════════════════════════════════════════════════════════════════════════════


def test_emission_action_closed_world() -> None:
    """#1｜动作越界 → 判失败（不猜、不取默认）——`specs/clarification.md:108`。"""
    state = _state()
    with _scripted(_json({"action": "execute", "tool": "data_query"})) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyRejection)
    assert [reason.code for reason in outcome.reasons] == [REASON_ACTION_OUT_OF_WORLD]
    reason = outcome.reasons[0].reason
    assert reason.startswith("action 缺失或越界")  # 解析面机器拒文（`str` 逐字承载）
    # 不猜、不取默认：无定案、无挂起、未路由出去；拒因回喂面在场（回本相位重决策）
    assert state.question_group is None
    assert state.pending_ask is None
    assert state.next_intent == INTENT_DECISION
    assert state.decision_error == reason
    assert len(completer.calls) == 1


def test_ledger_notes_required_with_reject_feedback() -> None:
    """#2｜`ledger_notes` 为空 → 判失败并带拒因回喂（不自动修补）——`specs/clarification.md:109`。"""
    state = _state()
    with _scripted(_decompose(_subtask(ledger_notes=""))) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyRejection)
    assert [reason.code for reason in outcome.reasons] == [REASON_LEDGER_NOTES_EMPTY]
    reason = outcome.reasons[0].reason
    assert reason.startswith("subtasks s1 缺 ledger_notes")
    assert _last_step_payload(state)[PAYLOAD_REJECTION] == reason
    assert state.decision_error == reason  # 回喂面（增量条「上次发射被拒」渲染源）
    assert state.question_group is None  # 不自动修补
    assert len(completer.calls) == 1


def test_subtask_cap_from_budget_table(monkeypatch: Any) -> None:
    """#3｜子问题条数越界 → 判失败（上限取限额真源双指；条数键数值真源 `walk/09` §七 Q-C）。

    真源面：`recon/K-上下文事件指南预算.md` R-K-72…R-K-78 ＋ `walk/裁决表.md` §06-A 两源
    **均未单列条数键**，故数值真源＝`docs/runtime-refactor/walk/09-澄清-分解问题.md` §七 Q-C
    （`state` 承载键未落定——`specs/parsing.md` 风险 7⑤）；本块为该值的**注入方单点**。
    """
    assert MAX_SUBTASKS == 4  # 真源 walk/09 §七 Q-C 的口径值（对读件）

    at_cap = [_subtask(f"s{i}") for i in range(1, MAX_SUBTASKS + 1)]
    state = _state()
    with _scripted(_decompose(*at_cap)):
        assert isinstance(clarify(state), ClarifyFinal)
    assert isinstance(state.question_group, Mapping)
    assert len(state.question_group["subtasks"]) == MAX_SUBTASKS

    over_cap = [_subtask(f"s{i}") for i in range(1, MAX_SUBTASKS + 2)]
    state = _state()
    with _scripted(_decompose(*over_cap)):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyRejection)
    assert [reason.code for reason in outcome.reasons] == [REASON_SUBTASK_COUNT_OUT_OF_RANGE]
    assert "超出上限" in outcome.reasons[0].reason

    # 单点证明：改单点值 → 判据边界随之移动（上限不在分派逻辑里硬编码）
    monkeypatch.setattr(clarification_constants, "MAX_SUBTASKS", 1)
    state = _state()
    with _scripted(_decompose(_subtask("s1"), _subtask("s2"))):
        shifted = clarify(state)
    assert isinstance(shifted, ClarifyRejection)
    assert [reason.code for reason in shifted.reasons] == [REASON_SUBTASK_COUNT_OUT_OF_RANGE]

    # 限额数值零复制：本块源码不出现 `state` 侧限额键的数值（R-K-75／76／72 逐键对读）
    hits = {
        f"{path.name}:{line}": values
        for path, tree in _clarification_sources()
        if (found := _limit_literal_hits(tree, _LIMIT_VALUES))
        for line, values in found.items()
    }
    assert hits == {}, hits
    # 探测器非空转：伪造裸限额字面必被咬
    assert _limit_literal_hits(ast.parse(f"LIMIT = {ASK_CAP}\n"), _LIMIT_VALUES) == {1: (ASK_CAP,)}


def test_chain_enum_closed_world() -> None:
    """#4｜`chain` 越界值 → 判失败——`specs/clarification.md:111`。"""
    for chain in ("data", "knowledge"):
        state = _state()
        with _scripted(_decompose(_subtask(chain=chain))):
            outcome = clarify(state)
        assert isinstance(outcome, ClarifyFinal), chain
        assert isinstance(state.question_group, Mapping)
        assert state.question_group["subtasks"][0]["chain"] == chain

    state = _state()
    with _scripted(_decompose(_subtask(chain="sql"))):
        rejected = clarify(state)
    assert isinstance(rejected, ClarifyRejection)
    assert [reason.code for reason in rejected.reasons] == [REASON_CHAIN_OUT_OF_WORLD]
    assert "chain 越界" in rejected.reasons[0].reason


def test_finalize_requires_substantive_observation() -> None:
    """#5｜零实质观察（非 notice）→ 不得判「材料足够」直答收口（**钉 `pin-05`，P0**）——:112。

    钉本体（`eng/04a-应钉行为清单.md:14`）：「零实质观察（非 notice）时 decision 不得判
    「材料足够」直答收口」——本用例即该 P0 承重钉的机检面。
    """
    state = _state(observations=[_notice_observation()])
    with _scripted(_finalize()):
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyRejection)
    assert [reason.code for reason in outcome.reasons] == [
        REASON_FINALIZE_ZERO_OBSERVATION,
        REASON_REJECTION_GUIDANCE,
    ]
    assert outcome.reasons[0].reason == "零实质观察禁定稿"
    # 不得直答收口：直答三键零写、去向不是 answer、无挂起
    assert state.draft == ""
    assert state.draft_kind == ""
    assert state.next_intent == INTENT_DECISION
    assert state.pending_ask is None

    # 窗内非 notice 实质观察 ≥1 → 定案放行（去向 answer；起草归作答相位、本块零干预）
    passed = _state(observations=[_material_observation()])
    with _scripted(_finalize()):
        assert clarify(passed) is None
    assert passed.next_intent == INTENT_ANSWER
    assert passed.draft == ""


def test_finalize_rejection_three_segment_guidance() -> None:
    """#6｜`finalize` 被拒 → 拒因载荷带三段带路（**钉 `pin-07`，P1**）——:113。

    **V2-88 改判（A14）**：前置判定的投影形＝`preconditions.SubtaskVerdict.as_payload()` 五键
    （`subtask_id`／`decision`／`hit_rule`／`notes`／`reason`，**无 `state` 键**）；旧载荷
    `{"state": "blocked_refuse"}` 是生产中不存在的形状（死判据 ⇒ ①段恒缺席）。本测改真形：
    ①段判据＝`decision="refuse"` ∧ `reason.rule_id` ∈ 换链/未绑定闭世界。
    """
    fingerprint = discover_fingerprint("data_query", {"metric_slot": "产液量"})
    assert json.loads(fingerprint)["tool"] == "data_query"
    state = _state(
        observations=[_notice_observation()],
        precondition_verdicts=[
            {
                "subtask_id": "s1",
                "decision": "refuse",
                "hit_rule": HIT_RULE_CHAIN_SWITCH,
                "notes": [],
                "reason": {
                    "rule_id": HIT_RULE_CHAIN_SWITCH,
                    "human_text": "未绑定口径——agg 汇总层无承载列，不代答",
                    "alternatives": [],
                },
            }
        ],
        empty_probes=[fingerprint],
    )
    with _scripted(_finalize()) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyRejection)
    guidance = outcome.reasons[1]
    assert guidance.code == REASON_REJECTION_GUIDANCE
    expected = "；".join(
        [
            GUIDANCE_PRECONDITION,
            "已空手探查：data_query——禁再试同名同参",
            GUIDANCE_FALLBACK,
        ]
    )
    assert guidance.reason == expected
    # 三段可逐段定位（「；」连接成单段；段③兜底句恒在）
    assert "该指标材料走报告检索：分解时 chain=knowledge、tool=doc_retrieve" in guidance.reason
    assert "已空手探查：data_query——禁再试同名同参" in guidance.reason
    assert GUIDANCE_FALLBACK in guidance.reason
    assert "；" in guidance.reason and not guidance.reason.endswith("；")
    assert state.decision_error == "零实质观察禁定稿；" + expected  # 回喂单段文本
    assert len(completer.calls) == 1  # 零模型调用（带路由机器已知事实拼装）

    # 段缺则跳：无绑定拒、无空手探查 → 仅兜底句（无前导「；」）
    bare = _state(observations=[_notice_observation()])
    with _scripted(_finalize()):
        bare_outcome = clarify(bare)
    assert isinstance(bare_outcome, ClarifyRejection)
    assert bare_outcome.reasons[1].reason == GUIDANCE_FALLBACK


def test_guidance_triggers_on_structured_rule_id() -> None:
    """V2-88｜①段判据＝**结构化投影**（`decision`＋`reason.rule_id`），零文案子串。

    两面（主窗 2026-10-18 授权合流）：
    - `refuse` × 换链/未绑定闭世界两值（`chain_switch`／`unregistered_metric`）→ ①段在场；
    - `allow` × `notes` 含换链重入注记（换链**首次触发**＝放行＋注记＋新计点——B-正6 纯换链
      回炉的真实路径）→ ①段在场；
    - `allow` 无注记／`refuse` 其它 rule_id → 不在场（不误亮）。
    另钉验收 3 的源码面：`guidance.py` 不再消费生产中不存在的 `{"state":…}` 键。
    """
    def _verdict(
        decision: str,
        *,
        rule_id: str = "",
        notes: Sequence[str] = (),
        subtask_id: str = "s1",
    ) -> dict[str, Any]:
        return {
            "subtask_id": subtask_id,
            "decision": decision,
            "hit_rule": rule_id,
            "notes": list(notes),
            "reason": None
            if decision == "allow"
            else {
                "rule_id": rule_id,
                "human_text": "数据链无承载——如实拒",
                "alternatives": [],
            },
        }

    for rule_id in (HIT_RULE_CHAIN_SWITCH, HIT_RULE_UNREGISTERED_METRIC):
        state = _state(precondition_verdicts=[_verdict("refuse", rule_id=rule_id)])
        assert GUIDANCE_PRECONDITION in rejection_guidance(state)

    switched = _state(
        precondition_verdicts=[
            _verdict(
                "allow",
                notes=(
                    "「配产量」在册未绑定——agg 汇总层无承载列",
                    ENGINE_REENTRY_NOTE,
                ),
            )
        ]
    )
    assert GUIDANCE_PRECONDITION in rejection_guidance(switched)

    plain_allow = _state(
        precondition_verdicts=[_verdict("allow", notes=("单井过滤未支持——照常发射全井计划",))]
    )
    assert GUIDANCE_PRECONDITION not in rejection_guidance(plain_allow)

    other_rule = _state(precondition_verdicts=[_verdict("refuse", rule_id="ban")])
    assert GUIDANCE_PRECONDITION not in rejection_guidance(other_rule)

    # 值引用对账（R1 禁相位互 import ⇒ 两处各持值）：闭世界与注记以**真源**为锚，漂移即红
    assert clarification_constants.REROUTE_RULE_IDS == frozenset(
        {HIT_RULE_CHAIN_SWITCH, HIT_RULE_UNREGISTERED_METRIC}
    )
    assert clarification_constants.NOTE_CHAIN_SWITCH_REENTRY == ENGINE_REENTRY_NOTE
    assert frozenset(decision_round._REROUTE_RULE_IDS) == clarification_constants.REROUTE_RULE_IDS
    assert decision_round._NOTE_CHAIN_SWITCH_REENTRY == ENGINE_REENTRY_NOTE

    # 验收 3｜源码面：不再读 {"state":…} 键（结构化判据＝decision+reason.rule_id/notes）
    source = (_CLARIFY_DIR / "guidance.py").read_text(encoding="utf-8")
    assert '"state"' not in source and "'state'" not in source


def test_rework_line_matches_engine_reason() -> None:
    """V2-88｜词面触发兜底**对齐引擎原文**：拒因含「不在指标台账」→ 回炉行追加改道后缀。

    旧触发词 `("未绑定", "不在台账")` 与引擎拒因原文「…不在指标台账——…」不同族 ⇒ 子串校永不
    命中，回炉轮少了「该换 knowledge 链」这句路由动词。
    """
    state = _state(
        subtask_results=[
            {
                "id": "s2",
                "question": "各井日产液量",
                "status": "bad_args",
                "reason": (
                    "指标 '日产液量' 不在指标台账——确定性校验拒"
                    "（不在目录不代答；台账闭世界校验）"
                ),
            }
        ]
    )
    increment = assemble_decision_increment(state, phase=PHASE_CLARIFY)
    assert "- [s2] 各井日产液量——拒因：" in increment
    assert decision_round._REROUTE_SUFFIX in increment

    # 非同族词面 → 不追加（词面触发面不越界扩张）
    quiet = _state(
        subtask_results=[
            {
                "id": "s2",
                "question": "各井日产液量",
                "status": "retryable",
                "reason": "上游超时——可重试",
            }
        ]
    )
    quiet_increment = assemble_decision_increment(quiet, phase=PHASE_CLARIFY)
    assert decision_round._REROUTE_SUFFIX not in quiet_increment


def test_ledger_notes_slot_reconciliation() -> None:
    """#11｜台账注入块在场且注释过**三段槽位对账**（真机 N-01 形必过）——`clarification.md:119`。

    **改前改后对比（墙拆证明）**：旧判据＝「注释在注入块内逐字子串」（`note_text in block`）——
    真机台账行是 `指标｜★产量完成率：…（绑定态：unbound）` 长句形，模型照合同样例拼的
    `产量完成率｜未绑定｜2026-09-16~2026-10-16` **永远不是块内子串** → 旧判据必拒（真机 run
    run-0d2e0274／run-1f5792d8 各烧 2–3 轮）；新判据＝三段槽位对账（段一逐字 ∈ 台账名录／段二 ∈
    闭世界／段三＝合法窗形）→ 同一形必过、且台账行仍在**交付前**被对账（不放行杜撰名）。
    段一取自投影结构名（`metrics[].slot`——剥法纯名，与合同样例教的形同源），非块内行首串
    （行首是 `★产量完成率`，逐字取会连样例形一起拒——正是本改要拆的墙）；名录四类＝指标／对象／
    关系／**术语**（术语条亦台账条目行——2026-10-16 微批随真机形补入）。
    """
    state = _state()
    block = render_ledger_resident_block(state)
    assert block and RESIDENT_BLOCK_BEGIN in block and RESIDENT_BLOCK_END in block
    assert _METRIC_VALUE in block  # 台账条目逐字转抄（`specs/prompts.md` 行为 8）
    note = "油田｜未绑定｜2026-09-16~2026-10-16"  # 真机 N-01 形（槽位＝台账对象名）
    assert "油田（草案）：§5 未列属性" in block  # 槽位同名台账行在场（名录源面）
    assert note not in block  # 旧判据必拒形（墙：逐字子串求不得）

    with _scripted(_decompose(_subtask(ledger_notes=note))):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyFinal)  # 新判据放行（旧判据此处必拒）
    # 注入块随相位首入包进链（模型面可见＝对账前提）
    package = state.messages[0]
    assert package["role"] == "user"
    assert RESIDENT_BLOCK_BEGIN in package["content"]
    assert isinstance(state.question_group, Mapping)
    notes = [subtask["ledger_notes"] for subtask in state.question_group["subtasks"]]
    assert notes == [note]  # 逐字承接（程序零改写）
    # 段一逐字 ∈ 名录面（指标 slot／对象名／术语名）：唯一化的名三种写法
    for slot in (_NOTE_SLOT, "油田"):
        single = _state()
        with _scripted(_decompose(_subtask(ledger_notes=f"{slot}｜未绑定｜窗未定"))):
            assert isinstance(clarify(single), ClarifyFinal), slot
    # 术语名亦在名录（`_NAME_COLUMNS` 含 `terms[].term`——2026-10-16 微批）：块内 `术语｜…` 行
    # 与名录同源，术语作段一必过（旧名录无术语 = 白烧轮；真机日志有该形）
    term_name = str(_TERM_ROW["term"])
    term_state = _state(ledger_dump=_dump(terms=[_TERM_ROW]))
    assert f"术语｜{term_name}" in render_ledger_resident_block(term_state)
    with _scripted(_decompose(_subtask(ledger_notes=f"{term_name}｜未绑定｜窗未定"))):
        assert isinstance(clarify(term_state), ClarifyFinal)

    # 真机 ledger × 真机形（判据不依赖 fixture）：问数组台账态快照投影下，N-01 形同过；
    # 且「油田」真在真投影对象名录（2026-10-16 探针：`appv2/knowledge/snapshot.py` 对象行 4）
    real = _state(ledger_dump=_real_ledger_dump())
    assert "油田" in {row.get("obj") for row in real.ledger_dump["objects"]}
    with _scripted(_decompose(_subtask(ledger_notes=note))):
        assert isinstance(clarify(real), ClarifyFinal)


def test_waiting_not_counted_resume_resets() -> None:
    """#12｜挂起等待不计轮；`resume` 重置轮预算（**钉 `pin-15` 的挂起半面，P1**）——:119。"""
    state = _state(rounds=2)
    with _scripted(_ask()):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyAsk)
    assert outcome.kind == "clarify"
    assert state.rounds == 2  # 挂起不计轮
    assert state.pending_ask is not None

    choice = "对比计划产量"
    state.resume_choices = [
        {"kind": "clarify", "choice": choice, "decision": None, "approval_id": None}
    ]
    with _scripted(_ask("还想跟哪个标准比？", ("对比上月同期", "对比同类井平均"))):
        resumed = clarify(state)
    assert isinstance(resumed, ClarifyAsk)
    assert state.rounds == 0  # resume 重置轮预算
    assert state.pending_ask is not None  # 二次挂起（不静默放行）
    # 用户所选原话进对话链（去空白前缀）＋对话层来源闭世界（`clarify_approval_replay`）
    assert {"role": "user", "content": choice} in state.messages
    assert state.dialogue[-1] == {
        "role": "user",
        "content": choice,
        "origin": "clarify_approval_replay",
    }
    assert any(PAYLOAD_RESUME in payload for payload in _step_payloads(state))


def test_resume_reloads_volatile() -> None:
    """#13｜恢复时重取易变量（水位／新鲜度／地基）——`specs/clarification.md:120`。"""
    state = _state(ledger_dump=_dump(terms=[], objects=[]))
    state.pending_ask = {
        "kind": "clarify",
        "prompt": "「正常」想跟哪个标准比？",
        "options": ["对比计划产量", "对比上月同期"],
        "detail": None,
    }
    state.resume_choices = [{"kind": "clarify", "choice": "对比计划产量"}]
    # 等待期环境变了：台账加术语条、本体加对象、观察落库（挂起前的读数是全零）
    state.ledger_dump["terms"] = [dict(_TERM_ROW)]
    state.ledger_dump["objects"] = [dict(_OBJECT_ROW)]
    state.observations = [_material_observation()]

    with _scripted(_ask()):
        assert isinstance(clarify(state), ClarifyAsk)

    readings = _resume_readings(state)
    assert tuple(VOLATILE_KEYS) == ("watermark", "freshness", "foundation", "new_rows")
    assert sorted(readings) == sorted(VOLATILE_KEYS)  # 四键闭世界
    assert readings["new_rows"] == len(state.observations) == 1
    assert readings["foundation"] == 1  # 本体三块行数（等待期新增对象计入）
    assert readings["freshness"] == [_TERM_ROW["freshness"]]
    assert readings["watermark"] == ""  # 投影未携水位 → 如实空串（不编造）
    # 「重取」而非复用挂起前旧结论：读数与挂起前（零行）不同源
    assert dict(readings) != {"watermark": "", "freshness": [], "foundation": 0, "new_rows": 0}


def test_resume_volatile_watermark_carried_by_dump() -> None:
    """#13 补｜恢复路径水位非空＋roundtrip（dump 携数据面水位——顺带 bug 修复）。

    病灶：`tools.ledger.dump_from_store` 不产 `watermark` 键，而 `read_volatile`
    读 `dump["watermark"]` → 四易变量之一恒空串（「等待期环境是否失效」判据面失效）。
    修后＝生产 dump 由组合根经 water_line 水位注入该键；本测核「dump 携值 → 恢复
    路径读数逐字一致」＋「缺位仍如实空串」（旧检查点／未接线面不编造）。
    """
    from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
    from appv2.runtimev2.clarification.volatile import read_volatile
    from appv2.tools.ledger import dump_from_store

    dump = dict(
        dump_from_store(
            InMemoryKnowledgeStore(question_array_snapshot()), watermark="2026-08-31"
        )
    )
    assert dump["watermark"] == "2026-08-31"
    # roundtrip：投影携值 → 读数逐字（不加工不裁剪）。
    assert read_volatile(_state(ledger_dump=dump))["watermark"] == "2026-08-31"

    # 恢复路径（挂起→resume）落步骤 payload 的读数＝同一投影值。
    state = _state(ledger_dump=dump)
    state.pending_ask = {
        "kind": "clarify",
        "prompt": "「正常」想跟哪个标准比？",
        "options": ["对比计划产量", "对比上月同期"],
        "detail": None,
    }
    state.resume_choices = [{"kind": "clarify", "choice": "对比计划产量"}]
    with _scripted(_ask()):
        assert isinstance(clarify(state), ClarifyAsk)
    readings = _resume_readings(state)
    assert readings["watermark"] == "2026-08-31"
    assert readings["watermark"] == state.ledger_dump["watermark"]
    # 缺位形态回归：投影未携水位 → 如实空串（不编造）。
    assert read_volatile(_state(ledger_dump=_dump()))["watermark"] == ""


def test_ask_cap_truncate_with_material() -> None:
    """#14｜到上限 → 截断＋带材料如实直答（不环）（**钉 `pin-15` 的到顶半面，P1**）——:121。"""
    state = _state(
        observations=[_material_observation("A7 井 2026-10-14 产液量 120 立方米")],
        budget=Budget(ask_cap=2),
    )
    with _scripted(_ask()):
        assert isinstance(clarify(state), ClarifyAsk)  # 第 1 次反问挂起（计数 1）
    assert state.pending_ask is not None
    state.resume_choices = [{"kind": "clarify", "choice": "对比计划产量"}]
    with _scripted(_ask("还想跟哪个标准比？", ("对比上月同期", "对比同类井平均"))):
        capped = clarify(state)

    assert capped is None  # 不占三返回位（去向 answer 收口）
    assert state.pending_ask is None  # 不环：不再挂起
    assert state.next_intent == INTENT_ANSWER
    assert state.draft_kind == "direct"
    assert state.draft.startswith(
        "（追问次数已到上限——先把已经查到的材料如实交给你，不再继续追问）"
    )  # 2026-10-17 EB4b 白话化逐字（旧「（连续澄清截断——已取得材料如实交付，不再挂起）」）
    assert "- A7 井 2026-10-14 产液量 120 立方米" in state.draft  # 带已取得材料如实直答
    notices = [item for item in state.notices if item["type"] == "clarify_capped"]
    assert len(notices) == 1
    assert set(notices[0]) == {"type", "gates", "content"}  # 通知恰三键
    assert str(state.budget.ask_cap) in notices[0]["content"]  # 上限值引 budget 键（零复制）
    assert any(payload.get(PAYLOAD_CAPPED) for payload in _step_payloads(state))  # 机读信号

    # 零材料形＝如实壳（不冒充已交付）
    bare = _state(budget=Budget(ask_cap=2))
    with _scripted(_ask()):
        clarify(bare)
    bare.resume_choices = [{"kind": "clarify", "choice": "对比计划产量"}]
    with _scripted(_ask()):
        assert clarify(bare) is None
    assert bare.draft == NO_MATERIAL_SHELL


def test_no_lexicon_or_regex_in_clarification() -> None:
    """#16｜程序侧无词表／正则语义判断（AST 扫描本模块；**豁免面＝形态处理**）——:123。"""
    sources = _clarification_sources()
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
        assert _wordface_calls(tree) == [], f"{path.name}: {_wordface_calls(tree)}"
        assert _cjk_membership_judgements(tree) == [], f"{path.name} 汉字串成员判据"
        if path.name != "constants.py":  # 逻辑面零字面表：文本与映射表只在常量单点
            assert _cjk_collection_literals(tree) == [], (
                f"{path.name}: {_cjk_collection_literals(tree)}"
            )

    # 拒因映射表单点：定义点恰一处（常量单点），查找函数一处（分派面）
    definitions = [
        (path.name, _module_level_definitions(tree, "REASON_MARKERS"))
        for path, tree in sources
        if _module_level_definitions(tree, "REASON_MARKERS")
    ]
    assert definitions == [("constants.py", 1)], definitions
    lookups = [
        path.name for path, tree in sources if "REASON_MARKERS" in path.read_text(encoding="utf-8")
    ]
    assert lookups == ["constants.py", "core.py"], lookups

    # 探测器非空转：伪造词表／汉字成员判据／词面判方法／正则即被咬
    assert _cjk_collection_literals(ast.parse('WORDS = ["提及", "执行"]\n')) != []
    assert _cjk_membership_judgements(ast.parse('if word in "提及执行":\n    pass\n')) != []
    assert _wordface_calls(ast.parse('text.startswith("理解：")\n')) != []
    forged = ast.parse("import re\nre.compile('x')\n")
    assert "re" in _imported_modules(forged)


def test_clarify_signal_present() -> None:
    """#17｜拒因／截断／挂起的机读信号在场（ask 帧／`pending_ask`／拒因字段／notice）——:124。"""
    # ① 挂起：`ask` 帧投影（`pending_ask`）＋步 payload 帧标记＋返回位
    state = _state()
    with _scripted(_ask()):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyAsk)
    frame = state.pending_ask
    assert isinstance(frame, Mapping)
    assert set(frame) == {"kind", "prompt", "options", "detail"}
    assert frame["kind"] == "clarify"
    assert frame["options"] == ["对比计划产量", "对比上月同期"]
    assert frame["detail"] is None
    assert _last_step_payload(state)[PAYLOAD_ASK_FRAME] == frame

    # ② 拒因：step payload 拒因字段＋回喂面（槽位对账不过——段一不在名录形）
    rejected = _state()
    with _scripted(_decompose(_subtask(ledger_notes="采出程度｜未绑定｜2026-09-16~2026-10-16"))):
        rejection = clarify(rejected)
    assert isinstance(rejection, ClarifyRejection)
    assert _last_step_payload(rejected)[PAYLOAD_REJECTION] == rejection.reasons[0].reason
    assert rejected.decision_error == rejection.reasons[0].reason

    # ③ 截断：notice（`type` 引 `transport.NOTICE_TYPES` 闭世界值）
    capped_state = _state(budget=Budget(ask_cap=1), observations=[_material_observation()])
    with _scripted(_ask()):
        assert clarify(capped_state) is None
    assert [item["type"] for item in capped_state.notices] == ["clarify_capped"]


def test_discover_routed_not_direct_call() -> None:
    """#18｜`discover` 经 `orchestration` 路由出去执行（本块零工具直调、不返回）——:125。"""
    state = _state()
    with _scripted(_discover("semantic_query", {"text": "产液量"})):
        outcome = clarify(state)

    assert outcome is None  # 不占三返回位
    assert state.next_intent == INTENT_DISCOVER  # 信道＝`next_intent="discover"`
    assert state.pending_discovers == [{"tool": "semantic_query", "args": {"text": "产液量"}}]

    # 零工具直调：本块源码不 import 工具面／引擎面（AST；R6／票面边界红线②）
    forbidden = ("appv2.tools", "appv2.knowledge", "appv2.query", "appv2.retrieval")
    imported = set()
    for _, tree in _clarification_sources():
        imported |= _imported_modules(tree)
    assert not sorted(
        module
        for module in imported
        if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden)
    )
    # 依赖白名单（规格「框架与依赖红线」）：四个包根＋`infra.clock`（时间 B14）＋本包内部件
    # （含 V2-82b 对象歧义门 `subject_ask`——纯判据＋注入素材，仍零工具面 import）
    assert sorted(module for module in imported if module.startswith("appv2.")) == [
        "appv2.infra.clock",
        "appv2.runtimev2.bookkeeping",
        "appv2.runtimev2.clarification.constants",
        "appv2.runtimev2.clarification.core",
        "appv2.runtimev2.clarification.guidance",
        "appv2.runtimev2.clarification.models",
        "appv2.runtimev2.clarification.subject_ask",
        "appv2.runtimev2.clarification.volatile",
        "appv2.runtimev2.parsing",
        "appv2.runtimev2.prompts",
        "appv2.runtimev2.state",
    ]


def test_no_rediscover_when_window_set() -> None:
    """#19｜台账命中且时间窗已定 → 禁再 `discover`（机械半句）——`specs/clarification.md:126`。"""
    group = {"subtasks": [dict(_subtask())]}
    blocked = _state(question_group=group)
    with _scripted(_discover()) as completer:
        outcome = clarify(blocked)

    assert isinstance(outcome, ClarifyRejection)
    assert [reason.code for reason in outcome.reasons] == [REASON_NO_REDISCOVER]
    assert "禁再 discover" in outcome.reasons[0].reason
    assert blocked.next_intent == INTENT_DECISION  # 未交出发现信道
    assert blocked.pending_discovers == []  # 未定型发射支
    assert len(completer.calls) == 1  # 零工具直调（只有一次模型调用）

    # 机械条件两面（零语义判断）：无既成问题组 → 放行
    allowed = _state()
    with _scripted(_discover()):
        assert clarify(allowed) is None
    assert allowed.next_intent == INTENT_DISCOVER

    # 机械条件两面：台账投影空（未命中面）→ 不触发「台账命中」
    empty_ledger = _state(ledger_dump={}, question_group=group)
    with _scripted(_discover()):
        assert clarify(empty_ledger) is None
    assert empty_ledger.next_intent == INTENT_DISCOVER


def test_parse_rejection_str_to_clarify_rejection_consumer_side() -> None:
    """#20｜解析拒文（parsing `str`）→ `ClarifyRejection` 结构化转换归本块（消费方）——:127。"""
    cases = {
        "action 缺失或越界（discover/decompose/ask/finalize 四值）：'execute'": (
            REASON_ACTION_OUT_OF_WORLD
        ),
        "subtasks s1 chain 越界（data/knowledge）：'sql'": REASON_CHAIN_OUT_OF_WORLD,
        "subtasks s1 缺 ledger_notes（台账注释必带）：…": REASON_LEDGER_NOTES_EMPTY,
        "subtasks 超出上限（≤4 个——Owner 认可值）": REASON_SUBTASK_COUNT_OUT_OF_RANGE,
        "解析面其余 schema 违例（不可解析／形状／预算前缀）": REASON_SCHEMA_INVALID,
    }
    for text, code in cases.items():
        assert code_of_rejection(text) == code, text

    # 端到端：解析不合格 → 结构化拒因；`str` **逐字**进 `reason` 字段（承载位换、文本不变）
    raw = _parse(_ask("x", ("只有一个选项",)))
    assert isinstance(raw, str), raw
    state = _state()
    with _scripted(_ask("x", ("只有一个选项",))):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyRejection)
    assert outcome.reasons[0].reason == raw
    assert outcome.reasons[0].code == REASON_SCHEMA_INVALID
    assert state.decision_error == raw
    assert outcome.reasons  # 恒非空（机读信号面）


# ══════════════════════════════════════════════════════════════════════════════
# 票面对象 7 行（规格表行序 7／8／9／10／15／21／22）——RT-W4-02b（-B 半面）
# ══════════════════════════════════════════════════════════════════════════════

# 无时间词的默认窗注记（默认值＋注记同批产出——真源 `walk/08` §七 Q-B）
_DEFAULT_WINDOW_NOTE = "未指明时间窗——已按近 30 天默认（2026-09-16~2026-10-16）"
# 默认窗下的子问题原文（窗由模型侧结论给出、程序逐字承接——程序零自造窗）
_DEFAULT_WINDOW_QUESTION = "查 A7 井 2026-09-16~2026-10-16 产液量"
# 依赖／顺序类键（保留集判据面：`Subtask` 无依赖字段——行为 10「独立并行」）
_DEPENDENCY_KEYS = frozenset(
    {"depends_on", "dependencies", "deps", "after", "before", "parent_id", "order", "seq"}
)


def _decompose_with_note(note: str, *subtasks: Mapping[str, Any]) -> str:
    """带注记的分解发射（注记＝模型侧结论的原话承载——行为 3「并注记」面）。"""
    rows = [dict(subtask) for subtask in subtasks]
    return _json({"action": "decompose", "question_group": {"subtasks": rows}, "note": note})


def _finalize_with_note(note: str) -> str:
    """带注记的定案发射（注记出流与动作无关，只随 `note` 在场）。"""
    return _json({"action": "finalize", "note": note})


def _notices_of(state: RunState, notice_type: str) -> list[Mapping[str, Any]]:
    """按类型取通知条目（注记出流的机读信号面）。"""
    return [item for item in state.notices if item.get("type") == notice_type]


def _question_text_reads(tree: ast.Module) -> list[str]:
    """问句原文读点探测（`state.question` 属性访问）——「程序不验收判断本身」的机检面。"""
    found: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "question"
            and isinstance(node.value, ast.Name)
            and node.value.id == "state"
        ):
            found.append(f"L{node.lineno}")
    return found


def test_no_ask_when_time_resolvable() -> None:
    """#7｜时间可确定 → 不反问，直接定范围（**分派形**；判断本身不入程序验收面）——:114。

    断的是模型结论的**分派形**：「能否从问句确定／是否需反问」的判断在模型侧产出
    （`walk/裁决表.md` 项目级裁决 #13）——模型给非 ask 结论即直接定范围／定案，程序零自造反问、
    零问句原文读点（不验收判断本身）。
    """
    windowed = _subtask(question="查 A7 井 2026-10-01~2026-10-03 产液量")
    state = _state(question="A7 井 2026-10-01 到 2026-10-03 的产液量是多少？")
    with _scripted(_decompose(windowed)) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyFinal)  # 模型结论＝时间可确定 → 直接定范围（分解形）
    assert state.pending_ask is None  # 零挂起
    assert not any(PAYLOAD_ASK_FRAME in payload for payload in _step_payloads(state))  # 零反问帧
    assert state.question_group == {"subtasks": [dict(windowed)]}  # 窗原样（程序不改写）
    assert state.next_intent == INTENT_TOOLMATCH
    assert len(completer.calls) == 1

    # 定案形同款分派（同一分派形：程序只按结论分派）
    settled = _state(observations=[_material_observation()])
    with _scripted(_finalize()):
        assert clarify(settled) is None
    assert settled.pending_ask is None
    assert settled.next_intent == INTENT_ANSWER

    # 「只验收分派形，不验收判断本身」：本块源码零问句原文读点
    for path, tree in _clarification_sources():
        assert _question_text_reads(tree) == [], f"{path.name} 读问句原文"
    assert _question_text_reads(ast.parse("flag = state.question\n")) == ["L1"]  # 探测器非空转


def test_default_window_with_note() -> None:
    """#8｜无时间词 → 默认近 30 天并带注记——`specs/clarification.md:115`。

    默认值＋**注记**同批产出（真源 `walk/08` §七 Q-B）：默认窗是模型侧结论（程序零日期算术、
    零窗口字面），注记由本块**逐字转抄**为机读 `decision_note` 通知（恰三键）；缺位不产通知。
    """
    state = _state(question="A7 井的产液量是多少？")  # 无时间词
    with _scripted(
        _decompose_with_note(_DEFAULT_WINDOW_NOTE, _subtask(question=_DEFAULT_WINDOW_QUESTION))
    ):
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyFinal)
    assert state.pending_ask is None  # 默认窗＝不反问
    assert state.question_group["subtasks"][0]["question"] == _DEFAULT_WINDOW_QUESTION  # 逐字承接
    notes = _notices_of(state, NOTICE_DECISION_NOTE)
    assert len(notes) == 1  # 注记同批出流（恰一条）
    assert set(notes[0]) == {"type", "gates", "content"}  # 通知恰三键
    assert notes[0]["content"] == _DEFAULT_WINDOW_NOTE  # 逐字转抄（不改写、不摘要）
    assert notes[0]["gates"] == []

    # 定案形同款出流（注记只随 `note` 在场——不挑动作）
    settled = _state(observations=[_material_observation()])
    with _scripted(_finalize_with_note(_DEFAULT_WINDOW_NOTE)):
        assert clarify(settled) is None
    shipped = _notices_of(settled, NOTICE_DECISION_NOTE)
    assert [item["content"] for item in shipped] == [_DEFAULT_WINDOW_NOTE]

    # 缺位不产通知（不得凭空产注记）
    bare = _state()
    with _scripted(_decompose(_subtask())):
        assert isinstance(clarify(bare), ClarifyFinal)
    assert bare.notices == []

    # 程序零自造默认窗：本块零日期算术（`timedelta` 零接触）、零窗口天数裸字面
    for path, tree in _clarification_sources():
        assert "timedelta" not in _imported_modules(tree), path.name
        assert not any(
            isinstance(node, ast.Attribute) and node.attr == "timedelta"
            for node in ast.walk(tree)
        ), path.name
        assert _limit_literal_hits(tree, frozenset({30})) == {}, path.name


def test_caliber_ambiguity_asks() -> None:
    """#9｜口径歧义 → 反问（不给默认）——`specs/clarification.md:116`。

    口径有歧义 → **反问**、不交模型猜（真源 `walk/08` §七 Q-B）：模型给 ask 结论即挂起出卡；
    程序**零默认注入**——出卡选项＝模型原话逐字（不追加「默认」项、不替模型选口径、不落默认材料）。
    """
    prompt = "「正常产量」按哪个口径比？"
    options = ("对比计划产量", "对比上月同期", "对比同类井平均")
    state = _state(question="A7 井产量正常吗？")
    with _scripted(_ask(prompt, options)) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyAsk)
    assert outcome.prompt == prompt
    assert outcome.options == list(options)  # 模型原话逐字：零默认项、零改写
    frame = state.pending_ask
    assert frame is not None
    assert frame["options"] == list(options)
    # 不给默认：程序不替模型选口径——零定案、零直答、零自造材料落场
    assert state.question_group is None
    assert state.draft == "" and state.draft_kind == "" and state.answer == ""
    assert len(completer.calls) == 1


def test_ask_card_merged() -> None:
    """#10｜同轮多处歧义 → 合并成一张卡——`specs/clarification.md:117`。

    同一轮里多处歧义 → **合并成一张卡**一次问清（反对逐条追问，行为 11）：本块对一次发射只出
    一张卡（单返回位／单挂起帧／单 ask 步），卡内选项＝模型合并后的全量选项——零拆分、零二次追问。
    """
    prompt = "两处歧义一起问：查哪些井？「正常」按哪个口径比？"
    options = ("A7 井", "全部井", "对比计划产量")
    state = _state()
    with _scripted(_ask(prompt, options)) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyAsk)
    assert set(type(outcome).__dataclass_fields__) == {"kind", "prompt", "options"}  # 卡载荷三键
    frame = state.pending_ask
    assert frame is not None
    assert set(frame) == {"kind", "prompt", "options", "detail"}
    assert frame["options"] == list(options)  # 合并后的全量选项（不拆分）
    assert len([p for p in _step_payloads(state) if PAYLOAD_ASK_FRAME in p]) == 1  # 恰一张卡
    assert len(completer.calls) == 1  # 零逐条追问（不用第二次模型调用补问）

    # 合并只改条数：歧义几处都只出一卡、选项原样出（个数闭世界由解析面守）
    for merged in (("A7 井", "对比计划产量"), ("A7 井", "A8 井", "对比计划产量", "对比上月同期")):
        merged_state = _state()
        with _scripted(_ask(prompt, merged)):
            merged_outcome = clarify(merged_state)
        assert isinstance(merged_outcome, ClarifyAsk)
        assert merged_outcome.options == list(merged)
        assert len([p for p in _step_payloads(merged_state) if PAYLOAD_ASK_FRAME in p]) == 1


def test_coverage_self_proof_model_only() -> None:
    """#15｜覆盖校验由模型自证；程序不判覆盖——`specs/clarification.md:122`。

    拆完后由**模型**自证「子问题合起来覆盖原题」；**程序只校格式，不拿词表猜覆盖**（行为 9；
    风险 2）——程序侧只有 schema／前置合规两把闸：单子问题覆盖多诉求原题照收定案（零覆盖缺口
    拒因），模型自证原文经注记逐字出流（零评价、零改写）。
    """
    proof = "覆盖自证：s1 覆盖「哪些井」与「哪个指标」两个诉求"
    state = _state(question="A7 井和 A8 井的产液量分别是多少？")  # 多诉求原题
    with _scripted(_decompose_with_note(proof, _subtask(question="查 A7 井产液量"))):
        outcome = clarify(state)

    # 程序不判覆盖：单子问题覆盖多诉求原题照收（不做覆盖缺口判定）
    assert isinstance(outcome, ClarifyFinal)
    assert isinstance(state.question_group, Mapping)
    assert len(state.question_group["subtasks"]) == 1
    # 自证在模型侧：原文经注记逐字出流（本块不评价、不修补）
    assert [item["content"] for item in _notices_of(state, NOTICE_DECISION_NOTE)] == [proof]
    # 拒因闭世界无覆盖缺口码（程序对账面＝动作／条数／注释／路线，无覆盖项）
    assert not any(
        word in code for code in REASON_CODES for word in ("coverage", "覆盖", "gap")
    )
    # 程序零覆盖判断：本块逻辑面无语义词表（AST 两探针复用 -A 已立的形态处理豁免面）
    for path, tree in _clarification_sources():
        assert _cjk_membership_judgements(tree) == [], path.name
        assert _wordface_calls(tree) == [], path.name


def test_boundary_slot_reconciliation_rejections() -> None:
    """#21｜【边界集】`ledger_notes` 三段槽位对账不过 → 判违约（**带段级拒因**）——`:129`。

    判据＝三段槽位对账（行为 8；2026-10-16 改·流水 64；**形态处理豁免面内**——闭世界集合成员校
    ＋日期形解析，非语义词表／正则）：任一不过 → 判违约、拒因回喂（**指明哪一段／哪个值／为什么**
    ＋【期望形】＋【台账相关行】）、**不静默放行、不自动修补**。四类拒形逐条：
    ①槽位不在名录（含语义改写／摘要／自造的段一形）；②绑定态越界（「草案」等台账行外值）；
    ③窗形不合法（胡写）；④段数非三（缺段／多段——位次固定）。
    """
    block = render_ledger_resident_block(_state())
    assert _METRIC_VALUE in block  # 台账行在场（【台账相关行】取值面）

    cases: dict[str, tuple[str, str, str]] = {
        # label: (note 形, 拒段名, 拒因原因逐字)
        "槽位不在名录": ("采出程度｜未绑定｜2026-09-16~2026-10-16", "槽位", "不在台账名录"),
        "槽位非逐字改写": (
            "产液量（日度生产指标）｜未绑定｜2026-09-16~2026-10-16", "槽位", "不在台账名录",
        ),
        "槽位自造": (
            "产液量大概就是每天的产水量｜未绑定｜2026-09-16~2026-10-16",
            "槽位",
            "不在台账名录",
        ),
        "绑定态越界": ("产液量｜草案｜2026-09-16~2026-10-16", "绑定态", "绑定态越界"),
        "绑定态英文形越界": ("产液量｜bound｜2026-09-16~2026-10-16", "绑定态", "绑定态越界"),
        "窗形胡写": ("产液量｜未绑定｜下个月", "窗", "窗形不合法"),
        "窗单端非法": ("产液量｜未绑定｜2026-09-16~下个月", "窗", "窗形不合法"),
        "窗缺段": ("产液量｜未绑定｜", "窗", "窗形不合法"),
        "段数缺": ("产液量｜未绑定", "段数", "段数非三"),
        "段数多": ("产液量｜未绑定｜2026-09-16~2026-10-16｜备注", "段数", "段数非三"),
    }
    for label, (note_text, segment, cause) in cases.items():
        state = _state()
        with _scripted(_decompose(_subtask(ledger_notes=note_text))) as completer:
            outcome = clarify(state)
        assert isinstance(outcome, ClarifyRejection), label
        assert [reason.code for reason in outcome.reasons] == [
            REASON_LEDGER_NOTES_SLOT_MISMATCH
        ], label
        reason = outcome.reasons[0].reason
        assert reason.startswith("上次发射被拒：ledger_notes 槽位对账未过：s1"), label
        assert f"【拒因】s1 的「{segment}」段" in reason, label
        assert cause in reason, label  # 拒因指明原因
        assert (
            "【期望形】〈台账行首名｜或「无台账命中」〉｜已绑定|未绑定"
            "｜〈锚定窗形：2026-09-16~2026-10-16｜检索式无窗：窗未定或 null~null〉" in reason
        ), label
        assert "——修正后重新输出 JSON。" in reason, label
        if segment in ("槽位", "段数"):
            assert "【台账相关行】（名录无此名" in reason, label
        else:
            assert "【台账相关行】指标｜产液量：" in reason, label  # 整行原文（同注入块形）
        assert state.question_group is None  # 不静默放行、不自动修补
        assert state.decision_error == reason  # 拒因回喂（增量条「上次发射被拒」行源）
        assert _last_step_payload(state)[PAYLOAD_REJECTION] == reason
        assert len(completer.calls) == 1

    # 多名越界同发：头行列全 offender、逐 id 一块（回喂面单段文本）
    multi = _state()
    rows = [
        _subtask("s1", ledger_notes="采出程度｜未绑定｜2026-09-16~2026-10-16"),
        _subtask("s2", ledger_notes="产液量｜草案｜2026-09-16~2026-10-16"),
    ]
    with _scripted(_decompose(*rows)):
        multi_outcome = clarify(multi)
    assert isinstance(multi_outcome, ClarifyRejection)
    assert "槽位对账未过：s1、s2" in multi_outcome.reasons[0].reason
    assert "【拒因】s1 的「槽位」段" in multi_outcome.reasons[0].reason
    assert "【拒因】s2 的「绑定态」段" in multi_outcome.reasons[0].reason
    assert multi_outcome.reasons[0].reason.count("【期望形】") == 2  # 逐 id 一块
    # 步骤标题／过程档案用单行同义形（多行拒因正文不进标题槽）
    assert any(
        "槽位对账未过：s1、s2" in str(step.get("title", "")) for step in multi.steps
    )

    # 边界另一面：三段位次对齐、值皆合法 → 放行（同一判据无中间态）；段三「无时间窗」＝
    # 「窗未定」同义形（knowledge 链检索式无窗概念，2026-10-16 微批收编——真机日志实测写法）
    for note_text in (
        _NOTE,
        _NOTE_WINDOW_UNRESOLVED,
        f"{_NOTE_SLOT}｜已绑定｜无时间窗",
        f"{_NOTE_SLOT}｜已绑定｜null~null",
    ):
        allowed = _state()
        with _scripted(_decompose(_subtask(ledger_notes=note_text))):
            allowed_outcome = clarify(allowed)
        assert isinstance(allowed_outcome, ClarifyFinal), note_text
        assert allowed.question_group["subtasks"][0]["ledger_notes"] == note_text

    # 空投影（注入块缺位）＝名录制空 → 判违约（fail-closed，不降级放行）
    empty = _state(ledger_dump={})
    with _scripted(_decompose(_subtask(ledger_notes=_NOTE))):
        empty_outcome = clarify(empty)
    assert isinstance(empty_outcome, ClarifyRejection)
    assert "不在台账名录" in empty_outcome.reasons[0].reason


# ══════════════════════════════════════════════════════════════════════════════
# L3 阻塞修复批（流水 66）：无台账命中形入闭世界＋拒因回喂壳恰一遍
# ══════════════════════════════════════════════════════════════════════════════


def test_ledger_notes_no_ledger_hit_form_legal() -> None:
    """#21 补｜槽位段第二形「无台账命中」＝合法——`specs/clarification.md:129`。

    L3 阻塞修复批·流水 66（真机 `run-18e5d273`）：knowledge 链报告题（如「完井液密度」）**本就
    没有台账行**，旧判据只认名录 → 模型**没有任何合法形可写**、三写「不在名录」三拒烧光轮次
    （证据 `docs/runtime-refactor/ladder/L3/01-完井液在二开钻进段与三开-summary.md`：`id=5／7／9`
    三条「ledger_notes 槽位对账未过：s1」＋`budget_converged`）。空命中是**合法业务态**、非违约。
    断言四面：①真机 s1 形（`无台账命中｜未绑定｜null~null`）与题面点名形（`…｜窗未定`）均放行；
    ②无命中形**只免锚台账行**——绑定态／窗段照验，越界照拒且【台账相关行】示无命中行文；
    ③自造名 ≠ 无命中（真机自造名「完井液密度」照拒，壳语明示——防「无命中」变垃圾桶）；
    ④空投影（名录制空 fail-closed 面）下无命中形照放行（有无台账行与投影态无关）。
    """
    for note_text in (
        f"{NOTE_SLOT_NO_HIT}｜未绑定｜窗未定",  # 题面点名形
        f"{NOTE_SLOT_NO_HIT}｜未绑定｜null~null",  # 真机 run-18e5d273 的 s1 原形（改此形必过）
        f"{NOTE_SLOT_NO_HIT}｜已绑定｜2026-09-16~2026-10-16",
    ):
        state = _state()
        with _scripted(_decompose(_subtask(ledger_notes=note_text))):
            outcome = clarify(state)
        assert isinstance(outcome, ClarifyFinal), note_text
        assert state.question_group["subtasks"][0]["ledger_notes"] == note_text
        assert state.decision_error == ""  # 零拒因（放行即清回喂面）

    # 只免锚台账行：②③段照验（段级拒因照旧指明段名与原因）
    for note_text, segment, cause in (
        (f"{NOTE_SLOT_NO_HIT}｜草案｜窗未定", "绑定态", "绑定态越界"),
        (f"{NOTE_SLOT_NO_HIT}｜未绑定｜下个月", "窗", "窗形不合法"),
    ):
        state = _state()
        with _scripted(_decompose(_subtask(ledger_notes=note_text))):
            rejected = clarify(state)
        assert isinstance(rejected, ClarifyRejection), note_text
        reason = rejected.reasons[0].reason
        assert f"【拒因】s1 的「{segment}」段" in reason, note_text
        assert cause in reason, note_text
        assert NO_LEDGER_HIT_ROW_SHELL in reason, note_text  # 无命中形照实示
        assert "名录无此名" not in reason, note_text  # 不误套名录外自造名的行文

    # 自造名 ≠ 无命中：真机自造名（完井液密度）照拒，壳语明示该界
    coined_state = _state()
    with _scripted(_decompose(_subtask(ledger_notes="完井液密度｜未绑定｜窗未定"))):
        coined = clarify(coined_state)
    assert isinstance(coined, ClarifyRejection)
    coined_reason = coined.reasons[0].reason
    assert "不在台账名录" in coined_reason
    assert "自造名≠「无台账命中」" in coined_reason

    # 空投影（名录制空＝fail-closed 面）下无命中形照放行：无台账行与投影态无关
    empty = _state(ledger_dump={})
    with _scripted(_decompose(_subtask(ledger_notes=f"{NOTE_SLOT_NO_HIT}｜未绑定｜窗未定"))):
        empty_outcome = clarify(empty)
    assert isinstance(empty_outcome, ClarifyFinal)

    # 真机台账 × 真机形（判据不依赖 fixture——问数组台账态快照投影）：真投影下 s1 原形同过；
    # 且真机自造名「完井液密度」**真不在**真名录（复现 run-18e5d273 被拒面——无命中形才是其合法出路）
    real = _state(ledger_dump=_real_ledger_dump())
    with _scripted(_decompose(_subtask(ledger_notes=f"{NOTE_SLOT_NO_HIT}｜未绑定｜null~null"))):
        assert isinstance(clarify(real), ClarifyFinal)
    coined_real = _state(ledger_dump=_real_ledger_dump())
    with _scripted(_decompose(_subtask(ledger_notes="完井液密度｜未绑定｜null~null"))):
        coined_outcome = clarify(coined_real)
    assert isinstance(coined_outcome, ClarifyRejection)
    assert "不在台账名录" in coined_outcome.reasons[0].reason


def test_no_ledger_hit_selfmade_forms_still_rejected() -> None:
    """#21 补²｜真机失败形**照拒**（防「样例补全样例行」变松闸）——2026-10-17 补（L3 阻塞修复批·
    分解样例补行）。

    真机 `run-b5b6b056`（`docs/runtime-refactor/ladder/L3/06`）三轮全拒：r1＝槽位段尾加解释
    （`无台账命中——…`→段数非三）、r2＝绑定态／窗段自造形（`无台账命中｜无绑定｜检索式无窗`）、
    r3＝窗段自造形（`无台账命中｜未绑定｜检索式无窗`）。样例区补「无台账命中形全样例行」只教
    合法形（逐字 `无台账命中｜未绑定｜窗未定`；机读面
    `tests/domains/test_v2_prompts.py::decompose_example_no_hit_full_row`）、**不改闸**：三形照拒
    不误放、拒因指明段名与原因（无命中形照实示【台账相关行】行文）。
    """
    cases: dict[str, tuple[str, str, str, str]] = {
        # label: (真机形, 拒段名, 拒因原因逐字, [台账相关行]行文)
        "r1 段尾加解释": (
            "无台账命中——完井液密度属于完井工程报告事实",
            "段数",
            "段数非三",
            "名录无此名",
        ),
        "r2 绑定态自造形": (
            "无台账命中｜无绑定｜检索式无窗",
            "绑定态",
            "绑定态越界",
            NO_LEDGER_HIT_ROW_SHELL,
        ),
        "r3 窗段自造形": (
            "无台账命中｜未绑定｜检索式无窗",
            "窗",
            "窗形不合法",
            NO_LEDGER_HIT_ROW_SHELL,
        ),
    }
    for label, (note_text, segment, cause, row_shell) in cases.items():
        state = _state()
        with _scripted(_decompose(_subtask(ledger_notes=note_text))):
            outcome = clarify(state)
        assert isinstance(outcome, ClarifyRejection), label
        assert [reason.code for reason in outcome.reasons] == [
            REASON_LEDGER_NOTES_SLOT_MISMATCH
        ], label
        reason = outcome.reasons[0].reason
        assert reason.startswith("上次发射被拒：ledger_notes 槽位对账未过：s1"), label
        assert f"【拒因】s1 的「{segment}」段" in reason, label
        assert cause in reason, label  # 拒因指明原因
        assert row_shell in reason, label
        assert state.question_group is None, label  # 不静默放行、不自动修补
        assert state.decision_error == reason, label  # 拒因回喂面在场


def test_slot_mismatch_feedback_single_frame() -> None:
    """#21 补｜槽位对账拒因回喂**壳恰一遍**（流水 66·叠字病灶，真机 `run-18e5d273`）。

    真机回喂形＝「**上次发射被拒：上次发射被拒：**ledger_notes…」「——修正后重新输出 JSON。
    ——修正后重新输出 JSON。」：拒因载荷**自带整套壳体**（流水 64 裁：头行带「上次发射被拒：」、
    尾行「——修正后重新输出 JSON。」），增量条回喂行又套一次 → 壳两遍。
    断言：载荷原文（拒因载荷形＝一本账）零改动恰一遍进回喂文本——壳两件各计 1（判据＝回喂文本
    恰一遍），且载荷原文原样在场、零改写。
    """
    state = _state()
    with _scripted(_decompose(_subtask(ledger_notes="采出程度｜未绑定｜2026-09-16~2026-10-16"))):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyRejection)
    payload = state.decision_error
    assert payload.startswith("上次发射被拒：ledger_notes 槽位对账未过：s1")
    assert payload.endswith("——修正后重新输出 JSON。")

    feedback = assemble_decision_increment(state, phase=PHASE_CLARIFY)
    assert payload in feedback  # 拒因载荷原文原样在场（零改写）
    assert feedback.count("上次发射被拒：") == 1  # 前缀恰一遍（旧形＝两遍）
    assert feedback.count("——修正后重新输出 JSON。") == 1  # 尾件恰一遍（旧形＝两遍）


def test_retention_no_ask_no_dependency() -> None:
    """#22｜【保留集】非歧义问句不产生 ask；子问题独立并行行为不变——`specs/clarification.md:129`。

    行为 10：`Subtask` **不含依赖字段**，子问题**独立并行**（依赖声明与顺序执行＝**不做**）。
    保留集＝这两个既有行为不因本块改形：非歧义问句走分解（零 ask）＋问题组条目键形恒四键
    （无依赖／顺序／外键）、发射序原样。
    """
    rows = [_subtask("s1", question="查 A7 井产液量"), _subtask("s2", question="查 A8 井产液量")]
    state = _state(question="A7 井和 A8 井的产液量分别是多少？")
    with _scripted(_decompose(*rows)) as completer:
        outcome = clarify(state)

    assert isinstance(outcome, ClarifyFinal)  # 非歧义 → 零 ask（保留原行为）
    assert state.pending_ask is None
    assert not any(PAYLOAD_ASK_FRAME in payload for payload in _step_payloads(state))
    assert len(completer.calls) == 1

    # 子问题独立并行行为不变：条目键形恒四键、发射序原样（不回排）、零依赖字段
    assert isinstance(state.question_group, Mapping)
    subtasks = state.question_group["subtasks"]
    assert [row["id"] for row in subtasks] == ["s1", "s2"]
    assert [subtask.id for subtask in outcome.subtasks] == ["s1", "s2"]
    for row in subtasks:
        assert set(row) == {"id", "question", "ledger_notes", "chain"}
        assert not set(row) & _DEPENDENCY_KEYS

    # 「依赖声明与顺序执行＝不做」的承载位面：`Subtask` 不含依赖字段
    assert set(Subtask.__dataclass_fields__) == {"id", "question", "ledger_notes", "chain"}
    assert not set(Subtask.__dataclass_fields__) & _DEPENDENCY_KEYS
