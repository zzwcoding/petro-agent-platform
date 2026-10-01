"""kb_issue_report

域前缀纪律：slug 以域前缀开头（infra_/sem_/kb_/wiki_…，99 §1 表前缀＝模块
归属可读化；versions/ 单目录平放——alembic.ini 头注）。

P1-04 B2 切片管理：kb_issue_report（质检复核队列——落位 B2 页〔Owner
2026-10-01 拍板〕；99 §2.5 逐字段：state CHECK 四态「待质检复核,已修正,
已驳回,已销记」v0.3 冻结＋reject_reason nullable＋marked_by/marked_at＋
reviewed_by/reviewed_at nullable；uq 部分索引＝待质检复核态 fragment_id 唯一
——重复标记 409 判据，全列 uq 会卡死驳回后重新标记，按 99 注记语义落部分
索引，差异登记票面）。仅新增一表，不触碰任何既有表与数据。

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-01 21:28:11.854839

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('kb_issue_report',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('fragment_id', sa.String(length=32), nullable=False),
    sa.Column('state', sa.String(length=8), nullable=False),
    sa.Column('reject_reason', sa.Text(), nullable=True),
    sa.Column('marked_by', sa.Text(), nullable=False),
    sa.Column('marked_at', sa.DateTime(), nullable=False),
    sa.Column('reviewed_by', sa.Text(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint(
        "state IN ('待质检复核','已修正','已驳回','已销记')",
        name='ck_kb_issue_report_state',
    ),
    sa.ForeignKeyConstraint(['fragment_id'], ['kb_fragment.id'], ),
    sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_kb_issue_report_state', 'kb_issue_report', ['state'], unique=False)
    op.create_index(
        'uq_kb_issue_report_pending_fragment', 'kb_issue_report', ['fragment_id'],
        unique=True, postgresql_where=sa.text("state = '待质检复核'"),
    )


def downgrade() -> None:
    op.drop_index('uq_kb_issue_report_pending_fragment', table_name='kb_issue_report')
    op.drop_index('ix_kb_issue_report_state', table_name='kb_issue_report')
    op.drop_table('kb_issue_report')
