"""well_status_log 补位表——井状态变更行台账（99 §2.3 列形；M-02）。

- 来源：A2 井档案施工批（M-02）——A2 端点 3「纪录」合并视图的状态变更行
  在设定书 8 表字典无落表（A2 开放问题 1），99 册存储设计批已裁落表补位
  （§2.0③/§2.3 wells 域唯一落表）；本迁移即该列形的 Alembic 承载，与
  ``ensure_wells_tables``（P0-08 惯例幂等直建，main.py lifespan 调用）并行
  存活。
- 列形照抄 99 §2.3：id bigserial（追加型序列主键例外，§1.2）· well_id
  （归一化主键——FK 语义指向中台 raw.well_info，跨库语义外键不落物理 FK）·
  occurred_on date（状态变更发生日＝A2 events 排序键）· title · outcome
  （警示文案 nullable）· source_batch（来源批次——补录语义可缺，§A.4
  batch_id 同形；99 未标 nullable，本迁移落 nullable，装配批若裁决 NOT NULL
  随批改）＋基线列 created_at/updated_at（§1.3）；索引 (well_id, occurred_on)。
- 写入通道悬置（99 开放问题 2——中台 CDC/工作流 Writeback/人工登记待工作流
  执行链合同批）：wells 域纯读无写出口，本表本批只落读面承载。
- 链上编排：down_revision 接 0015（单头线性链——0016→0014→0015 现势头）。

数据影响评估：全新空表＋一索引，零存量触碰、零回填；downgrade 删表即状态
变更行丢弃（本表尚无消费写口，无业务损失）；不触任何其他表与列。

Revision ID: 0017
Revises: 0015
Create Date: 2026-10-04

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """建 well_status_log（99 §2.3 列形——状态变更行平台侧补位）。"""
    op.create_table(
        "well_status_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("well_id", sa.String(length=8), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("source_batch", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "well_status_log_well_id_occurred_on_idx",
        "well_status_log",
        ["well_id", "occurred_on"],
    )


def downgrade() -> None:
    """删 well_status_log（本表无消费写口——回滚零业务损失）。"""
    op.drop_index(
        "well_status_log_well_id_occurred_on_idx", table_name="well_status_log"
    )
    op.drop_table("well_status_log")
