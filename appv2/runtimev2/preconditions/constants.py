"""preconditions 的常量单点：三态闭世界 ＋ ask 两形与帧映射 ＋ 判定序八位 ＋ 写口字面。

真源＝`specs/preconditions.md`（接口定义节三态闭世界与两形映射 `:37–:53`；判定序明文表
`:84–:93`；序 2 位输入口径注 `:95`）＋`specs/modules.md` `## preconditions` 卡（签名以卡为准）。

- **三态闭世界**：`DECISION_ALLOW`／`DECISION_REFUSE`／`DECISION_ASK`——`decision` 越界判失败
  （不猜、不取默认；行为 1／2＋验收 2 行）。
- **`AskReason.kind` 两形 ＋ 唯一映射表**（`AskReason.kind` → ask 帧 `frame.kind`）：
  `external_table_approval` → `external_table_approval`；`caliber_clarify` → `clarify`（帧侧
  闭世界真源 `docs/runtime-refactor/synth/S6-事件与帧目录.md` §一；**发帧与映射由
  `orchestration`／`transport` 承接**，两处取值不得各说各话——本表即对账依据）。
- **判定序八位**：`RULE_ORDER` 逐字按判定序明文表位次取序（位 1 闸1 禁用词 → 位 8 闸6 单井支持，
  6 主闸号＋2 子闸）——取值**引真源不复述**：八位标识真源＝`appv2.tools` 闸件公开面
  （`HIT_RULE_*`／`HIT_RULES`，包根导出；位 2 与位 5／6 的标识由该闭世界逐字给出）。
- **写口字面**：步类型引 `state.STEP_DECISION`；notice 类型的取值真源＝`transport.NOTICE_TYPES`
  （本模块不复述取值集，只落本块选用的字面）；步 payload 键名与本块文案落此单点。
- **`mention_mode` 两值**（真源 `specs/tool_matching.md:56`／`:75`——「提及 vs 执行」结论由
  `tool_matching` 的模型产出，**机械分派**在本块判定序第 1 位，pin-31）：本块守 R1 不 import
  相位块，故按真源逐字落本单点，**不新增第三值**。
"""

from __future__ import annotations

from collections.abc import Mapping

from appv2.runtimev2.state import STEP_DECISION
from appv2.tools import (
    HIT_RULE_ASK,
    HIT_RULE_BAN,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FRESHNESS_WINDOW,
    HIT_RULE_FUZZY_WINDOW,
    HIT_RULE_NORMALIZED_SLOT,
    HIT_RULE_SINGLE_WELL,
    HIT_RULE_UNREGISTERED_METRIC,
)

# ── 三态闭世界（规格 :39／:55——`decision`，越界判失败）────────────────────────────
DECISION_ALLOW = "allow"
DECISION_REFUSE = "refuse"
DECISION_ASK = "ask"

DECISIONS: frozenset[str] = frozenset({DECISION_ALLOW, DECISION_REFUSE, DECISION_ASK})

# ── AskReason.kind 两形（规格 :48）＋ 唯一映射表（规格 :53）────────────────────────
ASK_KIND_EXTERNAL_TABLE_APPROVAL = "external_table_approval"
ASK_KIND_CALIBER_CLARIFY = "caliber_clarify"

ASK_KINDS: frozenset[str] = frozenset(
    {ASK_KIND_EXTERNAL_TABLE_APPROVAL, ASK_KIND_CALIBER_CLARIFY}
)

# 帧侧取值（真源 `synth/S6-事件与帧目录.md` §一：帧 `kind` 闭世界＝
# clarify｜external_table_approval）
FRAME_KIND_EXTERNAL_TABLE_APPROVAL = "external_table_approval"
FRAME_KIND_CLARIFY = "clarify"

# **唯一映射表**（规格 :53——`AskReason.kind` → ask 帧 `frame.kind`；发帧归 `orchestration`／
# `transport`，两处取值不得各说各话）：`external_table_approval` → 同名；
# `caliber_clarify` → `clarify`。
FRAME_KIND_BY_ASK_KIND: Mapping[str, str] = {
    ASK_KIND_EXTERNAL_TABLE_APPROVAL: FRAME_KIND_EXTERNAL_TABLE_APPROVAL,
    ASK_KIND_CALIBER_CLARIFY: FRAME_KIND_CLARIFY,
}

# ── mention_mode 两值（真源 `specs/tool_matching.md:56`／`:75`；pin-31 分派面）─────
MENTION_EXECUTED = "executed"
MENTION_MENTIONED_ONLY = "mentioned_only"

MENTION_MODES: frozenset[str] = frozenset({MENTION_EXECUTED, MENTION_MENTIONED_ONLY})

# ── 判定序八位（规格 :84–:93 明文表逐位取序——标识引 tools 闸件公开面）───────────────
# 位 1 闸1 禁用词／位 2 闸1b 模糊时间词门／位 3 闸2 外表越集／位 4 闸3 合法口径（＋前置台账
# 闭世界）／位 5 闸4 在册绑定态／位 6 闸4b 软失败域闸／位 7 闸5 新鲜度窗／位 8 闸6 单井支持。
RULE_ORDER: tuple[str, ...] = (
    HIT_RULE_BAN,
    HIT_RULE_FUZZY_WINDOW,
    HIT_RULE_ASK,
    HIT_RULE_UNREGISTERED_METRIC,
    HIT_RULE_NORMALIZED_SLOT,
    HIT_RULE_CHAIN_SWITCH,
    HIT_RULE_FRESHNESS_WINDOW,
    HIT_RULE_SINGLE_WELL,
)

# allow 支形（pass／note——注记并入放行，无判定位命中；下游 tools 闸件同款口径：空串）。
HIT_RULE_NONE = ""

# ── fail-closed 判定位（错误契约：判定器抛错 → 不着 allow，转 refuse 并带拒因，规格 :58）──
# 本标识**不是判定位**（八位闭世界不增），是「闸件不可用」的结构化错误标记——非 allow 必携
# `hit_rule`（行为 8）与拒因 `rule_id` 在该路径上的唯一可诚实填写值（错误发生在闸内、位次不可知）。
# **两刀分类（2026-10-17 EB4b）**：下方 `GATE_UNAVAILABLE_TEXT` 是**回喂机面**（`human_text` →
# `subtask_results[].reason` → 答案轮模型窗 ＋ 审计对账），照 A-P6b-05 **零改动**——只改承载它的
# notice 壳（`NOTICE_REFUSED_TEMPLATE`），本字面一字不动。
RULE_GATE_UNAVAILABLE = "gate_unavailable"
GATE_UNAVAILABLE_TEXT = "前置条件机闸件不可用（判定器抛错）——按 fail-closed 如实拒答，不静默放行"

# ── 写口字面（步类型引 state 单点；payload 键名／notice 类型落本单点）────────────────
PHASE = "precondition"
STEP_KIND = STEP_DECISION

PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_SUBTASK_ID_KEY = "subtask_id"
PAYLOAD_DECISION_KEY = "decision"
PAYLOAD_HIT_RULE_KEY = "hit_rule"
PAYLOAD_NOTES_KEY = "notes"
PAYLOAD_REENTRY_KEY = "chain_switch_reentry"

# notice 类型（取值真源＝`transport.NOTICE_TYPES` 闭世界；本模块只落选用字面，不私扩闭世界）
NOTICE_SUBTASK_REFUSED = "subtask_refused"
NOTICE_ASK_APPROVAL = "approval_gate_pending"
NOTICE_VERDICT_NOTE = "decision_note"
NOTICE_CHAIN_SWITCH = "chain_switch_reentry"

# ── 本块文案（确定性：模板单点，调用点只填空；文案不含语义判据）──────────────────────
# **两刀分类（2026-10-17 EB4b 程序文案白话化）**：
# - **上屏面**（本批白话化）＝notice 帧内容（`NOTICE_*_TEMPLATE` 四壳；web `NoticeRow` 逐条渲染
#   `content`）＋ ask 帧 `prompt`（`WINDOW_ASK_PROMPT_TEMPLATE`——web 反问卡正文）＋ 经 notice
#   digest 带入的两条 NOTE（`NOTE_MENTION_ONLY`／`NOTE_CHAIN_SWITCH_REENTRY`）；
# - **非上屏面**（票面口径：上屏路径＝正文／supplement／notice／ask 帧）＝步帧标题
#   （`TITLE_TEMPLATE`／`TITLE_RULE_TEMPLATE`，进 step 帧标题／过程档案）——本批**零改**；
# - **回喂机面（A-P6b-05 零改动）**＝`GATE_UNAVAILABLE_TEXT`／`CHAIN_SWITCH_TERMINAL_*`：二者是
#   `RefusalReason.human_text`，既嵌 notice 壳又经 `execution._refusal_text` →
#   `subtask_results[].reason` → 答案轮「子问题结果清单」进**模型窗**（`prompts.answer_round`），
#   是对账面。故本批只改其外围 notice 壳，`{human}` 槽逐字不动。
TITLE_TEMPLATE = "前置条件机：{subtask}={decision}"
TITLE_RULE_TEMPLATE = "前置条件机：{subtask}={decision}（{rule}）"

# 2026-10-17 EB4b：两条 NOTE 经 `{digest}` 进 notice（＝上屏面），去「该废弃口径／在册未绑定／
# 题眼域错／回炉改链」工程腔；放行与回炉触发判据在 `core._allow_of`／闸件 `judge`，与本话术无关
# （判定面语义零改）。上屏文本去票据号（`pin-31` 留本注与 `specs` 真源——业务用户读不到）。
NOTE_MENTION_ONLY = (
    "这个词只是被提到、不是真要查它的数——按判断放行，不用这个已废弃的说法出数"
    "（系统按判定序第 1 位自动放行，不额外判断）"
)
NOTE_CHAIN_SWITCH_REENTRY = (
    "这一问的取数方式走不通（名册里没有它的数值，或问的井不在数据范围内）——已请系统回头"
    "重新选一次取数方式（只试一次；再走不通就如实说查不到）"
)
# ask 帧 prompt（用户看到的反问卡正文）。2026-10-17 EB4b：旧「子问题 {subtask} 的时间范围未能确定
# （模型发射载荷窗槽双 null＝不能确定）——请先选定时间范围（模糊时间词不解析、不默认）」——
# 「载荷窗槽双 null」是机器判据原文、`{subtask}` 是内部代号，业务用户都读不到，故一并去；
# 判据面零改（位 2 结构判据＝`core._window_undetermined` 读载荷窗槽，读的是 state 不是本话术）；
# 调用点 `.format(subtask=…)` 的多余键对 `str.format` 无害（模板已无该槽）。
WINDOW_ASK_PROMPT_TEMPLATE = (
    "这个问题没说清要看哪段时间——请先选一个时间范围"
    "（含糊的说法我不会自己猜，也不会默认取最近一段时间）"
)
CHAIN_SWITCH_TERMINAL_TEXT_TEMPLATE = (
    "换链回炉已用尽（一次为界）：坚持 data 链同参（指纹 {fingerprint}…在簿）——{tail}"
)
CHAIN_SWITCH_TERMINAL_TAIL_UNBOUND = "未绑定口径如实拒答，不代答"
CHAIN_SWITCH_TERMINAL_TAIL_DOMAIN = "题眼井不在数据链井闭世界——域错如实拒答，不代答"

# notice 四壳（notice 帧内容＝上屏面）。2026-10-17 EB4b：旧统一前缀
# 「前置条件机：子问题 {subtask} …」——「前置条件机」是内部工序名、「子问题」是内部说法，
# 业务用户读不到；改白话壳，机器槽位（`{subtask}`／`{rule}`／`{kind}`／`{count}`／`{human}`／
# `{prompt}`／`{digest}`）逐个保留，对账可查：机读真源是步 payload（`hit_rule`／`decision`／
# `notes`），本节只改人读壳。
NOTICE_REFUSED_TEMPLATE = "这一问没能给出结果：{human}（问题 {subtask}／规则 {rule}）"
NOTICE_ASK_TEMPLATE = "这一问在等你确认：{prompt}（问题 {subtask}／{kind}）"
NOTICE_NOTE_TEMPLATE = "这一问可以继续查：{digest}（问题 {subtask}／说明 {count} 条）"
NOTICE_CHAIN_SWITCH_TEMPLATE = (
    "这一问的取数方式走不通，已请系统回头重选：{digest}（问题 {subtask}）"
)
