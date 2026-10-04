"""agg 汇总层星型读模型三表（DP-04：数据面直写主平台库——ADR-0003 裁决 15）。

- 合同真源＝teach 99 册 §2.12 末行（D6 star_model 合同值）：
  * `agg.dim_well`——井维度（well_id PK＋区块/油田层级属性列；物理列名沿源口径 §A.1）；
  * `agg.dim_date`——日期维度（date PK＋月/季对照列；**数据面自建**——自 calendar 确定性
    生成，无业务发明〔DP-04 票面 Owner 方针〕）；
  * `agg.fct_daily_metering`——事实表（grain＝一井×一天：组合 PK well_id+prod_date 承载；
    oil_output/liquid_output/oil_pressure numeric 沿源口径 §A.2；batch_id＝批次水位；
    quality_flag＝质检状态标记——99 册合同列但值域无冻结枚举，列恒可空，值域随质检实体
    落库批对齐）；idx (prod_date)（99 册合同索引）；机器名＝A1 解释链②冻结，
    A1 问数链 SELECT 唯一落点（M-01 问数链消费归 Wave 2，本票只落结构）。
- 写权限＝数据面限写三表专用账号（99 册 §2.12/§4.4：账号建立随数据面部署批；账号 SQL
  模板在 data-plane 仓 migrations/agg_writer.sql）——本迁移只落结构、不建账号、不授权。
- 替换对象＝数据面 v2 的 parquet marts 三模型（fct_block_monthly/fct_valid_output_monthly/
  fct_wellset_annual——模型名/粒度与 99 册不符，DP-04 票面盘点 v2 差距 3）；随 DP-04
  数据面侧退役删除，问数读模型以本迁移三表为准。
- 链上编排：文件编号沿用 DP-04 票面点名 0014；down_revision 接 0016（P2-04 修复拍已占
  0013→0016 段、编号跳 0014/0015 备案见 P2-04 fix 回报偏差 2）——Alembic 按链不按文件名
  序，单头线性链保持（99 册 §4.4 线性序列纪律）。

数据影响评估：全新 agg schema＋三张新表，零存量表触碰（agg 三表为 99 册 §2.12 已注册的
汇总层读模型，随数据面部署批物理落位）；downgrade 删三表＋schema——
读模型＝加工产物可重建，删除不损真源（raw 层 as-is 数据在中台库不受影响）；生产环境
downgrade 前需确认无问数链在读（M-01 Wave 2 未接线，开发期安全）。

Revision ID: 0014
Revises: 0016
Create Date: 2026-10-04

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """建 agg schema＋星型三表（99 册 §2.12 列形；幂等 IF NOT EXISTS——湖先 boot 不炸同款纪律）。"""
    op.execute("CREATE SCHEMA IF NOT EXISTS agg")
    op.execute("COMMENT ON SCHEMA agg IS "
               "'汇总层问数读模型（数据面 dp 系管道直写——限写三表专用账号；99 册 §2.12/§4.4）'")

    op.execute("""
        CREATE TABLE IF NOT EXISTS agg.dim_well (
            well_id    VARCHAR(8)  NOT NULL,
            block_name VARCHAR(16),
            field_name VARCHAR(32),
            PRIMARY KEY (well_id)
        )
    """)
    op.execute("COMMENT ON TABLE agg.dim_well IS "
               "'汇总层井维度（well_id PK＋区块/油田层级属性列）——99 册 §2.12/D6 star_model；"
               "物理列名沿源口径（设定书 §A.1）'")
    op.execute("COMMENT ON COLUMN agg.dim_well.block_name IS "
               "'区块（层级属性；源口径 block_name，设定书 §A.1）'")
    op.execute("COMMENT ON COLUMN agg.dim_well.field_name IS "
               "'油田（层级属性；源口径 field_name，设定书 §A.1）'")

    op.execute("""
        CREATE TABLE IF NOT EXISTS agg.dim_date (
            date    DATE       NOT NULL,
            month   VARCHAR(7) NOT NULL,
            quarter VARCHAR(7) NOT NULL,
            PRIMARY KEY (date)
        )
    """)
    op.execute("COMMENT ON TABLE agg.dim_date IS "
               "'汇总层日期维度（date PK＋月/季对照列 month=YYYY-MM/quarter=YYYY-Q#；"
               "数据面自建——calendar 确定性生成无业务发明）——99 册 §2.12'")

    op.execute("""
        CREATE TABLE IF NOT EXISTS agg.fct_daily_metering (
            well_id       VARCHAR(8)   NOT NULL,
            prod_date     DATE         NOT NULL,
            oil_output    NUMERIC(10,2),
            liquid_output NUMERIC(10,2),
            oil_pressure  NUMERIC(6,2),
            batch_id      VARCHAR(64),
            quality_flag  VARCHAR(16),
            PRIMARY KEY (well_id, prod_date)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agg_fct_prod_date "
               "ON agg.fct_daily_metering (prod_date)")
    op.execute("COMMENT ON TABLE agg.fct_daily_metering IS "
               "'汇总层日产计量事实（grain=一井×一天，组合 PK well_id+prod_date；"
               "A1 问数链 SELECT 唯一落点，机器名=解释链②冻结）——99 册 §2.12/D6 star_model；"
               "物理列名沿源口径（设定书 §A.2）'")
    op.execute("COMMENT ON COLUMN agg.fct_daily_metering.batch_id IS "
               "'批次水位（进料/加工批次寻址，随行溯源）——99 册 §2.12'")
    op.execute("COMMENT ON COLUMN agg.fct_daily_metering.quality_flag IS "
               "'质检状态标记（99 册合同列；值域无冻结枚举——数据面管道暂写 NULL，"
               "值域随质检实体落库批对齐）'")


def downgrade() -> None:
    """删三表＋schema（读模型＝加工产物可重建；生产 downgrade 前确认无问数链在读）。"""
    op.execute("DROP INDEX IF EXISTS agg.idx_agg_fct_prod_date")
    op.execute("DROP TABLE IF EXISTS agg.fct_daily_metering")
    op.execute("DROP TABLE IF EXISTS agg.dim_date")
    op.execute("DROP TABLE IF EXISTS agg.dim_well")
    op.execute("DROP SCHEMA IF EXISTS agg")
