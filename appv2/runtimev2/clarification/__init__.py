"""澄清：意图澄清、分解问题、反问挂起与恢复

模块卡见 `specs/modules.md` 的 `## clarification` 一节；规格见 `specs/clarification.md`
（行为与形状真源）。包根即公开面（卡「公开接口」节的 `clarify` ＋本块返回位形状）：

- `clarify(state, *, guide_text="") -> ClarifyOutcome`——一次调用＝一次 LLM 决策周期：挂起恢复支 →
  轮装配 → 经 `bookkeeping.call_model` 单点发起 → 四动作闭世界对账 → 单出口互斥返回位；
  `guide_text`＝§A 指南段文本注入参（流水 63——编排面按启动快照注入；缺省空串＝空段头）；
- 返回位形状：`ClarifyAsk`（反问卡 → 挂起）｜`ClarifyFinal`（定案 → 进下一相位）｜
  `ClarifyRejection`（结构化拒因 → 回喂重决策）；`discover` 与到顶截断**不占返回位**
  （路由意图经 `state.next_intent` 交出），实现形以 `None` 表达该「不占位」；
- `ClarifyReason`——结构化拒因单条（`code` 闭世界 ＋ `reason` 机器面原文）。

依赖面（规格「框架与依赖红线」）：`prompts`（轮装配）／`parsing`（发射解析与拒文产出）／
`bookkeeping`（写口与模型调用发起面——单点发起；本块**不直引** `gateway_adapter`）／`state`
（形状与限额键），四者皆只经包根（R2）；**零工具直调**（`discover` 交 `orchestration` 路由）、
**零落盘**、**零语义判断**（`specs/clarification.md` 行 16 的 AST 机检面）。

本批（`RT-W4-02a`）落地面＝-A 半面：四动作闭世界对账／`finalize` 合法性闸与打回三段带路／
挂起·恢复·到顶截断／机读信号面／拒文转换（行为 19）＋本块三条 pin（`pin-05`／`pin-07`／
`pin-15`）。反问卡生产簇（时机分派形／默认窗／口径歧义／合并一卡）＋覆盖自证归 `RT-W4-02b`——
该半面（`RT-W4-02b`）已落地：时机三条与合并一卡＝**分派形**（程序只按模型结论分派，问句原文
零读点）、覆盖自证归模型（程序只校格式）、`Subtask` 无依赖字段；新增面＝发射注记逐字出流为
`decision_note` 机读通知（行为 3「并注记」）。
"""

from appv2.runtimev2.clarification.core import clarify
from appv2.runtimev2.clarification.models import (
    ClarifyAsk,
    ClarifyFinal,
    ClarifyOutcome,
    ClarifyReason,
    ClarifyRejection,
)

__all__ = [
    "ClarifyAsk",
    "ClarifyFinal",
    "ClarifyOutcome",
    "ClarifyReason",
    "ClarifyRejection",
    "clarify",
]
