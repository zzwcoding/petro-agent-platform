"""RT-W4-04 preconditions 验收——`specs/preconditions.md`「验收测试」表 14 行逐行落测（1:1 同名）。

14 行对应（规格表 `specs/preconditions.md:105–:118` 原序、标识逐字）：
- 行 1 `exactly_one_verdict_per_subtask`：每子问题恰一条 verdict；`subtask_id` 对不上 → 判失败；
- 行 2 `decision_enum_closed_world`：`decision` 越界取值 → 判失败（三态闭世界）；
- 行 3 `fixed_order_short_circuit`：判定序固定＋命中即停（打在序 3 上不进序 4）；
- 行 4 `note_merges_into_allow`：带注记的判定位 → `allow` ＋ `notes` 非空（**不设第四态**）；
- 行 5 `declared_external_table_asks`：外表越集（申报面）→ `ask`（kind=external_table_approval）；
- 行 6 `resume_reconsume_approved_ids`：恢复后消费 `approved_ids` 重判放行；
- 行 7 `rewire_once_then_refuse`：换链回炉只允许一次；二次触发 → `refuse`（**pin-16 承重面**）；
- 行 8 `refusal_has_rule_text_alternatives`：非 `allow` 必带 `hit_rule` ＋ 人话；
  口径类拒答必带替代项；
- 行 9 `gate_error_fail_closed`：闸件抛错 → fail-closed 转 `refuse`（**不静默放行**）；
- 行 10 `no_model_call_in_preconditions`：本模块与闸件零 LLM（AST＋import 双证）；
- 行 11 `no_lexicon_or_regex_in_preconditions`：程序侧无词表／正则语义判断（AST 扫描本模块；
  豁免面＝形态处理／集合成员判定）；
- 行 12 `verdict_signal_present`：判定结果的机读信号在场（step payload ＋ notice）；
- 行 13 `boundary_each_rule_hits`：【边界集】空窗／越界水位／未绑定指标／单井不支持 →
  各自命中对应判定位；
- 行 14 `retention_plain_allow_unchanged`：【保留集】`allow` 的普通子问题行为不变
  （无注记、无额外信号）。

「测试网钉」4 行对应用例（`specs/preconditions.md:140–:143` pin 行；pin-17 为 P0 承重钉）：
- `pin31_terminated_word_dispatch`：废弃词结论的**分派**（判定序位 1，机械分派；
  判断在 `tool_matching`）；
- `pin14_fuzzy_window_ask_frame`：时间窗不能确定（载荷窗槽双 null）→ `ask` 反问（帧 `clarify`）；
- `pin16_chain_switch_once_boundary`：软失败域闸 → 换链回炉恰 1 次为界；
- `pin17_three_state_semantics_p0`：三态语义一字不动＋判定固定序命中即停＋零 LLM 面＋
  扩口未批不得直答终局。

本票另三条自有面（非规格表行）：`card_signature_and_shapes`（卡面签名＋四接口件逐字段）、
`public_face_is_package_root`（包根即公开面）、`no_bypass_on_public_faces`（只经 `tools` 公开面／
不引其它相位与旧码／不引模型出口——R1／R5／R6／R7／R8 import 面）。

真源：`specs/preconditions.md`（已定稿）／卡 `specs/modules.md` `## preconditions`；闸件＝
`appv2.tools.precondition`（只经其公开面 `judge`／`ledger_facts` 单点调用）。
"""

from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence
from dataclasses import fields
from datetime import date
from inspect import Parameter, signature
from pathlib import Path
from typing import Any

import pytest

import appv2.runtimev2.preconditions as preconditions
from appv2.knowledge import InMemoryKnowledgeStore, question_array_snapshot
from appv2.runtimev2.preconditions import (
    ASK_KIND_CALIBER_CLARIFY,
    ASK_KIND_EXTERNAL_TABLE_APPROVAL,
    ASK_KINDS,
    DECISION_ALLOW,
    DECISION_ASK,
    DECISION_REFUSE,
    DECISIONS,
    FRAME_KIND_BY_ASK_KIND,
    HIT_RULE_NONE,
    MENTION_EXECUTED,
    MENTION_MENTIONED_ONLY,
    MENTION_MODES,
    PAYLOAD_DECISION_KEY,
    PAYLOAD_HIT_RULE_KEY,
    PAYLOAD_NOTES_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REENTRY_KEY,
    PHASE,
    RULE_GATE_UNAVAILABLE,
    RULE_ORDER,
    AskReason,
    RefusalReason,
    SubtaskVerdict,
    gate_all,
)
from appv2.runtimev2.state import LIMIT_KINDS, RunState
from appv2.runtimev2.transport import ASK_FRAME_KINDS, NOTICE_TYPES
from appv2.tools import (
    DATA_QUERY,
    DOC_RETRIEVE,
    HIT_RULE_ASK,
    HIT_RULE_BAN,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FRESHNESS_WINDOW,
    HIT_RULE_FUZZY_WINDOW,
    HIT_RULE_SINGLE_WELL,
    HIT_RULE_UNREGISTERED_METRIC,
    dump_from_store,
)

# ── 底座（真源同产线一路：快照→读面→dump_from_store——词典层判定输入）────────────────

_STORE = InMemoryKnowledgeStore(question_array_snapshot(), today=date(2026, 10, 8))
LEDGER_DUMP = dump_from_store(_STORE)

WINDOW = {"window_start": "2025-09-01", "window_end": "2025-09-03"}
BOUND_PLAN = {"metric_slot": "日产油量", "ranking": False, **WINDOW}
WATERMARK = date(2026, 8, 31)

_PRECONDITIONS_DIR = Path(preconditions.__file__).resolve().parent


def _subtask(
    subtask_id: str, question: str, *, chain: str = "data", tool: str = DATA_QUERY
) -> dict[str, Any]:
    return {"id": subtask_id, "question": question, "chain": chain, "tool": tool}


def _match(
    subtask_id: str,
    *,
    chain: str = "data",
    tool: str = DATA_QUERY,
    plan: Mapping[str, Any] | None = None,
    retrieval_need: Mapping[str, Any] | None = None,
    mention_mode: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": subtask_id, "chain": chain, "tool": tool}
    if plan is not None:
        payload["plan"] = dict(plan)
    if retrieval_need is not None:
        payload["retrieval_need"] = dict(retrieval_need)
    if mention_mode is not None:
        payload["mention_mode"] = mention_mode
    return payload


def _knowledge_match(subtask_id: str) -> dict[str, Any]:
    return _match(
        subtask_id,
        chain="knowledge",
        tool=DOC_RETRIEVE,
        retrieval_need={"question": f"{subtask_id} 子问题原句"},
    )


def _state(
    *subtasks: Mapping[str, Any],
    matches: Sequence[Mapping[str, Any]] = (),
    **overrides: Any,
) -> RunState:
    state = RunState(
        run_id="run-preconditions",
        actor="dev-user",
        question="原题",
        question_group={"subtasks": [dict(item) for item in subtasks]},
        tool_matches=[dict(item) for item in matches],
        ledger_dump=LEDGER_DUMP,
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def _by_id(verdicts: Sequence[SubtaskVerdict]) -> dict[str, SubtaskVerdict]:
    return {verdict.subtask_id: verdict for verdict in verdicts}


def _payloads(state: RunState) -> list[Mapping[str, Any]]:
    return [
        step["payload"]
        for step in state.steps
        if isinstance(step, Mapping) and isinstance(step.get("payload"), Mapping)
    ]


def _with_risk_plan() -> dict[str, Any]:
    """指标在册（在册未绑定＝换链回炉触发面）＋窗已给定（位 2 不命中，位 5 命中）。"""
    return {"metric_slot": "产量完成率", "ranking": False, **WINDOW}


# ── 行 1：每子问题恰一条 verdict ────────────────────────────────────────────────


def test_exactly_one_verdict_per_subtask() -> None:
    """行 1｜每子问题**恰好一条** `SubtaskVerdict`；`subtask_id` 必须对上某子问题
    （对不上＝判失败）。"""
    state = _state(
        _subtask("s1", "各井日产油量"),
        _subtask("s2", "W-111 井完井报告", chain="knowledge", tool=DOC_RETRIEVE),
        matches=(_match("s1", plan=BOUND_PLAN), _knowledge_match("s2")),
    )
    verdicts = gate_all(state)

    assert [verdict.subtask_id for verdict in verdicts] == ["s1", "s2"]
    assert len(verdicts) == len(state.question_group["subtasks"])  # type: ignore[index]
    assert [item["subtask_id"] for item in state.precondition_verdicts] == ["s1", "s2"]

    # 上游契约违例＝判失败（fail-closed：缺组／支缺 id——不猜、不补、不跳过子问题）
    with pytest.raises(ValueError):
        gate_all(RunState(run_id="run-x", question_group=None))
    with pytest.raises(ValueError):
        gate_all(_state({"question": "没有 id 的支"}))
    # 形状把守：`subtask_id` 空＝判失败
    with pytest.raises(ValueError):
        SubtaskVerdict(subtask_id="", decision=DECISION_ALLOW)


# ── 行 2：三态闭世界 ────────────────────────────────────────────────────────────


def test_decision_enum_closed_world() -> None:
    """行 2｜`decision` 越界取值 → 判失败（三态闭世界：`allow`｜`refuse`｜`ask`）。"""
    assert DECISIONS == frozenset({DECISION_ALLOW, DECISION_REFUSE, DECISION_ASK})

    state = _state(
        _subtask("s1", "各井日产油量"),
        _subtask("s2", "各井老完成率"),
        _subtask("s3", "各井日产油量"),
        matches=(
            _match("s1", plan=BOUND_PLAN),
            _match("s2", plan=BOUND_PLAN),
            _match("s3", plan={"metric_slot": "日产油量", "ranking": False}),
        ),
    )
    verdicts = _by_id(gate_all(state))
    # 三态各态可达（放行／拒答／等用户）
    assert verdicts["s1"].decision == DECISION_ALLOW
    assert verdicts["s2"].decision == DECISION_REFUSE
    assert verdicts["s3"].decision == DECISION_ASK

    # 越界取值判失败（不猜、不取默认）；配对越界同判失败
    with pytest.raises(ValueError):
        SubtaskVerdict(subtask_id="s1", decision="blocked_ask")
    with pytest.raises(ValueError):
        SubtaskVerdict(
            subtask_id="s1",
            decision=DECISION_ALLOW,
            reason=AskReason(kind=ASK_KIND_CALIBER_CLARIFY, prompt="p"),
        )
    with pytest.raises(ValueError):
        AskReason(kind="other_kind", prompt="p")


# ── 行 3：判定序固定＋命中即停 ──────────────────────────────────────────────────


def test_fixed_order_short_circuit() -> None:
    """行 3｜判定序固定＋命中即停（打在序 3 上不进序 4）＋八位次序与明文表逐行一致。

    位 1 先于位 2、位 2 先于位 3：命中即出结论、不再往下（同一子问题不得乱序、不得并行判定）。
    """
    # 判定位条数＝8（6 主闸号＋2 子闸）且次序＝明文表位次逐字
    assert RULE_ORDER == (
        HIT_RULE_BAN,
        HIT_RULE_FUZZY_WINDOW,
        HIT_RULE_ASK,
        HIT_RULE_UNREGISTERED_METRIC,
        "normalized_slot",
        HIT_RULE_CHAIN_SWITCH,
        HIT_RULE_FRESHNESS_WINDOW,
        HIT_RULE_SINGLE_WELL,
    )
    assert len(RULE_ORDER) == 8 and len(set(RULE_ORDER)) == 8

    state = _state(
        # 位 1（禁用词）命中：不进位 2（窗双 null 也不出 ask）
        _subtask("s1", "各井老完成率"),
        # 位 2（窗不能确定）：不进位 3（计划申报了外表也不出审批 ask）
        _subtask("s2", "各井含油量"),
        # 位 3（外表越集）命中：不进位 4（口径非法也不再判——出审批 ask 而非拒答）
        _subtask("s3", "各井含水率数值"),
        matches=(
            _match("s1", plan={"metric_slot": "老完成率", "ranking": False}),
            _match(
                "s2",
                plan={
                    "metric_slot": "日产油量",
                    "ranking": False,
                    "external_tables": ["erp_well_register"],
                },
            ),
            _match(
                "s3",
                plan={
                    "metric_slot": "含水率",
                    "ranking": False,
                    "caliber_key": "Z",
                    "external_tables": ["erp_well_register"],
                    **WINDOW,
                },
            ),
        ),
    )
    verdicts = _by_id(gate_all(state))

    assert verdicts["s1"].decision == DECISION_REFUSE and verdicts["s1"].hit_rule == HIT_RULE_BAN
    assert verdicts["s2"].decision == DECISION_ASK
    assert verdicts["s2"].hit_rule == HIT_RULE_FUZZY_WINDOW
    assert verdicts["s3"].decision == DECISION_ASK and verdicts["s3"].hit_rule == HIT_RULE_ASK
    assert isinstance(verdicts["s3"].reason, AskReason)
    assert verdicts["s3"].reason.kind == ASK_KIND_EXTERNAL_TABLE_APPROVAL
    assert "erp_well_register" in verdicts["s3"].reason.prompt


# ── 行 4：注记并入放行 ──────────────────────────────────────────────────────────


def test_note_merges_into_allow() -> None:
    """行 4｜命中带注记的判定位 → `decision="allow"` 且 `notes` 非空（**不设第四态**）。"""
    state = _state(
        _subtask("s1", "N-01 井 2025-09-01 日产油量"),
        matches=(_match("s1", plan=BOUND_PLAN),),
    )
    verdict = _by_id(gate_all(state))["s1"]

    assert verdict.decision == DECISION_ALLOW
    assert verdict.notes and any("单井" in note for note in verdict.notes)
    assert verdict.reason is None
    assert verdict.hit_rule == HIT_RULE_NONE
    assert DECISIONS == frozenset({DECISION_ALLOW, DECISION_REFUSE, DECISION_ASK})  # 无第四态


# ── 行 5：外表越集（申报面）→ ask ───────────────────────────────────────────────


def test_declared_external_table_asks() -> None:
    """行 5｜外表越集（申报面）→ `ask`（kind=external_table_approval）＋唯一映射表对账。"""
    assert FRAME_KIND_BY_ASK_KIND == {
        ASK_KIND_EXTERNAL_TABLE_APPROVAL: "external_table_approval",
        ASK_KIND_CALIBER_CLARIFY: "clarify",
    }
    assert set(FRAME_KIND_BY_ASK_KIND.values()) <= ASK_FRAME_KINDS  # 帧侧闭世界真源（synth/S6 §一）
    assert set(FRAME_KIND_BY_ASK_KIND) == ASK_KINDS

    plan = {
        "metric_slot": "日产油量",
        "ranking": False,
        "external_tables": ["erp_well_register"],
        **WINDOW,
    }
    state = _state(_subtask("s1", "井位台账关联日产油量"), matches=(_match("s1", plan=plan),))
    verdict = _by_id(gate_all(state))["s1"]

    assert verdict.decision == DECISION_ASK
    assert verdict.hit_rule == HIT_RULE_ASK
    assert isinstance(verdict.reason, AskReason)
    assert verdict.reason.kind == ASK_KIND_EXTERNAL_TABLE_APPROVAL
    assert verdict.reason.options


# ── 行 6：恢复后消费 approved_ids 重判放行 ──────────────────────────────────────


def test_resume_reconsume_approved_ids() -> None:
    """行 6｜恢复后本块消费 `approved_ids` 重判放行（放行态注记随行、不重排计划）。"""
    plan = {
        "metric_slot": "日产油量",
        "ranking": False,
        "external_tables": ["erp_well_register"],
        **WINDOW,
    }
    state = _state(
        _subtask("s1", "井位台账关联日产油量"),
        matches=(_match("s1", plan=plan),),
        approved_ids=["erp_well_register"],
    )
    verdict = _by_id(gate_all(state))["s1"]

    assert verdict.decision == DECISION_ALLOW
    assert verdict.notes and any("放行" in note for note in verdict.notes)


# ── 行 7：换链回炉一次为界 ─────────────────────────────────────────────────────


def test_rewire_once_then_refuse() -> None:
    """行 7｜换链回炉只允许一次；二次触发 → `refuse`（记账面＝`state.chain_switch_marks`）。"""
    state = _state(
        _subtask("s1", "各井产量完成率数值"),
        matches=(_match("s1", plan=_with_risk_plan()),),
    )
    first = _by_id(gate_all(state))["s1"]

    assert first.decision == DECISION_ALLOW
    assert first.notes and any("换链" in note for note in first.notes)
    assert first.subtask_id in state.chain_switch_marks  # 一次为界：标记在册
    assert any(item["type"] == "chain_switch_reentry" for item in state.notices)

    second = _by_id(gate_all(state))["s1"]
    assert second.decision == DECISION_REFUSE
    assert second.hit_rule == HIT_RULE_CHAIN_SWITCH
    assert isinstance(second.reason, RefusalReason)
    assert second.reason.rule_id == HIT_RULE_CHAIN_SWITCH
    assert second.reason.human_text


# ── 行 8：可解释性（判定位＋人话＋替代项）───────────────────────────────────────


def test_refusal_has_rule_text_alternatives() -> None:
    """行 8｜非 `allow` 必带 `hit_rule` ＋ 人话；口径类拒答必带**替代项**（缺项＝判失败）。"""
    state = _state(
        # 口径支非法（指标在册：替代项＝该指标口径支 keys）
        _subtask("s1", "各井含水率数值"),
        # 指标不在台账（替代项＝台账名录）
        _subtask("s2", "各井采出程度数值"),
        matches=(
            _match(
                "s1",
                plan={"metric_slot": "含水率", "ranking": False, "caliber_key": "Z", **WINDOW},
            ),
            _match("s2", plan={"metric_slot": "采出程度", "ranking": False, **WINDOW}),
        ),
    )
    verdicts = _by_id(gate_all(state))

    for verdict in verdicts.values():
        assert verdict.decision == DECISION_REFUSE
        assert verdict.hit_rule == HIT_RULE_UNREGISTERED_METRIC
        assert isinstance(verdict.reason, RefusalReason)
        assert verdict.reason.rule_id == verdict.hit_rule
        assert verdict.reason.human_text  # 人话在场
        assert verdict.reason.alternatives  # 替代项非空（口径面结构化派生）
        assert verdict.as_payload()["reason"]["human_text"] == verdict.reason.human_text

    assert set(verdicts["s1"].reason.alternatives) == {"A", "B"}  # type: ignore[union-attr]
    assert "日产油量" in verdicts["s2"].reason.alternatives  # type: ignore[union-attr]

    # 形状把守：非 allow 缺 hit_rule／缺人话＝构造期判失败
    with pytest.raises(ValueError):
        SubtaskVerdict(
            subtask_id="s1",
            decision=DECISION_REFUSE,
            reason=RefusalReason(rule_id="x", human_text="y"),
        )
    with pytest.raises(ValueError):
        RefusalReason(rule_id="", human_text="y")


# ── 行 9：闸件抛错 → fail-closed ───────────────────────────────────────────────


class _ExplodingPlan(dict):  # type: ignore[type-arg]
    """闸件判定期抛错的注入面（判定器内部异常——非合法载荷；用于 fail-closed 取证）。"""

    def get(self, key: str, default: Any = None) -> Any:  # type: ignore[override]
        raise RuntimeError("闸件判定内部异常")


def test_gate_error_fail_closed() -> None:
    """行 9｜闸件抛错 → **不着 `allow`**（fail-closed），转 `refuse` 并带拒因，不静默放行。"""
    exploding = _state(
        _subtask("s1", "各井日产油量"),
        matches=(
            {"id": "s1", "chain": "data", "tool": DATA_QUERY, "plan": _ExplodingPlan(BOUND_PLAN)},
        ),
    )
    verdict = _by_id(gate_all(exploding))["s1"]
    assert verdict.decision == DECISION_REFUSE
    assert verdict.hit_rule == RULE_GATE_UNAVAILABLE
    assert isinstance(verdict.reason, RefusalReason)
    assert verdict.reason.human_text

    # 台账面不可用（闸件判定输入缺失）同口径 fail-closed
    broken = _state(
        _subtask("s1", "各井日产油量"),
        matches=(_match("s1", plan=BOUND_PLAN),),
        ledger_dump={"metrics": 5},
    )
    unavailable = _by_id(gate_all(broken))["s1"]
    assert unavailable.decision == DECISION_REFUSE
    assert unavailable.hit_rule == RULE_GATE_UNAVAILABLE


# ── 行 10：零 LLM 双证（本模块 ＋ 闸件）────────────────────────────────────────


_MODEL_CALL_NAMES = ("complete", "ainvoke", "invoke", "agenerate", "generate", "chat")
_MODEL_MODULES = (
    "litellm",
    "langchain",
    "langchain_core",
    "langgraph",
    "openai",
    "anthropic",
    "appv2.infra.llm_client",
    "appv2.infra.gateway",
    "appv2.runtimev2.gateway_adapter",
)
_REPO = Path(__file__).resolve().parents[2]


def _scan_trees(labeled_trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    findings: list[str] = []
    for label, tree in labeled_trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in _MODEL_MODULES:
                        findings.append(f"{label}:{node.lineno} import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module in _MODEL_MODULES:
                findings.append(f"{label}:{node.lineno} from {node.module}")
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in _MODEL_CALL_NAMES:
                    findings.append(f"{label}:{node.lineno} call {name}")
    return findings


def test_no_model_call_in_preconditions() -> None:
    """行 10｜本模块与闸件零 LLM（AST＋import 双证——R7／R8＋B6 的机检面）。"""
    sources = [
        *sorted(_PRECONDITIONS_DIR.glob("*.py")),
        _REPO / "appv2" / "tools" / "precondition.py",
    ]
    assert all(path.is_file() for path in sources), "扫描面不全"
    trees = [(path.name, ast.parse(path.read_text(encoding="utf-8"))) for path in sources]

    assert _scan_trees(trees) == []

    # 探测器非空转：伪造模型调用／模型出口 import 必被咬
    forged = ast.parse(
        "from appv2.runtimev2.gateway_adapter import complete\n"
        "import litellm\n"
        "def phase(state):\n"
        "    return complete([])\n"
    )
    assert len(_scan_trees([("forged.py", forged)])) == 3


# ── 行 11：程序侧无词表／正则语义判断 ───────────────────────────────────────────


_LEXICON_STR_METHODS = frozenset(
    {"startswith", "endswith", "lower", "upper", "casefold", "split", "partition", "count"}
)


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表／字面判据探测（字面集合含汉字串＝词表形；汉字字面成员判＝词面判）。"""
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
                    and not operand.value.isascii()
                ):
                    violations.append(f"L{node.lineno} 非结构字符集判据")
    return violations


def test_no_lexicon_or_regex_in_preconditions() -> None:
    """行 11｜程序侧无词表／正则语义判断（AST 扫描本模块；豁免面＝形态处理／集合成员判定）。"""
    sources = sorted(_PRECONDITIONS_DIR.glob("*.py"))
    assert sources, "扫描面为空"
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = path.name
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
        assert "re" not in imported and "regex" not in imported, f"{where} 引入正则面"
        assert not any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "re"
            for node in ast.walk(tree)
        ), f"{where} 使用 re.*"
        assert _lexicon_violations(tree) == [], f"{where}: {_lexicon_violations(tree)}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in _LEXICON_STR_METHODS, (
                    f"{where}:{node.lineno} 词面判方法 {node.func.attr}"
                )

    # 豁免面本体＝闭世界取值集与结构键名（非语义词表）
    assert all(value.isascii() for value in DECISIONS | ASK_KINDS | frozenset(RULE_ORDER))
    # 探测器非空转
    assert _lexicon_violations(ast.parse('WORDS = ["最近", "近期"]\n')) != []
    assert _lexicon_violations(ast.parse('if mode in ("提及", "执行"):\n    pass\n')) != []


# ── 行 12：判定结果的机读信号在场 ───────────────────────────────────────────────


def test_verdict_signal_present() -> None:
    """行 12｜判定结果的机读信号在场（step payload 的 `hit_rule`／`decision`／`notes`
    ＋ notice）。"""
    state = _state(
        _subtask("s1", "各井日产油量"),  # 普通放行：零额外信号（不产空 notice）
        _subtask("s2", "各井老完成率"),  # 拒答
        _subtask("s3", "各井日产油量"),  # 等待时间窗
        _subtask("s4", "N-01 井 2025-09-01 日产油量"),  # 带注记的放行
        matches=(
            _match("s1", plan=BOUND_PLAN),
            _match("s2", plan={"metric_slot": "老完成率", "ranking": False, **WINDOW}),
            _match("s3", plan={"metric_slot": "日产油量", "ranking": False}),
            _match("s4", plan=BOUND_PLAN),
        ),
    )
    verdicts = _by_id(gate_all(state))

    payloads = [payload for payload in _payloads(state) if payload.get(PAYLOAD_PHASE_KEY) == PHASE]
    assert [payload[PAYLOAD_DECISION_KEY] for payload in payloads] == [
        "allow",
        "refuse",
        "ask",
        "allow",
    ]
    assert [payload[PAYLOAD_HIT_RULE_KEY] for payload in payloads] == [
        HIT_RULE_NONE,
        HIT_RULE_BAN,
        HIT_RULE_FUZZY_WINDOW,
        HIT_RULE_NONE,
    ]
    # 静默放行是已知失败模式：`allow` 带注记时注记必须落在 step payload 里
    assert payloads[3][PAYLOAD_NOTES_KEY] == list(verdicts["s4"].notes)
    assert payloads[3][PAYLOAD_NOTES_KEY]
    assert payloads[0][PAYLOAD_NOTES_KEY] == []
    assert [payload[PAYLOAD_REENTRY_KEY] for payload in payloads] == [False, False, False, False]

    assert {item["type"] for item in state.notices} <= NOTICE_TYPES
    assert all(set(item) == {"type", "gates", "content"} for item in state.notices)
    assert all(set(item["gates"]) <= LIMIT_KINDS for item in state.notices)
    # 非 allow（s2 拒答／s3 等用户）与带注记的 allow（s4）各有 notice；普通放行（s1）零通知
    assert len(state.notices) == 3
    assert all(item["content"].startswith("前置条件机：") for item in state.notices)


# ── 行 13：【边界集】各自命中对应判定位 ─────────────────────────────────────────


def test_boundary_each_rule_hits() -> None:
    """行 13｜【边界集】空窗／越界水位／未绑定指标／单井不支持 → 各自命中对应判定位。"""
    state = _state(
        _subtask("s1", "各井日产油量"),  # 空窗（双 null）→ 位 2
        _subtask("s2", "各井日产油量"),  # 越界水位 → 位 7
        _subtask("s3", "各井产量完成率数值"),  # 未绑定指标 → 位 5（换链回炉面）
        _subtask("s4", "N-01 井 2025-09-01 日产油量"),  # 单井不支持 → 位 8
        matches=(
            _match("s1", plan={"metric_slot": "日产油量", "ranking": False}),
            _match(
                "s2",
                plan={
                    "metric_slot": "日产油量",
                    "ranking": False,
                    "window_start": "2026-01-01",
                    "window_end": "2026-10-08",
                },
            ),
            _match("s3", plan=_with_risk_plan()),
            _match("s4", plan=BOUND_PLAN),
        ),
    )
    verdicts = _by_id(gate_all(state, watermark=WATERMARK))

    assert verdicts["s1"].decision == DECISION_ASK
    assert verdicts["s1"].hit_rule == HIT_RULE_FUZZY_WINDOW
    assert verdicts["s2"].decision == DECISION_ALLOW
    assert any(str(WATERMARK) in note for note in verdicts["s2"].notes)
    assert verdicts["s3"].decision == DECISION_ALLOW
    assert any("未绑定" in note for note in verdicts["s3"].notes)
    assert verdicts["s4"].decision == DECISION_ALLOW
    assert any("单井" in note for note in verdicts["s4"].notes)


# ── 行 14：【保留集】普通放行行为不变 ───────────────────────────────────────────


def test_retention_plain_allow_unchanged() -> None:
    """行 14｜【保留集】`allow` 的普通子问题行为不变（无注记、无额外信号）。"""
    state = _state(
        _subtask("s1", "2025-09-01 到 09-03 各井日产油量"),
        _subtask(
            "s2",
            "W-111 井完井报告记载的投产初期日产油",
            chain="knowledge",
            tool=DOC_RETRIEVE,
        ),
        matches=(_match("s1", plan=BOUND_PLAN), _knowledge_match("s2")),
    )
    before_notices = len(state.notices)
    verdicts = gate_all(state)

    assert [verdict.decision for verdict in verdicts] == [DECISION_ALLOW, DECISION_ALLOW]
    for verdict in verdicts:
        assert verdict.notes == ()
        assert verdict.reason is None
        assert verdict.hit_rule == HIT_RULE_NONE
        assert verdict.as_payload()["reason"] is None
    assert len(state.notices) == before_notices  # 零额外信号
    payloads = [payload for payload in _payloads(state) if payload.get(PAYLOAD_PHASE_KEY) == PHASE]
    assert [payload[PAYLOAD_NOTES_KEY] for payload in payloads] == [[], []]


# ── pin 行：测试网钉 4 根 ───────────────────────────────────────────────────────


def test_pin31_terminated_word_dispatch() -> None:
    """pin-31（分派半边）｜废弃词结论的**分派**在判定序位 1（机械分派；判断在 `tool_matching`）。

    模型结论 `mentioned_only` → 放行（不按废弃口径出数）；结论 `executed` → 照闸件判（禁用户语
    命中＝拒答）。同一问句两结论两分派＝本块只照结论办事，不认字面、不猜意思。
    """
    question = "以前是不是把产液量叫老完成率"  # 词面命中禁用词（老完成率）
    assert MENTION_MODES == frozenset({MENTION_EXECUTED, MENTION_MENTIONED_ONLY})  # 两值闭世界
    state = _state(
        _subtask("s1", question),
        _subtask("s2", question),
        matches=(
            _match(
                "s1",
                plan={"metric_slot": "日产液量", "ranking": False, **WINDOW},
                mention_mode=MENTION_MENTIONED_ONLY,
            ),
            _match(
                "s2",
                plan={"metric_slot": "日产液量", "ranking": False, **WINDOW},
                mention_mode=MENTION_EXECUTED,
            ),
        ),
    )
    verdicts = _by_id(gate_all(state))

    assert verdicts["s1"].decision == DECISION_ALLOW
    assert verdicts["s1"].notes and any("仅提及" in note for note in verdicts["s1"].notes)
    assert verdicts["s2"].decision == DECISION_REFUSE
    assert verdicts["s2"].hit_rule == HIT_RULE_BAN


def test_pin14_fuzzy_window_ask_frame() -> None:
    """pin-14｜时间窗不能确定（载荷窗槽双 null＝结构判据）→ `ask` 走 clarify 反问帧。

    **不设「确定性词面门」**：问句带模糊时间词但窗已给定＝不反问；窗双 null＝反问（候选窗＝
    注入参 `window_candidates`）。
    """
    state = _state(
        _subtask("s1", "最近各井日产油量"),
        _subtask("s2", "最近各井日产油量"),
        matches=(
            _match("s1", plan={"metric_slot": "日产油量", "ranking": False}),
            _match("s2", plan=BOUND_PLAN),
        ),
    )
    candidates = ("近一月", "近三月", "本年度")
    verdicts = _by_id(gate_all(state, window_candidates=candidates))

    assert verdicts["s1"].decision == DECISION_ASK
    assert verdicts["s1"].hit_rule == HIT_RULE_FUZZY_WINDOW
    assert isinstance(verdicts["s1"].reason, AskReason)
    assert verdicts["s1"].reason.kind == ASK_KIND_CALIBER_CLARIFY
    assert FRAME_KIND_BY_ASK_KIND[verdicts["s1"].reason.kind] == "clarify"  # 帧侧唯一映射表
    assert verdicts["s1"].reason.options == candidates
    assert verdicts["s1"].reason.prompt

    # 词面不是判据：窗已给定 → 放行（不反问）
    assert verdicts["s2"].decision == DECISION_ALLOW


def test_pin16_chain_switch_once_boundary() -> None:
    """pin-16｜软失败域闸：题眼域↔链路域不一致 → 换链回炉**恰 1 次**为界，二次＝拒答终局。"""
    state = _state(
        _subtask("s1", "N-01 井 2025-09-01 日产油量"),
        matches=(_match("s1", plan=BOUND_PLAN),),
    )
    first = _by_id(gate_all(state, data_wells=("W-111",)))["s1"]
    second = _by_id(gate_all(state, data_wells=("W-111",)))["s1"]

    assert first.decision == DECISION_ALLOW
    assert first.hit_rule == HIT_RULE_NONE
    assert any("题眼井" in note for note in first.notes)
    assert state.chain_switch_marks.get("s1")
    assert second.decision == DECISION_REFUSE
    assert second.hit_rule == HIT_RULE_CHAIN_SWITCH
    assert isinstance(second.reason, RefusalReason)
    assert second.reason.human_text


def test_pin17_three_state_semantics_p0() -> None:
    """pin-17（P0）｜三态语义一字不动＋判定固定序命中即停＋零 LLM 面＋扩口未批不得直答终局。"""
    assert DECISIONS == frozenset({"allow", "refuse", "ask"})  # 三态一字不动（不设第四态）
    assert [field.name for field in fields(SubtaskVerdict)] == [
        "subtask_id",
        "decision",
        "notes",
        "reason",
        "hit_rule",
    ]

    # 零 LLM 面（R8）：本块不引闸件以外的模型出口（import 面断言）
    assert not any(name.endswith("gateway_adapter") for name in dir(preconditions))

    # 扩口未批不得直答终局：外表越集 → 等用户审批（ask），**不是**终局拒答／直答
    plan = {
        "metric_slot": "日产油量",
        "ranking": False,
        "external_tables": ["erp_well_register"],
        **WINDOW,
    }
    state = _state(_subtask("s1", "井位台账关联日产油量"), matches=(_match("s1", plan=plan),))
    verdict = _by_id(gate_all(state))["s1"]
    assert verdict.decision == DECISION_ASK
    assert verdict.decision != DECISION_REFUSE
    assert isinstance(verdict.reason, AskReason)
    assert verdict.reason.kind == ASK_KIND_EXTERNAL_TABLE_APPROVAL


# ── 自有面（卡面签名／包根公开面／无旁路）──────────────────────────────────────


def test_card_signature_and_shapes() -> None:
    """卡面签名（`gate_all(state, *, window_candidates=None)`——实参形不动）＋四形状字段齐。"""
    parameters = list(signature(gate_all).parameters.values())
    assert parameters[0].name == "state"
    assert parameters[0].kind is Parameter.POSITIONAL_OR_KEYWORD
    assert all(parameter.kind is Parameter.KEYWORD_ONLY for parameter in parameters[1:])
    assert parameters[1].name == "window_candidates" and parameters[1].default is None
    assert {parameter.name for parameter in parameters[1:]} == {
        "window_candidates",
        "watermark",
        "data_wells",
    }
    assert all(parameter.default is None for parameter in parameters[1:])

    assert [field.name for field in fields(RefusalReason)] == [
        "rule_id",
        "human_text",
        "alternatives",
    ]
    assert [field.name for field in fields(AskReason)] == ["kind", "prompt", "options"]


def test_public_face_is_package_root() -> None:
    """包根即公开面（R2）：形状与闭世界常量全经 `appv2.runtimev2.preconditions` 可取。"""
    for name in (
        "gate_all",
        "SubtaskVerdict",
        "RefusalReason",
        "AskReason",
        "DECISIONS",
        "ASK_KINDS",
        "FRAME_KIND_BY_ASK_KIND",
        "RULE_ORDER",
        "MENTION_MODES",
    ):
        assert name in preconditions.__all__
        assert hasattr(preconditions, name)
    assert "core" not in preconditions.__all__ and "models" not in preconditions.__all__


def test_no_bypass_on_public_faces() -> None:
    """无旁路（R1／R5／R6／R7／R8 import 面）：不引其它相位／旧码／引擎直引／模型出口。"""
    forbidden = (
        "appv2.runtime",  # R5（旧码）
        "appv2.knowledge",  # R6（引擎只经 tools 公开面）
        "appv2.query",
        "appv2.retrieval",
        "appv2.infra.llm_client",  # R7
        "appv2.runtimev2.gateway_adapter",  # R8
        "appv2.runtimev2.understanding",
        "appv2.runtimev2.clarification",
        "appv2.runtimev2.tool_matching",
        "appv2.runtimev2.execution",
        "appv2.runtimev2.answering",
        "appv2.runtimev2.verification",  # R1（相位互不 import）
    )
    # R2：公共层只经包根（业务相位不得直引公共层深层子模块）
    common_layers = (
        "appv2.runtimev2.state",
        "appv2.runtimev2.bookkeeping",
        "appv2.runtimev2.parsing",
        "appv2.runtimev2.prompts",
        "appv2.runtimev2.context",
        "appv2.runtimev2.transport",
        "appv2.runtimev2.persistence",
        "appv2.runtimev2.gateway_adapter",
    )
    for path in sorted(_PRECONDITIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for module in sorted(imported):
            assert module not in forbidden, f"{path.name} 触界 import {module}"
            assert not any(
                module.startswith(f"{layer}.") for layer in common_layers
            ), f"{path.name} 直引公共层深层 {module}"
