"""appv2.tools —— 工具层（V2-05；specs/tools.md、specs/modules.md tools 卡）。

ToolRegistry＝agent 与世界的唯一接触面（受控行动链工具侧落位）——knowledge/
query/retrieval 三引擎包装成只读工具（semantic_query/data_query/
doc_retrieve）＋V2-31 发现工具 table_schema（白名单⑥结构卡）＋
V2-52 辅助模式发现工具 faq_lookup（faq_* 读缝注入时在册）＋V2-96 作答侧两新工具
fetch_section/fetch_report（按来源取节/取篇，只读；截断＋披露）；
`graph_query` handler 与 GraphSource/compound 件保留，但已从注册面摘除
（V2-97／D7——恒返空集回退，恢复条件见 `specs/tools.md` 摘除注记）：
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
- locator 结构化载荷槽键（`LOCATOR_PAYLOAD_KEY` 族——血缘卡五要素机读面，
  2026-10-17 EB2：`runtimev2.context` 合成口径行／`runtimev2.execution` 帧透传
  同引本处名字）；
- QueryFace/RetrievalFace 引擎缝（结构性 Protocol）＋build_tools 装配单点；
- SEMANTIC_QUERY/DATA_QUERY/DOC_RETRIEVE/GRAPH_QUERY 工具名闭世界；
- ArgsError（参数校验/装配失败）＋classify_exception（异常三分类单点）；
- ASKBACK_TIME_QUESTION/ASKBACK_TIME_CHOICES（缺参反问时间窗候选常量——经本
  包根转出供 runtimev2 消费）；
- WellRosterFace（井名录取值缝，table_schema 的 dim_well 名录段/`well` 查值
  消费）＋normalize_well_id/roster_entries/roster_lookup（RULE-PETRO-005 井号
  归一与名录比对单点——2026-10-17 流水 70）；
- subject_candidates/term_candidates（题面主体/术语候选的程序预识别——V2-82a 流水 88：
  理解相位经包根调用拼「程序预识别」推荐行；零模型零 I/O，复用 anchors 实体锚件与
  well_ids 归一单点）＋oilfield_instances/metric_requires_subject（对象歧义 ask 的两件
  程序侧素材——V2-82b 流水 88：油田实例名单与「粒度要求主体」判定；判定门本体归
  runtimev2 `clarification.subject_ask`，两侧字面真源归 runtimev2 `state.constants`）；
- fake 三假引擎＋FakeUpstreamRejection（P-006 复用件）。
"""

# askback 候选窗常量转出（真源＝appv2/query/domain.py:78-84，经本面包根供
# runtimev2 消费——守 R6，2026-10-16 流水 58）。
from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
)
from appv2.tools.anchors import (
    entity_anchor_tokens,
    inject_retrieval_anchors,
    normalize_anchor_text,
    term_anchor_tokens,
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
    FETCH_REPORT,
    FETCH_SECTION,
    GRAPH_QUERY,
    SCHEMA_PROBE,
    SEMANTIC_QUERY,
    FaqLookupFace,
    QueryFace,
    RetrievalFace,
    WellRosterFace,
    build_tools,
    faq_lookup,
    fetch_report,
    fetch_section,
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
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
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
from appv2.tools.subject_terms import (
    OILFIELD_INSTANCES_CAP,
    metric_requires_subject,
    oilfield_instances,
    subject_candidates,
    term_candidates,
)
from appv2.tools.table_scan import (
    TableScanFindings,
    extract_external_table_refs,
    scan_unapproved_tables,
)
from appv2.tools.well_ids import (
    normalize_well_id,
    roster_entries,
    roster_lookup,
)

__all__ = [
    "ALL_SCHEMA_CARDS",
    "ASKBACK_TIME_CHOICES",
    "ASKBACK_TIME_QUESTION",
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
    "FETCH_REPORT",
    "FETCH_SECTION",
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
    "LINEAGE_LIMIT_HIT_KEY",
    "LINEAGE_LIMIT_KEY",
    "LINEAGE_LIMIT_ROWS_KEY",
    "LINEAGE_PAYLOAD_KEY",
    "LOCATOR_PAYLOAD_KEY",
    "META_QUESTION_MARKERS",
    "OILFIELD_INSTANCES_CAP",
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
    "WellRosterFace",
    "ban_exempt_notice_text",
    "build_tools",
    "classify_exception",
    "dump_from_store",
    "entity_anchor_tokens",
    "extract_external_table_refs",
    "faq_lookup",
    "fetch_report",
    "fetch_section",
    "inject_retrieval_anchors",
    "is_ban_exempt",
    "judge",
    "ledger_facts",
    "metric_requires_subject",
    "normalize_anchor_text",
    "normalize_metric_name",
    "normalize_well_id",
    "oilfield_instances",
    "recall_relevant",
    "render_aliases",
    "render_cards",
    "render_ledger_rows",
    "resolve_metric_slot",
    "resolve_send_budget",
    "roster_entries",
    "roster_lookup",
    "scan_unapproved_tables",
    "subject_candidates",
    "term_anchor_tokens",
    "term_candidates",
]
