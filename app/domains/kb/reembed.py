"""domains.kb.reembed —— kb 片段向量批量重嵌脚本（P1-11 迁移 0012 配套）。

背景：Alembic 0012 将 kb_fragment.embedding 列形 384→1536（embo-01 真维度）
并清空存量占位向量——本脚本重跑 embed 步补齐真向量（与入库管线 embed 步同
源：非父块片段、按当前版本文本、db 型语料向量）。

用法（运维入口，`app.domains.semantics.exporter` 同款 -m 惯例）：
    uv run python -m app.domains.kb.reembed            # 全量缺向量片段重嵌
    uv run python -m app.domains.kb.reembed --report rpt-xxxx   # 单报告范围

后端选型：默认真模型（config/models.yaml petro-embed＝MiniMax embo-01，
infra.llm_client.embeddings db 型）；KB_EMBED_BACKEND=local 环境变量切本地
确定性占位（测试/离线底座——非语义向量，只补列形不补语义）。

B6：供应商接触只在 infra.llm_client（本脚本经 RemoteEmbedder 视图消费）；
B14：时间只经 infra.clock。
"""

from __future__ import annotations

import argparse
import asyncio
import os

from app.domains.kb import domain as d
from app.domains.kb.store import FragmentRow, FragmentStore
from app.infra.config import load_database_specs
from app.infra.db import ConnectionManager
from app.infra.llm_client import LlmClient

# 单次向量化批量上限（embo-01 单文本 4096 token；16 片段/批的保守实施值）。
BATCH_SIZE = 16


def _backend() -> d.EmbeddingBackend:
    """重嵌后端（真模型默认；KB_EMBED_BACKEND=local 切本地占位——离线底座）。"""
    if os.environ.get("KB_EMBED_BACKEND") == "local":
        return d.LocalHashEmbedder()
    return d.RemoteEmbedder(LlmClient(), input_type="db")


async def reembed(
    report_id: str | None = None, *, manager: ConnectionManager | None = None
) -> int:
    """缺向量片段重嵌（embed 步同源：非父块＋当前版本文本＋db 型）→ 行数。

    manager 形参＝测试注桩缝（sqlite 底座）；缺省按 config/database.yaml 装配
    （运维入口直跑即真库）。
    """
    if manager is None:
        manager = ConnectionManager(load_database_specs())
        manager_owned = True
    else:
        manager_owned = False
    fragments = FragmentStore(manager)
    embedder = _backend()
    rows: list[FragmentRow] = [
        frag
        for frag in await fragments.list_children()
        if frag.embedding is None and not frag.is_parent_only
        and (report_id is None or frag.report_id == report_id)
    ]
    done = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        texts = [await _fragment_text(fragments, frag) for frag in batch]
        vectors = await embedder.embed(texts)
        await fragments.set_embeddings(
            list(zip((frag.id for frag in batch), vectors, strict=True))
        )
        done += len(batch)
    if manager_owned:
        await manager.dispose()
    return done


async def _fragment_text(fragments: FragmentStore, frag: FragmentRow) -> str:
    versions = await fragments.versions_of([frag.id])
    rows = versions.get(frag.id, [])
    return rows[-1].text if rows else ""


def main() -> None:
    parser = argparse.ArgumentParser(description="kb 片段向量批量重嵌（0012 配套）")
    parser.add_argument("--report", default=None, help="限定报告 id（缺省全量）")
    args = parser.parse_args()
    done = asyncio.run(reembed(args.report))
    print(f"reembed done: {done} fragments")


if __name__ == "__main__":
    main()
