"""kb_retrieval_enrich 富化索引表入版本轴（V2-47 R1b 切片富化）。

- 表＝V2 检索域自有 additive 富化索引（kb_* 原表零触碰——旧向量/原文可重建
  不毁 fixture；回滚＝清空本表即回落原向量/原文）。行两类：slice_embed（切
  片富化向量——索引文本〔本段节选自〈报告名〉·〈章节路径〉〕＋原文的 db 型
  重嵌）＋section_summary（节级摘要节点——确定性 node_id，节路径＋覆盖要点
  ＋出处链三级＋族随行）。
- 与 appv2/retrieval/pg_enrich.py ``ensure_enrich_tables`` 双轨同形（P0-08
  先例、0018 收口惯例）：全部 IF NOT EXISTS 幂等——ensure 先建的既有库再跑
  本迁移零冲突、零改写。
- 幂等钉的物理承载：PRIMARY KEY (kind, key)——同键重跑删插覆写零重复节点
  （确定性 node_id＝md5(report_id|root)）。
- 链位编排：down_revision=0022（文件名序＝链序，无中插）。

数据影响评估：全新库＝新建一表＋一索引，零存量；既有库＝IF NOT EXISTS 跳
过，零触碰、零回填；downgrade 删表＝富化索引丢弃（kb_* 原表不动——检索自
动回落原向量/原文，零业务数据损失）。

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-10

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COMMENTS: list[tuple[str, str, str]] = [
    ("kb_retrieval_enrich", "kind", "行类（slice_embed＝切片向量｜section_summary＝摘要节点）"),
    ("kb_retrieval_enrich", "key", "行键（fragment_id｜node_id＝ensum-md5 前 12 字符）"),
    ("kb_retrieval_enrich", "report_id", "出处报告 id（摘要节点在案；overlay 行空串）"),
    ("kb_retrieval_enrich", "report", "出处报告名（摘要节点出处链——读面自足）"),
    ("kb_retrieval_enrich", "library_id", "出处库 id（出处链三级）"),
    ("kb_retrieval_enrich", "library", "出处库名（出处链三级）"),
    ("kb_retrieval_enrich", "family", "族标注（库 biz_template 透传——供给分池键）"),
    ("kb_retrieval_enrich", "section", "节路径（摘要节点＝顶层章名——节内展开键）"),
    ("kb_retrieval_enrich", "node_text", "摘要节点文本（〔节级摘要｜…〕＋覆盖要点；overlay 行空）"),
    ("kb_retrieval_enrich", "cover_count", "覆盖切片支数（摘要节点）"),
    ("kb_retrieval_enrich", "source_ids", "成员切片 id JSON 数组（摘要节点）"),
    ("kb_retrieval_enrich", "embedding", "富化向量（embo-01 db 型 1536 维——索引文本＝前缀＋原文）"),
    ("kb_retrieval_enrich", "model", "向量化后端名（记账面）"),
    ("kb_retrieval_enrich", "enriched_at", "富化时刻（infra.clock——B14）"),
]

_TABLE_COMMENT = (
    "V2 检索富化索引（V2-47 R1b——切片上下文前缀重嵌＋节级摘要层；additive "
    "幂等，kb_* 原表零触碰；回滚＝清空本表）"
)


def upgrade() -> None:
    """建表＋索引（IF NOT EXISTS——与 ensure_enrich_tables 幂等并存）。"""
    op.execute("""
        CREATE TABLE IF NOT EXISTS kb_retrieval_enrich (
            "kind" VARCHAR(16) NOT NULL,
            "key" VARCHAR(64) NOT NULL,
            "report_id" VARCHAR(32) NOT NULL,
            "report" TEXT NOT NULL,
            "library_id" VARCHAR(32) NOT NULL,
            "library" TEXT NOT NULL,
            "family" VARCHAR(16) NOT NULL,
            "section" TEXT,
            "node_text" TEXT,
            "cover_count" INTEGER,
            "source_ids" TEXT,
            "embedding" vector(1536) NOT NULL,
            "model" VARCHAR(64) NOT NULL,
            "enriched_at" TEXT NOT NULL,
            PRIMARY KEY ("kind", "key")
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_kb_retrieval_enrich_report "
        "ON kb_retrieval_enrich (report_id)"
    )
    op.execute(f"COMMENT ON TABLE kb_retrieval_enrich IS '{_TABLE_COMMENT}'")
    for table, column, comment in _COMMENTS:
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{comment}'")


def downgrade() -> None:
    """drop 索引＋表（kb_* 原表不动——检索自动回落原向量/原文）。"""
    op.execute("DROP INDEX IF EXISTS ix_kb_retrieval_enrich_report")
    op.execute("DROP TABLE IF EXISTS kb_retrieval_enrich")
