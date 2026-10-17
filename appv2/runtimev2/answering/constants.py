"""answering 的接线常量与闭世界指针（本块自有的唯一常量点；闭世界取值一律引真源、此处不复述）。

真源＝`specs/answering.md`（行为约定节＋「接口定义」节五形状）与 `specs/modules.md`
`## answering` 卡。本模块只落**接线面**常量（模型调用归因桶／过程档案与步标题／事件面取值／
机读 payload 键名／收口话术），**不复述任何别处已定义的闭世界族**：

- 步类型：引 `state.STEP_ANSWER`（`STEP_KINDS` 的真源在 `state`——引真源、不复述字面）；
- 通知类型：**不在本模块立第二份清单**——两字面只作取值指针，其合法性与闭世界由写入面把守
  （`bookkeeping.notice` 按 `transport.NOTICE_TYPES` 逐值判，越界即抛——fail-closed）；
- 路由意图：引 `state.INTENT_VERIFY`／`INTENT_END`（调用点直引，此处不中转）；
- 模型调用归因桶：`MODEL_CALLER` 的字面真源＝`bookkeeping` 的归因桶闭世界
  （`specs/gateway_adapter.md` 行为 5「三桶族：理解／决策／作答」）——**本块不引其常量模块**
  （R2：业务相位只经公共层包根、禁深层子模块），故以字面指针落此，落点唯一。
"""

from appv2.runtimev2.state import STEP_ANSWER
from appv2.runtimev2.transport import (
    SUPPLEMENT_HEAD_MARK_ATTRIBUTION,
    SUPPLEMENT_HEAD_MARK_CITATIONS,
    SUPPLEMENT_HEAD_MARK_SPLIT,
)

# ── 模型调用归因（`bookkeeping.call_model` 的 `caller`）──────────────────────────
# 真源＝`bookkeeping` 归因桶闭世界「understand／decision／answer」（`specs/gateway_adapter.md`
# 行为 5）；本块为作答轮，恒取作答桶（字面唯一落点——R2 禁引 `bookkeeping.constants` 深层）。
MODEL_CALLER = "answer"

# ── 过程档案与对话链面（`bookkeeping.note`／`append_message`）────────────────────
PHASE = "answer"  # 过程档案 phase 标记（同桶名）
ROLE_USER = "user"  # 对话链角色（真源＝`bookkeeping` 写口闭世界，越界由其抛错）
ROLE_ASSISTANT = "assistant"  # 终稿追加链尾的角色（同款）
# 过程档案标记（起草留痕）：既是「模型原话只进过程档案」的落点（行为 8），也是本块自立的
# 「起草已发生」机读判据（先例＝`understanding.assembly` 的「任务书已装配」标记条目）。
DRAFT_NOTE_TITLE = "起草答案"

# ── 步面（`bookkeeping.record_step`）──────────────────────────────────────────
# 引用真源、不复述取值：`STEP_KINDS` 的取值域在 `state`（六值闭世界）。
DRAFT_STEP_KIND = STEP_ANSWER
FINALIZE_STEP_KIND = STEP_ANSWER
DRAFT_STEP_TITLE = "起草答案"
FINALIZE_STEP_TITLE = "答案收口"

# ── 事件面（真源 `synth/S6-事件与帧目录.md` §一 text／citation 两行）────────────
TEXT_EVENT = "text"  # 本块自产的增量文本事件（一段一帧）
CITATION_EVENT = "citation"  # 本块自产的引标落账事件（收口批）
# 帧载荷键：`text`＝`{content[, kind]}`（本块不带 `kind`——`kind="understanding"` 属理解步）；
# `citation`＝`{index, source, source_id, trust}`（S6 逐字）。
TEXT_PAYLOAD_CONTENT = "content"
CITATION_PAYLOAD_INDEX = "index"
CITATION_PAYLOAD_SOURCE = "source"
CITATION_PAYLOAD_SOURCE_ID = "source_id"
CITATION_PAYLOAD_TRUST = "trust"

# ── 通知分型指针（取值真源 `transport.NOTICE_TYPES`——写入面把守；本块不私扩闭世界）──
NOTICE_EMISSION_STRIP = "emission_strip"  # 发射通道残留检出（钉 pin-04 的机读面）
NOTICE_MATERIAL_TRUNCATED = "material_truncated"  # 材料截断披露（帧面分型同族）

# ── 降级与引用簇机读面（`RT-W4-06b`：行为 6／12／14／15／16 的步 payload 键单点）──────
# 七键同落**起草答案**步 payload（起草＝交付面第一手；收口步另携 `contradiction_seqs`）。
PAYLOAD_ECHO_FLAG_KEY = "echo_flag"  # 行为 14（字段名逐字＝A-P4b-61——观测字段只记不拦）
PAYLOAD_ENGINE_NOTES_KEY = "engine_notes"  # 行为 15：引擎注记原文（no_hit 等——不得静默丢弃）
PAYLOAD_CONTRADICTION_SEQS_KEY = "contradiction_seqs"  # 行为 6：矛盾池成员序号（分源列明面）
# 行集交付对账（行为 12 **交付侧**）：`engine_rows`＝引擎返回行数（窗口行集族行数）、
# `delivered_rows`＝答案面实际交付的行数（被引支数）——与 `specs/verification.md` 行为 11 的
# `obs_rows`／`delivered_rows` 同口径（本块为交付侧第一手记账，核验侧对账归 verification）。
PAYLOAD_ENGINE_ROWS_KEY = "engine_rows"
PAYLOAD_DELIVERED_ROWS_KEY = "delivered_rows"
# 排名型子问题消费面（行为 16）：排名观察支序号（窗口行集族序）＋交付序一致性（序信息面）。
PAYLOAD_RANKING_SEQS_KEY = "ranking_seqs"
PAYLOAD_RANKING_ORDER_OK_KEY = "ranking_order_ok"

# ── 机读 payload 键名（本块答案面步的 `citations`／`gaps` 字段——「不降级与静默禁令」节）──
PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_CITATIONS_KEY = "citations"
PAYLOAD_GAPS_KEY = "gaps"
# 坏引标剥除留痕（2026-10-17 EB5b）：起草段剥除的**界外引标序号列**（出现序去重）——机读面，
# 判据＝`degradation.strip_dangling_citations`；无剥除＝空列表（键恒在场，对账面可复算）。
PAYLOAD_DANGLING_SEQS_KEY = "dangling_citation_seqs"
PAYLOAD_GAP_KIND_KEY = "kind"
PAYLOAD_GAP_SUBTASK_KEY = "subtask_id"
PAYLOAD_GAP_REASON_KEY = "reason"
# 步 payload 的阶段面取值（迁移照抄 V1 answer 节点的 `"phase": "draft"／"finalize"`）。
PAYLOAD_PHASE_DRAFT = "draft"
PAYLOAD_PHASE_FINALIZE = "finalize"

# ── 子问题结果态面（`state.subtask_results` 取值域——真源 `execution`；此处只作分派指针）──
SUBTASK_STATUS_OK = "ok"  # 执行块成功实录
SUBTASK_STATUS_REFUSED = "refused"  # 前置闸拒／闸拒（终局）——非 ok 非拒者落「缺失」

# ── 确定性直答定型值指针（`state.draft_kind`）────────────────────────────────────
# 真源＝`bookkeeping.constants.DRAFT_KIND_DIRECT`（`specs/bookkeeping.md` 行为 12／14 逐字
# `draft_kind="direct"`）——**R2 禁引深层子模块**，故以字面指针落此，落点唯一。
DRAFT_KIND_DIRECT = "direct"

# ── 引用块（迁移照抄 V1 `_finalize` 的引用块形）────────────────────────────────
# **两刀分类（2026-10-17 EB4b）**：引用块走增补面（`block="citations"`，`core._citation_block`），
# 属**用户可见面**；本字面（「引用：」）已是白话、零行话词，EB4b 核实后零改（不是回喂面，
# 是「无需改的白话面」——记录以免下一轮重复核查）。
# **文本单点（2026-10-17 EB5c）**：块头字面改**引块头模式族**（`transport` 的
# `SUPPLEMENT_HEAD_MARK_*`——三块头与核验分列块头、血缘族同族一处定义），本行只做
# 「`"\n\n"` 前缀 ＋ 换行」的行形装配；字面本身全仓唯一位于 `transport/constants.py`。
CITATION_BLOCK_HEAD = "\n\n" + SUPPLEMENT_HEAD_MARK_CITATIONS + "\n"

# ── 收口话术（本块自有文案——空白/缺失与披露面）───────────────────────────────
# **两刀分类（2026-10-17 EB4b）**：四个 `*_REASON` 是**机读缺口面**——`Gap.reason` 只进答案面步
# payload（`gaps` 三键），无上屏路径（`web/src/landing/*` 不渲染 `gaps`），属**审计消费面**，
# 照 A-P6b-05 零改动；`EMISSION_STRIP_CONTENT`／`MATERIAL_TRUNCATED_CONTENT` 是 notice 帧内容
# （`material_truncated`／`emission_strip`），web 侧 `NoticeRow` 逐条渲染 content＝**用户可见面**，
# 故白话化。判定面语义零改（只改话术不动判据——照 EB2 D3「段头去工程腔」先例）。
ZERO_MATERIAL_REASON = (
    "零实质材料（观察面无非 notice 条目）——本轮回答无材料可核，未及核验"
)
EMPTY_DRAFT_REASON = (
    "模型未产出草稿（剥离后空稿）——不推空答案，按结构化缺口如实收口"
)
MISSING_DRAFT_REASON = "起草未产出可交付答案——按结构化缺口如实收口"
SUBTASK_MISSING_REASON = "执行未取得材料（失败／重试耗尽）"
# 2026-10-17 EB4b（程序文案白话化）：旧「起草面检出 JSON 通道残留（发射围栏／裸 JSON 段）——
# 确定性剥离，不进答案面（V2-48：…）」→ 白话；剥离判据（`strip_emission_fences`／
# `EMISSION_ACTIONS` 闭世界）与帧型（`NOTICE_EMISSION_STRIP`）零改，只改上屏话术。
EMISSION_STRIP_CONTENT = (
    "这次模型回复里混进了程序用的格式内容——已自动去掉，答案不受影响。"
)
# 2026-10-17 EB4b：旧「答案视野检索片段仅渲染 {rendered}/{total} 支（权威行集与台账卡已全量）
# ——未渲染部分不作答（V2-61）」→ 白话（去「视野／渲染／行集／台账卡」工程腔与票据号，内部计数
# 单位「支」改「条」）；披露判据与两槽位（`rendered`／`total`）零改；规格验收行 13 的声明逐字
# 随本批同步（`specs/answering.md`）。
MATERIAL_TRUNCATED_CONTENT = (
    "这次回答只用到检索到的 {rendered}/{total} 条材料——没用上的部分不作答。"
)

# ── 降级与引用簇（`RT-W4-06b`：行为 6／12／13／14／15／16／17——本块自有文案单点）─────────
# 矛盾分源块（行为 6：分源列明、不强调和；「互不一致」标出——对应 `refuted_by` 取向）。
# 逐支行形逐字迁移 V1 `graph.py` `_contradiction_members` 的列明形（recon/A2 R-A2-29）。
# 2026-10-17 EB2 D3（段头去工程腔）：旧「互不一致——多来源分源列明（禁止无出处调和）：」→
# 友好话术；判定面语义零改（仍逐支原文照抄、不调和）。**「互不一致」标保留**——`specs/answering.md`
# 行为 6 的「标出『互不一致』」面（其验收测试 `::contradiction_split_not_merged` 同钉），
# 判据话术与 `verification.SPLIT_BLOCK_HEAD` 同句（两相位 R1 禁互引，故按字面同句落此——
# 本常量＝本相位唯一落点，块头禁再出现第二处字面）。**2026-10-17 EB5c 收正**：两相位的分源块头
# 同句现已**同为块头模式族成员**（`transport.SUPPLEMENT_HEAD_MARK_SPLIT`／`..._SPLIT_VERIFY`
# ——「同一句字面全仓一处」由此成立，本行只做 `"\n\n"` 前缀装配）。
CONTRADICTION_SECTION_HEAD = "\n\n" + SUPPLEMENT_HEAD_MARK_SPLIT
CONTRADICTION_LINE = "[{seq}] {source} · {source_id}：{content}"
# 分源列明归属块（行为 17：逐源归属配对——来源名↔数值／结论配对；「某区块」含糊形不得由本块产出）。
# 2026-10-17 EB4b（段头去工程腔续 EB2 D3）：旧「分源列明（逐源归属——来源名↔数值／结论配对）：」
# ——「分源列明」「逐源归属」是内部工序说法，业务用户读不到；判定面语义零改（仍逐支原文照抄、
# 仍逐源配对，配对判据在 `degradation.source_section`，零改）。增补面属**交付面**（评分面＝
# 正文＋增补面合并判——Owner 2026-10-17 裁决），故与正文同列**用户可见面**。
SOURCE_SECTION_HEAD = "\n\n" + SUPPLEMENT_HEAD_MARK_ATTRIBUTION
SOURCE_LINE = "[{seq}] {source}：{content}"
# 引擎注记段（行为 15 的「不静默」面：台账 no_hit 等引擎注记在 `context.render_materials` 里
# 整体排除（`specs/context.md` 行为 2），故本块另以其原文送入窗口——「不得静默丢弃」）。
# **两刀分类（2026-10-17 EB4b）**：本常量**不是上屏文案**——`engine_notes_block` 的唯一消费点是
# `core._draft` 里追加给**模型**的材料段（`append_message`，见 `core.py:264`），属**回喂机面**
# （材料/指令文本），照 EB2 D1「引擎注记保留进窗（模型如实转述所必需）」与 A-P6b-05 零改动。
ENGINE_NOTES_HEAD = "\n引擎注记（引擎降级／拦停／未绑定注记——如实转述，不得静默丢弃）：\n"
# 起草回声签名判据（行为 14；字面逐字＝A-P4b-61）。两字面是规格给定的**形态签名**：
# 只记签名、零拦截、零改写（「观测字段只记不拦」——不是语义词表，见 `degradation` 模块注）。
ECHO_HEAD = "理解："
ECHO_CANDIDATE_MARK = "指标候选"
ECHO_WINDOW = 100
# 方括号记号体分型（行为 13 占位符 `[n]` 与引标 `[n]` 的形态判据字符集——零语义）。
ASCII_DIGITS = "0123456789"
ASCII_LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
FULLWIDTH_COLON = "："  # 矛盾池 subject 切分符（逐字迁移 V1 `_contradiction_members`）

# ── 观察面形态取值指针（`locator.kind` 判定面——闭世界取值真源不在本块，此处只作取值指针）──
# 行集族：`locator.kind` ∈ 行集族 ⇔ 该观察是引擎返回的**数据行**（行集全量交付、丢行＝0——
# 取值真源＝`specs/execution.md` 行为 4 与 `execution.constants.ROWSET_OBSERVATION_KINDS`；
# **R1 禁引其它相位**，故以取值指针落此，落点唯一）。
ROWSET_OBSERVATION_KINDS: frozenset[str] = frozenset({"agg_row"})
# 引擎注记观察（`context.render_materials` 行为 2 整体排除面——本块以「引擎注记」段补回窗口）。
KIND_NOTICE = "notice"
# 矛盾池豁免面（逐字迁移 V1 `_contradiction_members`：行级时序事实 `agg_row`／血缘卡 `lineage`／
# 元信息 `notice` 不入池——recon/A2 R-A2-30）。
CONTRADICTION_EXEMPT_KINDS: frozenset[str] = frozenset({"agg_row", "lineage", "notice"})

# ── 发射动作闭世界（`strip_emission_fences` 的域内判据）─────────────────────────
# 真源＝旧码 `appv2/runtime/graph.py` L180 `ACTION_KINDS` 四值（`docs/runtime-refactor/recon/
# A2-核验规则与归属审.md` R-A2-04「行内含裸发射令牌（action ∈ 四值闭世界）」——发射剥离的
# 逐字迁移面；R-A2-06「域外 JSON 零误伤」由此闭世界定界）。**本族不是本块新立的闭世界**：
# 判据本体（泄漏=0 的已根治态）随 V1 字面迁移、不新造；V2 侧相位①动作族另见 `parsing`
# （本块不引其深层子模块，R2），两处非同族第二定义（登记见票面回报）。
EMISSION_ACTIONS = frozenset({"discover", "execute", "ask", "finalize"})
