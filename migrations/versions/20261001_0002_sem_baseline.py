"""sem 域基线——sem_* 九表建表（99 §2.8 逐字段；tickets/phase1/README.md P1-01）。

sem 域迁移首执行点（操作序照 P0-08 登记）：env.py 域模型登记区补挂
app.domains.semantics.store import → 本迁移 autogenerate 生成（revision 0002、
slug 域前缀 sem_）→ upgrade head / downgrade base 双向实跑过（PG16@5433）。

交接关系（并行存活，不切换）：sem_* 九表同时由 ensure_semantics_tables 幂等
checkfirst 建表（main.py lifespan，沿 P0-04 audit / P0-05 gateway 惯例）——
应用启动建表路径不变，Alembic 立版本轴；ensure_* 退役拍随后续票裁决。
本迁移**只触 sem_* 九表**：audit_log / gateway 三表 / infra_outbox 等既有表
由各自域票追溯（env.py 未挂其模型 import，autogenerate 的「removed table」
误报已人工剔除——不属于本域迁移的职责）。

数据影响评估（upgrade head @ petro@5433 演示库）：仅新增 sem_* 九表（空表），
不触碰任何既有表与数据；downgrade base 只 drop sem_* 九表（本迁移建的部分）。

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01 18:05:12.036334

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """建 sem_* 九表（99 §2.8；枚举落 CHECK、jsonb 按 §1.5 裁决清单）。"""
    op.create_table(
        "sem_action",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("register_name", sa.String(length=64), nullable=False),
        sa.Column("business_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("register_name", name="uq_sem_action_register_name"),
    )
    op.create_table(
        "sem_join_whitelist",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("left_table", sa.Text(), nullable=False),
        sa.Column("right_table", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(length=8), nullable=False),
        sa.Column("tables", sa.Text(), nullable=False),
        sa.Column("how", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("verdict IN ('可以','默认不给')", name="ck_sem_join_whitelist_verdict"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sem_join_whitelist_left_right", "sem_join_whitelist", ["left_table", "right_table"]
    )
    op.create_table(
        "sem_ledger_revision",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("domain", sa.String(length=16), nullable=False),
        sa.Column("row_id", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("changed_by", sa.Text(), nullable=False),
        sa.Column("source_proposal_id", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "domain IN ('term','metric','object','relation','whitelist','workflow','action')",
            name="ck_sem_ledger_revision_domain",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", "row_id", "version", name="uq_sem_ledger_revision_row_ver"),
    )
    op.create_index(
        "ix_sem_ledger_revision_source_proposal", "sem_ledger_revision", ["source_proposal_id"]
    )
    op.create_table(
        "sem_metric",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mark", sa.String(length=1), nullable=True),
        sa.Column("slot_name", sa.Text(), nullable=False),
        sa.Column("def", sa.Text(), nullable=False),
        sa.Column("grain", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("dispute", sa.Text(), nullable=True),
        sa.Column(
            "modifiers",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("ambiguous", sa.Boolean(), nullable=False),
        sa.Column(
            "calibers",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("default_caliber", sa.String(length=8), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("mark IS NULL OR mark IN ('★','☆')", name="ck_sem_metric_mark"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot_name", name="uq_sem_metric_slot_name"),
    )
    op.create_table(
        "sem_object",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("obj", sa.Text(), nullable=False),
        sa.Column("attr", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sem_relation",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("rel", sa.Text(), nullable=False),
        sa.Column("read", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sem_term",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("def", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("status_key", sa.String(length=24), nullable=False),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status_key IN ('有效','禁用词','有效（限作业区语境）',"
            "'有效（待联席裁决）','有效（引用马涛）','有效（已届满）')",
            name="ck_sem_term_status_key",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sem_term_status_key_owner", "sem_term", ["status_key", "owner"])
    op.create_table(
        "sem_version",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("current", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sem_workflow",
        sa.Column("id", sa.String(length=8), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=4), nullable=False),
        sa.Column("account", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column(
            "card",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('登记','草案')", name="ck_sem_workflow_status"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """drop sem_* 九表（本迁移所建；既有 ensure_* 表不在此追溯——见模块 docstring）。"""
    op.drop_table("sem_workflow")
    op.drop_table("sem_version")
    op.drop_index("ix_sem_term_status_key_owner", table_name="sem_term")
    op.drop_table("sem_term")
    op.drop_table("sem_relation")
    op.drop_table("sem_object")
    op.drop_table("sem_metric")
    op.drop_index("ix_sem_ledger_revision_source_proposal", table_name="sem_ledger_revision")
    op.drop_table("sem_ledger_revision")
    op.drop_index("ix_sem_join_whitelist_left_right", table_name="sem_join_whitelist")
    op.drop_table("sem_join_whitelist")
    op.drop_table("sem_action")
