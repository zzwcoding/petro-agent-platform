"""appv2.tools —— 工具层（V2-05；specs/tools.md、specs/modules.md tools 卡）。

ToolRegistry＝agent 与世界的唯一接触面（受控行动链工具侧落位）——knowledge/
query/retrieval 三引擎包装成四个只读工具（semantic_query/data_query/
doc_retrieve/graph_query）＋V2-31 发现工具 table_schema（白名单⑥结构卡）＋
V2-52 辅助模式发现工具 faq_lookup（faq_* 读缝注入时在册）：
统一 Observation 出处链（INV-1 输入）、错误三分类
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

from appv2.tools.anchors import (
    entity_anchor_tokens,
    inject_retrieval_anchors,
    normalize_anchor_text,
)
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
    FAQ_AUX_THRESHOLD,
    FAQ_LOOKUP,
    GRAPH_QUERY,
    SCHEMA_PROBE,
    SEMANTIC_QUERY,
    FaqLookupFace,
    QueryFace,
    RetrievalFace,
    build_tools,
    faq_lookup,
    recall_relevant,
)
from appv2.tools.ledger import (
    ALL_SCHEMA_CARDS,
    RESIDENT_BLOCK_BEGIN,
    RESIDENT_BLOCK_END,
    dump_from_store,
    render_aliases,
    render_cards,
    render_ledger_rows,
)
from appv2.tools.precondition import (
    BAN_EXEMPT_QUOTE_PAIRS,
    BAN_EXEMPT_SENTENCE_BREAKS,
    CHAIN_SWITCH_HINT,
    CHAIN_SWITCH_KIND_DOMAIN,
    CHAIN_SWITCH_KIND_UNBOUND,
    FUZZY_TIME_MARKERS,
    HIT_RULE_ASK,
    HIT_RULE_BAN,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FRESHNESS_WINDOW,
    HIT_RULE_FUZZY_WINDOW,
    HIT_RULE_NONE,
    HIT_RULE_NORMALIZED_SLOT,
    HIT_RULE_SINGLE_WELL,
    HIT_RULE_UNREGISTERED_METRIC,
    HIT_RULES,
    META_QUESTION_MARKERS,
    STATE_BLOCKED_ASK,
    STATE_BLOCKED_REFUSE,
    STATE_NOTE,
    STATE_PASS,
    SUBTASK_STATES,
    BannedFact,
    LedgerFacts,
    MetricFact,
    SubtaskInput,
    Verdict,
    ban_exempt_notice_text,
    is_ban_exempt,
    judge,
    ledger_facts,
    normalize_metric_name,
    resolve_metric_slot,
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
    resolve_send_budget,
)
from appv2.tools.table_scan import (
    TableScanFindings,
    extract_external_table_refs,
    scan_unapproved_tables,
)

__all__ = [
    "ALL_SCHEMA_CARDS",
    "ASK_CLARIFY",
    "ASK_EXTERNAL_TABLE_APPROVAL",
    "ASK_KINDS",
    "BAN_EXEMPT_QUOTE_PAIRS",
    "BAN_EXEMPT_SENTENCE_BREAKS",
    "CATEGORY_ALL",
    "CATEGORY_BAD_ARGS",
    "CATEGORY_REFUSED",
    "CATEGORY_RETRYABLE",
    "CHAIN_SWITCH_HINT",
    "CHAIN_SWITCH_KIND_DOMAIN",
    "CHAIN_SWITCH_KIND_UNBOUND",
    "DATA_QUERY",
    "DOC_RETRIEVE",
    "FAQ_AUX_THRESHOLD",
    "FAQ_LOOKUP",
    "FUZZY_TIME_MARKERS",
    "GRAPH_QUERY",
    "HIT_RULES",
    "HIT_RULE_ASK",
    "HIT_RULE_BAN",
    "HIT_RULE_CHAIN_SWITCH",
    "HIT_RULE_FRESHNESS_WINDOW",
    "HIT_RULE_FUZZY_WINDOW",
    "HIT_RULE_NONE",
    "HIT_RULE_NORMALIZED_SLOT",
    "HIT_RULE_SINGLE_WELL",
    "HIT_RULE_UNREGISTERED_METRIC",
    "META_QUESTION_MARKERS",
    "RESIDENT_BLOCK_BEGIN",
    "RESIDENT_BLOCK_END",
    "SCHEMA_PROBE",
    "SEMANTIC_QUERY",
    "STATE_BLOCKED_ASK",
    "STATE_BLOCKED_REFUSE",
    "STATE_NOTE",
    "STATE_PASS",
    "STATUS_ALL",
    "STATUS_ASK",
    "STATUS_FAILED",
    "STATUS_OK",
    "SUBTASK_STATES",
    "ArgsError",
    "AskFrame",
    "BannedFact",
    "FakeKnowledgeStore",
    "FakeQueryEngine",
    "FakeRetrievalEngine",
    "FakeUpstreamRejection",
    "FaqLookupFace",
    "LedgerFacts",
    "MetricFact",
    "Observation",
    "QueryFace",
    "RetrievalFace",
    "SubtaskInput",
    "TableScanFindings",
    "Tool",
    "ToolContext",
    "ToolDescriptor",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "Verdict",
    "ban_exempt_notice_text",
    "build_tools",
    "classify_exception",
    "dump_from_store",
    "entity_anchor_tokens",
    "extract_external_table_refs",
    "faq_lookup",
    "inject_retrieval_anchors",
    "is_ban_exempt",
    "judge",
    "ledger_facts",
    "normalize_anchor_text",
    "normalize_metric_name",
    "recall_relevant",
    "render_aliases",
    "render_cards",
    "render_ledger_rows",
    "resolve_metric_slot",
    "resolve_send_budget",
    "scan_unapproved_tables",
]
