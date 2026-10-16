"""orchestration 的常量单点：图节点名、命令两态、帧名引用面与路由意图引用面。

三条纪律：① **闭世界取值一律不复述**——帧名、事件名、意图、状态取值全部引真源常量
（`state.INTENT*`／`transport` 帧族／`state.RUN_*`），本模块只落「本块自有的名字」；
② **路由意图十值的真源在 `state.constants`**，本模块只做「意图 → 节点」的映射（路由表在
`graph._ROUTES` 一处集中）；③ **帧名不私有**——本模块发的是 `transport` 闭世界内的既有名，
取名字面只在此处出现一次（`EVENT_*`）。
"""

from appv2.runtimev2.transport import EVENT_KINDS, WIRE_FRAMES

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
NOTICE_RUN_FAILED = "run_failed"

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
    """自守：本模块引用的帧名字面必须落在 `transport` 闭世界内（防私扩帧名）。"""
    for name in (EVENT_STEP, EVENT_ASK, EVENT_VERDICT, EVENT_BLACKBOX, EVENT_NOTICE):
        if name not in EVENT_KINDS:
            raise ValueError(f"帧名越界（不在 transport.EVENT_KINDS 内）：{name!r}")
    if EVENT_NOTICE not in EVENT_KINDS or not WIRE_FRAMES:
        raise ValueError("transport 帧族常量未就绪（闭世界引用面异常）")
