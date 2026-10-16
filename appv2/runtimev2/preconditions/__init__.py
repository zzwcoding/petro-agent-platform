"""前置检查：逐子问题三态闸（放行／拒答／等用户），纯程序零 LLM，注记并入放行。

模块卡见 `specs/modules.md` 的 `## preconditions` 一节；规格见 `specs/preconditions.md`
（形状与行为真源）；架构图见 `docs/architecture-v3.html`。包根即公开面（R2：消费方只经
`appv2.runtimev2.preconditions` 消费，深层子模块私有）：

- 相位单入口：`gate_all`（卡面签名 `gate_all(state, *, window_candidates=None)`——每子问题恰
  一条 `SubtaskVerdict`，三态闭世界；注入面三参见 `core.gate_all` docstring）；
- 定型类三件：`SubtaskVerdict`（三态 ＋ 注记 ＋ 判定位标识）／`RefusalReason`（拒因三面）／
  `AskReason`（等用户两形）；
- 闭世界常量族：`DECISIONS`／`DECISION_*`（三态）／`ASK_KINDS`／`ASK_KIND_*`（ask 两形）／
  `FRAME_KIND_BY_ASK_KIND`（**唯一映射表**：`AskReason.kind` → ask 帧 `frame.kind`）／
  `RULE_ORDER`（判定序八位，引 `tools` 闸件标识）／`MENTION_MODES`／`MENTION_*`（「提及 vs
  执行」结论两值）／`RULE_GATE_UNAVAILABLE`（fail-closed 错误标记）；
- 接线字面：`PHASE`／`STEP_KIND`／`PAYLOAD_*`（步 payload 键名）／`NOTICE_*`（notice 类型）。

**分工**：语义类结论（废弃词「提及 vs 执行」、口径归一、时间窗能否确定）由 `tool_matching` 的
模型产出；本块只按结论**机械分派**（行为 4），八位判定位的判定本体在 `tools` 闸件
（`appv2.tools.precondition.judge`——本块只经其公开面单点调用，取 `Verdict.hit_rule` 结构化判定位，
不复制语义、不文案反推）。

**边界**（规格「框架与依赖红线」＋卡「依赖」）：无点名框架（R5b）；**零 LLM 铁律**——不调模型、
不引 `litellm`／`appv2.infra.llm_client`（R7）／`gateway_adapter`（R8）；只经 `tools` 公开面接触
世界（R6）；不引旧码 `appv2.runtime`（R5）；不 import 其它相位（R1）。**相位不直写共享写面**：
步记录与 notice 全经 `bookkeeping` 唯一写口（`record_step`／`notice`），本块只落自己的产物面
（`state.precondition_verdicts` 与换链回炉记账 `state.chain_switch_marks`）。
"""

from appv2.runtimev2.preconditions.constants import (
    ASK_KIND_CALIBER_CLARIFY,
    ASK_KIND_EXTERNAL_TABLE_APPROVAL,
    ASK_KINDS,
    DECISION_ALLOW,
    DECISION_ASK,
    DECISION_REFUSE,
    DECISIONS,
    FRAME_KIND_BY_ASK_KIND,
    FRAME_KIND_CLARIFY,
    FRAME_KIND_EXTERNAL_TABLE_APPROVAL,
    HIT_RULE_NONE,
    MENTION_EXECUTED,
    MENTION_MENTIONED_ONLY,
    MENTION_MODES,
    NOTICE_ASK_APPROVAL,
    NOTICE_CHAIN_SWITCH,
    NOTICE_SUBTASK_REFUSED,
    NOTICE_VERDICT_NOTE,
    PAYLOAD_DECISION_KEY,
    PAYLOAD_HIT_RULE_KEY,
    PAYLOAD_NOTES_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REENTRY_KEY,
    PAYLOAD_SUBTASK_ID_KEY,
    PHASE,
    RULE_GATE_UNAVAILABLE,
    RULE_ORDER,
    STEP_KIND,
)
from appv2.runtimev2.preconditions.core import gate_all
from appv2.runtimev2.preconditions.models import (
    AskReason,
    RefusalReason,
    SubtaskVerdict,
)

__all__ = [
    "ASK_KINDS",
    "ASK_KIND_CALIBER_CLARIFY",
    "ASK_KIND_EXTERNAL_TABLE_APPROVAL",
    "DECISIONS",
    "DECISION_ALLOW",
    "DECISION_ASK",
    "DECISION_REFUSE",
    "FRAME_KIND_BY_ASK_KIND",
    "FRAME_KIND_CLARIFY",
    "FRAME_KIND_EXTERNAL_TABLE_APPROVAL",
    "HIT_RULE_NONE",
    "MENTION_EXECUTED",
    "MENTION_MENTIONED_ONLY",
    "MENTION_MODES",
    "NOTICE_ASK_APPROVAL",
    "NOTICE_CHAIN_SWITCH",
    "NOTICE_SUBTASK_REFUSED",
    "NOTICE_VERDICT_NOTE",
    "PAYLOAD_DECISION_KEY",
    "PAYLOAD_HIT_RULE_KEY",
    "PAYLOAD_NOTES_KEY",
    "PAYLOAD_PHASE_KEY",
    "PAYLOAD_REENTRY_KEY",
    "PAYLOAD_SUBTASK_ID_KEY",
    "PHASE",
    "RULE_GATE_UNAVAILABLE",
    "RULE_ORDER",
    "STEP_KIND",
    "AskReason",
    "RefusalReason",
    "SubtaskVerdict",
    "gate_all",
]
