"""runtime.audit —— V2 链路关键事件落审计责任账（V2-20 任务 1——P-010 S3 修复）。

四事件闭世界（票面：run 创建/completed/failed/拒答收口/外表审批批准驳回），
逐事件一行、action 恒 `agent_v2.*` 前缀（specs/infra.md 行为约定 3——与 V1
action 命名空间隔离）；写口唯一＝security.audit（B12）：
- run 创建      → agent_v2.run_created
- 终态收口      → agent_v2.run_completed / agent_v2.run_failed（一类两值）
- 拒答收口      → agent_v2.refused（与 notice type=refused 机读同源——约定 3）
- 外表审批决定  → agent_v2.extable_approved / agent_v2.extable_rejected（一类两值）

职责边界注记（票面任务 1）：run 簿记表（agent_v2_run/agent_v2_step）＝过程态
——状态机现值与逐步留痕，服务状态读面/回放；audit_log＝责任账——谁在何时以
何输入收的口，SM3 摘要指纹随行（00 §8）。两账分工不互替：簿记行可随 resume
重投影，审计行只追加（append-only）。

who 槽口径：恒取 resolve_actor 产的 Actor.who（label 全名）——ask 命令自带
（api 层 resolve_actor 解析后经 AskRequest.actor 进），resume 段回读 run 簿记行
actor 列（同源值）；空 actor 缺省落默认角色（00 §2.4，PRD 拍板＝阿强）。

直写扫描自守：本模块只 import SecurityService/AuditRow/ensure_audit_table——
audit_log 零直写面（tests/infra test_audit_single_writer 全树扫描仍绿）。
建表走 ensure_audit_table 幂等（checkfirst）——空库首次写审计不 500
（app/main.py:150 同款惯例；ensure 双轨约定，P0-08 先例）。
"""

from __future__ import annotations

from appv2.infra.db import ConnectionManager
from appv2.infra.security import Actor, AuditRow, SecurityService, resolve_actor
from appv2.infra.security.store import ensure_audit_table

# ---------- action 闭世界（四事件六值——恒 agent_v2.* 前缀） ----------

ACTION_RUN_CREATED = "agent_v2.run_created"
ACTION_RUN_COMPLETED = "agent_v2.run_completed"
ACTION_RUN_FAILED = "agent_v2.run_failed"
ACTION_REFUSED = "agent_v2.refused"
ACTION_EXTABLE_APPROVED = "agent_v2.extable_approved"
ACTION_EXTABLE_REJECTED = "agent_v2.extable_rejected"

# 输入/收口摘要截断（content 槽携人话摘要——正文全文归簿记行/事件流，不进审计）。
SUMMARY_LIMIT = 120


def summarize(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """摘要单点：换行折叠＋超长截断（截断可见——「…」后缀明示未全文）。"""
    flat = " ".join(text.split())
    if len(flat) <= limit:
        return flat
    return flat[:limit] + "…"


def who_of(actor: Actor) -> str:
    """who 槽单点：Actor.who 优先；空 actor 缺省落默认角色（00 §2.4）。"""
    return actor.who or resolve_actor(actor.user_id).who


class RunAuditor:
    """V2 run 链路审计面（executor 专用——四事件各一行，security.audit 唯一写口）。

    审计失败不静默也不翻盘：写口异常由调用方（executor._audit）转 notice 出流，
    已落定的 run 状态机零改动（责任账缺口可见，过程态不被污染）。
    """

    def __init__(
        self, db: ConnectionManager, security: SecurityService | None = None
    ) -> None:
        self._db = db
        self._security = security if security is not None else SecurityService(db)
        self._ready = False

    async def ensure_ready(self) -> None:
        """audit_log 幂等建表（每实例至多一次——空库首写不 500 惯例，见模块注）。"""
        if self._ready:
            return
        self._ready = True  # 先置后建（并发受理去重；checkfirst 幂等兜底）
        await ensure_audit_table(self._db.engine())

    async def run_created(self, *, run_id: str, question: str, who: str) -> None:
        await self._security.audit(
            AuditRow(
                who=who,
                action=ACTION_RUN_CREATED,
                content=f"问答受理：{summarize(question)}",
                meta={"run_id": run_id},
            )
        )

    async def run_completed(
        self, *, run_id: str, answer: str, manifest_digest: str, who: str
    ) -> None:
        await self._security.audit(
            AuditRow(
                who=who,
                action=ACTION_RUN_COMPLETED,
                content=f"回答收口：{summarize(answer)}",
                meta={"run_id": run_id, "manifest_digest": manifest_digest},
            )
        )

    async def run_failed(self, *, run_id: str, error: str, who: str) -> None:
        await self._security.audit(
            AuditRow(
                who=who,
                action=ACTION_RUN_FAILED,
                content=f"执行失败：{summarize(error)}",
                meta={"run_id": run_id},
            )
        )

    async def refused(self, *, run_id: str, reason: str, who: str) -> None:
        await self._security.audit(
            AuditRow(
                who=who,
                action=ACTION_REFUSED,
                content=f"拒答收口：{summarize(reason)}",
                meta={"run_id": run_id},
            )
        )

    async def extable_decided(
        self, *, run_id: str, approved: bool, approval_id: str, who: str
    ) -> None:
        action = ACTION_EXTABLE_APPROVED if approved else ACTION_EXTABLE_REJECTED
        verb = "批准" if approved else "驳回"
        await self._security.audit(
            AuditRow(
                who=who,
                action=action,
                content=f"外表审批{verb}：单号 {approval_id or '（未携）'}",
                meta={"run_id": run_id, "approval_id": approval_id},
            )
        )
