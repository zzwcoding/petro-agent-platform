"""orchestration 的常量单点：图节点名、命令两态、帧名引用面与路由意图引用面。

三条纪律：① **闭世界取值一律不复述**——帧名、事件名、意图、状态取值全部引真源常量
（`state.INTENT*`／`transport` 帧族／`state.RUN_*`），本模块只落「本块自有的名字」；
② **路由意图十值的真源在 `state.constants`**，本模块只做「意图 → 节点」的映射（路由表在
`graph._ROUTES` 一处集中）；③ **帧名不私有**——本模块发的是 `transport` 闭世界内的既有名，
取名字面只在此处出现一次（`EVENT_*`）。

**EB4b 白话化核实（2026-10-17）**：本模块**零用户可见文案**——全部取值为节点名／命令态／帧名／
payload 键名（闭世界符号与机读键），上屏文本归各相位 `constants.py`。故 EB4b 对 orchestration
**零改**（记录以免下一轮重复核查）。
"""

from appv2.runtimev2.transport import EVENT_KINDS, NOTICE_TYPES, WIRE_FRAMES

# ── 图节点名（八节点：读题一步＋四相位＋回炉发现步＋作答／核验两节点）──────────
NODE_UNDERSTAND = "understand"
NODE_CLARIFY = "clarify"
NODE_DISCOVER = "discover"
NODE_TOOLMATCH = "toolmatch"
NODE_PRECONDITION = "precondition"
NODE_BATCH = "batch"
NODE_ANSWER = "answer"
NODE_VERIFY = "verify"

NODES: frozenset[str] = frozenset(
    {
        NODE_UNDERSTAND,
        NODE_CLARIFY,
        NODE_DISCOVER,
        NODE_TOOLMATCH,
        NODE_PRECONDITION,
        NODE_BATCH,
        NODE_ANSWER,
        NODE_VERIFY,
    }
)

# ── 命令两态闭世界（`RunCommand.kind`——seam 的命令侧）───────────────────────
COMMAND_ASK = "ask"
COMMAND_RESUME = "resume"
COMMAND_KINDS: frozenset[str] = frozenset({COMMAND_ASK, COMMAND_RESUME})

NEW_RUN_PREFIX = "run-"

# ── 本块发射的帧名（字面单点；取值 ∈ `EVENT_KINDS ∪ WIRE_FRAMES`，本模块不扩闭世界）──
EVENT_STEP = "step"
EVENT_ASK = "ask"
EVENT_VERDICT = "verdict"
EVENT_BLACKBOX = "blackbox"
EVENT_NOTICE = "notice"
EVENT_TEXT = "text"  # 直答旁路收口后的交付正文帧（见 `PAYLOAD_TEXT_CONTENT_KEY` 注）
# 增补面帧（2026-10-17 EB3 D1——程序追加内容不进正文，走结构化增补面）；载荷形与块型闭世界
# 归 `transport`（恰二键 `{block, text}`＋`SUPPLEMENT_BLOCKS` 四值），本处只作帧名字面单点。
EVENT_SUPPLEMENT = "supplement"
# text 帧载荷键（真源 `synth/S6-事件与帧目录.md` §一 text 行＝`{content[, kind]}`；本处只取
# `content`——答案正文帧**不带 kind**，与 `answering` 起草段的发射形一致（语义单点在那个键上）。
PAYLOAD_TEXT_CONTENT_KEY = "content"
# 直答旁路定型值指针（`state.draft_kind`）：真源＝`bookkeeping.constants.DRAFT_KIND_DIRECT`
# （`specs/bookkeeping.md` 行为 12／14 逐字 `draft_kind="direct"`）——字面单点在该块，本模块只作
# 取值指针、不复述语义（同 `NOTICE_*` 的引用法）。
DRAFT_KIND_DIRECT = "direct"
# ── 本块发射的通知类型（取值真源＝`transport.NOTICE_TYPES`，本模块只取名不扩闭世界）──
NOTICE_RUN_FAILED = "run_failed"
NOTICE_REFUSED = "refused"  # 拒答分型（V1 遗留值——V2 侧拒答收口判据取 NOTICE_SUBTASK_REFUSED）
NOTICE_SUBTASK_REFUSED = "subtask_refused"  # 子问题闸拒（V2 拒答机读分型面）
NOTICE_BAN_EXEMPT = "ban_exempt"  # 禁用词豁免留痕位（V2 待产位——触发源归入口闸族）
NOTICE_AUDIT_WRITE_FAILED = "audit_write_failed"  # 审计写口异常如实出流（不静默）
NOTICE_BLACKBOX_WRITE_FAILED = "blackbox_write_failed"  # 黑匣子写口异常如实出流

# ── 步帧载荷三键（真源 `synth/S6-事件与帧目录.md` §一 step 行；键集归发射方）──────
PAYLOAD_STEP_KEY = "step"
PAYLOAD_SEQ_KEY = "seq"
PAYLOAD_TITLE_KEY = "title"
# 收口 `verdict` 帧的判形键（`transport` 行为 6：含 `status` 键 → `final` 形）
PAYLOAD_STATUS_KEY = "status"

# ── 挂起帧投影键（`state.pending_ask`；形状真源 `synth/S6` §一 ask 行）──────────
ASK_KEY_KIND = "kind"
ASK_KEY_PROMPT = "prompt"
ASK_KEY_OPTIONS = "options"
ASK_KEY_DETAIL = "detail"
ASK_KEY_APPROVAL_ID = "approval_id"

MANIFEST_DIGEST_CHARS = 16  # 收口摘要面取哈希前 16 位（非闭世界，只截显示长度）


def assert_frame_names() -> None:
    """自守：本模块引用的帧名与通知类型字面必须落在 `transport` 闭世界内（防私扩）。"""
    for name in (
        EVENT_STEP,
        EVENT_ASK,
        EVENT_VERDICT,
        EVENT_BLACKBOX,
        EVENT_NOTICE,
        EVENT_TEXT,
        EVENT_SUPPLEMENT,
    ):
        if name not in EVENT_KINDS:
            raise ValueError(f"帧名越界（不在 transport.EVENT_KINDS 内）：{name!r}")
    if EVENT_NOTICE not in EVENT_KINDS or not WIRE_FRAMES:
        raise ValueError("transport 帧族常量未就绪（闭世界引用面异常）")
    for notice_type in (
        NOTICE_RUN_FAILED,
        NOTICE_REFUSED,
        NOTICE_SUBTASK_REFUSED,
        NOTICE_BAN_EXEMPT,
        NOTICE_AUDIT_WRITE_FAILED,
        NOTICE_BLACKBOX_WRITE_FAILED,
    ):
        if notice_type not in NOTICE_TYPES:
            raise ValueError(f"通知类型越界（不在 transport.NOTICE_TYPES 内）：{notice_type!r}")
