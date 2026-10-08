"""knowledge.pg_store —— PgKnowledgeStore（sem_* 台账生产读面——V2-19，
specs/modules.md knowledge 卡外部依赖「PG sem_* 表（只读）」的落位件）。

specs/knowledge.md「不做什么」：「不做缓存层（本期直读 PG，量级允许）」——
本适配器**每次查询直读 sem_* 现行行**（逐调用新建专用会话管理器），零跨调用
缓存；证据装配（Row→Evidence 机械拼装、命中顺序、binding_state 判定）单点
复用 InMemoryKnowledgeStore——同一行值下两适配器 Evidence 逐字段全等
（tests/domains/test_v2_knowledge_pgstore.py 机器证明），生产行为与 fixture
读面对齐不靠誊写。

同步缝桥（KnowledgeStore 四方法为 specs 接口定义节的同步签名；DB 面经
infra.db ConnectionManager 为异步会话）：_run_sync 把协程落到事件循环——
无运行环（测试/组合态）本线程 asyncio.run 直跑；已在运行环内（runtime 工具
处理器）落专用单线程池另起环执行。逐调用新建 ConnectionManager 的理由：
连接池绑定创建它的事件循环（asyncpg 连接不可跨环复用）——专用管理器随调用
建/拆（finally dispose），池连接永远与当次环同源；会话获取仍唯一经 infra.db
（B3 红线不破），readonly() 只读守卫恒挂（INV-2/只读会话双保险）。

表访问＝Core 轻声明（sqlalchemy.table/column——读模型不入 ORM Base.metadata，
V1 agg 星型同款纪律）；jsonb 列经驱动回 str（asyncpg 对 jsonb 缺省回文本，
sqlite 测试底座 TEXT 同形）——投影层 json.loads 单点归一，方言零分叉。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import column, select, table

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.knowledge.domain import Evidence, SemanticQuery
from appv2.knowledge.snapshot import (
    RELATION_TYPES_JSON,
    LedgerSnapshot,
    MetricRow,
    ObjectRow,
    RelationRow,
    TermRow,
    glossary_aliases,
    load_relation_families,
)
from appv2.knowledge.store import InMemoryKnowledgeStore, KnowledgeStore


def _run_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """同步缝→异步 DB 桥（无环本线程直跑；有环专用线程另起环——见模块 docstring）。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


# ---------- sem_* 四账轻声明（DDL 真源＝Alembic 0002/0019——读面消费列投影） ----------

_SEM_METRIC = table(
    "sem_metric",
    column("id"), column("name"), column("slot_name"), column("def"),
    column("grain"), column("unit"), column("status"), column("dispute"),
    column("version"), column("calibers"), column("default_caliber"),
)
_SEM_TERM = table(
    "sem_term",
    column("id"), column("term"), column("type"), column("def"),
    column("status"), column("status_key"), column("version"), column("expires_at"),
)
_SEM_OBJECT = table(
    "sem_object",
    column("id"), column("obj"), column("attr"), column("status"), column("version"),
)
_SEM_RELATION = table(
    "sem_relation",
    column("id"), column("rel"), column("read"),
)


def _json_list(value: Any) -> list[Any]:
    """jsonb/TEXT 双形态归一（驱动回 str 则解析；测试底座直回容器则透传）。"""
    if value is None:
        return []
    if isinstance(value, str):
        loaded = json.loads(value)
        return list(loaded) if isinstance(loaded, list) else [loaded]
    return list(value)


def _as_date(value: Any) -> date | None:
    """DATE 列双形态归一（asyncpg 回 date；aiosqlite 回 ISO 文本）。"""
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _calibers(raw: Any) -> tuple[dict[str, Any], ...]:
    """calibers jsonb → 读面投影三键（key/name/default——desc 不消费，快照同口径）。"""
    return tuple(
        {"key": str(item["key"]), "name": str(item["name"]),
         "default": bool(item.get("default"))}
        for item in _json_list(raw)
    )


class PgKnowledgeStore(KnowledgeStore):
    """sem_* 台账直读读面（生产适配器——四公开方法＝KnowledgeStore seam 原形）。

    构造只收连接规格（每查询新建专用 ConnectionManager——循环绑定安全，见模块
    docstring）；aliases/families 无台账承载列（glossary 投影/本体导出物）——
    沿 fixture 同源装载（glossary_aliases/load_relation_families），构造期可注
    覆盖。全程只读（INV-2）：readonly 会话守卫＋返回容器副本＋零写出口。
    """

    def __init__(
        self,
        specs: Sequence[DatabaseSpec],
        *,
        today: date | None = None,
        aliases: dict[str, str] | None = None,
        families_path: Path | None = None,
    ) -> None:
        self._specs = tuple(specs)
        self._today = today
        self._aliases = dict(aliases) if aliases is not None else None
        self._families_path = (
            families_path if families_path is not None else RELATION_TYPES_JSON
        )

    # ---------- 四公开方法（KnowledgeStore 实现） ----------

    def evidence(self, query: SemanticQuery) -> list[Evidence]:
        return self._store().evidence(query)

    def metric_by_name(self, name: str) -> Evidence | None:
        return self._store().metric_by_name(name)

    def aliases(self) -> dict[str, str]:
        if self._aliases is not None:
            return dict(self._aliases)
        return dict(glossary_aliases())

    def families(self) -> dict[str, list[str]]:
        rows, _version = load_relation_families(self._families_path)
        return {row.name: list(row.group) for row in rows}

    # ---------- 台账直读（每次查询现行行——零缓存层） ----------

    def _store(self) -> InMemoryKnowledgeStore:
        """直读现行行→快照→证据装配单点（行为与 fixture 读面共用同一实现）。"""
        return InMemoryKnowledgeStore(self._load_sync(), today=self._today)

    def _load_sync(self) -> LedgerSnapshot:
        return _run_sync(self._load())

    async def _load(self) -> LedgerSnapshot:
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                metric_rows = (
                    await session.execute(
                        select(*_SEM_METRIC.c).order_by(_SEM_METRIC.c.id)
                    )
                ).all()
                term_rows = (
                    await session.execute(
                        select(*_SEM_TERM.c).order_by(_SEM_TERM.c.id)
                    )
                ).all()
                object_rows = (
                    await session.execute(
                        select(*_SEM_OBJECT.c).order_by(_SEM_OBJECT.c.id)
                    )
                ).all()
                relation_rows = (
                    await session.execute(
                        select(*_SEM_RELATION.c).order_by(_SEM_RELATION.c.id)
                    )
                ).all()
        finally:
            await db.dispose()
        return self._snapshot(
            [dict(row._mapping) for row in metric_rows],
            [dict(row._mapping) for row in term_rows],
            [dict(row._mapping) for row in object_rows],
            [dict(row._mapping) for row in relation_rows],
        )

    def _snapshot(
        self,
        metric_rows: Sequence[Any],
        term_rows: Sequence[Any],
        object_rows: Sequence[Any],
        relation_rows: Sequence[Any],
    ) -> LedgerSnapshot:
        """驱动行 → 读面投影行（行值零改动——只做类型归一与读面列裁剪）。"""
        metrics = tuple(
            MetricRow(
                id=int(row["id"]),
                name=str(row["name"]),
                slot_name=str(row["slot_name"]),
                def_=str(row["def"]),
                grain=str(row["grain"]),
                unit=str(row["unit"]),
                status=tuple(str(s) for s in _json_list(row["status"])),
                dispute=str(row["dispute"]) if row["dispute"] is not None else None,
                version=int(row["version"]),
                calibers=_calibers(row["calibers"]),
                default_caliber=(
                    str(row["default_caliber"]) if row["default_caliber"] is not None else None
                ),
            )
            for row in metric_rows
        )
        terms = tuple(
            TermRow(
                id=int(row["id"]),
                term=str(row["term"]),
                type=str(row["type"]),
                def_=str(row["def"]),
                status=str(row["status"]),
                status_key=str(row["status_key"]),
                version=int(row["version"]),
                expires_at=_as_date(row["expires_at"]),
            )
            for row in term_rows
        )
        objects = tuple(
            ObjectRow(
                id=int(row["id"]),
                obj=str(row["obj"]),
                attr=str(row["attr"]) if row["attr"] is not None else None,
                status=str(row["status"]),
                version=int(row["version"]) if row["version"] is not None else None,
            )
            for row in object_rows
        )
        relations = tuple(
            RelationRow(id=int(row["id"]), rel=str(row["rel"]), read=str(row["read"]))
            for row in relation_rows
        )
        families, families_version = load_relation_families(self._families_path)
        return LedgerSnapshot(
            label=(
                "sem_* 直读（PG 现行行："
                f"{len(metrics)} 指标/{len(terms)} 术语/"
                f"{len(objects)} 对象/{len(relations)} 关系）"
            ),
            metrics=metrics,
            terms=terms,
            objects=objects,
            relations=relations,
            aliases=tuple(self.aliases().items()),
            families=families,
            families_version=families_version,
        )
