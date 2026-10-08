"""V2 runtime 三组表（agent_v2_ 前缀隔离 V1 表——V2-06；specs/agent-loop.md 行为约定 8）。

- agent_v2_run：run 状态机行（running→waiting_ask→（resume）→running→
  completed/failed；answer/manifest_digest 随终态落）；
- agent_v2_step：步记录（INV-5：六类 step 各一行，Manifest 随模型调用步存档）；
- agent_v2_checkpoint/_blob/_write：PgCheckpointer 存储载体（langgraph checkpoint
  机制表——state schema 自有，checkpointer 仅存储，ADR-0002 红线③；存储模型
  镜像官方 saver：checkpoint 行＋channel blob 去重＋task 级 write）。

Alembic 独立版本文件（票面验收：前缀隔离 V1 表）；ensure_agent_v2_tables 与本
文件双轨同形（P0-08 前约定，gateway/security store 同款）。

Revision ID: 0022
Revises: 0021
链上编排：单头线性链（99 §4.4）；全新表零存量变更。
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_v2_run",
        sa.Column("run_id", sa.String(32), primary_key=True),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("actor", sa.String(128), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("manifest_digest", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_table(
        "agent_v2_step",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("run_id", sa.String(32), nullable=False),
        sa.Column("seq", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("title", sa.Text, nullable=False, server_default=""),
        sa.Column("manifest", sa.JSON, nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_agent_v2_step_run_id", "agent_v2_step", ["run_id"])
    op.create_table(
        "agent_v2_checkpoint",
        sa.Column("thread_id", sa.String(64), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(128), primary_key=True),
        sa.Column("checkpoint_id", sa.String(64), primary_key=True),
        sa.Column("parent_checkpoint_id", sa.String(64), nullable=True),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("checkpoint", sa.LargeBinary, nullable=False),
        sa.Column("metadata_json", sa.LargeBinary, nullable=False),
    )
    op.create_table(
        "agent_v2_checkpoint_blob",
        sa.Column("thread_id", sa.String(64), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(128), primary_key=True),
        sa.Column("channel", sa.String(128), primary_key=True),
        sa.Column("version", sa.String(64), primary_key=True),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("blob", sa.LargeBinary, nullable=False),
    )
    op.create_table(
        "agent_v2_checkpoint_write",
        sa.Column("thread_id", sa.String(64), primary_key=True),
        sa.Column("checkpoint_ns", sa.String(128), primary_key=True),
        sa.Column("checkpoint_id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), primary_key=True),
        sa.Column("idx", sa.Integer, primary_key=True),
        sa.Column("channel", sa.String(128), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("blob", sa.LargeBinary, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_v2_checkpoint_write")
    op.drop_table("agent_v2_checkpoint_blob")
    op.drop_table("agent_v2_checkpoint")
    op.drop_index("ix_agent_v2_step_run_id", table_name="agent_v2_step")
    op.drop_table("agent_v2_step")
    op.drop_table("agent_v2_run")
