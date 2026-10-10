"""appv2.retrieval —— 检索引擎（V2-04；specs/modules.md retrieval 卡公开接口）。

RetrievalEngine（retrieve＋graph 两面）＝唯一公开行为面；RetrievalNeed/
RetrievalBundle/Observation＝specs/retrieval.md 接口定义节定稿 schema；
FragmentLibrary/GraphSource/Embedder＝三条可替换缝（生产装配在组合根，
测试注 InMemoryFragmentLibrary＋LocalHashEmbedder 桩）。

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
    RRF_K,
    FragmentRecord,
    GraphEdgeRecord,
    Hit,
    Observation,
    RetrievalBundle,
    RetrievalNeed,
    anchor_seat_tokens,
    build_window_note,
    is_table_rowset_question,
    supply_window,
)
from appv2.retrieval.embedder import (
    EMBED_DIM,
    Embedder,
    LocalHashEmbedder,
    RemoteEmbedder,
)
from appv2.retrieval.engine import Completer, CompletionView, RetrievalEngine
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
    "RRF_K",
    "Completer",
    "CompletionView",
    "Embedder",
    "FragmentLibrary",
    "FragmentRecord",
    "GraphEdgeRecord",
    "GraphSource",
    "Hit",
    "InMemoryFragmentLibrary",
    "LocalHashEmbedder",
    "Observation",
    "PgFragmentLibrary",
    "RemoteEmbedder",
    "RetrievalBundle",
    "RetrievalEngine",
    "RetrievalNeed",
    "anchor_seat_tokens",
    "build_window_note",
    "is_table_rowset_question",
    "supply_window",
]
