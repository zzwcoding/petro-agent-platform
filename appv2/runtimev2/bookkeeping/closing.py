"""bookkeeping.closing —— 触界收敛落地、完成收口旁路与调模型单点（本块写口）。

真源＝`specs/bookkeeping.md` 接口定义节「触界收敛与完成收口」／「调模型与工具面」＋行为 12–15。
**判定与落地分层**：触界**判定**归 `state.check_limits`（纯计算，不在本块），本模块只**落地**它给
的结论——「不许自述完成」（`specs/bookkeeping.md`「不降级与静默禁令」）。

三个成员的行为体随 `RT-W3-01b-bookkeeping.md` 落地（本票只出签名与公开面）：

- `converge`：命中落六键、未命中零副作用、已收敛再调无操作（幂等）；收敛正文与通知未完成项
  清单**同一材料面**（行为 12／13）。
- `direct_answer`：收口旁路恒写三键（`draft`／`draft_kind`／`next_intent`）——拒答、闸拒、收敛
  转答、直答共用同一出口（行为 14）。
- `call_model`：从状态取 `run_id` → 调 `gateway_adapter.complete` → **向节点只回 `content`**；
  回执的用量与归因面由本块记进步记录与 Manifest（行为 15——**禁裸文本吞掉记账面**）。

未落地前调用一律 fail-closed（`NotImplementedError`）——**不静默兜底、不假成功**。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from appv2.runtimev2.state import RunState


def converge(state: RunState) -> None:
    """触界收敛落地（行为 12／13）：判定归 `state.check_limits`，本函数只落地其结论。

    命中 → 落地六键（`budget_hit` 追加命中项／通知追加如实注记／答案正文＝已取得材料逐条如实
    交付／`draft_kind="direct"`／`status="completed"`／`next_intent=answer`）；未命中 →
    **零副作用**；已收敛（`budget_hit` 非空）再调 → **无操作**（幂等）。行为体随
    `RT-W3-01b-bookkeeping.md` 落地。
    """
    raise NotImplementedError(
        "bookkeeping.converge 的行为体随 RT-W3-01b-bookkeeping.md 落地（本票只出签名与公开面）"
    )


def direct_answer(state: RunState, text: str) -> None:
    """完成收口旁路单点（行为 14）：恒写三键（`draft=text`／`draft_kind="direct"`／
    `next_intent=answer`）——免起草免核验的同一出口。行为体随 `RT-W3-01b-bookkeeping.md` 落地。
    """
    raise NotImplementedError(
        "bookkeeping.direct_answer 的行为体随 RT-W3-01b-bookkeeping.md 落地（本票只出签名与公开面）"
    )


def call_model(state: RunState, caller: str, messages: Sequence[Mapping[str, str]]) -> str:
    """节点侧调模型单点（行为 15）：从状态取 `run_id` → 调 `gateway_adapter.complete` →
    向节点只回 `content`；回执的用量与归因面由本块记进步记录与 Manifest。行为体随
    `RT-W3-01b-bookkeeping.md` 落地。
    """
    raise NotImplementedError(
        "bookkeeping.call_model 的行为体随 RT-W3-01b-bookkeeping.md 落地（本票只出签名与公开面）"
    )
