"""编排与执行：图装配与路由、命令受理与执行器、挂起恢复、检查点 saver 组合。

模块卡见 `specs/modules.md` 的 `## orchestration` 一节；规格见 `specs/agent-loop.md`（已定稿）；
架构图见 `docs/architecture-v3.html`。包根即公开面（卡「公开接口」节 ＋ 流水 51 卡级修正注）：

- `AgentRuntime`（卡面签名逐字）——`ask(q: AskRequest) -> RunHandle` ／
  `resume(run_id: str, choice: AskChoice) -> RunHandle`：受理三形态唯一入口；
- **受理三形状经包根 re-export 供 `api` 消费**（`AskRequest`／`AskChoice`／`RunHandle`——形状
  真源在 `state`，本块零第二定义）；
- **装配面经包根 re-export 供 `api` 消费**（流水 51 卡级修正注；清单逐名见下）：`RunExecutor`
  （构造／注入形：工具注册表 ＋ 存储口 ＋ 限额 ＋ 检查点 saver ＋ 相位注入参
  〔`watermark`／`data_wells`／`guide_text`——编排只持有并下传，装配面归
  `api` 组合根〕）＋ `RunCommand`／
  `RunEvent`（`RunCommand → 执行器 → RunEvent` 显式接缝）＋错误族两件（`api` 据此映射 404／409）
  ＋ `Budget`（限额参数表——`api` 装配构造注入件用）。**真源块注（防一头两认）**：`AskRequest`／
  `AskChoice`／`RunHandle`／`Budget` 的形状真源＝`state`（本块只 re-export、零第二定义）；
  `RunExecutor`／`RunCommand`／`RunEvent`／错误族＝本块自有件；**模型 completer 注入缝
  （`set_completer`／`ScriptedCompleter`）真源＝`gateway_adapter`**——该缝**不在本包根复述**
  （`api` 装配直接取 `gateway_adapter` 包根，避免同一缝两处名字）；**检查点 saver 同理不出本包根**
  （见末段）。

**框架只在本模块内部**（规格 `specs/agent-loop.md:71` 逐字）：LangGraph（含 `langchain*`）不得
渗漏出本模块（R5b）；`RunState` 是自有 dataclass、框架只当 schema 消费（无 reducer／无通道并入，
节点就地改状态）；**框架类型不出现在公开面签名上**（图／节点／checkpointer 类一律不出本包根——
`build_graph`／`LoopDeps` 是模块面私有件，测试经黑盒观测或 AST／grep 断言）。
**检查点 saver 组合**（卡职责行本块专责）＝`checkpointer.PgCheckpointer`（`BaseCheckpointSaver`
一族只活本模块、**组合 `persistence` 的框架无关行级口、不直连表**）——由 `RunExecutor` 内部构造
（装配点可注入替身），故框架类型**零出口**；其行落在 `persistence` 的 `agent_v2_checkpoint*` 三表
（前缀隔离，与 V1 表共存——规格「依赖与风险」）。

**审计接线（H3）**：五处留痕（受理／三态收口／拒答收口／外表审批决定／禁用词豁免）经
`persistence.audit`（唯一写口＝`security.audit`，B12）落责任账；**action 闭世界七值**的唯一口径表
＝`audit.AUDIT_PLACES`（本块零字面量、不写类数）；身份解析只经 `infra.security.resolve_actor`
（本块唯一消费点＝`audit.who_of`／`who_of_id`）。**装配点义务**：审计写口须由组合根经
`persistence.configure_audit_sink` 注入（真件＝`security.audit` 桥）；未注入＝留痕缺口，本块以
`audit_write_failed` 通知如实出流（不静默、不翻盘 run 终态）。
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
from appv2.runtimev2.state import AskChoice, AskRequest, Budget, RunHandle

__all__ = [
    "COMMAND_ASK",
    "COMMAND_KINDS",
    "COMMAND_RESUME",
    "NODES",
    "AgentRuntime",
    "AskChoice",
    "AskRequest",
    "Budget",
    "OrchestrationError",
    "RunCommand",
    "RunEvent",
    "RunExecutor",
    "RunHandle",
    "RunNotFoundError",
    "RunNotSuspendedError",
    "watermark_of",
]
