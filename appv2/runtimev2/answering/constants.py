"""answering 的接线常量与闭世界指针（本块自有的唯一常量点；闭世界取值一律引真源、此处不复述）。

真源＝`specs/answering.md`（行为约定节＋「接口定义」节五形状）与 `specs/modules.md`
`## answering` 卡。本模块只落**接线面**常量（模型调用归因桶／过程档案与步标题／事件面取值／
机读 payload 键名／收口话术），**不复述任何别处已定义的闭世界族**：

- 步类型：引 `state.STEP_ANSWER`（`STEP_KINDS` 的真源在 `state`——引真源、不复述字面）；
- 通知类型：**不在本模块立第二份清单**——两字面只作取值指针，其合法性与闭世界由写入面把守
  （`bookkeeping.notice` 按 `transport.NOTICE_TYPES` 逐值判，越界即抛——fail-closed）；
- 路由意图：引 `state.INTENT_VERIFY`／`INTENT_END`（调用点直引，此处不中转）；
- 模型调用归因桶：`MODEL_CALLER` 的字面真源＝`bookkeeping` 的归因桶闭世界
  （`specs/gateway_adapter.md` 行为 5「三桶族：理解／决策／作答」）——**本块不引其常量模块**
  （R2：业务相位只经公共层包根、禁深层子模块），故以字面指针落此，落点唯一。
"""

from appv2.runtimev2.state import STEP_ANSWER

# ── 模型调用归因（`bookkeeping.call_model` 的 `caller`）──────────────────────────
# 真源＝`bookkeeping` 归因桶闭世界「understand／decision／answer」（`specs/gateway_adapter.md`
# 行为 5）；本块为作答轮，恒取作答桶（字面唯一落点——R2 禁引 `bookkeeping.constants` 深层）。
MODEL_CALLER = "answer"

# ── 过程档案与对话链面（`bookkeeping.note`／`append_message`）────────────────────
PHASE = "answer"  # 过程档案 phase 标记（同桶名）
ROLE_USER = "user"  # 对话链角色（真源＝`bookkeeping` 写口闭世界，越界由其抛错）
ROLE_ASSISTANT = "assistant"  # 终稿追加链尾的角色（同款）
# 过程档案标记（起草留痕）：既是「模型原话只进过程档案」的落点（行为 8），也是本块自立的
# 「起草已发生」机读判据（先例＝`understanding.assembly` 的「任务书已装配」标记条目）。
DRAFT_NOTE_TITLE = "起草答案"

# ── 步面（`bookkeeping.record_step`）──────────────────────────────────────────
# 引用真源、不复述取值：`STEP_KINDS` 的取值域在 `state`（六值闭世界）。
DRAFT_STEP_KIND = STEP_ANSWER
FINALIZE_STEP_KIND = STEP_ANSWER
DRAFT_STEP_TITLE = "起草答案"
FINALIZE_STEP_TITLE = "答案收口"

# ── 事件面（真源 `synth/S6-事件与帧目录.md` §一 text／citation 两行）────────────
TEXT_EVENT = "text"  # 本块自产的增量文本事件（一段一帧）
CITATION_EVENT = "citation"  # 本块自产的引标落账事件（收口批）
# 帧载荷键：`text`＝`{content[, kind]}`（本块不带 `kind`——`kind="understanding"` 属理解步）；
# `citation`＝`{index, source, source_id, trust}`（S6 逐字）。
TEXT_PAYLOAD_CONTENT = "content"
CITATION_PAYLOAD_INDEX = "index"
CITATION_PAYLOAD_SOURCE = "source"
CITATION_PAYLOAD_SOURCE_ID = "source_id"
CITATION_PAYLOAD_TRUST = "trust"

# ── 通知分型指针（取值真源 `transport.NOTICE_TYPES`——写入面把守；本块不私扩闭世界）──
NOTICE_EMISSION_STRIP = "emission_strip"  # 发射通道残留检出（钉 pin-04 的机读面）
NOTICE_MATERIAL_TRUNCATED = "material_truncated"  # 材料截断披露（帧面分型同族）

# ── 机读 payload 键名（本块答案面步的 `citations`／`gaps` 字段——「不降级与静默禁令」节）──
PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_CITATIONS_KEY = "citations"
PAYLOAD_GAPS_KEY = "gaps"
PAYLOAD_GAP_KIND_KEY = "kind"
PAYLOAD_GAP_SUBTASK_KEY = "subtask_id"
PAYLOAD_GAP_REASON_KEY = "reason"
# 步 payload 的阶段面取值（迁移照抄 V1 answer 节点的 `"phase": "draft"／"finalize"`）。
PAYLOAD_PHASE_DRAFT = "draft"
PAYLOAD_PHASE_FINALIZE = "finalize"

# ── 子问题结果态面（`state.subtask_results` 取值域——真源 `execution`；此处只作分派指针）──
SUBTASK_STATUS_OK = "ok"  # 执行块成功实录
SUBTASK_STATUS_REFUSED = "refused"  # 前置闸拒／闸拒（终局）——非 ok 非拒者落「缺失」

# ── 确定性直答定型值指针（`state.draft_kind`）────────────────────────────────────
# 真源＝`bookkeeping.constants.DRAFT_KIND_DIRECT`（`specs/bookkeeping.md` 行为 12／14 逐字
# `draft_kind="direct"`）——**R2 禁引深层子模块**，故以字面指针落此，落点唯一。
DRAFT_KIND_DIRECT = "direct"

# ── 引用块（迁移照抄 V1 `_finalize` 的引用块形）────────────────────────────────
CITATION_BLOCK_HEAD = "\n\n引用：\n"

# ── 收口话术（本块自有文案——空白/缺失与披露面）───────────────────────────────
ZERO_MATERIAL_REASON = (
    "零实质材料（观察面无非 notice 条目）——本轮回答无材料可核，未及核验"
)
EMPTY_DRAFT_REASON = (
    "模型未产出草稿（剥离后空稿）——不推空答案，按结构化缺口如实收口"
)
MISSING_DRAFT_REASON = "起草未产出可交付答案——按结构化缺口如实收口"
SUBTASK_MISSING_REASON = "执行未取得材料（失败／重试耗尽）"
EMISSION_STRIP_CONTENT = (
    "起草面检出 JSON 通道残留（发射围栏／裸 JSON 段）——确定性剥离，不进答案面"
    "（V2-48：发射围栏确定性剥离＋通道隔离）"
)
MATERIAL_TRUNCATED_CONTENT = (
    "答案视野检索片段仅渲染 {rendered}/{total} 支（权威行集与台账卡已全量）"
    "——未渲染部分不作答（V2-61）。"
)

# ── 发射动作闭世界（`strip_emission_fences` 的域内判据）─────────────────────────
# 真源＝旧码 `appv2/runtime/graph.py` L180 `ACTION_KINDS` 四值（`docs/runtime-refactor/recon/
# A2-核验规则与归属审.md` R-A2-04「行内含裸发射令牌（action ∈ 四值闭世界）」——发射剥离的
# 逐字迁移面；R-A2-06「域外 JSON 零误伤」由此闭世界定界）。**本族不是本块新立的闭世界**：
# 判据本体（泄漏=0 的已根治态）随 V1 字面迁移、不新造；V2 侧相位①动作族另见 `parsing`
# （本块不引其深层子模块，R2），两处非同族第二定义（登记见票面回报）。
EMISSION_ACTIONS = frozenset({"discover", "execute", "ask", "finalize"})
