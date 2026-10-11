"""knowledge.pg_faq —— faq_* 常见问题库生产读面（V2-52 辅助模式——faq_lookup 取数件）。

faq_entry（faq-<n> 主键）＋faq_similar_question（相似问）两表只读投影——
specs 层面 faq_lookup 发现工具的取数件：serve 态条目的标准问/相似问归一精确
命中判定（V1 N18 match_index 语义的 V2 承载——确定性词面，零模型零向量）。

同步缝桥与 PgKnowledgeStore 同款（_run_sync：无运行环本线程直跑，有环专用
单线程池另起环）；逐调用直读现行行（零缓存层——specs/knowledge.md「不做
缓存层」同纪律）。表访问＝Core 轻声明（读模型不入 ORM Base.metadata）。
全程只读（INV-2）：readonly 会话守卫＋返回冻结 dataclass。

非 serve 态（draft/disabled/negative）不进命中集——禁用条目照台账纪律不消费。
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
from collections.abc import Coroutine, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from sqlalchemy import column, select, table

from appv2.infra.db import ConnectionManager, DatabaseSpec

_FAQ_ENTRY = table(
    "faq_entry",
    column("id"), column("question"), column("answer"), column("status"),
)
_FAQ_SIMILAR = table(
    "faq_similar_question",
    column("entry_id"), column("text"),
)

_FAQ_SERVE = "serve"

# 精确归一命中分（V2-52 附 B「score ≥ THRESHOLD」的确定性承载：命中即满分，
# 向量相似路未接线——阈下形态在读面不存在，阈值闸恒通过、语义随附 B 在案）。
FAQ_EXACT_SCORE = 1.0


def normalize_faq_question(text: str) -> str:
    """FAQ 精确匹配的问句归一单点（两表两列同尺；P-051b 审查①等效补齐）。

    归一口径等效 V1 faq normalize_text（app/domains/faq/domain.py 同构）：
    NFKC 全半角折叠＋casefold＋剥全部标点/空白（`[\\s\\W_]+` 整体剥除）——
    全角「Ｎ－０２井，？」与半角「N-02井?」同判（较窄归一升全）。
    """
    folded = unicodedata.normalize("NFKC", text or "").casefold()
    return re.sub(r"[\s\W_]+", "", folded, flags=re.UNICODE)


@dataclass(frozen=True, slots=True)
class FaqAuxHit:
    """FAQ 归一命中（faq_lookup 辅助材料的素材面——entry_id 可溯源）。"""

    entry_id: str
    question: str  # 标准问（辅助材料 content 的 Q 面）
    answer: str
    matched: str  # 命中的标准问/相似问原文（溯源面）
    score: float  # 精确归一命中＝FAQ_EXACT_SCORE（向量路未接线）
    disabled: bool  # serve 读面恒 False（禁用条目不返回——附 B 双保险消费面）


def _run_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """同步缝→异步 DB 桥（PgKnowledgeStore 同款——见其模块 docstring）。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


class PgFaqStore:
    """faq_* 直读读面（faq_lookup 发现工具的命中判定缝——similar 单公开方法）。"""

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._specs = tuple(specs)

    @classmethod
    def from_specs(cls, spec: DatabaseSpec) -> PgFaqStore:
        return cls([spec])

    def similar(self, question: str, top: int = 3) -> list[FaqAuxHit]:
        """问句→serve 条目归一精确命中列（top 上限；相似问先于标准问——
        V1 match_index 序，P-051 审查①等效补齐）。

        每次调用直读现行行（零缓存）——逐调用新建专用 ConnectionManager
        （池连接与当次环同源，PgKnowledgeStore 同纪律）。未命中＝空集如实。
        """
        return _run_sync(self._similar(question, top))

    async def _similar(self, question: str, top: int) -> list[FaqAuxHit]:
        db = ConnectionManager(self._specs)
        try:
            async with db.readonly() as session:
                entry_rows = (
                    await session.execute(
                        select(*_FAQ_ENTRY.c).where(
                            _FAQ_ENTRY.c.status == _FAQ_SERVE
                        )
                    )
                ).all()
                similar_rows = (
                    await session.execute(select(*_FAQ_SIMILAR.c))
                ).all()
        finally:
            await db.dispose()
        entries = {str(row.id): row for row in entry_rows}
        normalized = normalize_faq_question(question)
        if not normalized or top <= 0:
            return []
        hits: list[FaqAuxHit] = []
        seen: set[str] = set()
        # 相似问先于标准问（V1 service.match_index 判定序——优先级等效补齐）。
        for row in similar_rows:
            entry = entries.get(str(row.entry_id))
            if entry is None:
                continue
            if normalize_faq_question(str(row.text)) == normalized:
                hits.append(
                    FaqAuxHit(
                        entry_id=str(entry.id),
                        question=str(entry.question),
                        answer=str(entry.answer),
                        matched=str(row.text),
                        score=FAQ_EXACT_SCORE,
                        disabled=False,
                    )
                )
                seen.add(str(entry.id))
        for row in entry_rows:
            if str(row.id) in seen:
                continue  # 同条目标准问不重复（相似问优先序已收录）
            if normalize_faq_question(str(row.question)) == normalized:
                hits.append(
                    FaqAuxHit(
                        entry_id=str(row.id),
                        question=str(row.question),
                        answer=str(row.answer),
                        matched=str(row.question),
                        score=FAQ_EXACT_SCORE,
                        disabled=False,
                    )
                )
                seen.add(str(row.id))
        return hits[:top]
