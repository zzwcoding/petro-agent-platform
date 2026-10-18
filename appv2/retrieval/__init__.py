"""appv2.retrieval —— 检索引擎（V2-04；specs/modules.md retrieval 卡公开接口）。

RetrievalEngine（retrieve＋graph 两面）＝唯一公开行为面；RetrievalNeed/
RetrievalBundle/Observation＝specs/retrieval.md 接口定义节定稿 schema；
FragmentLibrary/GraphSource/Embedder＝三条可替换缝（生产装配在组合根，
测试注 InMemoryFragmentLibrary＋LocalHashEmbedder 桩）。

索引富化面（V2-47 R1b）：context_prefix/enriched_index_text（切片上下文
前缀——索引期富化纯语义）、enrich_index（富化编排——切片重嵌＋节级摘要）、
EnrichedFragmentLibrary（在线消费装配读面）、EnrichStore/PgEnrichStore/
InMemoryEnrichStore（富化索引存储缝三形）、ensure_enrich_tables（幂等建表
——与 Alembic 0023 双轨）。

边界：本包依赖只许 appv2.infra（embedder.RemoteEmbedder 消费 llm_client
.embeddings——B6）；不 import app.**／knowledge/query（V2 引擎互禁——
importlinter 在案）。
"""

from appv2.retrieval.domain import (
    FAMILY_ALL,
    FAMILY_BLANK,
    FAMILY_COMPLETION,
    FAMILY_DYNAMIC,
    FAMILY_MONTHLY,
    FETCH_TRUNCATION_MARK,
    NODE_SECTION_SUMMARY,
    NODE_SLICE,
    NOTE_FETCH_REPORT_SENT,
    NOTE_FETCH_SECTION_MISSING,
    NOTE_FETCH_SECTION_SENT,
    NOTE_FETCH_TRUNCATED,
    NOTE_MISSING_SOURCES,
    QUESTION_BLOCK_TYPE,
    RRF_K,
    FragmentRecord,
    GraphEdgeRecord,
    Hit,
    Observation,
    RetrievalBundle,
    RetrievalNeed,
    anchor_seat_tokens,
    context_prefix,
    enriched_index_text,
    is_table_rowset_question,
    promote_subject_hits,
    section_root,
    source_diversify,
    summary_node_id,
    supply_window,
)
from appv2.retrieval.embedder import (
    EMBED_DIM,
    Embedder,
    EmbedUsage,
    LocalHashEmbedder,
    RemoteEmbedder,
)
from appv2.retrieval.engine import Completer, CompletionView, RetrievalEngine
from appv2.retrieval.enrich import (
    SUMMARY_MIN_COVER,
    EnrichedFragmentLibrary,
    EnrichLedger,
    EnrichStore,
    InMemoryEnrichStore,
    SectionCluster,
    SliceOverlay,
    SummaryNode,
    build_summary_text,
    cluster_sections,
    enrich_index,
)
from appv2.retrieval.pg_enrich import PgEnrichStore, ensure_enrich_tables
from appv2.retrieval.pg_source import PgFragmentLibrary
from appv2.retrieval.source import (
    FragmentLibrary,
    GraphSource,
    InMemoryFragmentLibrary,
)

__all__ = [
    "EMBED_DIM",
    "FAMILY_ALL",
    "FAMILY_BLANK",
    "FAMILY_COMPLETION",
    "FAMILY_DYNAMIC",
    "FAMILY_MONTHLY",
    "FETCH_TRUNCATION_MARK",
    "NODE_SECTION_SUMMARY",
    "NODE_SLICE",
    "NOTE_FETCH_REPORT_SENT",
    "NOTE_FETCH_SECTION_MISSING",
    "NOTE_FETCH_SECTION_SENT",
    "NOTE_FETCH_TRUNCATED",
    "NOTE_MISSING_SOURCES",
    "QUESTION_BLOCK_TYPE",
    "RRF_K",
    "SUMMARY_MIN_COVER",
    "Completer",
    "CompletionView",
    "EmbedUsage",
    "Embedder",
    "EnrichLedger",
    "EnrichStore",
    "EnrichedFragmentLibrary",
    "FragmentLibrary",
    "FragmentRecord",
    "GraphEdgeRecord",
    "GraphSource",
    "Hit",
    "InMemoryEnrichStore",
    "InMemoryFragmentLibrary",
    "LocalHashEmbedder",
    "Observation",
    "PgEnrichStore",
    "PgFragmentLibrary",
    "RemoteEmbedder",
    "RetrievalBundle",
    "RetrievalEngine",
    "RetrievalNeed",
    "SectionCluster",
    "SliceOverlay",
    "SummaryNode",
    "anchor_seat_tokens",
    "build_summary_text",
    "cluster_sections",
    "context_prefix",
    "enrich_index",
    "enriched_index_text",
    "ensure_enrich_tables",
    "is_table_rowset_question",
    "promote_subject_hits",
    "section_root",
    "source_diversify",
    "summary_node_id",
    "supply_window",
]
