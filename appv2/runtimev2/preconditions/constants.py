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
TITLE_TEMPLATE = "前置条件机：{subtask}={decision}"
TITLE_RULE_TEMPLATE = "前置条件机：{subtask}={decision}（{rule}）"

NOTE_MENTION_ONLY = (
    "禁用词结论「仅提及（mentioned_only）」——按模型结论放行，不按该废弃口径出数"
    "（判定序位 1 机械分派，pin-31）"
)
NOTE_CHAIN_SWITCH_REENTRY = (
    "换链回炉提议：本子问题命中软失败面（在册未绑定／题眼域错）——回炉①澄清相位改链"
    "重决策（一次为界；同支再触发＝如实拒答终局）"
)
WINDOW_ASK_PROMPT_TEMPLATE = (
    "子问题 {subtask} 的时间范围未能确定（模型发射载荷窗槽双 null＝不能确定）"
    "——请先选定时间范围（模糊时间词不解析、不默认）"
)
CHAIN_SWITCH_TERMINAL_TEXT_TEMPLATE = (
    "换链回炉已用尽（一次为界）：坚持 data 链同参（指纹 {fingerprint}…在簿）——{tail}"
)
CHAIN_SWITCH_TERMINAL_TAIL_UNBOUND = "未绑定口径如实拒答，不代答"
CHAIN_SWITCH_TERMINAL_TAIL_DOMAIN = "题眼井不在数据链井闭世界——域错如实拒答，不代答"

NOTICE_REFUSED_TEMPLATE = "前置条件机：子问题 {subtask} 拒答（判定位 {rule}）——{human}"
NOTICE_ASK_TEMPLATE = "前置条件机：子问题 {subtask} 等用户（{kind}）——{prompt}"
NOTICE_NOTE_TEMPLATE = "前置条件机：子问题 {subtask} 放行（注记 {count} 条）——{digest}"
NOTICE_CHAIN_SWITCH_TEMPLATE = "前置条件机：子问题 {subtask} 换链回炉提议——{digest}"
