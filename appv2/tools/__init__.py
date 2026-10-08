"""appv2.tools —— 工具层（V2-05；specs/tools.md、specs/modules.md tools 卡）。

ToolRegistry＝agent 与世界的唯一接触面（受控行动链工具侧落位）——knowledge/
query/retrieval 三引擎包装成四个只读工具（semantic_query/data_query/
doc_retrieve/graph_query）：统一 Observation 出处链（INV-1 输入）、错误三分类
（retryable|bad_args|refused）、ASK 帧形态（clarify|external_table_approval）；
data_query 内部先经 query.validate（不过＝failed(bad_args, 校验理由)，引擎零
执行）。

边界（specs/modules.md 边界规则）：依赖只许 appv2.knowledge/query/retrieval
公开接口＋appv2.infra；不 import app.**／runtime（importlinter V2 契约在案）；
本包零 LLM 调用（精排/嵌入归引擎缝——B6 出口已在引擎内收口，工具层纯转发）。

INV-2（工具层落点）：全部工具 readonly=True 且零写副作用——registry 拒绝注册
readonly!=True 的工具，公开面仅 register/descriptors/call；假引擎 adapter
（fake 模块）供 P-006 runtime 票测试复用。

公开面（specs/modules.md tools 卡＋specs/tools.md 接口定义节）：
- ToolRegistry（register/descriptors/call）＋Tool（注册项）；
- ToolDescriptor/ToolContext/ToolResult/AskFrame 四 schema（票面点名随本票
  定稿）＋ToolError/Observation 伴生件＋status/category/ask kind 闭世界常量；
- QueryFace/RetrievalFace 引擎缝（结构性 Protocol）＋build_tools 装配单点；
- SEMANTIC_QUERY/DATA_QUERY/DOC_RETRIEVE/GRAPH_QUERY 工具名闭世界；
- ArgsError（参数校验/装配失败）＋classify_exception（异常三分类单点）；
- fake 三假引擎＋FakeUpstreamRejection（P-006 复用件）。
"""

from appv2.tools.argscheck import ArgsError
from appv2.tools.fake import (
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    FakeUpstreamRejection,
)
from appv2.tools.handlers import (
    DATA_QUERY,
    DOC_RETRIEVE,
    GRAPH_QUERY,
    SEMANTIC_QUERY,
    QueryFace,
    RetrievalFace,
    build_tools,
)
from appv2.tools.registry import ToolRegistry, classify_exception
from appv2.tools.schema import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    ASK_KINDS,
    CATEGORY_ALL,
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    CATEGORY_RETRYABLE,
    STATUS_ALL,
    STATUS_ASK,
    STATUS_FAILED,
    STATUS_OK,
    AskFrame,
    Observation,
    Tool,
    ToolContext,
    ToolDescriptor,
    ToolError,
    ToolResult,
)

__all__ = [
    "ASK_CLARIFY",
    "ASK_EXTERNAL_TABLE_APPROVAL",
    "ASK_KINDS",
    "CATEGORY_ALL",
    "CATEGORY_BAD_ARGS",
    "CATEGORY_REFUSED",
    "CATEGORY_RETRYABLE",
    "DATA_QUERY",
    "DOC_RETRIEVE",
    "GRAPH_QUERY",
    "SEMANTIC_QUERY",
    "STATUS_ALL",
    "STATUS_ASK",
    "STATUS_FAILED",
    "STATUS_OK",
    "ArgsError",
    "AskFrame",
    "FakeKnowledgeStore",
    "FakeQueryEngine",
    "FakeRetrievalEngine",
    "FakeUpstreamRejection",
    "Observation",
    "QueryFace",
    "RetrievalFace",
    "Tool",
    "ToolContext",
    "ToolDescriptor",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "build_tools",
    "classify_exception",
]
