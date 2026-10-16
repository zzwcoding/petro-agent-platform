"""审计接线（H3）——五处留痕经 `security.audit` **唯一写口**落责任账（INV-5；B12）。

规格原文（`specs/agent-loop.md:153`）：「**审计接线（H3）**：受理／三态收口／拒答收口／外表审批决定／
禁用词豁免**五处留痕**都经 `security.audit` 唯一写口落责任账——**计数口径以「action 闭世界七值」为
准**（真源 `docs/runtime-refactor/recon/J-存储留痕与网关缝.md` R-J-05；三态收口＝完成／失败两值、
审批决定＝批准／驳回两值），**本处不写类数**（旧「四事件」说法已废——它漏了禁用词豁免）；action 恒
`agent_v2.*` 前缀，INV-5」。本模块即该条的落地面：

1. **唯一写口**：每条留痕都构造 `persistence.AuditRecord` 交给 `persistence.audit`（其真件＝装配点
   注入的 `security.audit` 桥，B12）——本模块**不直引 `appv2.infra.security` 的写口实现**，不开第二
   条写路；
2. **计数口径单点**：`AUDIT_PLACES` 是「五处留痕 → action 取值」的**唯一**表（取值全部引
   `persistence` 的七值闭世界常量，本模块**零字面量**、**不写类数**）；
3. **失败不静默也不翻盘**（先例＝旧码 `appv2/runtime/executor.py` 的 `_audit` 守卫）：写口异常 →
   `notice(type="audit_write_failed")` 出流（留痕缺口可见），run 状态机零改动——「合法降级路径＝无」
   指的是编排层不自降级；审计写口不可用是**装配缺口**，如实暴露而非静默吞掉。

**身份缝**（行 33／`specs/agent-loop.md:154`）：「请求身份经 `infra.security.resolve_actor` 解析
（开发期身份桩；正式接 OAuth2.0 **只换该函数实现**，其余零改动）」——本模块的 `who_of` 是该缝在编排
块的**唯一**消费点：受理腿取入口点已解析的 `Actor` 全名（`Actor.who`），空身份经 `resolve_actor` 落
缺省角色；恢复腿只有 run 簿记行的**行级身份字符串**，一律经 `resolve_actor` 重新解析（不自建角色表、
不猜全名）。

**禁用词豁免半面**：V2 **零豁免**（`specs/gate.md` 行为 13 逐字：「不做豁免／元问／引用形判定（V1
禁用词豁免机制不落本块；V2 亦不引入）」）——故本处留痕位在 V2 是**待产位**（分支在场、V2 无触发源）；
`ban_exempt` 取值仍在 action 闭世界七值内（真源 R-J-05），本模块照旧保留其发射分支（沿旧码先例的切片
法：只审本腿**新增**的豁免通知，防跨腿重放重复行）。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.infra.security import Actor, UnauthenticatedError, resolve_actor
from appv2.runtimev2.orchestration.constants import (
    EVENT_NOTICE,
    NOTICE_AUDIT_WRITE_FAILED,
    NOTICE_BAN_EXEMPT,
    NOTICE_SUBTASK_REFUSED,
)
from appv2.runtimev2.persistence import (
    AUDIT_ACTION_BAN_EXEMPT,
    AUDIT_ACTION_EXTABLE_APPROVED,
    AUDIT_ACTION_EXTABLE_REJECTED,
    AUDIT_ACTION_REFUSED,
    AUDIT_ACTION_RUN_COMPLETED,
    AUDIT_ACTION_RUN_CREATED,
    AUDIT_ACTION_RUN_FAILED,
    AuditRecord,
    audit,
)
from appv2.runtimev2.state import RUN_FAILED, RUN_WAITING_ASK
from appv2.runtimev2.transport import EventBus

# 五处留痕 → action 取值（**计数口径的唯一表**；取值全引 `persistence` 七值闭世界常量）。
AUDIT_PLACES: Mapping[str, tuple[str, ...]] = {
    "受理": (AUDIT_ACTION_RUN_CREATED,),
    "三态收口": (AUDIT_ACTION_RUN_COMPLETED, AUDIT_ACTION_RUN_FAILED),
    "拒答收口": (AUDIT_ACTION_REFUSED,),
    "外表审批决定": (AUDIT_ACTION_EXTABLE_APPROVED, AUDIT_ACTION_EXTABLE_REJECTED),
    "禁用词豁免": (AUDIT_ACTION_BAN_EXEMPT,),
}

_APPROVAL_KIND = "external_table_approval"
_APPROVE = "approve"
_APPROVAL_ID_KEY = "approval_id"
_APPROVAL_DECISION_KEY = "decision"


def who_of(actor: Actor | None) -> str:
    """受理腿 who 槽：入口点已解析的 `Actor` 全名优先，空身份经唯一身份缝落缺省角色。

    逐字照旧码先例 `who_of(actor) = actor.who or resolve_actor(actor.user_id).who`
    （`appv2/runtime/audit.py`）——「身份解析只经 `resolve_actor`」：本函数**不猜全名、不建角色表**。
    """
    if actor is not None and actor.who:
        return actor.who
    return resolve_actor(None if actor is None else actor.user_id).who


def who_of_id(actor_id: str) -> str:
    """恢复腿 who 槽：run 簿记行的行级身份字符串经**唯一身份缝**解析回全名。

    恢复腿没有受理腿的 `Actor` 对象（run 行只存行级字符串投影），故经 `resolve_actor` 重新解析——
    未登记的身份字符串（`UnauthenticatedError`）由调用方的发射守卫如实暴露（不静默、不猜）。
    """
    try:
        return resolve_actor(actor_id).who
    except UnauthenticatedError as exc:
        raise UnauthenticatedError(
            f"身份解析失败——run 簿记行的行级身份 {actor_id!r} 未登记（身份只经 resolve_actor 解析）"
        ) from exc


# ── 五处留痕的发射面（各一条记录；写口异常 → notice，run 状态机零改动）────────────


def run_created(bus: EventBus, *, run_id: str, who: str, question: str) -> None:
    """留痕①：受理（`agent_v2.run_created`）。"""
    _emit(
        bus,
        _record(
            run_id,
            who,
            AUDIT_ACTION_RUN_CREATED,
            facts=f"问答受理：{question}",
            evidence={"run_id": run_id, "question": question},
        ),
    )


def closeout(
    bus: EventBus,
    *,
    run_id: str,
    who: str,
    status: str,
    answer: str = "",
    error: str = "",
    manifest_digest: str = "",
    refused: bool = False,
) -> None:
    """留痕②③：三态收口（完成／失败两值）＋拒答收口（`refused` 在场＝拒答收口，与正常收口互斥）。

    挂起收束（`waiting_ask`）不是 run 收口（该 run 还会被 resume 续推）——本处不发终态留痕。
    """
    if status == RUN_WAITING_ASK:
        return
    if refused:
        _emit(
            bus,
            _record(
                run_id,
                who,
                AUDIT_ACTION_REFUSED,
                facts=f"拒答收口：{answer}",
                evidence={"status": status, "run_id": run_id},
            ),
        )
        return
    if status == RUN_FAILED:
        _emit(
            bus,
            _record(
                run_id,
                who,
                AUDIT_ACTION_RUN_FAILED,
                facts=f"run 收口：失败（{error}）",
                evidence={"status": status, "error": error, "run_id": run_id},
            ),
        )
        return
    _emit(
        bus,
        _record(
            run_id,
            who,
            AUDIT_ACTION_RUN_COMPLETED,
            facts=f"run 收口：完成（{answer}）",
            evidence={
                "status": status,
                "manifest_digest": manifest_digest,
                "run_id": run_id,
            },
        ),
    )


def extable_decisions(
    bus: EventBus, *, run_id: str, who: str, choices: Sequence[Mapping[str, Any]]
) -> None:
    """留痕④：外表审批决定（批准／驳回两值）——只审本腿新增的选择（切片由调用方给）。"""
    for choice in choices:
        if str(choice.get("kind") or "") != _APPROVAL_KIND:
            continue  # 澄清回收等非审批决定不在本留痕位闭世界（零溢行）
        approval_id = str(choice.get(_APPROVAL_ID_KEY) or "")
        approved = choice.get(_APPROVAL_DECISION_KEY) == _APPROVE
        _emit(
            bus,
            _record(
                run_id,
                who,
                AUDIT_ACTION_EXTABLE_APPROVED if approved else AUDIT_ACTION_EXTABLE_REJECTED,
                facts=f"外表越集审批：{'批准' if approved else '驳回'}（{approval_id}）",
                evidence={"approval_id": approval_id, "approved": approved, "run_id": run_id},
                authorization=approval_id,
            ),
        )


def exempts(bus: EventBus, *, run_id: str, who: str, notices: Sequence[Mapping[str, Any]]) -> None:
    """留痕⑤：禁用词豁免（V2 待产位——触发源归入口闸族；本块只保留发射分支）。

    只审本腿新增的豁免通知（切片由调用方给——旧码先例：跨腿重放不重复落行）。
    """
    for notice in notices:
        if str(notice.get("type") or "") != NOTICE_BAN_EXEMPT:
            continue
        _emit(
            bus,
            _record(
                run_id,
                who,
                AUDIT_ACTION_BAN_EXEMPT,
                facts=f"禁用词豁免放行：{notice.get('content', '')}",
                evidence={"term": str(notice.get("term") or ""), "run_id": run_id},
            ),
        )


def refused_closeout(state_notices: Sequence[Mapping[str, Any]]) -> bool:
    """拒答收口判据（结构判据，非语义判断）：本 run 的通知里有**拒答分型**一支。

    旧码先例 `_audit_closeout`（`appv2/runtime/executor.py`：notices 里的拒答分型 → 拒答收口留痕，
    否则正常收口）同构照搬，**分型值随 V2 判定**：V1 侧的 `"refused"` 在 V2 由 `preconditions`／
    `execution` 的**子问题闸拒分型** `subtask_refused` 承载（其常量单点＝两块的
    `NOTICE_SUBTASK_REFUSED`；取值闭世界真源＝`transport.NOTICE_TYPES`）。拒答收口行与正常收口行
    **互斥**（run 终态恰一行）。
    """
    return any(str(notice.get("type") or "") == NOTICE_SUBTASK_REFUSED for notice in state_notices)


# ── 内部件 ──────────────────────────────────────────────────────────────────


def _record(
    run_id: str,
    who: str,
    action: str,
    *,
    facts: str,
    evidence: dict[str, Any],
    authorization: str = "",
) -> AuditRecord:
    """审计记录（四要素齐备——主体／意图／事实／结果；`scope`＝主体的范围细化＝会话线程）。"""
    return AuditRecord(
        run_id=run_id,
        who=who,
        scope=run_id,
        action=action,
        authorization=authorization,
        facts=facts,
        evidence=evidence,
    )


def _emit(bus: EventBus, record: AuditRecord) -> None:
    """写口发射守卫：唯一写口＝`persistence.audit`（真件＝`security.audit` 桥）。

    写口异常 → `audit_write_failed` 通知出流（留痕缺口可见、run 状态机零改动——旧码同款守卫）。
    """
    try:
        audit(record)
    except Exception as exc:  # 写口未装配／落库失败 → 留痕缺口不静默（不翻盘 run 状态）
        bus.emit(
            EVENT_NOTICE,
            {
                "type": NOTICE_AUDIT_WRITE_FAILED,
                "gates": [],
                "content": f"审计写口异常（责任账缺口，过程态不受影响）：{exc}",
            },
        )


__all__ = [
    "AUDIT_PLACES",
    "closeout",
    "exempts",
    "extable_decisions",
    "refused_closeout",
    "run_created",
    "who_of",
    "who_of_id",
]
