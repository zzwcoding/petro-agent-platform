"""runtime.executor —— RunCommand seam＋GraphRunExecutor＋AgentRuntime（ADR-0003）。

ADR-0003 预留接缝的落点：runtime 以 RunCommand（ask/resume）→执行器→RunEvent
流建模——命令入口（AgentRuntime）与执行器（GraphRunExecutor）之间为显式 seam；
将来水平扩展时执行器换 Redis Stream 消费者，api/tools/事件契约零改动。

执行器职责：受理命令→装配六步图（checkpointer 注入）→后台驱动→run 状态机
落库（running→waiting_ask/completed/failed）→事件流收束。挂起恢复时刷新段时限
（预算三闸之「总时长 300s」按段计时——跨进程恢复不误触时长闸）。
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any

from langgraph.types import Command

from appv2.infra.db import ConnectionManager
from appv2.infra.security import Actor
from appv2.runtime.budget import Budget, now_monotonic
from appv2.runtime.context import ContextBuilder
from appv2.runtime.events import EventBus
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
from appv2.tools import ToolRegistry

# ---------- RunCommand（ADR-0003 seam 的命令侧闭世界） ----------

COMMAND_ASK = "ask"
COMMAND_RESUME = "resume"
COMMAND_KINDS: frozenset[str] = frozenset({COMMAND_ASK, COMMAND_RESUME})


@dataclass(frozen=True, slots=True)
class RunCommand:
    """run 命令（ask/resume 两态闭世界——api 层只经 AgentRuntime 入命令）。"""

    kind: str
    question: str = ""
    actor: Actor | None = None
    run_id: str = ""
    choice: AskChoice | None = None

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
    ) -> None:
        self._registry = registry
        self._models = models
        self._db = db
        self._saver = saver
        self._budget = budget or Budget()
        self._builder = builder or ContextBuilder()
        self._store = RunStore(db)
        self._tasks: set[asyncio.Task[None]] = set()

    async def execute(self, command: RunCommand) -> RunHandle:
        """受理命令（立即返回 RunHandle——图在后台任务驱动，事件流实时消费）。"""
        bus = EventBus()
        if command.kind == COMMAND_ASK:
            actor = command.actor or Actor(user_id="", display="")
            run_id = new_run_id()
            await self._store.create_run(
                run_id=run_id, question=command.question, actor=actor.who
            )
            graph = build_graph(self._deps(bus), checkpointer=self._saver)
            state = self._initial_state(run_id, command.question, actor.user_id)
            config: dict[str, Any] = {"configurable": {"thread_id": run_id}}
            self._spawn(graph, state, config, bus, run_id)
            return RunHandle(run_id=run_id, stream=bus.stream())
        if command.kind == COMMAND_RESUME:
            run = await self._store.get_run(command.run_id)
            if run is None:
                raise RunNotFoundError(f"run 不存在：{command.run_id}")
            if run.status != RUN_WAITING_ASK:
                raise RunNotSuspendedError(
                    f"run 非挂起态不可 resume（status={run.status}）：{command.run_id}"
                )
            graph = build_graph(self._deps(bus), checkpointer=self._saver)
            config = {"configurable": {"thread_id": command.run_id}}
            # 段时限＋段步基线刷新（挂起等人工不计预算——恢复段重新起算两闸）。
            snapshot = await graph.aget_state(config)
            prior_steps = list((snapshot.values or {}).get("steps") or [])
            await graph.aupdate_state(
                config,
                {
                    "deadline_monotonic": now_monotonic() + self._budget.total_seconds,
                    "segment_step_base": len(prior_steps),
                },
            )
            choice = command.choice or AskChoice(value="")
            self._spawn(
                graph,
                Command(resume=choice.as_payload()),
                config,
                bus,
                command.run_id,
            )
            return RunHandle(run_id=command.run_id, stream=bus.stream())
        raise ValueError(f"未知 RunCommand：{command.kind!r}")

    # ---------- 内部位 ----------

    def _deps(self, bus: EventBus) -> LoopDeps:
        return LoopDeps(
            registry=self._registry,
            models=self._models,
            builder=self._builder,
            store=self._store,
            bus=bus,
        )

    def _initial_state(self, run_id: str, question: str, actor_id: str) -> RunState:
        started = now_monotonic()
        return RunState(
            run_id=run_id,
            question=question,
            actor=actor_id,
            status=RUN_RUNNING,
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
    ) -> None:
        task = asyncio.create_task(self._drive(graph, graph_input, config, bus, run_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _drive(
        self,
        graph: Any,
        graph_input: Any,
        config: dict[str, Any],
        bus: EventBus,
        run_id: str,
    ) -> None:
        """图驱动收口：状态落库（run 状态机四态）＋事件流收束。"""
        try:
            final = await graph.ainvoke(graph_input, config)
            await self._store.put_steps(run_id, list(final.get("steps") or []))
            if final.get("pending_ask"):
                await self._store.finish_run(run_id, status=RUN_WAITING_ASK)
            elif final.get("error"):
                await self._store.finish_run(
                    run_id, status=RUN_FAILED, error=str(final["error"])
                )
            else:
                await self._store.finish_run(
                    run_id,
                    status=RUN_COMPLETED,
                    answer=final.get("answer"),
                    manifest_digest=final.get("manifest_digest") or None,
                )
        except Exception as exc:  # 引擎/网关异常——run failed，如实留痕（不静默）
            await self._store.finish_run(run_id, status=RUN_FAILED, error=str(exc))
            bus.emit(
                "notice",
                {"type": "run_failed", "gates": [], "content": f"run 执行失败：{exc}"},
            )
        finally:
            bus.close()


class AgentRuntime:
    """命令入口（modules.md runtime 卡公开接口——api 只见此层）。"""

    def __init__(self, executor: GraphRunExecutor) -> None:
        self._executor = executor

    async def ask(self, q: AskRequest) -> RunHandle:
        """建 run，返 run_id＋事件流（specs/agent-loop.md 接口定义节）。"""
        return await self._executor.execute(
            RunCommand(kind=COMMAND_ASK, question=q.question, actor=q.actor)
        )

    async def resume(self, run_id: str, choice: AskChoice) -> RunHandle:
        """挂起 run 凭选择续跑（非挂起态/不存在＝RunNotSuspendedError/RunNotFoundError）。"""
        return await self._executor.execute(
            RunCommand(kind=COMMAND_RESUME, run_id=run_id, choice=choice)
        )
