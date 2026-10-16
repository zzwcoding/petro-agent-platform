"""台账/名录投影取得：经 `tools` 公开面、取一次；失败＝fail-fast

真源：`specs/context.md` 接口定义节 `load_ledger_dump` 签名＋行为 10／11；卡面职责行
「台账/名录投影取得（经 `tools` 公开面装载进 state）」；投影形＝`appv2/tools/ledger.py`
模块 docstring 的 dump schema（迁移契约）。

**装载入口形＝前置核定项（未获核定）**：规格风险 5 原文——「**loader 的 tools 公开面调用形
未落定**」＋「已裁（流水 43⑥）：大面维持原裁（context 经 `tools` 装载）；tools 装载入口形＝
**阶段 5 context 施工票前置核定**（`tools` 规格旧版式、现在定不出真形）」。故本模块**只出端口＋
注入缝**（`LedgerProjectionPort`＝端口、`wire_ledger_projection`＝注入缝）——真实现形（哪一工具／
参形／工具面结果形）待核定后由装配面注入，本块**不发明该入口形**（AGENTS.md 6b）。

**取一次**：`state.ledger_dump` 非 `None` 即原样复用（含空投影 `{}`＝已取之空态，不再取）；
`None`＝未取得→取并写回——**本块唯一状态写入面**；返回为副本（改返回值不改 state）。
**失败＝fail-fast**（Owner 流水 44 翻案——合法降级路径＝无）：判据面＝工具面返回 failed 态
∪ 调用异常捕获面 → 抛 `LedgerLoadError`（稳定错误提示），run 由编排面直接终局失败、不带
缺台账的投影续跑；**合法空投影与失败不同路**（工具成功返回空 ≠ 失败）。失败事实的 Manifest
过程注记留痕＝编排面/`bookkeeping` 义务（本块零写过程档案）。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from appv2.runtimev2.state import RunState

# 装载失败稳定提示（fail-fast 的唯一文案单点——用户面帧面归发射方，`specs/transport.md`
# 行为 9 失败腿；原始异常文本只经异常链进内部留痕、不进本提示）。
_FAILURE_HINT = "台账投影装载失败——本轮无法取得台账材料，run 已失败收场（未带缺台账的投影续跑）"


class LedgerLoadError(RuntimeError):
    """台账投影装载失败（fail-fast——行为 11；合法降级路径＝无）。"""


class LedgerProjectionPort(Protocol):
    """台账/名录投影装载端口（**真实现形待核定**——规格风险 5）。

    成功＝返回投影 dict（空投影 `{}`＝合法成功态）；工具面返回 **failed 态** ⇒ 返回 `None`；
    调用异常 ⇒ 由 `load_ledger_dump` 捕获（判据面＝failed 态 ∪ 异常捕获面）。投影形＝
    `appv2/tools/ledger.py` dump schema（迁移契约）。
    """

    async def fetch(self) -> Mapping[str, Any] | None:
        ...


_PORT: LedgerProjectionPort | None = None


def wire_ledger_projection(port: LedgerProjectionPort | None) -> None:
    """装载端口接线（注入缝）——真实现形（tools 装载入口）核定后由装配面注入。

    `None`＝撤线（测试复位／未接线态——未接线时 `load_ledger_dump` 走 fail-fast，不静默兜底）。
    """
    global _PORT
    _PORT = port


async def load_ledger_dump(state: RunState) -> dict[str, Any]:
    """台账/名录投影取一次（行为 10）——已有投影（含空投影）零工具调用、返回值副本。

    `state.ledger_dump` 为空 → 经注入端口取一次并写回（**本块唯一状态写入面**）；
    取得失败（端口返回 `None`＝工具面 failed 态，或端口抛异常）→ `LedgerLoadError`
    （fail-fast——不做空投影续跑，不静默兜底）。
    """
    if state.ledger_dump is not None:
        return dict(state.ledger_dump)
    port = _PORT
    if port is None:
        raise LedgerLoadError(_FAILURE_HINT)
    try:
        dump = await port.fetch()
    except LedgerLoadError:
        raise
    except Exception as exc:  # 调用异常捕获面（判据面之一——不静默吞失败）
        raise LedgerLoadError(_FAILURE_HINT) from exc
    if dump is None:  # 工具面返回 failed 态（判据面之二）
        raise LedgerLoadError(_FAILURE_HINT)
    state.ledger_dump = dict(dump)
    return dict(state.ledger_dump)
