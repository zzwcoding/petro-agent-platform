"""parsing 的闭世界常量族（逐字迁移——真源 `appv2/runtime/subtask.py` L29-L58）。

- `chain` 闭世界两值＋`chain→tool` 对表（相位②闭合世界对账判据，真源 L33-L43）；
- 相位①动作闭世界四值（真源 L48-L54）；
- 发现预算闸拒因标记＝本块唯一机读前缀（真源 L58）；
- 理解面 `route` 闭世界两值（真源 `specs/understanding.md` 接口定义——本块为理解面
  载荷类的物理定义点，`specs/parsing.md` 行为 1／差异点①）。

**不含 `MAX_SUBTASKS_CONTRACT`／`MAX_DISCOVERS_*`**：限额数值随「注入制」退场
（`specs/parsing.md` 差异点③／行为 16）——本块源码不写裸上限值，三个限额参数由调用方
注入（`max_subtasks` 数值真源＝`walk/09` §七 Q-C＋`eng/00` F-14，`state` 承载键未落定）。
"""

from typing import Literal

# ── chain 闭世界（子问题→工具链两值；真源 subtask.py L33-L35）──────────────────
CHAIN_DATA = "data"
CHAIN_KNOWLEDGE = "knowledge"
CHAIN_KINDS: frozenset[str] = frozenset({CHAIN_DATA, CHAIN_KNOWLEDGE})

# ── 工具闭世界（chain→tool 一致性收口；真源 subtask.py L38-L43）────────────────
TOOL_DATA_QUERY = "data_query"
TOOL_DOC_RETRIEVE = "doc_retrieve"
_CHAIN_TOOL: dict[str, str] = {
    CHAIN_DATA: TOOL_DATA_QUERY,
    CHAIN_KNOWLEDGE: TOOL_DOC_RETRIEVE,
}

# ── 相位①动作闭世界（发现／分解／反问／定稿直答；真源 subtask.py L48-L54）─────
CLARIFY_DISCOVER = "discover"
CLARIFY_DECOMPOSE = "decompose"
CLARIFY_ASK = "ask"
CLARIFY_FINALIZE = "finalize"
CLARIFY_ACTIONS: frozenset[str] = frozenset(
    {CLARIFY_DISCOVER, CLARIFY_DECOMPOSE, CLARIFY_ASK, CLARIFY_FINALIZE}
)

# ── 发现预算闸拒因标记（机读甄别面恰一值；真源 subtask.py L58）─────────────────
BUDGET_REJECT_MARK = "发现预算"

# ── 理解面 route 闭世界（两形互斥；真源 `specs/understanding.md` 接口定义）──────
ROUTE_FULL: Literal["full"] = "full"
ROUTE_DIRECT: Literal["direct"] = "direct"

# ── 作答第二出口 `explore` 闭世界（V2-96 D5；真源 §五·5.1）────────────────────
# 动作名＝模型发射 JSON 的 `action` 取值（本块自有字面；与路由意图 `state.INTENT_EXPLORE`
# 同字面属**同名巧合**——一处是发射合同、一处是路由意图，两处各自单点、互不引用）。
EXPLORE_ACTION = "explore"
# 工具闭世界三值（作答侧只读检索三件；越界即拒）。
EXPLORE_TOOL_DOC_RETRIEVE = "doc_retrieve"
EXPLORE_TOOL_FETCH_SECTION = "fetch_section"
EXPLORE_TOOL_FETCH_REPORT = "fetch_report"
EXPLORE_TOOLS: frozenset[str] = frozenset(
    {
        EXPLORE_TOOL_DOC_RETRIEVE,
        EXPLORE_TOOL_FETCH_SECTION,
        EXPLORE_TOOL_FETCH_REPORT,
    }
)
# 每轮请求条数闭世界（1..2——真源 §五·5.1「每轮 requests 1..2」）。
EXPLORE_REQUEST_MIN = 1
EXPLORE_REQUEST_MAX = 2
