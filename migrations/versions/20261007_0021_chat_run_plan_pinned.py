"""chat_run 加 plan_pinned jsonb（L-05 pinned_plan 持久化载体——机制 11）。

形状＝已验证 QueryPlan 的 dict 投影（domain.plan_pinned_payload 单源序列化：
五源槽位＋服务端重推导字段全量；window 端点 ISO 日期字符串）。NULL＝本 run
未走 LLM 生效路（快路-only 现状零变化）。审批挂起恢复消费前必经
domain.revalidate_pinned_plan 确定性复验（重跑 validator 零模型——不盲信
持久化载荷，F7 幂等升级为「持久化意图的确定性重放」）。

Revision ID: 0021
Revises: 0020
链上编排：单头线性链（99 §4.4）；零存量列变更——只加列、存量行保持 NULL。
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_run", sa.Column("plan_pinned", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("chat_run", "plan_pinned")
