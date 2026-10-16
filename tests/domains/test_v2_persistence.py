"""persistence 块验收（RT-W2-01a：骨架＋接口＋落盘读回主干＋本块全部 3 条 pin 行；
RT-W2-01b：守门与红线面／元／边界·保留集）。

票面对象＝`specs/persistence.md`「验收测试」表：-a 收第 1–5、9、10、11、12、15 行；**-b** 收第
6、7、8、13、14、16、17、18、19、20 行（逐字，测试标识同规格列；`#` 保留规格表行序、不重编）。
测试网钉＝pin-12（`::verify_fields_readable_in_step`，落盘面）／pin-28
（`::run_id_stamped_across_records`，落盘面）／pin-30（`::legacy_read_honest`——本块**唯一**挂断言的
面：旧 run **黑匣子回放**如实；检查点状态字段读入面挂 `specs/state.md` 行为 8，两处对象不同）——三钉
全在 -a，-b 零 pin 行。

真源指针：形状＝`specs/modules.md` `## persistence` 卡＋`specs/persistence.md` 接口定义节；
列事实与常量＝`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`（R-J-02 白名单／R-J-05 审计
action 七值／R-J-06 摘要长度 120／R-J-17 唯一合法转移／R-J-50 身份面四键／R-J-60 单行 96／
R-J-62 分面 30·60·80·40／R-J-63 空白折叠）；`pin-12` 字段面＝`specs/verification.md`
行为 11（`delivered_rows`／`obs_rows`）＋`arch/P7a-交接包与挂账清单.md` A-P7a-38；`pin-28` 对账口径
＝`eval/results/Q15-对账报告.md`（逐题 `ledger_run_ids` 与 jsonl 同跑 `run_id` 集合等值）。

时间列一律经 `infra.clock`（B14）——本件用 `clock.freeze` 冻结，`RunStore` 缺省钟即走该出口。
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Iterator, Sequence
from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import datetime
from inspect import signature
from pathlib import Path
from typing import Any

import pytest

from appv2.infra import clock
from appv2.runtimev2.persistence import (
    APPEND_ONLY_TABLES,
    AUDIT_ACTION_PREFIX,
    AUDIT_ACTION_REFUSED,
    AUDIT_ACTION_RUN_COMPLETED,
    AUDIT_ACTION_RUN_CREATED,
    AUDIT_ACTIONS,
    AUDIT_REQUIRED_FIELDS,
    BLACKBOX_ALLOWED_KEYS,
    BLACKBOX_IDENTITY_KEYS,
    BLACKBOX_LINE_LIMIT,
    BLACKBOX_NEWLINE_MARK,
    BLACKBOX_RECORD_KEYS,
    BOOKKEEPING_TABLE_PREFIX,
    CHECKPOINT_KIND_STATE,
    CHECKPOINT_TABLES,
    DEFAULT_NS,
    FACET_LIMITS,
    REPLAY_CHANNELS,
    SUMMARY_LIMIT,
    TABLE_BLACKBOX,
    TABLE_BLOB,
    TABLE_CHECKPOINT,
    TABLE_CHECKPOINT_BLOB,
    TABLE_CHECKPOINT_WRITE,
    TABLE_RUN,
    TABLE_STEP,
    TABLES,
    TRUNCATION_MARK,
    AlreadyArchivedError,
    AuditActionOutOfWorldError,
    AuditElementMissingError,
    AuditRecord,
    BlackBox,
    BlackBoxKeyOutOfWorldError,
    BlobRef,
    CheckpointBlobRow,
    CheckpointRow,
    CheckpointWriteRow,
    MemoryTables,
    PersistenceError,
    RowOp,
    RunNotFoundError,
    RunRecord,
    RunStore,
    StatusTransitionError,
    StepConflictError,
    StepRecord,
    TableWriteError,
    UnknownHandleError,
    audit,
    checkpoint_blobs,
    checkpoint_rows,
    checkpoint_writes,
    configure_audit_sink,
    delete_thread,
    encode_metadata,
    encode_state,
    facet_head,
    head,
    put_checkpoint_rows,
    replay_channels,
    summarize,
)
from appv2.runtimev2.state import DIALOGUE_ORIGINS, RUN_STATUS_KINDS, STEP_KINDS, RunState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PERSISTENCE_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "persistence"
_T0 = datetime(2026, 10, 16, 9, 0, 0)

# 规格 「接口定义」节的两个闭世界（本块**引 state 常量**、不复述取值——本件断言引面不漂）
_SPEC_RUN_STATUSES = {"running", "waiting_ask", "completed", "failed"}
_SPEC_STEP_KINDS = {"decision", "discover", "execute", "observe", "verify", "answer"}
_SPEC_STEP_STATUSES = {"ok", "failed", "refused"}

# 规格 行为 6 的 action 闭世界七值（真源 recon/J R-J-05——计数唯一口径＝七值本身）
_SPEC_AUDIT_ACTIONS = {
    "agent_v2.run_created",
    "agent_v2.run_completed",
    "agent_v2.run_failed",
    "agent_v2.refused",
    "agent_v2.extable_approved",
    "agent_v2.extable_rejected",
    "agent_v2.ban_exempt",
}
# 规格 行为 13 的截断长度（真源 recon/J R-J-06／R-J-60／R-J-62——分面名即 R-J-62 分面）
_SPEC_FACET_LIMITS = {
    "title_process_notes": 30,
    "title_steps": 60,
    "digest": 80,
    "source": 40,
    "content": 96,
}
# 检查点三表（写操作只经五个行级口——行 13）：源面常量名与表名字面值两形都算直连判据
_CHECKPOINT_TABLE_MARKS = (
    "TABLE_CHECKPOINT",
    "TABLE_CHECKPOINT_BLOB",
    "TABLE_CHECKPOINT_WRITE",
    TABLE_CHECKPOINT,
    TABLE_CHECKPOINT_BLOB,
    TABLE_CHECKPOINT_WRITE,
)

# 禁引模块（行 18 AST 红线）：正则／词表族 ＋ 模型出口族 ＋ 框架族（R5b 与 R7 的 AST 降维面）
_FORBIDDEN_IMPORT_MODULES = (
    "re",
    "regex",
    "litellm",
    "openai",
    "anthropic",
    "langgraph",
    "langchain",
    "langchain_core",
    "langchain_community",
    "appv2.infra.llm_client",
)
_REGEX_CALL_NAMES = (
    "match",
    "fullmatch",
    "search",
    "findall",
    "finditer",
    "compile",
    "sub",
    "split",
)
_MODEL_CALL_NAMES = (
    "complete",
    "acomplete",
    "chat",
    "responses",
    "embed",
    "embedding",
    "embeddings",
)
_LEXICON_NAME_MARKS = ("lexicon", "wordlist", "keyword_table", "词表")

# v1 旧黑匣子记录（`recon/I2b` 旧形）：对话条目只有 `{role, content}`、**无来源标签**
_V1_BLACKBOX_RECORD: dict[str, Any] = {
    "run_id": "run-v1",
    "question": "旧问句",
    "status": "completed",
    "error": "",
    "messages": [{"role": "user", "content": "旧任务书"}],
    "dialogue": [{"role": "user", "content": "旧对话"}, {"role": "assistant", "content": "旧终稿"}],
    "steps": [{"seq": 1, "kind": "decision", "title": "旧步"}],
    "answer": "旧答案",
}

# v1 旧检查点载荷（`recon/I2b` 旧码字段面）：含已取消字段、`budget` 裸 dict、无来源标签的对话条目
_V1_STATE_PAYLOAD: dict[str, Any] = {
    "run_id": "run-v1",
    "question": "旧问句",
    "actor": "laowang",
    "status": "completed",
    "followup_of": "",
    "messages": [{"role": "user", "content": "旧任务书"}],
    "dialogue": [{"role": "user", "content": "旧对话"}],
    "schema_version": 1,
    "rounds": 1,
    "consecutive_asks": 0,  # 已取消字段（流水 49①）
    "manifests": [],  # 已取消字段
    "budget": {"rounds": 3, "discovers_per_round": 2, "unknown_legacy_key": 1.0},
    "budget_hit": [],
    "answer": "旧答案",
    "manifest_digest": "",
    "error": None,
}


@pytest.fixture(autouse=True)
def _frozen_clock() -> Iterator[None]:
    """冻结钟：`RunStore` 缺省钟＝`infra.clock.now`（B14 唯一时间出口）。"""
    with clock.freeze(_T0):
        yield


@pytest.fixture
def audit_records() -> Iterator[list[AuditRecord]]:
    """审计写口替身（真件＝`security.audit` 桥，B12；本票不建 DB 连接件）。"""
    collected: list[AuditRecord] = []
    previous = configure_audit_sink(collected.append)
    yield collected
    configure_audit_sink(previous)


# ---------- fixture 与 helpers ----------


def _store() -> tuple[RunStore, MemoryTables]:
    tables = MemoryTables()
    return RunStore(tables), tables


def _run(run_id: str = "run-a", *, status: str = "running", **overrides: Any) -> RunRecord:
    values: dict[str, Any] = {
        "run_id": run_id,
        "question": "渤海某井 2026 年日产油量？",
        "actor": "laowang",
        "status": status,
        "answer": None,
        "error": None,
        "manifest_digest": None,
        "followup_of": "",
        "created_at": _T0,
        "updated_at": _T0,
    }
    values.update(overrides)
    return RunRecord(**values)


def _step(run_id: str = "run-a", seq: int = 1, **overrides: Any) -> StepRecord:
    values: dict[str, Any] = {
        "run_id": run_id,
        "seq": seq,
        "step": "decision",
        "status": "ok",
        "title": "决策",
        "manifest": None,
        "payload": None,
        "created_at": _T0,
    }
    values.update(overrides)
    return StepRecord(**values)


def _blackbox(run_id: str = "run-a", record: dict[str, Any] | None = None) -> BlackBox:
    return BlackBox(
        run_id=run_id,
        record={"run_id": run_id, "status": "completed"} if record is None else record,
        created_at=_T0,
    )


def _audit(run_id: str = "run-a", *, action: str = AUDIT_ACTION_RUN_CREATED) -> AuditRecord:
    return AuditRecord(
        run_id=run_id,
        who="老王 · 油藏工程师",
        scope="会话线程 run-a／子问题域 全量",
        action=action,
        authorization="",
        facts="问答受理",
        evidence={"run_id": run_id},
    )


def _source_trees() -> list[tuple[str, ast.Module]]:
    return [
        (path.name, ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(_PERSISTENCE_DIR.rglob("*.py"))
    ]


def _arg_name(node: ast.expr) -> str:
    """实参名面：字面量取字面值，`Name` 取标识符，其余记「非字面量」。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    return "<非字面量>"


def _is_row_op(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "RowOp"
    )


def _row_op_sites(trees: Sequence[tuple[str, ast.Module]]) -> list[tuple[str, int, str, str]]:
    """本块源码里 `RowOp(...)` 的全部构造位点 → `(文件, 行, 表名实参, 操作实参)`。"""
    sites: list[tuple[str, int, str, str]] = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if _is_row_op(node):
                sites.append((name, node.lineno, _arg_name(node.args[0]), _arg_name(node.args[3])))
    return sites


def _row_op_violations(sites: Sequence[tuple[str, int, str, str]]) -> list[str]:
    """「只追加／无改写删除路径」的静态判据：操作实参必须闭世界且字面；只追加表只许 append。"""
    findings: list[str] = []
    for name, line, table, op in sites:
        if op not in {"put", "append", "delete"}:
            findings.append(f"{name}:{line} 行级操作非闭世界字面量：{op}")
        if "audit" in table.lower():
            findings.append(f"{name}:{line} 出现审计表写面：{table}")
        if table in {"TABLE_BLACKBOX", TABLE_BLOB} and op != "append":
            findings.append(f"{name}:{line} 只追加表 {table} 出现 {op} 路径")
    return findings


def _table_write_calls(tree: ast.Module) -> list[str]:
    """源码里的簿记表写入面（`*.write(...)` 调用与 `RowOp(...)` 构造）——审计面无两者的判据。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "write":
            findings.append(f"L{node.lineno} 调用 write")
        elif isinstance(func, ast.Name) and func.id == "RowOp":
            findings.append(f"L{node.lineno} 构造 RowOp")
    return findings


def _direct_checkpoint_write_sites(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """直连检查点三表的写位点（`RowOp(...)` 构造）：只许出现在唯一行级口模块 `checkpoint.py`。

    表名实参按**源面两形**识别（常量名 `TABLE_CHECKPOINT*` 与字面值 `agent_v2_checkpoint*`）
    ——绕开常量直写字面值同样算直连。
    """
    findings: list[str] = []
    for name, line, table, _op in _row_op_sites(trees):
        if table in _CHECKPOINT_TABLE_MARKS and name != "checkpoint.py":
            findings.append(f"{name}:{line} 直连检查点表 {table}")
    return findings


def _judgement_or_model_findings(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """行 18 的 AST 判据：词表／正则语义判定与模型调用在本块源码里的全部位点。

    判据面＝禁引模块（正则族／模型出口族／框架族）＋正则族根名的调用＋模型面调用名＋
    词表名面。**不判**纯长度边界与空白归一（截断单点合法）。
    """
    findings: list[str] = []
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if _is_forbidden_module(alias.name):
                        findings.append(f"{name}:{node.lineno} 禁引模块 {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if _is_forbidden_module(module):
                    findings.append(f"{name}:{node.lineno} 禁引模块 {module}")
            elif isinstance(node, ast.Call):
                findings.extend(
                    f"{name}:{node.lineno} {finding}" for finding in _call_findings(node)
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if any(mark in node.name.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.name}")
            elif isinstance(node, ast.Name):
                if any(mark in node.id.lower() for mark in _LEXICON_NAME_MARKS):
                    findings.append(f"{name}:{node.lineno} 词表名面 {node.id}")
    return findings


def _is_forbidden_module(module: str) -> bool:
    return module in _FORBIDDEN_IMPORT_MODULES or module.split(".")[0] in _FORBIDDEN_IMPORT_MODULES


def _call_findings(node: ast.Call) -> list[str]:
    """一次调用的判据命中——正则族根名的调用、模型面调用名。"""
    findings: list[str] = []
    target = node.func
    if isinstance(target, ast.Attribute):
        root = target
        while isinstance(root, ast.Attribute):
            root = root.value
        root_name = root.id if isinstance(root, ast.Name) else ""
        if root_name in {"re", "regex"} and target.attr in _REGEX_CALL_NAMES:
            findings.append(f"正则语义判定 {root_name}.{target.attr}")
        if target.attr in _MODEL_CALL_NAMES:
            findings.append(f"模型调用 .{target.attr}")
    elif isinstance(target, ast.Name) and target.id in _MODEL_CALL_NAMES:
        findings.append(f"模型调用 {target.id}")
    return findings


def _import_findings(trees: Sequence[tuple[str, ast.Module]]) -> list[str]:
    """import 白名单（规格 框架与依赖红线④的 AST 降维面）：本块只依赖 `state`／`infra`＋自身。"""
    findings: list[str] = []
    allowed = (
        "appv2.runtimev2.state",
        "appv2.runtimev2.persistence",
        "appv2.infra",
    )
    for name, tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                if not module.startswith("appv2."):
                    continue
                if not module.startswith(allowed):
                    findings.append(f"{name}:{node.lineno} 越界引块 {module}")
    return findings


class _ProbeTables:
    """业务表写入探针（`Tables` 端口替身）：记下每次行级写的表名，非簿记表一律拒收（INV-2）。"""

    def __init__(self) -> None:
        self._inner = MemoryTables()
        self._inner.ensure()
        self.attempted: list[str] = []

    def ensure(self) -> None:
        self._inner.ensure()

    def write(self, ops: Sequence[RowOp]) -> None:
        for op in ops:
            self.attempted.append(op.table)
            if not op.table.startswith(BOOKKEEPING_TABLE_PREFIX):
                raise TableWriteError(f"业务表拒写（INV-2 唯一写面＝簿记表）：{op.table}")
        self._inner.write(ops)

    def get(self, table: str, key: tuple[str, ...]) -> dict[str, Any] | None:
        return self._inner.get(table, key)

    def scan(self, table: str, column: str, value: str) -> list[dict[str, Any]]:
        return self._inner.scan(table, column, value)


class _FailingTables:
    """写失败注入件（行为 14）：记下本次尝试后原样抛出——无部分行、不吞错、不返回哨兵。"""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.attempted: list[RowOp] = []
        self.rows: dict[str, dict[tuple[str, ...], dict[str, Any]]] = {}

    def ensure(self) -> None:
        raise self.error

    def write(self, ops: Sequence[RowOp]) -> None:
        self.attempted.extend(ops)
        raise self.error

    def get(self, table: str, key: tuple[str, ...]) -> dict[str, Any] | None:
        return self.rows.get(table, {}).get(key)

    def scan(self, table: str, column: str, value: str) -> list[dict[str, Any]]:
        return [row for row in self.rows.get(table, {}).values() if row.get(column) == value]


# ---------- 1 三类落盘语义（行为 1） ----------


def test_three_write_semantics(audit_records: list[AuditRecord]) -> None:
    """三类落盘语义各按其规则（更新／幂等／只追加）。"""
    store, tables = _store()

    # ① 运行记录＝按状态机更新（同一 run 一行）
    store.save(_run("run-a"))
    store.save(_run("run-a", status="waiting_ask", question="渤海某井 2026 年日产油量？（改问）"))
    store.save(
        _run("run-a", status="running", question="渤海某井 2026 年日产油量？（改问）")
    )
    rows = tables.scan(TABLE_RUN, "run_id", "run-a")
    assert len(rows) == 1, "同一 run 出现多行（运行记录＝更新，非追加）"
    current = store.run("run-a")
    assert current is not None and current.status == "running"
    assert current.question == "渤海某井 2026 年日产油量？（改问）"

    # ② 步记录＝同键幂等（重复落盘不产生第二行；内容等价才允许覆盖）
    store.save(_step("run-a", 1))
    store.save(_step("run-a", 1))
    assert len(store.steps("run-a")) == 1
    assert len(tables.scan(TABLE_STEP, "run_id", "run-a")) == 1
    with pytest.raises(StepConflictError):
        store.save(_step("run-a", 1, title="换了标题"))  # 不等价 → 不许覆盖
    with pytest.raises(ValueError):
        store.save(_step("run-a", 2, step="think"))  # step 越界（闭世界＝state.STEP_KINDS）
    with pytest.raises(ValueError):
        store.save(_step("run-a", 2, status="skipped"))  # status 越界（闭世界三值）

    # ③ 黑匣子与审计＝只追加（既成行不得改写、不得删除）
    store.save(_blackbox("run-a", {"run_id": "run-a", "status": "completed"}))
    with pytest.raises(AlreadyArchivedError):
        store.save(_blackbox("run-a", {"run_id": "run-a", "status": "failed"}))
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1
    audit(_audit("run-a"))
    audit(_audit("run-a", action=AUDIT_ACTION_RUN_COMPLETED))
    assert [record.action for record in audit_records] == [
        AUDIT_ACTION_RUN_CREATED,
        AUDIT_ACTION_RUN_COMPLETED,
    ], "审计两写必须两条（只追加，非覆盖）"


# ---------- 2 只追加无改写路径（AST＋行为双证；行为 1③／行为 4） ----------


def test_append_only_no_mutation_path(audit_records: list[AuditRecord]) -> None:
    """黑匣子与审计行无改写／删除路径（AST＋行为双证）。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))
    first = {
        "run_id": "run-a",
        "status": "completed",
        "dialogue": [{"role": "user", "content": "原话", "origin": "user_verbatim"}],
    }
    store.save(_blackbox("run-a", first))
    with pytest.raises(AlreadyArchivedError):
        store.save(_blackbox("run-a", {"run_id": "run-a", "status": "failed"}))
    stored = store.blackbox("run-a")
    assert stored is not None and stored.record == first, "二次归档改动了首写行"
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1

    # 行为证①：读口返回副本——改返回值不改库内行
    view = store.blackbox("run-a")
    assert view is not None
    view.record["status"] = "改写的"
    assert store.blackbox("run-a").record == first

    # 行为证②：只追加表只许 append——覆盖（put）与删除（delete）都被拒
    assert APPEND_ONLY_TABLES == {TABLE_BLACKBOX, TABLE_BLOB}
    for bad_op in ("put", "delete"):
        with pytest.raises(TableWriteError):
            tables.write([RowOp(TABLE_BLACKBOX, ("run-a",), {"run_id": "run-a"}, bad_op)])
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1

    # 行为证③：审计只追加（本块无审计表写面；两次调用两条、首条不被改写）
    audit(_audit("run-a"))
    audit(_audit("run-a", action=AUDIT_ACTION_REFUSED))
    assert len(audit_records) == 2
    assert audit_records[0].action == AUDIT_ACTION_RUN_CREATED
    assert audit_records[0].facts == "问答受理"
    assert all("audit" not in table.lower() for table in TABLES), "簿记表清单出现审计表"

    # AST 证：写位点全经行级口且操作闭世界；黑匣子／载体只见 append；无审计写面
    sites = _row_op_sites(_source_trees())
    assert sites, "未扫到 RowOp 写位点——探测器失效（非缺陷判定）"
    assert _row_op_violations(sites) == []

    # 审计路径：写面只有注入的写口——审计模块零表写入调用（无 `write`／`RowOp` 位点）
    audit_tree = ast.parse((_PERSISTENCE_DIR / "audit.py").read_text(encoding="utf-8"))
    assert _table_write_calls(audit_tree) == [], "审计模块出现表写入路径"
    forged_audit = ast.parse(
        "tables.write([RowOp('agent_v2_audit', ('x',), {}, 'append')])"  # type: ignore[name-defined]
    )
    assert _table_write_calls(forged_audit) != [], "探测器空转"

    # 探测器非空转（伪造两形各命中）
    forged = [
        ("probe", ast.parse("RowOp(TABLE_BLACKBOX, ('x',), {}, 'put')")),
        ("probe", ast.parse("RowOp(TABLE_AUDIT, ('x',), {}, 'append')")),
        ("probe", ast.parse("RowOp(TABLE_STEP, ('x',), {}, dynamic_op)")),
    ]
    findings = _row_op_violations(_row_op_sites(forged))
    assert any("只追加表" in finding for finding in findings)
    assert any("审计表写面" in finding for finding in findings)
    assert any("闭世界字面量" in finding for finding in findings)


# ---------- 3 状态机把守（行为 2） ----------


def test_status_machine_guarded() -> None:
    """`status` 取值闭世界；`waiting_ask→running` 唯一合法方向。"""
    store, _ = _store()
    # 闭世界引面不漂：本块把守用的就是 state 的四值（规格：本块不复述取值）
    assert RUN_STATUS_KINDS == _SPEC_RUN_STATUSES
    assert STEP_KINDS == _SPEC_STEP_KINDS

    store.save(_run("run-a"))  # 创建（running）
    store.save(_run("run-a", status="waiting_ask"))  # 挂起
    store.save(_run("run-a", status="running"))  # 恢复——唯一合法「恢复」迁移方向
    current = store.run("run-a")
    assert current is not None and current.status == "running"
    _, other_tables = _store()
    assert other_tables.scan(TABLE_RUN, "run_id", "run-a") == [], "缺省件串扰（跨 store 泄漏）"

    # 反向／非 `waiting_ask` 出发的「恢复」→ 抛错（先例 recon/J R-J-17「running→running 也拒」）
    with pytest.raises(StatusTransitionError):
        store.save(_run("run-a", status="running"))
    store.save(_run("run-a", status="completed"))  # 终态收口（该不该迁移的决策归 orchestration）
    with pytest.raises(StatusTransitionError):
        store.save(_run("run-a", status="running"))  # 终态不可复活

    # 取值闭世界越界 → 抛错（fail-closed：不静默丢弃、不返回哨兵）
    with pytest.raises(ValueError):
        store.save(_run("run-b", status="paused"))
    assert store.run("run-b") is None


# ---------- 4 恢复可重放（行为 3） ----------


def test_load_replayable_idempotent() -> None:
    """两次 `load` 等价且无副作用。"""
    store, tables = _store()
    store.ensure_tables()
    store.ensure_tables()  # 幂等建表：二跑不炸、表清单不变
    store.save(_run("run-a", status="waiting_ask"))
    state = RunState(
        run_id="run-a",
        question="渤海某井 2026 年日产油量？",
        actor="laowang",
        status="waiting_ask",
        messages=[{"role": "user", "content": "渤海某井 2026 年日产油量？"}],
        rounds=2,
        discover_used=1,
    )
    put_checkpoint_rows(
        [
            CheckpointRow(
                thread_id="run-a",
                ns=DEFAULT_NS,
                checkpoint_id="0001",
                parent_checkpoint_id=None,
                kind=CHECKPOINT_KIND_STATE,
                checkpoint=encode_state(state),
                metadata=encode_metadata({"messages": "1"}),
            )
        ],
        tables=tables,
    )
    before = len(tables.writes)
    first = store.load("run-a")
    second = store.load("run-a")
    assert first == second, "两次 load 不等价"
    assert asdict(first) == asdict(state), "读回与落盘快照逐字段不等"
    assert len(tables.writes) == before, "load 产生副作用（写盘）"

    # 无快照行＝按 run 行身份面如实装配（不抛错、不伪造历史）；run 行不存在 → 抛错
    store.save(_run("run-b", status="running", question="另一问"))
    fresh = store.load("run-b")
    assert (fresh.run_id, fresh.status, fresh.question) == ("run-b", "running", "另一问")
    assert fresh.messages == [] and fresh.dialogue == []
    with pytest.raises(RunNotFoundError):
        store.load("run-unknown")


# ---------- 5 黑匣子首写为准（行为 4） ----------


def test_blackbox_first_write_wins() -> None:
    """黑匣子重复归档不覆盖＋跳过记账在场。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))
    archived = _blackbox("run-a", {"run_id": "run-a", "status": "completed", "answer": "首写答案"})
    store.save(archived)

    # 跳过记账的落点＝该次归档调用的错误面：异常即机读信号（携首写行键与首写时间）
    notices: list[dict[str, Any]] = []
    with pytest.raises(AlreadyArchivedError) as raised:
        try:
            store.save(_blackbox("run-a", {"run_id": "run-a", "status": "failed"}))
        except AlreadyArchivedError as error:
            notices.append(
                {
                    "type": "blackbox_skipped",
                    "run_id": error.run_id,
                    "archived_at": error.archived_at.isoformat(),
                }
            )
            raise
    assert raised.value.run_id == "run-a"
    assert raised.value.archived_at == _T0
    assert notices == [
        {"type": "blackbox_skipped", "run_id": "run-a", "archived_at": "2026-10-16T09:00:00"}
    ], "调用方一次跳过记账缺席"

    # 二次归档后 blackbox(run_id) 内容与首次逐字相同
    stored = store.blackbox("run-a")
    assert stored is not None
    assert stored.record == archived.record
    assert stored.created_at == archived.created_at
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1


# ---------- 9 步记录 payload 原样保真（行为 8） ----------


def test_step_payload_faithful() -> None:
    """步记录 payload 原样保真（空结构与缺失可区分）。"""
    store, _ = _store()
    store.save(_run("run-a"))
    store.save(_step("run-a", 1, payload={}))  # 空结构
    store.save(_step("run-a", 2, payload=None))  # 无 payload
    nested = {"rows": [{"a": 1}], "text": "原样", "n": 0, "flag": False}
    store.save(_step("run-a", 3, payload=nested))
    store.save(_step("run-a", 0, payload={"seq": "先落的"}))

    seqs = [record.seq for record in store.steps("run-a")]
    assert seqs == [0, 1, 2, 3], "读回未按 seq 升序"
    by_seq = {record.seq: record for record in store.steps("run-a")}
    assert by_seq[1].payload == {}, "空 `{}` 被归一为缺失"
    assert by_seq[1].payload is not None, "空结构与缺失不可区分"
    assert by_seq[2].payload is None
    assert by_seq[3].payload == nested, "payload 被裁剪或改写"

    # `manifest` 同款原样（`{}` 与缺失可区分）
    store.save(_step("run-a", 4, manifest={}))
    store.save(_step("run-a", 5, manifest=None))
    by_seq = {record.seq: record for record in store.steps("run-a")}
    assert by_seq[4].manifest == {} and by_seq[5].manifest is None
    assert len(store.steps("run-a")) == 6, "同键重复落盘产生了第二行"


# ---------- 10 核验对账字段可机检（pin-12 落盘面） ----------


def test_verify_fields_readable_in_step() -> None:
    """核验对账机读字段可被读面机检（`pin-12` 落盘面）。"""
    store, _ = _store()
    store.save(_run("run-a"))
    payload = {
        "supported": 5,
        "rewritten": 1,
        "split": 0,
        "cited": 6,
        "attribution": True,
        "ok": False,
        "gaps": ["第 3 行无据"],
        "delivered_rows": 12,  # 字段面真源 specs/verification.md 行为 11
        "obs_rows": 20,
    }
    store.save(_step("run-a", 2, step="verify", payload=payload))
    read = store.steps("run-a")[0]
    assert read.step == "verify" and read.payload is not None
    machine = {key: read.payload[key] for key in ("delivered_rows", "obs_rows")}
    assert machine == {"delivered_rows": 12, "obs_rows": 20}, "机读字段读面取不到（被裁／被串化）"
    assert all(isinstance(value, int) for value in machine.values())
    assert read.payload["obs_rows"] - read.payload["delivered_rows"] == 8  # 差额可算（记账面）
    assert read.payload == payload, "整包逐字段不等（未原样保真）"


# ---------- 11 run_id 全盖章（pin-28 落盘面） ----------


def test_run_id_stamped_across_records(audit_records: list[AuditRecord]) -> None:
    """`run_id` 全盖章：四类记录可按 run 聚合对账。"""
    store, _ = _store()
    ledger_run_ids = {"run-a", "run-b"}
    for run_id in sorted(ledger_run_ids):
        store.save(_run(run_id, status="completed"))
        store.save(_step(run_id, 1))
        store.save(_blackbox(run_id, {"run_id": run_id, "status": "completed"}))
        audit(_audit(run_id))

    # 四类记录的字段面都携 `run_id`
    for shape in (RunRecord, StepRecord, BlackBox, AuditRecord):
        assert "run_id" in {field.name for field in fields(shape)}, shape.__name__

    # 按 run 聚合：无遗漏、无外键错挂
    for run_id in sorted(ledger_run_ids):
        run_row = store.run(run_id)
        box = store.blackbox(run_id)
        assert run_row is not None and box is not None
        aggregated = (
            {run_row.run_id}
            | {record.run_id for record in store.steps(run_id)}
            | {box.run_id}
            | {record.run_id for record in audit_records if record.run_id == run_id}
        )
        assert aggregated == {run_id}

    # 逐题账集合与落盘记录等值（对账数据源口径：eval/results/Q15-对账报告.md）
    assert {record.run_id for record in audit_records} == ledger_run_ids
    archived_run_ids = set()
    for run_id in sorted(ledger_run_ids):
        box = store.blackbox(run_id)
        assert box is not None
        archived_run_ids.add(box.run_id)
    assert archived_run_ids == ledger_run_ids
    assert {record.run_id for record in store.steps("run-a")} == {"run-a"}, "他 run 的行错挂"

    # 黑匣子记录自带 run_id 与行键不一致 → 抛错（无外键错挂的写入面把守）
    store.save(_run("run-c"))
    with pytest.raises(PersistenceError, match="错挂"):
        store.save(_blackbox("run-c", {"run_id": "run-x", "status": "completed"}))


# ---------- 12 引用载体往返与坏 handle（行为 10） ----------


def test_material_ref_roundtrip_and_bad_ref() -> None:
    """引用载体往返逐字节相同；坏 `handle` 抛错。"""
    store, tables = _store()
    blob = bytes(range(256))  # 含 0x00／0xff 的二进制面（逐字节判据）
    ref = store.put_ref(blob)
    assert isinstance(ref, BlobRef)
    assert ref.bytes == len(blob)
    assert ref.sha256 == hashlib.sha256(blob).hexdigest()
    assert store.read_ref(ref.handle) == blob, "往返不逐字节相同"
    assert store.put_ref(blob).handle == ref.handle, "同原文未定同一 handle（可寻址）"

    # `execution.MaterialRef.handle` 同源同值：窗口侧材料条目直接喂 `read_ref` 取回原文
    material_ref = {"handle": ref.handle, "summary": "某井日产油量表", "row_count": 256}
    assert store.read_ref(material_ref["handle"]) == blob
    stored_row = tables.get(TABLE_BLOB, (ref.handle,))
    assert stored_row is not None
    assert stored_row["blob"] == blob and stored_row["sha256"] == ref.sha256

    # 坏 handle 抛错（fail-closed：不猜、不返回哨兵）
    bad_handles = [
        "",
        "sha256:" + ref.sha256,
        ref.handle[:-1],
        "blob-" + "0" * 64,
        "blob-不是十六进制",
    ]
    for bad in bad_handles:
        with pytest.raises(UnknownHandleError):
            store.read_ref(bad)


# ---------- 15 旧检查点／旧黑匣子如实读入（pin-30 回放面） ----------


def test_legacy_read_honest() -> None:
    """旧检查点／旧黑匣子如实读入（对话通道空显）。"""
    store, tables = _store()
    store.save(_run("run-v1", status="completed"))

    # ① 旧黑匣子**回放**：不抛错；旧 run 对话通道如实空显（不伪造补写）
    store.save(_blackbox("run-v1", _V1_BLACKBOX_RECORD))
    stored = store.blackbox("run-v1")
    assert stored is not None
    channels = replay_channels(stored.record)  # 不抛错
    assert channels["dialogue"] == [], "旧条目被伪造补写（对话通道应如实空显）"
    assert channels["messages"] == _V1_BLACKBOX_RECORD["messages"]
    assert channels["answer"] == "旧答案"
    assert set(channels) <= REPLAY_CHANNELS
    assert stored.record["dialogue"] == _V1_BLACKBOX_RECORD["dialogue"], "落盘原文被改写"
    # 缺键／非列表形不炸（如实空显为「无通道」）
    assert "dialogue" not in replay_channels({"run_id": "run-v1"})
    assert replay_channels({"run_id": "run-v1", "dialogue": "旧串"})["dialogue"] == []
    # v2 条目如实承接（空显只针对旧条目）
    v2_record = {
        "run_id": "run-v2",
        "dialogue": [{"role": "user", "content": "新问", "origin": "user_verbatim"}],
    }
    assert replay_channels(v2_record)["dialogue"] == v2_record["dialogue"]

    # ② 旧检查点读入：不抛错、`schema_version` 取读入态、对话通道空显
    put_checkpoint_rows(
        [
            CheckpointRow(
                thread_id="run-v1",
                ns=DEFAULT_NS,
                checkpoint_id="0001",
                parent_checkpoint_id=None,
                kind=CHECKPOINT_KIND_STATE,
                checkpoint=json.dumps(_V1_STATE_PAYLOAD, ensure_ascii=False).encode("utf-8"),
                metadata=b"not-json",
            )
        ],
        tables=tables,
    )
    legacy = store.load("run-v1")  # 不抛错
    assert legacy.schema_version == 1, "schema_version 未取读入态（伪造历史）"
    assert legacy.dialogue == [], "旧对话条目被补标收编"
    assert legacy.answer == "旧答案"
    assert legacy.budget.rounds == 3  # v1 裸 dict 按七键转 Budget
    assert legacy.rounds == 1
    assert set(DIALOGUE_ORIGINS) == {"user_verbatim", "assistant_final", "clarify_approval_replay"}
    assert len(BLACKBOX_RECORD_KEYS) == 20, "蒸馏白名单条数漂移（真源 recon/J R-J-02）"
    assert _SPEC_STEP_STATUSES == {"ok", "failed", "refused"}


# ---------- 票面验收判据：骨架与公开面齐备（卡面签名；非规格表行） ----------


def test_public_surface_complete() -> None:
    """骨架与公开面齐备：「`RunStore`／五张行投影／检查点三表行级口／`AuditRecord`」（票面验收判据）。

    签名以 `specs/modules.md` `## persistence` 卡为准（规格接口定义节同源）；八类形状的
    `frozen+slots` 是本块定型（规格未明写——与 `state` 同款：既成行投影不可原地改，接只追加纪律）。
    """
    for method in (
        "save",
        "load",
        "run",
        "steps",
        "blackbox",
        "put_ref",
        "read_ref",
        "ensure_tables",
    ):
        assert callable(getattr(RunStore, method)), f"RunStore 缺方法 {method}"
    assert list(signature(RunStore.save).parameters)[1:] == ["record"]
    assert list(signature(RunStore.load).parameters)[1:] == ["run_id"]
    assert list(signature(RunStore.run).parameters)[1:] == ["run_id"]
    assert list(signature(RunStore.steps).parameters)[1:] == ["run_id"]
    assert list(signature(RunStore.blackbox).parameters)[1:] == ["run_id"]
    assert list(signature(RunStore.put_ref).parameters)[1:] == ["blob"]
    assert list(signature(RunStore.read_ref).parameters)[1:] == ["handle"]
    assert list(signature(RunStore.ensure_tables).parameters)[1:] == []

    # 检查点三表五个框架无关行级口（编排块 saver 组合它们、不直连表）
    assert "rows" in signature(put_checkpoint_rows).parameters
    for function in (checkpoint_rows, delete_thread):
        assert "thread_id" in signature(function).parameters, function.__name__
    for function in (checkpoint_blobs, checkpoint_writes):
        assert "thread_id" in signature(function).parameters, function.__name__
        assert "checkpoint_id" in signature(function).parameters, function.__name__
    assert callable(audit)

    # 八类形状在场（规格 接口定义节）
    instances = (
        _run(),
        _step(),
        _blackbox("run-a"),
        BlobRef(handle="blob-" + "0" * 64, bytes=1, sha256="0" * 64),
        CheckpointRow("t", DEFAULT_NS, "1", None, CHECKPOINT_KIND_STATE, b"", b""),
        CheckpointBlobRow("t", DEFAULT_NS, "ch", "1", "json", b""),
        CheckpointWriteRow("t", DEFAULT_NS, "1", "task", 0, "ch", "json", b""),
        _audit(),
    )
    assert {type(instance).__name__ for instance in instances} == {
        "RunRecord",
        "StepRecord",
        "BlackBox",
        "BlobRef",
        "CheckpointRow",
        "CheckpointBlobRow",
        "CheckpointWriteRow",
        "AuditRecord",
    }
    for instance in instances:
        shape = type(instance)
        assert shape.__dataclass_params__.frozen is True, shape.__name__
        assert not hasattr(instance, "__dict__"), f"{shape.__name__} 缺 slots"
        with pytest.raises(FrozenInstanceError):
            setattr(instance, fields(shape)[0].name, None)


def test_checkpoint_ports_roundtrip() -> None:
    """检查点三表五个行级口的往返自证（**票面骨架面**；行 13「写操作全经五口」的守门断言归 -b）。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))
    put_checkpoint_rows(
        [
            CheckpointRow(
                thread_id="run-a",
                ns=DEFAULT_NS,
                checkpoint_id="0002",
                parent_checkpoint_id="0001",
                kind=CHECKPOINT_KIND_STATE,
                checkpoint=encode_state(RunState(run_id="run-a")),
                metadata=encode_metadata({"messages": "2"}),
            ),
            CheckpointBlobRow("run-a", DEFAULT_NS, "messages", "2", "json", b"blob-2"),
            CheckpointWriteRow(
                "run-a", DEFAULT_NS, "0002", "task-1", 0, "messages", "json", b"write-1"
            ),
        ],
        tables=tables,
    )
    stored = checkpoint_rows("run-a", tables=tables)
    assert [(row.checkpoint_id, row.parent_checkpoint_id, row.kind) for row in stored] == [
        ("0002", "0001", CHECKPOINT_KIND_STATE)
    ]
    blobs = checkpoint_blobs("run-a", "0002", tables=tables)
    assert [(row.channel, row.version, row.blob) for row in blobs] == [
        ("messages", "2", b"blob-2")
    ]
    writes = checkpoint_writes("run-a", "0002", tables=tables)
    assert [(row.task_id, row.idx, row.blob) for row in writes] == [("task-1", 0, b"write-1")]

    # 检查点行不存在 → 抛错（fail-closed：不留无声缺口）；未知线程可读为空
    with pytest.raises(PersistenceError):
        checkpoint_blobs("run-a", "9999", tables=tables)
    assert checkpoint_rows("run-unknown", tables=tables) == []

    # 删线程＝只清检查点三表（簿记与黑匣子不随线程删——recon/J R-J-45）
    store.save(_step("run-a", 1))
    store.save(_blackbox("run-a", {"run_id": "run-a", "status": "completed"}))
    delete_thread("run-a", tables=tables)
    assert checkpoint_rows("run-a", tables=tables) == []
    assert checkpoint_writes("run-a", "0002", tables=tables) == []
    with pytest.raises(PersistenceError):
        checkpoint_blobs("run-a", "0002", tables=tables)
    assert store.run("run-a") is not None and len(store.steps("run-a")) == 1
    assert store.blackbox("run-a") is not None


# ══════════════════════════════════════════════════════════════════════════════════
# RT-W2-01b 票面（`specs/persistence.md`「验收测试」表第 6、7、8、13、14、16、17、18、19、20 行）
# ══════════════════════════════════════════════════════════════════════════════════


# ---------- 6 审计四要素齐备（行为 5；Owner 裁决 walk/16 §七 Q-C） ----------


def test_audit_four_elements_required(audit_records: list[AuditRecord]) -> None:
    """审计四要素缺项判失败。"""
    audit(_audit("run-a"))  # 四要素齐备 → 过
    assert len(audit_records) == 1

    # 四要素＝主体（`who`；`scope` 是主体的范围细化）／意图（`action`；`authorization` 是其授权
    # 依据、无则空串）／事实（`facts`）／结果（`evidence`）；`run_id` 是四类记录同源聚合的范围键。
    assert AUDIT_REQUIRED_FIELDS == ("run_id", "who", "scope", "action", "facts", "evidence")
    missing_cases: dict[str, dict[str, Any]] = {
        "run_id": {"run_id": ""},
        "who": {"who": ""},
        "scope": {"scope": ""},
        "action": {"action": ""},
        "facts": {"facts": ""},
        "evidence": {"evidence": {}},
    }
    for field_name, override in missing_cases.items():
        with pytest.raises(AuditElementMissingError) as raised:
            audit(replace(_audit("run-a"), **override))
        assert raised.value.missing == (field_name,), f"{field_name} 未落缺项分支"
        assert raised.value.run_id == override.get("run_id", "run-a")
    assert len(audit_records) == 1, "缺项记录被落库（静默吞错——缺项判失败须一行不落）"

    # `authorization` 无则空串＝不算缺项（并入意图、不另立要素）；`evidence` 有内容即在场
    audit(replace(_audit("run-a"), authorization="", evidence={"notice": "无审批单"}))
    assert audit_records[-1].authorization == ""
    assert len(audit_records) == 2


# ---------- 7 审计 action 七值闭世界（行为 6；真源 recon/J R-J-05） ----------


def test_audit_action_closed_world(audit_records: list[AuditRecord]) -> None:
    """审计 action 七值闭世界＋`agent_v2.` 前缀。"""
    # 计数唯一口径＝action 七值（分组说法不产生第二个数字）
    assert AUDIT_ACTIONS == _SPEC_AUDIT_ACTIONS
    assert len(AUDIT_ACTIONS) == 7
    assert all(action.startswith(AUDIT_ACTION_PREFIX) for action in AUDIT_ACTIONS)

    for action in sorted(AUDIT_ACTIONS):
        audit(_audit("run-a", action=action))
    assert [record.action for record in audit_records] == sorted(AUDIT_ACTIONS)

    # 越界 → 抛错、一行不落（前缀缺失／未知值／近似前缀／另一命名空间）
    for bad in (
        "run_created",
        "agent_v2.",
        "agent_v2.unknown",
        "agent_v2x.run_created",
        "chat.ask.ban_exempt",
        "agent_v2.RUN_CREATED",
    ):
        with pytest.raises(AuditActionOutOfWorldError) as raised:
            audit(_audit("run-a", action=bad))
        assert raised.value.action == bad
    assert len(audit_records) == 7, "越界 action 被落库"

    # 空串落缺项分支（四要素守门在先——action 是要素之一）
    with pytest.raises(AuditElementMissingError):
        audit(_audit("run-a", action=""))


# ---------- 8 业务表零写（INV-2；行为 7） ----------


def test_no_business_table_write(audit_records: list[AuditRecord]) -> None:
    """业务表零写（探针注入判失败）。"""
    probe = _ProbeTables()
    store = RunStore(probe)

    # 全生命周期（四类记录＋引用载体＋检查点三表口）的每一次写都经探针
    store.save(_run("run-a", status="completed"))
    store.save(_step("run-a", 1))
    store.save(_blackbox("run-a", {"run_id": "run-a", "status": "completed"}))
    store.put_ref("大结果原文".encode())
    put_checkpoint_rows(
        [
            CheckpointRow(
                "run-a", DEFAULT_NS, "0001", None, CHECKPOINT_KIND_STATE, b"{}", b"{}"
            )
        ],
        tables=probe,
    )
    delete_thread("run-a", tables=probe)
    audit(_audit("run-a"))
    assert probe.attempted, "探针未接到任何写入（探测器空转）"
    assert all(table.startswith(BOOKKEEPING_TABLE_PREFIX) for table in probe.attempted)
    assert set(probe.attempted) <= set(TABLES)

    # 表名清单与簿记前缀一致（唯一写面＝`agent_v2_*` 簿记表）
    assert TABLES == (
        TABLE_RUN,
        TABLE_STEP,
        TABLE_BLACKBOX,
        TABLE_BLOB,
        TABLE_CHECKPOINT,
        TABLE_CHECKPOINT_BLOB,
        TABLE_CHECKPOINT_WRITE,
    )
    assert all(table.startswith(BOOKKEEPING_TABLE_PREFIX) for table in TABLES)

    # 探针注入：任何对业务表的写入尝试被判失败（含近似前缀的伪装名）
    for business in ("petro_well", "public.wells", "oilfield_production", "agent_v3_run"):
        with pytest.raises(TableWriteError):
            probe.write([RowOp(business, ("w-1",), {"run_id": "run-a"}, "put")])
    assert probe.scan(TABLE_RUN, "run_id", "run-a") != [], "探针内层件失灵（先前的合法写未落）"

    # 缺省件同款把守（INV-2 在端口层，不靠调用方自觉）
    inner = MemoryTables()
    inner.ensure()
    for business in ("petro_well", "agent_v3_run"):
        with pytest.raises(TableWriteError, match="非簿记表"):
            inner.write([RowOp(business, ("w-1",), {"well_id": "w-1"}, "put")])
    assert inner.scan(TABLE_STEP, "run_id", "run-a") == [], "业务表写入漏进了簿记面"


# ---------- 13 检查点三表写操作只经五个行级口（接口定义 + 行 13） ----------


def test_saver_writes_only_via_port_functions() -> None:
    """检查点三表的写操作全经五个行级口（编排块 saver 不直连表）。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))

    # 行为证①：saver 组合路径——写只经 `put_checkpoint_rows`，三表行如实落地、读口可见
    put_checkpoint_rows(
        [
            CheckpointRow(
                "run-a",
                DEFAULT_NS,
                "0001",
                None,
                CHECKPOINT_KIND_STATE,
                encode_state(RunState(run_id="run-a")),
                encode_metadata({"messages": "1"}),
            ),
            CheckpointBlobRow("run-a", DEFAULT_NS, "messages", "1", "json", b"blob-1"),
            CheckpointWriteRow("run-a", DEFAULT_NS, "0001", "task-1", 0, "messages", "json", b"w1"),
        ],
        tables=tables,
    )
    assert [row.checkpoint_id for row in checkpoint_rows("run-a", tables=tables)] == ["0001"]
    assert [row.blob for row in checkpoint_blobs("run-a", "0001", tables=tables)] == [b"blob-1"]
    assert [row.blob for row in checkpoint_writes("run-a", "0001", tables=tables)] == [b"w1"]
    written = [table for table, _key, _op in tables.writes]
    assert set(written) <= set(TABLES)
    assert CHECKPOINT_TABLES == {TABLE_CHECKPOINT, TABLE_CHECKPOINT_BLOB, TABLE_CHECKPOINT_WRITE}

    # 行为证②：本块其它写面不碰检查点三表（`RunStore.save` 落 run／步／黑匣子／引用载体）
    before = len(tables.writes)
    store.save(_step("run-a", 1))
    store.save(_blackbox("run-a", {"run_id": "run-a", "status": "completed"}))
    store.put_ref("原文".encode())
    assert all(table not in CHECKPOINT_TABLES for table, _key, _op in tables.writes[before:])

    # 行为证③：四读口零写（读不动表）；删线程＝五口里的 delete 口（只清检查点三表）
    before = len(tables.writes)
    checkpoint_rows("run-a", tables=tables)
    checkpoint_blobs("run-a", "0001", tables=tables)
    checkpoint_writes("run-a", "0001", tables=tables)
    assert len(tables.writes) == before, "读口产生写（读面不净）"
    delete_thread("run-a", tables=tables)
    assert checkpoint_rows("run-a", tables=tables) == []
    assert store.run("run-a") is not None, "删线程误清簿记面（R-J-45）"

    # AST 证：检查点三表的 `RowOp` 构造位点只在唯一行级口模块（saver 不直连表的本块面）
    assert _direct_checkpoint_write_sites(_source_trees()) == []
    forged = [("store.py", ast.parse("RowOp(TABLE_CHECKPOINT, ('t',), {}, 'put')"))]
    assert _direct_checkpoint_write_sites(forged) != [], "探测器空转"


# ---------- 14 黑匣子键白名单闭世界（行为 11；真源 recon/J R-J-02／R-J-03／R-J-50） ----------


def test_blackbox_keys_closed_world() -> None:
    """黑匣子键白名单闭世界（越界键判失败）。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))
    # 白名单＝蒸馏二十键（顺序即记录键插入顺序）＋身份面四键；越界判据＝键集差
    assert len(BLACKBOX_RECORD_KEYS) == 20
    assert BLACKBOX_ALLOWED_KEYS == set(BLACKBOX_RECORD_KEYS) | set(BLACKBOX_IDENTITY_KEYS)
    assert set(BLACKBOX_IDENTITY_KEYS) == {"run_id", "question", "status", "error"}

    # 全白名单键 → 过（白名单内不设额外限制：值面归各相位，本块只保真）
    full_record: dict[str, Any] = dict.fromkeys(sorted(BLACKBOX_ALLOWED_KEYS))
    full_record["run_id"] = "run-a"
    full_record["status"] = "completed"
    store.save(_blackbox("run-a", full_record))
    stored = store.blackbox("run-a")
    assert stored is not None and set(stored.record) == set(BLACKBOX_ALLOWED_KEYS)

    # 越界键判失败：未入列键不进黑匣子（含已取消字段名与近似名）
    store.save(_run("run-b", status="completed"))
    for bad_key in ("consecutive_asks", "messages_v2", "understanding", "question_group_x"):
        with pytest.raises(BlackBoxKeyOutOfWorldError) as raised:
            store.save(_blackbox("run-b", {"run_id": "run-b", bad_key: "越界"}))
        assert raised.value.unknown == (bad_key,)
        assert raised.value.run_id == "run-b"
    assert tables.scan(TABLE_BLACKBOX, "run_id", "run-b") == [], "越界键被落库（白名单外偷偷进）"
    assert store.blackbox("run-b") is None

    # 越界不引入改写路径：首写行逐字不变、仍为一行
    assert store.blackbox("run-a").record == full_record
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1


# ---------- 16 截断必带可见标记（行为 13；真源 recon/J R-J-06／R-J-60／R-J-62／R-J-63） ----------


def test_truncation_visible(audit_records: list[AuditRecord]) -> None:
    """截断必带可见标记。"""
    # ① 审计 `facts`：空白折叠（R-J-63）＋超长截断可见、长度受控 ≤ SUMMARY_LIMIT=120（R-J-06）
    long_facts = "核对" * 200
    audit(replace(_audit("run-a"), facts=long_facts))
    truncated = audit_records[-1].facts
    assert truncated.endswith(TRUNCATION_MARK), "超长审计摘要未带截断标记（静默截断）"
    assert len(truncated) <= SUMMARY_LIMIT, "审计摘要长度不受控"
    assert truncated[:-1] == long_facts[: SUMMARY_LIMIT - 1], "截断保留了非原文内容"
    audit(replace(_audit("run-a"), facts="第一行\n第二行\t第三行"))
    assert audit_records[-1].facts == "第一行 第二行 第三行"
    assert summarize("短摘要") == "短摘要"

    # ② 黑匣子单行摘要：换行替换 `" ⏎ "`、按替换后字符数计（R-J-60）＋截断可见 ≤ 96
    lines = head("行一\n行二\n" + "长" * 300)
    assert lines.startswith("行一" + BLACKBOX_NEWLINE_MARK + "行二" + BLACKBOX_NEWLINE_MARK)
    assert lines.endswith(TRUNCATION_MARK)
    assert len(lines) <= BLACKBOX_LINE_LIMIT
    assert head("单行短值") == "单行短值"

    # ③ 转写分面截断（R-J-62）：title 30（process_notes）／60（steps）、digest 80、source 40
    assert dict(FACET_LIMITS) == _SPEC_FACET_LIMITS
    for facet, limit in _SPEC_FACET_LIMITS.items():
        text = "字" * 500
        clipped = facet_head(facet, text)
        assert len(clipped) <= limit, f"{facet} 未按分面长度截断"
        assert clipped.endswith(TRUNCATION_MARK)
        assert clipped[:-1] == text[: limit - 1]
    assert facet_head("未在册分面", "字" * 500) == facet_head(
        "content", "字" * 500
    )  # 未在册＝通用值


# ---------- 17 写失败 fail-closed（行为 14；A-P7a-37） ----------


def test_write_failure_fail_closed() -> None:
    """写失败 fail-closed：抛错且无部分行、无静默缺口。"""
    failure = RuntimeError("存储不可用：写失败")
    failing = _FailingTables(failure)
    store = RunStore(failing)

    # ① 写失败上抛（原样上抛、不吞错、不换形、不返回哨兵）
    with pytest.raises(RuntimeError) as raised:
        store.save(_run("run-a"))
    assert raised.value is failure
    assert len(failing.attempted) == 1, "写失败未如实上抛（重试／吞错）"
    assert failing.rows == {}, "写失败留下部分行"
    # 步／黑匣子写入先经 run 在场把守（缺行即抛错）——写面任一路都不静默、不落半成品
    with pytest.raises(RunNotFoundError):
        store.save(_step("run-a", 1))
    for attempt in (
        lambda: store.put_ref("原文".encode()),
        lambda: store.ensure_tables(),
        lambda: put_checkpoint_rows(
            [CheckpointRow("t", DEFAULT_NS, "1", None, CHECKPOINT_KIND_STATE, b"", b"")],
            tables=failing,
        ),
    ):
        with pytest.raises(RuntimeError):
            attempt()

    # ② 无静默缺口：读面如实（缺行＝None／抛错），不留无声的半成品
    assert store.run("run-a") is None
    with pytest.raises(RunNotFoundError):
        store.load("run-a")
    assert failing.scan(TABLE_RUN, "run_id", "run-a") == []

    # ③ 批量原子：同批次后一行非法 → 前一行不落（无部分行、失败批次不入写账）
    _, tables = _store()
    good = RowOp(TABLE_STEP, ("run-a", "1"), {"run_id": "run-a", "seq": 1}, "put")
    with pytest.raises(TableWriteError):
        tables.write([good, RowOp("petro_well", ("w-1",), {"well_id": "w-1"}, "put")])
    assert tables.scan(TABLE_STEP, "run_id", "run-a") == [], "批次半写（前一行已落）"
    assert tables.writes == [], "失败批次被记入写账（假成功）"

    # ④ 检查点批量口同款：批中一枚非行投影 → 全批不落（接口面 fail-closed）
    with pytest.raises(TypeError):
        put_checkpoint_rows(
            [
                CheckpointRow("run-a", DEFAULT_NS, "1", None, CHECKPOINT_KIND_STATE, b"", b""),
                {"thread_id": "run-a"},  # type: ignore[list-item]
            ],
            tables=tables,
        )
    assert checkpoint_rows("run-a", tables=tables) == []
    assert tables.writes == []


# ---------- 18 本块零判断零模型（行为 15 AST 扫描） ----------


def test_no_judgement_or_model_in_persistence() -> None:
    """本块零判断零模型（AST 扫描）。"""
    trees = _source_trees()
    assert trees, "未扫到本块源码（探测器失效）"
    assert _judgement_or_model_findings(trees) == [], "本块出现词表／正则语义判定或模型调用"

    # 同族红线面（规格 框架与依赖红线④的 AST 降维）：本块只依赖 `state`／`infra`＋自身
    assert _import_findings(trees) == [], "本块引了包内其它块（成环风险）"

    # 探测器非空转：伪造源各形逐一命中
    forged = [
        ("probe", ast.parse("import re\nre.match('x', text)")),
        ("probe", ast.parse("from appv2.infra.llm_client import embeddings\nembeddings(['x'])")),
        ("probe", ast.parse("llm.complete('提示')")),
        ("probe", ast.parse("LEXICON = {'关键词': '值'}")),
        ("probe", ast.parse("import langgraph")),
        ("probe", ast.parse("from appv2.runtimev2.orchestration import saver")),
    ]
    findings = _judgement_or_model_findings(forged)
    assert any("禁引模块 re" in finding for finding in findings)
    assert any("禁引模块 appv2.infra.llm_client" in finding for finding in findings)
    assert any("模型调用 .complete" in finding for finding in findings)
    assert any("词表名面 LEXICON" in finding for finding in findings)
    assert any("禁引模块 langgraph" in finding for finding in findings)
    assert _import_findings(forged) != []


# ---------- 19 【边界集】（规格 表行 19） ----------


def test_boundary_empty_huge_badref_legacy(audit_records: list[AuditRecord]) -> None:
    """【边界集】空 payload／超长事实／坏 ref／旧版本记录 → 各落对应分支。"""
    store, tables = _store()
    store.save(_run("run-a", status="completed"))

    # ① 空 payload／空结构：如实落盘读回（不归 NULL、不抛错——空结构与缺失可区分）
    store.save(_step("run-a", 1, payload={}, manifest={}))
    empty = store.steps("run-a")[0]
    assert empty.payload == {} and empty.payload is not None
    assert empty.manifest == {} and empty.manifest is not None

    # ② 超长事实：落截断可见分支（标记＋长度受控）；空串＝不触界（不添标记）
    audit(replace(_audit("run-a"), facts="超" * 500))
    assert audit_records[-1].facts.endswith(TRUNCATION_MARK)
    assert len(audit_records[-1].facts) <= SUMMARY_LIMIT
    assert len(head("长" * 500)) <= BLACKBOX_LINE_LIMIT
    assert summarize("") == "" and head("") == ""

    # ③ 坏 ref：不可解析 handle → 抛错分支（不猜、不返回哨兵）；空原文＝合法 handle 的边界
    empty_ref = store.put_ref(b"")
    assert empty_ref.bytes == 0 and empty_ref.sha256 == hashlib.sha256(b"").hexdigest()
    assert store.read_ref(empty_ref.handle) == b""
    for bad_handle in (
        "",
        "blob-",
        "blob-" + "0" * 63,
        "blob-" + "0" * 65,
        "blob-" + "Z" * 64,
        "sha256:" + "0" * 64,
    ):
        with pytest.raises(UnknownHandleError):
            store.read_ref(bad_handle)

    # ④ 旧版本记录：黑匣子回放／检查点读入各落「如实空显」分支（不抛错、不补写、不回溯改写）
    store.save(_run("run-v1", status="completed"))
    store.save(_blackbox("run-v1", _V1_BLACKBOX_RECORD))
    archived = store.blackbox("run-v1")
    assert archived is not None
    assert replay_channels(archived.record)["dialogue"] == []
    assert archived.record["dialogue"] == _V1_BLACKBOX_RECORD["dialogue"]

    store.save(_run("run-legacy", status="completed"))
    put_checkpoint_rows(
        [
            CheckpointRow(
                "run-legacy",
                DEFAULT_NS,
                "0001",
                None,
                CHECKPOINT_KIND_STATE,
                json.dumps(
                    dict(_V1_STATE_PAYLOAD, run_id="run-legacy"), ensure_ascii=False
                ).encode("utf-8"),
                b"not-json",
            )
        ],
        tables=tables,
    )
    legacy = store.load("run-legacy")  # 不抛错
    assert legacy.schema_version == 1 and legacy.dialogue == [] and legacy.answer == "旧答案"

    # 迁移落地的历史行（含已取消列）读面照旧可读、不回溯改写（风险 2 对策）；写面把守不变
    migrated = {"run_id": "run-legacy", "status": "completed", "legacy_only_key": "旧列"}
    tables.write(
        [
            RowOp(
                TABLE_BLACKBOX,
                ("run-legacy",),
                {"run_id": "run-legacy", "record": migrated, "created_at": _T0},
                "append",
            )
        ]
    )
    read_back = store.blackbox("run-legacy")
    assert read_back is not None and read_back.record == migrated
    with pytest.raises(BlackBoxKeyOutOfWorldError):
        store.save(_blackbox("run-legacy", migrated))


# ---------- 20 【保留集】（规格 表行 20） ----------


def test_retention_normal_roundtrip_unchanged(audit_records: list[AuditRecord]) -> None:
    """【保留集】常规落盘读回与未触发边界时的行为不变。"""
    store, tables = _store()
    store.ensure_tables()

    # 常规四类记录＋引用载体＋检查点三表：全量落盘（无一处触界）
    run = _run("run-a", status="waiting_ask")
    step = _step("run-a", 1, payload={"delivered_rows": 12, "obs_rows": 20}, manifest={"kb": 1})
    box_record: dict[str, Any] = {
        "run_id": "run-a",
        "status": "waiting_ask",
        "answer": "短答案",
        "dialogue": [{"role": "user", "content": "原话", "origin": "user_verbatim"}],
    }
    facts = "问答受理（四要素齐备）"
    blob = "大结果原文".encode()
    checkpoint = CheckpointRow(
        "run-a",
        DEFAULT_NS,
        "0001",
        None,
        CHECKPOINT_KIND_STATE,
        encode_state(RunState(run_id="run-a", status="waiting_ask")),
        encode_metadata({"messages": "1"}),
    )
    blob_row = CheckpointBlobRow("run-a", DEFAULT_NS, "messages", "1", "json", b"blob-1")
    write_row = CheckpointWriteRow(
        "run-a", DEFAULT_NS, "0001", "task-1", 0, "messages", "json", b"w1"
    )
    store.save(run)
    store.save(step)
    store.save(_blackbox("run-a", box_record))
    audit(replace(_audit("run-a"), facts=facts))
    ref = store.put_ref(blob)
    put_checkpoint_rows([checkpoint, blob_row, write_row], tables=tables)

    # 读回逐字段等价（未触发边界＝不改写、不归一）
    assert store.run("run-a") == run
    assert store.steps("run-a") == [step]
    assert store.blackbox("run-a") == BlackBox("run-a", box_record, _T0)
    assert audit_records[-1].facts == facts, "短摘要被改写／加了标记"
    assert audit_records[-1].evidence == {"run_id": "run-a"}
    assert store.read_ref(ref.handle) == blob
    assert checkpoint_rows("run-a", tables=tables) == [checkpoint]
    assert checkpoint_blobs("run-a", "0001", tables=tables) == [blob_row]
    assert checkpoint_writes("run-a", "0001", tables=tables) == [write_row]

    # 每表恰一行（无多写、无重复落盘）——各按其主键列计
    assert len(tables.scan(TABLE_RUN, "run_id", "run-a")) == 1
    assert len(tables.scan(TABLE_STEP, "run_id", "run-a")) == 1
    assert len(tables.scan(TABLE_BLACKBOX, "run_id", "run-a")) == 1
    assert len(tables.scan(TABLE_BLOB, "handle", ref.handle)) == 1
    assert len(tables.scan(TABLE_CHECKPOINT, "thread_id", "run-a")) == 1
    assert len(tables.scan(TABLE_CHECKPOINT_BLOB, "thread_id", "run-a")) == 1
    assert len(tables.scan(TABLE_CHECKPOINT_WRITE, "thread_id", "run-a")) == 1

    # 两次读回等价且无副作用
    before = len(tables.writes)
    assert store.load("run-a") == store.load("run-a")
    assert store.run("run-a") == run and store.steps("run-a") == [step]
    assert store.read_ref(ref.handle) == blob
    assert len(tables.writes) == before, "读回产生副作用"
