"""domains.retrieval.service —— 薄服务面：编排 store 与域校验（语义在 domain.py）。

公开面（D2 两端点＋P1-08a/b 消费读缝）：
- effective_config：全量生效配置（首次读取自动落种子——gateway_budget_config
  单例种子先例）；端点 1「GET 恒返回当前生效值，待审 patch 不进响应」。
- submit_change_request：变更单受理→生效一体（阶段 1 过渡形态——服务端记审计
  由 api 层经 security.audit 承担，B12；版本推进/via 回链在本事务闭环）。

在途闸（D2 409「单在途串行」）：阶段 1 受理→生效一体、无审批等待期，在途窗口
＝受理处理期——进程内 check-and-set 闸（单进程演示底座；A3/C3 接入批切回审批
链后在途单权威状态以 A3 单据投影，跨进程串行化随批）。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domains.retrieval.domain import (
    PENDING_STATE,
    ConfigSnapshot,
    ConfigVersion,
    RetrievalConflictError,
    merge_config,
    next_change_request_id,
    next_version_no,
    snapshot_from_dict,
    validate_patch,
)
from app.domains.retrieval.store import ConfigStore, RetrievalConfigVersionRow
from app.infra.clock import now
from app.infra.db import ConnectionManager


@dataclass(frozen=True, slots=True)
class ChangeRequestReceipt:
    """变更单受理回执（端点 2：合同冻结字段＋票面追加的新配置与版本）。

    state 维持合同字面 "pending"（A3 审批链形态值——阶段 1 变动单不落 A3，
    受理即生效；生效性由 version.via＝本单号回链承载，差异登记于票面）。
    """

    change_request_id: str
    state: str
    config: ConfigSnapshot
    version: ConfigVersion
    sections: tuple[str, ...]


class RetrievalService:
    """检索配置域服务（薄）：种子/版本链在 store，校验/合并/号段在 domain。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db
        self._store = ConfigStore(db)
        self._submit_inflight = False

    async def effective_config(self) -> ConfigSnapshot:
        """全量生效配置（端点 1 读面＋P1-08a/b 消费缝；首次读取自动落种子）。"""
        async with self._db.session() as session:  # 可写会话——首读种子（gateway 先例）
            _pointer, current = await self._store.ensure_seeded(session)
            return self._snapshot_of(current)

    async def submit_change_request(
        self, patch: object, *, updated_by: str
    ) -> ChangeRequestReceipt:
        """变更单受理→生效一体（阶段 1 过渡——版本推进＋via 回链＋指针切换同事务）。

        校验（400 带字段与允许区间）→ 新版本落库（via=变更单号）→ 生效指针
        切换；空库先落种子再叠加 patch。B12 审计（retrieval.config_changed）
        由 api 层在服务成功返回后经 security.audit 落笔（gateway 先例——本域
        不依赖 security）。
        """
        self._begin_submit()
        try:
            sections = validate_patch(patch)  # RetrievalParamError（400）——域校验单源
            async with self._db.session() as session:
                pointer, current = await self._store.ensure_seeded(session)
                merged = merge_config(current.config, sections)
                at = now()
                version_no = next_version_no(await self._store.version_nos(session))
                change_request_id = next_change_request_id(await self._store.vias(session), at)
                row = RetrievalConfigVersionRow(
                    version_no=version_no,
                    config=merged,
                    updated_at=at,
                    updated_by=updated_by,
                    via=change_request_id,
                    created_at=at,
                )
                session.add(row)
                await session.flush()  # 先 INSERT 版本行（FK 被引用方——P1-06 flush 排序纪律）
                pointer.current_version_no = version_no
                pointer.updated_at = at
                await session.flush()
                version = ConfigVersion(
                    no=version_no, updated_at=at, updated_by=updated_by, via=change_request_id
                )
                return ChangeRequestReceipt(
                    change_request_id=change_request_id,
                    state=PENDING_STATE,
                    config=snapshot_from_dict(merged, version),
                    version=version,
                    sections=tuple(sections),
                )
        finally:
            self._end_submit()

    @staticmethod
    def _snapshot_of(row: RetrievalConfigVersionRow) -> ConfigSnapshot:
        version = ConfigVersion(
            no=row.version_no, updated_at=row.updated_at, updated_by=row.updated_by, via=row.via
        )
        return snapshot_from_dict(row.config, version)

    def _begin_submit(self) -> None:
        """在途闸 check-and-set（同步段——并发受理下先到者确定性胜出）。"""
        if self._submit_inflight:
            raise RetrievalConflictError(
                "已有在途变更受理——同页变更单串行（D2 409；阶段 1 受理即生效，"
                "在途窗口＝受理处理期）"
            )
        self._submit_inflight = True

    def _end_submit(self) -> None:
        self._submit_inflight = False
