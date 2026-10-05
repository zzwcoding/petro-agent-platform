"""S-01 语义台账投影种子——本体 bohai glossary/M1 → sem_term/sem_metric（＋版本轴配套）。

- 修的缺口：sem_* 九表全空——N7.1 问数链「指标槽位未命中可出数的注册声明」
  恒降级、检索链 S3 词表级与词条卡（P1F-02）无台账行可命中（Owner 拍板
  2026-10-05「台账种子从本体导入」＋依赖地图第 0 层；先例＝DP-05 quality_rule
  ←本体 M3 投影 0015）。
- 消费面核实结论（本票施工方案第 1 步——种子形状逐字段对齐依据）：
  * 指标声明运行时消费＝**DB 表 sem_metric**：app/main.py metrics_loader →
    SemanticsService.list_metrics 公开读口（B5）→ 装配层路 2 指标卡台账 →
    chains._metric_card_for_plan 按 slot_name 查 MEASURE_COLUMNS；
  * 计量列绑定＝**代码注册面**（app/domains/chat/domain.py MEASURE_COLUMNS，
    M-06 冻结：日产油量→oil_output／日产液量→liquid_output／油压→oil_pressure）
    ——种子行 slot_name 必须与键逐字一致才出数；未绑定行（含水率/配产量）
    照链体设计走降级解释链如实标注，不冒充审定口径；
  * 术语运行时消费＝**DB 表 sem_term**：main.py terms_loader → list_terms →
    装配层路 3 术语台账＋词条卡一等材料（P1F-02）；
  * 配套行实况（app/domains/semantics/store.py）：台账行变更一律随
    sem_ledger_revision 行版本轴留痕（ADR-0004——latest_row_version 消费面），
    本迁移逐行落 v1 revision（payload＝全行快照、基线列除外，与同步器
    _row_dict/_json_safe 口径同形）；sem_version 不插（无运行时消费方强制；
    版本推进只归治理链发布事务 C3——store.SemVersion docstring）。
- 种子内容（权威源＝ontology/bohai/，只读投影；「种子与本体权威定义逐字对照」
  为 T1 审查项）：
  * sem_metric 5 条＝M1 AGG-BOHAI-002 日产计量五计量属性（fieldforge 数据
    覆盖面；名称照抄 M1 label、slot_name＝剥法纯名 metric_slot_name；票面简称
    「产液量/计划产量」对应本体 label「日产液量（方）/配产量（吨）」——种子
    从本体不从票面简称）：日产油量（oil_output）／日产液量（liquid_output）／
    含水率（water_cut）／油压（oil_pressure）／配产量（plan_output）；绑定依据
    99 册 §2.12＋§A.2 源口径——含水率/配产量的源列在湖表 oil_production_daily
    在案、但 agg 星型读模型未落该两列（§2.12 事实表仅三计量列），故台账照登、
    出数绑定缺位如实注记（链体降级解释链兜住，不假绑定）；
  * sem_term 6 条＝glossary-model.yaml 报告域相关核心词：躺井／剔检产量／
    有效产量／时率／递减增油／存水率。票面点名词考据：躺井＝GLS-BOHAI-004
    正条；「检泵」＝检泵周期指标域词（M3 RULE-BOHAI-016）、非 GLS 独立词条；
    「限作业区」＝躺井 status 语境串；「停产待检泵」＝躺井 aliases[0]；
    「洗井」GLS 无此条——零发明不建（纪律 7）。
- id 段位（技术键位，非业务事实）：bohai 种子占 200+（指标 201~205／术语
  211~216）——与本体仓同步器投影键空间（app/domains/semantics/domain.py
  petro 种子：指标 1~15／术语 1~11，upsert 主键即 id）显式隔离防互踩。
- 幂等：INSERT … ON CONFLICT DO NOTHING（0015 先例同款——重放不翻倍）；
  downgrade 只删本票种子行（台账 11 行＋版本轴 11 行），不删表、不碰结构。
- 链上编排：down_revision 接 0017（单头线性链纪律，99 §4.4）。
- 数据影响评估：九表现存空表 INSERT 22 行（11 台账＋11 版本轴）；零存量表
  触碰、零列变更；downgrade 删该 22 行复原空表态——ledger 行消费方（问数链
  N7.1/检索链 S3/词条卡/C1 读面）随 downgrade 回到「未命中」态。

Revision ID: 0019
Revises: 0017
Create Date: 2026-10-05

"""
from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from alembic import op
from sqlalchemy import text

revision: str = "0019"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 种子行投影身份（sem_ledger_revision.changed_by——who 槽；同步器身份同槽惯例）。
_CHANGED_BY = "migrations-0019（S-01 本体种子投影——fix/s-01-sem-ledger-seed）"

# ---------- sem_metric 种子（5 条——M1 AGG-BOHAI-002 日产计量五计量属性） ----------
# 列序 (id, name, slot_name, def, grain, unit, status, owner, source, dispute,
#        modifiers, ambiguous, calibers, default_caliber)。
# 每行尾注本体锚（照 0015 RULE-BOHAI- 锚定格式）：M1 属性锚＋绑定依据
# （99 册 §2.12 agg 读模型列／§A.2 源口径）。owner 本体无承载位（M5 角色映射
# 未建指标级）——记「语义 Owner（待落）」如实标注，不发明业务岗。
# 口径声明（calibers）：血缘卡①口径行消费面（chains._metric_card_for_plan 取
# name 串）——名字集从 M1 裁决注记投影，零发明。
_MetricSeed = tuple[
    int, str, str, str, str, str, list[str], str, str, str | None,
    list[dict[str, Any]] | None, bool, list[dict[str, Any]], str,
]
_METRIC_SEEDS: list[_MetricSeed] = [
    (201, "日产油量（吨）", "日产油量",
     "日产计量的日产油量——源 oil_production_daily.oil_output（R5·A.2，行粒度＝班次、"
     "日口径＝同井同日各班合计，PROP-BOHAI-007=A）；agg 读模型绑定列 "
     "agg.fct_daily_metering.oil_output（99 §2.12）",
     "日/井", "吨", ["生效中"], "语义 Owner（待落）",
     "ontology/bohai/m1-object-model.yaml AGG-BOHAI-002.oilOutput（R5·A.2）",
     "吨方混写脏值（D1——RULE-BOHAI-020 检出位已建）", None, False,
     [{"key": "A", "name": "班次合计日口径", "default": True,
       "desc": "行粒度＝班次，日口径＝同井同日各班合计（AGG-BOHAI-002 · "
               "PROP-BOHAI-007=A）；绑定 agg.fct_daily_metering.oil_output（99 §2.12）"}],
     "A"),  # M1 oilOutput→agg.oil_output（MEASURE_COLUMNS 键「日产油量」）
    (202, "日产液量（方）", "日产液量",
     "日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；"
     "agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12）",
     "日/井", "方", ["生效中"], "语义 Owner（待落）",
     "ontology/bohai/m1-object-model.yaml AGG-BOHAI-002.liquidOutput（R5·A.2）",
     None, None, False,
     [{"key": "A", "name": "班次合计日口径", "default": True,
       "desc": "行粒度＝班次，日口径＝同井同日各班合计（AGG-BOHAI-002 · "
               "PROP-BOHAI-007=A）；绑定 agg.fct_daily_metering.liquid_output（99 §2.12）"}],
     "A"),  # M1 liquidOutput→agg.liquid_output（MEASURE_COLUMNS 键「日产液量」）
    (203, "含水率（%）", "含水率",
     "日产计量化验折算含水率——日度监控口径；月度/正式指标以流体化验实测为准、"
     "偏差 >5pp 以化验校正（PROP-BOHAI-008=C 并存分场景）；源 "
     "oil_production_daily.water_cut（R5·A.2）——agg 读模型未落该列（99 §2.12 "
     "事实表仅三计量列），暂不可出数",
     "日/井", "%", ["生效中"], "语义 Owner（待落）",
     "ontology/bohai/m1-object-model.yaml AGG-BOHAI-002.waterCut（R5·A.2）",
     "化验 vs 计量打架（并存分场景已裁——PROP-BOHAI-008=C）", None, False,
     [{"key": "A", "name": "计量折算（日度监控）", "default": True,
       "desc": "oil_production_daily.water_cut 化验折算；与化验偏差 >5pp 以化验"
               "校正（RULE-BOHAI-002 容差）"},
      {"key": "B", "name": "化验实测（月度/正式）", "default": False,
       "desc": "fluid_test.water_cut_lab（AGG-BOHAI-006）——月度/正式指标权威源"
               "（PROP-BOHAI-008=C）"}],
     "A"),  # M1 waterCut（化验实测支锚 AGG-BOHAI-006.waterCutLab）——无 agg 绑定列
    (204, "配产量（吨）", "配产量",
     "日产计量的配产量——源 oil_production_daily.plan_output（R5·A.2）；"
     "agg 读模型未落该列（99 §2.12），暂不可出数",
     "日/井", "吨", ["生效中"], "语义 Owner（待落）",
     "ontology/bohai/m1-object-model.yaml AGG-BOHAI-002.planOutput（R5·A.2）",
     "配产版本切换日双值行（D4 待 Owner）", None, False,
     [{"key": "A", "name": "配产版本当日值", "default": True,
       "desc": "plan_output 当日配产（配产版本切换日双值行 D4 待 Owner）；"
               "agg 未落列——暂不可出数"}],
     "A"),  # M1 planOutput→源列 plan_output（票面简称「计划产量」）——无 agg 绑定列
    (205, "油压（MPa）", "油压",
     "日产计量的油压——源 oil_production_daily.oil_pressure（R5·A.2）；"
     "agg 读模型绑定列 agg.fct_daily_metering.oil_pressure（99 §2.12）",
     "日/井", "MPa", ["生效中"], "语义 Owner（待落）",
     "ontology/bohai/m1-object-model.yaml AGG-BOHAI-002.oilPressure（R5·A.2）",
     None, None, False,
     [{"key": "A", "name": "计量直取日值", "default": True,
       "desc": "oil_production_daily.oil_pressure（MPa）；绑定 "
               "agg.fct_daily_metering.oil_pressure（99 §2.12）"}],
     "A"),  # M1 oilPressure→agg.oil_pressure（MEASURE_COLUMNS 键「油压」）
]

# ---------- sem_term 种子（6 条——glossary-model.yaml 报告域相关核心词） ----------
# 列序 (id, term, type, def, status, status_key, owner, source, expires_at)。
# term/definition/status/owner 照抄 GLS 权威定义（逐字对照）；type＝termType+
# aliases 展示拼装（对齐矩阵 §2.1「可逆投影」口径）；expires_at＝GLS 无承载
# （对齐矩阵裁决项 g）——NULL 不发明演示日期；source 注 GLS 元素锚。
_TERM_SEEDS: list[tuple[int, str, str, str, str, str, str, str]] = [
    (211, "躺井", "黑话 → 停产待检泵",
     "作业区口语，指停产待检泵的井（及该检修事件）。",
     "有效（限作业区语境）", "有效（限作业区语境）", "采油工艺所",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-004（R5·设定书 §6）"),  # aliases[0]=停产待检泵
    (212, "剔检产量", "别名 → 净产量",
     "剔除检修井口径的产量（即净产量）。",
     "有效", "有效", "开发室",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-002（R5·设定书 §6）"),  # aliases[0]=净产量
    (213, "有效产量", "一词两译",
     "需修饰词消歧的产量词：开井日历支 / 剔检支，两支口径并列，单说「有效产量」必须追问修饰词。",
     "有效", "有效", "开发室",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-003（R5·设定书 §6）"),
    (214, "时率", "缩写 → 抽油机时率",
     "「抽油机时率」的缩写；= Σ开井时长/Σ日历时长×100（见指标 14）。",
     "有效", "有效", "采油工艺所",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-005（R5·设定书 §6）"),  # aliases[0]=抽油机时率
    (215, "递减增油", "术语",
     "措施后增产油量=（实际产量−递减基线产量）×劈分系数；基线 q₀(1−dₐ)^t 拟合参数"
     "设定书未给。含口径争议注记：事故 7「一数多源」争议、待联席裁决。",
     "有效（待联席裁决）", "有效（待联席裁决）", "采油工艺所",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-007（R5·设定书 §6）"),
    (216, "存水率", "术语",
     "注入水留存地层比例（物质平衡用）。",
     "有效", "有效", "开发室",
     "ontology/bohai/glossary-model.yaml GLS-BOHAI-008（R5·设定书 §6）"),
]

# 版本轴 payload 键序＝同步器 _row_dict 口径（基线列 created_at/updated_at 除外；
# def 列名照 99 §2.8）——将来同步器幂等比对同形。
_METRIC_PAYLOAD_KEYS = (
    "id", "name", "mark", "slot_name", "def", "grain", "unit", "status", "owner",
    "source", "dispute", "modifiers", "ambiguous", "calibers", "default_caliber",
    "version",
)
_TERM_PAYLOAD_KEYS = (
    "id", "term", "type", "def", "status", "status_key", "owner", "source",
    "version", "expires_at",
)

_SEED_VERSION = 1  # 首投影 v1（latest_row_version 消费面：无 revision 行＝0）


def _metric_payload(row: tuple[Any, ...]) -> dict[str, Any]:
    (seed_id, name, slot, def_, grain, unit, status, owner, source, dispute,
     modifiers, ambiguous, calibers, default_caliber) = row
    return {
        "id": seed_id, "name": name, "mark": None, "slot_name": slot, "def": def_,
        "grain": grain, "unit": unit, "status": status, "owner": owner,
        "source": source, "dispute": dispute, "modifiers": modifiers,
        "ambiguous": ambiguous, "calibers": calibers,
        "default_caliber": default_caliber, "version": _SEED_VERSION,
    }


def _term_payload(row: tuple[Any, ...]) -> dict[str, Any]:
    (seed_id, term, type_, def_, status, status_key, owner, source) = row
    return {
        "id": seed_id, "term": term, "type": type_, "def": def_, "status": status,
        "status_key": status_key, "owner": owner, "source": source,
        "version": _SEED_VERSION, "expires_at": None,
    }


def upgrade() -> None:
    """种子落库（幂等——ON CONFLICT DO NOTHING）：11 台账行＋11 版本轴行。"""
    bind = op.get_bind()
    metric_stmt = text(
        "INSERT INTO sem_metric (id, name, mark, slot_name, \"def\", grain, unit, "
        "status, owner, source, dispute, modifiers, ambiguous, calibers, "
        "default_caliber, version, created_at, updated_at) "
        "VALUES (:id, :name, :mark, :slot_name, :def, :grain, :unit, "
        "CAST(:status AS jsonb), :owner, :source, :dispute, "
        "CAST(:modifiers AS jsonb), :ambiguous, CAST(:calibers AS jsonb), "
        ":default_caliber, :version, now(), now()) "
        "ON CONFLICT (id) DO NOTHING"
    )
    for row in _METRIC_SEEDS:
        payload = _metric_payload(row)
        bind.execute(metric_stmt, {
            "id": payload["id"], "name": payload["name"], "mark": payload["mark"],
            "slot_name": payload["slot_name"], "def": payload["def"],
            "grain": payload["grain"], "unit": payload["unit"],
            "status": json.dumps(payload["status"], ensure_ascii=False),
            "owner": payload["owner"], "source": payload["source"],
            "dispute": payload["dispute"],
            "modifiers": (
                json.dumps(payload["modifiers"], ensure_ascii=False)
                if payload["modifiers"] is not None else None
            ),
            "ambiguous": payload["ambiguous"],
            "calibers": json.dumps(payload["calibers"], ensure_ascii=False),
            "default_caliber": payload["default_caliber"],
            "version": payload["version"],
        })
    term_stmt = text(
        "INSERT INTO sem_term (id, term, type, \"def\", status, status_key, owner, "
        "source, version, expires_at, created_at, updated_at) "
        "VALUES (:id, :term, :type, :def, :status, :status_key, :owner, :source, "
        ":version, :expires_at, now(), now()) "
        "ON CONFLICT (id) DO NOTHING"
    )
    for row in _TERM_SEEDS:
        payload = _term_payload(row)
        bind.execute(term_stmt, {
            "id": payload["id"], "term": payload["term"], "type": payload["type"],
            "def": payload["def"], "status": payload["status"],
            "status_key": payload["status_key"], "owner": payload["owner"],
            "source": payload["source"], "version": payload["version"],
            "expires_at": payload["expires_at"],
        })
    # 版本轴配套行（ADR-0004——台账行变更随 sem_ledger_revision 留痕；payload＝
    # 全行快照〔基线列除外〕，键序与同步器 _row_dict 同形；changed_at 基准＝DB 钟，
    # 与 created_at/updated_at 同语句同源）。
    revision_stmt = text(
        "INSERT INTO sem_ledger_revision (domain, row_id, version, payload, "
        "changed_by, source_proposal_id, changed_at, created_at, updated_at) "
        "VALUES (:domain, :row_id, :version, CAST(:payload AS jsonb), :changed_by, "
        "NULL, now(), now(), now()) "
        "ON CONFLICT (domain, row_id, version) DO NOTHING"
    )
    for row in _METRIC_SEEDS:
        bind.execute(revision_stmt, {
            "domain": "metric", "row_id": str(row[0]), "version": _SEED_VERSION,
            "payload": json.dumps(_metric_payload(row), ensure_ascii=False),
            "changed_by": _CHANGED_BY,
        })
    for row in _TERM_SEEDS:
        bind.execute(revision_stmt, {
            "domain": "term", "row_id": str(row[0]), "version": _SEED_VERSION,
            "payload": json.dumps(_term_payload(row), ensure_ascii=False),
            "changed_by": _CHANGED_BY,
        })


def downgrade() -> None:
    """删本票种子行（版本轴先行——台账 11 行＋版本轴 11 行）；表结构与九表
    其余行（本票未触及）原样保留。逐 id 精确删除——只删本票键位（200+ 段），
    同步器投影行（1~15/1~11 段）零触碰。"""
    bind = op.get_bind()
    for seed_id in [str(row[0]) for row in _METRIC_SEEDS]:
        bind.execute(
            text("DELETE FROM sem_ledger_revision WHERE domain = 'metric' "
                 "AND row_id = :row_id"),
            {"row_id": seed_id},
        )
        bind.execute(text("DELETE FROM sem_metric WHERE id = :id"), {"id": int(seed_id)})
    for seed_id in [str(row[0]) for row in _TERM_SEEDS]:
        bind.execute(
            text("DELETE FROM sem_ledger_revision WHERE domain = 'term' "
                 "AND row_id = :row_id"),
            {"row_id": seed_id},
        )
        bind.execute(text("DELETE FROM sem_term WHERE id = :id"), {"id": int(seed_id)})
