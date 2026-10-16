"""clarification 块验收（`RT-W4-02a`：-A 半面 15 行 ＋ 本块三条 pin）。

票面对象＝`specs/clarification.md`「验收测试」表逐行转抄（`#` 列保留规格表行序、不重编；测试
标识与规格列逐字一致）。本票 15 行＝行序 1／2／3／4／5／6／11／12／13／14／16／17／18／19／20；
余 7 行（行序 7／8／9／10／15／21／22）归 `RT-W4-02b`。

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
from appv2.runtimev2.clarification import clarify
from appv2.runtimev2.clarification.constants import (
    GUIDANCE_FALLBACK,
    GUIDANCE_PRECONDITION,
    MAX_SUBTASKS,
    NO_MATERIAL_SHELL,
    PAYLOAD_ASK_FRAME,
    PAYLOAD_CAPPED,
    PAYLOAD_REJECTION,
    PAYLOAD_RESUME,
    REASON_ACTION_OUT_OF_WORLD,
    REASON_CHAIN_OUT_OF_WORLD,
    REASON_FINALIZE_ZERO_OBSERVATION,
    REASON_LEDGER_NOTES_EMPTY,
    REASON_NO_REDISCOVER,
    REASON_REJECTION_GUIDANCE,
    REASON_SCHEMA_INVALID,
    REASON_SUBTASK_COUNT_OUT_OF_RANGE,
    VOLATILE_KEYS,
)
from appv2.runtimev2.clarification.core import code_of_rejection
from appv2.runtimev2.clarification.models import (
    ClarifyAsk,
    ClarifyFinal,
    ClarifyRejection,
)
from appv2.runtimev2.gateway_adapter import ScriptedCompleter, set_completer
from appv2.runtimev2.parsing import (
    ClarifyEmission,
    discover_fingerprint,
    parse_question_group,
)
from appv2.runtimev2.prompts import (
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    render_ledger_resident_block,
)
from appv2.runtimev2.state import (
    ASK_CAP,
    INTENT_ANSWER,
    INTENT_DECISION,
    INTENT_DISCOVER,
    MAX_DISCOVERS_PER_RUN,
    MAX_ROUNDS,
    Budget,
    RunState,
)

# ══════════════════════════════════════════════════════════════════════════════
# fixture 与探测器（状态投影／发射文本／剧本化 completer／源码扫描）
# ══════════════════════════════════════════════════════════════════════════════

_CLARIFY_DIR = Path(clarification_constants.__file__).parent

# 台账条目原文（ledger_notes 逐字求得的源面——注释必须能在注入块里一字不差地找到）
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
    return {
        "metrics": metric_rows,
        "terms": [dict(row) for row in (terms or [])],
        "objects": [dict(row) for row in (objects or [])],
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


def _json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _subtask(
    sid: str = "s1",
    *,
    ledger_notes: str = _METRIC_VALUE,
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
    """#6｜`finalize` 被拒 → 拒因载荷带三段带路（**钉 `pin-07`，P1**）——:113。"""
    fingerprint = discover_fingerprint("data_query", {"metric_slot": "产液量"})
    assert json.loads(fingerprint)["tool"] == "data_query"
    state = _state(
        observations=[_notice_observation()],
        precondition_verdicts=[{"subtask_id": "s1", "state": "blocked_refuse"}],
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


def test_ledger_notes_verbatim_from_injection() -> None:
    """#11｜台账注入块存在且注释可逐字求得——`specs/clarification.md:118`。"""
    state = _state()
    block = render_ledger_resident_block(state)
    assert block and RESIDENT_BLOCK_BEGIN in block and RESIDENT_BLOCK_END in block
    assert _METRIC_VALUE in block  # 台账条目逐字转抄（`specs/prompts.md` 行为 8）

    with _scripted(_decompose(_subtask(ledger_notes=_METRIC_VALUE))):
        outcome = clarify(state)
    assert isinstance(outcome, ClarifyFinal)
    # 注入块随相位首入包进链（模型面可见＝逐字可求得的前提）
    package = state.messages[0]
    assert package["role"] == "user"
    assert RESIDENT_BLOCK_BEGIN in package["content"]
    assert isinstance(state.question_group, Mapping)
    notes = [subtask["ledger_notes"] for subtask in state.question_group["subtasks"]]
    assert notes == [_METRIC_VALUE]
    assert all(note in block for note in notes)


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
    assert state.draft.startswith("（连续澄清截断——已取得材料如实交付，不再挂起）")
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

    # ② 拒因：step payload 拒因字段＋回喂面
    rejected = _state()
    with _scripted(_decompose(_subtask(ledger_notes="产液量大概就是每天的产水量"))):
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
    assert sorted(module for module in imported if module.startswith("appv2.")) == [
        "appv2.infra.clock",
        "appv2.runtimev2.bookkeeping",
        "appv2.runtimev2.clarification.constants",
        "appv2.runtimev2.clarification.core",
        "appv2.runtimev2.clarification.guidance",
        "appv2.runtimev2.clarification.models",
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
