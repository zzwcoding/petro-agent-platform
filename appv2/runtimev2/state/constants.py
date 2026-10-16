"""state 的常量单点：三族闭世界（真源 `recon/I2a`）与限额真源数值（真源 `recon/K` R-K-72…R-K-76）。

三族都是 `RunState` 字段的取值域（`specs/state.md` 行为 9）；取值与条数真源＝
`docs/runtime-refactor/recon/I2a-状态常量与清单.md`（22 条常量实测）。限额数值真源＝
`docs/runtime-refactor/recon/K-上下文事件指南预算.md` R-K-72…R-K-76（逐键承载 `Budget` 七键）。

本模块只落常量、不落行为：`Budget` 的字段缺省引这里的名字，判定与调用点同引——「同一件事
多处数字」的预防面（`specs/state.md` 行为 10／风险 8）；全仓第二处自建集合与裸状态字面量把守
＝缺陷（行为 9，机检面 `::no_second_source_of_constants`）。
"""

# ── step 类型六值闭世界（真源 recon/I2a R-I2a-01；ReAct 周期）────────────────────
STEP_DECISION = "decision"
STEP_DISCOVER = "discover"
STEP_EXECUTE = "execute"
STEP_OBSERVE = "observe"
STEP_VERIFY = "verify"
STEP_ANSWER = "answer"

STEP_KINDS: frozenset[str] = frozenset(
    {STEP_DECISION, STEP_DISCOVER, STEP_EXECUTE, STEP_OBSERVE, STEP_VERIFY, STEP_ANSWER}
)

# ── run 状态四值闭世界（真源 recon/I2a R-I2a-02；running→waiting_ask→（resume）→终态）──
RUN_RUNNING = "running"
RUN_WAITING_ASK = "waiting_ask"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"

RUN_STATUS_KINDS: frozenset[str] = frozenset(
    {RUN_RUNNING, RUN_WAITING_ASK, RUN_COMPLETED, RUN_FAILED}
)

# ── 路由意图十值闭世界（真源 recon/I2a R-I2a-03／R-I2a-04；条件边唯一判据）──────
# 四相位不新增 clarify 意图——沿用 INTENT_DECISION 承载（R-I2a-04）；toolmatch／
# precondition／batch 三相位值随 V2-34 入闭世界。
INTENT_DECISION = "decision"
INTENT_DISCOVER = "discover"
INTENT_EXECUTE = "execute"
INTENT_OBSERVE = "observe"
INTENT_VERIFY = "verify"
INTENT_ANSWER = "answer"
INTENT_END = "end"
INTENT_TOOLMATCH = "toolmatch"
INTENT_PRECONDITION = "precondition"
INTENT_BATCH = "batch"

INTENT: frozenset[str] = frozenset(
    {
        INTENT_DECISION,
        INTENT_DISCOVER,
        INTENT_EXECUTE,
        INTENT_OBSERVE,
        INTENT_VERIFY,
        INTENT_ANSWER,
        INTENT_END,
        INTENT_TOOLMATCH,
        INTENT_PRECONDITION,
        INTENT_BATCH,
    }
)

# ── 限额真源数值（真源 recon/K R-K-72…R-K-76——七键逐键承载；`Budget` 缺省引此）──
MAX_ROUNDS = 3  # R-K-72 轮数上限（轮＝LLM 决策周期）
MAX_DISCOVERS_PER_ROUND = 2  # R-K-73 轮内发现上限
MAX_EXECUTES_PER_ROUND = 2  # R-K-73 轮内主执行上限
TOTAL_SECONDS = 300.0  # R-K-74 单段总时长
TOOL_TIMEOUT_SECONDS = 30.0  # R-K-74 单工具超时
MAX_DISCOVERS_PER_RUN = 10  # R-K-75 全 run 发现上限
ASK_CAP = 6  # R-K-76 连续反问截断上限

# 触界注记的 `type` 值（`Convergence.notice["type"]`）：真源＝`specs/transport.md` 的
# `NOTICE_TYPES`（二十二值，含本值）。类型取值闭世界归 `transport`——本块只定义「注记恰三键」
# 的形状、不复述取值集（`specs/modules.md` `## state` 卡注）；本块守 R4 不 import `transport`，
# 故以值引用＋真源指针落此单点，不在别处再写一遍。
_CONVERGENCE_NOTICE_TYPE = "budget_converged"
