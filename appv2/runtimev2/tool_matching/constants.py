"""tool_matching 的闭世界常量与接线字面（本块唯一常量点；闭世界取值一律引真源）。

真源＝`specs/tool_matching.md`（已定稿）接口定义节与行为 4／5／11；卡 `specs/modules.md`
`## tool_matching`。本模块只落**取值与接线字面**、不落行为：

- **拒因枚举六类**（`MatchReason.kind`）：成员名**逐字**取规格 `:66`（前五类与「错误契约」
  `:72` 逐字同源；第六类 `malformed_matches` ＝支形状失败，成员名照 V1 码面）——
  「同一族两处定义」禁止，本处即该族 V2 唯一落点；
- **`mention_mode` 两值**（行为 5；规格 `:56`／`:75`）与 **`direction` 两值**（行为 5）；
- **`chain` 两值**：**不自建**——取值真源＝`parsing` 单点（`CHAIN_KINDS`／`CHAIN_DATA`／
  `CHAIN_KNOWLEDGE`），本模块只**别名转出**（`DATA_CHAIN`／`KNOWLEDGE_CHAIN`），禁第二份；
- **接线字面**（模型调用归因桶／过程档案相位标记／对话链角色／通知类型／机读 payload 键）：
  取值真源在各自的单点模块（`bookkeeping` 归因桶闭世界／`prompts.PHASE_TOOLMATCH`／
  `bookkeeping` 写口闭世界／`transport.NOTICE_TYPES`）——本模块只作**字面指针**，
  合法性与越界把守交写入面（R2：业务相位只经公共层包根、禁深层子模块）；
- **拒因映射表** `REJECTION_KIND_BY_MARK`：解析面逐字拒文 → 拒因枚举的**机械适配**（行为 11）。
  键＝**逐字拒文的稳定子串**（字面真源＝V1 码面 `appv2/runtime/subtask.py` 与解析单点
  `parsing/parsers.py`，两处禁自撰）；**不是语义词表**——只在**解析拒文**上做子串匹配，
  不经问句／子问题／台账文本，故与行 10 的「零词表」不抵（规格「豁免面＝结构归一／形态处理」）。
"""

from collections.abc import Mapping

from appv2.runtimev2.parsing import CHAIN_DATA, CHAIN_KNOWLEDGE
from appv2.runtimev2.prompts import PHASE_TOOLMATCH

# ── chain 闭世界（两值；成员判定引 parsing 的 `CHAIN_KINDS`）——取值真源＝parsing 单点，
# 本处只别名转出，禁第二份 ─────────────────────────────────────────────────────
DATA_CHAIN = CHAIN_DATA
KNOWLEDGE_CHAIN = CHAIN_KNOWLEDGE

# ── direction 闭世界（两值；行为 5）────────────────────────────────────────────
DIRECTION_ASC = "asc"
DIRECTION_DESC = "desc"
DIRECTIONS: frozenset[str] = frozenset({DIRECTION_ASC, DIRECTION_DESC})

# ── mention_mode 闭世界（两值；行为 5——pin-31 判断产出面的字段载体）─────────────
MENTION_EXECUTED = "executed"
MENTION_MENTIONED_ONLY = "mentioned_only"
MENTION_MODES: frozenset[str] = frozenset({MENTION_EXECUTED, MENTION_MENTIONED_ONLY})

# ── MatchReason.kind 六类闭世界（成员名逐字取规格 :66；顺序＝规格表序）───────────
KIND_MISSING_SUBTASK = "缺配"
KIND_DUPLICATE = "多配"
KIND_UNKNOWN_ID = "编号不符"
KIND_MISSING_REQUIRED = "必填缺"
KIND_ENUM_OUT_OF_RANGE = "枚举越界"
KIND_MALFORMED = "malformed_matches"
MATCH_REASON_KINDS: frozenset[str] = frozenset(
    {
        KIND_MISSING_SUBTASK,
        KIND_DUPLICATE,
        KIND_UNKNOWN_ID,
        KIND_MISSING_REQUIRED,
        KIND_ENUM_OUT_OF_RANGE,
        KIND_MALFORMED,
    }
)

# ── 接线字面（取值真源在各自单点模块，本块只作字面指针）──────────────────────────
# 模型调用归因桶：真源＝`bookkeeping` 归因桶闭世界「understand／decision／answer」
# （`specs/gateway_adapter.md` 行为 5）——本块为决策轮，故取「决策」桶。
MODEL_CALLER = "decision"
# 过程档案相位标记／机读 payload 的 phase 字段：真源＝`prompts.PHASE_TOOLMATCH`
# （同值＝`bookkeeping` 合同追加相位闭世界的 `toolmatch`）。
PHASE = PHASE_TOOLMATCH
# 对话链角色（真源＝`bookkeeping` 写口闭世界，越界由其抛错）。
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
# 通知类型（真源＝`transport.NOTICE_TYPES` 二十九值；发射被拒＝既有同族值，本块不私扩闭世界）。
NOTICE_DECISION_REJECTED = "decision_rejected"
# 机读 payload 键（本块自有——步载荷拒因字段的载体形状）。
PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_REJECTION_KEY = "rejection"
PAYLOAD_KIND_KEY = "kind"
PAYLOAD_REASON_KEY = "reason"

# ── 拒因映射表：解析面逐字拒文 → 拒因枚举（行为 11 机械适配；键为逐字拒文子串）────
# 序＝先窄后宽（多词键在前），首命中即断；键全部取自逐字稿载体（本处禁自撰）。
REJECTION_KIND_BY_MARK: Mapping[str, str] = {
    # 缺配（覆盖缺口／整组缺 matches）
    "覆盖缺口": KIND_MISSING_SUBTASK,
    "缺 matches": KIND_MISSING_SUBTASK,
    # malformed_matches（支形状失败／发射不可解析＝同族形状失败）
    "支须为对象": KIND_MALFORMED,
    "工具匹配不可解析": KIND_MALFORMED,
    # 编号不符（支缺 id／id 不在问题组内）
    "支缺 id": KIND_UNKNOWN_ID,
    "不在问题组内": KIND_UNKNOWN_ID,
    # 多配
    "id 重复": KIND_DUPLICATE,
    # 必填缺（逐槽位）
    "缺 tool": KIND_MISSING_REQUIRED,
    "data 链缺 plan": KIND_MISSING_REQUIRED,
    "plan 缺 metric_slot": KIND_MISSING_REQUIRED,
    "knowledge 链缺 retrieval_need": KIND_MISSING_REQUIRED,
    "retrieval_need 缺 question": KIND_MISSING_REQUIRED,
    # 枚举越界（chain 越界／链-工具不一致）
    "chain 越界": KIND_ENUM_OUT_OF_RANGE,
    "chain/tool 不一致": KIND_ENUM_OUT_OF_RANGE,
}
