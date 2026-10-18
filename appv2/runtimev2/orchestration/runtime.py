"""命令受理与执行器：`AgentRuntime`（公开面）＋`RunExecutor`（拒 har 驱动、三态收口、事件流出）。

规格原文（`specs/agent-loop.md:150–:155`）：「**命令受理（H3）**：`ask`／`resume` 是唯一入口——
**`RunCommand → 执行器 → RunEvent` 为显式接缝**（将来换队列消费者，`api`／`tools`／事件契约零
改动）」「**图驱动（H3）**：组合图执行由本块驱动（命令进、事件流出），业务相位不自驱」。

本模块做五件事（别的一律不做——业务语义在相位块内）：

1. **受理**（`ask`／`resume` 两态）：身份对象→行级字符串的转换点（`state.md`「依赖与风险」5）、
   run 号生成、追问播种（前 run 检查点**终链整链承接**——钉 `pin-23`）、断线重连复用活体总线；
   **挂起恢复**＝选择回喂（`resume_choices` 留痕／澄清回收帧留场交相位消费／批准落 `approved_ids`
   ＋`extable_rounds`）＋轮预算重置（行为 7「澄清回收重置轮预算合法」）；恢复腿**重取易变环境量**
   （台账投影经 `load_ledger_dump` 重装载、工具调用环境由相位侧恢复守卫现取——行为 13）；
2. **驱动**：`load_ledger_dump` 取一次装载（`context`；失败＝run 直接失败，fail-fast）→
   `build_graph` → `ainvoke`（**状态就地改**，无 reducer）；恢复腿的步／通知帧计数从**载入态既有
   条数**起算（本腿只发本腿新产的帧）；
3. **三态收口**（H3）：`completed`／`failed`／`waiting_ask` 写 run 行（`answer`／`manifest_digest`
   随三态落）；检查点行经 `persistence` 的**框架无关行级口**落（`encode_state`——saver 组合面，
   不直连表）；**挂起收束**＝腿收口帧（`verdict`，`status=waiting_ask`）落定即止——**不关总线**
   （历史缓冲常驻、跨腿续编「不重启」）、**不发黑匣子帧**（`specs/transport.md` 行为 10：任一 run
   恰一帧 `blackbox`——它是 run 收口段那一帧）；
4. **帧面**：步帧（逐条）、收口 `verdict` 终形（**与核验 `verify` 形同批落定**——行为 11 承接
   条款）、黑匣子瘦指针、`close`；相位自产的 `text`／`tool`／`observation`／`citation`／`notice`
   ／`verdict(verify)` 帧不经本模块转发（总线同一根，本块只发自己那几种）；
5. **失败收束**：图执行器不可用／相位抛错 → fail-closed 收束为 `failed` ＋ `run_failed` notice
   （**不产出半成品答案**——「不降级与静默禁令」节：合法降级路径＝无）；
6. **审计接线与检查点 saver 组合**（H3，-C 收口簇）：五处留痕经 `persistence.audit`（唯一写口＝
   `security.audit`）落责任账（见 `audit` 模块）；检查点由本块 saver（`checkpointer.PgCheckpointer`
   ——`BaseCheckpointSaver` 一族只活本模块）**组合 `persistence` 的框架无关行级口**落——收口快照行走
   `encode_state`（`RunStore.load` 的恢复载体），saver 行走 serde 体（同表族、`kind` 列区分）。

**单腿读口与跨腿续编**（`_leg_stream`）：run 的总线在 run 生命期内常驻（历史缓冲）；`ask`／`resume`
两腿经单腿读口读到本腿收口帧为止（`ask` 帧之后的行为归 `api` 开流段——挂起铁律「`ask` 帧之后照发
`done`」），断线重连（`resume_run_id`）读**该 run 全流**直至 run 收口。帧对象／信封／游标三件的
唯一实现仍在 `transport`——本块只决定「本腿读到哪为止」，不产帧、不编号。

**零旁路**：模型只经 `bookkeeping.call_model` 发起（相位侧已收敛）、工具只经 `tools` 公开面、
帧只经 `transport` 包根（本模块 import 的是包根公开面）。
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
from collections.abc import AsyncIterator, Callable, Collection, Mapping, Sequence
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from appv2.infra import clock as infra_clock
from appv2.runtimev2.clarification.constants import ASK_DETAIL_SLOT_KEY
from appv2.runtimev2.context import DEFAULT_MAX_OBSERVATIONS, load_ledger_dump
from appv2.runtimev2.orchestration.audit import (
    closeout as audit_closeout,
)
from appv2.runtimev2.orchestration.audit import (
    exempts as audit_exempts,
)
from appv2.runtimev2.orchestration.audit import (
    extable_decisions as audit_extable_decisions,
)
from appv2.runtimev2.orchestration.audit import (
    refused_closeout,
    who_of,
    who_of_id,
)
from appv2.runtimev2.orchestration.audit import (
    run_created as audit_run_created,
)
from appv2.runtimev2.orchestration.checkpointer import PgCheckpointer
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
    NOTICE_AUDIT_WRITE_FAILED,
    NOTICE_BAN_EXEMPT,
    NOTICE_BLACKBOX_WRITE_FAILED,
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
from appv2.runtimev2.prompts import SYSTEM_BACKGROUND
from appv2.runtimev2.state import (
    ALL_FIELDS_OPTION,
    ALL_FIELDS_SENTINEL,
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
from appv2.runtimev2.transport import EventBus, SseEvent
from appv2.tools import ASKBACK_TIME_CHOICES, ToolRegistry

_APPROVED_KIND = "external_table_approval"
_APPROVE = "approve"
_APPROVAL_ID_KEY = "approval_id"
_TABLES_KEY = "tables"


async def _leg_stream(bus: EventBus, cursor: int = 0) -> AsyncIterator[SseEvent]:
    """**单腿读口**：本块给受理面的「本腿读到哪为止」视图（命令受理侧的唯一出口包装）。

    帧的来源仍然唯一——本视图**只从 `transport.EventBus.stream(cursor)` 取帧**：不产帧、不编号、
    不拼信封（帧对象／信封／游标三件的唯一实现仍在 `transport`，本块不立第二套帧通路）；它只回答
    「本次受理的这一腿（提问腿／恢复腿）到哪里为止」。

    收束判据＝**本腿的收口帧**：

    - `blackbox` 帧：run 终态收口——`specs/transport.md` 行为 10 明写它是「业务帧意义上的流末帧」，
      其后恒 `close()`（本块终态路径同批关闭总线）；
    - `verdict` 帧且 `status="waiting_ask"`：挂起收束——本腿以 ask 挂起结束（`ask` 帧之后的行为
      归 `api` 开流段：挂起铁律「`ask` 帧之后照发 `done`」，见 `specs/transport.md` 行为 8）。

    **跨腿续编**（`specs/transport.md` 行为 3「跨段不重启」）：挂起腿**不关闭**总线——run 的总线在
    run 生命期内常驻（历史缓冲），恢复腿在同一条总线上按排他起点继续读（游标＝上一腿收口帧之后），
    故 `seq` 跨腿严格递增、无重复。
    """
    async for frame in bus.stream(cursor):
        yield frame
        if frame.event == EVENT_BLACKBOX:
            return
        if frame.event == EVENT_VERDICT and frame.data.get(PAYLOAD_STATUS_KEY) == RUN_WAITING_ASK:
            return


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
        saver: Any = None,
        window_candidates: Sequence[str] | None = ASKBACK_TIME_CHOICES,
        watermark: Any = None,
        data_wells: Collection[str] | None = None,
        guide_text: str = "",
        execution_date: str = "",
        max_observations: int = DEFAULT_MAX_OBSERVATIONS,
        load_ledger: bool = True,
        clock: Any = None,
        field_instances: Callable[[], Sequence[str]] | None = None,
    ) -> None:
        self._registry = registry
        self._store = store if store is not None else RunStore()
        self._budget = budget or Budget()
        # 检查点 saver（本块专责的**组合件**）：缺省由本块内构造（框架类型不外泄——规格原文
        # `specs/agent-loop.md:71`「LangGraph（含 `langchain*`）不得渗漏出本模块」）；可注入替身。
        self._saver = saver if saver is not None else PgCheckpointer()
        self._window_candidates = window_candidates
        self._watermark = watermark
        self._data_wells = data_wells
        # 油田实例读缝（V2-82b）：对象歧义门的数据源——本块只持有并随 `LoopDeps` 下传
        # （**loader 不现值**：门判定通过前不触读面；缺省 None＝门不出声）。
        self._field_instances = field_instances
        # §A 指南段全文（流水 63）：相位侧 `clarify`／`match` 的文本注入参——装配面（启动
        # 快照）归 api 组合根，本块只持有并随 `LoopDeps` 下传（缺省空串＝空段头）。
        self._guide_text = guide_text
        # 执行日时间量（V2-123——材料头「执行日」段与期错位比对；L0 裁定 D-g：时间量经注入参）。
        # 装配面＝组合根解析一次 `today`（eval＝`gateway_adapter.frozen_date`／生产＝`infra.clock`，
        # B14）随本类注入；本块只持有并随 `LoopDeps` 下传（缺省空串＝材料头无执行日段，零漂移）。
        self._execution_date = execution_date
        self._max_observations = max_observations
        self._load_ledger = load_ledger
        # 段时长闸的计时面（行为 7「单段时限」）：**编排侧自计时**——组合根持有的时钟读数口
        # （B14 唯一时间出口 `infra.clock`；可注入替身）＋逐段起点（受理腿取；挂起等人工不计时、
        # 跨段不累计——按段取起点，故每腿受理时重取）。二者都是本类**实例字段、非状态字段**
        # （`RunState` 形状不加计时位——流水 49① 已取消计时字段）。
        self._clock = infra_clock.now if clock is None else clock
        self._started: dict[str, datetime] = {}
        self._buses: dict[str, EventBus] = {}
        self._cursors: dict[str, int] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        # 审计接线（H3）的三件随 run 走的读数：who 槽（受理腿已解析全名／恢复腿行级身份串）、
        # 本腿留痕切片基线（决定行 `resume_choices` 起点 ＋ 豁免通知起点——跨腿不重放旧行）。
        self._who: dict[str, str] = {}
        self._identity_source: dict[str, str] = {}
        self._audit_bases: dict[str, tuple[int, int]] = {}

    # ── 受理（H3）──────────────────────────────────────────────────────────

    async def execute(self, command: RunCommand) -> RunHandle:
        if command.kind == COMMAND_RESUME:
            return await self._resume(command)
        return await self._ask(command)

    async def _ask(self, command: RunCommand) -> RunHandle:
        if command.run_id:  # 形态②：断线重连——复用既有 run 的活体总线（历史缓冲），不新起 run
            bus = self._buses.get(command.run_id)
            if bus is None:
                raise RunNotFoundError(f"run 流不可达（无活体总线）：{command.run_id}")
            # 重连读口＝**run 全流跟随**（从 0 起给全部历史与后续新帧，直至 run 收口）——断点过滤
            # 归受理面（客户端回送 `id`，换算 `cursor = id + 1` 的排他起点语义真源
            # `specs/transport.md` 行为 5）。
            return handle_of(command.run_id, bus.stream())
        run_id = new_run_id()
        bus = EventBus()
        self._buses[run_id] = bus
        self._started[run_id] = self._clock()  # 本段计时起点（行为 7「单段时限」按段取）
        # 留痕①受理（`security.audit` 唯一写口）：who 槽＝入口点已解析的 `Actor` 全名（空身份经
        # `resolve_actor` 落缺省角色——身份解析只此一缝）。**解析先于建 run 行**：身份不可解析时
        # 不留半建的 run（fail-closed）。
        who = who_of(command.actor)
        seed = self._seed_messages(command.followup_of)
        state = self._initial_state(command, run_id, seed)
        self._store.save(self._run_record(state, RUN_RUNNING))
        self._who[run_id] = who
        self._audit_bases[run_id] = (0, 0)
        audit_run_created(bus, run_id=run_id, who=who, question=command.question)
        self._spawn(state, bus, run_id)
        return handle_of(run_id, _leg_stream(bus))

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
        # 留痕切片基线先取（本腿只审**新增**决定／豁免——跨腿不重放旧行）；who＝run 簿记行的行级
        # 身份串，收口时经唯一身份缝 `resolve_actor` 解析回全名（行 33 单一入口）。
        self._audit_bases[command.run_id] = (len(state.resume_choices), _exempt_count(state))
        self._identity_source[command.run_id] = run.actor
        self._who.pop(command.run_id, None)
        self._apply_choice(state, choice)
        state.status = RUN_RUNNING
        cursor = self._cursors.get(command.run_id, 0)
        bus = self._bus_of(command.run_id)
        # 恢复腿计时起点重取（行为 7：挂起等人工不计时、不累计跨段——计步计时均按段）。
        self._started[command.run_id] = self._clock()
        self._store.save(self._run_record(state, RUN_RUNNING))
        self._spawn(state, bus, command.run_id)
        # 恢复腿＝**同一条总线续编**（`specs/transport.md` 行为 3「跨段不重启、重放不位移」）：
        # 排他起点＝上一腿收口帧之后（`_cursors`），回执 `cursor` 与之一致（＝本腿下一帧 `seq`）。
        return handle_of(command.run_id, _leg_stream(bus, cursor), cursor=cursor)

    def _elapsed_seconds(self, run_id: str) -> float:
        """本段内已用时（秒）：本腿受理时取的起点 ← 钟读数差（B14 唯一时间出口，可注入替身）。

        起点缺席（旧 run／未经本执行器受理）＝`0.0`——**不冒充用时**（判据处 `>=` 不因兜底假命中）。
        """
        started = self._started.get(run_id)
        if started is None:
            return 0.0
        return float((self._clock() - started).total_seconds())

    def _bus_of(self, run_id: str) -> EventBus:
        """取 run 的活体总线（历史缓冲）；缺席／已封口（跨进程恢复面）→ 新起一条续编。"""
        bus = self._buses.get(run_id)
        if bus is None or bus.closed:
            bus = EventBus()
            self._buses[run_id] = bus
            self._cursors.setdefault(run_id, 0)
        return bus

    def _apply_choice(self, state: RunState, choice: AskChoice) -> None:
        """恢复选择回喂（`state.resume_choices` 留痕 ＋ 逐形回喂）。

        两形（`AskChoice.kind` 闭世界，形状真源 `specs/state.md` 行为 14）：

        - **澄清回收**（`kind="clarify"`）：选择经 `resume_choices` 交澄清相位消费——其契约
          `_consume_resume` 以 `state.pending_ask.kind` 判形，故**帧留场**（由该相位消费时清除）；
          同时重置轮预算（行为 7 原文「澄清回收（resume）重置轮预算合法——rounds=0」）；
          **对象歧义 ask 的选中项**（V2-82b）在此先映射进 `state.subjects`（见
          `_apply_subject_choice`——澄清消费前的编排责任）；**回答程序落位**（V2-118）在此把
          用户原话写进 `state.answer_slots[ask 帧 detail.slot]`（见 `_apply_answer_slot`——后续
          决策轮据此回喂「用户已回答『{slot}』＝{value}」，模型不必把回答编码进没有该字段的合同）；
        - **外表越集审批**（`kind="external_table_approval"`）：批准时把审批单号与其越集表集并入
          `approved_ids`（`bookkeeping.tool_context` 的放行名单面）＋`extable_rounds` 计点；帧即
          消费完毕（清除），回前置条件机重判。
        """
        frame = state.pending_ask if isinstance(state.pending_ask, dict) else {}
        state.resume_choices.append(choice_payload(choice))
        state.rounds = 0
        if choice.kind != _APPROVED_KIND:
            self._apply_subject_choice(state, choice)
            self._apply_answer_slot(state, frame, choice)
            return  # 澄清回收：帧留场交澄清相位消费（`clarification._consume_resume` 契约）
        state.pending_ask = None
        if choice.decision != _APPROVE:
            return
        detail = frame.get(ASK_KEY_DETAIL)
        detail = detail if isinstance(detail, dict) else {}
        approval_id = choice.approval_id or str(detail.get(_APPROVAL_ID_KEY) or "")
        tables = [str(name) for name in (detail.get(_TABLES_KEY) or ()) if str(name).strip()]
        state.approved_ids = [*state.approved_ids, approval_id, *tables]
        state.extable_rounds = int(state.extable_rounds) + 1

    def _apply_answer_slot(
        self, state: RunState, frame: Mapping[str, Any], choice: AskChoice
    ) -> None:
        """澄清回答的**程序落位**（V2-118——编排侧，澄清消费前；镜像 V2-82b 先例）。

        槽位标签＝本 run 该问实际给过的 ask 帧 `detail.slot`（`clarification._on_ask`／
        `_precondition_frame` 落；**不给过的不认、零发明**）：

        - 标签在场 ∧ 回答非空 ⇒ `state.answer_slots[slot]＝用户原话`（去首尾空白）——后续决策轮
          增量条据此回喂「用户已回答『{slot}』＝{value}」行，回答不再只作匿名 `user_hint`；
        - 标签缺位／非串（旧检查点残形、对象歧义程序 ask——其落位是既有 `subjects` 映射）⇒
          **本处零动作**（不编造槽位，旧路径逐字不变）；
        - 回答空串 ⇒ 不落位（如实空——不写空值冒充「已回答」）。

        三段 `ledger_notes` 槽位闭世界**零接触**（本处只写状态位，不碰对账判据）。
        """
        detail = frame.get(ASK_KEY_DETAIL)
        detail = detail if isinstance(detail, Mapping) else {}
        slot = detail.get(ASK_DETAIL_SLOT_KEY)
        if not isinstance(slot, str) or not slot:
            return
        value = str(choice.choice or "").strip()
        if not value:
            return
        state.answer_slots[slot] = value
        if choice.decision != _APPROVE:
            return
        detail = frame.get(ASK_KEY_DETAIL)
        detail = detail if isinstance(detail, dict) else {}
        approval_id = choice.approval_id or str(detail.get(_APPROVAL_ID_KEY) or "")
        tables = [str(name) for name in (detail.get(_TABLES_KEY) or ()) if str(name).strip()]
        state.approved_ids = [*state.approved_ids, approval_id, *tables]
        state.extable_rounds = int(state.extable_rounds) + 1

    def _apply_subject_choice(self, state: RunState, choice: AskChoice) -> None:
        """对象歧义 ask 的选项→主体映射（V2-82b——编排侧，澄清消费前），写后清候选。

        发射面（`clarification.subject_ask.object_ambiguity_ask`）把当次实例候选名单落在
        `state.pending_subject_options`；本处按**本 run 该问实际给过**的选项映射（不给过的不认，
        零发明）：

        - 选中项＝`ALL_FIELDS_OPTION`（逐字「都要（分源对比）」）⇒ `state.subjects`＝
          `(ALL_FIELDS_SENTINEL,)`——哨兵形（字面单点在 `state.constants`；下游分源装配认它＝
          全油田，消费面后续批）；
        - 选中项 ∈ 实例候选 ⇒ `state.subjects`＝（该实例，）；
        - 其余（自由文本／别的选项）⇒ `subjects` **不改写**（如实不猜主体——本题按原路继续，
          下一次入口仍可再问，受连续反问预算约束）。

        无论命中与否，候选名单**写后即清**（一问一答：下一个 ask 的候选不得沿用上一个）。
        候选缺位（无对象歧义 ask 在场）⇒ 本处零动作（既有澄清回收路径逐字不变）。
        """
        options = state.pending_subject_options
        if not options:
            return
        state.pending_subject_options = ()
        picked = str(choice.choice or "").strip()
        if picked == ALL_FIELDS_OPTION:
            state.subjects = (ALL_FIELDS_SENTINEL,)
        elif picked in options:
            state.subjects = (picked,)

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
        # 链首背景块（2026-10-17 H 批·角色分家）：**真链首**在此落（题面 user 条之前）——系统作用／
        # 原理／目的的背景交代（逐字稿＝`prompts.SYSTEM_BACKGROUND`），每链恰一条。追问 run 的链由
        # 前轮终链整链承接（`seed` 非空、其链首已带背景），故只在新建链（`seed` 空）时挂——
        # 「每链恰一条、恒在链首」；角色字面同下一行 `"user"`（真源＝`bookkeeping` 写口闭世界）。
        background = [] if seed else [{"role": "system", "content": SYSTEM_BACKGROUND}]
        messages = [*background, *seed, {"role": "user", "content": command.question}]
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
        # 增补面收集列表（2026-10-17 EB3 D2）：本腿相位把程序追加块入列，作答收口处出帧
        # （`graph._flush_supplements`）；收口时随 run 行落库（`supplements` 列，D1）。
        supplements: list[dict[str, Any]] = []
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
                guide_text=self._guide_text,
                execution_date=self._execution_date,
                max_observations=self._max_observations,
                field_instances=self._field_instances,
                # 恢复腿重入（同 run 第二腿起）：已落状态的步／通知**不再重发帧**（本腿只发
                # 本腿新产的帧）——计数起点＝载入态的既有条数（`_flush_steps`／`_flush_notices`
                # 按「新增逐条」语义发帧）。
                emitted_steps=len(state.steps),
                emitted_notices=len(state.notices),
                supplements=supplements,
                # 段时长闸的用量读数（行为 7「单段时限」）：受理腿取的起点 ← 钟读数差——本腿现算
                # （挂起等人工不计时、跨段不累计）。
                elapsed_seconds=lambda: self._elapsed_seconds(run_id),
            )
            result = await build_graph(deps, checkpointer=self._saver).ainvoke(
                state,
                {
                    "recursion_limit": _recursion_limit(state),
                    # 线程＝run（一 run 一线程）：检查点 saver 按 `thread_id` 落／读
                    # （挂起态跨进程恢复的物理载体——行 27）。
                    "configurable": {"thread_id": run_id},
                },
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
            await self._close_out(state, bus, run_id, error=error, supplements=supplements)

    async def _close_out(
        self,
        state: RunState,
        bus: EventBus,
        run_id: str,
        *,
        error: str,
        supplements: Sequence[dict[str, Any]] = (),
    ) -> None:
        """收口（两态）：三态判定 ＋ 状态行／步行／检查点行 ＋ 收口 `verdict(final)` 帧。

        - **挂起收束**（`waiting_ask`）：本腿以挂起结束——`verdict(final)` 帧落定后**腿即收束**
          （受理面单腿读口据此收口，`ask` 帧之后的行为归 `api` 开流段），但 run 未收口：**不关总线**
          （历史缓冲常驻、跨腿续编不重启）、**不发黑匣子帧**（`specs/transport.md` 行为 10：任一 run
          的帧序列含**恰一帧** `blackbox`——它是 run 收口段那一帧，不是每腿一帧）；
        - **run 终态收口**（`completed`／`failed`）：黑匣子帧（瘦指针，写库成败都在）＋`close()`。
          「合法降级路径＝无」——失败同样如实收口，不产出半成品答案。
        """
        digest = _manifest_digest(state)
        state.manifest_digest = digest
        status = _terminal_status(state, error=error)
        state.status = status
        self._persist(state, bus, status=status, digest=digest, supplements=supplements)
        # 审计接线（H3）：决定留痕（外表审批批准／驳回）＋豁免留痕（待产位）逐腿发；三态收口与
        # 拒答收口只在 run 终态发（挂起收束不发终态行——该 run 还会被 resume 续推）。
        self._audit_leg(state, bus, run_id, status=status, error=error)
        verdict = bus.emit(
            EVENT_VERDICT,
            {
                PAYLOAD_STATUS_KEY: status,
                "run_id": run_id,
                "manifest_digest": digest,
            },
        )
        # 下一腿的排他起点＝本腿收口帧之后（事件帧计数＋1）——恢复腿据此续编、游标诚实地交回受理面。
        self._cursors[run_id] = verdict.seq + 1
        if status == RUN_WAITING_ASK:
            return
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
                    "type": NOTICE_BLACKBOX_WRITE_FAILED,
                    "gates": [],
                    "content": f"黑匣子写口异常（过程档案缺口，run 终态不受影响）：{exc}",
                },
            )
        bus.emit(EVENT_BLACKBOX, _blackbox_pointer(record, stored=stored, size=size))
        bus.close()

    def _audit_leg(
        self, state: RunState, bus: EventBus, run_id: str, *, status: str, error: str
    ) -> None:
        """本腿五处留痕（H3）：`security.audit` 唯一写口；切片基线防跨腿重放。

        who 槽两源（受理腿＝入口点已解析的 `Actor` 全名；恢复腿＝run 簿记行的行级身份串经
        `resolve_actor` 重解析）。身份解析失败与写口异常同归「留痕缺口」机读信号
        （`audit_write_failed` 通知出流）——不静默丢审计、也不翻盘 run 终态（旧码同款守卫先例）。
        """
        choice_base, exempt_base = self._audit_bases.get(run_id, (0, 0))
        try:
            who = self._who_for(run_id)
            audit_extable_decisions(
                bus, run_id=run_id, who=who, choices=state.resume_choices[choice_base:]
            )
            audit_exempts(
                bus,
                run_id=run_id,
                who=who,
                notices=[
                    entry
                    for entry in _exempt_notices(state)[exempt_base:]
                    if isinstance(entry, dict)
                ],
            )
            audit_closeout(
                bus,
                run_id=run_id,
                who=who,
                status=status,
                answer=state.answer or "",
                error=error or (state.error or ""),
                manifest_digest=state.manifest_digest,
                refused=refused_closeout(state.notices),
            )
        except Exception as exc:  # 身份解析失败／写口异常 → 留痕缺口如实出流（不静默、不翻盘）
            bus.emit(
                EVENT_NOTICE,
                {
                    "type": NOTICE_AUDIT_WRITE_FAILED,
                    "gates": [],
                    "content": f"审计留痕缺口（责任账未落，过程态不受影响）：{exc}",
                },
            )

    def _who_for(self, run_id: str) -> str:
        """本腿 who 槽：受理腿已解析的全名优先；恢复腿经唯一身份缝解析行级身份串。"""
        resolved = self._who.get(run_id)
        if resolved is not None:
            return resolved
        return who_of_id(self._identity_source.get(run_id, ""))

    def _persist(
        self,
        state: RunState,
        bus: EventBus,
        *,
        status: str,
        digest: str,
        supplements: Sequence[dict[str, Any]] = (),
    ) -> None:
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
        self._store.save(
            self._run_record(state, status, digest=digest, supplements=supplements)
        )
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

    def _run_record(
        self,
        state: RunState,
        status: str,
        *,
        digest: str = "",
        supplements: Sequence[dict[str, Any]] = (),
    ) -> RunRecord:
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
            supplements=[dict(entry) for entry in supplements],
        )


# ── 收口件（三态判定、摘要、黑匣子）────────────────────────────────────────────


def _exempt_notices(state: RunState) -> list[dict[str, Any]]:
    """本 run 的豁免通知序（留痕切片的定基数面；`type` 取值真源＝`transport.NOTICE_TYPES`）。"""
    return [
        entry
        for entry in state.notices
        if isinstance(entry, dict) and entry.get("type") == NOTICE_BAN_EXEMPT
    ]


def _exempt_count(state: RunState) -> int:
    """豁免通知计数（本腿留痕切片的起点——恢复腿只审新增，跨腿不重放旧行）。"""
    return len(_exempt_notices(state))


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
