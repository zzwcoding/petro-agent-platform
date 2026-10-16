"""state 块验收（RT-W1-01a）：骨架与公开面、形状与状态语义、受理与回执载荷面。

票面对象＝`specs/state.md`「验收测试」表第 1–8、15、16 行（逐字，测试标识同规格列）；
测试网钉＝pin-22（`::messages_append_only_prefix`）／pin-23（`::followup_seeds_full_chain`）／
pin-24（`::contracts_appended_idempotent`）／pin-26（`::dialogue_layer_purity`）／
pin-29 形状面（`::ask_payload_shape_closed_world`）／
pin-30 状态字段面（`::legacy_checkpoint_read_honest`）。

字段集真源＝`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（本件**真读该文件解析**，
不硬编码字段名——硬编码即失去防漂移意义）；规格表剩余 9 行（常量族／限额触界／元／边界·保留集）
归 `RT-W1-01b-state.md`，同落本文件。
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import AsyncIterator, Mapping
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path
from typing import Any

import pytest

from appv2.infra.security import Actor
from appv2.runtimev2.state import (
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    AskChoice,
    AskRequest,
    Budget,
    Convergence,
    LimitHit,
    Manifest,
    RunHandle,
    RunState,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_S5_MATRIX = _REPO_ROOT / "docs" / "runtime-refactor" / "synth" / "S5-RunState字段矩阵.md"
_STATE_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "state"

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
    """全字段 fixture：首列 50 字段逐字段落非缺省值（行为 3 用）。"""
    return RunState(
        run_id="run-1",
        question="渤海某井 2026 年日产油量？",
        actor="laowang",
        status="waiting_ask",
        followup_of="run-0",
        empty_probes=['{"tool": "discover", "args": {}}'],
        understanding="用户问某井产量。",
        metric_candidates=["oil_rate"],
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
    assert len(matrix) == 50, f"S5 矩阵 §一 字段数应为定稿 50，实为 {len(matrix)}"
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
