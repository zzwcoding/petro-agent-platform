"""domains.chat —— A1 问一问域公开出口（B2：router 只 import 本包公开名）。

98 §3.1 卡骨架拍（P1-08a）：问答编排引擎——四层流水线（安检→六路装配→裁决
→17 链分发）＋SSE 19 类事件帧＋澄清帧有界循环；三链分派缝（检索/FAQ 秒回/
图谱问答）随 P1-08b 填肉。会话料源读口 recent_qa_pairs＝B3 扫库 session_loader
注入位（P1-06 疑点 6 收口）。端点随 A1 页票（本票 SSE 主链拍）。
"""

from app.domains.chat.domain import (
    BANNED_TERMS,
    CHAIN17,
    CLARIFY_CANDIDATE_CAP,
    CLARIFY_MAX_POPUPS,
    FRAME_NAMES,
    INJECTION_PATTERNS,
    MATCHERS,
    SEAM_CHAINS,
    SEC_CHECKS,
    ChainContext,
    ChainDispatcher,
    ChainOutcome,
    ChatParamError,
    ChatRunNotFoundError,
    ChatRunStateError,
    ClarifyChoice,
    ClarifyFrame,
    FaqHitFace,
    GraphHitFace,
    IndexHitFace,
    LaneResult,
    MetricFace,
    QaBehaviorFace,
    SseEvent,
    SuggestionPool,
    SuggestionSignal,
    TermFace,
    build_caliber_clarify,
    cap_choices,
)
from app.domains.chat.service import ChatService

__all__ = [
    "BANNED_TERMS",
    "CHAIN17",
    "CLARIFY_CANDIDATE_CAP",
    "CLARIFY_MAX_POPUPS",
    "FRAME_NAMES",
    "INJECTION_PATTERNS",
    "MATCHERS",
    "SEAM_CHAINS",
    "SEC_CHECKS",
    "ChainContext",
    "ChainDispatcher",
    "ChainOutcome",
    "ChatParamError",
    "ChatRunNotFoundError",
    "ChatRunStateError",
    "ChatService",
    "ClarifyChoice",
    "ClarifyFrame",
    "FaqHitFace",
    "GraphHitFace",
    "IndexHitFace",
    "LaneResult",
    "MetricFace",
    "QaBehaviorFace",
    "SseEvent",
    "SuggestionPool",
    "SuggestionSignal",
    "TermFace",
    "build_caliber_clarify",
    "cap_choices",
]
