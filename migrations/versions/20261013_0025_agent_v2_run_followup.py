"""agent_v2_run 追问链列（followup_of——V2-74 对话任务面）。

agent_v2_run 加 followup_of（String(32) 非空默认空串）：追问链前轮 run_id——
非空＝本 run 是该前轮的追问轮，空串＝独立新对话（链根）。执行器受理段随
RunCommand.followup_of 落库（executor.create_run 同拍）；列表读口 RunListItem
随行，前端按链分组呈现「一个对话任务一行」（A1V2 左栏对话列表）。

Alembic 独立版本文件（与 ensure_agent_v2_tables 双轨同形——0022 同款纪律）；
存量行零迁移语义：server_default 空串＝既有 run 全部视为链根（历史行为兼容）。

Revision ID: 0025
Revises: 0024
链上编排：单头线性链（99 §4.4）。
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_v2_run",
        sa.Column("followup_of", sa.String(32), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("agent_v2_run", "followup_of")
