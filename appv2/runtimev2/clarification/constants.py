"""clarification 块的常量单点：拒因码闭世界、拒因映射表、文本常量族、易变量清单。

真源＝`specs/clarification.md`（行为 8／15／16／17／18／19 与接口定义节）＋迁移前逐字稿载体
`appv2/runtime/graph.py`（`clarify_node` 段：拒因回喂、三段带路、到顶截断、恢复回收）与
`appv2/runtime/budget.py`（`NO_MATERIAL_SHELL`）。

**数值面零复制**：本块源码不复述任何封顶字面值——连续反问上限取 `state.budget.ask_cap`、
发现预算两参取 `state.budget` 的「轮内发现／全 run 发现」键（限额键面归 `state`，
`specs/state.md` 行为 10）；唯一本块自持的限额值是**子问题条数上限**（`MAX_SUBTASKS`——
其真源 `walk/09` §七 Q-C 属「两处限额真源均未单列」的第三源，`state` 承载键待落定，
`specs/parsing.md` 风险 7⑤；本块是该值的**注入方单点**，parsing 侧签名保持注入制无缺省值）。

**取值一律引真源、此单点仅作值引用**（同 `state.constants` 的 `_CONVERGENCE_NOTICE_TYPE` 先例）：
`caller` 桶、`AskChoice`／`pending_ask` 帧的 `kind`、通知类型、对话层来源、前置判定 state 值——
皆落真源指针，不在本处另立第二套闭世界（`specs/state.md` 行为 9 同款纪律）。
"""

from typing import Final

# ── 子问题条数上限（本块注入方单点）────────────────────────────────────────────
# 数值真源＝`docs/runtime-refactor/walk/09-澄清-分解问题.md` §七 Q-C（`≤4`，自定值、可调，
# 其自述「进统一预算表」——该表未落盘）＋`docs/runtime-refactor/eng/00-阶段2-模块划分草案.md`
# F-14 口径；`state` 承载键未落定（`specs/parsing.md` 风险 7⑤——「条数键两源未单列」）。
# 本常量为**注入方单点**：`parsing.parse_question_group` 的 `max_subtasks` 由本块供值。
MAX_SUBTASKS: Final[int] = 4

# ── 值引用单点（真源指针逐项标注；跨块取值不复制第二套闭世界）──────────────────
# 模型调用归因桶：真源＝`specs/gateway_adapter.md` 行为 5「三桶族：理解／决策／作答」；
# bookkeeping 的桶常量在深层子模块（`appv2.runtimev2.bookkeeping.*`——R2 禁引），故以值引用落此。
CALLER_DECISION: Final[str] = "decision"
# 挂起帧 kind：真源＝`state.AskChoiceKind`／`transport.ASK_FRAME_KINDS`（二值
# `clarify`｜`external_table_approval`）；本块只生产 `clarify` 帧（审批帧归审批面）。
ASK_KIND_CLARIFY: Final[str] = "clarify"
ASK_KIND_EXTERNAL_TABLE_APPROVAL: Final[str] = "external_table_approval"
# 通知类型：真源＝`specs/transport.md` 的 `NOTICE_TYPES`（二十九值，含本三值）；
# 落点校验由 `bookkeeping.notice` 写口把守（越界即拒）。
NOTICE_CLARIFY_CAPPED: Final[str] = "clarify_capped"
NOTICE_EMISSION_QUOTE_REPAIR: Final[str] = "emission_quote_repair"
# 发射注记出流（行为 3「无时间词 → 默认「近 30 天」**并注记**」的机读承载位——
# 默认值＋注记同批产出：默认窗是模型侧结论、注记经本值出流为机读信号）。
# 逐字迁移 V1 `appv2/runtime/graph.py` `clarify_node` 两处 `"type": "decision_note"`
# （L2501／L2616——承载位换、文本不变）。
NOTICE_DECISION_NOTE: Final[str] = "decision_note"
# 对话层来源：真源＝`specs/state.md` 行为 6「`clarify_approval_replay`（澄清与审批回收原文）」；
# 落点校验由 `bookkeeping.append_dialogue` 写口把守。
DIALOGUE_ORIGIN_CLARIFY_REPLAY: Final[str] = "clarify_approval_replay"
# 前置判定 state 值（三段带路①的触发面）：真源＝`appv2/tools/schema.py` 的 `STATE_NOTE`（note）／
# `STATE_BLOCKED_REFUSE`（blocked_refuse）——本块零工具面 import（票面边界红线②），故值引用。
VERDICT_STATE_NOTE: Final[str] = "note"
VERDICT_STATE_BLOCKED_REFUSE: Final[str] = "blocked_refuse"
VERDICT_REFUSAL_STATES: Final[frozenset[str]] = frozenset(
    {VERDICT_STATE_NOTE, VERDICT_STATE_BLOCKED_REFUSE}
)

# ── 拒因码闭世界（`ClarifyReason.code`）────────────────────────────────────────
# 规格枚举六值＝`specs/clarification.md` 接口定义节（动作越界／条数越界／注释为空／注释槽位对账
# 不过／chain 越界／零实质观察禁定稿）；另三项为本块必需出口：
# - `no_rediscover_when_window_set`＝行为 16 后半机械半句的回喂出口（驳回「再 discover」）；
# - `rejection_guidance`＝行为 18 三段带路的承载位（拒因载荷必带——不做第二套返回形）；
# - `schema_invalid`＝解析面其余 schema 违例（不可解析 JSON／discover 与 ask 形状／预算前缀）
#   的残差出口。
# **扩员须回设计仓对账（登记项，呈主窗）**。
REASON_ACTION_OUT_OF_WORLD: Final[str] = "action_out_of_world"
REASON_SUBTASK_COUNT_OUT_OF_RANGE: Final[str] = "subtask_count_out_of_range"
REASON_LEDGER_NOTES_EMPTY: Final[str] = "ledger_notes_empty"
# 注释非逐字 → 槽位对账不过（2026-10-16 改·流水 64，Owner 裁）：判据由「在台账注入块内逐字
# 求得」改为「三段槽位对账」（行为 8）——承载位与枚举位次不变，码面随判据改名（枚举仍九值，
# 未扩员）。
REASON_LEDGER_NOTES_SLOT_MISMATCH: Final[str] = "ledger_notes_slot_mismatch"
REASON_CHAIN_OUT_OF_WORLD: Final[str] = "chain_out_of_world"
REASON_FINALIZE_ZERO_OBSERVATION: Final[str] = "finalize_without_substantive_observation"
REASON_NO_REDISCOVER: Final[str] = "no_rediscover_when_window_set"
REASON_REJECTION_GUIDANCE: Final[str] = "rejection_guidance"
REASON_SCHEMA_INVALID: Final[str] = "schema_invalid"

REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        REASON_ACTION_OUT_OF_WORLD,
        REASON_SUBTASK_COUNT_OUT_OF_RANGE,
        REASON_LEDGER_NOTES_EMPTY,
        REASON_LEDGER_NOTES_SLOT_MISMATCH,
        REASON_CHAIN_OUT_OF_WORLD,
        REASON_FINALIZE_ZERO_OBSERVATION,
        REASON_NO_REDISCOVER,
        REASON_REJECTION_GUIDANCE,
        REASON_SCHEMA_INVALID,
    }
)

# 拒因映射表（行为 19：解析拒文 `str` → 拒因枚举的**机械适配**——逐字子串校，零语义判断；
# 属 `specs/clarification.md` 行 16 的**形态处理豁免面**）。
# 序＝由专到泛（首个命中者胜）；标记逐字取自 `appv2/runtimev2/parsing/parsers.py` 与
# `parsing/helpers.py` 的机器面拒文（其文本改动时本表随之对账——登记面）。
# 未命中任一标记 → `schema_invalid`（残差出口：不可解析 JSON／discover·ask 形状／预算前缀）。
REASON_MARKERS: Final[tuple[tuple[str, str], ...]] = (
    ("缺失或越界", REASON_ACTION_OUT_OF_WORLD),
    ("chain 越界", REASON_CHAIN_OUT_OF_WORLD),
    ("ledger_notes", REASON_LEDGER_NOTES_EMPTY),
    ("超出上限", REASON_SUBTASK_COUNT_OUT_OF_RANGE),
)

# 观察的 notice 定位型（行为 17 的实质观察过滤面）：真源＝`appv2/tools/schema.py` 的
# `Observation.locator.kind`（通知型观察 `notice` 不算实质材料——V1 `_zero_probe_block` 同式）。
NOTICE_LOCATOR_KIND: Final[str] = "notice"

# 「首拒免轮、连续第 2 次起占轮」的第三类拒（浅探查／重复钻取／预算驱动）的 streak 阈值
# （真源 `arch/P4b` A-P4b-06；本块只在 `_record_rejection` 一处消费）。
REJECT_FREE_STREAK: Final[int] = 2

# ── 易变量清单（行为 13：恢复时重取一遍）──────────────────────────────────────
# 清单原文＝`specs/clarification.md` 行为 13／风险 3：数据水位／新鲜度／地基／落库新数据。
VOLATILE_KEYS: Final[tuple[str, ...]] = ("watermark", "freshness", "foundation", "new_rows")

# ── `ledger_notes` 三段槽位对账（行为 8 的判据面；2026-10-16 改·流水 64，Owner 裁）────────
# 判据真源＝`specs/clarification.md` 行为 8（三段对账：槽位逐字∈台账名录 ∪「无台账命中」／
# 绑定态∈闭世界／窗形合法）；合同 `ledger_notes` 形逐字＝`槽位｜绑定态｜窗`（分隔符全角「｜」、
# 三段位次固定）。
NOTE_SLOT_SEPARATOR: Final[str] = "｜"
# 段名（拒因文案「{段名}」槽位——段位次固定名；段数非三时用「段数」承名）。
NOTE_SEGMENT_SLOT: Final[str] = "槽位"
NOTE_SEGMENT_BINDING: Final[str] = "绑定态"
NOTE_SEGMENT_WINDOW: Final[str] = "窗"
NOTE_SEGMENT_COUNT: Final[str] = "段数"
# 段位次表（段数与段名同源一处——判据面引 `len(NOTE_SEGMENTS)`，不另立条数常量）。
NOTE_SEGMENTS: Final[tuple[str, ...]] = (
    NOTE_SEGMENT_SLOT,
    NOTE_SEGMENT_BINDING,
    NOTE_SEGMENT_WINDOW,
)
# 绑定态闭世界（流水 64 裁：照台账行「（绑定态：…）」中文形两值；越界即拒）。
BINDING_STATES: Final[frozenset[str]] = frozenset({"已绑定", "未绑定"})
# 槽位段第二形「无台账命中」＝本子问题**无台账行可锚**（knowledge 链报告内容题常态——
# 2026-10-16 补·流水 66：真机 run-18e5d273「完井液密度」无台账行，旧判据只认名录，
# 模型**没有任何合法形可写**、三写「不在名录」三拒烧光轮次；空命中是合法业务态、非违约）。
# 槽位段合法集＝台账名录 ∪ 本闭世界（判据 `core._note_slot_mismatch` 消费本表，不另立字面）。
NOTE_SLOT_NO_HIT: Final[str] = "无台账命中"
NOTE_SLOT_LITERALS: Final[frozenset[str]] = frozenset({NOTE_SLOT_NO_HIT})
# 窗段合法形（除「ISO~ISO 锚定窗」外的字面形；窗形读法照 `appv2/tools/precondition.py`
# 的 `date.fromisoformat(window_end[:10])`——截读长度即 ISO 日形串长，取自形串本身；
# 本块不新造窗面判据）。
WINDOW_SEPARATOR: Final[str] = "~"
WINDOW_SEGMENT_TOTAL: Final[int] = 2
ISO_DAY_SHAPE: Final[str] = "2000-01-01"
WINDOW_UNRESOLVED: Final[str] = "窗未定"
# 「无时间窗」＝「窗未定」同义形（knowledge 链检索式问题无窗概念，模型自发写法两种；
# 2026-10-16 微批收编——真机日志实测模型写「无时间窗」，旧判据必拒白烧轮）。
WINDOW_UNTIMED: Final[str] = "无时间窗"
WINDOW_NULL_PAIR: Final[str] = "null~null"
# 非锚定窗合法字面（闭世界集合单点——判据 `core._window_legal` 消费本表，不另立字面）。
WINDOW_LITERALS: Final[tuple[str, ...]] = (
    WINDOW_UNRESOLVED,
    WINDOW_UNTIMED,
    WINDOW_NULL_PAIR,
)

# ── 文本常量族（逐字迁移自 `appv2/runtime/graph.py` `_shallow_probe_feedback`／
#    `_clarify_capped_answer`／`_quote_repair_notice` 与 `appv2/runtime/budget.py`
#    `NO_MATERIAL_SHELL`——承载位换、文本不变）─────────────────────────────────
# **两刀分类（2026-10-17 EB4b 白话化；票面口径：上屏路径＝正文／supplement／notice／ask 帧）**：
# - **上屏面**（本批白话化）：`CAPPED_ANSWER_HEADER`（进正文首行＝text 帧）／
#   `CAPPED_NOTICE_TEMPLATE`（notice `clarify_capped`）／`QUOTE_REPAIR_NOTICE_CONTENT`
#   （notice `emission_quote_repair`）；
# - **非上屏面**（零改）：`CAPPED_NOTE_DIGEST`／`STEP_TITLE_*`／`NOTE_DIGEST_*`（过程档案与步帧
#   标题）、`MATERIAL_ROW_PREFIX`（正文行前缀，形态记号）；
# - **回喂机面（A-P6b-05 零改动）**：`GUIDANCE_*`／`TEXT_SLOT_MISMATCH_*`／`TEXT_ZERO_OBSERVATION`／
#   `TEXT_NO_REDISCOVER`／`CAUSE_*`／`NO_LEDGER_*_SHELL`——它们是解析拒因回喂面（文本进模型窗），
#   一字不动；
# - **已是白话的样板**：`NO_MATERIAL_SHELL`（V2-80d 人话壳，EB4b 样板）——零改。
# 三段带路（行为 18：零模型调用、段缺则跳、「；」连接成单段；段③兜底句恒在）。
GUIDANCE_PRECONDITION: Final[str] = (
    "数据链已被前置判定拒（在册未绑定/台账外）——该指标材料走报告检索："
    "分解时 chain=knowledge、tool=doc_retrieve"
)
GUIDANCE_EMPTY_PROBES: Final[str] = "已空手探查：{tools}——禁再试同名同参"
GUIDANCE_FALLBACK: Final[str] = (
    "先 discover 取得条目（精确名单词），或 decompose 分解走 doc_retrieve 检索执行。"
)
GUIDANCE_JOIN: Final[str] = "；"
EMPTY_PROBES_JOIN: Final[str] = "、"

# 到顶截断（行为 15：带已取得材料如实直答、明示未完成项、不环）。
# 2026-10-17 EB4b：旧「（连续澄清截断——已取得材料如实交付，不再挂起）」——「澄清截断／挂起」
# 是内部工序说法，业务用户读不到；本行进**正文首行**（text 帧）＝上屏面，故白话化；
# 到顶判据（`ask_cap` 计数）与「带材料直答」行为零改（判定面语义零改）。
CAPPED_ANSWER_HEADER: Final[str] = (
    "（追问次数已到上限——先把已经查到的材料如实交给你，不再继续追问）"
)
# 上限值以槽位插值（V1 把「≥6」写死在文案里——数值单点纪律下不复现）。
# 2026-10-17 EB4b：旧「连续澄清已达上限（连续 ask ≥{cap}）——不再挂起，带已取得材料如实直答。」
# → 白话（notice `clarify_capped` 内容＝上屏面）；`{cap}` 槽与截断判据零改。
CAPPED_NOTICE_TEMPLATE: Final[str] = (
    "连续追问已到上限（{cap} 次）——不再继续追问，先把已经查到的材料如实交给你。"
)
# 过程档案 digest（非上屏面——步帧／过程档案行，EB4b 零改）。
CAPPED_NOTE_DIGEST: Final[str] = "连续澄清达上限（≥{cap}）——带材料直答"
NO_MATERIAL_SHELL: Final[str] = (
    "没能查到能回答这个问题的材料——可以换个问法，或告诉我更多背景"
    "（哪口井、哪个时间段），我再帮您查。"
)
MATERIAL_ROW_PREFIX: Final[str] = "- "

# 引号自修受理 notice（解析侧「受理编排」的调用方义务——`specs/parsing.md` 行为 10）。
# 2026-10-17 EB4b：旧「发射 JSON 值内裸引号——程序确定性修复后受理（零模型零占轮；值内引号换
# 中文引号）」——「发射 JSON／零模型零占轮」是工程腔，业务用户读不到；notice
# `emission_quote_repair` 内容＝上屏面，故白话化（修号行为与判据零改）。
QUOTE_REPAIR_NOTICE_CONTENT: Final[str] = (
    "这次的指令里引号写法不对——已经自动改正后继续（没有多花模型调用，也没有多占一轮）。"
)

# ── 机器面拒因文本（本块产：行为 16 后半／行为 8 槽位对账）────────────────────
TEXT_ZERO_OBSERVATION: Final[str] = "零实质观察禁定稿"
TEXT_NO_REDISCOVER: Final[str] = "台账命中且时间窗已定——禁再 discover（直发分解）"

# 槽位对账拒因（**逐字稿载体＝流水 64 Owner 裁**——头行＋逐子问题三行块〔拒因／期望形／
# 台账相关行〕＋尾行；`{…}` 为槽位，程序照填：id／段名／值／原因／台账整行原文）。
# **2026-10-16 补（L0/L2 三病灶修复批②）**：窗段【期望形】给**具体示例**（锚定窗形 ＋ 检索式
# 无窗形）——真机实测首秀形窗段写法无据可依（L2/r1 必拒），拒因壳语是回喂面唯一的教具；
# 合法形真源＝`specs/clarification.md` 行为 8③（锚定窗／`窗未定`／`null~null` 三形）。
# **2026-10-16 补（流水 66）**：槽段【期望形】补第二合法形「或「无台账命中」」（同上理由——
# 无台账行的报告内容题旧判据无合法形可写，真机 run-18e5d273 三拒烧光轮次）。
TEXT_SLOT_MISMATCH_HEAD: Final[str] = "上次发射被拒：ledger_notes 槽位对账未过：{ids}"
# 步骤标题/过程档案用单行同义形（拒因正文多行，不宜作标题槽——头行去「上次发射被拒」前缀）。
TEXT_SLOT_MISMATCH_TITLE: Final[str] = "ledger_notes 槽位对账未过：{ids}"
TEXT_SLOT_MISMATCH_BLOCK: Final[str] = (
    "【拒因】{id} 的「{segment}」段「{value}」{cause}\n"
    "【期望形】〈台账行首名｜或「无台账命中」〉｜已绑定|未绑定"
    "｜〈锚定窗形：2026-09-16~2026-10-16｜检索式无窗：窗未定或 null~null〉\n"
    "【台账相关行】{row}"
)
TEXT_SLOT_MISMATCH_TAIL: Final[str] = "——修正后重新输出 JSON。"
TEXT_JOIN: Final[str] = "\n"
# 不过原因三值（段级诊断用词）＋段数越界原因（段名「段数」承名）。
CAUSE_SLOT_NOT_IN_LEDGER: Final[str] = "不在台账名录"
CAUSE_BINDING_OUT_OF_WORLD: Final[str] = "绑定态越界"
CAUSE_WINDOW_ILLEGAL: Final[str] = "窗形不合法"
CAUSE_SEGMENT_COUNT: Final[str] = "段数非三（形＝槽位｜绑定态｜窗，位次固定）"
# 槽位不在名录时的【台账相关行】行文（流水 64 裁逐字；名录四类＝指标/对象/关系/术语——
# 2026-10-16 微批补「关系/术语」，与 `volatile._NAME_COLUMNS` 名录面同步）。**2026-10-16 补
# （流水 66）**：尾附「自造名≠无命中」明示句——防「无台账命中」（＝本子问题不锚台账行）
# 被当垃圾桶；名录外自造名照拒不误放。
NO_LEDGER_ROW_SHELL: Final[str] = (
    "（名录无此名——只许用台账注入块内出现的指标/对象/关系/术语名；"
    "自造名≠「无台账命中」——无台账行时才写它）"
)
# 「无台账命中」形的【台账相关行】行文（流水 66 裁逐字）：槽位合法但绑定态／窗段不过时该段
# 照实示「本子问题不锚台账行」（不空手、不套「名录无此名」——两形语义不同）。
NO_LEDGER_HIT_ROW_SHELL: Final[str] = "（无命中形——本子问题不锚台账行）"

# ── 步骤标题与过程档案（逐字迁移 V1 `clarify_node` 的标题形）──────────────────
STEP_TITLE_PROMPT_CHARS: Final[int] = 24
STEP_TITLE_ASK: Final[str] = "澄清 r{round}：反问（{prompt}）"
STEP_TITLE_DISCOVER: Final[str] = "澄清钻取 ×{count}（{names}）"
STEP_TITLE_DECOMPOSE: Final[str] = "澄清 r{round}：分解 {count} 子问题"
STEP_TITLE_FINALIZE: Final[str] = "澄清定稿：材料足够——直答收口"
STEP_TITLE_CAPPED: Final[str] = "澄清 r{round}：连续反问到顶——截断带材料直答"
STEP_TITLE_REJECTED: Final[str] = "澄清 r{round} 被拒：{reason}"
STEP_TITLE_RESUME: Final[str] = "澄清回收：{value}"
# 对象歧义 ask 的提示模板（V2-82b——票面逐字稿；`{name}`＝题面命中的术语/指标名，取
# 候选序首个）。`options` 逐字＝油田实例名单（≤3）＋`state.ALL_FIELDS_OPTION`「都要（分源对比）」。
SUBJECT_ASK_PROMPT: Final[str] = (
    "这道题问的是「{name}」——系统里有多个油田的数据。请确认要查哪一个："
)
# ── 主体程序回填的留痕字面（V2-82 批 EB6 修 1——A2 门误触；2026-10-17）──────────────
# 模型槽空 ∧ 题面程序抽得到主体 ⇒ 门把程序候选回填 `state.subjects` 并不弹 ask（题面点名主体
# ＝对象已定）——留痕机制同 V2-82a 主体识别分歧注记（`bookkeeping.note` 唯一写口、有界一句），
# 但**标题/digest 本块自持**：理解侧那对字面在 `understanding.constants`，而本块零
# `understanding` import（依赖白名单红线，AST 机检）——故作同机制的**另一对**字面（各自表述
# 「模型未给主体」与「模型给出主体」两种情形；digest 上限由 `bookkeeping.note` 写入点把守）。
SUBJECT_BACKFILL_NOTE_TITLE: Final[str] = "主体程序回填"
SUBJECT_BACKFILL_DIGEST: Final[str] = "模型未给主体——程序候选{names}回填进 subjects"
SUBJECT_BACKFILL_SEP: Final[str] = "、"
TOOL_NAME_MISSING: Final[str] = "?"
NOTE_PHASE: Final[str] = "clarify"
NOTE_TITLE: Final[str] = "澄清"
NOTE_DIGEST_ASK: Final[str] = "澄清反问"
NOTE_DIGEST_FINALIZE: Final[str] = "澄清定稿：材料足够——直答收口"
NOTE_DIGEST_RESUME: Final[str] = "澄清回收"
NOTE_DIGEST_DISCOVER: Final[str] = "澄清钻取 ×{count}"
NOTE_DIGEST_REJECTED: Final[str] = "澄清 r{round} 被拒：{reason}"
NOTE_DIGEST_CAPPED: Final[str] = "连续澄清达上限——带材料直答"

# ── 步骤 payload 键与标记（发射方面；`specs/transport.md` 行为 6：载荷键集归发射方）──
PAYLOAD_PHASE: Final[str] = "phase"
PAYLOAD_EMISSION: Final[str] = "emission"
PAYLOAD_REJECTION: Final[str] = "rejection"
PAYLOAD_ASK_FRAME: Final[str] = "ask_frame"
PAYLOAD_CAPPED: Final[str] = "capped"
PAYLOAD_RESUME: Final[str] = "resume"
PAYLOAD_VOLATILE: Final[str] = "volatile"

# 挂起帧缺省面（`specs/transport.md` 行为 8：`ask` 帧载荷 `{frame: {kind, prompt, options,
# detail}, run_id}`；`detail` 澄清帧恒 None——真源 `recon/E1` 第 10 支）。
ASK_FRAME_DETAIL_NONE: Final[None] = None
