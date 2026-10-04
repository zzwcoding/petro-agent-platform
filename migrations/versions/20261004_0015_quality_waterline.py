"""E2 质检台 quality 表族＋water_line 水位表（DP-05：质检实体落库同源＋报水位）。

- 合同真源＝teach 99 册 §2.12 dataops 域 quality 六表（列形/键·索引/合同锚逐列对照；
  quality_* 表族归属**主平台库**——99 册＝主平台库 90 表清单，DP-05 同源裁决：
  数据面质检产出 report/quarantine 实体与主平台 E2 质检台读**同一批表**，不建第二份）；
  E2 册 v0.4/v0.5（行为约定 3/4/8/9）为落库语义的合同口径。
- 六表：
  * `quality_rule`——质检规则（20 条种子＋启停态；判据权威源＝本体仓 bohai 域 M3
    规则 RULE-BOHAI-*（E2 行为约定 9），种子文本按 E2 v0.5 冻结值——规则 1/5/6/11
    判据即 v0.4 本体对齐版（RULE-BOHAI-030/023/025/038），规则 2-12 锚 RULE-BOHAI-001
    ~008（设定书 §4 逐条编号对应），**规则 13-20 仅登记不实施**（v0.5——判据在提取件二
    仓内无全文，零发明；enabled=false 恒不参与执行，启停写口归主平台 E2 独占）；
  * `quality_task`——质检任务（＋合规报告 1:1，report jsonb 含 quarantined_rows/
    rejected_batches；数据面质检跑批写、M-05a/b 读——同源物理落点＝同表）；
  * `quality_issue`／`quality_issue_transition`——问题单五态状态机＋流转留痕
    （建单/流转归主平台 E2（M-05a）；本票只落结构承载同源，quarantine_row.issue_id
    FK 依本表）；
  * `quarantine_row`——隔离区（**append-only**：坏行 payload+rule_no+batch_id 落表
    永不改写，与湖表同教义；整批拒收落批次级记录；告警类规则不产生隔离行）；
  * `water_line`——三层数据新鲜度水位（原始/清洗层＝入湖管道回写、汇总层＝数据面
    agg 刷新水位——E2 行为约定 8；promise=T-1 常量，T-1 判定后端算归 E2 端点 8）。
- 写权限（DP-05 同源裁决，待 L0 确认疑点）：数据面限写账号只授 quality_task/
  quarantine_row/water_line 写权＋quality_rule 只读（启停＝主平台 E2 独写）——
  账号 SQL 模板在 data-plane 仓 migrations/quality_writer.sql（agg_writer.sql 同款
  纪律：部署批交付物不进迁移链）；本迁移只落结构＋种子、不建账号、不授权。
- 链上编排：文件编号沿用 DP-05 票面点名 0015；down_revision 接 0014（DP-04 已并）——
  单头线性链保持（99 册 §4.4 线性序列纪律）。

数据影响评估：全新六表（空表）＋quality_rule 20 行种子（INSERT ON CONFLICT DO NOTHING
幂等），零存量表触碰；downgrade 按依赖逆序删六表（种子随表删）——E2 质检台未上线
（M-05a/b 未施工），开发期 downgrade 无消费方。

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-04

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")

# 规则种子（E2 册 v0.5 冻结值照抄；判据权威源＝ontology/bohai/m3-rule-model.yaml——
# 每行尾注 M3 锚；13-20 仅登记不实施 enabled=false）。列序 (no, kind, rule, crit,
# action, autofix, enabled)。
_RULE_SEED: list[tuple[int, str, str, str, str, bool, bool]] = [
    (1, "重复",
     "同一口井同一天每个班次只能有一条日产记录——A/B 班手抄重复行即命中",
     "班次三元组（井,日,班次）唯一；重复/缺失行进问题单人工复核，不静默去重",
     "告警", False, True),  # RULE-BOHAI-030（v0.4：不静默去重，autoFix 撤出）
    (2, "缺失", "日产油量不许空着", "非空率 ≥ 99.5%", "隔离", False, True),  # RULE-BOHAI-003
    (3, "准不准",
     "产油单位要对：按区块密度折算后，密度须落在 0.82–0.98 t/m³——抓住\"吨方混写\"",
     "折算密度 ∈ [0.82, 0.98]", "隔离", False, True),  # RULE-BOHAI-001
    (4, "两本账打架", "含水率：生产日报（计量）vs 化验样，偏差不能太大",
     "偏差 ≤ 5 个百分点", "告警", False, True),  # RULE-BOHAI-002
    (5, "超范围",
     "含水率 0–100、开井小时数 0–24，越界即不合格（停井日开井小时数仍大于 0 的矛盾行："
     "标注出清单交业务核实，不归零不直改）",
     "越界即 fail；矛盾行清单制", "告警", False, True),  # RULE-BOHAI-023＋值域下沉 M1 refRules
    (6, "迟到",
     "检修台账补录窗口：超 T-5 不拒收（数据不丢是底线），收单转问题单闭环走特批核实"
     "——T-3 补录照收但留痕",
     "≤ T-5；超窗不拒收转问题单", "告警", False, True),  # RULE-BOHAI-025（T-1 拒收改 T-5 转单）
    (7, "写法不统一", "井号写法归一：N2 / N-2 都归成 N-02，归一表要全命中",
     "归一表全命中", "隔离", True, True),  # RULE-BOHAI-005（autoFix 白名单）
    (8, "写法不统一", "设备停机原因码要用新编码表：旧码 R3（皮带断）映射到新码 BELT，全表命中",
     "映射表全命中", "隔离", True, True),  # RULE-BOHAI-006（autoFix 白名单）
    (9, "重复 / 记账",
     "井档案一井一行，状态变更要有据可查：生产中→停产 必须有记录"
     "——N-11\"已停仍记生产中\"就是反例",
     "主键唯一＋迁移合法", "隔离", False, True),  # RULE-BOHAI-007
    (10, "假数嫌疑", "恒值检测：生产日报连续 30 天是同一个数——要么真停产、要么抄数，告警让人看",
     "连续 30 日同值 → 告警", "告警", False, True),  # RULE-BOHAI-004
    (11, "假数嫌疑",
     "传感器零值：当日批内电流全零即疑似设备/采集异常，出清单交业务核实（批面近似，无实时窗口）",
     "当日批内全零 → 告警", "告警", False, True),  # RULE-BOHAI-038（v0.4：批面近似）
    (12, "账对不上", "物质平衡账：区块月注入量 ≈ 产出量＋存水率变动，偏差大了说明有数不对",
     "偏差 ≤ 3%", "告警", False, True),  # RULE-BOHAI-008
    # —— 13-20 通用规则族：仅登记不实施（v0.5；判据在提取件二，零发明；总册占位值）
    (13, "引用完整", "引用的编号要能在关联的表里找到对应记录",
     "详见规则库总册", "—（总册）", False, False),
    (14, "跨表一致", "两张表记同一件事时，数字要对得上",
     "详见规则库总册", "—（总册）", False, False),
    (15, "枚举合法", "字段取值必须在约定清单里——只许从清单里选",
     "详见规则库总册", "—（总册）", False, False),
    (16, "正则格式", "有固定写法的字段（编号、日期）按格式校验",
     "详见规则库总册", "—（总册）", False, False),
    (17, "极值", "数值超出合理上下限即标出",
     "详见规则库总册", "—（总册）", False, False),
    (18, "波动率", "数值短期内突变即提示",
     "详见规则库总册", "—（总册）", False, False),
    (19, "钩稽", "几处本该相等的数互相核对",
     "详见规则库总册", "—（总册）", False, False),
    (20, "洗数规则", "清洗层的改数动作要有记录、可回查",
     "详见规则库总册", "—（总册）", False, False),
]


def upgrade() -> None:
    """建 quality 六表＋water_line（99 §2.12 列形；种子 20 条规则——幂等）。"""
    op.create_table(
        "quality_rule",
        sa.Column("no", sa.Integer(), nullable=False, comment="规则号（20 条；E2 DTO `no`）"),
        sa.Column("kind", sa.String(length=16), nullable=False,
                  comment="查什么分类（重复/缺失/…）"),
        sa.Column("rule", sa.String(length=512), nullable=False, comment="规则原文"),
        sa.Column("crit", sa.String(length=512), nullable=False,
                  comment="判据（权威源＝本体 M3 RULE-BOHAI-*）"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true"),
                  comment="启停态（停用＝任务跳过不删；写口＝主平台 E2 独占——数据面限写账号只读）"),
        sa.Column("action", sa.String(length=16), nullable=False,
                  comment="命中动作三档＋总册占位值（E2 冻结值）"),
        sa.Column("autofix", sa.Boolean(), nullable=False, server_default=sa.text("false"),
                  comment="安全类自动修复（v0.4 白名单收窄为规则 7/8；只作用派生层）"),
        sa.PrimaryKeyConstraint("no"),
        sa.CheckConstraint("action IN ('隔离','整批拒收','告警','—（总册）')",
                           name="ck_quality_rule_action"),
        comment="质检规则（20 条种子＋启停态）——99 册 §2.12/E2 端点 1/2；"
                "判据权威源＝ontology/bohai/m3-rule-model.yaml（E2 行为约定 9）；"
                "13-20 仅登记不实施（E2 v0.5）",
    )
    op.create_table(
        "quality_task",
        sa.Column("id", sa.String(length=32), nullable=False,
                  comment="任务号 QT-YYYYMMDD-NN（当日序号递增）"),
        sa.Column("status", sa.String(length=8), nullable=False, comment="running|done"),
        sa.Column("step", sa.SmallInteger(), nullable=True,
                  comment="四步流水进度（扫描→跑规则→建单→分发；数据面跑批完成至第 2 步"
                          "——建单/分发归 E2 接续）"),
        sa.Column("rules_count", sa.Integer(), nullable=True,
                  comment="启用规则数（E2 DTO 键 rules——rules_count 为存储侧命名）"),
        sa.Column("hits", sa.Integer(), nullable=True,
                  comment="命中数（单据粒度＝（规则＋对象＋数据日期）去重）"),
        sa.Column("report", _JSON, nullable=True,
                  comment="合规报告（任务 1:1；含 quarantined_rows/rejected_batches"
                          "——99 册合同键）"),
        sa.Column("time", sa.DateTime(), nullable=False,
                  comment="任务时刻（机器 timestamp；展示串读侧拼装）"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('running','done')", name="ck_quality_task_status"),
        comment="质检任务（＋合规报告 1:1）——99 册 §2.12/E2 端点 3-5；"
                "数据面质检跑批写、M-05a/b 读（同源：不建第二份）",
    )
    op.create_index("idx_quality_task_time_desc", "quality_task", [sa.text("time DESC")])

    op.create_table(
        "quality_issue",
        sa.Column("id", sa.String(length=32), nullable=False, comment="问题单号（E2 DTO `id`）"),
        sa.Column("lane", sa.SmallInteger(), nullable=False,
                  comment="五态 0-4：分发/认领/整改/复核/关闭"),
        sa.Column("rule_no", sa.Integer(), nullable=False, comment="关联规则号（E2 v0.3）"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default=sa.text("1"),
                  comment="命中次数（挂单去重键之一；>1 即有挂单，+1 不翻倍）"),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False,
                  comment="挂单去重键（规则＋对象＋数据日期——技术列 uq）"),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("desc", sa.String(length=1024), nullable=True,
                  comment="描述（SQL 保留字引号承载——同 0009 `group` 先例）"),
        sa.Column("owner", sa.String(length=128), nullable=True,
                  comment="责任岗展示文案（含环节前缀）"),
        sa.Column("ai_note", sa.String(length=1024), nullable=True,
                  comment="诊断说明（v0.5：V1＝规则判据说明服务端投影，存储恒可空；LLM 起草冻结）"),
        sa.Column("verify", _JSON, nullable=True,
                  comment="整改与复验 {batch, note}（复扫回填）"),
        sa.Column("close_note", sa.String(length=1024), nullable=True,
                  comment="不经修正的关闭原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["rule_no"], ["quality_rule.no"], name="fk_quality_issue_rule"),
        sa.UniqueConstraint("dedupe_key", name="uq_quality_issue_dedupe_key"),
        sa.CheckConstraint("lane BETWEEN 0 AND 4", name="ck_quality_issue_lane"),
        comment="问题单（五态状态机）——99 册 §2.12/E2 端点 6/7；建单/流转归主平台 E2（M-05a）",
    )
    op.create_index("idx_quality_issue_rule_no", "quality_issue", ["rule_no"])
    op.create_index("idx_quality_issue_lane", "quality_issue", ["lane"])

    op.create_table(
        "quality_issue_transition",
        sa.Column("issue_id", sa.String(length=32), nullable=False, comment="问题单号 FK"),
        sa.Column("seq", sa.Integer(), nullable=False, comment="流转序号"),
        sa.Column("from_lane", sa.SmallInteger(), nullable=True, comment="流转前态"),
        sa.Column("to_lane", sa.SmallInteger(), nullable=True, comment="流转后态"),
        sa.Column("operator", sa.String(length=64), nullable=True, comment="操作人"),
        sa.Column("time", sa.DateTime(), nullable=False, comment="流转时刻"),
        sa.PrimaryKeyConstraint("issue_id", "seq"),
        sa.ForeignKeyConstraint(["issue_id"], ["quality_issue.id"],
                                name="fk_quality_issue_transition_issue"),
        comment="问题单流转留痕（操作人/时间/前后态——与 A3 审计同口径）——99 册 §2.12/E2 端点 7",
    )

    op.create_table(
        "quarantine_row",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True,
                  comment="行号（bigserial）"),
        sa.Column("batch_id", sa.String(length=64), nullable=False,
                  comment="批次寻址（质检任务＝QT-*；湖进料批＝b-*——append-only 可追溯键）"),
        sa.Column("rule_no", sa.Integer(), nullable=False, comment="命中规则号 FK"),
        sa.Column("action", sa.String(length=16), nullable=False,
                  comment="隔离|整批拒收（整批拒收落批次级记录；告警类不产生隔离行）"),
        sa.Column("loc", sa.String(length=256), nullable=True,
                  comment="位置（如 生产日报 · N-02 · 2026-09-14）"),
        sa.Column("payload", _JSON, nullable=False, comment="原始坏行（as-is 落库，永不改写）"),
        sa.Column("issue_id", sa.String(length=32), nullable=True,
                  comment="关联问题单（建单后回挂——M-05a 写）"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["rule_no"], ["quality_rule.no"], name="fk_quarantine_row_rule"),
        sa.ForeignKeyConstraint(["issue_id"], ["quality_issue.id"],
                                name="fk_quarantine_row_issue"),
        sa.CheckConstraint("action IN ('隔离','整批拒收')", name="ck_quarantine_row_action"),
        comment="隔离区（append-only：坏行 payload+rule_no+batch_id 落表永不改写，与湖表同教义）"
                "——99 册 §2.12/E2 端点 9；数据面限写账号仅 INSERT"
                "（无 UPDATE/DELETE——账号级 append-only）",
    )
    op.create_index("idx_quarantine_row_batch_id", "quarantine_row", ["batch_id"])
    op.create_index("idx_quarantine_row_rule_no", "quarantine_row", ["rule_no"])
    op.create_index("idx_quarantine_row_issue_id", "quarantine_row", ["issue_id"])

    op.create_table(
        "water_line",
        sa.Column("layer", sa.String(length=8), nullable=False,
                  comment="三 tier：原始层|清洗层|汇总层"),
        sa.Column("data_date", sa.Date(), nullable=False,
                  comment="数据已到业务日期（原始/清洗层＝入湖水位，汇总层＝agg 刷新水位"
                          "——E2 行为约定 8）"),
        sa.Column("promise", sa.String(length=8), nullable=False, server_default=sa.text("'T-1'"),
                  comment="承诺水位（T-1 常量；达标/落后判定后端算归 E2 端点 8）"),
        sa.Column("refreshed_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"),
                  comment="水位刷新时刻"),
        sa.PrimaryKeyConstraint("layer"),
        sa.CheckConstraint("layer IN ('原始层','清洗层','汇总层')", name="ck_water_line_layer"),
        comment="三层数据新鲜度水位——99 册 §2.12/E2 端点 8；数据面进料/agg 刷新回写"
                "（限写账号 INSERT+UPDATE）",
    )

    # 规则种子（20 条；幂等——重放不翻倍；M3 锚见 _RULE_SEED 行尾注；绑定参数执行）
    seed = sa.text(
        "INSERT INTO quality_rule (no, kind, rule, crit, enabled, action, autofix) "
        "VALUES (:no, :kind, :rule, :crit, :enabled, :action, :autofix) "
        "ON CONFLICT (no) DO NOTHING")
    bind = op.get_bind()
    for no, kind, rule, crit, action, autofix, enabled in _RULE_SEED:
        bind.execute(seed, {"no": no, "kind": kind, "rule": rule, "crit": crit,
                            "enabled": enabled, "action": action, "autofix": autofix})


def downgrade() -> None:
    """按依赖逆序删六表（种子随表删；E2 质检台未上线，开发期无消费方）。"""
    op.drop_index("idx_quarantine_row_issue_id", table_name="quarantine_row")
    op.drop_index("idx_quarantine_row_rule_no", table_name="quarantine_row")
    op.drop_index("idx_quarantine_row_batch_id", table_name="quarantine_row")
    op.drop_table("quarantine_row")
    op.drop_table("quality_issue_transition")
    op.drop_index("idx_quality_issue_lane", table_name="quality_issue")
    op.drop_index("idx_quality_issue_rule_no", table_name="quality_issue")
    op.drop_table("quality_issue")
    op.drop_index("idx_quality_task_time_desc", table_name="quality_task")
    op.drop_table("quality_task")
    op.drop_table("water_line")
    op.drop_table("quality_rule")
