"""domains.dataops.quality.channel —— 复扫执行通道生产适配器（M-05b）。

增量复扫（E2 端点 7 ``action:"rescan"``）接数据面质检通道的跨服务形态，按
DP-04 交付适配：数据面＝APScheduler worker 管道，跨服务通信走**任务表轮询**
（quality_task 行形＝接口合同，零共享库——四耦合点①；HTTP 触发接口 DP-04
未交付，不虚构端点）。

复扫子操作的通道语义（对位合同「对修正批次重跑命中规则——数据面质检通道的
子操作」）：
1. 发起半边：经 QualityService.accept_task 落复扫任务行（running/step=0，
   复扫不是重跑——不撤分发单 clear_stale=False；单任务闸同闸 409）；
2. 拾取半边：数据面 worker 拾取执行（施工归数据面仓票——本票只锁行形合同）；
3. 结论半边：限时轮询任务表至 done，按单裁决——报告 hits 中该单规则是否仍
   命中该单对象（hit_identity 同投影对位 dedupe_key 逆解析身份）：仍命中＝
   仍有命中（明细随行），未命中＝全绿。

判绿词表纪律（M-05a rev F2 义务）：本适配器只产出 RescanOutcome（batch/green/
detail）——verify.note 文案一律由 service 经 ``domain.rescan_note`` 落笔，
全绿＝RESCAN_GREEN_NOTE 哨兵同词表，关闭守卫机判不失配。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

from app.domains.dataops.quality.domain import (
    QualityIssueNotFoundError,
    QualityTaskChannelDeferredError,
    RescanOutcome,
    RescanRequest,
    TaskAcceptedReceipt,
    hit_identity,
    hit_render,
    parse_dedupe_key,
)
from app.domains.dataops.quality.service import QualityService
from app.domains.dataops.quality.store import QualityStore
from app.infra.db import ConnectionManager

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_POLL_SECONDS = 0.25


class TaskAcceptor(Protocol):
    """复扫发起缝形（QualityService.accept_task 的结构类型——B9 运行期只见 callable）。"""

    async def __call__(
        self, *, clear_stale: bool = True
    ) -> TaskAcceptedReceipt: ...


class DataPlaneChannelRescanExecutor:
    """复扫通道适配器（生产装配——main.py 组合根经 QualityService 两段绑定）。

    拾取半边不可 stub 进本类（替身纪律：只许测试替身，替身在测试侧直接改写
    quality_task 行——模拟数据面 worker 拾取，行形＝DP-05 交付语义）。
    """

    def __init__(
        self,
        db: ConnectionManager,
        accept_task: TaskAcceptor,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
    ) -> None:
        self._db = db
        self._accept = accept_task
        self._timeout = timeout_seconds
        self._poll = poll_seconds

    async def __call__(self, request: RescanRequest) -> RescanOutcome:
        """复扫执行缝本体（domain.RescanExecutor 形状——lane 不变回填由 service）。"""
        store = QualityStore(self._db)
        issue = await store.get_issue(request.issue_id)
        if issue is None:
            raise QualityIssueNotFoundError(f"问题单不存在：{request.issue_id}")
        # 单身份＝挂单去重键逆解析（本域私产键形）；与请求规则号不一致以键为准
        # （键定义挂单身份——请求号只是单面冗余，不硬转不失配）。
        rule_no, object_key, data_date = parse_dedupe_key(issue.dedupe_key or "")
        accepted = await self._accept(clear_stale=False)
        deadline = time.monotonic() + self._timeout
        while True:
            row = await store.get_task(accepted.task_id)
            if row is not None and row.status == "done" and row.report is not None:
                return self._verdict(
                    str(row.id), dict(row.report), rule_no, object_key, data_date
                )
            if time.monotonic() >= deadline:
                raise QualityTaskChannelDeferredError(
                    f"复扫任务 {accepted.task_id} 在 {self._timeout:g}s 内未被数据面"
                    "拾取完成（任务表轮询通道超时——数据面 worker 拾取半边未运行，"
                    "不 mock 假复扫结论）"
                )
            await asyncio.sleep(self._poll)

    @staticmethod
    def _verdict(
        task_id: str,
        report: dict[str, Any],
        rule_no: int,
        object_key: str,
        data_date: str,
    ) -> RescanOutcome:
        """按单裁决：报告 hits 中该单规则是否仍命中该单对象（白名单投影同键对位）。
        该单对象不再命中＝全绿（哪怕同规则他对象仍挂——增量复扫按单说话）。"""
        for entry in report.get("hits") or []:
            if not isinstance(entry, dict) or entry.get("rule_no") != rule_no:
                continue
            for loc in entry.get("sample") or []:
                if not isinstance(loc, dict):
                    continue
                if hit_identity(loc) == (object_key, data_date):
                    return RescanOutcome(
                        batch=task_id,
                        green=False,
                        detail=f"规则 {rule_no} 仍命中：{hit_render(loc)}",
                    )
        return RescanOutcome(batch=task_id, green=True)


def bind_channel_rescan(service: QualityService, db: ConnectionManager) -> None:
    """组合根装配（main.py 用）：service × 通道适配器两段绑定——消解「服务持缝、
    缝需服务受理口」的环（B9：绑定后运行期只见 callable）。"""
    service.bind_rescan_executor(
        DataPlaneChannelRescanExecutor(db, service.accept_task)
    )


__all__ = [
    "DEFAULT_POLL_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "DataPlaneChannelRescanExecutor",
    "bind_channel_rescan",
]
