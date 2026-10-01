"""chat 域基线——chat 三表建表（99 §2.2 逐字段；tickets/phase1/README.md P1-08a）。

chat 域迁移首执行点（操作序照 P0-08/P1-01 登记）：env.py 域模型登记区补挂
app.domains.chat.store import → 本迁移按 99 §2.2 表序手写（会话→消息→运行；
消息 FK 引用会话、运行 FK 引用会话；双向实跑 PG16@5433）。

- `chat_session`：服务端持久会话（A1 端点 2——换设备不丢；updated_at 排序键）。
  `group` 为 SQL 保留字（99 §2.2 注记——DDL 引号承载，SQLAlchemy 自动处理）。
- `chat_message`：会话消息（A1 端点 3——answer 与 SSE answer 帧同形 DTO）；
  uq(session_id, seq) 与 idx run_id 按 99 键·索引列落（uq 落唯一索引，与 ORM
  双轨同形）；role CHECK(user,assistant)。
- `chat_run`：一次问答运行（A1 端点 4/5——聚合根；status 六值 CHECK；verdict/
  pending_interrupt jsonb；clarify_count smallint CHECK 0–1＝澄清帧有界循环
  「最多弹一次」的存储强制，第二次 clarify 409——99 §2.2 合同锚原文）。
- 19 类事件帧不落库（99 §1.5「SSE 事件缓冲不落库」裁决——本域无帧表）。
- chat_artifact_task/chat_artifact/chat_tool/chat_scenario 四表不属本票（产物
  任务/工具注册表/场景注册表随其端点票落）。

数据影响评估（upgrade head @ petro@5433 演示库）：仅新增 chat_* 三表（空表，
无种子——会话经 asks 受理即落行），不触碰任何既有表与数据；downgrade 只
drop chat_* 三表。

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    """建 chat 三表（99 §2.2 表序：会话先建——消息/运行 FK 引用 session）。"""
    op.create_table(
        "chat_session",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("group", sa.Text(), nullable=True),
        sa.Column("scenario_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_session_user_updated", "chat_session", ["user_id", "updated_at"])
    op.create_table(
        "chat_message",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("run_id", sa.String(length=32), nullable=True),
        sa.Column("answer", _JSON, nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("role IN ('user','assistant')", name="ck_chat_message_role"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_chat_message_session_seq", "chat_message", ["session_id", "seq"], unique=True
    )
    op.create_index("ix_chat_message_run", "chat_message", ["run_id"])
    op.create_table(
        "chat_run",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("session_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("verdict", _JSON, nullable=True),
        sa.Column("pending_interrupt", _JSON, nullable=True),
        sa.Column("pending_approval_id", sa.String(length=64), nullable=True),
        sa.Column("clarify_count", sa.SmallInteger(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running','interrupt_clarify','interrupt_approval',"
            "'done','failed','cancelled')",
            name="ck_chat_run_status",
        ),
        sa.CheckConstraint("clarify_count >= 0 AND clarify_count <= 1", name="ck_chat_run_clarify"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_run_session", "chat_run", ["session_id"])


def downgrade() -> None:
    """drop chat 三表（本迁移所建；既有 ensure_* 表不追溯）。"""
    op.drop_index("ix_chat_run_session", table_name="chat_run")
    op.drop_table("chat_run")
    op.drop_index("ix_chat_message_run", table_name="chat_message")
    op.drop_index("uq_chat_message_session_seq", table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_index("ix_chat_session_user_updated", table_name="chat_session")
    op.drop_table("chat_session")
