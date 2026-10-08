"""V2-19 retrieval 生产读面——PgFragmentLibrary 行为测试（specs/modules.md
retrieval 卡外部依赖「PG kb_* 表」的落位件验收）。

装配：sqlite 测试底座手建 kb_* 四表（kb_library/kb_report/kb_fragment/
kb_fragment_version——DDL 投影读面消费列；pgvector 向量列 sqlite 侧由
with_variant(JSON) 承载，文本形与 V1 PgVectorType bind 产物一致＝
"[0.1,0.2]" JSON 数组）。行值＝测试自建量级样本（业务事实零发明——行值只
服务断言，不注源为业务数字；test_chat_query_store_pg 同款纪律）。

覆盖：
- fragments() 出处链三级（fragment→report→library）＋family（biz_template
  透传）＋section＋最新版全文（kb_fragment_version max(v)——修正版胜出）；
- 父块不对外寻址（is_parent_only 行不进语料——F30）；
- embedding：有向量行解析 list[float]、无向量行 None（向量腿跳过语义）；
- 只读（INV-2）：两次调用返回独立副本、行对象不可变投影。
"""

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.retrieval import PgFragmentLibrary

EMBEDDING = [0.1, -0.2, 0.3]


def _spec(main_db: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(main_db), user="", password="", pool_size=2, max_overflow=1,
    )


_KB_DDL = (
    """CREATE TABLE kb_library (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, biz_template TEXT NOT NULL,
        status TEXT NOT NULL)""",
    """CREATE TABLE kb_report (
        id TEXT PRIMARY KEY, lib_id TEXT NOT NULL, doc TEXT NOT NULL)""",
    """CREATE TABLE kb_fragment (
        id TEXT PRIMARY KEY, report_id TEXT NOT NULL, section TEXT,
        is_parent_only INTEGER NOT NULL, embedding TEXT)""",
    """CREATE TABLE kb_fragment_version (
        fragment_id TEXT NOT NULL, v INTEGER NOT NULL, text TEXT NOT NULL,
        PRIMARY KEY (fragment_id, v))""",
)

_SEED = (
    "INSERT INTO kb_library VALUES ('lib-1', '完井报告类', 'completion', 'active')",
    "INSERT INTO kb_report VALUES ('rpt-1', 'lib-1', '《A-W11井完井工程报告》')",
    # f1：有向量＋两版（v2 修正版胜出）；f2：无向量单版；f3：父块（不对外寻址）。
    "INSERT INTO kb_fragment VALUES ('f1', 'rpt-1', '章节 03 射孔设计', 0, "
    "'" + json.dumps(EMBEDDING) + "')",
    "INSERT INTO kb_fragment VALUES ('f2', 'rpt-1', '正文', 0, NULL)",
    "INSERT INTO kb_fragment VALUES ('f3', 'rpt-1', NULL, 1, NULL)",
    "INSERT INTO kb_fragment_version VALUES ('f1', 1, 'v1 原文：射孔井段 2850-2910m')",
    "INSERT INTO kb_fragment_version VALUES ('f1', 2, 'v2 修正：射孔井段 2850.0-2910.5m')",
    "INSERT INTO kb_fragment_version VALUES ('f2', 1, '防砂方式：筛管完井')",
)


@pytest.fixture
async def library(tmp_path: Path) -> PgFragmentLibrary:
    db = ConnectionManager([_spec(tmp_path / "kb.db")])
    try:
        async with db.session() as session:
            for ddl in _KB_DDL:
                await session.execute(text(ddl))
            for row in _SEED:
                await session.execute(text(row))
        yield PgFragmentLibrary([_spec(tmp_path / "kb.db")])
    finally:
        await db.dispose()


async def test_fragments_provenance_chain(library: PgFragmentLibrary) -> None:
    """出处链三级＋family 透传＋最新版全文——FragmentRecord 逐字段断言。"""
    fragments = {f.fragment_id: f for f in await library.fragments()}
    assert set(fragments) == {"f1", "f2"}  # 父块 f3 不对外寻址（F30）
    f1 = fragments["f1"]
    assert f1.report_id == "rpt-1"
    assert f1.report == "《A-W11井完井工程报告》"
    assert f1.library_id == "lib-1"
    assert f1.library == "完井报告类"
    assert f1.family == "completion"
    assert f1.section == "章节 03 射孔设计"
    assert f1.text == "v2 修正：射孔井段 2850.0-2910.5m"  # max(v) 修正版胜出
    f2 = fragments["f2"]
    assert f2.text == "防砂方式：筛管完井"
    assert f2.embedding is None  # 未入向量索引——向量腿跳过（关键词腿兜底）


async def test_embedding_parsed_as_floats(library: PgFragmentLibrary) -> None:
    """有向量行：embedding 解析 list[float]（维度保真）。"""
    fragments = {f.fragment_id: f for f in await library.fragments()}
    assert fragments["f1"].embedding == EMBEDDING
    assert all(isinstance(x, float) for x in fragments["f1"].embedding or [])


async def test_inv2_fresh_copy(library: PgFragmentLibrary) -> None:
    """只读：两次调用独立副本——改返回列不落库（INV-2）。"""
    first = await library.fragments()
    first.append(first[0])  # 污染返回列
    second = await library.fragments()
    assert len(second) == 2
    assert [f.fragment_id for f in second] == ["f1", "f2"]
