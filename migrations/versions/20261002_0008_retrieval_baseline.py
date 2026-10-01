"""retrieval 域基线——retrieval 两表建表（99 §2.10 逐字段；tickets/phase1/README.md P1-07）。

retrieval 域迁移首执行点（操作序照 P0-08/P1-01 登记）：env.py 域模型登记区补挂
app.domains.retrieval.store import → 本迁移按 99 §2.10 表序手写（版本表先建——
指针表 FK 引用 version_no；双向实跑 PG16@5433）。

- `retrieval_config_version`：PK(version_no)（99 自然键注册表——「v23」形合同
  字段即键）；config jsonb 六配置节（order/params/rerank/citation_format/
  fallback/qa_behavior——R1 snake 迁移同款节键，「七个配置节」计数含 version
  元信息节、version 走列不走 jsonb）；via 生效变动单号可空（种子行非变更产生
  →null）；回滚端点不立（D2 开放问题 4 已裁决——Owner 2026-10-01），版本行
  承载＝append-only 修改历史。
- `retrieval_config`：id='singleton' PK＋current_version_no FK（生效指针单例行
  ——D2 端点 1「恒返回生效值；待审 patch 不进响应」）。
- 枚举不落列级 CHECK：配置节枚举承载于 jsonb、校验在域层（D2 400 带字段与
  允许区间），99 §2.10 未冻结 CHECK；基线列 created_at/updated_at（P0-04 惯例；
  版本行 append-only，updated_at 即版本生效时刻）。

数据影响评估（upgrade head @ petro@5433 演示库）：仅新增 retrieval_* 两表
（空表，种子经首次读取 ensure_seeded 自动落库——gateway_budget_config 单例
先例），不触碰任何既有表与数据；downgrade 只 drop retrieval_* 两表。

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-02

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    """建 retrieval 两表（99 §2.10 表序：版本表先建——指针表 FK 引用 version_no）。"""
    op.create_table(
        "retrieval_config_version",
        sa.Column("version_no", sa.String(length=16), nullable=False),
        sa.Column("config", _JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_by", sa.Text(), nullable=False),
        sa.Column("via", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("version_no"),
    )
    op.create_table(
        "retrieval_config",
        sa.Column("id", sa.String(length=16), nullable=False),
        sa.Column("current_version_no", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["current_version_no"], ["retrieval_config_version.version_no"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """drop retrieval 两表（本迁移所建；既有 ensure_* 表不追溯）。"""
    op.drop_table("retrieval_config")
    op.drop_table("retrieval_config_version")
