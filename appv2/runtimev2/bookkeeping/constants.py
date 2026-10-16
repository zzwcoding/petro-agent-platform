"""bookkeeping 自有闭世界常量（取值真源逐块标注；第三族的取值一律引真源、此处不复述）。

两块闭世界属本块自有（真源＝`specs/bookkeeping.md` 接口定义节）＋一块随 -B 落地（真源＝
`specs/gateway_adapter.md` 行为 5）：

- **合同追加相位闭世界**（`append_contract` 的 `phase` 取值域）：`decision`｜`clarify`｜
  `toolmatch`——合同文本追加面的相位标记集（现状锚＝旧码 `appv2/runtime/graph.py` 三处
  `contracts_appended` 标记写入；写手面真源＝`synth/S5-RunState字段矩阵.md` 的
  `contracts_appended` 行）。越界相位抛错（fail-closed，行为 8）。
- **对话链角色闭世界**（`append_message` 的 `role` 取值域）：`user`｜`assistant`——同
  `state.messages` 口径（接口定义节「写口入参形状」）。
- **模型调用归因桶闭世界**（`call_model` 的 `caller` 取值域）＋**三桶→步型**分派表——桶真源＝
  `specs/gateway_adapter.md` 行为 5「`caller` 取值来自调用方（三桶族：理解／决策／作答）」；
  步型分派见下（六值闭世界无 understand 型）。

不在此处复述的取值（一律引其真源单点）：步类型 `state.STEP_KINDS`、步状态
`persistence.STEP_STATUS_KINDS`、路由意图 `state.INTENT`、对话层来源
`state.DIALOGUE_ORIGINS`（＋来源↔角色不变量 `state.DIALOGUE_ORIGIN_ROLES`）、通知类型
`transport.NOTICE_TYPES`——「同一族两处定义」＝缺陷（`specs/state.md` 行为 9 同款纪律）。
"""

from collections.abc import Mapping

from appv2.runtimev2.state import STEP_ANSWER, STEP_DECISION

# ── 合同追加相位闭世界（真源 specs/bookkeeping.md 接口定义节）──────────────────────
CONTRACT_PHASE_DECISION = "decision"
CONTRACT_PHASE_CLARIFY = "clarify"
CONTRACT_PHASE_TOOLMATCH = "toolmatch"

CONTRACT_PHASES: frozenset[str] = frozenset(
    {CONTRACT_PHASE_DECISION, CONTRACT_PHASE_CLARIFY, CONTRACT_PHASE_TOOLMATCH}
)

# ── 对话链角色闭世界（真源 specs/bookkeeping.md 接口定义节「写口入参形状」）──────────
MESSAGE_ROLE_USER = "user"
MESSAGE_ROLE_ASSISTANT = "assistant"

MESSAGE_ROLES: frozenset[str] = frozenset({MESSAGE_ROLE_USER, MESSAGE_ROLE_ASSISTANT})

# ── 模型调用归因桶闭世界（`call_model` 的 `caller` 取值域）───────────────────────
# 真源＝`specs/gateway_adapter.md` 行为 5（原文：「`caller` 取值来自调用方（三桶族：理解／决策／
# 作答）」）；现状锚＝旧码 `appv2/runtime/graph.py` 的 `MODEL_KEYS`（`understand`／`decision`／
# `answer` 三值——理解／决策／作答三轮的调用归因）。
CALLER_UNDERSTAND = "understand"
CALLER_DECISION = "decision"
CALLER_ANSWER = "answer"

CALLERS: frozenset[str] = frozenset({CALLER_UNDERSTAND, CALLER_DECISION, CALLER_ANSWER})

# 三桶 → 步记录步型（`record_step` 的 `kind` 六值闭世界**无** understand 型）：理解轮与决策轮记
# `decision`、作答轮记 `answer`。现状锚＝旧码 `understand_node` 记步 `STEP_DECISION`
# （`appv2/runtime/graph.py`）＋常规步序四连 `decision`（`tests/api/test_v2_asks.py` 的
# `HAPPY_STEP_KINDS`）；「每个模型调用 step 落 Manifest」＝`specs/agent-loop.md` 验收表行 18。
CALLER_STEP_KINDS: Mapping[str, str] = {
    CALLER_UNDERSTAND: STEP_DECISION,
    CALLER_DECISION: STEP_DECISION,
    CALLER_ANSWER: STEP_ANSWER,
}

# ── 确定性直答定型值（`RunState.draft_kind`）───────────────────────────────────
# 真源＝`specs/bookkeeping.md` 行为 12／14 逐字 `draft_kind="direct"`（字段释义真源＝
# `specs/answering.md`：`""`＝待核验草稿、`direct`＝确定性直答——`state` 侧只释义、未供该常量）。
# 单点落此，不在多处再写一遍（`converge` 与 `direct_answer` 同引这一处）。
DRAFT_KIND_DIRECT = "direct"
