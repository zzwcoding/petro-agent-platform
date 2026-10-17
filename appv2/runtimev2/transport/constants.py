"""transport 的七个闭世界常量族（取值真源逐族标注——见各族注记）。

真源＝`specs/transport.md` 接口定义节「闭世界常量族」段（签名以 `specs/modules.md`
`## transport` 卡为准）。本模块只落取值、不落行为：同一族在别处再建第二份＝缺陷
（「闭世界只有一个常量族」——`specs/transport.md` 风险 2 的对策；文案随集合生成，不写死条数）。

**EB4b 白话化核实（2026-10-17）**：本模块**零用户可见文案**——全部取值为帧名／块型／通知类型／
信封取值（闭世界符号），上屏文本一律落在发射方各相位的 `constants.py`（本模块只保帧形与闭世界）。
故 EB4b 对 transport **零改**（记录以免下一轮重复核查）。**2026-10-17 EB5c 补注**：块头模式族
（末族）的字面同样是**匹配模式**（程序自产块头的文本面，上屏文本仍归发射方相位）——本模块
不新增上屏文案，EB4b 核实结论不变。
"""

# ── runtime 十类事件名（取值真源 `synth/S6-事件与帧目录.md` §一；九类口径真源
# `synth/S3-口径裁决清单.md` C-05——「八类」为 `EVENT_BLACKBOX` 入列前的陈旧注记；
# 2026-10-17 EB3 D1 增第十类 `supplement`）──
# `blackbox` **必须与其他八类同列导出面**（现状 `appv2/runtime/__init__.py` 缺该符号＝
# S3 C-10／D-P9a1-09；本块收正）。
EVENT_KINDS: frozenset[str] = frozenset(
    {
        "step",
        "text",
        "tool",
        "observation",
        "ask",
        "verdict",
        "citation",
        "notice",
        "blackbox",
        # 2026-10-17 EB3 D1（交付面分层）：程序追加内容（分源块／归属块／引用块／血缘五要素）
        # 不进正文——走结构化增补面，本帧即该面的出帧形（逐字稿＝
        # `docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D1）。
        "supplement",
    }
)

# ── wire 三帧（取值真源 `synth/S6-事件与帧目录.md` §二；发射时机与载荷归 `api` 开流段，
# 本块只保帧名在闭世界内与信封形状）────────────────────────────────────────────
WIRE_FRAMES: frozenset[str] = frozenset({"session", "done", "error"})

# ── 事件名的十三值全集（＝`EVENT_KINDS ∪ WIRE_FRAMES`，行为 1 的构造期判据面）──────
_FRAME_EVENTS: frozenset[str] = EVENT_KINDS | WIRE_FRAMES

# ── supplement 帧块型闭世界四值（2026-10-17 EB3 D1；取值真源＝
# `docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D1 逐字）──────────────
# 载荷恰二键 `{block, text}`：`split`＝多来源分源列明｜`attribution`＝跨源归属｜
# `citations`＝引用清单｜`lineage`＝血缘五要素全文。**「四类块不进正文」的机器面**：
# 块型取值越界＝构造期即拒（闭世界不经裁决不许长胖）。
SUPPLEMENT_BLOCK_SPLIT = "split"
SUPPLEMENT_BLOCK_ATTRIBUTION = "attribution"
SUPPLEMENT_BLOCK_CITATIONS = "citations"
SUPPLEMENT_BLOCK_LINEAGE = "lineage"
SUPPLEMENT_BLOCKS: frozenset[str] = frozenset(
    {
        SUPPLEMENT_BLOCK_SPLIT,
        SUPPLEMENT_BLOCK_ATTRIBUTION,
        SUPPLEMENT_BLOCK_CITATIONS,
        SUPPLEMENT_BLOCK_LINEAGE,
    }
)
# 本帧载荷两键名（本块自有的定形键——发射方按名填：`{"block": …/…, "text": …}`）。
SUPPLEMENT_PAYLOAD_BLOCK_KEY = "block"
SUPPLEMENT_PAYLOAD_TEXT_KEY = "text"

# ── 通知类型二十九值（取值真源＝本规格自立·实测全集——`specs/transport.md` 接口定义节
# 逐字列全；2026-10-16 补全（流水 53-C）：B5 golden 回放 54444 帧实测越界 7 值入列）──────
# 行为 7：`notice` 载荷恰三键 `{type, gates, content}`；取值越界即拒；**取消隐式兜底**
# （旧码 `locator.notice_type` 缺省填 `"notice"`）——**缺 `type` 即拒**，不猜不填；
# **新增类型必须同批入列**（禁「白名单外偷偷发」）。
NOTICE_TYPES: frozenset[str] = frozenset(
    {
        "refused",
        "run_failed",
        "ban_exempt",
        "budget_converged",
        "clarify_capped",
        "emission_strip",
        "emission_quote_repair",
        "material_truncated",
        "unsupported_claim",
        "contradiction_split",
        "attribution_split",
        "decision_note",
        "decision_rejected",
        "chain_switch_reentry",
        "window_miss_reentry",
        "approval_gate_pending",
        "approval_recorded",
        "tool_unavailable",
        "subtask_failed",
        "subtask_refused",
        "audit_write_failed",
        "blackbox_write_failed",
        # 2026-10-16 补全（流水 53-C）：B5 回放实测越界 7 值（来源＝V1 tools/query/gate 通道）
        "window_note",
        "no_hit",
        "unbound_degrade",
        "freshness_block",
        "same_param_replay",
        "rebind",
        "schema_not_allowed",
    }
)

# ── verdict 两形（行为 6：载荷含 `status` 键 → `final`，否则 → `verify`；二值闭世界）──
_VERDICT_VERIFY = "verify"
_VERDICT_FINAL = "final"

VERDICT_SUBTYPES: frozenset[str] = frozenset({_VERDICT_VERIFY, _VERDICT_FINAL})

# ── ask 帧 kind 二值（行为 8；`AskReason.kind` → 本闭世界的映射表在
# `specs/preconditions.md` 接口定义）─────────────────────────────────────────
ASK_FRAME_KINDS: frozenset[str] = frozenset({"clarify", "external_table_approval"})

# ── 块头模式族（2026-10-17 EB5c；真源＝`specs/transport.md` 行为 17）──────────────
# 四类增补面块（`SUPPLEMENT_BLOCKS`）在**正文文本**里的块头形态族——块剥除（answering 起草面
# 与 verification 剥除拍）与「同族块头在场」判据（answering 收口幂等）**共用本族单点**：
# 两相位互不 import（R1），故单点落本块（块型闭世界的**文本面**随块型闭世界落同一处）。
#
# **加粗变体子集**：块头行经「装饰归一」（去 markdown 强调／标题记号与首尾空白，见
# `SUPPLEMENT_HEAD_DECORATIONS`）后与族中记号同形——`**引用**`／`**互不一致**` 等变体**不另
# 立字面**（同一记号即同一族；真机帧证据 `eval/results/frames/EB3-NQ-M7.json` 的 text 帧）。
# **判据两条**（`blocks.block_head_kind`）：引用／分源／归属三族取「归一后整行**恰为**记号」
# （防正文散文误伤——「引用《月报》的数据…」不作块头条）；血缘族取「行内**含**记号」
# （2026-10-17 EB3 D2 逐字判据——五要素段可在段内整段内嵌）。
#
# 取值真源＝两相位现行块头字面（`answering.constants` 的引用块／分源块／归属块头与
# `verification.constants` 的核验分列块头／血缘五要素合同键）——**相位侧改为引本族名字**
# （文本单点：同一句字面全仓只在编译面出现一次）。占位形块头（`verification.ATTRIBUTION_BLOCK_HEAD`
# 携「题眼」占位符）**不入族**（占位符不可静态匹配——登记于行为 17）。
SUPPLEMENT_HEAD_MARK_CITATIONS = "引用："          # 程序引用块头（`CITATION_BLOCK_HEAD` 的行形）
SUPPLEMENT_HEAD_MARK_CITATIONS_BARE = "引用"       # 模型变体（`**引用**` 归一后形——NQ-M7 帧形）
SUPPLEMENT_HEAD_MARK_SPLIT = "互不一致——各来源说法如下，按来源分别列出："   # answering 分源块头
SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY = "各来源说法如下，按来源分别列出："      # verification 分列块头
SUPPLEMENT_HEAD_MARK_ATTRIBUTION = "按来源分别列出（每条结论都标出它来自哪个来源）："
SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE = "② 来源表"    # 血缘要素键（行内判据）
SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING = "⑤ 收口注记"  # 血缘要素键（行内判据）

# 块型 → 块头记号族（块型取值＝`SUPPLEMENT_BLOCKS` 成员；血缘族两记号＝要素键）。
SUPPLEMENT_BLOCK_HEAD_MARKS: dict[str, tuple[str, ...]] = {
    SUPPLEMENT_BLOCK_SPLIT: (
        SUPPLEMENT_HEAD_MARK_SPLIT,
        SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY,
    ),
    SUPPLEMENT_BLOCK_ATTRIBUTION: (SUPPLEMENT_HEAD_MARK_ATTRIBUTION,),
    SUPPLEMENT_BLOCK_CITATIONS: (
        SUPPLEMENT_HEAD_MARK_CITATIONS,
        SUPPLEMENT_HEAD_MARK_CITATIONS_BARE,
    ),
    SUPPLEMENT_BLOCK_LINEAGE: (
        SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE,
        SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING,
    ),
}
# 血缘族子集（行内判据那一族——`blocks.split_block_sections` 的剥出段归属面）。
SUPPLEMENT_LINEAGE_HEAD_MARKS: tuple[str, ...] = SUPPLEMENT_BLOCK_HEAD_MARKS[
    SUPPLEMENT_BLOCK_LINEAGE
]
# **剥除面**子集（块剥除只对这两类动手）：两类的正文面都是**程序机械再生产物**——引用清单由
# 被引集确定性生成（`answering._citation_block`）、血缘五要素随观察帧全量在场（`lineage` 增补面
# 由执行面发射与核验面剥出两路承接），故正文里的同族段可整段离场且零信息损失；分源／归属两族
# **不剥**（可能承载模型逐源作答正文——只作在场判据；2026-10-17 EB5c 判断）。
SUPPLEMENT_STRIPPABLE_BLOCKS: frozenset[str] = frozenset(
    {SUPPLEMENT_BLOCK_CITATIONS, SUPPLEMENT_BLOCK_LINEAGE}
)
# 块头行装饰记号（markdown 强调／标题记号——加粗变体的归一面；`str.strip` 参数字符集）。
SUPPLEMENT_HEAD_DECORATIONS = "*#"
# 血缘族口径说明例外上限（≤2 行且携 `[n]` 引标＝单行口径说明，保留正文——EB3 D2 逐字）。
SUPPLEMENT_LINEAGE_KEEP_MAX_LINES = 2
