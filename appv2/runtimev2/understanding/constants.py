"""understanding 的接线常量与机读字段名（本块自有的唯一常量点；闭世界取值一律引真源）。

真源＝`specs/understanding.md` 行为 1／2／9／12／13 与「不降级与静默禁令」节；`specs/modules.md`
`## understanding` 卡。本模块只落**接线面**常量（模型调用归因桶／过程档案标题／事件面取值／
机读上报字段名／schema 拒回喂载荷文案骨架／引号自修受理文案／收敛拒答文案）——**不复述任何
闭世界族的取值**：

- 步类型与步状态：引 `state.STEP_DECISION`（`STEP_KINDS` 的真源在 `state`）与 `persistence` 包根的
  `STEP_STATUS_FAILED`（`STEP_STATUS_KINDS` 的真源在 `persistence`——**引真源、不复述字面**；该
  引入面为规格「触及的模块」表外的登记项，见票面回报）；
- 通知类型：**不在本模块立第二份清单**——`NOTICE_*` 两字面只作取值指针，其合法性与闭世界由
  写入面把守（`bookkeeping.notice` 按 `transport.NOTICE_TYPES` 逐值判，越界即抛——fail-closed）；
- 模型调用归因桶：`MODEL_CALLER` 的字面真源＝`bookkeeping` 的归因桶闭世界
  （`specs/gateway_adapter.md` 行为 5「三桶族：理解／决策／作答」）——**本块不引其常量模块**
  （R2：业务相位只经公共层包根、禁深层子模块），故以字面指针落此，落点唯一。

`ROLE_USER` 同款：对话链角色闭世界（`user`｜`assistant`）的真源在 `bookkeeping` 写口
（`append_message` 自判、越界即抛），本块只作调用面字面。
"""

from appv2.runtimev2.state import STEP_DECISION

# ── 模型调用归因（`bookkeeping.call_model` 的 `caller`）───────────────────────────
# 真源＝`bookkeeping` 归因桶闭世界「understand／decision／answer」（`specs/gateway_adapter.md`
# 行为 5）；本块为理解轮，恒取理解桶（字面唯一落点——R2 禁引 `bookkeeping.constants` 深层）。
MODEL_CALLER = "understand"

# ── 过程档案与对话链面（`bookkeeping.note`／`append_message`）────────────────────
PHASE = "understand"  # 过程档案 phase 标记／机读上报 payload 的 phase 字段（同桶名）
READ_NOTE_TITLE = "读题"  # 模型原话留痕条目标题（行为 9）
TASK_BOOK_NOTE_TITLE = "任务书装配"  # 装配一次幂等标记条目标题（行为 9）
TASK_BOOK_NOTE_DIGEST = "任务书已装配（指令区→数据区〔来源＝台账活体投影〕→输出契约区）"
ROLE_USER = "user"  # 对话链角色（真源＝`bookkeeping` 写口闭世界，越界由其抛错）
ROLE_ASSISTANT = "assistant"  # 模型应答追加链尾的角色（同款）

# ── 事件面（行为 12；真源 `synth/S6-事件与帧目录.md` §一 text 行）─────────────────
TEXT_EVENT = "text"  # runtime 九类事件之一
TEXT_EVENT_KIND = "understanding"  # text 载荷的可选 kind——理解旁白灰条

# ── 机读上报面（「不降级与静默禁令」节：如实上报必带 notice ＋ step payload 字段）──
# 载体的定义点＝本块（叙事样板待主窗裁）；`notice.type` 取值取自事件闭世界 `NOTICE_TYPES`
# （`specs/transport.md` 接口定义节二十九值）——**该族无「候选违约／解析失败」专属值**，
# 故取语义最近的既有值，登记见票面回报（新增类型须同批入列，本块不私扩闭世界）。
NOTICE_CANDIDATE_VIOLATION = "unsupported_claim"  # 名录外候选＝无台账依据的断言（如实注记）
NOTICE_PARSE_FAILURE = "decision_rejected"  # 读题发射不可解析（V1 同族：发射被拒如实注记）
REPORT_STEP_KIND = STEP_DECISION  # 步型＝decision（六值闭世界无 understand 型，同归因桶判决）
PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_EVENT_KEY = "event"
PAYLOAD_EVENT_CANDIDATE_VIOLATION = "candidate_out_of_roster"
PAYLOAD_EVENT_PARSE_FAILURE = "parse_failure"
PAYLOAD_CANDIDATES_KEY = "metric_candidates"
PAYLOAD_OFFENDERS_KEY = "offenders"
PAYLOAD_RAW_EXCERPT_KEY = "raw_excerpt"

# ── 直答结构核验面（行为 5／11；退回口径与「直答退回」注记）───────────────────────
# 注记条目标题（钉 pin-26 渲染面：过程记录入档案、不入 dialogue）
DIRECT_REJECT_NOTE_TITLE = "直答退回"
NOTICE_DIRECT_REJECTED = "unsupported_claim"  # 直答断言无台账依据（同候选违约取语义最近既有值）
PAYLOAD_EVENT_DIRECT_REJECTED = "direct_rejected"
PAYLOAD_DIRECT_TEXT_KEY = "direct_text"
PAYLOAD_CLOSURE_HITS_KEY = "closure_hits"
PAYLOAD_HIT_KIND_KEY = "kind"
PAYLOAD_HIT_TOKEN_KEY = "token"

# ── schema 拒回喂面（行为 13；2026-10-16 补·流水 67——照澄清相位拒因载荷体例）──────────────
# 回喂载荷＝链尾一条 user 消息（链上直投、无外层壳）＋过程档案一条注记；本块自有的唯一常量点。
RETRY_NOTE_TITLE = "读题回喂重试"  # 过程档案注记条目标题（pin-26 渲染面：入档案、不入 dialogue）
FEEDBACK_JOIN = "\n"  # 三段连接符（照澄清面块件「\n」连接体例）
FEEDBACK_REASON = "【拒因】{reason}"  # 段一：具体不合项（取 parsing 的诊断出口——「哪一条」）
FEEDBACK_EXPECTED = (  # 段二：期望形（照理解面输出契约与样例集——metric_candidates 无命中＝空数组）
    '【期望形】{"route":"full","text":"理解：〈一句话题意〉",'
    '"metric_candidates":["〈台账名录里的指标名〉"]}'
    '（或 {"route":"direct","text":"〈回复内容〉"}）——route 只许这两个取值；'
    "route=full 时 text 与 metric_candidates 均为必填，metric_candidates 是字符串数组、"
    "无命中指标时给空数组 []；route=direct 时无 metric_candidates 键。"
)
FEEDBACK_TAIL = (
    "——只修正不合项，其余内容照旧，重新输出一个 JSON 对象（不要输出 JSON 之外的解释文字）。"
)

# ── 读题引号自修受理（行为 13 首段后的**格式层确定性受理**；2026-10-17 EB5a 补）─────────────
# 真病因（真机 3/3：EB3-NQ-C3／NQ-D3／NQ-M1）＝模型把题干里的成对引号**原样照搬进 JSON 字符串值
# 且不转义**（`"text":"…（2）"20/40目砾石挤压充填"在报告中…"`）→ `json.loads` 断裂。程序侧的处理＝
# **受理既有确定性引号自修件**（`parsing.parse_with_quote_repair`／`repair_inner_quotes`——V2-60
# ③层：只动格式不动语义，值内裸引号换中文引号、修后须全文可解析才受理）；零模型、零占轮、
# **不占回喂上限**。
# 通知类型取值＝既有闭世界值（真源 `specs/transport.md` 的 `NOTICE_TYPES`——`bookkeeping.notice`
# 写口逐值把守，越界即拒；本模块不复述该族清单）；
# 注记条目标题＝过程档案面（pin-26 渲染面：入档案、不入 dialogue）。
NOTICE_EMISSION_QUOTE_REPAIR = "emission_quote_repair"
# 文案走**白话**（与同 notice 型在澄清相位的同面文案同气质——两处各落本块常量点〔R1 禁跨相位
# import〕；若 Owner 要求逐字同句，归公共面另批，登记见票面回报）。
QUOTE_REPAIR_NOTICE_CONTENT = (
    "这次的读题里引号写法不对——已经自动改正后继续（没有多花模型调用，也没有多占一轮）。"
)
QUOTE_REPAIR_NOTE_TITLE = "读题引号自修"

# ── schema 两读皆拒的收敛拒答（行为 13 尾；2026-10-17 EB3 D4.4 补；文案按 2026-10-17 EB5a 改）──
# 拒答＝**直答旁路**一条确定性正文（`bookkeeping.direct_answer` 三键）——run 走收口、
# **不判 failed、不零交付**；不合项取同一诊断出口（`parsing.understanding_schema_feedback`）。
# **EB5a 改文案**：①收敛句改用同一句「没能完全读懂这道题，请补充说明」（全相位统一口径）；②带
# **材料面如实**（本相位结构上零材料——检索尚未开始；照 `bookkeeping` 触界收敛正文的零材料形）。
CONVERGE_NOTE_TITLE = "读题收敛拒答"  # 过程档案注记条目标题（pin-26 渲染面：入档案、不入 dialogue）
CONVERGE_DRAFT_TEMPLATE = (
    "没能完全读懂这道题，请补充说明——模型两次给出的读法都不合格式"
    "（具体不合项：{reason}；已带着它回喂重试过一次仍未通过）。"
    "已获材料：无（检索尚未开始，没有可交付的材料，如实说明）。"
    "为不猜、不取默认值、不出低质答案，本次不继续作答——"
    "请把问题再说得具体些（比如指明指标、时间范围、井号）后重问。"
)

# ── 原始应答片段留痕（`UnderstandingParseError` 携带；上限与可见标记口径同仓截断先例）──
RAW_EXCERPT_LIMIT = 200
TRUNCATION_MARK = "…"
