"""domains.wells.snapshot —— 湖当前版快照解析器（E10 前半——读面公用纯函数）。

定位（DE-01 票面）：湖底座 append-only——每批进料在 ``data_plane.lake_snapshot``
账本记一行，raw 湖表多批叠加即重复行（云上实证 well_info 4 批 480 行）。本模块
给定表名（如 ``well_info``）→ 返回该表湖当前版批次（最新 snapshot 行的寻址键），
供 wells 读面做「当前版」过滤（DE-02 三端点接线；本票不生产装配）。

三态语义（测试逐态断言，tests/domains/wells/test_wells_snapshot.py）：
- 账本多批 → 最新批（snapshot_id 最大——BIGSERIAL 单调，追加序即版本序）；
- 账本单批 → 该批；
- 账本无该表记录 → 返回 None＝不过滤（该表未经湖管道，读全量是合理缺省）
  ＋日志 warning 一次（每表一次，不刷屏）。

取数路径定案（DE-01 票面交付物 1——拓扑核对记录，证据全出仓内配置/部署文件）：
- **dev（compose 单实例）**：compose.yaml 仅一台 pg（localhost:5433/petro）；
  config/database.yaml midplatform 段缺省同实例（注释原文「dev 期与平台库同实例
  不同 schema（raw/clean/data_plane，DP-03 拍板）」）；runbook §5 数据面 dev 直连
  petro 开发账号——data_plane.lake_snapshot 与平台 primary 同库。
- **云（tpa 项目）**：deploy/cloud/compose.yml 单实例 tpa-postgres，tpa-backend
  与 tpa-worker 同网同依赖（worker 湖连接 DATABASE_URL 指 tpa-postgres）；E10
  实证 wells 读面看到 4 批湖数据＝midplatform 路由与湖账本同实例。
- **闭世界**：data-plane 仓 migrations/midplatform_readonly.sql——clean/data_plane
  schema 与湖元数据两表（lake_table/lake_snapshot）一律不授权；故本解析器走
  **平台 primary 只读路由**（``db.readonly(role="primary")``，与 well_status_log
  读面同款）读账本，midplatform 账号授权面零变更（PG 集成测试对账
  information_schema.role_table_grants 恰 8 表 SELECT——tests/domains/wells/
  test_wells_snapshot_pg.py）。
- 登记核对点：ADR-0003 拍板 2 生产拆分（中台库独立实例）落地后，平台 primary
  账号对湖账本是否仍可达＝部署批按实际拓扑核对（同 runbook §1.2 核对点句式；
  现状 dev/云两条链路均同实例，primary 可达）。

连接与建表面边界（B3）：不直建引擎、不落镜像；账本轻声明＝独立 MetaData 上的
Core 三列投影（DDL 真源＝data-plane 仓 migrations/001_lake_schemas.up.sql），
**不入 Base.metadata**（平台建表面绝不触碰）——同 store.py 中台源表轻声明惯例。
注入缝：``LakeSnapshotLoader`` 可空依赖类型（照 chat 域 WaterlineLoader 同款
形状——运行期只见 callable），DE-02 的 wells service 构造参数接入。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import (
    BigInteger,
    Column,
    MetaData,
    String,
    Table,
    select,
)
from sqlalchemy.exc import DBAPIError

from app.infra.db import ConnectionManager

LOGGER = logging.getLogger(__name__)

# PG undefined_table（SQLSTATE 42P01）＝账本表不存在（数据面未 boot）的驱动判据
_UNDEFINED_TABLE_SQLSTATE = "42P01"

# ---------- 湖账本轻声明（schema="data_plane"——独立 MetaData，不入平台建表面） ----------

_LAKE_META = MetaData()  # DDL 真源＝data-plane 仓 001_lake_schemas.up.sql；平台侧零建表

_LAKE_SNAPSHOT = Table(
    "lake_snapshot", _LAKE_META,
    Column("snapshot_id", BigInteger),
    Column("table_name", String(128)),
    Column("batch_id", String(64)),
    schema="data_plane",
)


# ---------- 投影面（轻量——服务层零裸字典） ----------


@dataclass(frozen=True, slots=True)
class SnapshotLedgerRow:
    """data_plane.lake_snapshot 行投影（解析输入——账本两业务列）。"""

    snapshot_id: int
    batch_id: str


@dataclass(frozen=True, slots=True)
class LakeSnapshotFace:
    """湖当前版批次面（解析器返回投影——形状照 chat 域 WaterlineFace 同款）。

    snapshot_id＝当前版过滤寻址键（raw 湖技术列 ``_snapshot_id`` 的对账值，
    E10 修法「_snapshot_id = 湖当前版」）；batch_id＝批次键随面携行（血缘/
    日志可读）；缺记录时 loader 返回 None（调用方不过滤＝读全量）。
    """

    table_name: str
    snapshot_id: int
    batch_id: str


# 注入缝（照 chat 域 WaterlineLoader 同款形状——可空依赖，运行期只见 callable）：
# DE-02 的 wells service 构造参数接入；本票不生产装配（组合根零改动）。
LakeSnapshotLoader = Callable[[str], Awaitable[LakeSnapshotFace | None]]


# ---------- 三态语义纯函数（无 DB、无框架——B1 可直测） ----------


def resolve_current_snapshot(
    rows: Sequence[SnapshotLedgerRow], table_name: str
) -> LakeSnapshotFace | None:
    """三态语义：多批→最新批；单批→该批；账本无记录→None＝不过滤。

    「最新」判据＝snapshot_id 最大（BIGSERIAL 单调递增——湖账本 append-only，
    追加序即版本序；committed_at 同源不另作判据）。表名原样携入投影。
    """
    if not rows:
        return None
    latest = max(rows, key=lambda row: row.snapshot_id)
    return LakeSnapshotFace(
        table_name=table_name,
        snapshot_id=latest.snapshot_id,
        batch_id=latest.batch_id,
    )


# ---------- 薄查询（primary 只读路由读账本；warning 每表一次） ----------


def _is_undefined_table(exc: BaseException) -> bool:
    """DBAPIError → PG undefined_table（SQLSTATE 42P01）判别。

    驱动异常携 ``sqlstate``；SQLAlchemy 包装后 ``orig`` 指回驱动层错误——
    两处任一命中即判（FX-01：非 42P01 的错误不吞、原样上抛）。
    """
    for source in (getattr(exc, "orig", None), exc):
        code = getattr(source, "sqlstate", None) or getattr(
            source, "pgcode", None
        )
        if code == _UNDEFINED_TABLE_SQLSTATE:
            return True
    return False


class LakeSnapshotReader:
    """湖账本薄查询——给定表名返回湖当前版批次面（纯函数承载选择逻辑）。

    取数路径＝primary 只读路由（拓扑核对定案，见模块 docstring）；midplatform
    路由不承担此读面（闭世界对 data_plane 零授权——不扩权，DE-01 红线）。
    账本无该表记录→None＋warning 一次（每表去重——None 是合理缺省不是错误，
    但「表未经湖管道」值得在案可见，读面排障有锚）。账本**表本身**不存在
    （数据面未 boot——建表方是数据面 LakeCatalog._ensure_meta，平台侧不建账本）
    → undefined_table 捕获后与「无记录」同归 None＋warning 一次（FX-01——
    读面回落全量，不再 500；R1-02 裁决）。
    """

    def __init__(self, db: ConnectionManager) -> None:
        self._db = db
        self._warned: set[str] = set()

    async def current_snapshot(self, table_name: str) -> LakeSnapshotFace | None:
        """解析表名 → 湖当前版批次面；账本无记录/账本表未建 → None（＋warning 一次）。"""
        ledger_missing = False
        stmt = select(
            _LAKE_SNAPSHOT.c.snapshot_id, _LAKE_SNAPSHOT.c.batch_id
        ).where(_LAKE_SNAPSHOT.c.table_name == table_name)
        try:
            async with self._db.readonly(role="primary") as session:
                ledger_rows = [
                    SnapshotLedgerRow(snapshot_id=int(row[0]), batch_id=str(row[1]))
                    for row in (await session.execute(stmt)).all()
                ]
        except DBAPIError as exc:
            # 账本表本身不存在（数据面未 boot，平台侧不建账本）＝与「无记录」
            # 同态：归 None 过滤缺省放行＋warning 一次（FX-01 兜底，R1-02）。
            if not _is_undefined_table(exc):
                raise
            ledger_missing = True
            ledger_rows = []
        face = resolve_current_snapshot(ledger_rows, table_name)
        if face is None and table_name not in self._warned:
            self._warned.add(table_name)
            if ledger_missing:
                LOGGER.warning(
                    "湖账本表 data_plane.lake_snapshot 不存在（表 %r 查询报"
                    " undefined_table——数据面未 boot，平台侧不建账本）——"
                    "当前版过滤缺省放行，读面回落全量（FX-01 兜底）",
                    table_name,
                )
            else:
                LOGGER.warning(
                    "湖账本无表 %r 的快照记录——当前版过滤缺省放行"
                    "（该表未经湖管道，读全量＝合理缺省；DE-01 三态语义）",
                    table_name,
                )
        return face


# ---------- 注入缝消费示例（DE-02 接线形状预告——本票不装配） ----------
#
#     class WellsService:
#         def __init__(
#             self, db: ConnectionManager,
#             snapshot_loader: LakeSnapshotLoader | None = None,
#         ) -> None: ...
#
#     # 生产装配（DE-02）：
#     reader = LakeSnapshotReader(manager)
#     WellsService(manager, snapshot_loader=reader.current_snapshot)
#
# 谓词形状由 DE-02 落地、FX-06 对齐湖 scan as-of：raw 行过滤＝per-key 最新版
# 半连接（每业务键取 ``_snapshot_id <= face.snapshot_id`` 的自身最新版——
# store._current_version_asof；face.snapshot_id 作 as-of 上界 N）。
