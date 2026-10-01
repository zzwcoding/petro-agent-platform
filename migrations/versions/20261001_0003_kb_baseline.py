"""kb 域基线——kb 八表建表（99 §2.5 逐字段；tickets/phase1/README.md P1-02a）。

kb 域迁移首执行点（操作序照 P0-08/P1-01 登记）：env.py 域模型登记区补挂
app.domains.kb.store import → 本迁移 autogenerate 生成（revision 0003、slug
域前缀 kb_）→ upgrade head / downgrade base 双向实跑过（PG16@5433）。

- 本迁移**只触 kb_* 八表**（kb_library/kb_library_config/kb_upload/kb_report/
  kb_ingest_task/kb_fragment/kb_fragment_version/kb_activity——kb_issue_report
  归 B2 批、kb_extract_config 归 derivatives 批）；autogenerate 对 env.py 未挂
  模型的既有 ensure_* 表（audit_log/gateway 三表/infra_outbox）误报 drop 已人工
  剔除——跨域追溯建表归各域票（P1-01 同款处置）。
- pgvector（ADR-0003 裁决 1）：upgrade 先 `CREATE EXTENSION IF NOT EXISTS
  vector`，kb_fragment.embedding 落 `vector(384)`（维度占位——99 册注记
  「维度待 embedding 模型选定后回填＝待办」）；downgrade 不 drop 扩展
  （扩展是库级资产，不随域迁移撤除）。
- kb_upload.lib_id 可空（差异登记：入库路由流受理时目标库未定——confirm 定型
  routed_lib_id；99 DDL 未标 NOT NULL，直指定流两列同值）。

数据影响评估（upgrade head @ petro@5433 演示库）：仅新增 kb_* 八表（空表）＋
pgvector 扩展（若未装），不触碰任何既有表与数据；downgrade 只 drop kb_* 八表。

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-01 19:12:19.115216

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.domains.kb.store import PgVectorType

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """建 kb_* 八表（99 §2.5；枚举落 CHECK、jsonb 按 §1.5 裁决清单、向量列 pgvector）。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "kb_library",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("biz_template", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "biz_template IN ('completion','monthly','dynamic','blank')",
            name="ck_kb_library_biz_template",
        ),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_kb_library_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kb_activity",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("lib_id", sa.String(length=32), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("who", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lib_id"], ["kb_library.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kb_activity_lib_time", "kb_activity", ["lib_id", sa.literal_column("time DESC")]
    )
    op.create_table(
        "kb_library_config",
        sa.Column("lib_id", sa.String(length=32), nullable=False),
        sa.Column("semantic", sa.Boolean(), nullable=False),
        sa.Column("keyword", sa.Boolean(), nullable=False),
        sa.Column("wiki", sa.Boolean(), nullable=False),
        sa.Column("graph", sa.Boolean(), nullable=False),
        sa.Column("mode", sa.String(length=8), nullable=False),
        sa.Column("add_summary", sa.Boolean(), nullable=False),
        sa.Column("add_questions", sa.Boolean(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), nullable=True),
        sa.Column("saved_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("mode IN ('smart','fixed','mixed')", name="ck_kb_library_config_mode"),
        sa.ForeignKeyConstraint(["lib_id"], ["kb_library.id"]),
        sa.PrimaryKeyConstraint("lib_id"),
    )
    op.create_table(
        "kb_report",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lib_id", sa.String(length=32), nullable=False),
        sa.Column("doc", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column(
            "related_objects",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("wiki_current_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('已入库')", name="ck_kb_report_status"),
        sa.ForeignKeyConstraint(["lib_id"], ["kb_library.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_report_lib", "kb_report", ["lib_id"])
    op.create_table(
        "kb_upload",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("size", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("lib_id", sa.String(length=32), nullable=True),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("suggested_topic", sa.Text(), nullable=True),
        sa.Column("routed_lib_id", sa.String(length=32), nullable=True),
        sa.Column("route_confirmed_by", sa.Text(), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','confirmed','expired')", name="ck_kb_upload_status"
        ),
        sa.ForeignKeyConstraint(["lib_id"], ["kb_library.id"]),
        sa.ForeignKeyConstraint(["routed_lib_id"], ["kb_library.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "kb_fragment",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("report_id", sa.String(length=32), nullable=False),
        sa.Column("type", sa.String(length=8), nullable=False),
        sa.Column("section", sa.Text(), nullable=True),
        sa.Column("well", sa.Text(), nullable=True),
        sa.Column("hit_text", sa.Text(), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("is_parent_only", sa.Boolean(), nullable=False),
        sa.Column("embedding", PgVectorType().with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "type IN ('原文块','图片说明块','图片文字块','摘要块','问题块')",
            name="ck_kb_fragment_type",
        ),
        sa.ForeignKeyConstraint(["report_id"], ["kb_report.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kb_fragment_report", "kb_fragment", ["report_id"])
    op.create_index("ix_kb_fragment_type", "kb_fragment", ["type"])
    op.create_table(
        "kb_ingest_task",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("upload_id", sa.String(length=32), nullable=True),
        sa.Column("report_id", sa.String(length=32), nullable=False),
        sa.Column("lib_id", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("current_step", sa.SmallInteger(), nullable=False),
        sa.Column("stop_at", sa.String(length=16), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "nodes",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "config_snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
        ),
        sa.Column(
            "extract_snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "source IN ('上传入库','片段修正','重跑定型')", name="ck_kb_ingest_task_source"
        ),
        sa.CheckConstraint(
            "state IN ('running','done','failed','stuck')", name="ck_kb_ingest_task_state"
        ),
        sa.ForeignKeyConstraint(["lib_id"], ["kb_library.id"]),
        sa.ForeignKeyConstraint(["report_id"], ["kb_report.id"]),
        sa.ForeignKeyConstraint(["upload_id"], ["kb_upload.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_kb_ingest_task_lib_started",
        "kb_ingest_task",
        ["lib_id", sa.literal_column("started_at DESC")],
    )
    op.create_index("ix_kb_ingest_task_source", "kb_ingest_task", ["source"])
    op.create_table(
        "kb_fragment_version",
        sa.Column("fragment_id", sa.String(length=32), nullable=False),
        sa.Column("v", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("context_text", sa.Text(), nullable=True),
        sa.Column("note", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "note IN ('原始解析','人工修正')", name="ck_kb_fragment_version_note"
        ),
        sa.ForeignKeyConstraint(["fragment_id"], ["kb_fragment.id"]),
        sa.PrimaryKeyConstraint("fragment_id", "v"),
    )


def downgrade() -> None:
    """drop kb_* 八表（本迁移所建；pgvector 扩展为库级资产不撤；既有 ensure_* 表不追溯）。"""
    op.drop_table("kb_fragment_version")
    op.drop_index("ix_kb_ingest_task_source", table_name="kb_ingest_task")
    op.drop_index("ix_kb_ingest_task_lib_started", table_name="kb_ingest_task")
    op.drop_table("kb_ingest_task")
    op.drop_index("ix_kb_fragment_type", table_name="kb_fragment")
    op.drop_index("ix_kb_fragment_report", table_name="kb_fragment")
    op.drop_table("kb_fragment")
    op.drop_table("kb_upload")
    op.drop_index("ix_kb_report_lib", table_name="kb_report")
    op.drop_table("kb_report")
    op.drop_table("kb_library_config")
    op.drop_index("ix_kb_activity_lib_time", table_name="kb_activity")
    op.drop_table("kb_activity")
    op.drop_table("kb_library")
