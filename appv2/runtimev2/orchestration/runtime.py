"""命令受理与执行器：`AgentRuntime`（公开面）＋`RunExecutor`（拒 har 驱动、三态收口、事件流出）。

规格原文（`specs/agent-loop.md:150–:155`）：「**命令受理（H3）**：`ask`／`resume` 是唯一入口——
**`RunCommand → 执行器 → RunEvent` 为显式接缝**（将来换队列消费者，`api`／`tools`／事件契约零
改动）」「**图驱动（H3）**：组合图执行由本块驱动（命令进、事件流出），业务相位不自驱」。

本模块做五件事（别的一律不做——业务语义在相位块内）：

1. **受理**（`ask`／`resume` 两态）：身份对象→行级字符串的转换点（`state.md`「依赖与风险」5）、
   run 号生成、追问播种（前 run 检查点**终链整链承接**——钉 `pin-23`）、断线重连复用活体总线；
2. **驱动**：`load_ledger_dump` 取一次装载（`context`；失败＝run 直接失败，fail-fast）→
   `build_graph` → `ainvoke`（**状态就地改**，无 reducer）；
3. **三态收口**（H3）：`completed`／`failed`／`waiting_ask` 写 run 行（`answer`／`manifest_digest`
   随三态落）；检查点行经 `persistence` 的**框架无关行级口**落（`encode_state`——saver 组合面，
   不直连表）；
4. **帧面**：步帧（逐条）、收口 `verdict` 终形（**与核验 `verify` 形同批落定**——行为 11 承接
   条款）、黑匣子瘦指针、`close`；相位自产的 `text`／`tool`／`observation`／`citation`／`notice`
   ／`verdict(verify)` 帧不经本模块转发（总线同一根，本块只发自己那几种）；
5. **失败收束**：图执行器不可用／相位抛错 → fail-closed 收束为 `failed` ＋ `run_failed` notice
   （**不产出半成品答案**——「不降级与静默禁令」节：合法降级路径＝无）。

**零旁路**：模型只经 `bookkeeping.call_model` 发起（相位侧已收敛）、工具只经 `tools` 公开面、
帧只经 `transport` 包根（本模块 import 的是包根公开面）。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import asdict
from datetime import date
from typing import Any

from appv2.infra import clock as infra_clock
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, load_ledger_dump
from appv2.runtimev2.orchestration.commands import (
    COMMAND_RESUME,
    RunCommand,
    RunEvent,
    ask_command,
    choice_payload,
    handle_of,
    new_run_id,
    resume_command,
)
from appv2.runtimev2.orchestration.constants import (
    ASK_KEY_DETAIL,
    EVENT_BLACKBOX,
    EVENT_NOTICE,
    EVENT_VERDICT,
    MANIFEST_DIGEST_CHARS,
    NODE_BATCH,
    NODES,
    NOTICE_RUN_FAILED,
    PAYLOAD_STATUS_KEY,
)
from appv2.runtimev2.orchestration.errors import (
    RunNotFoundError,
    RunNotSuspendedError,
)
from appv2.runtimev2.orchestration.graph import (
    RESUME_ENTRY_BY_ASK_KIND,
    LoopDeps,
    build_graph,
)
from appv2.runtimev2.persistence import (
    BLACKBOX_IDENTITY_KEYS,
    BLACKBOX_RECORD_KEYS,
    CHECKPOINT_KIND_STATE,
    DEFAULT_NS,
    BlackBox,
    CheckpointRow,
    RunRecord,
    RunStore,
    StepRecord,
    encode_metadata,
    encode_state,
    put_checkpoint_rows,
)
from appv2.runtimev2.state import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    RUN_WAITING_ASK,
    AskChoice,
    AskRequest,
    Budget,
    RunHandle,
    RunState,
)
from appv2.runtimev2.transport import EventBus
from appv2.tools import ASKBACK_TIME_CHOICES, ToolRegistry

_APPROVED_KIND = "external_table_approval"
_APPROVE = "approve"
_APPROVAL_ID_KEY = "approval_id"
_TABLES_KEY = "tables"


class AgentRuntime:
    """受理面（卡面公开接口逐字：`ask(q) -> RunHandle`／`resume(run_id, choice) -> RunHandle`）。"""

    def __init__(self, executor: RunExecutor) -> None:
        self._executor = executor

    async def ask(self, q: AskRequest) -> RunHandle:
        return await self._executor.execute(ask_command(q))

    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle:
        return await self._executor.execute(resume_command(run_id, choice))


class RunExecutor:
    """命令执行器（Seam 的默认实现）：`RunCommand → 图驱动 → RunEvent 流`。"""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        store: RunStore | None = None,
        budget: Budget | None = None,
        window_candidates: Sequence[str] | None = ASKBACK_TIME_CHOICES,
        watermark: Any = None,
        data_wells: Collection[str] | None = None,
        max_observations: int = DEFAULT_MAX_OBSERVATIONS,
        load_ledger: bool = True,
    ) -> None:
        self._registry = registry
        self._store = store if store is not None else RunStore()
        self._budget = budget or Budget()
        self._window_candidates = window_candidates
        self._watermark = watermark
        self._data_wells = data_wells
        self._max_observations = max_observations
        self._load_ledger = load_ledger
        self._buses: dict[str, EventBus] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    # ── 受理（H3）──────────────────────────────────────────────────────────

    async def execute(self, command: RunCommand) -> RunHandle:
        if command.kind == COMMAND_RESUME:
            return await self._resume(command)
        return await self._ask(command)

    async def _ask(self, command: RunCommand) -> RunHandle:
        if command.run_id:  # 形态②：断线重连——复用既有 run 的活体总线，不新起 run
            bus = self._buses.get(command.run_id)
            if bus is None:
                raise RunNotFoundError(f"run 流不可达（无活体总线）：{command.run_id}")
            return handle_of(command.run_id, bus.stream())
        run_id = new_run_id()
        bus = EventBus()
        self._buses[run_id] = bus
        seed = self._seed_messages(command.followup_of)
        state = self._initial_state(command, run_id, seed)
        self._store.save(self._run_record(state, RUN_RUNNING))
        self._spawn(state, bus, run_id)
        return handle_of(run_id, bus.stream())

    async def _resume(self, command: RunCommand) -> RunHandle:
        try:
            run = self._store.run(command.run_id)
        except Exception as exc:  # 读口异常 → 与「不存在」同形上抛（不静默）
            raise RunNotFoundError(f"run 不存在：{command.run_id}") from exc
        if run is None:
            raise RunNotFoundError(f"run 不存在：{command.run_id}")
        if run.status != RUN_WAITING_ASK:
            raise RunNotSuspendedError(
                f"run 非挂起态不可 resume（status={run.status}）：{command.run_id}"
            )
        state = self._store.load(command.run_id)
        choice = command.choice or AskChoice(kind="clarify")
        self._apply_choice(state, choice)
        state.status = RUN_RUNNING
        bus = EventBus()
        self._buses[command.run_id] = bus
        self._store.save(self._run_record(state, RUN_RUNNING))
        self._spawn(state, bus, command.run_id)
        return handle_of(command.run_id, bus.stream())

    def _apply_choice(self, state: RunState, choice: AskChoice) -> None:
        """恢复选择回喂（`state.resume_choices` 追加 ＋ 审批态落 `approved_ids`）。

        缓存 resume 面的两形（与相位侧读面同形）：澄清回收＝相位侧 `_consume_resume` 消费
        `choice`；**外表越集审批**＝批准时把审批单号与其越集表集并入 `approved_ids`
        （`bookkeeping.tool_context` 的放行名单面），回前置条件机重判。
        """
        frame = state.pending_ask if isinstance(state.pending_ask, dict) else {}
        state.resume_choices.append(choice_payload(choice))
        state.pending_ask = None
        state.rounds = 0
        if choice.kind != _APPROVED_KIND or choice.decision != _APPROVE:
            return
        detail = frame.get(ASK_KEY_DETAIL)
        detail = detail if isinstance(detail, dict) else {}
        approval_id = choice.approval_id or str(detail.get(_APPROVAL_ID_KEY) or "")
        tables = [str(name) for name in (detail.get(_TABLES_KEY) or ()) if str(name).strip()]
        state.approved_ids = [*state.approved_ids, approval_id, *tables]
        state.extable_rounds = int(state.extable_rounds) + 1

    # ── 播种与初态（钉 `pin-23` 的编排动作面）─────────────────────────────────

    def _seed_messages(self, followup_of: str) -> list[dict[str, str]]:
        """追问播种＝前 run 检查点**终链整链承接**（钉 `pin-23`：不裁剪、不摘要化）。

        前轮不存在 → 404 源异常；前轮非 `completed` → 409 源异常（在途轮走 resume、失败轮不可续）。
        只读不改写——前轮检查点零写回。
        """
        if not followup_of:
            return []
        try:
            prior = self._store.run(followup_of)
        except Exception as exc:
            raise RunNotFoundError(f"run 不存在：{followup_of}") from exc
        if prior is None:
            raise RunNotFoundError(f"run 不存在：{followup_of}")
        if prior.status != RUN_COMPLETED:
            raise RunNotSuspendedError(
                f"前轮未收口不可追问（status={prior.status}）：{followup_of}"
            )
        template = self._store.load(followup_of)
        return [
            {"role": str(turn.get("role", "")), "content": str(turn.get("content", ""))}
            for turn in template.messages
            if isinstance(turn, dict)
        ]

    def _initial_state(
        self, command: RunCommand, run_id: str, seed: list[dict[str, str]]
    ) -> RunState:
        actor = command.actor
        who = "" if actor is None else str(getattr(actor, "user_id", "") or "")
        messages = [*seed, {"role": "user", "content": command.question}]
        return RunState(
            run_id=run_id,
            question=command.question,
            actor=who,
            status=RUN_RUNNING,
            followup_of=command.followup_of,
            messages=messages,
            budget=self._budget,
        )

    # ── 驱动（命令进、事件流出）──────────────────────────────────────────────

    def _spawn(self, state: RunState, bus: EventBus, run_id: str) -> None:
        task = asyncio.create_task(self._drive(state, bus, run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _drive(self, state: RunState, bus: EventBus, run_id: str) -> None:
        error = ""
        try:
            if self._load_ledger:
                await load_ledger_dump(state)
            deps = LoopDeps(
                bus=bus,
                registry=self._registry,
                store=self._store,
                window_candidates=self._window_candidates,
                watermark=self._watermark,
                data_wells=self._data_wells,
                max_observations=self._max_observations,
            )
            result = await build_graph(deps).ainvoke(
                state, {"recursion_limit": _recursion_limit(state)}
            )
            state = _state_of(result, fallback=state)
        except Exception as exc:  # 图执行器不可用／相位抛错 → fail-closed 收束为 failed
            error = str(exc)
            state.error = error
            state.status = RUN_FAILED
            bus.emit(
                EVENT_NOTICE,
                {"type": NOTICE_RUN_FAILED, "gates": [], "content": f"run 执行失败：{exc}"},
            )
        finally:
            await self._close_out(state, bus, run_id, error=error)

    async def _close_out(
        self, state: RunState, bus: EventBus, run_id: str, *, error: str
    ) -> None:
        """三态收口：状态行 ＋ 步行 ＋ 检查点行 ＋ 收口 `verdict(final)` 帧 ＋ 黑匣子指针。"""
        digest = _manifest_digest(state)
        state.manifest_digest = digest
        status = _terminal_status(state, error=error)
        state.status = status
        self._persist(state, bus, status=status, digest=digest)
        bus.emit(
            EVENT_VERDICT,
            {
                PAYLOAD_STATUS_KEY: status,
                "run_id": run_id,
                "manifest_digest": digest,
            },
        )
        record = _blackbox_record(state, error=error)
        stored, size = False, 0
        try:
            size = len(json.dumps(record, ensure_ascii=False))
            self._store.save(BlackBox(run_id=run_id, record=record, created_at=infra_clock.now()))
            stored = True
        except Exception as exc:  # 黑匣子写口异常 → 留痕缺口不静默（run 终态零翻盘）
            bus.emit(
                EVENT_NOTICE,
                {
                    "type": "blackbox_write_failed",
                    "gates": [],
                    "content": f"黑匣子写口异常（过程档案缺口，run 终态不受影响）：{exc}",
                },
            )
        bus.emit(EVENT_BLACKBOX, _blackbox_pointer(record, stored=stored, size=size))
        bus.close()

    def _persist(self, state: RunState, bus: EventBus, *, status: str, digest: str) -> None:
        for entry in state.steps:
            if not isinstance(entry, dict):
                continue
            self._store.save(
                StepRecord(
                    run_id=str(entry.get("run_id") or state.run_id),
                    seq=int(entry.get("seq") or 0),
                    step=str(entry.get("step") or ""),
                    status=str(entry.get("status") or ""),
                    title=str(entry.get("title") or ""),
                    manifest=entry.get("manifest"),
                    payload=entry.get("payload"),
                    created_at=infra_clock.now(),
                )
            )
        self._store.save(self._run_record(state, status, digest=digest))
        put_checkpoint_rows(
            [
                CheckpointRow(
                    thread_id=state.run_id,
                    ns=DEFAULT_NS,
                    checkpoint_id=_checkpoint_id(state.run_id),
                    parent_checkpoint_id=None,
                    kind=CHECKPOINT_KIND_STATE,
                    checkpoint=encode_state(state),
                    metadata=encode_metadata({}),
                )
            ]
        )

    def _run_record(self, state: RunState, status: str, *, digest: str = "") -> RunRecord:
        now = infra_clock.now()
        return RunRecord(
            run_id=state.run_id,
            question=state.question,
            actor=state.actor,
            status=status,
            answer=state.answer or None,
            error=state.error,
            manifest_digest=digest or (state.manifest_digest or None),
            followup_of=state.followup_of,
            created_at=now,
            updated_at=now,
        )


# ── 收口件（三态判定、摘要、黑匣子）────────────────────────────────────────────


def _terminal_status(state: RunState, *, error: str) -> str:
    """三态判定（本块职权，规格原文 `specs/agent-loop.md:171`「提交完成的是本块」）。

    挂起（`pending_ask` 在场）＞ 失败（图抛错或状态带错）＞ 完成。
    """
    if state.pending_ask:
        return RUN_WAITING_ASK
    if state.status == RUN_FAILED or error:
        return RUN_FAILED
    return RUN_COMPLETED


def _manifest_digest(state: RunState) -> str:
    """收口摘要面：步记录 Manifest 投影的确定性哈希（同输入同摘要——计费对账面可复核）。"""
    manifests = [
        entry.get("manifest")
        for entry in state.steps
        if isinstance(entry, dict) and entry.get("manifest") is not None
    ]
    payload = json.dumps(manifests, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:MANIFEST_DIGEST_CHARS]


def _blackbox_record(state: RunState, *, error: str) -> dict[str, Any]:
    """黑匣子记录（只掐白名单键 ＋ 身份面四键——键集闭世界真源在 `persistence`）。"""
    values = asdict(state)
    record: dict[str, Any] = {key: values[key] for key in BLACKBOX_RECORD_KEYS if key in values}
    record["run_id"] = state.run_id
    record["question"] = state.question
    record["status"] = state.status
    record["error"] = error
    keys = (*BLACKBOX_RECORD_KEYS, *BLACKBOX_IDENTITY_KEYS)
    return {key: record[key] for key in keys if key in record}


def _blackbox_pointer(record: dict[str, Any], *, stored: bool, size: int) -> dict[str, Any]:
    """瘦指针（七个键；全文入库不入帧——`specs/transport.md` 行为 10）。"""
    return {
        "run_id": str(record.get("run_id", "")),
        "question": str(record.get("question", "")),
        "status": str(record.get("status", "")),
        "error": str(record.get("error", "")),
        "stored": bool(stored),
        "bytes": int(size),
        "counts": {
            "messages": len(record.get("messages") or []),
            "dialogue": len(record.get("dialogue") or []),
            "process_notes": len(record.get("process_notes") or []),
            "observations": len(record.get("observations") or []),
            "steps": len(record.get("steps") or []),
        },
    }


def _recursion_limit(state: RunState) -> int:
    """图执行的**框架安全网**（非业务闸）：超步上限 ＝ 轮预算 × 每轮最多节点数。

    定位说明：业务面「有界终止」（轮数／发现／时长三闸）归 -B／-C 票；本函数只是**框架递归上限**
    ——防相位自环（匹配拒因回喂、拒因回喂重决策）在模型持续发射不合格输出的极端情形下无界打转。
    上限按图结构推导：`预算轮数 × (节点数 ＋ 1) ＋ 节点数`（每轮最多走遍全部节点＋一次发现步，
    另留一轮余量）——超限＝`GraphRecursionError` → 由 `_drive` 按 fail-closed 收束为 `failed`。
    """
    per_round = len(NODES) + 1
    rounds = max(1, int(state.budget.rounds))
    return rounds * per_round + len(NODES)


def _state_of(result: Any, *, fallback: RunState) -> RunState:
    """图返回面 → `RunState`（节点交回的全字段通道值原样重建）。

    `ainvoke` 的返回＝**通道字典**（框架的 dataclass schema 形态）；节点的更新即全字段现值
    （`graph._updates_of`），故按字段名重建即得终态。返回非字典／重建失败 → 回退到调用方持有的
    那个状态对象（列表字段共享同一对象，就地追加仍可见）。
    """
    if isinstance(result, RunState):
        return result
    if not isinstance(result, Mapping):
        return fallback
    names = {field.name for field in dataclasses.fields(RunState)}
    try:
        return RunState(**{key: value for key, value in result.items() if key in names})
    except Exception:  # 重建失败（通道缺字段／取值越界）→ 回退（不吞错，终态照实收口）
        return fallback


def _checkpoint_id(run_id: str) -> str:
    """检查点号（同一线程内按写入时刻升序——`latest_state_row` 取最大即最新）。"""
    stamp = infra_clock.now().strftime("%Y%m%d%H%M%S%f")
    return f"{stamp}-{run_id}"


def watermark_of(clock: Any = None) -> date:
    """水位注入值（B14：时间只经 `infra.clock`；`now().date()`——裁决 L0-3 逐字）。"""
    reader = infra_clock.now if clock is None else clock
    return reader().date()


__all__ = [
    "NODE_BATCH",
    "RESUME_ENTRY_BY_ASK_KIND",
    "AgentRuntime",
    "RunEvent",
    "RunExecutor",
    "watermark_of",
]
