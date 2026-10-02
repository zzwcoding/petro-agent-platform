"""kb 片段向量列 384→1536（P1-11 选型接线：MiniMax embo-01 真维度回填）。

- 维度真源＝config/models.yaml petro-embed（embo-01，2026-10-02 curl 实测
  vectors[N][1536] 已归一化）；此前 384 为 LocalHash 本地占位维度（99 注记
  「维度待 embedding 模型选定后回填＝待办」本票兑现）。
- pgvector 不支持 vector(384)::vector(1536) 的跨维度 cast——先清空列值
  （UPDATE … SET embedding = NULL）再 ALTER TYPE；存量 384 维占位向量随清空
  失效，重嵌由 `uv run python -m app.domains.kb.reembed` 脚本补齐（embed 步
  同源实现——真模型重嵌/测试底座 LocalHash 重嵌皆可）。
- 与 ensure_kb_tables 双轨同形（PgVectorType.get_col_spec 读 d.EMBED_DIM 单源
  ——新库 ensure 直建 1536，旧库靠本迁移改形；幂等：USING 无 cast 直改＋
  NULL 清空对空列零写）。downgrade 回 384 同法（先清列再改形——1536 数据装
  不进 384 列，降级即弃嵌、升回后须再跑重嵌脚本，如实登记）。

数据影响评估：只触 kb_fragment.embedding 一列（清空＋改形），不触任何其他
表与列；演示量级 ALTER 即时。

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """清空存量占位向量→列形改 vector(1536)（embo-01 真维度）。"""
    op.execute("UPDATE kb_fragment SET embedding = NULL")
    op.execute("ALTER TABLE kb_fragment ALTER COLUMN embedding TYPE vector(1536)")


def downgrade() -> None:
    """回 384 占位列形（1536 向量装不进 384 列——先清列再改形，降级即弃嵌）。"""
    op.execute("UPDATE kb_fragment SET embedding = NULL")
    op.execute("ALTER TABLE kb_fragment ALTER COLUMN embedding TYPE vector(384)")
