"""understanding 的接线常量与机读字段名（本块自有的唯一常量点；闭世界取值一律引真源）。

真源＝`specs/understanding.md` 行为 1／2／9／12 与「不降级与静默禁令」节；`specs/modules.md`
`## understanding` 卡。本模块只落**接线面**常量（模型调用归因桶／过程档案标题／事件面取值／
机读上报字段名）——**不复述任何闭世界族的取值**：

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

# ── 原始应答片段留痕（`UnderstandingParseError` 携带；上限与可见标记口径同仓截断先例）──
RAW_EXCERPT_LIMIT = 200
TRUNCATION_MARK = "…"
