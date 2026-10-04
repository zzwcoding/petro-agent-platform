"""wiki 表族 PG 集成测试——99 §2.7 逐字段落位与 CHECK/uq/FK 真库断言。

约定同 kb/semantics PG 组（TEST_DATABASE_URL 未配置即 skip；测试自动改用
<库名>_test 独立库）。
"""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.domains.derivatives.store import ensure_derivatives_tables
from app.infra.db import ConnectionManager, DatabaseSpec

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")

_TABLES = ("wiki_page", "wiki_page_version")


def _isolated_url() -> URL:
    url = make_url(TEST_DATABASE_URL)
    return url.set(database=f"{url.database}_test")


async def _ensure_test_database(url: URL) -> None:
    admin = create_async_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as conn:
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": url.database},
                )
            ).scalar()
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await admin.dispose()


def _spec(url: URL) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary",
        role="primary",
        driver=url.drivername.split("+", 1)[0],
        host=url.host or "localhost",
        port=url.port or 5433,
        database=url.database or "",
        user=url.username or "",
        password=url.password or "",
        pool_size=2,
        max_overflow=1,
    )


@pytest.fixture
async def db() -> AsyncIterator[ConnectionManager]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL 未配置——PG 集成测试跳过（约定见票面）")
    url = _isolated_url()
    await _ensure_test_database(url)
    manager = ConnectionManager([_spec(url)])
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        for table in _TABLES:
            await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        # wiki 表族 FK 依赖 kb_library/kb_report——宿主表缺则补最小壳
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS kb_library ("
                " id varchar(32) PRIMARY KEY, name text NOT NULL,"
                " biz_template varchar(16) NOT NULL, status varchar(16) NOT NULL,"
                " created_at timestamp NOT NULL, updated_at timestamp NOT NULL)"
            )
        )
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS kb_report ("
                " id varchar(32) PRIMARY KEY, lib_id varchar(32) NOT NULL"
                " REFERENCES kb_library(id), doc text NOT NULL, subject text,"
                " status varchar(8) NOT NULL, related_objects jsonb NOT NULL,"
                " object_key text NOT NULL, wiki_current_version integer,"
                " created_at timestamp NOT NULL, updated_at timestamp NOT NULL)"
            )
        )
    await ensure_derivatives_tables(engine)
    await engine.dispose()
    yield manager
    await manager.dispose()


async def _columns(db: ConnectionManager, table: str) -> set[str]:
    async with db.session() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = :t"
                ),
                {"t": table},
            )
        ).scalars().all()
    return set(rows)


async def test_wiki_tables_columns_match_99(db: ConnectionManager) -> None:
    """wiki 族逐列断言（99 §2.7 基线＋B4 v0.4 页级覆盖三列；版本表随表留档）。"""
    expected = {
        "wiki_page": {
            "id", "title", "digest", "lib_id", "source_report_id",
            "current_version", "content", "claims", "glossary_terms",
            "created_at", "updated_at",
        },
        "wiki_page_version": {
            "page_id", "v", "content", "claims", "glossary_terms",
            "source", "desc", "operator", "task_no",
            "created_at", "updated_at",
        },
    }
    for table, columns in expected.items():
        actual = await _columns(db, table)
        missing = columns - actual
        assert not missing, f"{table} 缺列: {missing}"


async def test_wiki_constraints_and_roundtrip(db: ConnectionManager) -> None:
    """source CHECK 四态（F52 ①冻结值）/uq 1:1/PK(page_id,v)/往返。

    v0.4 注记：wiki_page_version 写路径已撤（B4 v0.4 覆盖语义——重建不再
    追加版本行），本组断言＝保留表的列形/CHECK 结构留档验证（表不删、
    历史行只读）；wiki_page 页级 content/claims/glossary_terms 覆盖往返同验。
    """
    async with db.session() as session:
        checks = (
            await session.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE contype = 'c' AND conrelid = 'wiki_page_version'::regclass"
                )
            )
        ).scalars().all()
        uniques = (
            await session.execute(
                text(
                    "SELECT conname, contype FROM pg_constraint "
                    "WHERE conrelid = 'wiki_page'::regclass"
                )
            )
        ).all()
        pks = (
            await session.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE contype = 'p' AND conrelid = 'wiki_page_version'::regclass"
                )
            )
        ).scalars().all()
    assert "ck_wiki_page_version_source" in checks
    # 1:1 报告＝source_report_id 唯一约束
    assert any(
        name.startswith("wiki_page_source_report_id_key")
        and (typ.decode() if isinstance(typ, bytes) else typ) == "u"
        for name, typ in uniques
    )
    assert any("page_id" in (d or "") and (", v" in (d or "")) for d in pks)
    # 往返（ORM——含 `desc` 保留字列的正确引号处理）：append-only 双版本＋jsonb 真库读写
    from datetime import datetime

    from sqlalchemy import select

    from app.domains.derivatives.store import WikiPageRow, WikiPageVersionRow
    from app.domains.kb.store import LibraryRow, ReportRow
    from app.infra.clock import now as clock_now

    async with db.session() as session:
        if (await session.execute(
            text("SELECT id FROM kb_library WHERE id = 'lib-t'")
        )).scalar() is None:
            session.add(LibraryRow(
                id="lib-t", name="完井报告库", biz_template="completion",
                status="active", created_at=clock_now(), updated_at=clock_now(),
            ))
            await session.flush()
        if (await session.execute(
            text("SELECT id FROM kb_report WHERE id = 'rpt-t'")
        )).scalar() is None:
            session.add(ReportRow(
                id="rpt-t", lib_id="lib-t", doc="《报告》", status="已入库",
                related_objects=[], object_key="k",
                created_at=clock_now(), updated_at=clock_now(),
            ))
            await session.flush()
        page = WikiPageRow(
            id="wiki-t", title="《报告》", digest="摘要", lib_id="lib-t",
            source_report_id="rpt-t", current_version=2,
            content="正文 v2（页级当前版——B4 v0.4 覆盖语义）",
            claims=[{"claim_id": "c9", "text": "页级论断",
                     "evidence_chunk_ids": ["f1"]}],
            glossary_terms=[],
            created_at=datetime.now(), updated_at=clock_now(),
        )
        session.add(page)
        await session.flush()
        session.add(WikiPageVersionRow(
            page_id="wiki-t", v=1, content="正文 v1\n[[claim:f1]]",
            claims=[{"claim_id": "c1", "text": "论断",
                     "evidence_chunk_ids": ["f1"]}],
            glossary_terms=[{"word": "综合含水率", "kind": "metric",
                             "ref_id": 5, "card": {}}],
            source="自动重建", desc="首次生成（报告入库自动建页）",
            operator="系统（入库管线）", task_no="task-t",
        ))
        await session.flush()
        session.add(WikiPageVersionRow(
            page_id="wiki-t", v=2, content="正文 v2", claims=[], glossary_terms=[],
            source="回滚", desc="回滚：恢复到 v1",
            operator="xiaoli · 地质/质检", task_no=None,
        ))
        await session.flush()
    async with db.readonly() as session:
        row = await session.get(WikiPageRow, "wiki-t")
        assert row is not None and row.current_version == 2
        assert row.content.startswith("正文 v2")  # 页级当前版往返
        assert row.claims[0]["text"] == "页级论断"  # jsonb 真库读写
        rows = (
            (await session.execute(
                select(WikiPageVersionRow)
                .where(WikiPageVersionRow.page_id == "wiki-t")
                .order_by(WikiPageVersionRow.v)
            )).scalars().all()
        )
    assert len(rows) == 2  # 保留表留档行往返（v0.4 起写路径不再追加）
    assert rows[0].source == "自动重建"
    assert rows[0].claims[0]["evidence_chunk_ids"] == ["f1"]
    assert rows[0].glossary_terms[0]["word"] == "综合含水率"
    assert rows[1].source == "回滚" and rows[1].task_no is None  # 留档列形
    # source CHECK：合同四态之外的值被拒（F52 ①值域冻结——随表留档仍生效）
    from sqlalchemy.exc import IntegrityError

    async with db.session() as session:
        session.add(WikiPageVersionRow(
            page_id="wiki-t", v=3, content="x", claims=[], glossary_terms=[],
            source="首次生成", desc="x",  # 「首次生成」是 desc 文案不是来源态
        ))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()  # 会话回滚复位（CHECK 拦截已验证）
