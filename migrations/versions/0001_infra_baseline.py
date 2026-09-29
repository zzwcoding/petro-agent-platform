"""infra 基线（空迁移）——P0-08 迁移分组起点（versions/ 域前缀纪律首件）。

本迁移**有意为空**：P0-04 起建表走 ensure_*_table（幂等 checkfirst），既有表
（audit_log / gateway 三表 / infra_outbox）不在此追溯建。交接关系（P0-08 票面）：
ensure_*_table 与 Alembic **并行存活**——应用启动建表路径不变（main.py lifespan），
Alembic 只立版本轴；各域把建表切换为迁移（含既有表追溯建表迁移）属各域票，
本票不切换。切域票操作序＝env.py 域模型登记区补 import → autogenerate 出该域
迁移（slug 带域前缀）→ 票面登记 ensure_* 退役拍。

Revision ID: 0001
Revises:
Create Date: 2026-09-30

"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """空基线：仅立版本轴（alembic_version 表由 alembic 自理），不触碰任何表。"""
    pass


def downgrade() -> None:
    """回退到无迁移态：空操作（alembic_version 随 downgrade base 由 alembic 清理）。"""
    pass
