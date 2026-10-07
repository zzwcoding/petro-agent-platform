"""domains.wells.store —— 井档案域读模型取数（中台源表只读＋平台补位表）。

边界（票面红线）：
- B3：只走 infra.db——中台 8 表行一律经 ``db.readonly(role="midplatform")``
  命名只读路由取行（99 §2.0② 映射卡固定落点），**不直建引擎、不落镜像**；
  平台补位表 well_status_log 走 primary（99 §2.3——写入通道挂 99 开放问题 2，
  本域只建读面）。
- 行级注入：查询装配经 M-01 两步缝——``with_row_filter(actor, table)`` 产
  RowDomainScope（预埋期谓词恒空＝WHERE 恒真）→
  ``ConnectionManager.with_row_filter(stmt, predicates)`` 物理装配（99 §4.2
  冻结形状原样消费；真分权只换谓词生产实现，本文件零改动）。
- 中台源表不建 ORM 模型（as-is 湖表非平台聚合——99 §2.0 裁决，DDL 真源在
  数据面仓 DP-03）：独立 MetaData 上的 Core 轻声明（schema="raw"）只服务
  select 装配与行级谓词组合，**不入 Base.metadata**（平台建表面绝不触碰）；
  行投影为轻量行类。
- 设备台账（raw.equip_status）现供给无井关联列（DP-03 DDL 注记「列缺疑点
  已登记」）——按井取行装配批随中台扩列启用，本读面暂不查询该表（设备行
  由合同冻结演示快照承载，见 domain.device_snapshot_for）。
- 湖当前版过滤（DE-02 接线——E10 多批重复行收口；FX-06 对齐湖 scan as-of）：
  raw 湖表 append-only 多批叠加即重复行，读面查询按 per-key 最新版半连接过滤
  （每业务键 well_id 取 ``_snapshot_id <= N`` 的自身最新版，N＝服务层经
  LakeSnapshotLoader 解析的湖当前版批——DE-01 解析器缝；与 data-plane
  lake_store.scan 的 as-of 原文同语义：同批并列行全保留、跨批旧版被新版覆盖
  不混用；键为 None＝不过滤：账本无该表记录/缝未装配回落全量，DE-01 三态语义）。
  三张在查源表（well_info/well_measures/well_overhaul）逐表各解析各过滤；
  平台补位表 well_status_log 不经湖管道，不过滤。
"""

from __future__ import annotations

from datetime import date
from typing import Any, cast

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    Text,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.elements import ColumnElement

from app.domains.security import Actor
from app.domains.wells.domain import normalize_well_id
from app.infra.clock import now
from app.infra.db import Base, ConnectionManager, with_row_filter

# ---------- 平台补位表：well_status_log（99 §2.3 列形——本域唯一落表） ----------


class WellStatusLogRow(Base):
    """well_status_log——井状态变更行台账（8 表字典缺口的平台侧补位）。

    id bigserial（追加型序列主键例外，99 §1.2）；well_id 归一化主键——FK 语义
    指向中台 raw.well_info（跨库语义外键，不落物理 FK）；occurred_on＝状态变更
    发生日（events 排序键）；outcome＝警示文案 nullable；source_batch＝来源批次
    （补录语义可缺——§A.4 batch_id 同形；写入通道悬置 99 开放问题 2，本域只建
    读面不产行）。基线列 created_at/updated_at（99 §1.3）；索引 (well_id,
    occurred_on)。
    """

    __tablename__ = "well_status_log"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    well_id: Mapped[str] = mapped_column(String(8), nullable=False)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_batch: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[Any] = mapped_column(DateTime, nullable=False, default=now)
    updated_at: Mapped[Any] = mapped_column(DateTime, nullable=False, default=now)


Index(
    "well_status_log_well_id_occurred_on_idx",
    WellStatusLogRow.__table__.c.well_id,
    WellStatusLogRow.__table__.c.occurred_on,
)


async def ensure_wells_tables(engine: AsyncEngine) -> None:
    """well_status_log 幂等建表（P0-08 惯例）——与 Alembic 0017 并行存活。"""
    async with engine.begin() as conn:
        await conn.run_sync(
            cast(Table, WellStatusLogRow.__table__).create, checkfirst=True
        )


# ---------- 中台源表轻声明（schema="raw"——独立 MetaData，不入平台建表面） ----------

_RAW_META = MetaData()  # DDL 真源＝数据面仓 DP-03；平台侧零建表零镜像（99 §2.0）

_WELL_INFO = Table(
    "well_info", _RAW_META,
    Column("well_id", String(8)),
    Column("well_name", String(64)),
    Column("well_type", String(2)),
    Column("first_prod_date", Date),
    Column("platform", String(16)),
    Column("block_name", String(16)),
    Column("current_status", String(16)),
    Column("remarks", String(255)),
    Column("_snapshot_id", BigInteger),  # 湖技术列（DDL 真源 DP-03——当前版过滤寻址）
    schema="raw",
)
_WELL_MEASURES = Table(
    "well_measures", _RAW_META,
    Column("well_id", String(8)),
    Column("measure_type", String(32)),
    Column("job_date", Date),
    Column("_snapshot_id", BigInteger),  # 同上——湖技术列
    schema="raw",
)
_WELL_OVERHAUL = Table(
    "well_overhaul", _RAW_META,
    Column("well_id", String(8)),
    Column("overhaul_start", Date),
    Column("overhaul_end", Date),
    Column("overhaul_type", String(32)),
    Column("affected_output", String(32)),
    Column("batch_id", String(64)),
    # 湖技术列（DDL 真源 DP-03——当前版过滤寻址；批次血缘列名是 _src_batch_id，
    # 避让业务 batch_id）
    Column("_snapshot_id", BigInteger),
    schema="raw",
)


# ---------- 行投影（轻量行类——服务层零裸字典） ----------


class WellInfoRow:
    """raw.well_info 行投影（__slots__ 轻量——读面专用）。"""

    __slots__ = (
        "block_name",
        "current_status",
        "first_prod_date",
        "platform",
        "remarks",
        "well_id",
        "well_name",
        "well_type",
    )

    def __init__(self, row: Any) -> None:
        (
            self.well_id, self.well_name, self.well_type, self.first_prod_date,
            self.platform, self.block_name, self.current_status, self.remarks,
        ) = row


class MeasureLedgerRow:
    """raw.well_measures 行投影。"""

    __slots__ = ("job_date", "measure_type", "well_id")

    def __init__(self, row: Any) -> None:
        (self.well_id, self.measure_type, self.job_date) = row


class OverhaulLedgerRow:
    """raw.well_overhaul 行投影。"""

    __slots__ = (
        "affected_output",
        "batch_id",
        "overhaul_end",
        "overhaul_start",
        "overhaul_type",
        "well_id",
    )

    def __init__(self, row: Any) -> None:
        (
            self.well_id, self.overhaul_start, self.overhaul_end,
            self.overhaul_type, self.affected_output, self.batch_id,
        ) = row


class StatusLogLedgerRow:
    """well_status_log 行投影（id 供 events key=s{id} 源锚）。"""

    __slots__ = ("id", "occurred_on", "outcome", "source_batch", "title", "well_id")

    def __init__(self, row: Any) -> None:
        (
            self.id, self.well_id, self.occurred_on, self.title,
            self.outcome, self.source_batch,
        ) = row


# ---------- 读模型取数（midplatform 只读路由＋行级注入两步缝） ----------

_WELL_COLUMNS = (
    _WELL_INFO.c.well_id, _WELL_INFO.c.well_name, _WELL_INFO.c.well_type,
    _WELL_INFO.c.first_prod_date, _WELL_INFO.c.platform,
    _WELL_INFO.c.block_name, _WELL_INFO.c.current_status, _WELL_INFO.c.remarks,
)


def _current_version_asof(table: Table, snapshot_id: int) -> ColumnElement[bool]:
    """per-key 最新版半连接谓词（FX-06——对齐湖底座 scan 的 as-of 原文语义）。

    快照 N＝截至 N 的全表生效视图：每业务键（well_id——三张在查源表的湖业务
    键，data-plane lake_store._BUSINESS_KEYS）取 ``_snapshot_id <= N`` 的自身
    最新版——行版本＝该键窗口内最大 ``_snapshot_id``（相关子查询半连接，与
    lake_store.scan 的 RANK()=1 等价：同批并列行全保留、跨批旧版被新版覆盖
    不混用）。替代 DE-02 的「全局最新批等值」——增量批（只导变化井）下不在
    最新批的井不再静默消失（R1-01 裁决：修正确语义优于锁「每批全量导出」前提）。
    """
    inner = table.alias()  # 自连接别名——相关子查询内表
    return table.c._snapshot_id == (
        select(func.max(inner.c._snapshot_id))
        .where(
            inner.c.well_id == table.c.well_id,
            inner.c._snapshot_id <= snapshot_id,
        )
        .scalar_subquery()
    )


class WellsStore:
    """井档案读模型取数（纯读——无写出口）。"""

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db

    async def list_wells(
        self, actor: Actor, snapshot_id: int | None = None
    ) -> list[WellInfoRow]:
        """选井全行（端点 1）——行级过滤在服务端（无权限的井不出现，F48）。

        snapshot_id＝湖当前版批（as-of 上界 N——非 None 时 per-key 最新版
        半连接过滤，见 ``_current_version_asof``／FX-06；None＝不过滤回落
        全量）。
        """
        scope = with_row_filter(actor.user_id, "raw.well_info")
        stmt = select(*_WELL_COLUMNS)
        if snapshot_id is not None:
            stmt = stmt.where(_current_version_asof(_WELL_INFO, snapshot_id))
        stmt = stmt.order_by(_WELL_INFO.c.well_id.asc())
        stmt = ConnectionManager.with_row_filter(stmt, scope.predicates)
        async with self._db.readonly(role="midplatform") as session:
            rows = (await session.execute(stmt)).all()
        return [WellInfoRow(r) for r in rows]

    async def get_well(
        self, well_id: str, actor: Actor, snapshot_id: int | None = None
    ) -> WellInfoRow | None:
        """单井档案行（行级过滤内）——403/404 判别的「过滤内」半边。

        snapshot_id＝湖当前版过滤键（DE-02——与判别另一半同键，井只在旧批
        存在＝当前世界没有＝404，不洗白成可见）。
        """
        scope = with_row_filter(actor.user_id, "raw.well_info")
        stmt = select(*_WELL_COLUMNS).where(
            _WELL_INFO.c.well_id == normalize_well_id(well_id)
        )
        if snapshot_id is not None:
            stmt = stmt.where(_current_version_asof(_WELL_INFO, snapshot_id))
        stmt = ConnectionManager.with_row_filter(stmt, scope.predicates)
        async with self._db.readonly(role="midplatform") as session:
            row = (await session.execute(stmt)).first()
        return WellInfoRow(row) if row is not None else None

    async def get_well_unfiltered(
        self, well_id: str, snapshot_id: int | None = None
    ) -> WellInfoRow | None:
        """单井档案行（不过滤）——「存在但无权 vs 世界里没有」的判别半边。

        「不过滤」指行级数据域谓词不装（403/404 二分语义）；湖当前版过滤
        与 get_well 同键同装（DE-02——两半边同一「当前版」世界）。
        """
        normalized = normalize_well_id(well_id)
        stmt = select(_WELL_INFO.c.well_id).where(
            _WELL_INFO.c.well_id == normalized
        )
        if snapshot_id is not None:
            stmt = stmt.where(_current_version_asof(_WELL_INFO, snapshot_id))
        async with self._db.readonly(role="midplatform") as session:
            row = (await session.execute(stmt)).first()
        return WellInfoRow(row) if row is not None else None

    async def list_measures(
        self, well_id: str, snapshot_id: int | None = None
    ) -> list[MeasureLedgerRow]:
        """措施台账行（映射卡固定落点 well_measures；作业日倒序——events 排序键）。

        snapshot_id＝湖当前版过滤键（DE-02——关系链台账同款过滤，多批叠加
        不重复出行；None＝不过滤）。
        """
        normalized = normalize_well_id(well_id)
        stmt = select(
            _WELL_MEASURES.c.well_id, _WELL_MEASURES.c.measure_type,
            _WELL_MEASURES.c.job_date,
        ).where(_WELL_MEASURES.c.well_id == normalized)
        if snapshot_id is not None:
            stmt = stmt.where(
                _current_version_asof(_WELL_MEASURES, snapshot_id)
            )
        stmt = stmt.order_by(_WELL_MEASURES.c.job_date.desc().nulls_last())
        async with self._db.readonly(role="midplatform") as session:
            rows = (await session.execute(stmt)).all()
        return [MeasureLedgerRow(r) for r in rows]

    async def list_overhauls(
        self, well_id: str, snapshot_id: int | None = None
    ) -> list[OverhaulLedgerRow]:
        """检修台账行（well_overhaul；完工日倒序——events 排序键）。

        snapshot_id＝湖当前版过滤键（DE-02——同 list_measures）。
        """
        normalized = normalize_well_id(well_id)
        stmt = select(
            _WELL_OVERHAUL.c.well_id, _WELL_OVERHAUL.c.overhaul_start,
            _WELL_OVERHAUL.c.overhaul_end, _WELL_OVERHAUL.c.overhaul_type,
            _WELL_OVERHAUL.c.affected_output, _WELL_OVERHAUL.c.batch_id,
        ).where(_WELL_OVERHAUL.c.well_id == normalized)
        if snapshot_id is not None:
            stmt = stmt.where(
                _current_version_asof(_WELL_OVERHAUL, snapshot_id)
            )
        stmt = stmt.order_by(_WELL_OVERHAUL.c.overhaul_end.desc().nulls_last())
        async with self._db.readonly(role="midplatform") as session:
            rows = (await session.execute(stmt)).all()
        return [OverhaulLedgerRow(r) for r in rows]

    async def list_status_changes(self, well_id: str) -> list[StatusLogLedgerRow]:
        """状态变更行（平台补位表 well_status_log——primary 读面；发生日倒序）。

        写入通道挂 99 开放问题 2（本域只读不写）；events key＝s{id}（源行锚）。
        """
        normalized = normalize_well_id(well_id)
        async with self._db.readonly(role="primary") as session:
            rows = (
                await session.execute(
                    select(
                        WellStatusLogRow.id, WellStatusLogRow.well_id,
                        WellStatusLogRow.occurred_on, WellStatusLogRow.title,
                        WellStatusLogRow.outcome, WellStatusLogRow.source_batch,
                    )
                    .where(WellStatusLogRow.well_id == normalized)
                    .order_by(WellStatusLogRow.occurred_on.desc().nulls_last())
                )
            ).all()
        return [StatusLogLedgerRow(r) for r in rows]
