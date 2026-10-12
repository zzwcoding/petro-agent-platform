"""runtime.executor —— RunCommand seam＋GraphRunExecutor＋AgentRuntime（ADR-0003）。

ADR-0003 预留接缝的落点：runtime 以 RunCommand（ask/resume）→执行器→RunEvent
流建模——命令入口（AgentRuntime）与执行器（GraphRunExecutor）之间为显式 seam；
将来水平扩展时执行器换 Redis Stream 消费者，api/tools/事件契约零改动。

执行器职责：受理命令→装配六步图（checkpointer 注入）→后台驱动→run 状态机
落库（running→waiting_ask/completed/failed）→事件流收束。挂起恢复时刷新段时限
（预算三闸之「总时长 300s」按段计时——跨进程恢复不误触时长闸）并在受理段回写
running（行为约定 8 的 →running 转移——恢复段 GET run 报现值，V2-20 C1）。

审计闭环（V2-20 任务 1——P-010 S3）：run 创建/终态（completed|failed）/拒答
收口/外表审批决定四事件经 RunAuditor 落 audit_log 责任账（唯一写口
security.audit，action 恒 agent_v2.* 前缀）；审计写口异常转 notice 出流——
留痕缺口不静默，已落定的 run 状态机零改动（过程态与责任账分离，见 audit.py）。
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langgraph.types import Command

from appv2.infra.db import ConnectionManager
from appv2.infra.security import Actor, SecurityService
from appv2.runtime.audit import RunAuditor, who_of
from appv2.runtime.blackbox import distill, pointer
from appv2.runtime.budget import Budget, now_monotonic
from appv2.runtime.context import ContextBuilder
from appv2.runtime.events import EVENT_BLACKBOX, EventBus
from appv2.runtime.graph import LoopDeps, build_graph
from appv2.runtime.llm import GatewayChatModel
from appv2.runtime.state import (
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_RUNNING,
    RUN_WAITING_ASK,
    AskChoice,
    AskRequest,
    RunHandle,
    RunState,
)
from appv2.runtime.store import RunStore
from appv2.tools import ASK_EXTERNAL_TABLE_APPROVAL, ToolRegistry

# ---------- RunCommand（ADR-0003 seam 的命令侧闭世界） ----------

COMMAND_ASK = "ask"
COMMAND_RESUME = "resume"
COMMAND_KINDS: frozenset[str] = frozenset({COMMAND_ASK, COMMAND_RESUME})


@dataclass(frozen=True, slots=True)
class RunCommand:
    """run 命令（ask/resume 两态闭世界——api 层只经 AgentRuntime 入命令）。

    followup_of（V2-38 追问续会话）：非空＝追问形态——新 run 播种该前轮线程的
    消息历史（前轮问句/决策/执行台账/答案随追问进上下文）；前轮须 completed。
    """

    kind: str
    question: str = ""
    actor: Actor | None = None
    run_id: str = ""
    choice: AskChoice | None = None
    followup_of: str = ""

    def __post_init__(self) -> None:
        if self.kind not in COMMAND_KINDS:
            raise ValueError(f"RunCommand.kind 越界（{sorted(COMMAND_KINDS)}）：{self.kind!r}")


class RunNotFoundError(Exception):
    """run 不存在（V2-07 api 404 的 runtime 侧异常源）。"""


class RunNotSuspendedError(Exception):
    """run 非挂起态不可 resume（V2-07 api 409 的 runtime 侧异常源）。"""


def new_run_id() -> str:
    """run 号（机器短 id 族 run-——00 §1.5 同族）。"""
    return f"run-{uuid.uuid4().hex[:8]}"


class GraphRunExecutor:
    """命令执行器：RunCommand →六步图驱动→RunEvent 流（seam 的默认实现）。"""

    def __init__(
        self,
        *,
        registry: ToolRegistry,
        models: dict[str, GatewayChatModel],
        db: ConnectionManager,
        saver: Any,  # PgCheckpointer（BaseCheckpointSaver——防环不直接 import 类型）
        budget: Budget | None = None,
        builder: ContextBuilder | None = None,
        security: SecurityService | None = None,
        guide: Any = None,  # GuideProvider（拍板⑦处理指南缝——防环不直接 import 类型）
        today: Any = None,  # date（指南缺省实现的今天锚点——测试钉日；缺省 infra.clock）
        four_phase: bool = False,  # V2-34 四相位装配（ADR-0005——骨架期缺省 False）
        ledger_dump: Any = None,  # Callable[[], dict] 词典层全量投影缝（拍板 a）
        watermark: Any = None,  # Callable[[], date | None] 水位读缝（前置条件机）
        data_wells: Any = None,  # Callable[[], frozenset[str]] 井闭世界读缝（V2-51 域闸）
        object_digests: Any = None,  # Callable[[], list[str]] 本体对象摘要缝（V2-58 理解步）
    ) -> None:
        self._registry = registry
        self._models = models
        self._db = db
        self._saver = saver
        self._budget = budget or Budget()
        self._builder = builder or ContextBuilder()
        self._guide = guide
        self._today = today
        self._four_phase = four_phase
        self._ledger_dump = ledger_dump
        self._watermark = watermark
        self._data_wells = data_wells
        self._object_digests = object_digests
        self._store = RunStore(db)
        self._auditor = RunAuditor(db, security)
        self._tasks: set[asyncio.Task[None]] = set()

    async def execute(self, command: RunCommand) -> RunHandle:
        """受理命令（立即返回 RunHandle——图在后台任务驱动，事件流实时消费）。"""
        bus = EventBus()
        await self._auditor.ensure_ready()
        if command.kind == COMMAND_ASK:
            actor = command.actor or Actor(user_id="", display="")
            who = who_of(actor)
            run_id = new_run_id()
            # 追问续会话（V2-38/ADR-0006 会话线程承接形态）：前轮线程消息历史
            # 播种新 run——追问进上下文含前轮问答（前轮须 completed，未收口轮走
            # resume；run 状态机零改动——追问＝新 run 行，api 层最小改动）。
            seed_history = await self._seed_history(command.followup_of)
            await self._store.create_run(
                run_id=run_id, question=command.question, actor=actor.who
            )
            await self._audit(
                bus,
                self._auditor.run_created,
                run_id=run_id,
                question=command.question,
                who=who,
            )
            graph = build_graph(
                self._deps(bus, run_id=run_id),
                checkpointer=self._saver,
                four_phase=self._four_phase,
            )
            state = self._initial_state(
                run_id, command.question, actor.user_id, history=seed_history,
                followup_of=command.followup_of,
            )
            config: dict[str, Any] = {"configurable": {"thread_id": run_id}}
            self._spawn(graph, state, config, bus, run_id, who=who)
            return RunHandle(run_id=run_id, stream=bus.stream())
        if command.kind == COMMAND_RESUME:
            run = await self._store.get_run(command.run_id)
            if run is None:
                raise RunNotFoundError(f"run 不存在：{command.run_id}")
            if run.status != RUN_WAITING_ASK:
                raise RunNotSuspendedError(
                    f"run 非挂起态不可 resume（status={run.status}）：{command.run_id}"
                )
            # 挂起恢复受理段回写 running（行为约定 8 →running 转移——C1）：恢复段
            # 执行期 GET run 报现值 running；转移把守仅 waiting_ask→running。
            try:
                await self._store.mark_running(command.run_id)
            except ValueError as exc:
                raise RunNotSuspendedError(str(exc)) from exc
            graph = build_graph(
                self._deps(bus, run_id=command.run_id),
                checkpointer=self._saver,
                four_phase=self._four_phase,
            )
            config = {"configurable": {"thread_id": command.run_id}}
            # 段时限刷新（挂起等人工不计预算——恢复段重新起算时长闸；原「段步
            # 基线 segment_step_base」为死字段已删——P-024b C1：全仓零消费点，
            # 挂起不计预算的实际机制就是本处 deadline_monotonic 段刷新）。
            snapshot = await graph.aget_state(config)
            values = snapshot.values or {}
            resume_choice_base = len(values.get("resume_choices") or [])
            # 豁免审计基线（挂起前已落账的 ban_exempt notice 数——恢复段只补
            # 增量，防累计 notices 重放重复行；resume_choice_base 同款切片法）。
            ban_exempt_base = sum(
                1
                for n in (values.get("notices") or [])
                if isinstance(n, dict) and n.get("type") == "ban_exempt"
            )
            await graph.aupdate_state(
                config,
                {
                    "deadline_monotonic": now_monotonic() + self._budget.total_seconds,
                },
            )
            choice = command.choice or AskChoice(value="")
            self._spawn(
                graph,
                Command(resume=choice.as_payload()),
                config,
                bus,
                command.run_id,
                who=str(run.actor),
                resume_choice_base=resume_choice_base,
                ban_exempt_base=ban_exempt_base,
            )
            return RunHandle(run_id=command.run_id, stream=bus.stream())
        raise ValueError(f"未知 RunCommand：{command.kind!r}")

    # ---------- 内部位 ----------

    async def _seed_history(self, followup_of: str) -> list[dict[str, str]]:
        """前轮线程消息历史（追问续会话的播种面——V2-38）。

        前轮不存在＝RunNotFoundError（api 404）；非 completed＝RunNotSuspendedError
        （api 409——挂起轮走 resume、在途/失败轮不可续）。历史取自 checkpointer
        的前轮线程终态（RunState.history 逐轮投影），前轮最终答案作 assistant 轮
        追加（草稿≠终稿——收口答案含核验改写/引用块，前轮问答史以终稿落）。
        """
        if not followup_of:
            return []
        prior = await self._store.get_run(followup_of)
        if prior is None:
            raise RunNotFoundError(f"run 不存在：{followup_of}")
        if prior.status != RUN_COMPLETED:
            raise RunNotSuspendedError(
                f"前轮未收口不可追问（status={prior.status}）：{followup_of}"
            )
        graph = build_graph(
            self._deps(EventBus(), run_id=followup_of),
            checkpointer=self._saver,
            four_phase=self._four_phase,
        )
        snapshot = await graph.aget_state(
            {"configurable": {"thread_id": followup_of}}
        )
        values = snapshot.values or {}
        turns = [
            {"role": str(t.get("role", "user")), "content": str(t.get("content", ""))}
            for t in (values.get("history") or [])
            if isinstance(t, dict)
        ]
        prior_answer = str(prior.answer or "")
        if prior_answer:
            turns.append({"role": "assistant", "content": f"上轮答案：{prior_answer}"})
        return turns

    def _deps(self, bus: EventBus, run_id: str = "") -> LoopDeps:
        # V2-33 run_id 盖章：per-run 模型副本携 run 号（GatewayChatModel.run_id →
        # completer 协议 params 面 → gateway 记账 run_id 列）。共享模型字典零
        # 变异——并发 run 各持副本，无交叉盖章。
        models: dict[str, GatewayChatModel] = self._models
        if run_id:
            models = {
                key: model.model_copy(update={"run_id": run_id})
                for key, model in self._models.items()
            }
        return LoopDeps(
            registry=self._registry,
            models=models,
            builder=self._builder,
            store=self._store,
            bus=bus,
            guide=self._guide,
            ledger_dump=self._ledger_dump,
            watermark=self._watermark,
            data_wells=self._data_wells,
            object_digests=self._object_digests,
            today=self._today,
        )

    def _initial_state(
        self,
        run_id: str,
        question: str,
        actor_id: str,
        history: list[dict[str, str]] | None = None,
        followup_of: str = "",
    ) -> RunState:
        started = now_monotonic()
        return RunState(
            run_id=run_id,
            question=question,
            actor=actor_id,
            status=RUN_RUNNING,
            followup_of=followup_of,  # V2-53 追问旁路判据（RunCommand 随行播种）
            history=list(history or []),  # 追问续会话播种（V2-38——前轮线程历史）
            budget=self._budget.as_dict(),
            started_monotonic=started,
            deadline_monotonic=started + self._budget.total_seconds,
        )

    def _spawn(
        self,
        graph: Any,  # CompiledStateGraph
        graph_input: Any,  # RunState | Command
        config: dict[str, Any],
        bus: EventBus,
        run_id: str,
        *,
        who: str = "",
        resume_choice_base: int = 0,
        ban_exempt_base: int = 0,
    ) -> None:
        task = asyncio.create_task(
            self._drive(
                graph, graph_input, config, bus, run_id,
                who=who, resume_choice_base=resume_choice_base,
                ban_exempt_base=ban_exempt_base,
            )
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _drive(
        self,
        graph: Any,
        graph_input: Any,
        config: dict[str, Any],
        bus: EventBus,
        run_id: str,
        *,
        who: str = "",
        resume_choice_base: int = 0,
        ban_exempt_base: int = 0,
    ) -> None:
        """图驱动收口：状态落库（run 状态机四态）＋审计四事件＋事件流收束。"""
        final: dict[str, Any] | None = None
        run_error = ""
        try:
            final = await graph.ainvoke(graph_input, config)
            await self._store.put_steps(run_id, list(final.get("steps") or []))
            if final.get("pending_ask"):
                await self._store.finish_run(run_id, status=RUN_WAITING_ASK)
                # 段首已处理的决定照落审计（本段可再次挂起——决定与终态无关）。
                await self._audit_decisions(
                    bus, run_id=run_id, final=final, who=who, base=resume_choice_base
                )
                await self._audit_ban_exempts(
                    bus, run_id=run_id, final=final, who=who, base=ban_exempt_base
                )
            elif final.get("error"):
                error = str(final["error"])
                await self._store.finish_run(run_id, status=RUN_FAILED, error=error)
                await self._audit(
                    bus, self._auditor.run_failed, run_id=run_id, error=error, who=who
                )
                await self._audit_decisions(
                    bus, run_id=run_id, final=final, who=who, base=resume_choice_base
                )
                await self._audit_ban_exempts(
                    bus, run_id=run_id, final=final, who=who, base=ban_exempt_base
                )
            else:
                answer = str(final.get("answer") or "")
                digest = str(final.get("manifest_digest") or "")
                await self._store.finish_run(
                    run_id,
                    status=RUN_COMPLETED,
                    answer=answer,
                    manifest_digest=digest or None,
                )
                # 决定行先于收口行（写入序＝时序）；拒答与正常收口互斥恰一行。
                await self._audit_decisions(
                    bus, run_id=run_id, final=final, who=who, base=resume_choice_base
                )
                # 豁免放行行先于收口行（N1 豁免必留痕——P-051b 审查②）。
                await self._audit_ban_exempts(
                    bus, run_id=run_id, final=final, who=who, base=ban_exempt_base
                )
                await self._audit_closeout(
                    bus, run_id=run_id, final=final, answer=answer, who=who
                )
        except Exception as exc:  # 引擎/网关异常——run failed，如实留痕（不静默）
            run_error = str(exc)
            await self._store.finish_run(run_id, status=RUN_FAILED, error=str(exc))
            await self._audit(
                bus,
                self._auditor.run_failed,
                run_id=run_id,
                error=str(exc),
                who=who,
            )
            bus.emit(
                "notice",
                {"type": "run_failed", "gates": [], "content": f"run 执行失败：{exc}"},
            )
        finally:
            # V2-54/V2-55 黑匣子收口：蒸馏入库（agent_v2_blackbox——过程档案
            # 不入帧防仓膨胀）＋瘦指针出流（帧自动收录的只是指针；完整面经
            # get_blackbox／tools.run_replay 读库）。写口失败→notice 留痕缺口
            # 不静默（审计守卫同款），终态零翻盘。异常段 final=None＝骨架记录。
            record = distill(final, run_id=run_id, error=run_error)
            stored, blob_bytes = False, 0
            try:
                blob_bytes = len(json.dumps(record, ensure_ascii=False))
                await self._store.put_blackbox(run_id, record)
                stored = True
            except Exception as exc:
                bus.emit(
                    "notice",
                    {
                        "type": "blackbox_write_failed",
                        "gates": [],
                        "content": (
                            f"黑匣子写口异常（过程档案缺口，run 终态不受影响）：{exc}"
                        ),
                    },
                )
            bus.emit(
                EVENT_BLACKBOX,
                pointer(record, stored=stored, bytes_written=blob_bytes),
            )
            bus.close()

    # ---------- 审计四事件（V2-20——唯一写口 security.audit，失败不静默不翻盘） ----------

    async def _audit(
        self,
        bus: EventBus,
        method: Callable[..., Awaitable[None]],
        /,
        **kwargs: Any,
    ) -> None:
        """审计发射守卫：写口异常→notice 出流（留痕缺口可见），run 状态机零改动。"""
        try:
            await method(**kwargs)
        except Exception as exc:
            bus.emit(
                "notice",
                {
                    "type": "audit_write_failed",
                    "gates": [],
                    "content": f"审计写口异常（责任账缺口，过程态不受影响）：{exc}",
                },
            )

    async def _audit_closeout(
        self,
        bus: EventBus,
        *,
        run_id: str,
        final: dict[str, Any],
        answer: str,
        who: str,
    ) -> None:
        """completed 段审计分型：拒答收口（refused）与正常收口互斥——终态审计恰一行。"""
        notices = [n for n in (final.get("notices") or []) if isinstance(n, dict)]
        refused = [n for n in notices if n.get("type") == "refused"]
        if refused:
            await self._audit(
                bus,
                self._auditor.refused,
                run_id=run_id,
                reason=str(refused[-1].get("content", "")),
                who=who,
            )
            return
        await self._audit(
            bus,
            self._auditor.run_completed,
            run_id=run_id,
            answer=answer,
            manifest_digest=str(final.get("manifest_digest") or ""),
            who=who,
        )

    async def _audit_decisions(
        self,
        bus: EventBus,
        *,
        run_id: str,
        final: dict[str, Any],
        who: str,
        base: int,
    ) -> None:
        """本段新增的 resume 决定审计（外表审批批准/驳回——resume_choices 切片）。"""
        choices = [c for c in (final.get("resume_choices") or []) if isinstance(c, dict)]
        for record in choices[max(base, 0) :]:
            if record.get("kind") != ASK_EXTERNAL_TABLE_APPROVAL:
                continue  # clarify 等非审批决定不在四事件闭世界（零溢行）
            await self._audit(
                bus,
                self._auditor.extable_decided,
                run_id=run_id,
                approved=record.get("value") == "批准",
                approval_id=str(record.get("approval_id") or ""),
                who=who,
            )

    async def _audit_ban_exempts(
        self, bus: EventBus, *, run_id: str, final: dict[str, Any], who: str, base: int
    ) -> None:
        """本段 N1 豁免放行审计（V2-52 附 C——豁免必留 audit 行，P-051b 审查②）。

        理解入口闸的豁免 notice（type=ban_exempt，携 term 机读键）逐条一行
        agent_v2.ban_exempt（三终态全覆盖——豁免后挂起/失败/收口都留痕）；
        base＝挂起前已落账数（恢复段切片只补增量——resume_choice_base 同款）。
        """
        notices = [n for n in (final.get("notices") or []) if isinstance(n, dict)]
        for notice in notices[max(base, 0) :]:
            if notice.get("type") != "ban_exempt":
                continue
            await self._audit(
                bus,
                self._auditor.ban_exempt,
                run_id=run_id,
                term=str(notice.get("term") or ""),
                who=who,
            )


class AgentRuntime:
    """命令入口（modules.md runtime 卡公开接口——api 只见此层）。"""

    def __init__(self, executor: GraphRunExecutor) -> None:
        self._executor = executor

    async def ask(self, q: AskRequest) -> RunHandle:
        """建 run，返 run_id＋事件流（specs/agent-loop.md 接口定义节）。

        followup_of 非空＝追问续会话（V2-38）——前轮线程历史随追问进上下文。
        """
        return await self._executor.execute(
            RunCommand(
                kind=COMMAND_ASK,
                question=q.question,
                actor=q.actor,
                followup_of=q.followup_of,
            )
        )

    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle:
        """挂起 run 凭选择续跑（非挂起态/不存在＝RunNotSuspendedError/RunNotFoundError）。"""
        return await self._executor.execute(
            RunCommand(kind=COMMAND_RESUME, run_id=run_id, choice=choice)
        )
