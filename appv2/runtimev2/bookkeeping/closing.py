"""bookkeeping.closing —— 触界收敛落地、完成收口旁路与调模型单点（本块写口）。

真源＝`specs/bookkeeping.md` 接口定义节「触界收敛与完成收口」／「调模型与工具面」＋行为 12–15。
**判定与落地分层**：触界**判定**归 `state.check_limits`（纯计算，不在本块），本模块只**落地**它给
的结论——「不许自述完成」（`specs/bookkeeping.md`「不降级与静默禁令」）。

- `converge`（行为 12／13）：命中 → 落地**六键**（`budget_hit` 追加命中项／`notices` 追加如实注记／
  `answer` 正文／`draft_kind="direct"`／`status="completed"`／`next_intent=answer`）；未命中 →
  **零副作用**；已收敛（`budget_hit` 非空）再调 → **无操作**（幂等守卫在判定之前——多入口单点）。
  **材料面＝单一真源** `_material_rows`（已入栈观察 ＋ 末次工具结果自带观察——现状锚
  `appv2/runtime/budget.py` 的 `material_rows`「R2 单源：交付正文与通知文案分叉同判此处」）；
  正文与注记两处的材料标识由**同一函数** `_material_clause` 生成——「两处不漂移」是构造性质，
  不是约定（断言面＝`::converge_material_same_source`）。措辞由材料面与实际命中闸名决定，
  **不写死前缀**（现状「已取得材料未及核验」是缺陷，`recon/B1` D-B1-04——风险 6）。
- `direct_answer`（行为 14）：收口旁路恒写三键（`draft`／`draft_kind="direct"`／
  `next_intent=answer`）——拒答、闸拒、收敛转答、直答共用**同一出口**（免起草免核验）。
- `call_model`（行为 15）：从状态取 `run_id` → 调 `gateway_adapter.complete` → **向节点只回
  `content`**；回执的**余键**（用量与归因面：`caller`／`run_id`／token／`cached_tokens`／`alias`／
  时长／`usage_estimated`／`error`）由本块记进步记录 `payload`，`token_count` 回填进随步的
  `Manifest`（真源 `specs/context.md`：「`token_count` 由记账面回填」）——**禁裸文本吞掉记账面**。

**同步缝**：规格 :73 的 `call_model` 是同步签名（`-> str`，`-01a` 已落地看守），而模型出口
`complete` 是协程（`specs/gateway_adapter.md` 行为 4 硬要求）——接缝单点＝`_run_sync`
（与 `appv2/query/pg_executor.py`／`appv2/knowledge/pg_faq.py` 同款两态桥：无运行环本线程直跑；
已在运行环内落专用单线程池另起环——不阻塞事件循环、不另立第二出口）。

**合法降级路径＝无**：闭世界越界即抛错；`call_model` 的失败（重试耗尽／不可重试类）由
`gateway_adapter` 原异常上抛、本块**不吞不兜**（收口归 `orchestration`）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Any

import appv2.runtimev2.persistence as persistence_module
from appv2.runtimev2.bookkeeping.constants import CALLER_STEP_KINDS, DRAFT_KIND_DIRECT
from appv2.runtimev2.bookkeeping.ports import record_step, set_intent
from appv2.runtimev2.gateway_adapter import ModelReply, complete
from appv2.runtimev2.state import INTENT_ANSWER, RUN_COMPLETED, Manifest, RunState, check_limits

# 回执里**唯一**属节点的字段（显式不落记账面）——其余键逐键入账（「禁裸文本吞掉记账面」）。
_REPLY_NODE_KEY = "content"


# ── 材料面（收敛正文与通知未完成项清单的**同一真源**）────────────────────────


def _material_rows(state: RunState) -> list[Mapping[str, Any]]:
    """已取得材料面（**单一真源**）：已入栈观察 ＋ 末次工具结果自带观察。

    现状锚＝`appv2/runtime/budget.py` 的 `material_rows`（R2 单源）：收敛交付正文与通知「未完成项」
    文案**同判此处**——本函数即该单源的 V2 落点。逐条**不重排、不去重、不裁剪**（「逐条如实
    交付」）；非 mapping 的行（旧检查点残形）不计。
    """
    rows: list[Mapping[str, Any]] = [
        row for row in state.observations if isinstance(row, Mapping)
    ]
    last_result = state.last_result
    if isinstance(last_result, Mapping):
        carried = last_result.get("observations")
        if isinstance(carried, list):
            rows.extend(row for row in carried if isinstance(row, Mapping))
    return rows


def _material_id(row: Mapping[str, Any]) -> str:
    """材料标识＝观察行的 `source_id`（缺锚如实空串——不拿正文冒充锚）。"""
    identifier = row.get("source_id")
    return identifier if isinstance(identifier, str) else ""


def _material_content(row: Mapping[str, Any]) -> str:
    """材料正文（逐条交付的正文面；缺键／非串如实空串——不加工、不改写）。"""
    content = row.get("content")
    return content if isinstance(content, str) else ""


def _material_clause(rows: Sequence[Mapping[str, Any]]) -> str:
    """材料标识的同源声明——**两处（正文与注记）调同一函数**，标识集合一致由构造保证。"""
    identifiers = [_material_id(row) for row in rows]
    return "材料清单：" + ("、".join(identifiers) if identifiers else "无")


def _convergence_answer(gates: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    """收敛正文（行为 12／13）：措辞由**材料面与命中闸名**决定——零材料与有材料两形，不写死前缀。"""
    gates_text = "、".join(gates)
    if not rows:
        return (
            f"（预算触界收敛——{gates_text}；未取得可交付材料，如实说明；{_material_clause(rows)}）"
        )
    header = (
        f"（预算触界收敛——{gates_text}；已取得材料 {len(rows)} 条逐条如实交付；"
        f"{_material_clause(rows)}）"
    )
    return "\n".join([header, *(f"- {_material_content(row)}" for row in rows)])


def _convergence_notice(
    notice: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """触界如实注记（行为 11／12／13）：`state` 给的恰三键注记 ＋ 本块装配的「未完成项」明细。

    `type`／`gates` 原样透传（真源＝`state.check_limits` 的 `Convergence.notice`；`gates` 取值＝
    `LimitHit.limit` 七限额键名）。「未完成项」取自**同一材料面**（同一 `_material_clause`）——
    「答案说交付了 X、通知说未完成 X」这种漂移在本块构造不出来（行为 13）。
    """
    if rows:
        unfinished = f"已取得材料 {len(rows)} 条尚未收口（{_material_clause(rows)}）"
    else:
        unfinished = f"未取得可交付材料（{_material_clause(rows)}）"
    return {
        "type": notice["type"],
        "gates": list(notice["gates"]),
        "content": f"{notice['content']}；未完成项：{unfinished}",
    }


# ── 触界收敛落地（行为 12／13）─────────────────────────────────────────────


def converge(state: RunState) -> None:
    """触界收敛落地（行为 12／13）：判定归 `state.check_limits`，本函数只**落地**其结论。

    三步（顺序即契约）：① **幂等守卫**——`budget_hit` 非空＝已收敛 → 直接无操作（不重复追加通知、
    不重复追加 gates、不覆盖答案与状态）；② **判定**——`state.check_limits(state)`（本块不复制其
    判据与数值）；③ **落地或零副作用**——命中 → 六键（`budget_hit`／`notices`／`answer`／
    `draft_kind`／`status`／`next_intent`，除这六项外**零字段改动**）；未命中 → 直接返回，状态
    深比较不变。

    正文材料与注记未完成项清单同源（`_material_clause` 同一函数）；状态取值引常量
    （`state.RUN_COMPLETED`／`INTENT_ANSWER`／本块 `DRAFT_KIND_DIRECT`），不落裸字面量。
    收敛**不产生步记录**（`recon/B1` R-B1-06：收敛事实面＝`notices`＋`budget_hit`，答案落
    answer 步）——故除六键外零字段改动。
    """
    if state.budget_hit:  # 已收敛 → 无操作（多入口单点：连判定都免）
        return
    convergence = check_limits(state)
    if not convergence.hit:  # 未命中 → 零副作用
        return
    limits = [hit.limit for hit in convergence.hit]
    notice = convergence.notice
    if notice is None:  # state 行为 12 的形态互斥（命中 ⇔ 注记在场）——违约即 fail-closed
        raise ValueError("触界命中却无注记（state.Convergence 形态互斥违约）——收敛不静默")
    rows = _material_rows(state)
    state.budget_hit.extend(limits)
    state.notices.append(_convergence_notice(notice, rows))
    state.answer = _convergence_answer(limits, rows)
    state.draft_kind = DRAFT_KIND_DIRECT
    state.status = RUN_COMPLETED
    set_intent(state, INTENT_ANSWER)


# ── 完成收口旁路（行为 14）─────────────────────────────────────────────────


def direct_answer(state: RunState, text: str) -> None:
    """完成收口旁路单点（行为 14）：恒写三键（`draft=text`／`draft_kind="direct"`／
    `next_intent=answer`）——免起草免核验的**同一出口**（拒答／闸拒／收敛转答／直答共用）。

    三键之外**零写**（不动 `answer`／`verdict`／`status`——收口由 answer 步按 `draft_kind` 走直答
    通道）；`next_intent` 经唯一写口 `set_intent` 落（闭世界越界即拒）。
    """
    state.draft = text
    state.draft_kind = DRAFT_KIND_DIRECT
    set_intent(state, INTENT_ANSWER)


# ── 调模型单点（行为 15）───────────────────────────────────────────────────


def call_model(state: RunState, caller: str, messages: Sequence[Mapping[str, str]]) -> str:
    """节点侧调模型单点（行为 15）：从状态取 `run_id` → 调 `gateway_adapter.complete` →
    **向节点只回 `content`**；回执余键（用量与归因面）记进步记录与 `Manifest`。

    - **发起面**＝`gateway_adapter.complete`（模块级唯一出口；经 `set_completer` 注入的同面缝实作
      ——生产桥／测试替身同面），本块**不直引供应商、不自建客户端**；
    - **只回 `content`**：返回值是纯字符串，记账面**不随返回值走**（裸文本吞账＝缺陷）；
    - **记账面**：`payload`＝回执余键九项（`caller`／`run_id`／`alias`／`prompt_tokens`／
      `completion_tokens`／`cached_tokens`／`usage_estimated`／`duration_ms`／`error`），
      `manifest.token_count` 回填实测 `prompt_tokens`（`specs/context.md`：`token_count` 由记账面
      回填）——**每模型调用都有 Manifest**；
    - **步态如实**：`error` 非 None＝失败尝试（回执契约）→ `status="failed"`；否则 `"ok"`；
    - **失败不吞**：出口抛错（重试耗尽／不可重试类）由本函数**原样上抛**（收口归 `orchestration`）
      ——本块不 catch、不兜底、不返回哨兵。
    """
    step_kind = _caller_step_kind(caller)
    reply = _run_sync(complete(messages, caller=caller, run_id=state.run_id))
    record_step(
        state,
        kind=step_kind,
        title=f"模型调用：{caller}",
        status=_reply_status(reply),
        payload=_usage_payload(reply),
        manifest=Manifest(token_count=reply.prompt_tokens),
    )
    return reply.content


def _caller_step_kind(caller: str) -> str:
    """`caller`（归因三桶族）→ 步记录步型：闭世界分派，越界即拒（fail-closed，不猜桶）。"""
    if caller not in CALLER_STEP_KINDS:
        values = "／".join(sorted(CALLER_STEP_KINDS))
        raise ValueError(f"模型调用归因桶（caller）越界（闭世界＝{values}）：{caller!r}")
    return CALLER_STEP_KINDS[caller]


def _reply_status(reply: ModelReply) -> str:
    """步态如实（`status` 由调用方如实给、本块不猜）：`error` 非 None＝失败尝试（回执契约）。"""
    return (
        persistence_module.STEP_STATUS_OK
        if reply.error is None
        else persistence_module.STEP_STATUS_FAILED
    )


def _usage_payload(reply: ModelReply) -> dict[str, Any]:
    """记账面 payload＝回执**余键**全量（逐键不丢、不改名；`content` 是节点唯一所得的那一件）。"""
    usage = asdict(reply)
    del usage[_REPLY_NODE_KEY]
    return usage


def _run_sync(awaitable: Coroutine[Any, Any, ModelReply]) -> ModelReply:
    """同步签名面 → 异步模型出口的**两态桥**（本块唯一一处事件循环接触）。

    无运行环 → 本线程 `asyncio.run` 直跑；已在运行环内 → 落专用单线程池另起环（不阻塞事件循环）
    ——同 `appv2/query/pg_executor.py`／`appv2/knowledge/pg_faq.py` 的 `_run_sync` 形。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()
