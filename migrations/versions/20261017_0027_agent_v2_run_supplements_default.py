"""agent_v2_run 增补面列默认（supplements server_default '[]'——BE-01 历史读口空列语义）。

`agent_v2_run.supplements` 补 server_default `'[]'`（2026-10-17 BE-01，对账
`docs/runtime-refactor/frontend-redesign-接口对账.md` D-4）：新行（INSERT 未携该列的写径）
落 `'[]'`＝「无块新轮」，不再落 NULL 与旧行混淆；**存量行零迁移**——不 UPDATE、null 保留
（null 即旧行的机读判据，历史行如实——读口投影「空列如实出 []、null 仅旧行」）。

Alembic 独立版本文件（接续 0026——0022／0025／0026 同款纪律）；链上编排：单头线性链
（99 §4.4）。

Revision ID: 0027
Revises: 0026
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "agent_v2_run", "supplements", existing_type=sa.JSON(), server_default="[]"
    )


def downgrade() -> None:
    op.alter_column(
        "agent_v2_run", "supplements", existing_type=sa.JSON(), server_default=None
    )
