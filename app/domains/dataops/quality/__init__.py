"""domains.dataops.quality —— E2 质检台（M-05a 管理面＋M-05b 执行通道）公开出口。

B2：api 层只经本包出口取用（禁深 import 域内私有模块）。公开面＝
QualityService（编排）＋ domain 语义值对象/错误类型＋ ensure_quality_tables
（装配幂等建表——Alembic 0015 并行存活）＋ DataPlaneChannelRescanExecutor/
bind_channel_rescan（复扫通道生产适配器——M-05b，组合根专用）。
"""

from app.domains.dataops.quality.channel import (
    DataPlaneChannelRescanExecutor,
    bind_channel_rescan,
)
from app.domains.dataops.quality.domain import (
    DISTRIBUTION_OWNER,
    LANES,
    RESCAN_ACTION,
    RESCAN_GREEN_NOTE,
    FollowupReceipt,
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
    QualityTaskNotFoundError,
    QualityTaskRunningError,
    QuarantineView,
    RescanExecutor,
    RescanOutcome,
    RescanRequest,
    RuleToggleReceipt,
    RuleView,
    TaskAcceptedReceipt,
    TaskRecordView,
    TaskStatusView,
    TransitionReceipt,
    VerifyView,
)
from app.domains.dataops.quality.service import QualityService
from app.domains.dataops.quality.store import ensure_quality_tables

__all__ = [
    "DISTRIBUTION_OWNER",
    "LANES",
    "RESCAN_ACTION",
    "RESCAN_GREEN_NOTE",
    "DataPlaneChannelRescanExecutor",
    "FollowupReceipt",
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
    "QualityTaskNotFoundError",
    "QualityTaskRunningError",
    "QuarantineView",
    "RescanExecutor",
    "RescanOutcome",
    "RescanRequest",
    "RuleToggleReceipt",
    "RuleView",
    "TaskAcceptedReceipt",
    "TaskRecordView",
    "TaskStatusView",
    "TransitionReceipt",
    "VerifyView",
    "bind_channel_rescan",
    "ensure_quality_tables",
]
