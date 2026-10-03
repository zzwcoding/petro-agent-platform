"""kb 入库任务表增 structure_snapshot 快照列（P1F-05 结构图版本级缓存落库位）。

- 来源：P1F-05（入库结构图 LLM 化＋代码守门，方案 A）——LLM 结构图随报告版本
  落 kb_ingest_task 任务快照列（缓存键绑定正文 sha256），同版本重入零 LLM
  调用、片段集字节级一致。ORM 侧（app/domains/kb/store.py
  IngestTaskRow.structure_snapshot＋TaskStore.list_for_report 缓存查找面）已随
  fix/P1F-05-structure-map 合入待并；本迁移按 PG 先行原则先给存量库补列
  （P-007b 迁移小票——列先于 ORM 合并落位，操作序照 P0-08/P1-01 惯例）。
- 可空语义：存量任务行无快照（NULL＝无缓存、走 LLM 提取）；LLM 不可用/超时/
  JSON 坏/校验不过的回退路径全规则时同样不写——列恒可空、零回填、零默认。
- 列形与 ORM 单源对齐：JSONB 可空（_J＝JSONB().with_variant(JSON,"sqlite")
  的 PG 半边，20261001_0003_kb_baseline 同款声明形；sqlite 测试底座走
  ensure_kb_tables 直建，不经迁移——双轨并行是现状，退役拍挂后续票）。

数据影响评估：仅 ADD COLUMN 一列（JSONB NULL），零数据迁移零回填；存量行该
列 NULL＝无快照走 LLM 提取（读侧判空回退，P1F-05 语义）；PG 无默认值加列为
元数据操作，演示量级即时完成，不触任何其他表与列。

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-03

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """增 structure_snapshot JSONB 可空列（存量行 NULL＝无快照走 LLM 提取）。"""
    op.add_column(
        "kb_ingest_task",
        sa.Column(
            "structure_snapshot",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """移除 structure_snapshot 列（缓存列可丢——重入回退 LLM 提取，无数据资产损失）。"""
    op.drop_column("kb_ingest_task", "structure_snapshot")
