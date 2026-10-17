"""execution 的常量单点：两处闭世界 ＋ 发射／载荷键名 ＋ 阈值与分型（逐条注真源）。

真源＝`specs/execution.md`（接口定义节 :35–:60 两处闭世界、行为 4／13／14／15、验收测试表）；
形状取值**引真源不复述**处一律注明（如 `notify`／`gates` 的取值集归 `transport.NOTICE_TYPES`）。

- 两处闭世界：`EXEC_STATUS_KINDS`（`ok`／`failed`／`need_input`）与 `ERROR_CATEGORIES`
  （`retryable`／`bad_args`／`refused`——对齐 `specs/tools.md` 错误三档「可重试｜修参｜拒答」）；
- 行集承载分型：`ROWSET_OBSERVATION_KINDS`（行为 4——行集题不落引用，判据＝工具观察的
  `locator.kind` 集合成员判定，属规格行为 9 的豁免面「形态处理／集合成员判定」）；
- 阈值：`BIG_RESULT_THRESHOLD_CHARS`（行为 4——**数值阶段 5 待定（随真机数据定）**，本票取
  占位值并登记呈主窗；本模块内以此单点为唯一数值面，调用点与测试皆引名字、不写裸值）；
- 两闸门名（行为 13／14「闸族」互引，两闸勿混）＋计划面闸门名（行为 15，2026-10-17 EB3 D4）
  与通知类型（字面指针，取值真源＝`transport.NOTICE_TYPES` 二十九值，本模块**不私扩闭世界**）；
- 计划面确定性规则的字面面（行为 15）：排名方向二值（真源 `appv2.query.domain.DIRECTION_*`——
  R6 隔断下持同值字面，漂移由对读件看守）、计划面两态与拒因文案、「前 N」→排名归一的过程档案
  注记标题／摘要模板；
- 事件名与载荷键名：`tool`／`observation` 帧键集（真源 `docs/runtime-refactor/synth/
  S6-事件与帧目录.md` §一）＋步 payload 的记账面键名（参数／行数／拒因——规格「不降级与
  静默禁令」节点名字段）。
"""

from __future__ import annotations

# ── 执行状态闭世界（specs/execution.md:43／:62——`exec_status`，越界判失败）───────────
EXEC_STATUS_OK = "ok"
EXEC_STATUS_FAILED = "failed"
EXEC_STATUS_NEED_INPUT = "need_input"

EXEC_STATUS_KINDS: frozenset[str] = frozenset(
    {EXEC_STATUS_OK, EXEC_STATUS_FAILED, EXEC_STATUS_NEED_INPUT}
)

# ── 失败分类闭世界（specs/execution.md:49／:62——`ErrorClass.category`，三档）─────────
ERROR_RETRYABLE = "retryable"  # 超时／上游抖动／限流——只重跑此档
ERROR_BAD_ARGS = "bad_args"  # 参数错（可回炉「修参」）
ERROR_REFUSED = "refused"  # 前置闸拒／闸拒——终局、不回炉

ERROR_CATEGORIES: frozenset[str] = frozenset(
    {ERROR_RETRYABLE, ERROR_BAD_ARGS, ERROR_REFUSED}
)

# ── 行集承载分型（行为 4：行集题全量交付为默认、丢行＝0——永不落引用）───────────────
# 判据＝工具观察自带 `locator.kind`（真源 `appv2/tools/handlers.py` 的权威表行观察：
# `{"kind": "agg_row", ...}` 逐行一条）；集合成员判定＝行为 9 豁免面（非语义词表／正则）。
ROWSET_OBSERVATION_KINDS: frozenset[str] = frozenset({"agg_row"})

# ── 大结果阈值（行为 4：**非行集**大结果超阈才落引用）──────────────────────────────
# 数值真源＝阶段 5 待定（随真机数据定）；本票取占位值——调用点与测试只引本名字。
BIG_RESULT_THRESHOLD_CHARS = 4000

# ── 闸门名（发射级拒的机读标记；两闸互引勿混——行为 13／14）───────────────────────
GATE_EMPTY_PROBE = "empty_probe"  # 行为 13：同参空手重发（记 discover_fingerprint）
GATE_SAME_PARAM_REPLAY = "same_param_replay"  # 行为 14：同参重投（查发射支载荷指纹）
GATE_PLAN_FACE_METRIC = "plan_face_metric"  # 行为 15：问句指标接地闸（2026-10-17 EB3 D4.1）

# ── 计划面确定性规则（行为 15；2026-10-17 EB3 D4 补）────────────────────────────
# 排名方向二值（字面真源＝`appv2.query.domain.DIRECTION_ASC/DIRECTION_DESC`——R6 隔断不可直引，
# 本块持同值字面；漂移由 `tests/domains/test_v2_eb3_d4_defects.py` 的对读件看守）。
PLAN_DIRECTION_ASC = "asc"
PLAN_DIRECTION_DESC = "desc"
# 计划面判定两态（pass 携归一后草案；refuse 两类＝问句无注册面／注册面不符）——行为 15。
# **两刀分类（2026-10-17 EB4b）**：下方两 `PLAN_FACE_REASON_*_TEMPLATE` 是**计划面闸拒原文**
# （回喂机面，票面点名禁改面）——一字不动；`TITLE_PLAN_FACE_REJECTED_TEMPLATE` 是步帧标题
# （非上屏面）、`CONTENT_PLAN_FACE_NOTICE_PREFIX` 是 notice 内容（上屏面：已是白话前缀，零行话词
# ——核查后零改，记录以免下一轮重复核查）。
PLAN_FACE_PASS = "pass"
PLAN_FACE_REFUSE_UNGROUNDED = "ungrounded_metric"
PLAN_FACE_REFUSE_MISMATCH = "metric_out_of_question"
PLAN_FACE_REASON_UNGROUNDED_TEMPLATE = (
    "计划面闸拒（问句指标在册无绑定／未注册）：计划指标「{slot}」无问句注册面支撑——"
    "禁止回落相近列出数（不给差不多）；改链（检索问答链如实说明）或如实拒答"
)
PLAN_FACE_REASON_MISMATCH_TEMPLATE = (
    "计划面闸拒（回落相近列）：问句注册面＝{slots}，计划指标「{slot}」不在其列——"
    "禁止把问句问及的指标换成相近代用品出数（不给差不多）；改链或如实拒答"
)
TITLE_PLAN_FACE_REJECTED_TEMPLATE = "子问题 {subtask} 计划面闸拒（问句指标未接地）"
CONTENT_PLAN_FACE_NOTICE_PREFIX = "计划面闸拒（问句指标未接地）："
# 「前 N」→排名归一的留痕（过程档案一条注记——计划草案的 args 载荷已是机读留痕面，
# 本注记补人读面；不加通知类型：`transport.NOTICE_TYPES` 闭世界无专属值，本块不私扩）。
NOTE_TITLE_PLAN_NORMALIZED = "计划面归一（前 N→排名）"
NOTE_DIGEST_PLAN_NORMALIZED_TEMPLATE = (
    "问句显式「前 {limit}」：计划归一为 ranking=true／direction={direction}／limit={limit}"
    "（V1 build_query_plan 同语义——照行为不照代码）"
)

# ── 通知类型（字面指针；取值真源＝`transport.NOTICE_TYPES`——本模块不复述取值集）────
NOTICE_SAME_PARAM_REPLAY = "same_param_replay"  # 两闸拒的 notice（同族既有值）
NOTICE_MATERIAL_TRUNCATED = "material_truncated"  # 落引用／截断必披露（行为 4）
NOTICE_SUBTASK_FAILED = "subtask_failed"  # 子问题执行失败（可回炉面）
NOTICE_SUBTASK_REFUSED = "subtask_refused"  # 子问题闸拒（终局不回炉）
NOTICE_TOOL_UNAVAILABLE = "tool_unavailable"  # 重试后仍不可用——如实收敛
NOTICE_DECISION_REJECTED = "decision_rejected"  # 拒因回喂模型重决策

# ── 事件名（帧闭世界取值真源＝`transport.EVENT_KINDS`；此处只作发射点字面）─────────
EVENT_TOOL = "tool"
EVENT_OBSERVATION = "observation"
EVENT_ASK = "ask"

# ── 帧载荷键名（键集真源＝synth/S6 §一 `tool`／`observation` 帧行）────────────────
PAYLOAD_TOOL = "tool"
PAYLOAD_STATUS = "status"
PAYLOAD_SEQ = "seq"
PAYLOAD_MESSAGE = "message"
PAYLOAD_INDEX = "index"
PAYLOAD_SOURCE = "source"
PAYLOAD_CONTENT = "content"
PAYLOAD_TRUST = "trust"
PAYLOAD_FRAME = "frame"
PAYLOAD_RUN_ID = "run_id"

# ── 步 payload 键名（记账面：参数／行数／拒因——规格「不降级与静默禁令」节逐字）────
PAYLOAD_PHASE_KEY = "phase"
PAYLOAD_SUBTASK_ID_KEY = "subtask_id"
PAYLOAD_CHAIN_KEY = "chain"
PAYLOAD_ARGS_KEY = "args"
PAYLOAD_ARGS_FINGERPRINT_KEY = "args_fingerprint"
PAYLOAD_ROW_COUNT_KEY = "row_count"
PAYLOAD_REJECT_REASON_KEY = "reject_reason"
PAYLOAD_GATE_KEY = "gate"
PAYLOAD_FINGERPRINTS_KEY = "fingerprints"
PAYLOAD_REF_KEY = "ref"
PAYLOAD_SUMMARY_KEY = "summary"
PAYLOAD_CONSUMES_ROUND_KEY = "consumes_round"
PAYLOAD_ATTEMPTS_KEY = "attempts"
PAYLOAD_HANDLE_KEY = "handle"
PAYLOAD_VOLATILE_KEY = "volatile"
PAYLOAD_REJECTED_KEY = "rejected"

# ── 机读信号子键（规格「不降级与静默禁令」节逐字：落引用／失败／缺参必产机读信号——
# step payload 的 `row_count`／`ref.handle`／`error.reason`）────────────────────────
# `row_count`／`ref`（`handle`／`summary`／`row_count`）键名复用上方步 payload 键名；
# 仅 `error` 子结构两键为本块新增（`error`＋`category`／`reason`——与 `SubtaskExec.error` 同档）。
PAYLOAD_ERROR_KEY = "error"
PAYLOAD_ERROR_CATEGORY_KEY = "category"
PAYLOAD_ERROR_REASON_KEY = "reason"

PHASE = "execution"  # 过程档案相位标记与步 payload 相位值（真源：本块名）
LEDGER_NOTE_PHASE = "tool"  # 执行台账条目相位（迁移照抄：V1 `_note("tool", ...)`）

# ── 拒因文本（机器拒因原文——逐字迁移；承载位换、文本不变）───────────────────────
# **两刀分类（2026-10-17 EB4b）**：本节三条＋上方 `PLAN_FACE_REASON_*` 两模板是**回喂机面**
# （拒因回喂行／计划面闸拒原文——进模型窗与审计对账），照 A-P6b-05 **一字不动**；
# 其 notice 侧壳（`CONTENT_*_NOTICE_PREFIX`／`CONTENT_*_TEMPLATE`）才是上屏面，本批已白话化。
# 空手闸拒因（真源 `appv2/runtime/graph.py` 的 clarify discover 拒回文，本块换承载位）。
EMPTY_PROBE_FEEDBACK_TEMPLATE = (
    "{tool} 同参已空手（探查未命中）——禁原样重发；"
    "改用其他探查（换参视为新尝试），或 decompose 分解走 doc_retrieve。"
)
# 同参重投闸拒因（真源 `appv2/runtime/graph.py` SAME_PARAM_REPLAY_REASON 逐字）。
SAME_PARAM_REPLAY_REASON = (
    "同参已执行（同参重执行零新信息）——带结果直答或改参"
    "（finalize 按观察材料作答，或换参数后再发射），不要重复发射同一计划"
)
# 缺出处（行为 9：观察必带出处——缺出处＝判失败；INV-1 的输入）。
MISSING_SOURCE_REASON = (
    "观察缺出处（source 为空）：观察必带出处（台账行／片段→报告→库／表名）——"
    "缺出处＝判失败（INV-1 的输入），不猜、不补、不静默收下"
)

# ── 步／通知的固定文案（承载位换、文本不变——真源同 V1 同族节点）───────────────────
# **两刀分类（2026-10-17 EB4b 白话化；票面口径：上屏路径＝正文／supplement／notice／ask 帧）**：
# - **上屏面**（本批白话化）＝`CONTENT_*` 六件 notice 帧内容（web `NoticeRow` 逐条渲染 `content`）；
#   其中嵌 `{reason}` 者**只改外围壳**，`{reason}` 槽＝拒因原文逐字不动；
# - **非上屏面**（零改）＝`TITLE_*` 步帧标题（进 step 帧标题／过程档案）；
# - **回喂机面（A-P6b-05 零改动）**＝`EMPTY_PROBE_FEEDBACK_TEMPLATE`／`SAME_PARAM_REPLAY_REASON`／
#   `MISSING_SOURCE_REASON` 与本文件上方 `PLAN_FACE_REASON_*` 两模板——它们是拒因回喂行／
#   计划面闸拒原文（文本进模型窗与审计对账），一字不动。
TITLE_RESUME_GUARD = "恢复重取易变环境量"
TITLE_EXECUTE_TEMPLATE = "{tool}：{status}（子问题 {subtask}）"
TITLE_DISCOVER_TEMPLATE = "{tool}：{status}"
TITLE_REPLAY_REJECTED_TEMPLATE = "{tool} 同参重投被拦（发射级拒）"
TITLE_EMPTY_PROBE_REJECTED_TEMPLATE = "{tool} 同参已空手（发射级拒）"
TITLE_ADMISSION_REJECTED_TEMPLATE = "子问题 {subtask} 前置闸拒（终局不回炉）"
# 2026-10-17 EB4b：两前缀是 notice 内容（`... + reason`）＝上屏面，去「机器闸／同参重投／空手重发」
# 工程腔；其后紧跟的 `reason`（拒因原文）零改——故本批只改前缀，不动回喂面。
CONTENT_REPLAY_NOTICE_PREFIX = "同样的查询没有再执行一遍："
CONTENT_EMPTY_PROBE_NOTICE_PREFIX = "同样的探查已经空手过一次："
CONTENT_REF_DISCLOSURE_TEMPLATE = (
    "这份材料太长，答案里只放摘要和出处，全文另存（共 {row_count} 行）"
    "——出处 {source}，编号 {handle}，随时可以按编号调出来看，没有丢。"
)
CONTENT_SUBTASK_REFUSED_TEMPLATE = "问题 {subtask} 没能查到数据——{reason}"
CONTENT_SUBTASK_FAILED_TEMPLATE = "问题 {subtask} 执行失败（稍后会再试一次）——{reason}"
CONTENT_TOOL_UNAVAILABLE_TEMPLATE = (
    "取数工具 {tool} 重试后仍不可用——先把已经查到的内容如实给你。（{reason}）"
)
CONTENT_DECISION_REJECTED_TEMPLATE = "取数参数没通过检查，已把原因交回系统重新决策：{reason}"
