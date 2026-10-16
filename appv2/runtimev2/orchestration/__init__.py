"""编排与执行：图装配与路由、命令受理与执行器、挂起恢复、检查点 saver 组合。

模块卡见 `specs/modules.md` 的 `## orchestration` 一节；规格见 `specs/agent-loop.md`（已定稿）；
架构图见 `docs/architecture-v3.html`。包根即公开面（卡「公开接口」节 ＋ 流水 51 卡级修正注）：

- `AgentRuntime`（卡面签名逐字）——`ask(q: AskRequest) -> RunHandle` ／
  `resume(run_id: str, choice: AskChoice) -> RunHandle`：受理三形态唯一入口；
- **受理三形状经包根 re-export 供 `api` 消费**（`AskRequest`／`AskChoice`／`RunHandle`——形状
  真源在 `state`，本块零第二定义）；
- **装配面经包根 re-export 供 `api` 消费**（流水 51 卡级修正注）：`RunExecutor`（构造／注入形：
  工具注册表 ＋ 存储口 ＋ 限额 ＋ 注入参）与 `RunCommand`／`RunEvent`（`RunCommand → 执行器 →
  RunEvent` 显式接缝）、错误族两件（`api` 据此映射 404／409）。

**框架只在本模块内部**（规格 `specs/agent-loop.md:71` 逐字）：LangGraph（含 `langchain*`）不得
渗漏出本模块（R5b）；`RunState` 是自有 dataclass、框架只当 schema 消费（无 reducer／无通道并入，
节点就地改状态）；**框架类型不出现在公开面签名上**（图／节点／checkpointer 类一律不出本包根——
`build_graph`／`LoopDeps` 是模块面私有件，测试经黑盒观测或 AST／grep 断言）。
"""

from appv2.runtimev2.orchestration.commands import (
    COMMAND_ASK,
    COMMAND_KINDS,
    COMMAND_RESUME,
    RunCommand,
    RunEvent,
)
from appv2.runtimev2.orchestration.constants import NODES
from appv2.runtimev2.orchestration.errors import (
    OrchestrationError,
    RunNotFoundError,
    RunNotSuspendedError,
)
from appv2.runtimev2.orchestration.runtime import AgentRuntime, RunExecutor, watermark_of
from appv2.runtimev2.state import AskChoice, AskRequest, RunHandle

__all__ = [
    "COMMAND_ASK",
    "COMMAND_KINDS",
    "COMMAND_RESUME",
    "NODES",
    "AgentRuntime",
    "AskChoice",
    "AskRequest",
    "OrchestrationError",
    "RunCommand",
    "RunEvent",
    "RunExecutor",
    "RunHandle",
    "RunNotFoundError",
    "RunNotSuspendedError",
    "watermark_of",
]
