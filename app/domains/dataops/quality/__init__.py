"""domains.dataops.quality —— E2 质检台管理面（M-05a）公开出口。

B2：api 层只经本包出口取用（禁深 import 域内私有模块）。公开面＝
QualityService（编排）＋ domain 语义值对象/错误类型＋ ensure_quality_tables
（装配幂等建表——Alembic 0015 并行存活）。
"""

from app.domains.dataops.quality.domain import (
    LANES,
    RESCAN_ACTION,
    RESCAN_GREEN_NOTE,
    FreshnessView,
    HitReceipt,
    IssueListPage,
    IssueView,
    QualityCloseBlockedError,
    QualityIssueNotFoundError,
    QualityIssueStateError,
    QualityParamError,
    QualityRuleNotFoundError,
    QualityTaskChannelDeferredError,
    QuarantineView,
    RescanExecutor,
    RescanOutcome,
    RescanRequest,
    RuleToggleReceipt,
    RuleView,
    TransitionReceipt,
    VerifyView,
)
from app.domains.dataops.quality.service import QualityService
from app.domains.dataops.quality.store import ensure_quality_tables

__all__ = [
    "LANES",
    "RESCAN_ACTION",
    "RESCAN_GREEN_NOTE",
    "FreshnessView",
    "HitReceipt",
    "IssueListPage",
    "IssueView",
    "QualityCloseBlockedError",
    "QualityIssueNotFoundError",
    "QualityIssueStateError",
    "QualityParamError",
    "QualityRuleNotFoundError",
    "QualityService",
    "QualityTaskChannelDeferredError",
    "QuarantineView",
    "RescanExecutor",
    "RescanOutcome",
    "RescanRequest",
    "RuleToggleReceipt",
    "RuleView",
    "TransitionReceipt",
    "VerifyView",
    "ensure_quality_tables",
]
