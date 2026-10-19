"""bookkeeping 自有闭世界常量（取值真源逐块标注；第三族的取值一律引真源、此处不复述）。

两块闭世界属本块自有（真源＝`specs/bookkeeping.md` 接口定义节）＋一块随 -B 落地（真源＝
`specs/gateway_adapter.md` 行为 5）：

- **合同追加相位闭世界**（`append_contract` 的 `phase` 取值域）：`decision`｜`clarify`｜
  `toolmatch`——合同文本追加面的相位标记集（现状锚＝旧码 `appv2/runtime/graph.py` 三处
  `contracts_appended` 标记写入；写手面真源＝`synth/S5-RunState字段矩阵.md` 的
  `contracts_appended` 行）。越界相位抛错（fail-closed，行为 8）。
- **对话链角色闭世界**（`append_message` 的 `role` 取值域）：`user`｜`assistant`｜`system`——
  同 `state.messages` 口径（接口定义节「写口入参形状」）。**`system` 位（2026-10-17 H 批·角色
  分家）**＝**链首背景块**唯一形态（每链恰一条，真源 `specs/prompts.md` 2026-10-17 H 批注）；
  环节规章**不入链**——经 `call_model` 的 `system` 注入参随本次请求走（同批注）。
- **模型调用归因桶闭世界**（`call_model` 的 `caller` 取值域）＋**桶→步型**分派表——桶真源＝
  `specs/gateway_adapter.md` 行为 5「`caller` 取值来自调用方（四桶族：理解／决策／作答／回炉）」；
  步型分派见下（六值闭世界无 understand 型）。**2026-10-19 V2-125**：加第四桶 `repair`（回炉
  修复轮——`orchestration/repair.py` 发起；此前复用 `answer` 桶，归因面无法把回炉调用与作答调用
  分开）——桶集合与分派表同批改本清单，机读面＝`tests/domains/test_v2_bookkeeping.py`。
- **过程档案 digest 写入点上限与截断可见标记**（`note` 的写入面）：上限真源＝
  `synth/S5-RunState字段矩阵.md` 的 `process_notes` 条目口径（`digest≤200`，真源
  `arch/P5b2` A-P5b2-03）；截断标记沿用同仓截断单点先例（`persistence.summary` 的
  `TRUNCATION_MARK`——「截断恒留可见标记、不静默截断」，行为 10 断言「截断可见」）。

不在此处复述的取值（一律引其真源单点）：步类型 `state.STEP_KINDS`、步状态
`persistence.STEP_STATUS_KINDS`、路由意图 `state.INTENT`、对话层来源
`state.DIALOGUE_ORIGINS`（＋来源↔角色不变量 `state.DIALOGUE_ORIGIN_ROLES`）、通知类型
`transport.NOTICE_TYPES`——「同一族两处定义」＝缺陷（`specs/state.md` 行为 9 同款纪律）。
"""

from collections.abc import Mapping

from appv2.runtimev2.state import STEP_ANSWER, STEP_DECISION, STEP_VERIFY

# ── 合同追加相位闭世界（真源 specs/bookkeeping.md 接口定义节）──────────────────────
CONTRACT_PHASE_DECISION = "decision"
CONTRACT_PHASE_CLARIFY = "clarify"
CONTRACT_PHASE_TOOLMATCH = "toolmatch"
# V2-134（2026-10-19）：加两值——`understand`／`answer` 的规章段亦并入其 user 首入包
# （承载位回链：恢复「同一 run 内相邻调用的完整请求互为前缀延伸」的追加形）。
# `decision` 为 V1 遗留值（生产无 `append_contract` 调用点）——本票不动，只登记。
CONTRACT_PHASE_UNDERSTAND = "understand"
CONTRACT_PHASE_ANSWER = "answer"

CONTRACT_PHASES: frozenset[str] = frozenset(
    {
        CONTRACT_PHASE_DECISION,
        CONTRACT_PHASE_CLARIFY,
        CONTRACT_PHASE_TOOLMATCH,
        CONTRACT_PHASE_UNDERSTAND,
        CONTRACT_PHASE_ANSWER,
    }
)

# ── 对话链角色闭世界（真源 specs/bookkeeping.md 接口定义节「写口入参形状」）──────────
# 2026-10-17 补（H 批·角色分家）：加第三值 `system`——**只承载链首背景块**（每链恰一条；
# 环节规章一律不入链，走 `call_model` 的 `system` 注入参）；`user`／`assistant` 语义零改。
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"
MESSAGE_ROLE_SYSTEM = "system"

MESSAGE_ROLES: frozenset[str] = frozenset(
    {MESSAGE_ROLE_USER, MESSAGE_ROLE_ASSISTANT, MESSAGE_ROLE_SYSTEM}
)

# ── 模型调用归因桶闭世界（`call_model` 的 `caller` 取值域）───────────────────────
# 真源＝`specs/gateway_adapter.md` 行为 5（原文：「`caller` 取值来自调用方（四桶族：理解／决策／
# 作答／回炉）」）；现状锚＝旧码 `appv2/runtime/graph.py` 的 `MODEL_KEYS`
# （`understand`／`decision`／`answer` 三值——理解／决策／作答三轮的调用归因）；第四桶
# `repair` 为 runtimev2 新增（V2-125——回炉修复轮，`orchestration/repair.py` 发起）。
CALLER_UNDERSTAND = "understand"
CALLER_DECISION = "decision"
CALLER_ANSWER = "answer"
CALLER_REPAIR = "repair"

CALLERS: frozenset[str] = frozenset(
    {CALLER_UNDERSTAND, CALLER_DECISION, CALLER_ANSWER, CALLER_REPAIR}
)

# 桶 → 步记录步型（`record_step` 的 `kind` 六值闭世界**无** understand 型）：理解轮与决策轮记
# `decision`、作答轮记 `answer`、回炉轮记 `verify`（V2-125——回炉步与核验步同型，真源
# `orchestration/repair.py` 的 `STEP_VERIFY` 步标题「核验回炉」）。现状锚＝旧码 `understand_node`
# 记步 `STEP_DECISION`（`appv2/runtime/graph.py`）＋常规步序四连 `decision`
# （`tests/api/test_v2_asks.py` 的 `HAPPY_STEP_KINDS`）；「每个模型调用 step 落 Manifest」＝
# `specs/agent-loop.md` 验收表行 18。
CALLER_STEP_KINDS: Mapping[str, str] = {
    CALLER_UNDERSTAND: STEP_DECISION,
    CALLER_DECISION: STEP_DECISION,
    CALLER_ANSWER: STEP_ANSWER,
    CALLER_REPAIR: STEP_VERIFY,
}

# ── 确定性直答定型值（`RunState.draft_kind`）───────────────────────────────────
# 真源＝`specs/bookkeeping.md` 行为 12／14 逐字 `draft_kind="direct"`（字段释义真源＝
# `specs/answering.md`：`""`＝待核验草稿、`direct`＝确定性直答——`state` 侧只释义、未供该常量）。
# 单点落此，不在多处再写一遍（`converge` 与 `direct_answer` 同引这一处）。
DRAFT_KIND_DIRECT = "direct"

# ── 过程档案 digest 写入点上限＋截断可见标记（行为 10；`note` 写入面）────────────
# 上限真源＝`synth/S5-RunState字段矩阵.md` 的 `process_notes` 条目口径（`digest≤200`，真源
# `arch/P5b2` A-P5b2-03）——上限「在写入点」生效：截断只发生在 `bookkeeping.note`，消费侧读到的
# 已是受控长度。截断**恒留可见标记**（不静默截断），标记**计入上限**（输出 `len ≤ 上限`）——与同仓
# 截断单点 `persistence.summary` 同口径（该处标注真源 `specs/persistence.md` 行为 13；本块复述其
# **口径**、不复述其数值，也不引其行为面）。
NOTE_DIGEST_LIMIT = 200
TRUNCATION_MARK = "…"
