"""agent_v2_run.created_at 降序索引（V2-141 列表读口 limit 下推的支撑索引）。

V2-141 把 `GET /api/v2/chat/runs` 的 limit 下推到端口侧——`Tables.scan_recent(limit)`
（PG 真件 SQL `SELECT ... FROM agent_v2_run ORDER BY created_at DESC LIMIT $1`）。
0022 只为 `agent_v2_step.run_id` 建了索引（`ix_agent_v2_step_run_id`），`agent_v2_run.created_at`
**无索引**（0025／0026／0027 均无）→ 本迁移补 `ix_agent_v2_run_created_at`（降序）。

Alembic 独立版本文件（接续 0027——0022／0025／0026／0027 同款纪律）；
链上编排：单头线性链（99 §4.4）。

**链上注意（Owner 2026-10-19 裁定：本票先落者定形状）**：V2-135 的迁移 0028（`agent_v2_blob`）
**未落**——其落地时须 rebase 迁移链：把本文件 `down_revision` 由 `0027` 改指 `0028`
（`down_revision: str | None = "0028"`），保持单头线性链不断。

Revision ID: 0029
Revises: 0027
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0027"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_agent_v2_run_created_at"


def upgrade() -> None:
    op.create_index(
        _INDEX_NAME, "agent_v2_run", [sa.text("created_at DESC")]
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="agent_v2_run")
