"""retrieval.pg_enrich —— 富化索引表存储适配器（V2-47 R1b——EnrichStore 生产缝）。

表＝kb_retrieval_enrich（V2 检索域自有 additive 表——kb_* 原表零触碰，旧索
引可重建不毁 fixture；回滚＝清空本表即回落原向量/原文）。行两类：
- kind='slice_embed'：切片富化向量（key=fragment_id——索引文本〔前缀＋原文〕
  的 db 型重嵌，覆盖原向量的索引面；embedding 列即富化向量）；
- kind='section_summary'：节级摘要节点（key=确定性 node_id——summary_node_id；
  节路径＋覆盖要点＋出处链三级＋族随行——读面自足，EnrichedFragmentLibrary
  零二次拼装）。

幂等（票面钉）：upsert＝同事务「删同键→插新行」——同键重跑零重复节点；
确定性身份（summary_node_id）保证跨批同键。双建轨（P0-08 先例）：本模块
ensure_enrich_tables（应用/批侧幂等建表）＋Alembic 0023（迁移轴同形 DDL）。

向量列＝pgvector `vector(1536)`（与 kb_fragment.embedding 同维——embo-01；
sqlite 测试底座 with_variant(JSON) 承载向量文本）。表访问＝Core 轻声明
（pg_source 同款——独立 MetaData 不入 ORM Base.metadata）；会话唯一经
infra.db（B3）；时间只经 infra.clock（B14）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    delete,
    func,
    insert,
    select,
    tuple_,
)
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.types import JSON, UserDefinedType

from appv2.infra.clock import now
from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.retrieval.embedder import EMBED_DIM
from appv2.retrieval.enrich import EnrichStore, SliceOverlay, SummaryNode

KIND_SLICE_EMBED = "slice_embed"
KIND_SECTION_SUMMARY = "section_summary"

_UPSERT_CHUNK = 64  # 删插分批（单事务内分片——参数量护栏）


class _PgVector(UserDefinedType[None]):
    """pgvector 向量列类型（bind＝"[...]" 文本、result 侧解析——kb 同款双面）。"""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return f"vector({EMBED_DIM})"

    def bind_processor(self, dialect: Any):  # type: ignore[no-untyped-def]
        def process(value: Any) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{float(v):.6f}" for v in value) + "]"

        return process

    def result_processor(self, dialect: Any, coltype: Any):  # type: ignore[no-untyped-def]
        def process(value: Any) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return [float(x) for x in value]
            body = str(value).strip().strip("[]")
            return [float(x) for x in body.split(",")] if body else []

        return process


_ENRICH_META = MetaData()

_KB_RETRIEVAL_ENRICH = Table(
    "kb_retrieval_enrich",
    _ENRICH_META,
    Column("kind", String(16), primary_key=True),  # slice_embed | section_summary
    Column("key", String(64), primary_key=True),  # fragment_id | node_id
    Column("report_id", String(32), nullable=False),
    Column("report", Text, nullable=False),
    Column("library_id", String(32), nullable=False),
    Column("library", Text, nullable=False),
    Column("family", String(16), nullable=False),
    Column("section", Text),
    Column("node_text", Text),
    Column("cover_count", Integer),
    Column("source_ids", Text),  # JSON 数组文本（摘要节点成员切片 id）
    Column("embedding", _PgVector().with_variant(JSON(), "sqlite"), nullable=False),
    Column("model", String(64), nullable=False),
    Column("enriched_at", Text, nullable=False),
)


async def ensure_enrich_tables(engine: AsyncEngine) -> None:
    """幂等建表（批入口与 lifespan 消费——与 Alembic 0023 双轨同形并存）。"""
    async with engine.begin() as conn:
        await conn.run_sync(_KB_RETRIEVAL_ENRICH.create, checkfirst=True)


class PgEnrichStore(EnrichStore):
    """富化索引表存储（生产适配器——EnrichStore 缝原形；additive 单表读写）。"""

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._specs = tuple(specs)

    async def snapshot(self) -> tuple[dict[str, list[float]], list[SummaryNode]]:
        """富化快照（切片 overlay 映射＋摘要节点列——只读副本语义）。"""
        stmt = select(
            _KB_RETRIEVAL_ENRICH.c.kind,
            _KB_RETRIEVAL_ENRICH.c.key,
            _KB_RETRIEVAL_ENRICH.c.report_id,
            _KB_RETRIEVAL_ENRICH.c.report,
            _KB_RETRIEVAL_ENRICH.c.library_id,
            _KB_RETRIEVAL_ENRICH.c.library,
            _KB_RETRIEVAL_ENRICH.c.family,
            _KB_RETRIEVAL_ENRICH.c.section,
            _KB_RETRIEVAL_ENRICH.c.node_text,
            _KB_RETRIEVAL_ENRICH.c.cover_count,
            _KB_RETRIEVAL_ENRICH.c.source_ids,
            _KB_RETRIEVAL_ENRICH.c.embedding,
            _KB_RETRIEVAL_ENRICH.c.model,
        ).order_by(_KB_RETRIEVAL_ENRICH.c.key)
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                rows = (await session.execute(stmt)).all()
        finally:
            await db.dispose()
        overlays: dict[str, list[float]] = {}
        nodes: list[SummaryNode] = []
        for row in rows:
            vector = _as_vector(row.embedding)
            if row.kind == KIND_SLICE_EMBED:
                if vector is not None:
                    overlays[str(row.key)] = vector
                continue
            nodes.append(
                SummaryNode(
                    node_id=str(row.key),
                    report_id=str(row.report_id),
                    report=str(row.report),
                    library_id=str(row.library_id),
                    library=str(row.library),
                    family=str(row.family),
                    section=str(row.section) if row.section is not None else "",
                    text=str(row.node_text) if row.node_text is not None else "",
                    cover_count=int(row.cover_count or 0),
                    source_ids=_as_source_ids(row.source_ids),
                    embedding=vector,
                    model=str(row.model),
                )
            )
        return overlays, nodes

    async def version(self) -> str:
        """富化库变更令牌（S1 读面缓存判据——标量行零向量列，远廉于 snapshot）。

        令牌＝行数＋enriched_at 最大戳（upsert 整批同戳、删行变行数——离线批
        变更两形全覆盖；同秒内覆写且行数不变的极端形按离线批节奏不可达）。
        """
        stmt = select(
            func.count(_KB_RETRIEVAL_ENRICH.c.key),
            func.max(_KB_RETRIEVAL_ENRICH.c.enriched_at),
        )
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                count, stamp = (await session.execute(stmt)).one()
        finally:
            await db.dispose()
        return f"{int(count or 0)}:{stamp or ''}"

    async def prune_summaries(self, keep_node_ids: set[str]) -> int:
        """删除 keep 集外摘要节点行（规则变更重跑的陈旧清理——终态幂等半边）。"""
        keep = {str(key) for key in keep_node_ids}
        stmt = delete(_KB_RETRIEVAL_ENRICH).where(
            _KB_RETRIEVAL_ENRICH.c.kind == KIND_SECTION_SUMMARY
        )
        if keep:
            stmt = stmt.where(_KB_RETRIEVAL_ENRICH.c.key.not_in(keep))
        db = ConnectionManager(self._specs)
        try:
            async with db.session() as session:
                result = cast(CursorResult[Any], await session.execute(stmt))
        finally:
            await db.dispose()
        return int(result.rowcount or 0)

    async def upsert(
        self, overlays: Sequence[SliceOverlay], summaries: Sequence[SummaryNode]
    ) -> int:
        """幂等写入（同事务删同键→插新行——重跑零重复；返回写入行数）。"""
        if not overlays and not summaries:
            return 0
        stamp = now().isoformat(timespec="seconds")
        rows: list[dict[str, Any]] = [
            {
                "kind": KIND_SLICE_EMBED,
                "key": overlay.fragment_id,
                "report_id": "",
                "report": "",
                "library_id": "",
                "library": "",
                "family": "",
                "section": None,
                "node_text": None,
                "cover_count": None,
                "source_ids": None,
                "embedding": list(overlay.embedding),
                "model": overlay.model,
                "enriched_at": stamp,
            }
            for overlay in overlays
        ]
        rows.extend(
            {
                "kind": KIND_SECTION_SUMMARY,
                "key": node.node_id,
                "report_id": node.report_id,
                "report": node.report,
                "library_id": node.library_id,
                "library": node.library,
                "family": node.family,
                "section": node.section,
                "node_text": node.text,
                "cover_count": node.cover_count,
                "source_ids": json.dumps(list(node.source_ids), ensure_ascii=False),
                "embedding": list(node.embedding) if node.embedding is not None else [],
                "model": node.model,
                "enriched_at": stamp,
            }
            for node in summaries
        )
        db = ConnectionManager(self._specs)
        try:
            async with db.session() as session:
                for start in range(0, len(rows), _UPSERT_CHUNK):
                    chunk = rows[start : start + _UPSERT_CHUNK]
                    keys = [(row["kind"], row["key"]) for row in chunk]
                    await session.execute(
                        _KB_RETRIEVAL_ENRICH.delete().where(
                            tuple_(
                                _KB_RETRIEVAL_ENRICH.c.kind, _KB_RETRIEVAL_ENRICH.c.key
                            ).in_(keys)
                        )
                    )
                    await session.execute(insert(_KB_RETRIEVAL_ENRICH), chunk)
        finally:
            await db.dispose()
        return len(rows)


def _as_vector(value: Any) -> list[float] | None:
    """embedding 列值→向量（result_processor 已解析双形兜底；空表 None）。"""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [float(x) for x in value]
    body = str(value).strip().strip("[]")
    return [float(x) for x in body.split(",")] if body else None


def _as_source_ids(value: Any) -> tuple[str, ...]:
    """source_ids JSON 文本→元组（空/坏值如实空元组——不炸读面）。"""
    if not value:
        return ()
    try:
        parsed = json.loads(str(value))
    except Exception:
        return ()
    return tuple(str(item) for item in parsed) if isinstance(parsed, list) else ()
