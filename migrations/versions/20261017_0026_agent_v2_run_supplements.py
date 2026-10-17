"""agent_v2_run 增补面列（supplements——EB3 D1 交付面分层）。

agent_v2_run 加 supplements（JSON，可空）：程序追加内容（分源块／归属块／引用清单／血缘
五要素全文）的落库形——条目 `{block, text}`、块型闭世界四值（`split`／`attribution`／
`citations`／`lineage`，真源 `specs/transport.md` 接口定义节 `SUPPLEMENT_BLOCKS`）。
正文（`answer` 列）不再含这些块（`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md`
D1／D2）；列表读口 `GET /api/v2/chat/runs` 随行携带（`RunListItem.supplements`）。

Alembic 独立版本文件（与 ensure_agent_v2_tables 双轨同形——0022／0025 同款纪律）；
存量行零迁移语义：可空列＝既有 run 无增补面（读回为空列，不回溯改写）。

Revision ID: 0026
Revises: 0025
链上编排：单头线性链（99 §4.4）。
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_v2_run",
        sa.Column("supplements", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_v2_run", "supplements")
