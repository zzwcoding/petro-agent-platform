"""domains.semantics —— 语义台账权威源公开出口（B2/B11：只许 import 本包公开名）。

98 §3.7 卡：四本账纯读面＋slots 枢纽＋唯一汇入写口（apply_definition_merge/
rollback_to 随 governance 批）＋本体仓同步口 sync_from_ontology_repo（本票落）。
读端点随 C1 页票（阶段 1）——本包当前公开面＝同步口＋剥法单点＋投影异常族。
"""

from app.domains.semantics.domain import (
    SCHEMA_VERSION_PIN,
    OntologyDriftError,
    OntologySchemaUnsupported,
    SyncReport,
    metric_grain_display,
    metric_slot_name,
    registered_items,
    term_expiry,
)
from app.domains.semantics.service import SemanticsService

__all__ = [
    "SCHEMA_VERSION_PIN",
    "OntologyDriftError",
    "OntologySchemaUnsupported",
    "SemanticsService",
    "SyncReport",
    "metric_grain_display",
    "metric_slot_name",
    "registered_items",
    "term_expiry",
]
