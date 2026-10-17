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

from appv2.runtimev2.transport import (
    SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING,
    SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE,
    SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY,
    SUPPLEMENT_LINEAGE_KEEP_MAX_LINES,
)

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
# 血缘卡观察分型（2026-10-17 EB5c——血缘统一走增补面的取值指针）。
# 取值真源＝`appv2/tools` 血缘观察装配面与 `context` 材料面分型表同字面（本块 R6 禁引引擎，
# 故以取值指针落此、落点唯一）；血缘在场 ⇒ 增补面必有 `lineage` 块（单点见
# `rules.lineage_observation_text`）。
LINEAGE_OBSERVATION_KIND = "lineage"

# ── 文本单点（逻辑面一律引名字，零字面副本）──────────────────────────────────────

# 2026-10-17 EB3 D3：改写前缀「未找到（材料未披露）：」**退役**——真无据断言按
# `specs/answering.md` 行为 3 **删句**（无据的话不写进答案），不留前缀残句；改写留痕＝
# `RewriteRecord`（原句＋原因）＋ `verdict.rewritten` 如实计数＋ `notice` 三处（不静默）。
# 2026-10-17 EB2 D3（段头去工程腔——逐字稿＝方案 D3）：旧「多来源不一致——分源列明
# （禁止无出处调和）：」→ 友好话术（判据面语义零改：仍逐支带出处、零调和）。
SPLIT_BLOCK_HEAD = SUPPLEMENT_HEAD_MARK_SPLIT_VERIFY   # 行为 4（INV-4）
SPLIT_LINE_TEMPLATE = "[{index}] {source}：{content}"            # 分列逐支带出处
SUBJECT_SEPARATOR = "："                    # 矛盾分组 subject 切分符（真源 `recon/A2` R-A2-29）

# 归属审块（行为 5 的答案面分源列明形；真源 `recon/A2` R-A2-27／R-A2-28）
# 2026-10-17 EB2 D3（段头去工程腔）：旧「跨源归属审——分源列明（题眼锚：{anchors}；
# 禁止无出处调和）：」→ 友好话术（{anchors} 占位保持）。
# **2026-10-17 EB5c 登记**：本块头**不入块头模式族**（携 `{anchors}` 占位符＝不可静态匹配的
# 模板形；见 `specs/transport.md` 行为 17 的族外登记）——族成员只收静态记号。
ATTRIBUTION_BLOCK_HEAD = "按来源归属如下（题眼：{anchors}）："
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

# ── D3 核验豁免两类的形态判据字面（2026-10-17 EB3 D3；逐字稿＝方案 D3）────────────
# 豁免面（只豁免「贴前缀／删句」，不改写、不一并判支撑）：两类线留在正文原样。
#
# (a) 引擎披露行：行内含窗 ISO 区间 **或** 含本块披露标记之一 —— 且与材料披露行事实一致。
#     披露标记四值逐字（方案 D3 逐字「封顶/截断/LIMIT/未覆盖」）——**单值常量**逐个落此
#     （本族是**闭世界取值**，非语义词表：判据面＝行内字面在场；四值不经裁决不许长胖）。
DISCLOSURE_MARK_CEILING = "封顶"
DISCLOSURE_MARK_TRUNCATED = "截断"
DISCLOSURE_MARK_LIMIT = "LIMIT"
DISCLOSURE_MARK_UNCOVERED = "未覆盖"
DISCLOSURE_MARKS: tuple[str, ...] = (
    DISCLOSURE_MARK_CEILING,
    DISCLOSURE_MARK_TRUNCATED,
    DISCLOSURE_MARK_LIMIT,
    DISCLOSURE_MARK_UNCOVERED,
)
# 窗形（「窗 ISO 区间」）＝行内出现 ISO 日期记号（`YYYY-MM-DD` 十个字符形——形态扫描，
# 零正则）；披露事实一致面＝比对材料披露行（血缘卡载荷／引擎注记观察）的数值记号集。
ISO_DATE_LENGTH = 10
ISO_DATE_SEPARATOR = "-"
DISCLOSURE_OBSERVATION_KINDS: frozenset[str] = frozenset({"lineage", "notice"})
# (b) 组头行：行尾落格（全角「：」）或**后邻行带引标**的数据表头（含表格列记号「|」者）。
GROUP_HEAD_SUFFIX = "："
TABLE_COLUMN_MARK = "|"

# ── 血缘五要素整段的形态判据字面（2026-10-17 EB3 D2；逐字稿＝方案 D2 的特征面）────────
# 特征 ②来源表／⑤收口注记：血缘五要素合同键逐字（`② 来源表`／`⑤ 收口注记`——**取值指针**，
# 真源 `appv2/query/domain.py` `LINEAGE_KEY_SOURCE`／`LINEAGE_KEY_CLOSING`；核验块 R6 禁引引擎，
# 故落点唯一者＝块头模式族（`transport.SUPPLEMENT_HEAD_MARK_LINEAGE_*`，2026-10-17 EB5c——
# 与 answering 相位共用同一族、同一剥除单点 `transport.split_block_sections`）。整段剥入
# `lineage` 增补面；**单行口径说明（≤2 行、带 `[n]` 引标）保留在正文**——口径说明不是血缘卡。
LINEAGE_MARK_SOURCE_TABLE = SUPPLEMENT_HEAD_MARK_LINEAGE_SOURCE
LINEAGE_MARK_CLOSING = SUPPLEMENT_HEAD_MARK_LINEAGE_CLOSING
LINEAGE_KEEP_MAX_LINES = SUPPLEMENT_LINEAGE_KEEP_MAX_LINES   # 上限（≤2 行——方案 D2 逐字）

# ── 通知分型（字面指针；取值真源＝`transport.NOTICE_TYPES`——本模块不复述取值集）──

NOTICE_UNSUPPORTED_CLAIM = "unsupported_claim"      # 无据断言删除（行为 3／钉 pin-02）
NOTICE_CONTRADICTION_SPLIT = "contradiction_split"  # 矛盾分列（行为 4）
NOTICE_ATTRIBUTION_SPLIT = "attribution_split"      # 归属失败（行为 5／钉 pin-01）
NOTICE_UNSUPPORTED_CONTENT = (
    "核验步删去无据断言 {rewritten} 行（EB3 D3：真无据断言删句、不贴前缀——"
    "禁止无据断言进答案；留痕＝rewrites 逐行原句 ＋ 本计数）"
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
    "核验删去 {rewritten} 行无据断言（EB3 D3：删句不贴前缀，无据的话不写进答案）——"
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
    "在窗数据行 {obs_rows} 行、答案交付 {delivered_rows} 行（差额 {delta} 行）；"
    "缺行序号 {missing}；引标序{order}——补如实注记（不改写数值断言、不重试、不拦截）"
)
# 引标序对齐标记的两字面（注记文本用——真值取自 `rules.rowset_audit` 的对齐标记）。
ROW_NOTE_ORDER_ALIGNED = "对齐（按引擎行号连续取行）"
ROW_NOTE_ORDER_MISALIGNED = "错位（跳号／整体偏移——渲染行号与引擎行号不一致）"
# 缺行序号列空值字面（零缺行＝无序号可列）。
ROW_NOTE_MISSING_NONE = "无"

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
# 行集对账扩面两键（2026-10-17 EB5c——「渲染行数＝引擎行数 ＋ 引标连续」两判据的**机读面**）：
# `rowset_missing`＝引擎行号未被交付的序号列（升序，缺行越空越短）；`rowset_aligned`＝交付的
# 引擎行号列是否恰为引擎行号序的前 L 项（跳号／整体偏移＝错位即 False）。判据单点＝
# `rules.rowset_audit`（与 `row_note` 同批落账——注记给人读、两键给机读，同一事实两面）。
PAYLOAD_ROWSET_MISSING_KEY = "rowset_missing"
PAYLOAD_ROWSET_ALIGNED_KEY = "rowset_aligned"
