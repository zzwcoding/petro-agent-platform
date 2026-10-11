"""agent_v2_blackbox 黑匣子蒸馏存档表（V2-55——payload 入库不入帧防仓膨胀）。

git/帧只留判分件与瘦指针（EVENT_BLACKBOX pointer）；过程档案（history 模型
原话／observations 全字段／steps payload／判定面）经本表由
RunStore.put_blackbox/get_blackbox 读写，tools/run_replay --distill 读面。

Alembic 独立版本文件（ensure_agent_v2_tables 双轨同形——0022 前例）。

Revision ID: 0024
Revises: 0023
链上编排：单头线性链（99 §4.4）；全新表零存量变更。
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """建表（幂等护栏——ensure_agent_v2_tables 双轨可能先建，0023 同款并存）。"""
    bind = op.get_bind()
    if sa.inspect(bind).has_table("agent_v2_blackbox"):
        return
    op.create_table(
        "agent_v2_blackbox",
        sa.Column("run_id", sa.String(32), primary_key=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_v2_blackbox")
