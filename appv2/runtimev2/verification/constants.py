"""verification 的常量单点：闭世界取值 ＋ 文本单点 ＋ 帧名／载荷键名（逐条注真源）。

真源＝`specs/verification.md`（接口定义节 :32–:51 两处闭世界；行为约定节 :71–:81；「不降级与
静默禁令」节 :83–:87）＋`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（核验规则与归属审
真源——carrier 字面 R-A2-11、归属审辖域 R-A2-26、矛盾池排除面 R-A2-30）＋`synth/S6-事件与帧目录.md`
§一（`verdict`／`notice` 帧行）。

- **闭世界取值引真源、不复述**：通知分型（`NOTICE_*`）是字面指针——取值真源＝
  `transport.NOTICE_TYPES`（本模块不私扩该闭世界，写入面把守）；
- **文本单点**：改写前缀、分列块与归属审块的全部话术只在本模块出现一次（逻辑面零字面表）；
- **闭世界常量**：`REWRITE_REASONS`（两值）与 `CARRIER_KINDS`／`ATTRIBUTION_CARRIER_KINDS`／
  `CONTRADICTION_EXCLUDED_KINDS`／`ROWSET_OBSERVATION_KINDS` 四族——形态值集，非语义词表。
"""

from __future__ import annotations

from typing import Literal

# ── 相位标记与步面 ─────────────────────────────────────────────────────────────

PHASE = "verify"  # 本块相位标记（步 payload 的 `phase` 值）

# ── 改写原因闭世界（`specs/verification.md:47／:54` 逐字两值——越界即判失败）────────

RewriteReason = Literal["no_material", "conflict"]
REWRITE_NO_MATERIAL: RewriteReason = "no_material"  # 无材料
REWRITE_CONFLICT: RewriteReason = "conflict"        # 矛盾
REWRITE_REASONS: frozenset[str] = frozenset({REWRITE_NO_MATERIAL, REWRITE_CONFLICT})

# ── 缺口闭世界（复用 `answering` 口径；核验侧只产 `unverified`——`specs/verification.md:49／:55`）

GapKind = Literal["refused", "missing", "unverified"]
GAP_UNVERIFIED: GapKind = "unverified"

# ── 承载豁免域（行为 2；真源 `recon/A2` R-A2-11 字面 `agg_row`／`lineage`／`fragment`——
#    权威承载不做「全数值复述」：任一数值重叠即支撑、零重叠照改）────────────────────

CARRIER_KINDS: frozenset[str] = frozenset({"agg_row", "lineage", "fragment"})

# ── 归属审辖域（行为 5；真源 `recon/A2` R-A2-26——只辖被引**检索片段**
#    `fragment`／`graph`；数据链行级与元信息不入辖域＝形态值集判定）──────────────────

ATTRIBUTION_CARRIER_KINDS: frozenset[str] = frozenset({"fragment", "graph"})
ATTRIBUTION_LIST_CAP = 4  # 在窗未引对齐支列前 4 支（真源 `recon/A2` R-A2-27）

# ── 矛盾池排除面（行为 4；真源 `recon/A2` R-A2-30——行级时序事实与元信息不入跨源矛盾池）

CONTRADICTION_EXCLUDED_KINDS: frozenset[str] = frozenset({"agg_row", "lineage", "notice"})

# ── 行集对账面（行为 11；数据链行集承载＝`locator.kind ∈` 本族——形态值集判定，
#    与 `execution.ROWSET_OBSERVATION_KINDS` 同形（相位互不 import，各留一份字面；
#    真源 `appv2/tools/handlers.py` 的权威表行观察）──────────────────────────────

ROWSET_OBSERVATION_KINDS: frozenset[str] = frozenset({"agg_row"})

# ── 文本单点（逻辑面一律引名字，零字面副本）──────────────────────────────────────

REWRITE_PREFIX = "未找到（材料未披露）："   # INV-1 前缀（行为 3；只挂无据行——钉 pin-11）
SPLIT_BLOCK_HEAD = "多来源不一致——分源列明（禁止无出处调和）："   # 行为 4（INV-4）
SPLIT_LINE_TEMPLATE = "[{index}] {source}：{content}"            # 分列逐支带出处
SUBJECT_SEPARATOR = "："                    # 矛盾分组 subject 切分符（真源 `recon/A2` R-A2-29）

# 归属审块（行为 5 的答案面分源列明形；真源 `recon/A2` R-A2-27／R-A2-28）
ATTRIBUTION_BLOCK_HEAD = "跨源归属审——分源列明（题眼锚：{anchors}；禁止无出处调和）："
ATTRIBUTION_ALIGNED_HEAD = "对齐题眼锚："
ATTRIBUTION_UNCITED_HEAD = "对齐题眼锚的材料（在窗未进答案引用——按出处核对）："
ATTRIBUTION_UNCITED_MORE = "……另 {rest} 支对齐材料从略（按出处核对）。"
ATTRIBUTION_NO_ALIGNED = (
    "窗内无对齐题眼锚（{anchors}）的材料——所引均为跨源材料，"
    "如实列明，不作题眼归属断言。"
)
ATTRIBUTION_CROSSED_HEAD = (
    "跨源引用（引标源与题眼锚不一致——按出处如实区分，不得并入题眼断言）："
)
ATTRIBUTION_LINE_TEMPLATE = "[{index}] {source}：{content}"

# ── 通知分型（字面指针；取值真源＝`transport.NOTICE_TYPES`——本模块不复述取值集）──

NOTICE_UNSUPPORTED_CLAIM = "unsupported_claim"      # 无据断言改写（行为 3／钉 pin-02）
NOTICE_CONTRADICTION_SPLIT = "contradiction_split"  # 矛盾分列（行为 4）
NOTICE_ATTRIBUTION_SPLIT = "attribution_split"      # 归属失败（行为 5／钉 pin-01）
NOTICE_UNSUPPORTED_CONTENT = (
    "核验步改写无据断言 {rewritten} 行（INV-1——禁止无据断言进答案）"
)
NOTICE_CONTRADICTION_CONTENT = (
    "多来源不一致——答案分源列明（INV-4——禁止无出处调和）"
)
NOTICE_ATTRIBUTION_CONTENT = (
    "跨源归属审（V2-50）：答案被引检索片段 {indices} 的引标源与题眼锚（{anchors}）不一致"
    "——答案面分源列明（跨源引用按出处如实区分）"
)

# ── 步面文本与机读注记（行为 6／11；「不降级与静默禁令」节）────────────────────────

STEP_TITLE_TEMPLATE = "核验：支撑 {supported}｜改写 {rewritten}｜分源 {split}"
SPLIT_YES = "是"
SPLIT_NO = "否"

GAP_REWRITE_REASON = (
    "核验改写 {rewritten} 行无据断言（改写成「未找到（材料未披露）」）——"
    "核验侧无据残留（行为 9：ok=False 才回炉）"
)
GAP_ATTRIBUTION_REASON = (
    "题眼锚归属对不上：被引检索片段 {indices} 与题眼锚（{anchors}）不一致"
    "——该情形如实写进缺口（行为 5）"
)
GAP_FAIL_CLOSED_REASON = (
    "核验器自身抛错（fail-closed）：{error}——不判 Verdict.ok=True，由编排承接"
)
ROW_NOTE_TEMPLATE = (
    "在窗数据行 {obs_rows} 行、答案交付 {delivered_rows} 行（差额 {delta} 行）"
    "且答案面无行集声明——补如实注记（不改写数值断言、不重试、不拦截）"
)

# ── 帧名（帧面上界真源＝`transport`；此处只作发射点字面）──────────────────────────

EVENT_VERDICT = "verdict"  # 核验裁决帧（`specs/verification.md` 行为 10；批次落定归 orchestration）
EVENT_NOTICE = "notice"    # 通知帧（恰三键——`transport` 定形载荷）

# ── 步 payload 键名（行为 11 ＋「不降级与静默禁令」节逐字六个计数键 ＋ 本块机读注记）──

PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_SUPPORTED_KEY = "supported"
PAYLOAD_REWRITTEN_KEY = "rewritten"
PAYLOAD_SPLIT_KEY = "split"
PAYLOAD_CITED_KEY = "cited"
PAYLOAD_DELIVERED_ROWS_KEY = "delivered_rows"
PAYLOAD_OBS_ROWS_KEY = "obs_rows"
PAYLOAD_ATTRIBUTION_KEY = "attribution"
PAYLOAD_OK_KEY = "ok"
PAYLOAD_REWRITES_KEY = "rewrites"
PAYLOAD_REWRITE_LINE_KEY = "line"
PAYLOAD_REWRITE_REASON_KEY = "reason"
PAYLOAD_GAPS_KEY = "gaps"
PAYLOAD_GAP_KIND_KEY = "kind"
PAYLOAD_GAP_SUBTASK_KEY = "subtask_id"
PAYLOAD_GAP_REASON_KEY = "reason"
PAYLOAD_ROW_NOTE_KEY = "row_note"
