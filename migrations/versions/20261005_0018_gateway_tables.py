"""gateway 表族迁移补建（DEP-01 部署准备批）——网关三表入版本轴。

- 来源：0016 全新库实跑发现的迁移缺口（P2-04.fix 偏差 2／P2-04.close 挂账）——
  gateway 三表自 P0-05 起走 ``ensure_gateway_tables``（main.py lifespan 幂等
  checkfirst 建表，app/domains/gateway/store.py），从未进迁移链；纯 Alembic
  供应的全新库断链于 0011（ALTER/索引落在 ensure-only 表上）。本迁移即该
  挂账的收口，也是 **0011 docstring 双轨前提的收敛**：0011 头注「ensure 先建
  的库再跑迁移不冲突」的前提由本迁移终结——迁移链自身供给表结构，ensure
  降级为应用启动侧的幂等兜底（两者 IF NOT EXISTS 同形并存，操作序不再敏感）。
- 表结构照 ORM 声明逐列落 DDL（真源＝app/domains/gateway/store.py 三模型：
  SpendRecord/DrillRun/BudgetConfigRow，99 册 §2.13）——无 server default
  （ORM default 均为 Python 侧默认，DDL 与 ensure 直建完全同形）；语义注释
  随 COMMENT 落库。pg_trgm 扩展与 id/note trgm GIN 索引仍归 0011（链上位于
  本迁移之后，fresh 链执行序 0018→0011 天然满足其表存在前提）。
- 链位编排：down_revision=**0010**（插在 0011 之前，0011 的 down_revision
  同批改指 0018）——**Alembic 按链不按文件名序**（0016→0014→0015→0017 先
  例，DP-04 偏差 1 同款备案）；若按文件名序挂尾（down_revision=0017），
  全新库仍断链于 0011，本票验收「全新库全链 0001→0018 upgrade head 成功」
  不可达。upgrade 全部 IF NOT EXISTS 幂等：ensure 先建的既有库再跑本迁移
  零冲突、零改写（列形一致性由既有行零触碰保证）。
- downgrade：drop 三基索引＋三表（不撤 pg_trgm 扩展——库级资产，0010/0011
  同惯例；trgm 两索引归 0011 的 downgrade 撤）。ensure 建表的既有库 downgrade
  本迁移同样删三表——迁移轴接管后回滚语义以链为准（应用启动侧 ensure 会在
  下次启动重建，不丢数据语义：账本/演练/预算行随表删，回滚前须人工确认）。

数据影响评估：全新库＝新建三表＋三索引，零存量；既有库（ensure 已建）＝
全部 IF NOT EXISTS 跳过，零触碰、零回填；downgrade 删三表＝花费账本/演练
历史/预算单例行丢弃（D5 账本唯一真源——生产回滚前必须先评估账本留存）。

Revision ID: 0018
Revises: 0010
Create Date: 2026-10-05

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 列注释（99 §2.13／ORM inline 注释同文——COMMENT 幂等，重复执行只覆盖）。
_COMMENTS: list[tuple[str, str, str]] = [
    ("gateway_spend_record", "id", "调用号（call- 机器短 id，主键）"),
    ("gateway_spend_record", "time", "调用时刻（账本排序键——读面恒 time 倒序，D1 合同）"),
    ("gateway_spend_record", "model_key", "模型槽位（main | backup）"),
    ("gateway_spend_record", "alias", "模型别名（models.yaml 路由别名）"),
    ("gateway_spend_record", "input_tokens", "输入 token 数"),
    ("gateway_spend_record", "output_tokens", "输出 token 数"),
    ("gateway_spend_record", "first_ms", "首字延迟 ms"),
    ("gateway_spend_record", "total_ms", "总耗时 ms"),
    ("gateway_spend_record", "cost_yuan", "本次花费（元，NUMERIC(12,6)——99 §2.13）"),
    ("gateway_spend_record", "fallback", "是否发生主备切换"),
    ("gateway_spend_record", "note", "备注（spend-logs keyword 检索列之一）"),
    ("gateway_spend_record", "caller", "调用方归因（D1 v0.2——枚举不封闭，空值归 unattributed）"),
    ("gateway_spend_record", "run_id", "run 聚合投影锚（D5——将来只做 run 聚合投影）"),
    ("gateway_spend_record", "served_model", "切换留痕：实际部署"),
    ("gateway_spend_record", "attempted_fallbacks", "切换留痕：失败部署序（jsonb 数组）"),
    ("gateway_spend_record", "created_at", "落账时刻"),
    ("gateway_spend_record", "updated_at", "更新时刻"),
    ("gateway_drill_run", "id", "演练任务号（drill- 机器短 id，主键）"),
    ("gateway_drill_run", "status", "双态 running|done（00 §5——CHECK 约束承载）"),
    ("gateway_drill_run", "nodes", "演练节点序列（jsonb）"),
    ("gateway_drill_run", "result", "演练结果（jsonb，可空）"),
    ("gateway_drill_run", "summary", "人话摘要（done 后回填；僵尸收口亦写）"),
    ("gateway_drill_run", "started_at", "受理时刻"),
    ("gateway_drill_run", "finished_at", "完成时刻（可空——running 期间）"),
    ("gateway_drill_run", "created_at", "创建时刻"),
    ("gateway_drill_run", "updated_at", "更新时刻"),
    ("gateway_budget_config", "id", "单例行主键（恒 ''singleton''）"),
    ("gateway_budget_config", "per_call_cost_limit_yuan", "单次调用花费阈值（元）"),
    ("gateway_budget_config", "gateway_budget_yuan_per_month", "月度网关预算（元）"),
    ("gateway_budget_config", "created_at", "创建时刻"),
    ("gateway_budget_config", "updated_at", "更新时刻"),
]

_TABLE_COMMENTS: list[tuple[str, str]] = [
    ("gateway_spend_record", "网关花费账本（全平台唯一——D5 裁决一「不建第二份账本」；99 §2.13）"),
    ("gateway_drill_run", "网关故障演练任务（00 §5 双态 running|done；99 §2.13）"),
    ("gateway_budget_config", "花费双阈值单例行（判据消费方＝gateway complete；99 §2.13）"),
]


def upgrade() -> None:
    """三表＋三基索引（全部 IF NOT EXISTS——与 ensure_gateway_tables 幂等并存）。"""
    op.execute("""
        CREATE TABLE IF NOT EXISTS gateway_spend_record (
            "id" VARCHAR(32) NOT NULL,
            "time" TIMESTAMP NOT NULL,
            "model_key" VARCHAR(16) NOT NULL,
            "alias" VARCHAR(64) NOT NULL,
            "input_tokens" INTEGER NOT NULL,
            "output_tokens" INTEGER NOT NULL,
            "first_ms" INTEGER NOT NULL,
            "total_ms" INTEGER NOT NULL,
            "cost_yuan" NUMERIC(12, 6) NOT NULL,
            "fallback" BOOLEAN NOT NULL,
            "note" TEXT NOT NULL,
            "caller" VARCHAR(64),
            "run_id" VARCHAR(32),
            "served_model" TEXT,
            "attempted_fallbacks" JSONB,
            "created_at" TIMESTAMP NOT NULL,
            "updated_at" TIMESTAMP NOT NULL,
            PRIMARY KEY ("id")
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gateway_spend_time_desc "
        'ON gateway_spend_record ("time" DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gateway_spend_model_time "
        'ON gateway_spend_record ("model_key", "time" DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_gateway_spend_run "
        'ON gateway_spend_record ("run_id")'
    )
    op.execute("""
        CREATE TABLE IF NOT EXISTS gateway_drill_run (
            "id" VARCHAR(32) NOT NULL,
            "status" VARCHAR(16) NOT NULL,
            "nodes" JSONB NOT NULL,
            "result" JSONB,
            "summary" TEXT,
            "started_at" TIMESTAMP NOT NULL,
            "finished_at" TIMESTAMP,
            "created_at" TIMESTAMP NOT NULL,
            "updated_at" TIMESTAMP NOT NULL,
            PRIMARY KEY ("id"),
            CONSTRAINT ck_drill_status CHECK (status IN ('running', 'done'))
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS gateway_budget_config (
            "id" VARCHAR(16) NOT NULL,
            "per_call_cost_limit_yuan" NUMERIC(12, 6) NOT NULL,
            "gateway_budget_yuan_per_month" NUMERIC(12, 6) NOT NULL,
            "created_at" TIMESTAMP NOT NULL,
            "updated_at" TIMESTAMP NOT NULL,
            PRIMARY KEY ("id")
        )
    """)
    for table, comment in _TABLE_COMMENTS:
        op.execute(f"COMMENT ON TABLE {table} IS '{comment}'")
    for table, column, comment in _COMMENTS:
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS '{comment}'")


def downgrade() -> None:
    """drop 三基索引＋三表（trgm 两索引与 pg_trgm 扩展归 0011 的 downgrade）。"""
    for index_name in (
        "ix_gateway_spend_run",
        "ix_gateway_spend_model_time",
        "ix_gateway_spend_time_desc",
    ):
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    op.execute("DROP TABLE IF EXISTS gateway_budget_config")
    op.execute("DROP TABLE IF EXISTS gateway_drill_run")
    op.execute("DROP TABLE IF EXISTS gateway_spend_record")
