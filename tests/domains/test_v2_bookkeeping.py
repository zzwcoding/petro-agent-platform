"""bookkeeping 块验收（RT-W3-01a：骨架＋共享可变写面核心＋全部 5 pin 行）。

票面对象＝`specs/bookkeeping.md`「验收测试」表逐行（本票 11 行：第 1–10、20 行；`#` 列保留规格表
行序、不重编；测试标识与规格列逐字一致）：

| # | 测试 | 验收标准（规格列原文） |
|---|---|---|
| 1 | `::single_write_port` | 共享写面只经本块（相位禁直写） |
| 2 | `::no_direct_state_write_in_phases` | 相位侧不得绕过写口直改状态字段 |
| 3 | `::seq_monotonic_paired` | 序号单调且与步数成对（禁手工偏移） |
| 4 | `::step_record_all_fields_and_status` | 步记录 `StepRecord` 全字段＋`status` 如实 |
| 5 | `::payload_faithful` | `payload` 原样保真（空与缺失可区分） |
| 6 | `::manifest_projected_or_empty` | `manifest` 投影随步且键恒在场 |
| 7 | `::messages_append_only` | 对话链只追加不改写 |
| 8 | `::contract_once` | 相位合同一次性（回炉轮不重发） |
| 9 | `::append_contract_sole_write_idempotent_closed_world` | `contracts_appended` 唯一写口 |
| 10 | `::dialogue_port_purity` | 对话层纯度：`origin` 闭世界且过程内容不入层 |
| 20 | `::set_intent_single_port_closed_world` | `next_intent` 唯一写口＋闭世界越界即拒 |

测试网钉（规格「与闸的挂钩表」5 行逐行，全在本票）：pin-22 写入点单点面（行 1／2）｜pin-22 写入面
（行 7）｜pin-24（行 8／9）｜pin-26（行 10）｜pin-12 承接面（行 5）。

本票验收另加三条机检面（票面「验收」节逐条）：公开面 13 成员签名逐字（`::public_face_signatures`）、
AST import 白名单＋无 DB／文件写路径（`::import_whitelist_and_no_disk_paths`）、织网义务 B1 的写口侧
观测面（`::write_port_channels_normalized_checkpoint_snapshot`）。

织网义务（eng/04 §三 B1 行，明写归本块）：钉法＝「经 checkpoint 快照／帧流钉『每步通道值归一形』」
——本票落地面＝**本票已落地的写口通道**（步记录／序号／对话链／对话层／合同标记／路由意图）；
`note`／`notice` 两通道的写入点行为体随 `RT-W3-01c-bookkeeping.md` 落地，其归一形由该票行 11／12
钉（本件不代钉、不冒充覆盖）。
"""

from __future__ import annotations

import ast
import inspect
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from appv2.runtimev2.bookkeeping import (
    append_contract,
    append_dialogue,
    append_message,
    next_seq,
    record_step,
    set_intent,
)
from appv2.runtimev2.persistence import STEP_STATUS_KINDS, decode_state, encode_state
from appv2.runtimev2.state import (
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    INTENT,
    STEP_KINDS,
    Manifest,
    RunState,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_BOOKKEEPING_DIR = _V2_DIR / "bookkeeping"

# ── 规格逐字面（独立于实现书写——实现漂移即红；真源 specs/bookkeeping.md 接口定义节／行为节）──
# 步记录七字段（行为 3，同 StepRecord 装配面、同序）
_SPEC_STEP_KEYS = ("run_id", "seq", "step", "status", "title", "manifest", "payload")
# 步状态三值（接口定义节；真源 specs/persistence.md）
_SPEC_STEP_STATUSES = {"ok", "failed", "refused"}
# 对话链角色闭世界（接口定义节「写口入参形状」）
_SPEC_MESSAGE_ROLES = {"user", "assistant"}
# 对话层来源闭世界三值（接口定义节；真源 specs/state.md 行为 6）
_SPEC_DIALOGUE_ORIGINS = {"user_verbatim", "assistant_final", "clarify_approval_replay"}
_SPEC_DIALOGUE_ORIGIN_ROLES = {
    "user_verbatim": "user",
    "assistant_final": "assistant",
    "clarify_approval_replay": "user",
}
# 合同追加相位闭世界三值（接口定义节：合同文本追加面的相位标记集）
_SPEC_CONTRACT_PHASES = {"decision", "clarify", "toolmatch"}
# 路由意图闭世界十值（接口定义节；真源 specs/state.md 行为 9）
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

# ── 共享写面七字段（行为 1 的六字段＋行为 8 的合同标记字段——规格两处均「并入行为 1 的写口单点
#    断言集」）与其唯一写口（写操作只许出现在下表函数里；`converge`／`direct_answer` 的本块内部写
#    见行为 6／12——本票只出签名，行为体随 RT-W3-01b 落地）────────────────────────────
_WRITE_FIELDS = (
    "messages",
    "steps",
    "process_notes",
    "notices",
    "dialogue",
    "next_intent",
    "contracts_appended",
)
_WRITE_PORT_OF: dict[str, frozenset[str]] = {
    "messages": frozenset({"append_message"}),
    "steps": frozenset({"record_step"}),
    "process_notes": frozenset({"note"}),
    "notices": frozenset({"notice", "converge"}),
    "dialogue": frozenset({"append_dialogue"}),
    "next_intent": frozenset({"set_intent", "converge", "direct_answer"}),
    "contracts_appended": frozenset({"append_contract"}),
}
# 就地改列表的方法（写操作——`state.steps.append(...)` 形）
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
# 七个业务相位＋编排层（相位侧扫描面＝这些包内**零**直写）
_PHASE_PACKAGES = (
    "understanding",
    "clarification",
    "tool_matching",
    "preconditions",
    "execution",
    "answering",
    "verification",
    "orchestration",
)
# 边界红线（规格「框架与依赖红线」）：import 白名单＝运行逻辑两块＋类型/常量形状三块＋本块自身
_RUNTIME_BLOCKS = ("appv2.runtimev2.state", "appv2.runtimev2.gateway_adapter")
_OWN_BLOCK = "appv2.runtimev2.bookkeeping"
_SHAPE_BLOCK_NAMES: dict[str, frozenset[str]] = {
    "appv2.tools": frozenset({"ToolContext", "ToolResult"}),
    "appv2.runtimev2.persistence": frozenset(
        {"StepRecord", "STEP_STATUS_DEFAULT", "STEP_STATUS_KINDS"}
    ),
    "appv2.runtimev2.transport": frozenset({"NOTICE_TYPES"}),
}
# 不落盘（红线④）与框架/引擎/模型出口禁入面（R5b／R6／R7）的静态禁字（import 白名单已覆盖大部分；
# 这几条是同一断言集的明写补足：文件写路径与 DB 面）
_FORBIDDEN_IMPORT_ROOTS = (
    "os",
    "pathlib",
    "shutil",
    "tempfile",
    "sqlalchemy",
    "asyncpg",
    "aiosqlite",
    "appv2.infra",
)


def _state(**overrides: Any) -> RunState:
    """状态 fixture（真源形：`state.RunState`）。"""
    values: dict[str, Any] = {
        "run_id": "run-bk-01",
        "question": "渤海某井 2026 年日产油量？",
        "actor": "laowang",
    }
    values.update(overrides)
    return RunState(**values)


def _bookkeeping_files() -> list[Path]:
    return sorted(_BOOKKEEPING_DIR.rglob("*.py"))


def _v2_sources() -> list[tuple[Path, ast.Module]]:
    """全 V2 树源码（旧码 `appv2/runtime/` 是重构退役面——不入扫描域；R5 亦禁引）。"""
    return [
        (path, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_V2_DIR.rglob("*.py"))
    ]


def _field_of(node: ast.expr) -> str | None:
    """该表达式是否直指七个共享写面字段（`state.<字段>`；取下标形的基座也算）。"""
    if isinstance(node, ast.Subscript):
        return _field_of(node.value)
    if isinstance(node, ast.Attribute) and node.attr in _WRITE_FIELDS:
        return node.attr
    return None


def _write_sites(tree: ast.Module) -> list[tuple[int, str, str]]:
    """写的操作点全列：`(行号, 字段名, 外层函数名)`（模块级＝`<module>`）。

    覆盖四形：赋值（`Assign`／`AugAssign`／`AnnAssign`——含 `state.messages = [...]` 整列替换）、
    删除（`Delete`）、就地改列表（`state.steps.append(...)` 一类调用）、下标写
    （`state.dialogue[0] = ...`，经 `_field_of` 的取下标解包）。扫描面是**黑盒化的写点形状**
    （attribute 名匹配），不逐符号翻译实现内部。

    口径取舍＝**按 attribute 名匹配**：宁可咬同名属性写点（误报可见、按实测收紧口径），也不放过
    真旁路（漏报不可见）——后续块若出现合法同名属性写点，改口径须回承载票（不许把闸磨钝换取绿）。
    """
    sites: list[tuple[int, str, str]] = []

    def _check(node: ast.AST, func: str) -> None:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                field = _field_of(target)
                if field is not None:
                    sites.append((node.lineno, field, func))
        elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
            field = _field_of(node.target)
            if field is not None:
                sites.append((node.lineno, field, func))
        elif isinstance(node, ast.Delete):
            for target in node.targets:
                field = _field_of(target)
                if field is not None:
                    sites.append((node.lineno, field, func))
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in _MUTATING_METHODS
        ):
            field = _field_of(node.func.value)
            if field is not None:
                sites.append((node.lineno, field, func))

    def _visit(node: ast.AST, func: str) -> None:
        _check(node, func)
        for child in ast.iter_child_nodes(node):
            child_func = (
                child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func
            )
            _visit(child, child_func)

    _visit(tree, "<module>")
    return sites


# ---------- 1 共享写面只经本块（相位禁直写） ----------


def test_single_write_port() -> None:
    """#1 共享写面只经本块（相位禁直写）——写口单点（钉 `pin-22` 的**写入点单点面**）。

    双面断言：① 本块内七字段的写操作只出现在下表唯一写口函数里；② 全 V2 树里这七字段的写操作
    只出现在 `bookkeeping/` 内（本块之外零写点）。
    """
    # ① 本块内：写点 → 唯一写口
    inside: list[str] = []
    for path in _bookkeeping_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for line, field, func in _write_sites(tree):
            if func not in _WRITE_PORT_OF[field]:
                ports_of_field = sorted(_WRITE_PORT_OF[field])
                inside.append(
                    f"{path.name}:{line} {field} ← {func}（唯一写口＝{ports_of_field}）"
                )
    assert not inside, f"本块内出现绕过唯一写口的写点：{inside}"

    # ② 全 V2 树：本块之外零写点
    outside: list[str] = []
    for path, tree in _v2_sources():
        if path.parent == _BOOKKEEPING_DIR:
            continue
        for line, field, func in _write_sites(tree):
            outside.append(f"{path.relative_to(_V2_DIR)}:{line} {field} ← {func}")
    assert not outside, f"本块之外出现直写共享写面字段：{outside}"

    # 探测器非空转：本块内确有写点（写口真在写），伪造的旁路写点必被咬
    live = [
        (field, func)
        for path in _bookkeeping_files()
        for _, field, func in _write_sites(ast.parse(path.read_text(encoding="utf-8")))
    ]
    assert len({field for field, _ in live}) >= 5, f"写口扫描面为空转：{live}"
    forged = ast.parse(
        "def phase_side(state):\n"
        "    state.messages = [{'role': 'user', 'content': '绕过写口'}]\n"
        "    state.steps.append({'seq': 99})\n"
    )
    assert {(line, field) for line, field, _ in _write_sites(forged)} == {
        (2, "messages"),
        (3, "steps"),
    }


# ---------- 2 相位侧不得绕过写口直改状态字段 ----------


def test_no_direct_state_write_in_phases() -> None:
    """#2 相位侧不得绕过写口直改状态字段（红线「禁手写替代」的相位侧半面）。

    与 `::single_write_port` 同断言集的相位侧扫描：七个业务相位包＋编排层的源码里，七字段
    **零写点**（相位只能经本块写口）。
    """
    scanned: set[str] = set()
    violations: list[str] = []
    for path, tree in _v2_sources():
        package = path.relative_to(_V2_DIR).parts[0]
        if package == "bookkeeping":
            continue
        if package in _PHASE_PACKAGES:
            scanned.add(package)
        for line, field, func in _write_sites(tree):
            violations.append(f"{path.relative_to(_V2_DIR)}:{line} {field} ← {func}")
    assert scanned == set(_PHASE_PACKAGES), f"相位侧扫描面不全：{sorted(scanned)}"
    assert not violations, f"相位侧出现直写共享写面字段：{violations}"

    # 探测器非空转：相位侧伪造写点必被咬
    forged = ast.parse(
        "def understand_node(state, deps):\n"
        "    state.process_notes.append({'phase': 'understand'})\n"
        "    state.next_intent = 'answer'\n"
        "    del state.notices[0]\n"
    )
    assert {field for _, field, _ in _write_sites(forged)} == {
        "process_notes",
        "next_intent",
        "notices",
    }


# ---------- 3 序号单调且与步数成对 ----------


def test_seq_monotonic_paired() -> None:
    """#3 序号单调且与步数成对（禁手工偏移）——行为 2。

    连记三步后序号 1／2／3 且步数＝3、`next_seq` 与 `len(steps)+1` 恒等；取号内置＝签名里没有
    序号入参（调用方无手加偏移的入口）。
    """
    state = _state()
    assert next_seq(state) == 1  # 空步列：首号＝1
    for index in range(1, 4):
        produced = record_step(state, kind="decision", title=f"第 {index} 步")
        assert state.steps[-1]["seq"] == index
        assert state.steps[-1] is produced  # 返回值＝入状态的那条投影
        assert next_seq(state) == len(state.steps) + 1
    assert [step["seq"] for step in state.steps] == [1, 2, 3]
    assert len(state.steps) == 3

    # 禁手工偏移：`record_step` 无序号入参（内置取号）
    assert "seq" not in inspect.signature(record_step).parameters
    assert not [
        name
        for name in inspect.signature(record_step).parameters
        if name != "state" and inspect.signature(record_step).parameters[name].kind
        is not inspect.Parameter.KEYWORD_ONLY
    ]


# ---------- 4 步记录全字段＋status 如实 ----------


def test_step_record_all_fields_and_status() -> None:
    """#4 步记录 `StepRecord` 全字段（含 `run_id`）＋`status` 如实（失败态可表达）——行为 3。"""
    assert set(STEP_STATUS_KINDS) == _SPEC_STEP_STATUSES
    assert set(STEP_KINDS) >= {"decision", "discover", "execute", "observe", "verify", "answer"}

    state = _state()
    record_step(state, kind="decision", title="决策：读题")
    default_step = state.steps[-1]
    assert tuple(default_step) == _SPEC_STEP_KEYS  # 键集合与键序＝七字段（归一形）
    assert set(default_step) == set(_SPEC_STEP_KEYS)
    assert default_step["run_id"] == state.run_id  # run_id 自状态取、不由调用方传
    assert default_step["step"] == "decision"
    assert default_step["title"] == "决策：读题"
    assert default_step["status"] == "ok"  # 缺省 ok

    # status 如实三值（失败与拒答态可表达——不得恒 ok）
    record_step(state, kind="execute", title="执行：取数", status="failed")
    record_step(state, kind="verify", title="核验：退回", status="refused")
    assert [step["status"] for step in state.steps[1:]] == ["failed", "refused"]
    assert all(tuple(step) == _SPEC_STEP_KEYS for step in state.steps)

    # run_id 随状态（不是硬编码）
    other = _state(run_id="run-bk-02")
    record_step(other, kind="observe", title="观察：回流")
    assert other.steps[-1]["run_id"] == "run-bk-02"

    # 闭世界越界即拒（fail-closed；不吞错、不返回哨兵）
    with pytest.raises(ValueError):
        record_step(state, kind="reflect", title="越界步类型")
    with pytest.raises(ValueError):
        record_step(state, kind="decision", title="越界步状态", status="error")
    assert len(state.steps) == 3  # 越界不落


# ---------- 5 payload 原样保真 ----------


def test_payload_faithful() -> None:
    """#5 `payload` 原样保真（空与缺失可区分）——行为 4（钉 `pin-12` 的**承接面**）。

    空 `{}` 照写 `{}`、缺省写缺省，两态读回不等价（**禁 `payload or {}` 式假值归一**）；经
    checkpoint 快照往返后两态仍可区分（承接面＝落盘侧读回）。
    """
    state = _state()
    record_step(state, kind="observe", title="空 payload", payload={})
    record_step(state, kind="observe", title="缺省 payload")
    empty_step, missing_step = state.steps[0], state.steps[1]
    assert "payload" in empty_step and "payload" in missing_step  # 键恒在场
    assert empty_step["payload"] == {}
    assert missing_step["payload"] is None
    assert empty_step["payload"] != missing_step["payload"]  # 两态读回不等价

    record_step(state, kind="execute", title="带内容", payload={"rows": 3})
    assert state.steps[2]["payload"] == {"rows": 3}

    restored = decode_state(encode_state(state))
    assert restored.steps[0]["payload"] == {}
    assert restored.steps[1]["payload"] is None
    assert restored.steps[0]["payload"] != restored.steps[1]["payload"]


# ---------- 6 manifest 投影随步且键恒在场 ----------


def test_manifest_projected_or_empty() -> None:
    """#6 `manifest` 投影随步且键恒在场——行为 5。

    `manifest` 非空 → `Manifest.as_dict()` 投影；为空 → 写空（**不省略键**）——两条路径的键集合
    相同（`Manifest()` 无参可构造，其投影＝全键缺省形）。
    """
    state = _state()
    manifest = Manifest(
        source_type=["ledger"],
        source_id=["canon-daily-oil"],
        version=["v2"],
        trust_level=["authoritative"],
        selected_reason="权威 1 支全量",
        token_count=42,
        material_total=1,
        material_rendered=1,
    )
    record_step(state, kind="answer", title="带 Manifest", manifest=manifest)
    record_step(state, kind="decision", title="无 Manifest", manifest=Manifest())
    record_step(state, kind="decision", title="缺省 Manifest")
    with_manifest, empty_manifest, no_manifest = state.steps
    assert tuple(with_manifest) == tuple(empty_manifest) == tuple(no_manifest) == _SPEC_STEP_KEYS
    assert with_manifest["manifest"] == manifest.as_dict()
    assert empty_manifest["manifest"] == Manifest().as_dict()
    assert no_manifest["manifest"] is None
    # 投影是拷贝语义（改投影不改原 Manifest——真源 specs/state.md 行为 15）
    projected = with_manifest["manifest"]
    assert isinstance(projected, dict)
    projected["source_id"].append("篡改")
    assert manifest.source_id == ["canon-daily-oil"]


# ---------- 7 对话链只追加不改写 ----------


def test_messages_append_only() -> None:
    """#7 对话链只追加不改写——行为 7（钉 `pin-22` 的**写入面**，P0）。

    追加 N 条后前 N-1 条逐字不变（不替换、不重排、不删除）；条目形态恰两键；`role` 闭世界。
    """
    assert _SPEC_MESSAGE_ROLES == {"user", "assistant"}
    state = _state()
    append_message(state, role="user", content="任务书：……（过程内容入链，不入对话层）")
    snapshot = deepcopy(state.messages)
    append_message(state, role="assistant", content="模型原话")
    append_message(state, role="user", content="追问：那 2025 年呢？")
    append_message(state, role="assistant", content="终稿")

    assert state.messages[: len(snapshot)] == snapshot  # 前 N-1 条逐字不变
    assert [entry["content"] for entry in state.messages[1:]] == [
        "模型原话",
        "追问：那 2025 年呢？",
        "终稿",
    ]
    assert all(set(entry) == {"role", "content"} for entry in state.messages)
    # 相邻两次调用互为前缀延伸（只追加的机读形）
    assert state.messages[:-1] == [
        {"role": "user", "content": "任务书：……（过程内容入链，不入对话层）"},
        {"role": "assistant", "content": "模型原话"},
        {"role": "user", "content": "追问：那 2025 年呢？"},
    ]

    with pytest.raises(ValueError):
        append_message(state, role="system", content="越界角色")
    assert len(state.messages) == 4  # 越界不落


# ---------- 8 相位合同一次性（回炉轮不重发） ----------


def test_contract_once() -> None:
    """#8 相位合同一次性（回炉轮不重发）——行为 8（钉 `pin-24` 的**写入面**）。

    调用方按 `state.contracts_appended` 标记判「是否重发」；同相位二次进入（回炉轮）后合同条数
    不变、标记写入幂等。
    """
    state = _state()
    contract_text = "【相位合同·决策】决策轮只输出路由意图，不得作答。"

    def enter_phase(phase: str) -> None:
        """相位进入（调用方形）：已标记＝不重发合同文本。"""
        if phase in state.contracts_appended:
            return
        append_contract(state, phase)
        append_message(state, role="user", content=contract_text)

    enter_phase("decision")
    enter_phase("decision")  # 回炉轮：同相位二次进入
    enter_phase("clarify")
    enter_phase("clarify")
    assert state.contracts_appended == ["decision", "clarify"]
    assert sum(1 for entry in state.messages if entry["content"] == contract_text) == 2


# ---------- 9 contracts_appended 唯一写口 ----------


def test_append_contract_sole_write_idempotent_closed_world() -> None:
    """#9 `contracts_appended` 唯一写口＝`append_contract`（幂等；越界相位抛错）——行为 8。

    幂等＝已标记相位再标记无操作（不重复追加、不重复标记）；越界相位抛错（fail-closed）；全 V2 树
    里 `contracts_appended` 的写点只在 `append_contract`。
    """
    state = _state()
    append_contract(state, "decision")
    append_contract(state, "decision")  # 幂等：无操作
    append_contract(state, "clarify")
    append_contract(state, "toolmatch")
    append_contract(state, "toolmatch")
    assert state.contracts_appended == ["decision", "clarify", "toolmatch"]

    for phase in ("understand", "answer", "execute", ""):
        with pytest.raises(ValueError):
            append_contract(state, phase)
    assert state.contracts_appended == ["decision", "clarify", "toolmatch"]  # 越界不落

    # 唯一写口：全 V2 树（含本块）里该字段的写点只在 bookkeeping 的 append_contract
    writers: list[str] = []
    for path, tree in _v2_sources():
        for line, field, func in _write_sites(tree):
            if field == "contracts_appended":
                writers.append(f"{path.relative_to(_V2_DIR)}:{line} ← {func}")
    assert writers, "contracts_appended 写点扫描面为空转"
    assert all(entry.endswith("← append_contract") for entry in writers), writers
    assert all(entry.startswith("bookkeeping/") for entry in writers), writers


# ---------- 10 对话层纯度 ----------


def test_dialogue_port_purity() -> None:
    """#10 对话层纯度：`origin` 闭世界且过程内容不入层——行为 9（钉 `pin-26` 的**写入面**）。

    注入「含任务书的一轮」后，`dialogue` 条目 `origin` 全落在三值内（且守来源↔角色不变量）；
    越界调用抛错——过程内容只能伪造来源标签混入，伪造即越界被抓（写入点即拒）。
    """
    assert _SPEC_DIALOGUE_ORIGINS == {"user_verbatim", "assistant_final", "clarify_approval_replay"}
    assert set(DIALOGUE_ORIGINS) == _SPEC_DIALOGUE_ORIGINS
    assert dict(DIALOGUE_ORIGIN_ROLES) == _SPEC_DIALOGUE_ORIGIN_ROLES

    state = _state()
    # 一轮：任务书与相位指令入对话链（`messages`），自然对话入对话层
    append_message(state, role="user", content="任务书：……（过程内容，走对话链）")
    append_message(state, role="user", content="相位指令：只输出 JSON")
    append_dialogue(
        state, role="user", content="这口井 2026 年日产油量是多少？", origin="user_verbatim"
    )
    append_dialogue(
        state, role="assistant", content="日产油量 12.5 t/d。", origin="assistant_final"
    )
    append_dialogue(
        state, role="user", content="批准（回收原文）", origin="clarify_approval_replay"
    )

    assert len(state.dialogue) == 3
    assert all(tuple(entry) == ("role", "content", "origin") for entry in state.dialogue)
    assert [entry["origin"] for entry in state.dialogue] == [
        "user_verbatim",
        "assistant_final",
        "clarify_approval_replay",
    ]
    for entry in state.dialogue:
        assert entry["origin"] in _SPEC_DIALOGUE_ORIGINS
        assert _SPEC_DIALOGUE_ORIGIN_ROLES[entry["origin"]] == entry["role"]
    # 过程内容不在对话层（只在对话链）
    assert not any("任务书" in entry["content"] for entry in state.dialogue)

    with pytest.raises(ValueError):  # 越界来源（伪造标签混过程内容）
        append_dialogue(state, role="user", content="任务书：……", origin="task_book")
    with pytest.raises(ValueError):  # 张冠李戴（来源↔角色不变量）
        append_dialogue(state, role="assistant", content="助手终稿", origin="user_verbatim")
    with pytest.raises(ValueError):
        append_dialogue(state, role="system", content="越界角色", origin="assistant_final")
    assert len(state.dialogue) == 3  # 越界不落


# ---------- 20 next_intent 唯一写口＋闭世界 ----------


def test_set_intent_single_port_closed_world() -> None:
    """#20 `next_intent` 唯一写口＋闭世界越界即拒——行为 6。

    取值 ∈ `INTENT`（十值）全数可写；越界（含未设态空串）即拒；全 V2 树里 `next_intent` 的写点只
    在本块（`set_intent`／`converge`／`direct_answer`——后两者为本块内部写，行为 6／12／14）。
    """
    assert INTENT == _SPEC_INTENT
    state = _state()
    assert state.next_intent == ""  # 缺省＝未设态
    for intent in sorted(_SPEC_INTENT):
        set_intent(state, intent)
        assert state.next_intent == intent
    # 写字段 ≠ 做路由决策：本块只写取值，不做跳转（本测只断言取值面）

    for intent in ("", "clarify", "route_home", "watch", "ANSWER"):
        with pytest.raises(ValueError):
            set_intent(state, intent)
    assert state.next_intent == "verify"  # 越界不覆盖既有取值

    writers: list[str] = []
    for path, tree in _v2_sources():
        for line, field, func in _write_sites(tree):
            if field == "next_intent":
                writers.append(f"{path.relative_to(_V2_DIR)}:{line} ← {func}")
    assert writers, "next_intent 写点扫描面为空转"
    assert all(entry.startswith("bookkeeping/") for entry in writers), writers
    assert all(
        entry.endswith(("← set_intent", "← converge", "← direct_answer")) for entry in writers
    ), writers


# ---------- 公开面 13 成员签名逐字（票面验收：骨架与公开面落位） ----------

_EMPTY = inspect.Parameter.empty
_POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
_KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY

# 逐字＝`specs/bookkeeping.md` 接口定义节（:56–:75）／`specs/modules.md` `## bookkeeping` 卡
_SPEC_FACE: dict[str, dict[str, Any]] = {
    "record_step": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("kind", "str", _KEYWORD_ONLY, _EMPTY),
            ("title", "str", _KEYWORD_ONLY, _EMPTY),
            ("status", "str", _KEYWORD_ONLY, "ok"),
            ("payload", "dict[str, Any] | None", _KEYWORD_ONLY, None),
            ("manifest", "Manifest | None", _KEYWORD_ONLY, None),
        ),
        "returns": "StepRecord",
    },
    "next_seq": {
        "params": (("state", "RunState", _POSITIONAL, _EMPTY),),
        "returns": "int",
    },
    "append_message": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("role", "str", _KEYWORD_ONLY, _EMPTY),
            ("content", "str", _KEYWORD_ONLY, _EMPTY),
        ),
        "returns": "None",
    },
    "append_dialogue": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("role", "str", _KEYWORD_ONLY, _EMPTY),
            ("content", "str", _KEYWORD_ONLY, _EMPTY),
            ("origin", "str", _KEYWORD_ONLY, _EMPTY),
        ),
        "returns": "None",
    },
    "note": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("phase", "str", _KEYWORD_ONLY, _EMPTY),
            ("title", "str", _KEYWORD_ONLY, _EMPTY),
            ("digest", "str", _KEYWORD_ONLY, _EMPTY),
        ),
        "returns": "None",
    },
    "notice": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("type", "str", _KEYWORD_ONLY, _EMPTY),
            ("gates", "Sequence[str]", _KEYWORD_ONLY, ()),
            ("content", "str", _KEYWORD_ONLY, _EMPTY),
        ),
        "returns": "None",
    },
    "set_intent": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("intent", "str", _POSITIONAL, _EMPTY),
        ),
        "returns": "None",
    },
    "append_contract": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("phase", "str", _POSITIONAL, _EMPTY),
        ),
        "returns": "None",
    },
    "converge": {
        "params": (("state", "RunState", _POSITIONAL, _EMPTY),),
        "returns": "None",
    },
    "direct_answer": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("text", "str", _POSITIONAL, _EMPTY),
        ),
        "returns": "None",
    },
    "call_model": {
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("caller", "str", _POSITIONAL, _EMPTY),
            ("messages", "Sequence[Mapping[str, str]]", _POSITIONAL, _EMPTY),
        ),
        "returns": "str",
    },
    "tool_context": {
        "params": (("state", "RunState", _POSITIONAL, _EMPTY),),
        "returns": "ToolContext",
    },
    "result_projection": {
        "params": (("result", "ToolResult", _POSITIONAL, _EMPTY),),
        "returns": "dict[str, Any]",
    },
}


def test_public_face_signatures() -> None:
    """公开面 13 成员齐备且签名逐字（票面验收：骨架与公开面落位——规格 :52 接口定义）。"""
    import appv2.runtimev2.bookkeeping as bookkeeping
    import appv2.runtimev2.bookkeeping.closing as closing
    import appv2.runtimev2.bookkeeping.ports as ports
    import appv2.runtimev2.bookkeeping.projection as projection

    assert set(bookkeeping.__all__) == set(_SPEC_FACE), "包根公开面与规格 13 成员不符"
    # 包根即公开面：不复制包装（与定义处同一对象）
    for name in ("record_step", "append_message", "note", "append_contract"):
        assert getattr(bookkeeping, name) is getattr(ports, name)
    for name in ("converge", "direct_answer", "call_model"):
        assert getattr(bookkeeping, name) is getattr(closing, name)
    for name in ("tool_context", "result_projection"):
        assert getattr(bookkeeping, name) is getattr(projection, name)

    for name, spec in _SPEC_FACE.items():
        function = getattr(bookkeeping, name)
        assert callable(function), name
        signature = inspect.signature(function)
        actual = tuple(
            (parameter.name, str(parameter.annotation), parameter.kind, parameter.default)
            for parameter in signature.parameters.values()
        )
        assert actual == spec["params"], f"{name} 参数面与规格接口定义不符：{actual}"
        assert str(signature.return_annotation) == spec["returns"], name


# ---------- 边界红线：import 只出现五块＋不落盘（票面验收：AST 白名单断言） ----------


def test_import_whitelist_and_no_disk_paths() -> None:
    """边界红线（规格「框架与依赖红线」）：import 只出现五块白名单＋无 DB／文件写路径。

    运行逻辑只依赖 `state`／`gateway_adapter`；类型与常量形状另引 `tools`／`persistence`／
    `transport`（**只许引类型与常量**，不许引其行为）；不落盘（无 DB／文件写路径）。该面无专属闸
    →降维 AST 断言（规格登记「人审＋AST 断言」）。
    """
    allowed_blocks = set(_RUNTIME_BLOCKS) | set(_SHAPE_BLOCK_NAMES) | {_OWN_BLOCK}
    modules: set[str] = set()
    shape_names: dict[str, set[str]] = {}
    disk_paths: list[str] = []
    for path in _bookkeeping_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # 相对 import＝本块内
                    continue
                module = node.module or ""
                modules.add(module)
                for block in _SHAPE_BLOCK_NAMES:
                    if module == block:
                        shape_names.setdefault(block, set()).update(a.name for a in node.names)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"open", "exec", "eval", "compile"}:
                    disk_paths.append(f"{path.name}:{node.lineno} {node.func.id}()")

    assert any(module.startswith("appv2") for module in modules), "import 扫描面为空转"
    outside = {
        module
        for module in modules
        if module.split(".")[0] not in sys.stdlib_module_names
        and not any(module == block or module.startswith(block + ".") for block in allowed_blocks)
    }
    assert not outside, f"出现五块白名单之外的 import：{sorted(outside)}"
    for module in _FORBIDDEN_IMPORT_ROOTS:
        assert not any(
            module == other or other.startswith(module + ".") for other in modules
        ), f"红线面 import 出现：{module}"
    for block, names in shape_names.items():
        assert names <= _SHAPE_BLOCK_NAMES[block], f"{block} 引入类型/常量之外的名字：{names}"
    assert not disk_paths, f"出现文件写/执行路径：{disk_paths}"


# ---------- 织网义务 B1：写口侧观测面（每步通道值归一形） ----------


def test_write_port_channels_normalized_checkpoint_snapshot() -> None:
    """织网义务 B1（eng/04 §三：「经 checkpoint 快照／帧流钉『每步通道值归一形』」，L1 特征钉）。

    全程走公开出口（写口 → `state` → persistence 的 checkpoint 快照编解码），钉常规三步流程后各
    通道值归一形：步记录七字段同序、对话链两键、对话层三键、合同标记与路由意图单值面；快照往返
    后逐字不变（黑盒化改造路径——不逐符号翻译内部实现）。
    """
    state = _state()
    append_message(state, role="user", content="问题")
    record_step(state, kind="decision", title="决策：读题")
    append_contract(state, "decision")
    set_intent(state, "discover")
    record_step(state, kind="discover", title="发现：检索", payload={"probes": 2})
    append_dialogue(state, role="user", content="问题（原话）", origin="user_verbatim")
    set_intent(state, "answer")
    record_step(state, kind="answer", title="作答：收口", status="ok", manifest=Manifest())
    append_message(state, role="assistant", content="终稿")

    assert [step["seq"] for step in state.steps] == [1, 2, 3]
    assert all(tuple(step) == _SPEC_STEP_KEYS for step in state.steps)
    assert all(set(entry) == {"role", "content"} for entry in state.messages)
    assert all(tuple(entry) == ("role", "content", "origin") for entry in state.dialogue)
    assert state.contracts_appended == ["decision"]
    assert state.next_intent == "answer"

    restored = decode_state(encode_state(state))
    assert restored.steps == state.steps
    assert restored.messages == state.messages
    assert restored.dialogue == state.dialogue
    assert restored.contracts_appended == state.contracts_appended
    assert restored.next_intent == state.next_intent
    assert tuple(restored.steps[-1]) == _SPEC_STEP_KEYS
