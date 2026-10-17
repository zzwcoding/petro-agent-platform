"""state 块验收（RT-W1-01a 骨架／-01b 常量族与限额触界面）。

票面对象＝`specs/state.md`「验收测试」表第 1–8、15、16 行（-a 逐字，测试标识同规格列）；
测试网钉＝pin-22（`::messages_append_only_prefix`）／pin-23（`::followup_seeds_full_chain`）／
pin-24（`::contracts_appended_idempotent`）／pin-26（`::dialogue_layer_purity`）／
pin-29 形状面（`::ask_payload_shape_closed_world`）／
pin-30 状态字段面（`::legacy_checkpoint_read_honest`）。

票面对象（RT-W1-01b）＝同表第 9、10、11、12、13、14、17、18、19 行（常量族与限额触界面／元／
边界·保留集），行序与规格列逐字一致。

字段集真源＝`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（本件**真读该文件解析**，
不硬编码字段名——硬编码即失去防漂移意义）；限额数值真源＝`docs/runtime-refactor/recon/K-上下文
事件指南预算.md` R-K-72…R-K-76（本件以期望值逐键钉住，代码侧单点在 `state.constants`）。
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import AsyncIterator, Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path
from typing import Any

import pytest

from appv2.infra.security import Actor
from appv2.runtimev2.state import (
    ASK_CAP,
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    INTENT,
    INTENT_ANSWER,
    LIMIT_KINDS,
    MAX_DISCOVERS_PER_ROUND,
    MAX_DISCOVERS_PER_RUN,
    MAX_EXECUTES_PER_ROUND,
    MAX_ROUNDS,
    RUN_COMPLETED,
    RUN_RUNNING,
    RUN_STATUS_KINDS,
    RUN_WAITING_ASK,
    STEP_DECISION,
    STEP_DISCOVER,
    STEP_EXECUTE,
    STEP_KINDS,
    TOOL_TIMEOUT_SECONDS,
    TOTAL_SECONDS,
    AskChoice,
    AskRequest,
    Budget,
    Convergence,
    LimitHit,
    Manifest,
    RunHandle,
    RunState,
    check_limits,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_S5_MATRIX = _REPO_ROOT / "docs" / "runtime-refactor" / "synth" / "S5-RunState字段矩阵.md"
_STATE_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "state"
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"

# 规格 行为 6 明列的来源闭世界三值（逐字：user_verbatim／assistant_final／clarify_approval_replay）
_SPEC_DIALOGUE_ORIGINS = {"user_verbatim", "assistant_final", "clarify_approval_replay"}
# 规格 行为 2 明列的不可变载荷七类
_SPEC_IMMUTABLE_SHAPES = {
    "Manifest",
    "AskRequest",
    "AskChoice",
    "RunHandle",
    "Budget",
    "Convergence",
    "LimitHit",
}


def _actor() -> Actor:
    return Actor(user_id="laowang", display="老王 · 油藏工程师")


async def _frames(*items: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """帧流替身（本块不产帧——只验证 `RunHandle.stream` 的形状位）。"""
    for item in items:
        yield item


def _full_state() -> RunState:
    """全字段 fixture：首列 53 字段逐字段落非缺省值（行为 3 用；V2-82a 追加 `subjects`／`terms`，
    V2-82b 追加 `pending_subject_options`）。"""
    return RunState(
        run_id="run-1",
        question="渤海某井 2026 年日产油量？",
        actor="laowang",
        status="waiting_ask",
        followup_of="run-0",
        empty_probes=['{"tool": "discover", "args": {}}'],
        understanding="用户问某井产量。",
        metric_candidates=["oil_rate"],
        subjects=("W-11",),
        terms=("日产油量",),
        ledger_dump={"oil_rate": {"unit": "m3/d"}},
        question_group={"subtasks": [{"id": "s1", "question": "某井产量"}]},
        tool_matches=[{"id": "s1", "tool": "data_query", "chain": "data"}],
        precondition_verdicts=[{"id": "s1", "state": "pass"}],
        subtask_results=[{"id": "s1", "status": "ok", "obs_count": 1}],
        chain_switch_marks={"s1": "fp-chain-1"},
        window_miss_marks={"s1": "fp-miss-1"},
        discover_used=2,
        messages=[
            {"role": "user", "content": "任务书"},
            {"role": "assistant", "content": "决策"},
        ],
        contracts_appended=["clarify"],
        process_notes=[{"role": "assistant", "content": "过程摘要（≤200）"}],
        dialogue=[
            {"role": "user", "content": "渤海某井 2026 年日产油量？", "origin": "user_verbatim"}
        ],
        dialogue_view_tokens=1234,
        schema_version=3,
        rounds=2,
        task_type="data",
        decision_error="schema 校验失败",
        user_hint="按月度聚合",
        budget_reject_streak=1,
        pending_discovers=[{"tool": "discover", "args": {}}],
        pending_plan={"plan": []},
        pending_retrieval={"args": {"q": "某井"}},
        last_execute={"payload": "x"},
        executed_payloads=["fp-exec-1"],
        tool_retries={"data_query": 1},
        extable_rounds=1,
        last_result={"ok": True},
        pending_ask={"kind": "clarify", "options": ["①"]},
        pending_subject_options=("渤中油田",),
        observations=[{"n": 1, "text": "某井日产 100 m3/d"}],
        resume_choices=[{"choice": "选窗①"}],
        approved_ids=["ap-1"],
        draft="草稿文本",
        draft_kind="",
        answer="某井 2026 年日产油量 100 m3/d。",
        verdict={"pass": True},
        manifest_digest="0" * 64,
        notices=[{"type": "notice", "gates": [], "content": "…"}],
        steps=[{"seq": 1, "kind": "decision", "title": "决策"}],
        budget=Budget(),
        budget_hit=["rounds"],
        next_intent="answer",
        error=None,
    )


def _matrix_fields() -> set[str]:
    """真读 `synth/S5` §一 字段矩阵，取首列字段名集合。"""
    names: set[str] = set()
    in_section = False
    for line in _S5_MATRIX.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_section = line.startswith("## 一、字段矩阵")
            continue
        if not in_section:
            continue
        matched = re.match(r"^\|\s*`([^`]+)`\s*\|", line)
        if matched:
            names.add(matched.group(1))
    return names


def _is_prefix_extended(prev: list[dict[str, str]], last: list[dict[str, str]]) -> bool:
    """规格 行为 4 原式：`后[:-len(尾段)] == 前`（尾段＝后链超出前链的部分）。"""
    tail = last[len(prev) :]
    return bool(tail) and last[: len(last) - len(tail)] == prev


def _call_model(state: RunState, sent: list[list[dict[str, str]]]) -> None:
    """模型调用＝发送**整链**（快照，防后续追加改动已发送面）。"""
    sent.append([dict(message) for message in state.messages])


def _enter_phase(state: RunState, phase: str, contract: dict[str, str]) -> None:
    """相位进入：首次追加合同文本并落标记；回炉轮不重发（`contracts_appended` 为把守）。"""
    if phase in state.contracts_appended:
        return
    state.messages.append(contract)
    state.contracts_appended.append(phase)


def _append_dialogue(state: RunState, *, role: str, content: str, origin: str) -> None:
    """对话层追加（写入点即拒的模型——正身写口在 `bookkeeping.append_dialogue`）。"""
    if origin not in DIALOGUE_ORIGINS:
        raise ValueError(f"origin 越界（来源闭世界外）：{origin!r}")
    if DIALOGUE_ORIGIN_ROLES[origin] != role:
        raise ValueError(f"origin↔role 不一致：{origin!r} ↔ {role!r}")
    state.dialogue.append({"role": role, "content": content, "origin": origin})


def _state_sources() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_STATE_DIR.rglob("*.py"))
    ]


def _dialogue_attribute_sites(tree: ast.Module) -> list[int]:
    """本块源码中一切 `*.dialogue` 属性访问位点（读或写）——用于「零业务写」AST 证。"""
    return [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "dialogue"
    ]


# ---------- 1 字段集单点（行为 1） ----------


def test_field_set_matches_matrix() -> None:
    """字段集与 `synth/S5` 矩阵一致（集合比较，不判顺序）。"""
    matrix = _matrix_fields()
    assert matrix, "S5 矩阵 §一 解析为空——解析式失效（非字段集失配）"
    # 定稿 50 ＋ V2-82a 追加 2（`subjects`／`terms`，2026-10-17）＋ V2-82b 追加 1
    # （`pending_subject_options`，2026-10-17）＝现行 53
    assert len(matrix) == 53, f"S5 矩阵 §一 字段数应为现行 53，实为 {len(matrix)}"
    assert {f.name for f in fields(RunState)} == matrix


# ---------- 2 两类形态（行为 2） ----------


def test_mutability_split() -> None:
    """不可变载荷全 `frozen+slots`、`RunState` 可变。"""
    instances: list[object] = [
        Manifest(),
        AskRequest(question="问", actor=_actor()),
        AskChoice(kind="clarify"),
        RunHandle(run_id="run-1", stream=_frames(), cursor=0),
        Budget(),
        LimitHit(limit="rounds", used=1.0, cap=3.0),
        Convergence(hit=(), notice=None),
    ]
    assert {type(obj).__name__ for obj in instances} == _SPEC_IMMUTABLE_SHAPES
    for obj in instances:
        cls = type(obj)
        assert cls.__dataclass_params__.frozen is True, cls.__name__
        assert not hasattr(obj, "__dict__"), f"{cls.__name__} 缺 slots"
        with pytest.raises(FrozenInstanceError):
            setattr(obj, fields(cls)[0].name, None)

    state = RunState(run_id="run-1")
    state.status = "waiting_ask"
    state.messages.append({"role": "user", "content": "问"})
    assert (state.status, len(state.messages)) == ("waiting_ask", 1)


# ---------- 3 状态可投影（行为 3） ----------


def test_state_json_projectable() -> None:
    """全字段 JSON 可投影（跨进程恢复无损前提）。"""
    state = _full_state()
    loaded = json.loads(json.dumps(asdict(state), ensure_ascii=False))
    assert set(loaded) == {f.name for f in fields(RunState)}
    assert loaded["budget"] == asdict(Budget())


# ---------- 4 `messages` 只追加（pin-22，P0） ----------


def test_messages_append_only_prefix() -> None:
    """`messages` 只追加：相邻调用互为前缀延伸。"""
    state = RunState(run_id="run-1", messages=[{"role": "user", "content": "任务书"}])
    sent: list[list[dict[str, str]]] = []

    _call_model(state, sent)  # 首轮调用
    state.messages.append({"role": "assistant", "content": "决策"})
    _call_model(state, sent)  # 第二轮调用
    state.messages.append({"role": "user", "content": "观察"})
    _call_model(state, sent)  # 第三轮调用

    assert len(sent) == 3
    assert _is_prefix_extended(sent[0], sent[1])
    assert _is_prefix_extended(sent[1], sent[2])

    # 任何替换／重排历史条＝判失败（前缀关系被打破）
    replaced = [{"role": "user", "content": "任务书（改写）"}, *sent[2][1:]]
    reordered = [sent[2][1], sent[2][0], *sent[2][2:]]
    assert not _is_prefix_extended(sent[0], replaced)
    assert not _is_prefix_extended(sent[1], reordered)


# ---------- 5 相位合同一次性（pin-24） ----------


def test_contracts_appended_idempotent() -> None:
    """相位合同一次性：回炉轮不重发、标记幂等。"""
    state = RunState(run_id="run-1")
    contract = {"role": "user", "content": "clarify 相位合同"}

    _enter_phase(state, "clarify", contract)
    after_first = (len(state.messages), list(state.contracts_appended))

    _enter_phase(state, "clarify", contract)  # 回炉轮二次进入
    assert len(state.messages) == after_first[0], "回炉轮重发了相位合同"
    assert state.messages.count(contract) == 1
    assert state.contracts_appended == after_first[1]
    assert state.contracts_appended.count("clarify") == 1


# ---------- 6 对话层纯度（pin-26） ----------


def test_dialogue_layer_purity() -> None:
    """对话层纯度：`dialogue` 条目 `origin` 全部落在来源闭世界内（不混层）。"""
    assert set(DIALOGUE_ORIGINS) == _SPEC_DIALOGUE_ORIGINS  # 闭世界不经裁决不许长胖

    state = RunState(run_id="run-1")
    state.process_notes.append({"role": "user", "content": "任务书：回答用户问题"})
    state.process_notes.append({"role": "assistant", "content": "相位指令：clarify 合同"})
    _append_dialogue(state, role="user", content="渤海某井日产多少？", origin="user_verbatim")
    _append_dialogue(state, role="assistant", content="答案是…", origin="assistant_final")
    _append_dialogue(state, role="user", content="选窗①", origin="clarify_approval_replay")

    for entry in state.dialogue:
        assert set(entry) == {"role", "content", "origin"}
        assert entry["origin"] in DIALOGUE_ORIGINS
        assert entry["role"] == DIALOGUE_ORIGIN_ROLES[entry["origin"]]
    assert {entry["origin"] for entry in state.dialogue} == _SPEC_DIALOGUE_ORIGINS

    # 过程内容要混进 dialogue 只能伪造来源标签——伪造即越界被抓
    with pytest.raises(ValueError):
        _append_dialogue(state, role="assistant", content="相位指令", origin="process_note")
    with pytest.raises(ValueError):
        _append_dialogue(
            state, role="user", content="助手终稿冒充用户原话", origin="assistant_final"
        )


# ---------- 7 追问播种＝前轮终链整链承接（pin-23，P0） ----------


def test_followup_seeds_full_chain() -> None:
    """追问播种＝前轮终链整链承接（跨 run 前缀延伸）。"""
    prev = RunState(
        run_id="run-1",
        messages=[
            {"role": "user", "content": "任务书"},
            {"role": "assistant", "content": "决策"},
            {"role": "assistant", "content": "终稿"},
        ],
    )
    prev_terminal_chain = [dict(message) for message in prev.messages]
    follow_up = RunState(
        run_id="run-2",
        followup_of=prev.run_id,
        messages=[*prev_terminal_chain, {"role": "user", "content": "那 2025 年呢？"}],
    )

    assert follow_up.followup_of == prev.run_id
    prefix_len = len(prev_terminal_chain)
    assert follow_up.messages[:prefix_len] == prev.messages  # 不裁剪、不摘要化
    assert follow_up.messages[prefix_len:] == [{"role": "user", "content": "那 2025 年呢？"}]


# ---------- 8 旧检查点如实读入（pin-30 状态字段面） ----------

# v1 旧检查点（`recon/I2b` 旧码 53 字段面：含已取消四字段与 `budget` 裸 dict）
_V1_CHECKPOINT: dict[str, Any] = {
    "run_id": "run-v1",
    "question": "旧问句",
    "actor": "laowang",
    "status": "completed",
    "followup_of": "",
    "empty_probes": [],
    "understanding": "旧理解",
    "metric_candidates": [],
    "ledger_dump": None,
    "question_group": None,
    "tool_matches": [],
    "precondition_verdicts": [],
    "subtask_results": [],
    "chain_switch_marks": {},
    "window_miss_marks": {},
    "discover_used": 0,
    "messages": [{"role": "user", "content": "旧任务书"}],
    "contracts_appended": [],
    "process_notes": [],
    "dialogue": [{"role": "user", "content": "旧对话"}],
    "schema_version": 1,
    "rounds": 1,
    "task_type": "data",
    "decision_error": "",
    "user_hint": "",
    "budget_reject_streak": 0,
    "pending_discovers": [],
    "pending_plan": None,
    "pending_retrieval": None,
    "last_execute": None,
    "executed_payloads": [],
    "consecutive_asks": 0,  # 已取消（流水 49①）
    "tool_retries": {},
    "extable_rounds": 0,
    "last_result": None,
    "pending_ask": None,
    "observations": [],
    "resume_choices": [],
    "approved_ids": [],
    "draft": "",
    "draft_kind": "",
    "answer": "旧答案",
    "verdict": None,
    "manifest_digest": "",
    "notices": [],
    "manifests": [],  # 已取消（流水 49①）
    "steps": [],
    "budget": {  # v1 裸 dict（D-I2b-03）
        "rounds": 3,
        "discovers_per_round": 2,
        "unknown_legacy_key": 1.0,
    },
    "started_monotonic": 0.0,  # 已取消（流水 49①）
    "deadline_monotonic": 0.0,  # 已取消（流水 49①）
    "budget_hit": [],
    "next_intent": "",
    "error": None,
}


def _is_v2_dialogue_entry(entry: Any) -> bool:
    """v2 条目形态＝固定三键 `{role, content, origin}` 且 origin 落在来源闭世界内。"""
    return (
        isinstance(entry, dict)
        and set(entry) == {"role", "content", "origin"}
        and entry["origin"] in DIALOGUE_ORIGINS
    )


def _read_v1_checkpoint(payload: Mapping[str, Any]) -> RunState:
    """旧检查点读入：未知键丢弃、缺字段补缺省、`schema_version` 取读入态（禁伪造历史）。"""
    known = {f.name for f in fields(RunState)}
    kwargs = {key: value for key, value in payload.items() if key in known}
    if isinstance(kwargs.get("budget"), dict):
        budget_keys = {f.name for f in fields(Budget)}
        converted = {k: v for k, v in kwargs["budget"].items() if k in budget_keys}
        kwargs["budget"] = Budget(**converted)
    entries = kwargs.get("dialogue")
    if isinstance(entries, list):
        # v1 条目只有 {role, content}、无来源标签（recon/I2b）——补标即伪造历史，故不承接
        kwargs["dialogue"] = [entry for entry in entries if _is_v2_dialogue_entry(entry)]
    return RunState(**kwargs)


def test_legacy_checkpoint_read_honest() -> None:
    """旧检查点如实读入（不抛错、对话通道空显、`schema_version` 如实）。"""
    state = _read_v1_checkpoint(_V1_CHECKPOINT)  # 不抛错
    assert state.schema_version == 1  # 取读入态（非缺省 3）
    assert state.dialogue == []  # 对话通道空显——不伪造、不补写历史
    assert state.answer == "旧答案"
    assert state.budget.rounds == 3  # v1 裸 dict 按七键转 Budget（缺键取缺省）
    assert state.budget.ask_cap == Budget().ask_cap
    assert not hasattr(state, "consecutive_asks")  # 已取消字段不复活

    # `dialogue` 无本块写入点（AST＋行为双证）
    for path, tree in _state_sources():
        assert _dialogue_attribute_sites(tree) == [], f"{path} 出现 .dialogue 访问位点"
    forged = ast.parse("state.dialogue.append(entry)")
    assert _dialogue_attribute_sites(forged) == [1]  # 探测器非空转


# ---------- 15 受理三形态互斥（pin-29 形状面） ----------


def test_ask_payload_shape_closed_world() -> None:
    """受理三形态互斥、`AskChoice` 两枚举闭世界。"""
    actor = _actor()
    assert AskRequest(question="问", actor=actor).question == "问"
    assert AskRequest(resume_run_id="run-1", actor=actor).resume_run_id == "run-1"
    ask_follow_up = AskRequest(question="问", followup_run_id="run-0", actor=actor)
    assert ask_follow_up.followup_run_id == "run-0"

    with pytest.raises(ValueError):  # resume_run_id 与 followup_run_id 同在场＝判失败
        AskRequest(resume_run_id="run-1", followup_run_id="run-0", actor=actor)

    closed_world = (
        ("clarify", None),
        ("clarify", "approve"),
        ("external_table_approval", "reject"),
    )
    for kind, decision in closed_world:
        choice = AskChoice(kind=kind, choice="选窗①", decision=decision, approval_id="ap-1")
        assert (choice.kind, choice.decision) == (kind, decision)
    with pytest.raises(ValueError):  # kind 越界
        AskChoice(kind="approval")
    with pytest.raises(ValueError):  # decision 越界
        AskChoice(kind="clarify", decision="ok")


# ---------- 16 Manifest 全键恒出（行为 15） ----------


def test_manifest_all_keys_and_copy() -> None:
    """`Manifest.as_dict` 全键恒出＋列表拷贝语义。"""
    empty = Manifest()  # 无参可构造（recon/I2a R-I2a-05）
    assert empty.transform == "filter→rank→budget→cite"
    assert empty.material_total == 0
    assert empty.material_rendered == 0
    assert empty.material_truncated is False

    manifest = Manifest(
        source_type=["kb"],
        source_id=["doc-1"],
        version=[None],
        trust_level=["high"],
        token_count=12,
    )
    projected = manifest.as_dict()
    assert set(projected) == {f.name for f in fields(Manifest)}  # 全键恒出
    for name in ("source_type", "source_id", "version", "trust_level"):
        assert projected[name] == getattr(manifest, name)
        assert projected[name] is not getattr(manifest, name)  # 列表值返回拷贝
    projected["source_type"].append("伪造")
    assert manifest.source_type == ["kb"]  # 改返回值不改原对象


# ---------- 9 三族常量闭世界（行为 9） ----------

# 取值与条数真源＝`recon/I2a-状态常量与清单.md`（22 条常量实测：STEP×6＋STEP_KINDS｜
# RUN×4＋RUN_STATUS_KINDS｜INTENT×10）——本件以期望值钉住，代码侧单点在 `state.constants`。
_SPEC_STEP_KINDS = {"decision", "discover", "execute", "observe", "verify", "answer"}
_SPEC_RUN_STATUS_KINDS = {"running", "waiting_ask", "completed", "failed"}
_SPEC_INTENT = {
    "decision",
    "discover",
    "execute",
    "observe",
    "verify",
    "answer",
    "end",
    "toolmatch",
    "precondition",
    "batch",
}


def test_constant_families_closed_world() -> None:
    """三族常量闭世界：越界取值抛错。"""
    assert STEP_KINDS == _SPEC_STEP_KINDS
    assert RUN_STATUS_KINDS == _SPEC_RUN_STATUS_KINDS
    assert INTENT == _SPEC_INTENT
    assert (len(STEP_KINDS), len(RUN_STATUS_KINDS), len(INTENT)) == (6, 4, 10)
    for family in (STEP_KINDS, RUN_STATUS_KINDS, INTENT):
        assert isinstance(family, frozenset)  # 闭世界不可变（运行期不可增删）

    # 越界取值抛错（把守面＝状态字段构造期 ＋ 步记录计数面）
    with pytest.raises(ValueError):
        RunState(run_id="run-1", status="paused")
    with pytest.raises(ValueError):
        RunState(run_id="run-1", next_intent="clarify")
    with pytest.raises(ValueError):
        check_limits(RunState(run_id="run-1", steps=[{"seq": 1, "step": "reflect"}]))

    # 族内取值不抛（含未设空串——`next_intent` 字段缺省）
    for status in sorted(RUN_STATUS_KINDS):
        assert RunState(run_id="run-1", status=status).status == status
    for intent in sorted(INTENT):
        assert RunState(run_id="run-1", next_intent=intent).next_intent == intent
    assert RunState(run_id="run-1").next_intent == ""

    # 每族必须有真实消费点（禁「定义了没人用」）：族名在本块常量定义处之外有引用位点
    consumers = {
        family: sum(
            _name_uses(tree, family)
            for path, tree in _state_sources()
            if path.name != "constants.py"
        )
        for family in ("STEP_KINDS", "RUN_STATUS_KINDS", "INTENT")
    }
    assert all(count >= 1 for count in consumers.values()), consumers


def _name_uses(tree: ast.Module, name: str) -> int:
    """源码里按名引用某符号的位点数（消费点机检用）。"""
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == name)


# ---------- 10 常量单点消费（行为 9） ----------


def _v2_sources() -> list[tuple[Path, ast.Module]]:
    """全 V2 树源码（旧码 `appv2/runtime/` 是重构退役面、不在本批改动面——不入扫描域）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _str_collections(tree: ast.Module) -> list[tuple[int, set[str]]]:
    """源码里一切字符串集合字面量／`set|frozenset(...)` 的元素集（「第二处自建集合」扫描用）。"""
    found: list[tuple[int, set[str]]] = []
    for node in ast.walk(tree):
        elements: list[ast.expr] = []
        if isinstance(node, (ast.Set, ast.Tuple, ast.List)):
            elements = list(node.elts)
        elif isinstance(node, ast.Dict):
            elements = [key for key in node.keys if key is not None]
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"set", "frozenset"}
        ):
            for argument in node.args:
                if isinstance(argument, (ast.Set, ast.Tuple, ast.List)):
                    elements.extend(argument.elts)
        else:
            continue
        strings = {
            element.value
            for element in elements
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
        if strings:
            found.append((node.lineno, strings))
    return found


def _guarding_literals(tree: ast.Module) -> list[tuple[int, str]]:
    """参与把守的裸字面量：比较（`==`／`!=`）与成员测试（`in`／`not in`）表达式里的字符串常量。"""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                found.append((sub.lineno, sub.value))
    return found


def _is_three_family_copy(values: set[str], families: frozenset[str]) -> bool:
    """该集合字面量是否为三族的**第二处自建集合**——元素**全落在**三族取值域内。

    真面＝禁复制 `STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT` 三族的集合／元组字面（整族复制与
    子集复制都算）；掺进族外取值即非族复制——与族取值**同名巧合**的合法集合（子问题状态三值、
    步记录 status 三值）不受牵连（2026-10-16 收紧·W3 前微修正批：原「扫全 V2 树的集合形裸字面
    × 三族取值**交集**」口径偏宽，误咬合法集合，见 `docs/runtime-refactor/00-决议与方法.md`
    流水 53 登记）。
    """
    return bool(values) and values <= families


def test_no_second_source_of_constants() -> None:
    """常量单点消费：无第二处自建集合、无裸状态字面量把守。

    集合面口径（2026-10-16 收紧）：只钉「**三族常量的第二处自建集合**」——字面集合／元组的
    字符串元素**全落在**三族取值域内才判失败（判据＝`_is_three_family_copy`）；裸字面量把守面
    口径不变（参与把守的字面量恰为族取值才判失败）。
    """
    # 包根 re-export 与定义处同一对象（不复制集合）
    from appv2.runtimev2.state import constants as constants_module

    assert STEP_KINDS is constants_module.STEP_KINDS
    assert RUN_STATUS_KINDS is constants_module.RUN_STATUS_KINDS
    assert INTENT is constants_module.INTENT

    families = STEP_KINDS | RUN_STATUS_KINDS | INTENT
    self_built: dict[str, list[int]] = {}
    bare_guards: dict[str, list[str]] = {}
    for path, tree in _v2_sources():
        if path == _STATE_DIR / "constants.py":  # 单一真源处（族名与取值的唯一定义点）
            continue
        for line, values in _str_collections(tree):
            if _is_three_family_copy(values, families):
                self_built.setdefault(path.name, []).append(line)
        for line, literal in _guarding_literals(tree):
            if literal in families:
                bare_guards.setdefault(path.name, []).append(f"{line}:{literal}")
    assert not self_built, f"出现第二处自建状态集合：{self_built}"
    assert not bare_guards, f"出现裸状态字面量把守：{bare_guards}"

    # 探测器非空转（两类探测器各在伪造源上命中）
    forged = ast.parse(
        '_S = frozenset({"running", "failed"})\n'
        'if state.status == "running":\n'
        "    pass\n"
        'if state.status in ("completed", "failed"):\n'
        "    pass\n"
    )
    assert any(_is_three_family_copy(values, families) for _, values in _str_collections(forged))
    assert {literal for _, literal in _guarding_literals(forged)} == {
        "running",
        "completed",
        "failed",
    }

    # 合法面回归（收紧后不咬「同名巧合的非族集合」——流水 53 登记的口径偏宽面）：
    # ① 伪造源照现文形写出（prompts 子问题状态三值／persistence 步记录 status 三值／
    #    prompts 决策轮中文触发词）——含与族同名的 `failed`，旧口径必咬、新口径放行；
    coincidental = ast.parse(
        '_SUBTASK_MARKS = {"ok": "完成", "refused": "已拒答", "failed": "失败"}\n'
        '_STEP_STATUSES = ("ok", "failed", "refused")\n'
        '_REROUTE_TRIGGERS = ("未绑定", "不在台账")\n'
    )
    assert any(  # 旧口径（元素与族有交集即咬）：同名巧合面必咬
        values & families for _, values in _str_collections(coincidental)
    )
    assert not any(  # 新口径：放行（元素未全落在三族内＝非三族复制）
        _is_three_family_copy(values, families) for _, values in _str_collections(coincidental)
    )
    # ② 现文（真文件）同断言：`prompts` 子树的字面集合无一被咬——`answer_round` `_SUBTASK_MARKS`
    #    （子问题状态三值，`failed` 与族同名系巧合）／`decision_round` `_REROUTE_TRIGGERS` 皆在场。
    prompts_dir = _V2_DIR / "prompts"
    assert not [
        f"{path.name}:{line}"
        for path in sorted(prompts_dir.rglob("*.py"))
        for line, values in _str_collections(ast.parse(path.read_text(encoding="utf-8")))
        if _is_three_family_copy(values, families)
    ]


# ---------- 11 限额参数键集闭世界（行为 10） ----------

# `Budget` 键集与缺省值真源＝`recon/K-上下文事件指南预算.md` R-K-72…R-K-76（七键逐键承载）。
_SPEC_BUDGET_KEYS = {
    "rounds",
    "discovers_per_round",
    "executes_per_round",
    "seconds",
    "tool_timeout",
    "discovers_per_run",
    "ask_cap",
}


def test_budget_keys_closed_world() -> None:
    """限额参数键集闭世界、缺键取缺省（无散落字面量）。"""
    keys = {field.name for field in fields(Budget)}
    assert keys == _SPEC_BUDGET_KEYS  # 键集闭世界（七键）
    assert LIMIT_KINDS == keys  # 与 `LimitHit.limit` 闭世界同集（判定按名取上限）
    assert set(Budget.__dataclass_fields__) == keys

    # 缺键取缺省：缺省面逐键引 `constants` 单点，数值与真源一致（R-K-72…R-K-76）
    assert Budget() == Budget(
        rounds=MAX_ROUNDS,
        discovers_per_round=MAX_DISCOVERS_PER_ROUND,
        executes_per_round=MAX_EXECUTES_PER_ROUND,
        seconds=TOTAL_SECONDS,
        tool_timeout=TOOL_TIMEOUT_SECONDS,
        discovers_per_run=MAX_DISCOVERS_PER_RUN,
        ask_cap=ASK_CAP,
    )
    assert (MAX_ROUNDS, MAX_DISCOVERS_PER_ROUND, MAX_EXECUTES_PER_ROUND) == (3, 2, 2)
    assert (TOTAL_SECONDS, TOOL_TIMEOUT_SECONDS) == (300.0, 30.0)
    assert (MAX_DISCOVERS_PER_RUN, ASK_CAP) == (10, 6)
    only_rounds = Budget(rounds=1)
    assert only_rounds.rounds == 1 and only_rounds.ask_cap == ASK_CAP  # 缺键取缺省

    # 无散落字面量：① `Budget` 类体的字段缺省表达式不含裸数值（引常量）；② 判定面无限额数值字面
    sources = dict(_state_sources())
    budget_class = _class_def(sources[_STATE_DIR / "models.py"], "Budget")
    for statement in budget_class.body:
        if isinstance(statement, ast.AnnAssign):
            assert statement.value is not None
            assert not any(
                isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
                for node in ast.walk(statement.value)
            ), f"Budget 缺省出现裸字面量：{ast.unparse(statement)}"
    limit_numbers = {3, 2, 300.0, 30.0, 10, 6}
    in_limits = {
        node.value
        for node in ast.walk(sources[_STATE_DIR / "limits.py"])
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
    }
    assert not (in_limits & limit_numbers), f"判定面出现限额字面量：{in_limits & limit_numbers}"


def _class_def(tree: ast.Module, name: str) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"未找到类定义：{name}")


# ---------- 12 触界判定确定、纯（行为 11） ----------


def _overlimit_state(
    *,
    rounds: int = 3,
    discover_used: int = 10,
    discovers: int = 2,
    executes: int = 2,
) -> RunState:
    """超限态 fixture：轮数／全 run 发现／当前轮发现／当前轮执行逐项到顶。

    步记录＝`StepRecord` 七字段形（`step` ∈ `STEP_KINDS`）；轮界＝末条 `decision` 步。
    """
    steps: list[dict[str, Any]] = [{"seq": 1, "step": STEP_DECISION, "status": "ok"}]
    steps += [
        {"seq": 2 + index, "step": STEP_DISCOVER, "status": "ok"} for index in range(discovers)
    ]
    steps += [
        {"seq": 2 + discovers + index, "step": STEP_EXECUTE, "status": "ok"}
        for index in range(executes)
    ]
    return RunState(
        run_id="run-over",
        rounds=rounds,
        discover_used=discover_used,
        steps=steps,
    )


def test_check_limits_pure_and_deterministic() -> None:
    """触界判定确定、纯、不改入参。"""
    state = _overlimit_state()
    before = asdict(state)
    first = check_limits(state)
    second = check_limits(state)

    assert (first.hit, first.notice) == (second.hit, second.notice)  # 两跑结果相等
    assert asdict(state) == before  # 调用前后入参深比较相等
    assert deepcopy(state) == state  # 判定不含随机／无副作用
    assert check_limits(_overlimit_state()).hit == first.hit  # 同输入异实例同结果（判定确定）
    assert state.budget_hit == [] and state.notices == []  # 判定不落状态（落地归 bookkeeping）


# ---------- 13 触界必带注记（行为 12） ----------


def test_converge_requires_notice() -> None:
    """触界必带注记（恰三键）；未触界恒无注记。"""
    hit_result = check_limits(_overlimit_state())
    assert hit_result.hit
    assert hit_result.notice is not None
    assert set(hit_result.notice) == {"type", "gates", "content"}  # 恰三键（不复述 type 取值）
    assert hit_result.notice["gates"] == [hit.limit for hit in hit_result.hit]
    content = hit_result.notice["content"]
    assert isinstance(content, str) and content
    assert all(hit.limit in content for hit in hit_result.hit)  # 如实：命中项照实入注记
    assert isinstance(hit_result.hit, tuple)  # 空元组／元组——非列表

    clear_result = check_limits(RunState(run_id="run-1"))
    assert clear_result.hit == () and clear_result.notice is None  # 未触界恒无注记

    # 形态互斥 fail-closed（行为 12：触界不得静默、未触界不得凭空产注记）
    one_hit = LimitHit(limit="rounds", used=3.0, cap=3.0)
    with pytest.raises(ValueError):
        Convergence(hit=(one_hit,), notice=None)
    with pytest.raises(ValueError):
        Convergence(hit=(), notice={"type": "budget_converged", "gates": [], "content": "…"})
    with pytest.raises(ValueError):  # 注记非恰三键
        Convergence(hit=(one_hit,), notice={"type": "budget_converged", "gates": []})


# ---------- 14 `budget_hit` 与注记同现（行为 13） ----------


def _land_convergence(state: RunState, convergence: Convergence) -> None:
    """触界收敛的**落地**写入（正身＝`bookkeeping.converge` 唯一写口；本件为消费侧模型）。

    行为 12／13：命中 → 落 `budget_hit` ＋如实注记（＋终态）；未命中 → 零副作用。
    """
    if not convergence.hit:
        return
    state.budget_hit.extend(hit.limit for hit in convergence.hit)
    if convergence.notice is not None:
        state.notices.append(dict(convergence.notice))
    state.status = RUN_COMPLETED
    state.next_intent = INTENT_ANSWER


def test_budget_hit_signal_present() -> None:
    """`budget_hit` 与注记同现（触界不静默）。"""
    state = _overlimit_state()
    convergence = check_limits(state)
    assert convergence.hit and convergence.notice is not None

    _land_convergence(state, convergence)
    assert state.budget_hit == [hit.limit for hit in convergence.hit]  # 状态字段机读信号（不静默）
    assert state.notices and set(state.notices[-1]) == {"type", "gates", "content"}
    assert (state.status, state.next_intent) == (RUN_COMPLETED, INTENT_ANSWER)

    # 未触界：零副作用（不产注记、不落 budget_hit、不改状态）
    clear = RunState(run_id="run-2")
    _land_convergence(clear, check_limits(clear))
    assert clear.budget_hit == [] and clear.notices == []
    assert clear.status == RUN_RUNNING


# ---------- 17 本块零判断零 IO（AST 扫描） ----------

# 本块 import 白名单：只许 stdlib 三件（dataclasses／typing／collections.abc）＋`infra` 身份对象
# 类型面（边界红线 ④）＋本包内模块（R4 由边界闸另咬）。白名单外一律判失败——模型出口、事件发射、
# DB／文件读写、正则与语义处理所需的 import 全在名单外。
_ALLOWED_IMPORTS = {
    "__future__",
    "collections.abc",
    "dataclasses",
    "typing",
    "appv2.infra.security",
}
_ALLOWED_IMPORT_PREFIXES = ("appv2.runtimev2.state.",)
_FORBIDDEN_CALLS = {
    "open",
    "print",
    "eval",
    "exec",
    "compile",
    "__import__",
    "emit",
    "complete",
    "embeddings",
    "connect",
    "execute",
    "fetchall",
    "read_text",
    "write_text",
    "read_bytes",
    "write_bytes",
}
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _imported_modules(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
    return found


def _callee_names(tree: ast.Module) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            found.append((node.lineno, func.id))
        elif isinstance(func, ast.Attribute):
            found.append((node.lineno, func.attr))
    return found


def _io_or_judgement_findings(tree: ast.Module) -> list[str]:
    """零判断零 IO 的机检面：白名单外 import／禁止调用／疑似语义词表（非标识符形字符串集合）。

    「语义词表」的机检代理＝字符串集合里出现非纯标识符项（含中文／空白／标点／正则元字符）——
    语义词表与正则表必带此类项，而枚举闭世界的取值与 `__all__` 名单都是纯标识符形。
    """
    findings: list[str] = []
    for module in sorted(_imported_modules(tree)):
        if module in _ALLOWED_IMPORTS or module.startswith(_ALLOWED_IMPORT_PREFIXES):
            continue
        findings.append(f"import {module}")
    for line, name in _callee_names(tree):
        if name in _FORBIDDEN_CALLS:
            findings.append(f"L{line} 调用 {name}")
    for line, values in _str_collections(tree):
        for value in sorted(values):
            if not _IDENTIFIER.fullmatch(value):
                findings.append(f"L{line} 疑似语义词表项 {value!r}")
    return findings


def test_no_judgement_or_io_in_state() -> None:
    """本块零判断零 IO（AST 扫描）。"""
    for path, tree in _state_sources():
        findings = _io_or_judgement_findings(tree)
        assert findings == [], f"{path.name}：{findings}"

    # 探测器非空转（模型调用／事件发射／DB 文件读写／语义词表四类各命中）
    forged = ast.parse(
        "import sqlite3\n"
        "import re\n"
        "open('痕迹.txt')\n"
        "bus.emit('notice', {})\n"
        "model.complete([])\n"
        'WORDS = {"拒答", "无据"}\n'
    )
    findings = _io_or_judgement_findings(forged)
    assert any(finding.startswith("import sqlite3") for finding in findings)
    assert any(finding.startswith("import re") for finding in findings)
    assert any("调用 open" in finding for finding in findings)
    assert any("调用 emit" in finding for finding in findings)
    assert any("调用 complete" in finding for finding in findings)
    assert any("语义词表" in finding for finding in findings)


# ---------- 18 【边界集】（行为 9–13 四形） ----------


def test_boundary_empty_overlimit_legacy_variants() -> None:
    """【边界集】空状态／超限状态／v1 旧态／异参受理 → 各落对应分支。"""
    # ① 空状态：零用量零步列 → 不触界、不抛错
    empty = RunState(run_id="run-empty")
    assert (empty.steps, empty.rounds, empty.discover_used) == ([], 0, 0)
    empty_result = check_limits(empty)
    assert empty_result.hit == () and empty_result.notice is None

    # ② 超限状态：四类有状态载体的限额逐个触界（各落对应分支）
    over_hits = {hit.limit: (hit.used, hit.cap) for hit in check_limits(_overlimit_state()).hit}
    assert over_hits == {
        "rounds": (3.0, 3.0),
        "discovers_per_round": (2.0, 2.0),
        "executes_per_round": (2.0, 2.0),
        "discovers_per_run": (10.0, 10.0),
    }
    # 判据＝「达上限即触界」（R-K-86）——各降一格即不触界
    under = _overlimit_state(rounds=2, discover_used=9, discovers=1, executes=1)
    assert check_limits(under).hit == ()
    # 判定面覆盖边界（注入形已备（流水 52-A），缺省调用三键不判定）：`seconds`／`tool_timeout`／
    # `ask_cap` 的用量面不在 `RunState` 形状内（流水 49① 取消计时与连续问计数字段）——上限归零
    # 也不生假命中，不冒充覆盖
    uncarried = RunState(run_id="run-3", budget=Budget(seconds=0.0, tool_timeout=0.0, ask_cap=0))
    assert check_limits(uncarried).hit == ()

    # ③ v1 旧态：如实读入后判定照常（旧形六键步记录无 `step` 键 → 不计，不抛错）
    legacy = _read_v1_checkpoint(_V1_CHECKPOINT)
    legacy_result = check_limits(legacy)
    assert legacy_result.hit == () and legacy_result.notice is None
    assert check_limits(RunState(steps=[{"seq": 1, "kind": "discover"}])).hit == ()

    # ④ 异参受理：越界组合抛错（形状面，与行 15 同断言集）
    with pytest.raises(ValueError):
        AskRequest(resume_run_id="run-1", followup_run_id="run-0", actor=_actor())
    with pytest.raises(ValueError):
        AskChoice(kind="approval")
    with pytest.raises(ValueError):
        AskChoice(kind="clarify", decision="ok")

    # ⑤ 形态越界 fail-closed（额外面）：限额表非 `Budget` 实例 → 判错不静默（不返回哨兵）
    with pytest.raises(ValueError):
        check_limits(RunState(budget={"rounds": 3}))  # type: ignore[arg-type]


# ---------- 19 【保留集】（常规读写与未触界路径） ----------


def test_retention_normal_state_unchanged() -> None:
    """【保留集】常规状态读写与未触界路径行为不变。"""
    state = RunState(run_id="run-1")
    # 常规读写：状态机取值、对话链追加、步记录追加——取值全落闭世界内
    state.status = RUN_WAITING_ASK
    state.messages.append({"role": "user", "content": "问"})
    state.steps.append({"seq": 1, "step": STEP_DECISION, "status": "ok"})
    state.rounds = 1
    state.discover_used = 1
    state.next_intent = INTENT_ANSWER

    before = asdict(state)
    result = check_limits(state)  # 未触界路径
    assert result.hit == () and result.notice is None
    assert asdict(state) == before  # 判定零副作用：不改入参、不动 budget_hit／notices
    assert state.budget_hit == [] and state.notices == []

    state.status = RUN_COMPLETED  # 终态取值仍在闭世界内
    assert (state.status, state.next_intent) == (RUN_COMPLETED, INTENT_ANSWER)

    # 形状保留：字段集与 `synth/S5` 矩阵逐一相符；限额键集与缺省面不变
    assert {field.name for field in fields(RunState)} == _matrix_fields()
    assert {field.name for field in fields(Budget)} == _SPEC_BUDGET_KEYS
    assert asdict(Budget()) == {
        "rounds": MAX_ROUNDS,
        "discovers_per_round": MAX_DISCOVERS_PER_ROUND,
        "executes_per_round": MAX_EXECUTES_PER_ROUND,
        "seconds": TOTAL_SECONDS,
        "tool_timeout": TOOL_TIMEOUT_SECONDS,
        "discovers_per_run": MAX_DISCOVERS_PER_RUN,
        "ask_cap": ASK_CAP,
    }
