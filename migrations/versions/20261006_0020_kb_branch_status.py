"""kb_ingest_task 加 branch_status jsonb（G-02 支路进度可见——百科/图谱支路状态入任务卡）。

形状：{"wiki": {"state": "running|done|failed", "detail": "..."},
      "graph": {"state": ..., "chunks_done": n, "chunks_total": n, "edges": n, "blocked": n}}
derivatives 支路经组合根注入的回写 callable 合并写；不参与任务 state（支路失败不回退 done）。

Revision ID: 0020
Revises: 0019
链上编排：单头线性链（99 §4.4）；零存量列变更——只加列＋存量行置空对象。
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "kb_ingest_task",
        sa.Column("branch_status", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.execute("UPDATE kb_ingest_task SET branch_status = '{}'::jsonb")
    op.alter_column("kb_ingest_task", "branch_status", server_default=None)


def downgrade() -> None:
    op.drop_column("kb_ingest_task", "branch_status")
