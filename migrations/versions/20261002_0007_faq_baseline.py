"""faq 域基线——faq 四表建表（99 §2.6 逐字段；tickets/phase1/README.md P1-06）。

faq 域迁移首执行点（操作序照 P0-08/P1-01 登记）：env.py 域模型登记区补挂
app.domains.faq.store import → 本迁移按 99 §2.6 表序手写（faq_entry →
faq_similar_question → faq_candidate → faq_scan_task，双向实跑 PG16@5433）。

- 本迁移**只触 faq_* 四表**（`faq_config` 已撤除——扩检收敛 D2
  `qa_behavior.faq_expand_rounds`，B3 v0.2 端点撤除登记，不建表；候选索引照
  99「idx (freq desc)」落 (freq)＋倒序查询 ORDER BY 显式化——索引不携方向，
  排序归 SQL）。
- 差异登记（99 关键列未列、审核流落定需要）：`faq_entry.is_negative` bool
  NOT NULL——待审核行承载负例登记意向（端点 3 入参名照抄），审核 publish 落
  negative；kb_upload.lib_id 可空先例同族，登记 tickets/phase1 README P1-06。
- 基线列 created_at/updated_at（P0-04 惯例，99 §1.3 timestamp 无时区）；
  展示「更新时间」日期粒度读侧取 date（R2 展示串不入库）。

数据影响评估（upgrade head @ petro@5433 演示库）：仅新增 faq_* 四表（空表，
演示种子经 lifespan seed_demo_if_empty 装载），不触碰任何既有表与数据；
downgrade 只 drop faq_* 四表。

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    """建 faq_* 四表（99 §2.6 表序；枚举落 CHECK、jsonb 按 §1.5 裁决清单）。"""
    op.create_table(
        "faq_entry",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("question_norm", sa.Text(), nullable=False),
        sa.Column("norm_hash", sa.String(length=64), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("is_negative", sa.Boolean(), nullable=False),
        sa.Column("hook_kind", sa.String(length=8), nullable=True),
        sa.Column("hook_name", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("maintainer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending_review','serve','negative','disabled')",
            name="ck_faq_entry_status",
        ),
        sa.CheckConstraint(
            "hook_kind IS NULL OR hook_kind IN ('metric','term')",
            name="ck_faq_entry_hook_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faq_entry_status", "faq_entry", ["status"])
    op.create_table(
        "faq_similar_question",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("entry_id", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_norm", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["faq_entry.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faq_similar_entry", "faq_similar_question", ["entry_id"])
    op.create_index("ix_faq_similar_text_norm", "faq_similar_question", ["text_norm"])
    op.create_table(
        "faq_candidate",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("variants", _JSON, nullable=False),
        sa.Column("freq", sa.Integer(), nullable=False),
        sa.Column("window", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("compare", _JSON, nullable=True),
        sa.Column("draft", sa.Text(), nullable=True),
        sa.Column("hook_kind", sa.String(length=8), nullable=True),
        sa.Column("hook_name", sa.Text(), nullable=True),
        sa.Column("source_entry_id", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','compared','drafted','published')",
            name="ck_faq_candidate_status",
        ),
        sa.CheckConstraint(
            "hook_kind IS NULL OR hook_kind IN ('metric','term')",
            name="ck_faq_candidate_hook_kind",
        ),
        sa.ForeignKeyConstraint(["source_entry_id"], ["faq_entry.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_faq_candidate_freq", "faq_candidate", ["freq"])
    op.create_table(
        "faq_scan_task",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("new_cluster_count", sa.Integer(), nullable=False),
        sa.Column("new_clusters", _JSON, nullable=False),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('running','done')", name="ck_faq_scan_task_status"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """drop faq_* 四表（本迁移所建；既有 ensure_* 表不追溯）。"""
    op.drop_table("faq_scan_task")
    op.drop_index("ix_faq_candidate_freq", table_name="faq_candidate")
    op.drop_table("faq_candidate")
    op.drop_index("ix_faq_similar_text_norm", table_name="faq_similar_question")
    op.drop_index("ix_faq_similar_entry", table_name="faq_similar_question")
    op.drop_table("faq_similar_question")
    op.drop_index("ix_faq_entry_status", table_name="faq_entry")
    op.drop_table("faq_entry")
