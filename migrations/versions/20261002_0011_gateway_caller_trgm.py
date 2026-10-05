"""gateway 账本 caller 归因列＋spend-logs keyword pg_trgm 索引（P1-10 D1 增强批）。

- `caller`：调用方归因列（D1 v0.2 端点 4/8——网关受理时落列、枚举不封闭、
  存量可空聚合归 unattributed 桶；99 §2.13 §2.13-20261001 对齐批已登记）。
- pg_trgm：pg_trgm 扩展（幂等——0010 kb hit_text 已落扩展，同惯例重复执行
  不报错）＋ id/note 两列 gin_trgm_ops GIN 索引——spend-logs keyword（匹配
  调用号/备注）改 SQL LIKE 子串检索，「98 keyword 内存过滤惯例」本端点退役。

与 ensure_gateway_tables 双轨同形（退役拍挂 P1-11 收官票）；upgrade 全部
IF NOT EXISTS 幂等（ensure 先建的库再跑迁移不冲突）。downgrade：drop 两
索引＋撤 caller 列（不撤 pg_trgm 扩展——库级资产，vector/0010 同惯例）。

链位（DEP-01 改，仅 down_revision 一行）：0010 → **0018**——gateway 表族
迁移补建（20261005_0018_gateway_tables.py）插在本迁移之前，纯 Alembic 全
新库不再断链于本迁移的 ALTER/索引（P2-04.fix 偏差 2 挂账收口——0011 docstring
「ensure 先建的库再跑迁移不冲突」双轨前提由 0018 收敛）。

数据影响评估：仅新增一可空列＋两索引，不触任何既有行；演示量级建索引即时。

Revision ID: 0011
Revises: 0018
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = ("ix_gateway_spend_note_trgm", "ix_gateway_spend_id_trgm")


def upgrade() -> None:
    """caller 归因列（可空——存量行聚合归 unattributed）＋trgm GIN 两索引。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "ALTER TABLE gateway_spend_record "
        "ADD COLUMN IF NOT EXISTS caller VARCHAR(64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gateway_spend_note_trgm "
        "ON gateway_spend_record USING gin (note gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gateway_spend_id_trgm "
        "ON gateway_spend_record USING gin (id gin_trgm_ops)"
    )


def downgrade() -> None:
    """drop 两索引＋caller 列（不撤 pg_trgm 扩展——库级资产，0010 同惯例）。"""
    for index_name in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    op.execute("ALTER TABLE gateway_spend_record DROP COLUMN IF EXISTS caller")
