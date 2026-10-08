"""query.pg_waterline —— 汇总层水位生产读缝（V2-19——E2 water_line 表只读）。

water_line（Alembic 0015——DP-05 质检实体落库同源）三层数据新鲜度水位：生产
装配取「汇总层」（问数用层——E2 行为约定 8）回 WatermarkFace（data_date/
promise 随行）；T-1 判定（freshness_judgment——V1 dataops/quality 同名纯函数
语义原样：基准＝T-1（today−1），data_date ≥ T-1 即达标，否则落后 N 天 · 超期）
在供给方单源算好随面携入（query 引擎只消费不重算——specs/modules.md query 卡
「新鲜度/降级语义内聚」的供给侧边界）。水位未回写（汇总层缺行）→ None——
血缘④「数据截至批次」如实缺行（不造达标假象）。

同步缝桥：WaterlineLoader＝Callable[[], WatermarkFace | None] 同步签名
（query.engine 定义）——与 pg_executor._run_sync 同款两态桥（无环本线程直跑；
有环专用线程另起环；逐调用新建专用 ConnectionManager——连接池与当次环同源）。
会话获取唯一经 infra.db（B3），readonly() 只读守卫恒挂（INV-2）。
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Any

from sqlalchemy import column, select, table

from appv2.infra import clock
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.query.engine import WatermarkFace

# ---------- T-1 判定（E2 端点 8 合同值——承诺 T-1＝昨天的数今天要能看到） ----------

WATER_PROMISE = "T-1"
WATER_LAYER_AGG = "汇总层"  # 问数用层（E2 行为约定 8——water_line 三层之问数读点）
FRESHNESS_OK_TAG = "达标（承诺 T-1）"
FRESHNESS_LATE_TAG = "落后 {n} 天 · 超期"


def freshness_judgment(data_date: date, today: date) -> tuple[str, int]:
    """T-1 判定（纯函数）：→ (tag, 落后天数)。

    基准＝T-1（today−1）：data_date ≥ T-1 即达标（承诺 T-1）；否则落后
    N 天＝T-1 基准日 − data_date（合同端点 8 示例：基准 09-14 对 data_date
    09-11 → 落后 3 天 · 超期）。V1 dataops/quality 同名函数语义原样。
    """
    baseline = today - timedelta(days=1)
    late = (baseline - data_date).days
    if late <= 0:
        return FRESHNESS_OK_TAG, 0
    return FRESHNESS_LATE_TAG.format(n=late), late


# ---------- water_line 轻声明（DDL 真源＝Alembic 0015——读面消费列投影） ----------

_WATER_LINE = table(
    "water_line",
    column("layer"), column("data_date"), column("promise"),
)


def _run_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """同步缝→异步 DB 桥（无环本线程直跑；有环专用线程另起环——见模块 docstring）。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


def _as_date(value: Any) -> date:
    """DATE 列双形态归一（asyncpg 回 date；aiosqlite 回 ISO 文本）。"""
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def production_waterline(
    specs: Sequence[DatabaseSpec],
    *,
    today: Any = None,
) -> Any:
    """汇总层水位读缝（WaterlineLoader 形——create_app 生产组合消费点）。

    today＝时钟缝（None＝infra.clock——B14；测试注入固定执行日）。loader 每
    次调用直读 water_line 现行行（零缓存——水位随数据面刷新即新）；汇总层
    缺行回 None（引擎血缘④如实缺行、新鲜度闸不误拦）。
    """
    def loader() -> WatermarkFace | None:
        return _run_sync(_load(tuple(specs), today))

    return loader


async def _load(specs: tuple[DatabaseSpec, ...], today: Any) -> WatermarkFace | None:
    db = ConnectionManager(specs)
    try:
        async with db.readonly() as session:
            rows = (
                await session.execute(
                    select(*_WATER_LINE.c).order_by(_WATER_LINE.c.layer)
                )
            ).all()
    finally:
        await db.dispose()
    row = next((r for r in rows if r.layer == WATER_LAYER_AGG), None)
    if row is None:
        return None
    data_date = _as_date(row.data_date)
    now = today() if today is not None else clock.now().date()
    tag, late_days = freshness_judgment(data_date, now)
    return WatermarkFace(
        layer=str(row.layer),
        data_date=data_date,
        promise=str(row.promise),
        tag=tag,
        late_days=late_days,
    )
