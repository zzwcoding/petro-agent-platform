"""bookkeeping 块验收（RT-W3-01a：骨架＋共享可变写面核心＋5 pin 行；-01b：触界收敛与收口簇）。

票面对象＝`specs/bookkeeping.md`「验收测试」表逐行（`#` 列保留规格表行序、不重编；测试标识与规格
列逐字一致）。三票（-01a／-01b／-01c）同落本件、各自收各行的行序。

`RT-W3-01a` 11 行：第 1–10、20 行——

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

`RT-W3-01b` 5 行：第 13–17 行（触界收敛与收口簇——本票零 pin 行，5 条 pin 行全在 -01a）——

| # | 测试 | 验收标准（规格列原文） |
|---|---|---|
| 13 | `::converge_lands_six_keys` | 触界收敛落地六键；未命中零副作用 |
| 14 | `::converge_idempotent` | 收敛幂等（二次调用不重复追加／不覆盖） |
| 15 | `::converge_material_same_source` | 收敛答案与通知材料面同源（不漂移） |
| 16 | `::direct_answer_three_keys` | 直答旁路恒写三键 |
| 17 | `::call_model_keeps_accounting` | 调模型单点：只回 `content`，用量/归因落记账 |

`RT-W3-01c` 7 行：第 11、12、18、19、21–23 行（装配与归一＋元面＋【边界集】／【保留集】——本票
零 pin 行，5 条 pin 行全在 -01a）——

| # | 测试 | 验收标准（规格列原文） |
|---|---|---|
| 11 | `::note_bounded_append_only` | 过程档案 `note` 写入点截断且只追加 |
| 12 | `::notice_three_keys_closed_world` | 通知恰三键＋`type`／`gates` 闭世界 |
| 19 | `::result_projection_faithful` | 结果投影原样（空值与缺省可区分） |
| 21 | `::no_judgement_in_bookkeeping` | 本块零判断（AST 扫描） |
| 23 | `::retention_normal_three_steps` | 【保留集】常规三步流程的记录形状与顺序不变 |

两行为长文（表格超行宽）另记（`#` 与测试标识逐字同规格表）：

- 18｜`::tool_context_assembly`｜工具上下文：身份只从状态取、放行态随上下文、预算按子问题数
- 22｜`::boundary_empty_huge_converged_enum`｜【边界集】空步列／超长 digest／已收敛再收敛／越界枚举
  → 各落对应分支

-01a 验收另加三条机检面（票面「验收」节逐条）：公开面 13 成员签名逐字
（`::public_face_signatures`）、
AST import 白名单＋无 DB／文件写路径（`::import_whitelist_and_no_disk_paths`）、织网义务 B1 的写口侧
观测面（`::write_port_channels_normalized_checkpoint_snapshot`）。

织网义务（eng/04 §三 B1 行，明写归本块）：钉法＝「经 checkpoint 快照／帧流钉『每步通道值归一形』」
——-01a 落地面＝已落地的写口通道（步记录／序号／对话链／对话层／合同标记／路由意图）；-01b 落地面
＝收口簇（`converge` 的六键与材料同源、`direct_answer` 三键、`call_model` 的记账步——收敛答案与
通知的材料面同源＝B3「触顶收敛落地」半行的 L1 特征钉）；-01c 落地面＝`note`／`notice` 两通道的
写入点行为体与其归一形（行 11／12 钉）＋结果归一投影（行 19——B1 钉「结果归一」半边）与工具
上下文装配（行 18）。
"""

from __future__ import annotations

import ast
import inspect
import json
import sys
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

import pytest

from appv2.runtimev2.bookkeeping import (
    append_contract,
    append_dialogue,
    append_message,
    call_model,
    converge,
    direct_answer,
    next_seq,
    note,
    notice,
    record_step,
    result_projection,
    set_intent,
    tool_context,
)
from appv2.runtimev2.gateway_adapter import ModelReply, ScriptedCompleter, set_completer
from appv2.runtimev2.persistence import STEP_STATUS_KINDS, decode_state, encode_state
from appv2.runtimev2.state import (
    DIALOGUE_ORIGIN_ROLES,
    DIALOGUE_ORIGINS,
    INTENT,
    LIMIT_KINDS,
    MAX_DISCOVERS_PER_RUN,
    MAX_ROUNDS,
    RUN_RUNNING,
    STEP_KINDS,
    Manifest,
    RunState,
)
from appv2.runtimev2.transport import NOTICE_TYPES
from appv2.tools import (
    AskFrame,
    Observation,
    ToolContext,
    ToolError,
    ToolRegistry,
    ToolResult,
    resolve_send_budget,
)
from appv2.tools.fake import FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine

_REPO_ROOT = Path(__file__).resolve().parents[2]
_V2_DIR = _REPO_ROOT / "appv2" / "runtimev2"
_BOOKKEEPING_DIR = _V2_DIR / "bookkeeping"

# ── 规格逐字面（独立于实现书写——实现漂移即红；真源 specs/bookkeeping.md 接口定义节／行为节）──
# 步记录七字段（行为 3，同 StepRecord 装配面、同序）
_SPEC_STEP_KEYS = ("run_id", "seq", "step", "status", "title", "manifest", "payload")
# 步状态三值（接口定义节；真源 specs/persistence.md）
_SPEC_STEP_STATUSES = {"ok", "failed", "refused"}
# 对话链角色闭世界（接口定义节「写口入参形状」；2026-10-17 H 批加第三值 `system`——
# 只承载链首背景块，每链恰一条；环节规章不入链、走 `call_model` 的 `system` 注入参）
_SPEC_MESSAGE_ROLES = {"user", "assistant", "system"}
# 对话层来源闭世界三值（接口定义节；真源 specs/state.md 行为 6）
_SPEC_DIALOGUE_ORIGINS = {"user_verbatim", "assistant_final", "clarify_approval_replay"}
_SPEC_DIALOGUE_ORIGIN_ROLES = {
    "user_verbatim": "user",
    "assistant_final": "assistant",
    "clarify_approval_replay": "user",
}
# 合同追加相位闭世界三值（接口定义节：合同文本追加面的相位标记集）
_SPEC_CONTRACT_PHASES = {"decision", "clarify", "toolmatch"}
# 路由意图闭世界十一值（接口定义节；真源 specs/state.md 行为 9；V2-96 追加 explore）
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
    "explore",  # V2-96 D5：作答第二出口路由意图
}
# 限额七键名闭世界（接口定义节「写口入参形状」；2026-10-16 裁·流水 52-B——`gates` 取值与
# 触界命中项同名；真源＝`state.LimitHit.limit` 的 Literal 七值）
_SPEC_LIMIT_KEYS = {
    "rounds",
    "discovers_per_round",
    "executes_per_round",
    "seconds",
    "tool_timeout",
    "discovers_per_run",
    "ask_cap",
}
# 归因三桶族（`call_model` 的 `caller` 取值域；真源 specs/gateway_adapter.md 行为 5）
_SPEC_CALLERS = {"understand", "decision", "answer"}

# 已取得材料面 fixture（材料行＝观察投影形：`content` 正文＋`source_id` 标识）
_SPEC_MATERIAL_ROWS: tuple[dict[str, str], ...] = (
    {"content": "Y-21 井 2026 年产油量 12.5 t/d", "source_id": "src-ledger-daily-oil"},
    {"content": "Y-22 井 2026 年产油量 4.0 t/d", "source_id": "src-ledger-daily-oil-2"},
)
# 收敛落地的六键（行为 12 逐字：budget_hit／通知／答案正文／draft_kind／status／next_intent）
_SPEC_CONVERGENCE_KEYS = {
    "budget_hit",
    "notices",
    "answer",
    "draft_kind",
    "status",
    "next_intent",
}
# 直答旁路三键（行为 14 逐字：draft／draft_kind／next_intent）
_SPEC_DIRECT_ANSWER_KEYS = {"draft", "draft_kind", "next_intent"}
# 材料同源声明的机读标记（本块 `_material_clause` 单点产出——正文与注记两处同标记）
_MATERIAL_MARKER = "材料清单："

# ── 共享写面七字段（行为 1 的六字段＋行为 8 的合同标记字段——规格两处均「并入行为 1 的写口单点
#    断言集」）与其唯一写口（写操作只许出现在下表函数里；`converge`／`direct_answer` 的本块内部写
#    见行为 6／12／14——行为体已随 RT-W3-01b 落地，本表口径不变）────────────────────────────
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
# 三块「形状块」的允许名字：类型／常量面；`appv2.tools` 另含行为 16 点名的**送窗预算公式函数**
# `resolve_send_budget`（数值与公式真源——规格「不复述数值」故本块只能引它、不能复算；它不是
# 「工具行为面」：不调工具、不落盘、不发帧，纯算式）。名字集合即白名单（多引一个名字即 FAIL）。
_SHAPE_BLOCK_NAMES: dict[str, frozenset[str]] = {
    "appv2.tools": frozenset({"ToolContext", "ToolResult", "resolve_send_budget"}),
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

    追加 N 条后前 N-1 条逐字不变（不替换、不重排、不删除）；条目形态恰两键；`role` 闭世界
    （2026-10-17 H 批三值：`user`／`assistant`／`system`——`system` 只承载链首背景块）。
    """
    assert _SPEC_MESSAGE_ROLES == {"user", "assistant", "system"}
    state = _state()
    append_message(state, role="system", content="【系统背景】……（链首背景块，每链恰一条）")
    append_message(state, role="user", content="任务书：……（过程内容入链，不入对话层）")
    snapshot = deepcopy(state.messages)
    append_message(state, role="assistant", content="模型原话")
    append_message(state, role="user", content="追问：那 2025 年呢？")
    append_message(state, role="assistant", content="终稿")

    assert state.messages[: len(snapshot)] == snapshot  # 前 N-1 条逐字不变
    assert [entry["content"] for entry in state.messages[2:]] == [
        "模型原话",
        "追问：那 2025 年呢？",
        "终稿",
    ]
    assert all(set(entry) == {"role", "content"} for entry in state.messages)
    # 相邻两次调用互为前缀延伸（只追加的机读形）
    assert state.messages[:-1] == [
        {"role": "system", "content": "【系统背景】……（链首背景块，每链恰一条）"},
        {"role": "user", "content": "任务书：……（过程内容入链，不入对话层）"},
        {"role": "assistant", "content": "模型原话"},
        {"role": "user", "content": "追问：那 2025 年呢？"},
    ]

    with pytest.raises(ValueError):
        append_message(state, role="tool", content="越界角色")
    assert len(state.messages) == 5  # 越界不落


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

    取值 ∈ `INTENT`（十一值）全数可写；越界（含未设态空串）即拒；全 V2 树里 `next_intent` 的写点只
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
        "params": (
            ("state", "RunState", _POSITIONAL, _EMPTY),
            ("elapsed_seconds", "float | None", _KEYWORD_ONLY, None),
            ("consecutive_asks", "int | None", _KEYWORD_ONLY, None),
        ),
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
            # 2026-10-17 H 批（角色分家·system 承载位）：本环节规章经该注入参前置进本次请求
            # （不入链、不进检查点、不用即散）——真源 `specs/bookkeeping.md` 行为 15 的 H 批注。
            ("system", "str | None", _KEYWORD_ONLY, None),
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
    `transport`（引入名逐个在册，见 `_SHAPE_BLOCK_NAMES`——`tools` 面另含行为 16 点名的送窗预算
    **公式函数** `resolve_send_budget`：只引不算、本块不复述数值）；不落盘（无 DB／文件写路径）。
    该面无专属闸→降维 AST 断言（规格登记「人审＋AST 断言」）。
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


# ══════════════════ RT-W3-01b：触界收敛与收口簇（规格表第 13–17 行）══════════════════
# 本票零 pin 行（5 条 pin 行全在 -01a 逐字转抄）——下列用例不改 -01a 落地的形状（写口九函数与
# 收敛／收口签名），只填行为体。


def _material_state(**overrides: Any) -> RunState:
    """已触界状态 fixture：轮数达上限（判定归 `state.check_limits`）＋已取得材料面。"""
    state = _state(**{"rounds": MAX_ROUNDS, **overrides})
    state.observations.extend(deepcopy(list(_SPEC_MATERIAL_ROWS)))
    return state


def _changed_fields(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    """前后状态投影的字段差集（`RunState` 全字段——「落六键」＝差集恰为六键的机读形）。"""
    assert set(before) == set(after)
    return {key for key in before if before[key] != after[key]}


def _material_ids_in(text: str) -> set[str]:
    """按同源声明标记抽材料标识集合（两处同一标记——集合相等即「不漂移」的机读形）。"""
    assert _MATERIAL_MARKER in text, f"缺少材料同源声明：{text!r}"
    tail = text.split(_MATERIAL_MARKER, 1)[1]
    for stop in ("）", "\n"):
        tail = tail.split(stop, 1)[0]
    return set() if tail in {"", "无"} else set(tail.split("、"))


# ---------- 13 触界收敛落地六键；未命中零副作用 ----------


def test_converge_lands_six_keys() -> None:
    """#13 触界收敛落地六键；未命中零副作用——行为 12（判定归 `state.check_limits`，本块只落地）。

    六键＝`budget_hit`（追加命中项）／`notices`（追加如实注记）／`answer`（正文＝已取得材料逐条
    如实交付）／`draft_kind="direct"`／`status="completed"`／`next_intent=answer`；除这六项外
    **零字段改动**（差集恰为六键）。未命中 → 状态深比较逐字段不变（零副作用）。
    """
    assert _SPEC_LIMIT_KEYS == set(LIMIT_KINDS)  # 七限额键名（流水 52-B：gates 取值域）
    state = _material_state()
    before = asdict(state)
    converge(state)
    assert _changed_fields(before, asdict(state)) == _SPEC_CONVERGENCE_KEYS

    # ①② 命中项与如实注记（`gates` 取 `LimitHit.limit` 键名；通知恰三键、只追加）
    assert state.budget_hit == ["rounds"]
    assert len(state.notices) == 1
    notice = state.notices[-1]
    assert tuple(notice) == ("type", "gates", "content")
    assert notice["type"] in NOTICE_TYPES
    assert notice["gates"] == ["rounds"]
    assert set(notice["gates"]) <= _SPEC_LIMIT_KEYS
    assert "未完成项" in notice["content"]  # 触界不静默
    # ③ 正文＝已取得材料逐条如实交付
    assert [line for line in state.answer.splitlines() if line.startswith("- ")] == [
        f"- {row['content']}" for row in _SPEC_MATERIAL_ROWS
    ]
    # ④⑤⑥ 收口三键
    assert state.draft_kind == "direct"
    assert state.status == "completed"
    assert state.next_intent == "answer"

    # 多命中：命中项逐条追加、不丢不重
    multi = _state(rounds=MAX_ROUNDS, discover_used=MAX_DISCOVERS_PER_RUN)
    converge(multi)
    assert multi.budget_hit == ["rounds", "discovers_per_run"]
    assert multi.notices[-1]["gates"] == ["rounds", "discovers_per_run"]

    # 未命中 → 零副作用（rounds 未达上限）
    fresh = _material_state(rounds=0)
    untouched = asdict(fresh)
    converge(fresh)
    assert asdict(fresh) == untouched


# ---------- 14 收敛幂等（二次调用不重复追加／不覆盖） ----------


def test_converge_idempotent() -> None:
    """#14 收敛幂等（二次调用不重复追加／不覆盖）——行为 12（治现状「已收敛仍可二次收敛」疑点）。

    已收敛（`budget_hit` 非空）再调 → **无操作**：通知条数与 `gates` 长度不变、答案与状态
    逐字段不变；幂等守卫在判定之前（已收敛态连判定都免——后继判定结果不再影响落地）。
    """
    state = _material_state()
    converge(state)
    once = asdict(state)
    gates_len = len(state.notices[-1]["gates"])

    converge(state)
    assert asdict(state) == once  # 不重复追加、不覆盖答案与状态
    assert len(state.notices) == 1
    assert len(state.notices[-1]["gates"]) == gates_len
    assert state.budget_hit == ["rounds"]

    # 已收敛态即便后继「未命中」也不动（幂等判据＝budget_hit 非空，不是重新判定）
    state.rounds = 0
    converged = asdict(state)
    converge(state)
    assert asdict(state) == converged


# ---------- 15 收敛答案与通知材料面同源（不漂移） ----------


def test_converge_material_same_source() -> None:
    """#15 收敛答案与通知材料面同源（不漂移）——行为 13（单一材料面，两处同一函数生成）。

    同一状态快照下，`answer` 正文与通知「未完成项」清单的材料标识集合**一致**；正文逐条同序
    如实交付；措辞由材料面决定（**不沿用旧码固定前缀「已取得材料未及核验」**——风险 6）。
    """
    state = _material_state()
    converge(state)
    answer = state.answer
    notice_content = state.notices[-1]["content"]
    assert [line[2:] for line in answer.splitlines() if line.startswith("- ")] == [
        row["content"] for row in _SPEC_MATERIAL_ROWS
    ]
    assert _material_ids_in(answer) == _material_ids_in(notice_content) == {
        row["source_id"] for row in _SPEC_MATERIAL_ROWS
    }
    assert "未及核验" not in answer  # 措辞随实际态（旧码前缀是缺陷，不承接）

    # 材料面第二来源（末次工具结果自带观察——尚未入栈亦属「已取得」）同源交付
    carried = _state(rounds=MAX_ROUNDS)
    carried.last_result = {
        "status": "ok",
        "observations": [{"content": "Y-23 井 3.0 t/d", "source_id": "src-exec-last"}],
        "ask": None,
        "error": None,
    }
    converge(carried)
    assert _material_ids_in(carried.answer) == _material_ids_in(carried.notices[-1]["content"])
    assert _material_ids_in(carried.answer) == {"src-exec-last"}

    # 零材料态：两处同口径（同一材料面为空——不冒充已交付）
    empty = _state(rounds=MAX_ROUNDS)
    converge(empty)
    assert _material_ids_in(empty.answer) == _material_ids_in(empty.notices[-1]["content"]) == set()
    assert "未取得可交付材料" in empty.answer
    assert "未取得可交付材料" in empty.notices[-1]["content"]


# ---------- 16 直答旁路恒写三键 ----------


def test_direct_answer_three_keys() -> None:
    """#16 直答旁路恒写三键——行为 14（拒答／闸拒／收敛转答／直答共用同一出口，免起草免核验）。

    四路调用方走**同一个函数**：三键齐备且取值固定（`draft=text`／`draft_kind="direct"`／
    `next_intent=answer`），三键之外零写（不动 `answer`／`verdict`／`status`）。
    """
    entries = (
        ("拒答", "抱歉，这个问题我不能回答。"),
        ("闸拒", "该请求涉及越集审批，已如实拒答。"),
        ("收敛转答", "预算触界——按已取得材料收敛。"),
        ("直答", "躺井：停产待检泵。"),
    )
    for label, text in entries:
        state = _state()
        before = asdict(state)
        direct_answer(state, text)
        assert state.draft == text, label
        assert state.draft_kind == "direct", label
        assert state.next_intent == "answer", label
        assert _changed_fields(before, asdict(state)) == _SPEC_DIRECT_ANSWER_KEYS, label
        assert state.answer == "" and state.verdict is None and state.status == RUN_RUNNING, label


# ---------- 17 调模型单点：只回 content，用量/归因落记账 ----------


class _SpyCompleter:
    """注入缝的同面缝（生产桥／替身同面）：记 `caller`／`run_id`／`messages` 进面；回执定值。"""

    def __init__(self, reply: ModelReply) -> None:
        self.reply = reply
        self.seen: list[tuple[str, str, list[dict[str, str]]]] = []

    async def complete(
        self, messages: Any, *, caller: str, run_id: str = ""
    ) -> ModelReply:
        self.seen.append((caller, run_id, [dict(message) for message in messages]))
        return self.reply


def test_call_model_keeps_accounting() -> None:
    """#17 调模型单点：只回 `content`，用量/归因落记账——行为 15（**禁裸文本吞掉记账面**）。

    从状态取 `run_id` → 调 `gateway_adapter.complete`（经 `set_completer` 注入的同面缝）→
    向节点只回 `content`；回执**余键**（用量与归因面）逐键入步记录 `payload`，`prompt_tokens`
    回填 `manifest.token_count`（每模型调用都有 Manifest）；失败尝试回执＝`status="failed"`。
    """
    messages = [{"role": "user", "content": "读题任务书：三区装配"}]
    state = _state()
    reply = ModelReply(
        content="路由意图：answer",
        caller="decision",
        run_id=state.run_id,
        alias="fake-model-a",
        prompt_tokens=123,
        completion_tokens=45,
        cached_tokens=7,
        usage_estimated=False,
        duration_ms=678,
    )
    spy = _SpyCompleter(reply)
    previous = set_completer(spy)
    try:
        content = call_model(state, "decision", messages)
    finally:
        set_completer(previous)

    assert content == "路由意图：answer" and isinstance(content, str)  # 只回 content
    assert spy.seen == [("decision", state.run_id, messages)]  # 从状态取 run_id 进面（逐调用盖章）
    assert len(state.steps) == 1
    step = state.steps[-1]
    assert tuple(step) == _SPEC_STEP_KEYS
    assert step["step"] == "decision"  # 三桶→步型（六值闭世界无 understand 型）
    assert step["status"] == "ok"
    assert step["seq"] == 1
    assert step["payload"] == {
        "caller": "decision",
        "run_id": state.run_id,
        "alias": "fake-model-a",
        "prompt_tokens": 123,
        "completion_tokens": 45,
        "cached_tokens": 7,
        "usage_estimated": False,
        "duration_ms": 678,
        "error": None,
    }
    assert "content" not in step["payload"]  # 裸文本不吞账、账不含文本
    assert step["manifest"]["token_count"] == 123  # 记账面回填 `token_count`
    assert set(step["manifest"]) == set(Manifest().as_dict())

    # 逐调用留痕（不覆盖）：换桶再调 → 新步落地，首步逐字不变；替身（生产同面）经同一缝
    first_step = deepcopy(step)
    scripted = ScriptedCompleter({"answer": ["终稿"]}, alias="fake-alias")
    previous = set_completer(scripted)
    try:
        second = call_model(state, "answer", [{"role": "user", "content": "作答任务书"}])
    finally:
        set_completer(previous)
    assert second == "终稿" and isinstance(second, str)
    assert scripted.calls == [("answer", [{"role": "user", "content": "作答任务书"}])]
    assert state.steps[0] == first_step
    assert [entry["seq"] for entry in state.steps] == [1, 2]
    assert state.steps[-1]["step"] == "answer"
    assert state.steps[-1]["payload"]["run_id"] == state.run_id

    # 失败尝试回执（`error` 非 None）→ 步态如实 `failed`；content 照原样回（不吞、不兜）
    failed = ModelReply(
        content="", caller="answer", run_id=state.run_id, error="上游拒绝 429: 限流"
    )
    previous = set_completer(_SpyCompleter(failed))
    try:
        assert call_model(state, "answer", messages) == ""
    finally:
        set_completer(previous)
    assert state.steps[-1]["status"] == "failed"
    assert state.steps[-1]["payload"]["error"] == "上游拒绝 429: 限流"

    # 归因桶闭世界（三桶族）：越界即拒（fail-closed，未发起调用）
    assert _SPEC_CALLERS == {"understand", "decision", "answer"}
    calls_before = len(state.steps)
    with pytest.raises(ValueError):
        call_model(state, "summarize", messages)
    assert len(state.steps) == calls_before


def test_call_model_system_injection_no_leak() -> None:
    """行为 15 的 2026-10-17 H 批注（角色分家·承载位）：`system` 注入参只随本次请求走。

    判据四面：① 有值 → **请求首条前置** `{"role": "system", …}`、其余逐字仍＝入参链；
    ② **不入链**（`state.messages` 零写、注入文本不出现在链上）；③ **不用即散**——下一次不带
    `system` 的调用请求＝入参链原样（**零泄漏到下一环节**）；④ 假值（`None`／空串）＝原链原样；
    ⑤ 记账面不受注入影响（步／Manifest 照落——「裸文本不吞账」）。
    """
    contract = "【相位①·业务澄清】本环节规章段（system 承载位）"
    chain = [{"role": "user", "content": "题面"}, {"role": "assistant", "content": "读题"}]
    state = _state()
    spy = _SpyCompleter(ModelReply(content="ok", caller="decision", run_id=state.run_id))
    previous = set_completer(spy)
    try:
        call_model(state, "decision", chain, system=contract)  # ① 有值 → 前置
        call_model(state, "decision", chain)  # ③ 不带 → 零残留
        call_model(state, "decision", chain, system="")  # ④ 空串 ＝ 缺省形
        call_model(state, "decision", chain, system=None)  # ④ None ＝ 缺省形
    finally:
        set_completer(previous)
    first, second, third, fourth = [sent for _caller, _run_id, sent in spy.seen]
    assert first == [{"role": "system", "content": contract}, *chain]
    assert second == chain and third == chain and fourth == chain
    # ② 不入链
    assert state.messages == [] and contract not in repr(state.messages)
    # ⑤ 记账面照落（四次调用四条步；`content` 不入账）
    assert len(state.steps) == 4
    assert all("content" not in step["payload"] for step in state.steps)



# ══════════ RT-W3-01c：装配与归一＋元面＋边界·保留集（规格表第 11、12、18、19、21–23 行）══════════
# 本票零 pin 行（5 条 pin 行全在 -01a）——下列用例只填行为体，不改 -01a／-01b 落地的形状（写口九
# 函数与收敛／收口签名）。

# ── 规格逐字面（独立于实现书写——实现漂移即红）────────────────────────────────────
# 过程档案条目形（`arch/P5b2` A-P5b2-03 逐字：{phase, title, digest}）；digest 上限真源＝同处
# 「digest 在写入点截断 ≤200 字」＋ `synth/S5-RunState字段矩阵.md`:33「过程档案（digest≤200）」
# ——规格「不复述数字」，故该值只钉在测试这一处真源面上。
_SPEC_NOTE_KEYS = ("phase", "title", "digest")
_SPEC_NOTE_DIGEST_LIMIT = 200
# 截断可见标记（行为 10 断言「截断可见」；同仓截断单点先例＝`persistence.summary` 的
# `TRUNCATION_MARK`「截断恒留可见标记、不静默截断」）。
_SPEC_TRUNCATION_MARK = "…"
# 通知恰三键（行为 11 逐字）
_SPEC_NOTICE_KEYS = ("type", "gates", "content")
# 工具上下文六字段（`specs/modules.md` `## tools` 卡逐字：actor／budget／metric_candidates／
# approved_tables＋V2-89b additive 留痕身份两键 run_id／sub_question_id）
_SPEC_TOOL_CONTEXT_FIELDS = (
    "actor", "budget", "metric_candidates", "approved_tables",
    "run_id", "sub_question_id",
)
# 结果投影键面（行为 17「无增删改名」——形状真源 `specs/modules.md` `## tools` 卡）
_SPEC_RESULT_KEYS = ("status", "observations", "ask", "error")


def _state_with_subtasks(count: int) -> RunState:
    """问题组 fixture（`question_group` 投影形＝`parsing` 的 `QuestionGroup.as_payload()`）。"""
    return _state(
        question_group={"subtasks": [{"id": f"s{index}"} for index in range(1, count + 1)]}
    )


# ---------- 11 过程档案 note 写入点截断且只追加 ----------


def test_note_bounded_append_only() -> None:
    """#11 过程档案 `note` 写入点截断且只追加——行为 10（上限真源 `synth/S5`:33／`arch/P5b2`
    A-P5b2-03，规格不复述数字）。

    三面：① 短摘要逐字照写（条目恰 `{phase, title, digest}` 三键）；② 恰在上限内不截、超长在
    **写入点**截断（长度受控且**截断可见**——不静默硬切片）；③ 只追加——既有条目逐字不变，快照
    往返后长度仍受控（写入点是唯一边界，消费侧读到的即受控形）。
    """
    from appv2.runtimev2.bookkeeping import constants as block_constants

    # 上限与标记单点（真源在别处、实现侧只许有一处）
    assert block_constants.NOTE_DIGEST_LIMIT == _SPEC_NOTE_DIGEST_LIMIT
    assert block_constants.TRUNCATION_MARK == _SPEC_TRUNCATION_MARK

    state = _state()
    note(state, phase="understand", title="读题", digest="三区装配：台账全量")
    entry = state.process_notes[-1]
    assert tuple(entry) == _SPEC_NOTE_KEYS
    assert entry == {"phase": "understand", "title": "读题", "digest": "三区装配：台账全量"}
    first = deepcopy(entry)

    # 恰在上限内：原样（不截、无标记）
    exact = "字" * _SPEC_NOTE_DIGEST_LIMIT
    note(state, phase="tool", title="doc_retrieve：ok", digest=exact)
    assert state.process_notes[-1]["digest"] == exact

    # 超长：写入点截断——长度受控、截断可见、内容仍是原文前缀（零改写）
    huge = "长" * (_SPEC_NOTE_DIGEST_LIMIT * 3)
    note(state, phase="tool", title="doc_retrieve：ok", digest=huge)
    recorded = state.process_notes[-1]["digest"]
    assert len(recorded) <= _SPEC_NOTE_DIGEST_LIMIT < len(huge)
    assert recorded.endswith(_SPEC_TRUNCATION_MARK)  # 截断可见（非静默硬切片）
    assert recorded[: -len(_SPEC_TRUNCATION_MARK)] == huge[: len(recorded) - 1]  # 原文前缀
    assert state.process_notes[0] == first  # 既有条目逐字不变

    # 只追加：条目数＝调用次数、旧条目逐字
    snapshot = deepcopy(state.process_notes)
    for index in range(3):
        note(state, phase="tool", title=f"台账 {index}", digest="一行")
    assert len(state.process_notes) == len(snapshot) + 3
    assert state.process_notes[: len(snapshot)] == snapshot
    assert all(tuple(item) == _SPEC_NOTE_KEYS for item in state.process_notes)

    # 快照往返：条目形与长度受控形逐字不变（写入点归一）
    restored = decode_state(encode_state(state))
    assert restored.process_notes == state.process_notes
    assert len(restored.process_notes[-1]["digest"]) <= _SPEC_NOTE_DIGEST_LIMIT


# ---------- 12 通知恰三键＋type／gates 闭世界 ----------


def test_notice_three_keys_closed_world() -> None:
    """#12 通知恰三键＋`type`／`gates` 闭世界——行为 11（`type` 真源 `transport.NOTICE_TYPES`；
    `gates` 真源 `state.LIMIT_KINDS` 七限额键名——流水 52-B）。

    四面：① 闭世界内取值（`type` 二十九值逐个、`gates` 七键子集）合法且落**恰三键**；② 缺键／多键
    在调用期即拒（签名面闭合）；③ 越界即拒（`type`／`gates` 双闭世界，零落地）；④ 只追加——通知列
    只增不减、既有条目逐字不变、`gates` 落列取拷贝（调用方改自己的列表不影响已落条目）。
    """
    # ① type 闭世界二十九值逐个（断言面＝`transport.NOTICE_TYPES` 本身，不复述取值清单）
    assert set(LIMIT_KINDS) == _SPEC_LIMIT_KEYS
    assert NOTICE_TYPES, "通知类型闭世界扫描面为空转"
    for notice_type in sorted(NOTICE_TYPES):
        state = _state()
        notice(state, type=notice_type, content=f"{notice_type} 注记")
        entry = state.notices[-1]
        assert tuple(entry) == _SPEC_NOTICE_KEYS
        assert entry == {"type": notice_type, "gates": [], "content": f"{notice_type} 注记"}

    # gates 子集（默认空；给子集照写；缺省形＝空列）
    state = _state()
    gates = ["rounds", "ask_cap"]
    notice(state, type="budget_converged", gates=gates, content="触界")
    gates.append("seconds")  # 落列取拷贝——调用方后续改动不影响已落条目
    note_entry = state.notices[-1]
    assert note_entry["gates"] == ["rounds", "ask_cap"]
    assert note_entry["gates"] is not gates
    notice(state, type="decision_note", content="读题注记")
    assert state.notices[-1]["gates"] == []
    assert len(state.notices) == 2

    # ② 恰三键：缺键／多键在调用期即拒（不落条目）
    with pytest.raises(TypeError):
        notice(state, type="run_failed")  # 缺 content
    with pytest.raises(TypeError):
        notice(state, content="缺 type")  # 缺 type
    with pytest.raises(TypeError):
        notice(state, type="run_failed", content="多键", extra="第四键")  # 多键

    # ③ 越界即拒（fail-closed；不吞错、不落哨兵）
    for bad_type in ("notice", "", "budget", "BUDGET_CONVERGED"):
        with pytest.raises(ValueError):
            notice(state, type=bad_type, content="越界类型")
    for bad_gates in (
        ("max_rounds",),
        ("轮数",),
        ("rounds", "total_seconds"),
        ("rounds", "unknown"),
    ):
        with pytest.raises(ValueError):
            notice(state, type="budget_converged", gates=bad_gates, content="越界闸名")
    assert len(state.notices) == 2  # 越界与缺／多键都不落

    # ④ 只追加：列只增不减、既有条目逐字不变；快照往返归一
    snapshot = deepcopy(state.notices)
    notice(state, type="run_failed", gates=("tool_timeout",), content="上游失败")
    assert state.notices[: len(snapshot)] == snapshot
    assert len(state.notices) == len(snapshot) + 1
    assert all(tuple(item) == _SPEC_NOTICE_KEYS for item in state.notices)
    restored = decode_state(encode_state(state))
    assert restored.notices == state.notices


# ---------- 18 工具上下文：身份只从状态取、放行态随上下文、预算按子问题数 ----------


def test_tool_context_assembly() -> None:
    """#18 工具上下文装配——行为 16（数值与公式真源＝`appv2.tools` 的 `resolve_send_budget`，
    规格不复述数值）。

    三面：① **身份只从状态取**（签名不接调用方传身份；换状态即换身份）；② **放行态随上下文走**
    ——`approved_tables` 取自状态且**参数的 schema 里无放行字段**（工具调用面＝`call(name, args,
    ctx)`，`args` 与 `ctx` 分离）；③ **预算按子问题数**——逐个与公式函数对表，且本块用的就是
    `appv2.tools` 的**同一个函数**（只引不复述＝无本块副本、无本块算式）。
    """
    from appv2.runtimev2.bookkeeping import projection as projection_module

    # 身份不接调用方传：签名只有 state（无身份入参）
    assert tuple(inspect.signature(tool_context).parameters) == ("state",)
    # 六字段＝卡面形状（字段序同卡；V2-89b 补留痕身份两键）
    assert [field.name for field in fields(ToolContext)] == list(_SPEC_TOOL_CONTEXT_FIELDS)

    state = _state(
        actor="laowang",
        approved_ids=["agg.fct_daily_metering"],
        metric_candidates=["日产油量"],
        question_group={"subtasks": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]},
    )
    context = tool_context(state)
    assert context.actor == state.actor == "laowang"  # 身份只从状态取
    assert context.approved_tables == tuple(state.approved_ids)  # 放行态随上下文走
    assert context.metric_candidates == ("日产油量",)
    assert context.budget == resolve_send_budget(3)  # 预算按子问题数（3 支）
    # V2-89b 留痕身份两键：run_id 恒从状态取；多支组拿不到「当前支」——如实留白
    # （逐支派遣载荷不在本块可及面，不发明归属）。
    assert context.run_id == state.run_id == "run-bk-01"
    assert context.sub_question_id == ""
    # 恰一支问题组＝可归属（子问题 id 逐字注入）。
    single = tool_context(
        _state(run_id="run-bk-09", question_group={"subtasks": [{"id": "s7"}]})
    )
    assert single.run_id == "run-bk-09" and single.sub_question_id == "s7"

    # 换状态即换身份／放行集（不是调用方传的常量、也不吃上一份状态）
    other = _state(actor="xiaoqi", approved_ids=["lake.raw_wells"], metric_candidates=[])
    other_context = tool_context(other)
    assert other_context.actor == "xiaoqi" != context.actor
    assert other_context.approved_tables == ("lake.raw_wells",)
    assert other_context.metric_candidates is None  # 空候选列＝未启用（现状形）

    # ③ 预算随子问题数：逐个与公式函数对表（无组／残形按 1 支计——下限由该函数自身兜）
    for count in (1, 2, 3, 6, 40):
        assert tool_context(_state_with_subtasks(count)).budget == resolve_send_budget(count), count
    no_group = tool_context(_state())
    assert no_group.budget == resolve_send_budget(1)
    assert no_group.actor == _state().actor and no_group.approved_tables == ()
    ragged = _state(question_group={"subtasks": [{"id": "s1"}, "残形", 7]})
    assert tool_context(ragged).budget == resolve_send_budget(1)  # 非 mapping 条目不计

    # 只引不复述：本块引用的是 `appv2.tools` 的同一个函数（无本块副本、无本块算式）
    assert projection_module.resolve_send_budget is resolve_send_budget

    # ② 参数里无放行态：调用面 args 与 ctx 分离；工具参数 schema 无放行字段（放行态只在 ctx）
    assert tuple(inspect.signature(ToolRegistry.call).parameters) == ("self", "name", "args", "ctx")
    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )
    descriptors = registry.descriptors()
    assert descriptors, "工具目录扫描面为空转"
    for descriptor in descriptors:
        leaking = sorted(
            key for key in _schema_keys(descriptor.args_schema) if _looks_like_approval(key)
        )
        assert not leaking, f"{descriptor.name} 的 args_schema 出现放行态字段：{leaking}"


_APPROVAL_HINTS = ("approved", "放行", "审批")


def _looks_like_approval(key: str) -> bool:
    """该键名是否像「放行态」（放行态只许活在 `ToolContext`，不许进工具参数）。"""
    return any(hint in key for hint in _APPROVAL_HINTS)


def _schema_keys(schema: Any) -> set[str]:
    """schema 里出现过的全部键名（递归——嵌套 `properties` 一并扫）。"""
    keys: set[str] = set()
    if isinstance(schema, Mapping):
        for key, value in schema.items():
            keys.add(str(key))
            keys |= _schema_keys(value)
    elif isinstance(schema, (list, tuple)):
        for item in schema:
            keys |= _schema_keys(item)
    return keys


# ---------- 19 结果投影原样（空值与缺省可区分） ----------


def test_result_projection_faithful() -> None:
    """#19 结果投影原样（空值与缺省可区分）——行为 17（治现状 `detail or None` 假值归一，
    `recon/B1` D-B1-13）。

    三面：① 逐字段**原样投影**（键集合与字段集合逐字相等、键序同形状、值相等、无增删改名）；
    ② 键集合固定（任意三态同键集——空态也带键）；③ **空值与缺省不等价**（`detail={}` 与
    `detail=None` 两态投影后不同且读回仍可区分；`well=""` 与 `well=None`、`hint=""` 与
    `hint=None` 同理），且投影是 JSON 原语形（入状态／快照往返无损）。
    """
    observation = Observation(
        content="Y-21 井 2026 年产油量 12.5 t/d",
        source="agg.fct_daily_metering#Y-21",
        source_id="src-ledger-daily-oil",
        version=None,
        freshness="fresh",
        scope="well:Y-21",
        locator={"kind": "agg_row", "table": "agg.fct_daily_metering"},
        well=None,
    )
    projected = result_projection(
        ToolResult(status="ok", observations=(observation,), ask=None, error=None)
    )
    # ① 顶层四键与行键面＝形状字段（逐字、同序、无增删改名）
    assert tuple(projected) == _SPEC_RESULT_KEYS
    assert [field.name for field in fields(ToolResult)] == list(_SPEC_RESULT_KEYS)
    row = projected["observations"][0]
    assert tuple(row) == tuple(field.name for field in fields(Observation))
    assert all(row[field.name] == getattr(observation, field.name) for field in fields(Observation))
    assert row["locator"] == dict(observation.locator)
    assert row["locator"] is not observation.locator  # 浅拷（投影非别名）
    assert projected["ask"] is None and projected["error"] is None

    ask_empty_detail = result_projection(
        ToolResult(
            status="ask",
            observations=(),
            ask=AskFrame(kind="clarify", prompt="问哪口井？", detail={}),
            error=None,
        )
    )
    ask_no_detail = result_projection(
        ToolResult(
            status="ask",
            observations=(),
            ask=AskFrame(kind="clarify", prompt="问哪口井？", detail=None),
            error=None,
        )
    )
    failed = result_projection(
        ToolResult(
            status="failed",
            observations=(),
            ask=None,
            error=ToolError(category="retryable", message="上游抖动", hint=None),
        )
    )
    # ② 键集合固定（三态同键集；嵌套行键面＝各自形状字段）
    assert (
        set(projected)
        == set(ask_empty_detail)
        == set(ask_no_detail)
        == set(failed)
        == set(_SPEC_RESULT_KEYS)
    )
    assert tuple(ask_empty_detail["ask"]) == tuple(field.name for field in fields(AskFrame))
    assert tuple(failed["error"]) == tuple(field.name for field in fields(ToolError))
    assert ask_empty_detail["observations"] == []  # 空列＝在场且为空（不归 None）

    # ③ 空值与缺省不等价（禁真假值归一）
    assert ask_empty_detail["ask"]["detail"] == {}
    assert ask_no_detail["ask"]["detail"] is None
    assert ask_empty_detail != ask_no_detail
    empty_well = result_projection(
        ToolResult(
            status="ok",
            observations=(_observation(well=""),),
            ask=None,
            error=None,
        )
    )
    missing_well = result_projection(
        ToolResult(
            status="ok",
            observations=(_observation(well=None),),
            ask=None,
            error=None,
        )
    )
    assert empty_well["observations"][0]["well"] == ""
    assert missing_well["observations"][0]["well"] is None
    assert empty_well != missing_well
    empty_hint = result_projection(
        ToolResult(
            status="failed",
            observations=(),
            ask=None,
            error=ToolError(category="retryable", message="上游抖动", hint=""),
        )
    )
    assert empty_hint["error"]["hint"] == "" and failed["error"]["hint"] is None
    assert empty_hint != failed

    # 投影是 JSON 原语形＋入状态读回可区分（承接面＝快照往返）
    assert json.loads(json.dumps(projected, ensure_ascii=False)) == projected
    state = _state()
    state.last_result = projected
    restored = decode_state(encode_state(state))
    assert restored.last_result == projected
    assert restored.last_result["observations"][0]["well"] is None
    state.last_result = ask_empty_detail
    restored = decode_state(encode_state(state))
    assert restored.last_result["ask"]["detail"] == {}  # 「有该字段但为空」读回仍是空 dict
    state.last_result = ask_no_detail
    restored = decode_state(encode_state(state))
    assert restored.last_result["ask"]["detail"] is None  # 「无该字段」读回仍是 None


def _observation(*, well: str | None) -> Observation:
    """观察行 fixture（只变 `well`——空串与缺省两态的对照件）。"""
    return Observation(
        content="Y-23 井 3.0 t/d",
        source="agg.fct_daily_metering#Y-23",
        source_id="src-exec-last",
        version=None,
        freshness="fresh",
        scope="well:Y-23",
        locator={"kind": "agg_row"},
        well=well,
    )


# ---------- 21 本块零判断（AST 扫描） ----------


# 行为 18 逐字「除 `call_model` 的转发与两侧闭世界分派外」的落地形——本块允许的跨块调用点：
# 判定归 `state`（`check_limits`）＋状态形状构造（`Manifest`）、模型出口转发（`complete`）、
# 送窗预算算式（`resolve_send_budget`）＋形状块类型构造（`ToolContext`）；`persistence`／
# `transport` **只引类型与常量**（零调用）。
_ALLOWED_CROSS_BLOCK_CALLS: dict[str, frozenset[str]] = {
    "appv2.runtimev2.state": frozenset({"check_limits", "Manifest"}),
    "appv2.runtimev2.gateway_adapter": frozenset({"complete"}),
    "appv2.tools": frozenset({"ToolContext", "resolve_send_budget"}),
    "appv2.runtimev2.persistence": frozenset(),
    "appv2.runtimev2.transport": frozenset(),
}
# 正则／词表机械（语义判定的底座——本块禁）
_JUDGEMENT_MODULES = frozenset({"re", "regex", "fnmatch", "difflib"})
# 词面判定方法（子串／大小写／正则族方法——本块禁）
_JUDGEMENT_METHODS = frozenset(
    {
        "match",
        "search",
        "fullmatch",
        "findall",
        "finditer",
        "sub",
        "subn",
        "startswith",
        "endswith",
        "find",
        "count",
        "casefold",
        "lower",
        "upper",
    }
)


def _module_bindings(tree: ast.Module) -> dict[str, tuple[str, str]]:
    """模块级 import 绑定表：本地名 → (模块全名, 被引原名〔`import M` 形为空串〕)。"""
    bindings: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                bindings[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bindings[alias.asname or alias.name.split(".")[0]] = (alias.name, "")
    return bindings


def _block_calls(tree: ast.Module) -> list[tuple[int, str, str]]:
    """本模块对「五块」的调用点全列：`(行号, 模块全名, 被调名)`（经 import 绑定表解析本地名）。"""
    bindings = _module_bindings(tree)
    calls: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in bindings:
            module, original = bindings[func.id]
            calls.append((node.lineno, module, original or func.id))
        elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            module, original = bindings.get(func.value.id, ("", ""))
            if module and not original:  # `import M as m; m.f(...)` 形
                calls.append((node.lineno, module, func.attr))
    return calls


def _is_inline_word_list(node: ast.expr) -> bool:
    """内联字面量「词表」判定：`x in ("a", "b")` 一类（闭世界取值必须来自在册常量，不许内联）。"""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        return bool(node.elts) and all(
            isinstance(element, ast.Constant) and isinstance(element.value, str)
            for element in node.elts
        )
    return False


def _judgement_hits(tree: ast.Module) -> list[str]:
    """零判断扫描命中项：词表／正则机械 import、词面判定方法、内联词表成员判定。"""
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _JUDGEMENT_MODULES:
                    hits.append(f"词表/正则机械 import：{alias.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in _JUDGEMENT_MODULES:
                hits.append(f"词表/正则机械 import：{node.module}")
        elif isinstance(node, ast.Attribute) and node.attr in _JUDGEMENT_METHODS:
            hits.append(f"词面判定方法：.{node.attr}")
        elif isinstance(node, ast.Compare) and any(
            isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
        ):
            for comparator in node.comparators:
                if _is_inline_word_list(comparator):
                    hits.append(f"内联词表判定：{ast.unparse(comparator)[:40]}")
    return hits


def test_no_judgement_in_bookkeeping() -> None:
    """#21 本块零判断（AST 扫描）——行为 18：除 `call_model` 的转发与两侧闭世界分派外，无词表／
    正则语义判定。

    三面机检：① 词表／正则机械与词面判定方法零出现；② 成员判定不许内联字面量词表（闭世界取值
    只许引在册常量）；③ 跨块调用点逐个在册（判定归 `state`、转发 `complete`、算式
    `resolve_send_budget`、形状块类型构造 `ToolContext`——`persistence`／`transport` 零调用）。
    """
    scanned: list[str] = []
    state_calls: set[str] = set()
    gateway_calls: set[str] = set()
    tools_calls: set[str] = set()
    shape_calls: list[str] = []
    for path in _bookkeeping_files():
        scanned.append(path.name)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # ①② 零判断面
        assert not _judgement_hits(tree), f"{path.name} 出现语义判定：{_judgement_hits(tree)}"
        # ③ 跨块调用白名单
        for line, module, name in _block_calls(tree):
            if module == "appv2.runtimev2.state":
                state_calls.add(name)
            elif module == "appv2.runtimev2.gateway_adapter":
                gateway_calls.add(name)
            elif module == "appv2.tools":
                tools_calls.add(name)
            if module in _ALLOWED_CROSS_BLOCK_CALLS:
                assert name in _ALLOWED_CROSS_BLOCK_CALLS[module], (
                    f"{path.name}:{line} 越出跨块调用白名单：{module}.{name}"
                )
            if module in ("appv2.runtimev2.persistence", "appv2.runtimev2.transport"):
                shape_calls.append(f"{path.name}:{line} {module}.{name}")

    assert "ports.py" in scanned and "closing.py" in scanned and "projection.py" in scanned
    # 非空转：三处真实调用点各在场（判定／转发／算式——白名单不是空名单）
    assert "check_limits" in state_calls, state_calls
    assert "complete" in gateway_calls, gateway_calls
    assert "resolve_send_budget" in tools_calls, tools_calls
    assert not shape_calls, f"形状块被引了行为面（调用）：{shape_calls}"

    # 探测器非空转：伪造三条判定形必被咬（词表内联／正则机械／词面方法）
    forged = ast.parse(
        "import re\n"
        "def classify(text):\n"
        "    if re.search('注水', text):\n"
        "        return 'water'\n"
        "    if text in {'步骤', '指令'}:\n"
        "        return 'task'\n"
        "    return text.lower()\n"
    )
    forged_hits = _judgement_hits(forged)
    assert any("内联词表判定" in hit for hit in forged_hits), forged_hits  # 内联词表
    assert any(hit.startswith("词表/正则机械") for hit in forged_hits), forged_hits  # 正则机械
    assert any(hit.endswith(".search") for hit in forged_hits), forged_hits  # 词面方法
    assert any(hit.endswith(".lower") for hit in forged_hits), forged_hits
    assert len(forged_hits) >= 4, forged_hits


# ---------- 22 【边界集】空步列／超长 digest／已收敛再收敛／越界枚举 ----------


def test_boundary_empty_huge_converged_enum() -> None:
    """#22【边界集】空步列／超长 digest／已收敛再收敛／越界枚举 → 各落对应分支。

    四形各落对应分支（分支本体在 -01a 行 3／4、-01b 行 14、-01a 行 9／10）：① 空步列＝首号 1、
    空材料面工具面不炸链；② 超长 digest＝写入点截断且可见（行为 10）；③ 已收敛再收敛＝无操作
    （行为 12 幂等，不重复追加／不覆盖）；④ 越界枚举＝双闭世界各拒且零落地（fail-closed）。
    """
    # ① 空步列
    empty = _state()
    assert empty.steps == [] and empty.notices == [] and empty.process_notes == []
    assert next_seq(empty) == 1
    first = record_step(empty, kind="decision", title="首步")
    assert first["seq"] == 1 and len(empty.steps) == 1 and tuple(first) == _SPEC_STEP_KEYS
    assert tool_context(empty).actor == empty.actor  # 空步列状态也能装配（不炸链）
    assert result_projection(
        ToolResult(status="ok", observations=(), ask=None, error=None)
    )["observations"] == []

    # ② 超长 digest（写入点截断：长度受控＋截断可见）
    huge = "长" * (_SPEC_NOTE_DIGEST_LIMIT + 1)
    note(empty, phase="tool", title="台账", digest=huge)
    bounded = empty.process_notes[-1]["digest"]
    assert len(bounded) <= _SPEC_NOTE_DIGEST_LIMIT
    assert bounded.endswith(_SPEC_TRUNCATION_MARK)
    assert bounded[:-1] == huge[: len(bounded) - 1]

    # ③ 已收敛再收敛（幂等：无操作）
    converged = _material_state()
    converge(converged)
    settled = asdict(converged)
    notice_count = len(converged.notices)
    converge(converged)
    assert asdict(converged) == settled
    assert len(converged.notices) == notice_count and converged.budget_hit == ["rounds"]

    # ④ 越界枚举（四种形各拒；状态零落地）
    enum_state = _state()
    before = asdict(enum_state)
    with pytest.raises(ValueError):
        record_step(enum_state, kind="reflect", title="越界步类型")
    with pytest.raises(ValueError):
        record_step(enum_state, kind="decision", title="越界步状态", status="error")
    with pytest.raises(ValueError):
        append_contract(enum_state, "understand")
    with pytest.raises(ValueError):
        append_message(enum_state, role="tool", content="越界角色")
    with pytest.raises(ValueError):
        append_dialogue(enum_state, role="user", content="越界来源", origin="task_book")
    with pytest.raises(ValueError):
        set_intent(enum_state, "route_home")
    with pytest.raises(ValueError):
        notice(enum_state, type="notice", content="越界通知类型")
    with pytest.raises(ValueError):
        notice(enum_state, type="budget_converged", gates=("max_rounds",), content="越界闸名")
    assert asdict(enum_state) == before


# ---------- 23 【保留集】常规三步流程的记录形状与顺序不变 ----------


def test_retention_normal_three_steps() -> None:
    """#23【保留集】常规三步流程的记录形状与顺序不变——-01a 落地的写口与 -01b 落地的收口面
    不因本票改形。

    常规三步（决策→发现→作答）走全部写口与读面后：步记录七字段同序、序号 1／2／3；过程档案／
    通知／对话链／对话层条目形状与追加顺序不变；读面（`tool_context`／`result_projection`）
    零副作用；快照往返后记录形状与顺序逐字不变。
    """
    state = _state(question_group={"subtasks": [{"id": "s1"}]})
    append_message(state, role="user", content="任务书：……")
    note(state, phase="understand", title="读题", digest="三区装配")
    notice(state, type="decision_note", content="读题注记")
    record_step(state, kind="decision", title="决策：读题")
    set_intent(state, "discover")

    append_message(state, role="user", content="相位合同：……")
    note(state, phase="tool", title="doc_retrieve：ok", digest="参数：… → 结果：2 行")
    record_step(state, kind="discover", title="发现：检索", payload={"probes": 2})
    append_dialogue(state, role="user", content="这口井 2026 年日产油量？", origin="user_verbatim")

    set_intent(state, "answer")
    record_step(state, kind="answer", title="作答：收口", manifest=Manifest())
    append_message(state, role="assistant", content="终稿")
    append_dialogue(
        state, role="assistant", content="日产油量 12.5 t/d。", origin="assistant_final"
    )

    # 步记录：七字段同序、序号与步型顺序不变
    assert [step["seq"] for step in state.steps] == [1, 2, 3]
    assert [step["step"] for step in state.steps] == ["decision", "discover", "answer"]
    assert all(tuple(step) == _SPEC_STEP_KEYS for step in state.steps)
    assert next_seq(state) == len(state.steps) + 1 == 4
    # 过程档案／通知／对话链／对话层：条目形状与追加顺序不变
    assert all(tuple(entry) == _SPEC_NOTE_KEYS for entry in state.process_notes)
    assert [entry["phase"] for entry in state.process_notes] == ["understand", "tool"]
    assert all(tuple(entry) == _SPEC_NOTICE_KEYS for entry in state.notices)
    assert [entry["type"] for entry in state.notices] == ["decision_note"]
    assert all(set(entry) == {"role", "content"} for entry in state.messages)
    assert all(tuple(entry) == ("role", "content", "origin") for entry in state.dialogue)

    # 读面零副作用（工具上下文装配与结果投影不改状态）
    before = asdict(state)
    tool_context(state)
    result_projection(
        ToolResult(status="ok", observations=(_observation(well=None),), ask=None, error=None)
    )
    assert asdict(state) == before

    # 快照往返：记录形状与顺序逐字不变（归一形）
    restored = decode_state(encode_state(state))
    assert restored.steps == state.steps
    assert restored.process_notes == state.process_notes
    assert restored.notices == state.notices
    assert restored.messages == state.messages
    assert restored.dialogue == state.dialogue
    assert restored.next_intent == state.next_intent
    assert tuple(restored.steps[-1]) == _SPEC_STEP_KEYS
