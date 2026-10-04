"""wiki_page 增覆盖语义页级三列 content/claims/glossary_terms（当前版载体）。

- 来源：P2-04 修复拍 F1（2026-10-04 中途审查发现升格——PG 部署前必办），
  与 dev 回报疑点②（存量 PG 库列形迁移）合并解决。B4 v0.4 覆盖语义
  （Owner 2026-10-04 拍板撤版本历史）：重建＝wiki_page 页级行原地更新，
  content（当前版自由 markdown 全文）/claims/glossary_terms（当前版投影段，
  生成时固化）三列承载当前版快照、current_version＝重建计数；ORM 侧
  （app/domains/derivatives/store.py WikiPageRow）已随 fe9692e 合入，而
  Alembic 0004_wiki_baseline 建 wiki_page 仍为 v0.3 旧列形（三列缺位）——
  ensure_derivatives_tables 只建不改（checkfirst），凡经 `alembic upgrade
  head` 供应的 PG 库（含全新库）wiki 生成/重铸 INSERT 必败
  （undefined column）；SQLite 测试底座走 ensure 直建新列形故 CI 不可见。
- 列形与 ORM 单源对齐：content TEXT NOT NULL、claims/glossary_terms JSONB
  NOT NULL（_J＝JSONB().with_variant(JSON,"sqlite") 的 PG 半边，
  20261001_0004 wiki_page_version 同款声明形）。
- 存量行语义：三列携 server_default（''／'[]'::jsonb）——ALTER 即以默认值
  落位，旧形页读面降级为空稿（status 按空正文派生＝「正常」，不留悬空
  NULL）；PG16 恒定默认加列为元数据操作，演示量级即时完成。
- SQLite 变体声明仅为 Alembic 离线 --sql 模式可用；sqlite 测试底座走
  ensure_derivatives_tables 直建、不经迁移（双轨并行是现状，退役拍挂后续票）。

数据影响评估：仅 ADD COLUMN 三列（NOT NULL＋恒定 server_default，零回填
语句），存量行落默认值＝空稿降级、新写路径照常覆盖；downgrade 删列即
**当前版稿不可逆丢弃**（v0.4 覆盖语义无版本留档可回查）——downgrade 仅备
列形回退，生产库禁用；不触任何其他表与列。

Revision ID: 0016
Revises: 0013
Create Date: 2026-10-04

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_J = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    """增 content/claims/glossary_terms 三列（当前版载体——覆盖语义落库位）。"""
    op.add_column(
        "wiki_page",
        sa.Column("content", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "wiki_page",
        sa.Column("claims", _J, nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "wiki_page",
        sa.Column(
            "glossary_terms", _J, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )


def downgrade() -> None:
    """删三列（当前版稿随删不可逆——v0.4 覆盖语义无版本留档，生产库禁用）。"""
    op.drop_column("wiki_page", "glossary_terms")
    op.drop_column("wiki_page", "claims")
    op.drop_column("wiki_page", "content")
