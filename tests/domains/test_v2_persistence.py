"""persistence 块验收（RT-W2-01a：骨架＋接口＋落盘读回主干＋本块全部 3 条 pin 行）。

票面对象＝`specs/persistence.md`「验收测试」表第 1–5、9、10、11、12、15 行（-a 逐字，测试标识同
规格列）；测试网钉＝pin-12（`::verify_fields_readable_in_step`，落盘面）／pin-28
（`::run_id_stamped_across_records`，落盘面）／pin-30（`::legacy_read_honest`——本块**唯一**挂断言的
面：旧 run **黑匣子回放**如实；检查点状态字段读入面挂 `specs/state.md` 行为 8，两处对象不同）。

真源指针：形状＝`specs/modules.md` `## persistence` 卡＋`specs/persistence.md` 接口定义节；
列事实与常量＝`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`（R-J-02 白名单／R-J-05 审计
action 七值／R-J-06 摘要长度／R-J-17 唯一合法转移）；`pin-12` 字段面＝`specs/verification.md`
行为 11（`delivered_rows`／`obs_rows`）＋`arch/P7a-交接包与挂账清单.md` A-P7a-38；`pin-28` 对账口径
＝`eval/results/Q15-对账报告.md`（逐题 `ledger_run_ids` 与 jsonl 同跑 `run_id` 集合等值）。

时间列一律经 `infra.clock`（B14）——本件用 `clock.freeze` 冻结，`RunStore` 缺省钟即走该出口。
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Iterator, Sequence
from dataclasses import FrozenInstanceError, asdict, fields
from datetime import datetime
from inspect import signature
from pathlib import Path
from typing import Any

import pytest

from appv2.infra import clock
from appv2.runtimev2.persistence import (
    APPEND_ONLY_TABLES,
    AUDIT_ACTION_REFUSED,
    AUDIT_ACTION_RUN_COMPLETED,
    AUDIT_ACTION_RUN_CREATED,
    BLACKBOX_RECORD_KEYS,
    CHECKPOINT_KIND_STATE,
    DEFAULT_NS,
    REPLAY_CHANNELS,
    TABLE_BLACKBOX,
    TABLE_BLOB,
    TABLE_RUN,
    TABLE_STEP,
    TABLES,
    AlreadyArchivedError,
    AuditRecord,
    BlackBox,
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
    put_checkpoint_rows,
    replay_channels,
)
from appv2.runtimev2.state import DIALOGUE_ORIGINS, RUN_STATUS_KINDS, STEP_KINDS, RunState

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PERSISTENCE_DIR = _REPO_ROOT / "appv2" / "runtimev2" / "persistence"
_T0 = datetime(2026, 10, 16, 9, 0, 0)

# 规格 「接口定义」节的两个闭世界（本块**引 state 常量**、不复述取值——本件断言引面不漂）
_SPEC_RUN_STATUSES = {"running", "waiting_ask", "completed", "failed"}
_SPEC_STEP_KINDS = {"decision", "discover", "execute", "observe", "verify", "answer"}
_SPEC_STEP_STATUSES = {"ok", "failed", "refused"}

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
