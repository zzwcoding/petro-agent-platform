"""kb 关键词路倒排索引——kb_fragment.hit_text pg_trgm GIN 索引（P1-04 收尾裁决②）。

前置双闸裁决（tickets/phase1/README.md P1-04 收尾）：阶段 1 关键词路＝pg_trgm
子串匹配（BM25 排名挂后续批——99 §6-5 语义差已登记）；倒排索引物理落法随
P1-08b 落位。查询语义＝kb.index_search/index_search_dual 的 trigram 覆盖率读面
不变——索引只加速（pg_trgm GIN 支撑 LIKE/相似度检索，中文免分词器，与 P1-10
同扩展族）。

- upgrade：CREATE EXTENSION IF NOT EXISTS pg_trgm（库级资产，与 vector 扩展
  同惯例）＋ hit_text gin_trgm_ops GIN 索引（ensure_kb_tables 双轨同形——
  双轨退役拍挂 P1-11 收官票）。
- downgrade：只 drop 索引（不撤扩展——库级资产，0003 vector 同惯例）。

数据影响评估：仅新增一索引，不触任何表数据；演示量级建索引即时完成。

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX_NAME = "ix_kb_fragment_hit_text_trgm"


def upgrade() -> None:
    """pg_trgm 扩展＋hit_text GIN 索引（关键词路倒排——查询语义不变只加速）。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        _INDEX_NAME,
        "kb_fragment",
        ["hit_text"],
        postgresql_using="gin",
        postgresql_ops={"hit_text": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """drop 索引（不撤 pg_trgm 扩展——库级资产，vector 扩展同惯例）。"""
    op.drop_index(_INDEX_NAME, table_name="kb_fragment")
