"""verification 的常量单点：闭世界取值 ＋ 文本单点 ＋ 帧名／载荷键名（逐条注真源）。

真源＝`specs/verification.md`（接口定义节 :32–:51 两处闭世界；行为约定节 :71–:81；「不降级与
静默禁令」节 :83–:87）＋`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（核验规则与归属审
真源——carrier 字面 R-A2-11、归属审辖域 R-A2-26、矛盾池排除面 R-A2-30）＋`synth/S6-事件与帧目录.md`
§一（`verdict`／`notice` 帧行）。

- **闭世界取值引真源、不复述**：通知分型（`NOTICE_*`）是字面指针——取值真源＝
  `transport.NOTICE_TYPES`（本模块不私扩该闭世界，写入面把守）；
- **文本单点**：改写前缀、分列块与归属审块的全部话术只在本模块出现一次（逻辑面零字面表）；
- **闭世界常量**：`REWRITE_REASONS`（两值）与 `CARRIER_KINDS`／`ATTRIBUTION_CARRIER_KINDS`／
  `CONTRADICTION_EXCLUDED_KINDS`／`ROWSET_OBSERVATION_KINDS`／`CALIBER_KINDS` 五族——形态值集，
  非语义词表。
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

# ── 核验动作档位（2026-10-18 V2-116——配置单点，环境变量 `VERIFY_ACTION`）───────────────
# 真源＝`tickets/v2/V2-116-校对员三档开关.md`（含末尾「Kimi 评审修正」）＋`specs/verification.md`
# 行为 14。四档语义：
# - `off`：完全跳过逐行核验（不检测、不改写）——交付＝草稿逐字；
# - `observe`：照常检测（判定逻辑零改）但**不删任何行**——检出项入 step payload
#   `intended_rewrites`（每条含原句 `line` 与 `reason`）＋ `verify_mode`；
# - `repair`：接 V2-115 回炉口；V2-115 未落地时等同 `observe` 并记 `verify_mode="repair-fallback"`；
# - `delete`：旧行为（无据断言整行离场——仅供既有单测显式指定／缺省保既有行为）。
# **缺省档＝`delete`**（评审修正 1：保既有 ~34 例零回退；`observe` 另立新测）。env 读点唯一
# （`core._verify_mode`，先例 `gateway_adapter.eval_clock.frozen_date`）；未设／空串＝缺省档，
# 闭世界外取值＝fail-fast 抛错（不静默回落）。
VERIFY_ACTION_ENV = "VERIFY_ACTION"
VERIFY_MODE_OFF = "off"
VERIFY_MODE_OBSERVE = "observe"
VERIFY_MODE_REPAIR = "repair"
VERIFY_MODE_DELETE = "delete"
VERIFY_MODES: frozenset[str] = frozenset(
    {VERIFY_MODE_OFF, VERIFY_MODE_OBSERVE, VERIFY_MODE_REPAIR, VERIFY_MODE_DELETE}
)
VERIFY_MODE_DEFAULT = VERIFY_MODE_DELETE
# `repair` 档的前置未落地时的标注值（V2-115 未落地 ⇒ 等同 observe；本值只作 `verify_mode` 标注，
# 不入 `VERIFY_MODES` 闭世界——它不是可选档，是 `repair` 档的如实降级标注）。
VERIFY_MODE_REPAIR_FALLBACK = "repair-fallback"

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

# ── 口径卡／台账卡记号面（2026-10-18 V2-105——**生产实点五 kind**；真源
#    `appv2/knowledge/domain.py:28-32` 的 `KIND_ALL`，本块 R6 禁直引引擎故以同值字面落此）──
# 台账／口径类观察（`metric`／`term`／`object`／`relation`／`family`）的**记号面只取口径数值**：
# 册号／节号形（文档结构记号 `§` 紧邻的数）不入数值断言面。真机证据＝EB11 `Q27`（
# `eval/suite-147/results/EB11-归因.md:83`）：唯一观察 `ledger｜sem_metric#201` 正文含
# 「99 §2.12」⇒ `number_tokens` 回 `('2.12',)` ⇒ 引用该卡的纯定性句（只读声明）被非承载
# 「全须复述」判无据删句。取值＝**生产实点五 kind**——**非**信任级 `ledger`、**非**
# `_KIND_TRUST` 旧键 `family_annotation`（两者与生产 `locator.kind` 永不匹配）。形态值集，
# 非语义词表（零 CJK 词表——零词表 AST 闸面）。
CALIBER_KINDS: frozenset[str] = frozenset(
    {"metric", "term", "object", "relation", "family"}
)

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

# ── 计量数值断言判据（2026-10-17 F1 件一）────────────────────────────────────────
# 数值断言＝**计量数值**（带单位／小数形／千分位形的量值）；**标识符**（井号 `W-22`、修井机编号
# `渤海 302`）与**日期**（`2026 年 11 月 1 日`）不算数值断言（真机证据＝`eval/results/frames/
# EB4-D-诱12.json`，run-c6fd52c7：草稿「W-22 井教训侧重…W-24 井教训侧重…」被误判无据断言整段删，
# 交付答案断在裸标题）。下列单位族是**闭世界取值**（各值单值常量——判据＝记号后紧邻字面在场，
# 非语义词表：不含「年／月／日」日期单位）。单位面可扩可收＝Owner 裁量；本批按票面列举面落值。
VALUE_UNIT_TON = "吨"
VALUE_UNIT_CUBIC_METER = "方"
VALUE_UNIT_METER = "米"
VALUE_UNIT_MILLIMETER = "毫米"
VALUE_UNIT_DAY = "天"
VALUE_UNIT_HOUR = "小时"
VALUE_UNIT_MINUTE = "分钟"
VALUE_UNIT_PERCENT = "%"
VALUE_UNIT_MEGAPASCAL = "MPa"
VALUE_UNIT_CUBIC = "m³"
VALUE_UNIT_DENSITY = "克每立方厘米"
VALUE_UNITS: tuple[str, ...] = (
    VALUE_UNIT_TON,
    VALUE_UNIT_CUBIC_METER,
    VALUE_UNIT_METER,
    VALUE_UNIT_MILLIMETER,
    VALUE_UNIT_DAY,
    VALUE_UNIT_HOUR,
    VALUE_UNIT_MINUTE,
    VALUE_UNIT_PERCENT,
    VALUE_UNIT_MEGAPASCAL,
    VALUE_UNIT_CUBIC,
    VALUE_UNIT_DENSITY,
)
# 量值形两记号（小数点／千分位分隔符——形态记号，非词表）。
DECIMAL_POINT = "."
THOUSANDS_SEPARATOR = ","
# 册号／节号的结构记号（「§」——文档结构记号，**非语义词表**；量值记号前紧邻者＝册号／节号，
# 不入口径数值面——2026-10-18 V2-105，真机证据＝EB11 `Q27` 的「99 §2.12」）。
SECTION_MARKS: frozenset[str] = frozenset({"\u00a7"})
# 记号与单位之间的空白（全角空白经 NFKC 归一为半角空格——`normalize_for_match`）。
MEASURE_GAP = " "

# ── 表格行结构判据（2026-10-18 V2-104 案 A——表格行裸数字入记号面）────────────────────
# 判据全为**版式结构**（行首缩进 ＋ 列空白分隔的数字列计数 ＋ 全文此类行计数），**零词表、
# 零正则**：与引擎侧表格承载判据同形（`retrieval.domain._is_table_bearing`「缩进数字行 ≥2」，
# 本块 R6 禁引引擎故以结构阈值字面落此）。空白面＝半角空格／制表符（全角空白经
# `normalize_for_match` 的 NFKC 归一为半角空格——与 `MEASURE_GAP` 同归一前提）。
TABLE_ROW_INDENT_MIN = 2  # 行首缩进至少两格（缩进＝版式面，非词面）
TABLE_ROW_COLUMN_GAP = 2  # 数字列前紧邻空白至少两格（列分隔／行首缩进——列判据）
TABLE_ROW_COLUMN_MIN = 2  # 行内至少两列数字（多列数字语境）
TABLE_ROW_LINE_MIN = 2  # 全文至少两条此类行（表体——与引擎表格承载判据同形）
TABLE_ROW_INDENT_CHARS: frozenset[str] = frozenset({" ", "\t"})
LINE_BREAK = "\n"  # 行结构记号（零正则切行面）

# ── 油田归属对账（2026-10-17 F1 件四）──────────────────────────────────────────
# 名录面（`appv2.tools.anchors`）实体专名族的**油田**过滤位——闭世界取值的成员取用面（本块不另
# 立第二份名录／词表：归一与闭世界匹配单点＝`appv2.tools.anchors`）。真机证据＝`eval/results/
# frames/Q14M-NQ-M4.json`（NQ-M4：题眼井号体系 Y 系〔渤中34-8〕而交付行引 `《B-渤中34-5油田躺井
# 治理与检泵作业月报-202608》` 的 302／305／22.5 天数据——跨油田张冠李戴）。
FIELD_NAME_NOUN = "油田"

# ── 件四零交付兜底（2026-10-18 V2-106）────────────────────────────────────────
# 件四（跨油田归属）**全行拒收**致零交付时，强制产出「本主体未覆盖＋已试什么」**正证据声明**
# （程序确定性、零模型、零词表）——不落空答。真源＝`tickets/v2/V2-106-件四零交付兜底.md`（任务段
# 逐字：「强制产出「本主体未覆盖」正证据声明，不落空答」「兜底文本进正文（非增补面），并记
# notice」）＋`docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.6（文本形：「本轮窗内材料
# 均属〈其他油田〉，未见〈题眼油田〉材料——本油田未覆盖」）。兜底文本进**正文**（`state.draft`，
# 非增补面；插入点必须在 `text="\n".join(out_lines)` **之前**，否则进不了 draft）＋ notice。
# 三个占位（全为程序确定性输入，零二次创作）：
# - `{scope}`＝题眼所辖油田名（`rules.aligned_field_names`——题眼点名的 ∪ 窗内承载题眼的）；
# - `{other}`＝被拒材料自带油田名（`rules.observation_field_names`——同一取词单点）；
# - `{tried}`＝已试材料清单（被拒行的被引序号＋出处名，升序——`ZERO_DELIVERY_TRIED_TEMPLATE`）。
ZERO_DELIVERY_FALLBACK = (
    "本主体未覆盖（题眼所辖：{scope}）——本轮窗内材料均属{other}，未见{scope}材料。"
    "已试什么：{tried}（均因跨油田归属对不上被拒收）。"
)
# 已试材料逐条形（序号＋出处名——与引标面同形；多条以 `_INDEX_SEPARATOR` 连接）。
ZERO_DELIVERY_TRIED_TEMPLATE = "[{index}] {source}"
# 兜底通知正文（`notice` 帧／状态写口同文——`unsupported_claim` 分型：拒收致零交付不静默）。
ZERO_DELIVERY_NOTICE = (
    "件四归属闸全行拒收致零交付：已按「本主体未覆盖＋已试什么」正证据兜底"
    "（兜底文本进正文、非增补面）——不静默落空答"
)

# ── 回炉零交付兜底（2026-10-18 V2-115）──────────────────────────────────────────
# 回炉（编排侧 LLM 改写）后**最终无内容**时，强制一段**诚实说明**（程序确定性、零模型）——
# 不落空答。真源＝`tickets/v2/V2-115-核验失败动作回炉修复.md` 任务 4（逐字：「零交付兜底：若
# 最终无内容，强制一段诚实说明（已试什么、仍缺什么）」）＋其「Kimi 评审修正」3（插入点须在
# `verification/core.py` 的 `text="\n".join(out_lines)` **之前**——与 V2-106 同点）。兜底文本进
# **正文**（`state.draft`，非增补面）＋ `unsupported_claim` notice；两占位全为程序确定性输入：
# - `{rounds}`＝已执行回炉改写轮数（`state.repair_rounds`——「已试什么」的如实面）；
# - `{anchors}`＝题眼锚（`rules.question_anchors` 的确定性投影——「仍缺什么」的题眼面）。
REPAIR_ZERO_DELIVERY_FALLBACK = (
    "本轮回炉未产出可交付正文（已试 {rounds} 轮按标红行重写；题眼：{anchors}）——"
    "已试什么：逐行重写核验标红行 {rounds} 轮；仍缺：本轮窗内材料未覆盖标红断言。"
)
REPAIR_ZERO_DELIVERY_NOTICE = (
    "核验回炉后正文为空：已按「已试什么＋仍缺什么」正证据兜底（兜底文本进正文、非增补面）"
    "——不静默落空答"
)

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
# 2026-10-18 V2-116：非 `delete` 档（`observe`／`repair-fallback`）下**未删任何行**——文案不得称
# 「删去」（档位诚实：检出 ≠ 离场；交付面＝草稿逐字）。`{mode}` 填如实档位标注值。
NOTICE_UNSUPPORTED_CONTENT_RECORD_ONLY = (
    "核验检出无据断言 {rewritten} 行（{mode} 档：只记录不删——交付面＝草稿逐字；"
    "留痕＝intended_rewrites 逐行原句 ＋ 本计数）"
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
# 2026-10-18 V2-116：非 `delete` 档下**未删行**——缺口文案同样按档诚实（检出 ≠ 离场）。
GAP_REWRITE_REASON_RECORD_ONLY = (
    "核验检出 {rewritten} 行无据断言（{mode} 档：只记录不删——交付面＝草稿逐字）——"
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
# 2026-10-18 V2-116：核验动作档位标注键 ＋ 检出项（本应改写／删除行）清单键。
# `verify_mode`＝如实档位（`off`／`observe`／`repair`／`delete`／`repair-fallback`）；
# `intended_rewrites`＝**检出条数**面（每条含原句 `line` 与 `reason`——非 `delete` 档下这些行
# **不离场**，故与 `rewrites` 分列：前者是「本应处置」的意图面，后者是既有改写留痕面）。
# 两键均 additive（`Verdict` 九键不动）。
PAYLOAD_VERIFY_MODE_KEY = "verify_mode"
PAYLOAD_INTENDED_REWRITES_KEY = "intended_rewrites"
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
# 油田归属对账机读面（2026-10-17 F1 件四）：归属另一油田（与题眼锚对不上且行内无分源说明）的
# 被引观察序号列——该行按既有删句族拒收，本键是其**机读维度面**（拒因复用删句族闭世界常量
# `REWRITE_NO_MATERIAL`，闭世界两值不动）。
PAYLOAD_FIELD_MISMATCH_KEY = "field_attribution_mismatch"
# 件四零交付兜底面（2026-10-18 V2-106）：件四全行拒收且零有支撑句 ⇒ 兜底正证据声明已进正文
# （`state.draft`）——additive 布尔键（`Verdict` 九键不动；真源＝
# `docs/runtime-refactor/design/统筹方案-核验澄清评测.md` §2.6「payload additive：
# `zero_delivery_fallback`」）。
PAYLOAD_ZERO_DELIVERY_KEY = "zero_delivery_fallback"
# 回炉零交付兜底面（2026-10-18 V2-115）：回炉后正文为空 ⇒ 程序诚实说明已进正文（`state.draft`）
# ——additive 布尔键（`Verdict` 九键不动）。与 V2-106 的 `zero_delivery_fallback` 分列（两种
# 零交付不同因：件四全拒 vs 回炉后无内容）。
PAYLOAD_REPAIR_ZERO_DELIVERY_KEY = "repair_zero_delivery_fallback"
