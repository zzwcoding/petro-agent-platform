"""appv2.knowledge —— V2 语义资产读面（specs/knowledge.md；tickets/v2/V2-02）。

把 sem_* 台账（指标/术语/对象/关系/族标注/别名）读成 agent 现场可消费的
Knowledge Evidence：agent 查得到、看得懂口径、知道能不能出数。

公开面（specs/modules.md knowledge 卡——KnowledgeStore 四方法＋两 schema；
依赖只许 appv2.infra 公开接口，不咬 V1 app.**、不引 query/retrieval）：
- KnowledgeStore／InMemoryKnowledgeStore（seam＋快照适配器）／PgKnowledgeStore
  （生产适配器——sem_* 直读，V2-19）；
- SemanticQuery／Evidence（接口定义节两 schema，随 V2-02 定稿）；
- KIND_*／BINDING_*／MEASURE_COLUMNS／term_expiry／term_binding_state／
  metric_binding_state（binding_state 三态判定单点——V1 冻结三绑定原样）；
- LedgerSnapshot／question_array_snapshot／glossary_aliases／
  load_relation_families（问数组台账态快照、别名投影与本体导出物族标注装载）。

只读纪律（INV-2）：本包零写路径——不产任何台账写面（增删改审沿用 V1
治理线端点）；不做缓存层（本期直读/快照读，量级允许）。
"""

from appv2.knowledge.domain import (
    BINDING_BOUND,
    BINDING_EXPIRED,
    BINDING_UNBOUND,
    KIND_ALL,
    KIND_FAMILY,
    KIND_METRIC,
    KIND_OBJECT,
    KIND_RELATION,
    KIND_TERM,
    MEASURE_COLUMNS,
    Evidence,
    SemanticQuery,
    metric_binding_state,
    term_binding_state,
    term_expiry,
)
from appv2.knowledge.pg_store import PgKnowledgeStore
from appv2.knowledge.snapshot import (
    FamilyRow,
    LedgerSnapshot,
    MetricRow,
    ObjectRow,
    RelationRow,
    TermRow,
    glossary_aliases,
    load_relation_families,
    question_array_snapshot,
)
from appv2.knowledge.store import InMemoryKnowledgeStore, KnowledgeStore

__all__ = (
    "BINDING_BOUND",
    "BINDING_EXPIRED",
    "BINDING_UNBOUND",
    "KIND_ALL",
    "KIND_FAMILY",
    "KIND_METRIC",
    "KIND_OBJECT",
    "KIND_RELATION",
    "KIND_TERM",
    "MEASURE_COLUMNS",
    "Evidence",
    "FamilyRow",
    "InMemoryKnowledgeStore",
    "KnowledgeStore",
    "LedgerSnapshot",
    "MetricRow",
    "ObjectRow",
    "PgKnowledgeStore",
    "RelationRow",
    "SemanticQuery",
    "TermRow",
    "glossary_aliases",
    "load_relation_families",
    "metric_binding_state",
    "question_array_snapshot",
    "term_binding_state",
    "term_expiry",
)
