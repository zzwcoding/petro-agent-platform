#!/usr/bin/env python3
"""kb 全库索引富化批入口（V2-47 R1b 切片富化——离线一次性全库富化）。

编排本体＝appv2.retrieval.enrich（enrich_index——切片重嵌＋节级摘要＋幂等
落库）；本脚本只是生产装配面：PG kb_* 语料（PgFragmentLibrary 读面——父块
不对外寻址）＋gateway complete 面（节级摘要——B6 唯一出口，逐笔落
gateway_spend_record，caller=agent_v2.retrieval.enrich）＋db 型重嵌
（RemoteEmbedder input_type="db"——MiniMax embo-01）。

用法（运维入口，V1 reembed 同惯例）：
    uv run python -m tools.v2_enrich_batch                 # 全库富化＋账本落盘
    uv run python -m tools.v2_enrich_batch --ledger PATH   # 自定账本路径

幂等（票面钉）：ensure 建表＋upsert 同键覆写——重跑零重复节点；kb_* 原表
零触碰（旧索引可重建不毁 fixture）。回滚路径：清空 kb_retrieval_enrich 即
回滚——检索自动回落原向量/原文（additive 单表，零业务数据损失）。

落位注记（R1 闭包闸）：本脚本在 tools/（仓级运维脚本位）而非 appv2/retrieval
——four_phase R1 闭包闸禁检索模块传递依赖 appv2.infra.gateway（模型判定通
道）；网关装配归本脚本，检索包内只留注入缝（enrich_index completer 形参）。

记账（票面「账本如实记账」）：complete 面逐笔账在 gateway_spend_record
（caller 归因——D5 账本唯一真源）；向量化面 token 由 RemoteEmbedder.usage_log
汇总；账本 JSON 落 eval/results/（批侧汇总面——complete 逐笔以网关账本为准）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

DEFAULT_LEDGER = "eval/results/P046-富化账本.json"


async def run_full_library_batch(
    *, specs: Sequence[Any] | None = None, ledger_path: str | None = None
) -> Any:
    """全库富化批（生产装配——V2-47 R1b 票面任务 3）。

    返回 EnrichLedger（账本数字面）；ledger_path 给定时落 JSON。
    """
    from appv2.infra.config import load_database_specs
    from appv2.infra.db import ConnectionManager
    from appv2.infra.gateway import GatewayService
    from appv2.infra.gateway.store import ensure_gateway_tables
    from appv2.infra.llm_client import LlmClient
    from appv2.retrieval import PgEnrichStore, enrich_index
    from appv2.retrieval.embedder import RemoteEmbedder
    from appv2.retrieval.pg_enrich import ensure_enrich_tables
    from appv2.retrieval.pg_source import PgFragmentLibrary

    resolved = tuple(specs) if specs is not None else tuple(load_database_specs())
    manager = ConnectionManager(resolved)
    try:
        await ensure_enrich_tables(manager.engine())
        await ensure_gateway_tables(manager.engine())
        corpus = await PgFragmentLibrary(resolved).fragments()
        gateway = GatewayService(manager, LlmClient())
        store = PgEnrichStore(resolved)
        ledger = await enrich_index(
            corpus=corpus,
            store=store,
            completer=gateway,
            embedder=RemoteEmbedder(LlmClient(), input_type="db"),
        )
    finally:
        await manager.dispose()
    if ledger_path:
        from appv2.infra.clock import now

        _write_ledger_json(ledger, ledger_path, now().isoformat(timespec="seconds"))
    return ledger


def _write_ledger_json(ledger: Any, path: str, at: str) -> None:
    """账本落盘（JSON——批次数字面；complete 面逐笔账以网关账本为准）。"""
    payload = {
        "ticket": "P-046 / V2-47 R1b 切片富化",
        "finished_at": at,
        "corpus_total": ledger.corpus_total,
        "corpus_embedded": ledger.corpus_embedded,
        "overlay_written": ledger.overlay_written,
        "clusters_total": ledger.clusters_total,
        "clusters_single_cover": ledger.clusters_single_cover,
        "summaries_written": ledger.summaries_written,
        "summaries_failed": list(ledger.summaries_failed),
        "complete_calls": ledger.complete_calls,
        "embedding_calls": ledger.embedding_calls,
        "embedding_tokens": ledger.embedding_tokens,
        "summary_rule": (
            "cover_count≥2 才生成节级摘要（P-046 中途审查 consider 1 采纳——"
            "单成员簇不生成；陈旧摘要行由 prune_summaries 清理）"
        ),
        "complete_ledger": (
            "gateway_spend_record WHERE caller='agent_v2.retrieval.enrich'"
        ),
        "rollback": (
            "清空 kb_retrieval_enrich 即回滚——kb_* 原表零触碰，检索回落原向量"
        ),
    }
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="kb 全库索引富化批（V2-47 R1b）")
    parser.add_argument(
        "--ledger",
        default=DEFAULT_LEDGER,
        help="账本 JSON 落盘路径（缺省 eval/results/）",
    )
    args = parser.parse_args()
    ledger = asyncio.run(run_full_library_batch(ledger_path=args.ledger))
    print(
        "enrich done: "
        f"corpus={ledger.corpus_total} embedded={ledger.corpus_embedded} "
        f"clusters={ledger.clusters_total} summaries={ledger.summaries_written} "
        f"failed={len(ledger.summaries_failed)} "
        f"embed_calls={ledger.embedding_calls} embed_tokens={ledger.embedding_tokens}"
    )


if __name__ == "__main__":
    main()
