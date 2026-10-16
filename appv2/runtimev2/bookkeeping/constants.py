"""bookkeeping 自有闭世界常量（取值真源逐块标注；第三族的取值一律引真源、此处不复述）。

两块闭世界属本块自有（真源＝`specs/bookkeeping.md` 接口定义节）：

- **合同追加相位闭世界**（`append_contract` 的 `phase` 取值域）：`decision`｜`clarify`｜
  `toolmatch`——合同文本追加面的相位标记集（现状锚＝旧码 `appv2/runtime/graph.py` 三处
  `contracts_appended` 标记写入；写手面真源＝`synth/S5-RunState字段矩阵.md` 的
  `contracts_appended` 行）。越界相位抛错（fail-closed，行为 8）。
- **对话链角色闭世界**（`append_message` 的 `role` 取值域）：`user`｜`assistant`——同
  `state.messages` 口径（接口定义节「写口入参形状」）。

不在此处复述的取值（一律引其真源单点）：步类型 `state.STEP_KINDS`、步状态
`persistence.STEP_STATUS_KINDS`、路由意图 `state.INTENT`、对话层来源
`state.DIALOGUE_ORIGINS`（＋来源↔角色不变量 `state.DIALOGUE_ORIGIN_ROLES`）、通知类型
`transport.NOTICE_TYPES`——「同一族两处定义」＝缺陷（`specs/state.md` 行为 9 同款纪律）。
"""

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
