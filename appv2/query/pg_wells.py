"""query.pg_wells —— 数据链井闭世界生产读缝（V2-51 R4 软失败域闸——agg.dim_well 只读）。

前置条件机「链路域↔题眼域」一致性闸（软失败域闸——A-正8 形：data 链成功出数
但题眼井不在数据链域）的链路域真源：agg.dim_well 井号全集（120 口——N/X/Z 系
域；W/Y 系井只在报告域）。生产装配取井号集回 loader（frozenset[str]），与
production_waterline 同款读缝形状——create_app 组合根消费、runtime 前置条件
节点经 LoopDeps.data_wells 注入；读缝缺省/异常由 runtime 侧吞为空集（域闸
静默零漂移，不误伤）。

两读面同源（2026-10-17 流水 70 加）：井名录取值缝 `production_well_roster`
（(well_id, block_name) 序对——tools 层 dim_well 结构卡的名录段消费），井闭世界
`production_data_wells` 由同一次读取投影出井号集（单条 SQL 单点，零第二份读法）。

同步缝桥：复用 pg_waterline._run_sync 同款两态桥（无环本线程直跑；有环专用
线程另起环）。会话获取唯一经 infra.db（B3），readonly() 只读守卫恒挂（INV-2）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import column, select, table

from appv2.infra.db import DatabaseSpec
from appv2.query.pg_waterline import _run_sync

# ---------- dim_well 轻声明（DDL 真源＝Alembic 0014 agg 星型——读面消费列投影；
# agg 表带 schema 限定——agg.dim_well 不在默认 search_path，裸表名＝
# UndefinedTableError（P050CA8 首批实录：域闸静默）——schema 面修复） ----------

_DIM_WELL = table(
    "dim_well", column("well_id"), column("block_name"), schema="agg"
)


def production_well_roster(specs: Sequence[DatabaseSpec]) -> Any:
    """井名录取值缝（Callable[[], tuple[tuple[str, str], ...]] 形——井号＋区块）。

    盘面消费点＝tools 层 table_schema 的 dim_well 结构卡名录段（discover 现读
    ——**给值时机＝每次调用**，非装配期冻结快照）；loader 每次直读 dim_well 现行
    行全集（零缓存——井档随数据面刷新即新；行集小——120 口量级）。
    """
    def loader() -> tuple[tuple[str, str], ...]:
        return _run_sync(_load_roster(tuple(specs)))

    return loader


def production_data_wells(specs: Sequence[DatabaseSpec]) -> Any:
    """数据链井闭世界读缝（Callable[[], frozenset[str]] 形——create_app 组合根
    消费点）。**与 `production_well_roster` 同一次读取的投影**（单条 SQL 单点；
    每次调用直读现行行，零缓存）。"""
    roster = production_well_roster(specs)

    def loader() -> frozenset[str]:
        return frozenset(well_id for well_id, _block in roster())

    return loader


async def _load_roster(specs: tuple[DatabaseSpec, ...]) -> tuple[tuple[str, str], ...]:
    from appv2.infra.db import ConnectionManager

    db = ConnectionManager(specs)
    try:
        async with db.readonly() as session:
            rows = (
                await session.execute(
                    select(_DIM_WELL.c.well_id, _DIM_WELL.c.block_name)
                )
            ).all()
    finally:
        await db.dispose()
    # 空区块归一为空串（区块列 NULL＝未标——展示面按「未标区块」如实承载，
    # 零发明：不猜区块名、不伪造归属）。
    return tuple((str(row.well_id), str(row.block_name or "")) for row in rows)
