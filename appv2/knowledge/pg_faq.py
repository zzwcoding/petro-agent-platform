"""knowledge.pg_faq —— faq_* 常见问题库生产读面（V2-52 五站迁移批·FAQ 直出链）。

faq_entry（faq-<n> 主键）＋faq_similar_question（相似问）两表只读投影——
specs 层面 FAQ 直出链的取数件：serve 态条目的标准问/相似问**精确命中**判定
（V1 N18 match_index 语义的 V2 承载——确定性词面，零模型零向量）。

同步缝桥与 PgKnowledgeStore 同款（_run_sync：无运行环本线程直跑，有环专用
单线程池另起环）；逐调用直读现行行（零缓存层——specs/knowledge.md「不做
缓存层」同纪律）。表访问＝Core 轻声明（读模型不入 ORM Base.metadata）。
全程只读（INV-2）：readonly 会话守卫＋返回冻结 dataclass。

非 serve 态（draft/disabled/negative）不进命中集——禁用条目照台账纪律不消费。
"""

from __future__ import annotations

import asyncio
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

# 问句归一（精确匹配的比较面）：剥首尾与内部引用符号＋空白＋问号——
# 「“躺井”是什么意思？」与「躺井是什么意思」同判；字母收小写（井号族不受影响）。
_QUOTE_CHARS = "「」『』“”\"'"


def normalize_faq_question(text: str) -> str:
    """FAQ 精确匹配的问句归一单点（两表两列同尺）。"""
    stripped = "".join(ch for ch in text.strip() if ch not in _QUOTE_CHARS)
    return (
        stripped.replace("？", "")
        .replace("?", "")
        .replace(" ", "")
        .replace("\u3000", "")
        .lower()
    )


@dataclass(frozen=True, slots=True)
class FaqHit:
    """FAQ 精确命中（直出链的语义锚——entry_id 可溯源）。"""

    entry_id: str
    question: str
    answer: str


def _run_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """同步缝→异步 DB 桥（PgKnowledgeStore 同款——见其模块 docstring）。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(awaitable)).result()


class PgFaqStore:
    """faq_* 直读读面（FAQ 直出链的命中判定缝——lookup 单公开方法）。"""

    def __init__(self, specs: Sequence[DatabaseSpec]) -> None:
        self._specs = tuple(specs)

    @classmethod
    def from_specs(cls, spec: DatabaseSpec) -> PgFaqStore:
        return cls([spec])

    def lookup(self, question: str) -> FaqHit | None:
        """问句→serve 条目精确命中（标准问优先、相似问次之；未命中 None）。

        每次调用直读现行行（零缓存）——逐调用新建专用 ConnectionManager
        （池连接与当次环同源，PgKnowledgeStore 同纪律）。
        """
        return _run_sync(self._lookup(question))

    async def _lookup(self, question: str) -> FaqHit | None:
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
        if not normalized:
            return None
        by_standard = {
            normalize_faq_question(str(row.question)): row for row in entry_rows
        }
        standard = by_standard.get(normalized)
        if standard is not None:
            return FaqHit(
                entry_id=str(standard.id),
                question=str(standard.question),
                answer=str(standard.answer),
            )
        by_similar: dict[str, Any] = {}
        for row in similar_rows:
            entry = entries.get(str(row.entry_id))
            if entry is not None:
                by_similar.setdefault(normalize_faq_question(str(row.text)), entry)
        similar = by_similar.get(normalized)
        if similar is not None:
            return FaqHit(
                entry_id=str(similar.id),
                question=str(similar.question),
                answer=str(similar.answer),
            )
        return None
