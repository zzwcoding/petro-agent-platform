"""retrieval.pg_source —— PgFragmentLibrary（kb_* 台账生产读面——V2-19，
specs/modules.md retrieval 卡外部依赖「PG kb_* 表」的落位件）。

specs/modules.md retrieval 卡「Seam: RetrievalEngine / embedder；Adapter:
fixture 片段库」——生产装配＝PG kb_* 只读读面（source.py seam docstring 自述
落点）。每次 fragments() 直读 kb_* 现行行（逐调用新建专用会话管理器——本面
为异步缝（FragmentLibrary.fragments async），运行环内直用；专用管理器随调用
建/拆保证池连接与当次环同源），零跨调用缓存；会话获取唯一经 infra.db（B3），
readonly() 只读守卫恒挂（INV-2）。

行形状＝FragmentRecord（domain.py 运行时投影——出处链三级 fragment→report→
library＋family＝kb_library.biz_template 透传）；全文＝kb_fragment_version
最新版（max(v)——人工修正版胜出，V1 report_detail 同口径）；父块不对外寻址
（is_parent_only 行不进语料——F30）；embedding 未入库行 None（向量腿跳过、
关键词腿兜底——specs/retrieval.md 行为约定 5）。

向量列＝pgvector `vector(1536)`（Alembic 0003/0012——DDL 真源）；本文件只读
不写——_PgVector 仅带 result_processor（"[0.1,0.2]" 文本解析，V1 PgVectorType
同款），sqlite 测试底座由 with_variant(JSON) 承载（bind 形态一致＝JSON 数组
文本）。表访问＝Core 轻声明（独立 MetaData——台账 owner 侧归 V1 kb 域与其
迁移链，读模型不入 ORM Base.metadata）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    func,
    select,
)
from sqlalchemy.types import JSON, UserDefinedType

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.retrieval.domain import FragmentRecord
from appv2.retrieval.embedder import EMBED_DIM
from appv2.retrieval.source import FragmentLibrary


class _PgVector(UserDefinedType[None]):
    """pgvector 向量列只读类型（result 侧 "[...]" 文本解析——V1 同款；不写向量）。"""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return f"vector({EMBED_DIM})"

    def result_processor(self, dialect: Any, coltype: Any):  # type: ignore[no-untyped-def]
        def process(value: Any) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, (list, tuple)):
                return [float(x) for x in value]
            body = str(value).strip().strip("[]")
            return [float(x) for x in body.split(",")] if body else []

        return process


# ---------- kb_* 四表轻声明（DDL 真源＝Alembic 0003——读面消费列投影） ----------

_KB_META = MetaData()

_KB_LIBRARY = Table(
    "kb_library", _KB_META,
    Column("id", String(32)),
    Column("name", Text),
    Column("biz_template", String(16)),
    Column("status", String(16)),
)
_KB_REPORT = Table(
    "kb_report", _KB_META,
    Column("id", String(32)),
    Column("lib_id", String(32)),
    Column("doc", Text),
)
_KB_FRAGMENT = Table(
    "kb_fragment", _KB_META,
    Column("id", String(32)),
    Column("report_id", String(32)),
    Column("section", Text),
    Column("is_parent_only", Boolean),
    Column("embedding", _PgVector().with_variant(JSON(), "sqlite")),
)
_KB_FRAGMENT_VERSION = Table(
    "kb_fragment_version", _KB_META,
    Column("fragment_id", String(32)),
    Column("v", Integer),
    Column("text", Text),
)


class PgFragmentLibrary(FragmentLibrary):
    """kb_* 台账直读片段库（生产适配器——fragments()＝FragmentLibrary seam 原形）。"""

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._specs = tuple(specs)

    async def fragments(self) -> list[FragmentRecord]:
        """子块片段全集（出处链三级＋最新版全文＋向量列随行；零写路径）。"""
        latest_v = (
            select(func.max(_KB_FRAGMENT_VERSION.c.v))
            .where(_KB_FRAGMENT_VERSION.c.fragment_id == _KB_FRAGMENT.c.id)
            # 相关子查询——显式锚外层片段行（禁 auto-correlation 抽走 FROM）。
            .correlate(_KB_FRAGMENT)
            .scalar_subquery()
        )
        stmt = (
            select(
                _KB_FRAGMENT.c.id.label("fragment_id"),
                _KB_FRAGMENT.c.report_id,
                _KB_REPORT.c.doc.label("report"),
                _KB_FRAGMENT.c.section,
                _KB_LIBRARY.c.id.label("library_id"),
                _KB_LIBRARY.c.name.label("library"),
                _KB_LIBRARY.c.biz_template.label("family"),
                _KB_FRAGMENT_VERSION.c.text,
                _KB_FRAGMENT.c.embedding,
            )
            .join(_KB_REPORT, _KB_REPORT.c.id == _KB_FRAGMENT.c.report_id)
            .join(_KB_LIBRARY, _KB_LIBRARY.c.id == _KB_REPORT.c.lib_id)
            .join(
                _KB_FRAGMENT_VERSION,
                and_(
                    _KB_FRAGMENT_VERSION.c.fragment_id == _KB_FRAGMENT.c.id,
                    _KB_FRAGMENT_VERSION.c.v == latest_v,
                ),
            )
            .where(_KB_FRAGMENT.c.is_parent_only == False)  # noqa: E712 - 父块不对外寻址（F30）
            .order_by(_KB_FRAGMENT.c.id)
        )
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                rows = (await session.execute(stmt)).all()
        finally:
            await db.dispose()
        return [
            FragmentRecord(
                fragment_id=str(row.fragment_id),
                report_id=str(row.report_id),
                report=str(row.report),
                section=str(row.section) if row.section is not None else None,
                library_id=str(row.library_id),
                library=str(row.library),
                family=str(row.family),
                text=str(row.text),
                embedding=list(row.embedding) if row.embedding is not None else None,
            )
            for row in rows
        ]
