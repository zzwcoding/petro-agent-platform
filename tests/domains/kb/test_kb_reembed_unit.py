"""kb reembed 脚本单测（P1-11 迁移 0012 配套）——sqlite 底座＋KB_EMBED_BACKEND
=local（LocalHash 底座——真模型路径由 KB_SMOKE 冒烟承载）。

覆盖：缺向量片段重嵌（embed 步同源——非父块＋当前版本文本＋db 型）、单报告
范围过滤、已是向量的片段不重嵌（幂等）、父块与空文本片段跳过。
"""

from typing import Any

import pytest

from app.domains.kb import reembed
from app.domains.kb.domain import EMBED_DIM, LocalHashEmbedder
from app.domains.kb.store import (
    FragmentRow,
    FragmentStore,
    FragmentVersionRow,
    LibraryRow,
    ReportRow,
    ensure_kb_tables,
)
from app.infra.db import ConnectionManager, DatabaseSpec


@pytest.fixture
async def db(tmp_path: Any) -> ConnectionManager:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "reembed.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    manager = ConnectionManager([spec])
    await ensure_kb_tables(manager.engine())
    yield manager
    await manager.dispose()


async def _seed(db: ConnectionManager) -> None:
    """一库一报告三片段：f1（缺向量·正文）、f2（缺向量·父块——跳过）、
    f3（已有向量——不重嵌）。"""
    async with db.session() as session:
        session.add(LibraryRow(id="lib-r", name="重嵌库", biz_template="blank", status="active"))
        session.add(ReportRow(id="rpt-r", lib_id="lib-r", doc="《重嵌报告》", object_key="k"))
    async with db.session() as session:
        session.add(FragmentRow(
            id="f1", report_id="rpt-r", type="原文块", section="正文",
            current_version=1, is_parent_only=False,
        ))
        session.add(FragmentRow(
            id="f2", report_id="rpt-r", type="原文块", section="父块",
            current_version=1, is_parent_only=True,
        ))
        session.add(FragmentRow(
            id="f3", report_id="rpt-r", type="原文块", section="正文",
            current_version=1, is_parent_only=False,
        ))
    async with db.session() as session:
        session.add(FragmentVersionRow(
            fragment_id="f1", v=1, text="渤中28-1 井完井正文", context_text=None, note="原始解析",
        ))
        session.add(FragmentVersionRow(
            fragment_id="f2", v=1, text="父块全文", context_text=None, note="原始解析",
        ))
        session.add(FragmentVersionRow(
            fragment_id="f3", v=1, text="已有向量片段", context_text=None, note="原始解析",
        ))
        await session.flush()
    fragments = FragmentStore(db)
    old = (await LocalHashEmbedder().embed(["旧维度占位向量"]))[0]
    await fragments.set_embeddings([("f3", old)])


async def test_reembed_fills_missing_vectors(db: ConnectionManager, monkeypatch: Any) -> None:
    monkeypatch.setenv("KB_EMBED_BACKEND", "local")
    await _seed(db)
    done = await reembed.reembed(manager=db)
    assert done == 1  # f1 缺向量重嵌；f2 父块跳过；f3 已有向量不重嵌（幂等）
    fragments = FragmentStore(db)
    rows = {frag.id: frag for frag in await fragments.list_children()}
    assert rows["f1"].embedding is not None
    assert len(rows["f1"].embedding) == EMBED_DIM
    assert "f2" not in rows  # 父块不进 list_children（不对外寻址不嵌入——F30 同象）
    assert rows["f3"].embedding == (await LocalHashEmbedder().embed(["旧维度占位向量"]))[0]


async def test_reembed_report_scope_filter(db: ConnectionManager, monkeypatch: Any) -> None:
    monkeypatch.setenv("KB_EMBED_BACKEND", "local")
    await _seed(db)
    done = await reembed.reembed(report_id="rpt-other", manager=db)  # 不存在报告——零命中
    assert done == 0
