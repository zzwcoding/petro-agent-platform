"""execution 的常量单点：两处闭世界 ＋ 发射／载荷键名 ＋ 阈值与分型（逐条注真源）。

真源＝`specs/execution.md`（接口定义节 :35–:60 两处闭世界、行为 4／13／14、验收测试表）；
形状取值**引真源不复述**处一律注明（如 `notify`／`gates` 的取值集归 `transport.NOTICE_TYPES`）。

- 两处闭世界：`EXEC_STATUS_KINDS`（`ok`／`failed`／`need_input`）与 `ERROR_CATEGORIES`
  （`retryable`／`bad_args`／`refused`——对齐 `specs/tools.md` 错误三档「可重试｜修参｜拒答」）；
- 行集承载分型：`ROWSET_OBSERVATION_KINDS`（行为 4——行集题不落引用，判据＝工具观察的
  `locator.kind` 集合成员判定，属规格行为 9 的豁免面「形态处理／集合成员判定」）；
- 阈值：`BIG_RESULT_THRESHOLD_CHARS`（行为 4——**数值阶段 5 待定（随真机数据定）**，本票取
  占位值并登记呈主窗；本模块内以此单点为唯一数值面，调用点与测试皆引名字、不写裸值）；
- 两闸门名（行为 13／14「闸族」互引，两闸勿混）与通知类型（字面指针，取值真源＝
  `transport.NOTICE_TYPES` 二十九值，本模块**不私扩闭世界**）；
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

PHASE = "execution"  # 过程档案相位标记与步 payload 相位值（真源：本块名）
LEDGER_NOTE_PHASE = "tool"  # 执行台账条目相位（迁移照抄：V1 `_note("tool", ...)`）

# ── 拒因文本（机器拒因原文——逐字迁移；承载位换、文本不变）───────────────────────
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
TITLE_RESUME_GUARD = "恢复重取易变环境量"
TITLE_EXECUTE_TEMPLATE = "{tool}：{status}（子问题 {subtask}）"
TITLE_DISCOVER_TEMPLATE = "{tool}：{status}"
TITLE_REPLAY_REJECTED_TEMPLATE = "{tool} 同参重投被拦（发射级拒）"
TITLE_EMPTY_PROBE_REJECTED_TEMPLATE = "{tool} 同参已空手（发射级拒）"
TITLE_ADMISSION_REJECTED_TEMPLATE = "子问题 {subtask} 前置闸拒（终局不回炉）"
CONTENT_REPLAY_NOTICE_PREFIX = "同参重投机器闸："
CONTENT_EMPTY_PROBE_NOTICE_PREFIX = "同参空手重发机器闸："
CONTENT_REF_DISCLOSURE_TEMPLATE = (
    "材料超阈落引用（窗口只留摘要＋引用＋行数，不留全文）：出处 {source}，"
    "原文 {row_count} 行已落引用 {handle}——可寻址读回，未静默丢弃。"
)
CONTENT_SUBTASK_REFUSED_TEMPLATE = "子问题 {subtask} 闸拒（如实转答）：{reason}"
CONTENT_SUBTASK_FAILED_TEMPLATE = "子问题 {subtask} 执行失败（回炉面）：{reason}"
CONTENT_TOOL_UNAVAILABLE_TEMPLATE = (
    "工具 {tool} 重试后仍不可用——如实收敛。（{reason}）"
)
CONTENT_DECISION_REJECTED_TEMPLATE = "工具校验拒因回喂重决策：{reason}"
