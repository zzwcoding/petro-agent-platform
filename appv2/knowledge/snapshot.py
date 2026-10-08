"""knowledge.snapshot —— sem_* 台账读面快照（fixture＝问数组台账态）。

specs/knowledge.md 依赖节：「sem_* fixture（问数组台账态：20 指标/11 术语/
10 对象/5 关系）」；票面验收「从共享 PG 快照或手建 fixture 快照，跑测试不要求
真库在场」。本模块＝手建快照：行值逐字誊自现行台账种子真源——

- 指标 20 行＝bohai 五行（migrations/versions/20261005_0019_sem_ledger_seed.py
  #201~#205，slot_name/定义/口径支/争议注记照抄）＋petro 十五行
  （app/domains/semantics/domain.py METRIC_SEEDS 照抄，grain/unit/slot_name/
  mark 为 M3 口径字段组投影值——schema 1.3.0 裁决 e 同值）；
- 术语 11 行＝TERM_SEEDS 逐字（含 expires_at 届满承载——#11 日产液
  2026-06-30 已届满即漂移标注演示源；0019 版 bohai 六术语行 211~216 已于
  2026-10-05 去重删除，不在台账态）；
- 对象 10 行＝OBJECT_SEEDS；关系 5 行＝RELATION_SEEDS 前 5 行
  （问数组台账态 relations＝5——G-05 扩充六~十行不在册）；
- 别名表＝ontology/petro/glossary-model.yaml terms[].aliases 全量投影
  （别名→规范单向归一，V1 B2-01 承载位同源；现值 12 键＝GLS-PETRO-012~017
  实体别名 8 键＋GLS-PETRO-002/004/005/011 术语别名 4 键——八键实体批原样
  在位，4 个术语键是台账内别名命中真实发生的归一对，缺它则「归一命中」验收
  无落点；字面「八键」口径差异已登记票面偏差，裁决权在 L0）；
- 族标注＝config/relation_types.json（本体导出物）group 键透传
  （load_relation_families 现读——导出物重导出后快照重build即生效）。

行形状只投影读面消费列（台账 owner/source 列等本读面未消费，不进快照——
视图投影口径，非台账全行拷贝）；calibers 只带 key/name/default 三键
（desc 见 0019/种子原文）。快照整体不可变（frozen dataclass＋tuple）——
只读面 INV-2 的数据侧前提。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
RELATION_TYPES_JSON = _REPO_ROOT / "config" / "relation_types.json"


# ---------- 台账行形状（读面投影列） ----------


@dataclass(frozen=True, slots=True)
class MetricRow:
    """sem_metric 现行行投影（slot_name＝剥法纯名——查目录键；version 随行）。"""

    id: int
    name: str  # 台账原名（含 ★☆ 与括注尾缀）
    slot_name: str
    def_: str  # 口径定义（列名照抄台账 "def"）
    grain: str
    unit: str
    status: tuple[str, ...]
    dispute: str | None
    version: int
    calibers: tuple[dict[str, Any], ...] = ()
    default_caliber: str | None = None


@dataclass(frozen=True, slots=True)
class TermRow:
    """sem_term 现行行投影（expires_at＝届满承载列；status_key 六值筛选键）。"""

    id: int
    term: str
    type: str  # 类型展示串（含「别名 → X」族——现口径指引载体）
    def_: str
    status: str
    status_key: str
    version: int
    expires_at: date | None


@dataclass(frozen=True, slots=True)
class ObjectRow:
    """sem_object 现行行投影（草案态整体呈现——status 恒「草案」）。"""

    id: int
    obj: str
    attr: str | None
    status: str
    version: int | None  # null → 台账未落版本


@dataclass(frozen=True, slots=True)
class RelationRow:
    """sem_relation 现行行投影（台账无版本列）。"""

    id: int
    rel: str
    read: str  # 关系的人话读法（C1 列名照抄）


@dataclass(frozen=True, slots=True)
class FamilyRow:
    """族标注行（本体导出物 relation_types.json 的 group 键——B1-01 scenario 透传）。"""

    id: int
    name: str
    group: tuple[str, ...]  # completion/monthly/dynamic 可空多值


@dataclass(frozen=True, slots=True)
class LedgerSnapshot:
    """台账读面快照（不可变整体——InMemoryKnowledgeStore 的构造注入物）。"""

    label: str
    metrics: tuple[MetricRow, ...]
    terms: tuple[TermRow, ...]
    objects: tuple[ObjectRow, ...]
    relations: tuple[RelationRow, ...]
    aliases: tuple[tuple[str, str], ...]  # （别名, 规范名）对——单向归一
    families: tuple[FamilyRow, ...]
    families_version: str | None  # 本体导出物 schema_version


# ---------- 本体导出物族标注（现读——透传纪律） ----------


def load_relation_families(
    path: Path = RELATION_TYPES_JSON,
) -> tuple[tuple[FamilyRow, ...], str | None]:
    """config/relation_types.json → （族标注行, schema_version）。

    group 键原样透传（本体无标注的行缺省不带键——additive 先例；空组行同样
    成行，group＝()）。文件缺失/损坏显式抛错——导出物是进 git 派生物，
    读不到属部署错误禁静默。
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = tuple(
        FamilyRow(
            id=int(row["id"]),
            name=str(row["name"]),
            group=tuple(str(g) for g in row.get("group") or ()),
        )
        for row in payload.get("relation_types") or []
    )
    version = payload.get("schema_version")
    return rows, str(version) if version is not None else None


# ---------- 别名表（glossary terms[].aliases 全量投影——单向归一） ----------

# 键须为原文名形态；值＝规范名。映射外名字零变化不猜测（V1 B2-01 同纪律）。
_GLOSSARY_ALIASES: tuple[tuple[str, str], ...] = (
    # GLS-PETRO-002 剔检产量
    ("净产量", "剔检产量"),
    # GLS-PETRO-004 躺井
    ("停产待检泵", "躺井"),
    # GLS-PETRO-005 时率
    ("抽油机时率", "时率"),
    # GLS-PETRO-011 日产液量（台账指标槽位在册——别名命中落点）
    ("日产液", "日产液量"),
    # GLS-PETRO-012 CEP-C平台（八键实体批——别名八键之两键）
    ("CEP-C 生产平台", "CEP-C平台"),
    ("CEP-C 平台", "CEP-C平台"),
    # GLS-PETRO-013 CEP-D平台（票面点名 CEP-D 修饰形）
    ("CEP-D 生产平台", "CEP-D平台"),
    ("CEP-D 井口平台", "CEP-D平台"),
    # GLS-PETRO-014 CEP-E平台
    ("中心平台 CEP-E", "CEP-E平台"),
    # GLS-PETRO-015/016 油田名空格形
    ("渤中 34-5 油田", "渤中34-5油田"),
    ("渤中 34-8 油田", "渤中34-8油田"),
    # GLS-PETRO-017 永久式封隔器（封隔器省式形）
    ("永久封隔器", "永久式封隔器"),
)


def glossary_aliases() -> tuple[tuple[str, str], ...]:
    """别名→规范名对全集（glossary 投影公开读侧——生产读面与快照同源单点）。"""
    return _GLOSSARY_ALIASES


# ---------- 问数组台账态快照（票面钉死：20 指标/11 术语/10 对象/5 关系） ----------

# calibers 字典键序：key/name/default（desc 不投影——见模块 docstring）。


def _m(row_id: int, name: str, slot: str, def_: str, grain: str, unit: str, *,
       status: tuple[str, ...] = ("生效中",), dispute: str | None = None,
       version: int = 3, calibers: tuple[dict[str, Any], ...] = (),
       default_caliber: str | None = None) -> MetricRow:
    return MetricRow(
        id=row_id, name=name, slot_name=slot, def_=def_, grain=grain, unit=unit,
        status=status, dispute=dispute, version=version,
        calibers=calibers, default_caliber=default_caliber,
    )


_CAL_A = {"key": "A", "name": "开井日历折算", "default": True}
_CAL_B = {"key": "B", "name": "检修剔除", "default": False}


def question_array_snapshot() -> LedgerSnapshot:
    """问数组台账态快照（行值逐字誊自种子真源——誊写来源见模块 docstring）。"""
    metrics: tuple[MetricRow, ...] = (
        # —— bohai 五行（0019 种子 #201~#205，version 1）——
        _m(201, "日产油量（吨）", "日产油量",
           "日产计量的日产油量——源 oil_production_daily.oil_output（R5·A.2，"
           "行粒度＝班次、日口径＝同井同日各班合计，PROP-BOHAI-007=A）；"
           "agg 读模型绑定列 agg.fct_daily_metering.oil_output（99 §2.12）",
           "日/井", "吨",
           dispute="吨方混写脏值（D1——RULE-BOHAI-020 检出位已建）", version=1,
           calibers=({"key": "A", "name": "班次合计日口径", "default": True},),
           default_caliber="A"),
        _m(202, "日产液量（方）", "日产液量",
           "日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；"
           "agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12）",
           "日/井", "方", version=1,
           calibers=({"key": "A", "name": "班次合计日口径", "default": True},),
           default_caliber="A"),
        _m(203, "含水率（%）", "含水率",
           "日产计量化验折算含水率——日度监控口径；月度/正式指标以流体化验实测为准、"
           "偏差 >5pp 以化验校正（PROP-BOHAI-008=C 并存分场景）；源 "
           "oil_production_daily.water_cut（R5·A.2）——agg 读模型未落该列"
           "（99 §2.12 事实表仅三计量列），暂不可出数",
           "日/井", "%",
           dispute="化验 vs 计量打架（并存分场景已裁——PROP-BOHAI-008=C）", version=1,
           calibers=({"key": "A", "name": "计量折算（日度监控）", "default": True},
                     {"key": "B", "name": "化验实测（月度/正式）", "default": False}),
           default_caliber="A"),
        _m(204, "配产量（吨）", "配产量",
           "日产计量的配产量——源 oil_production_daily.plan_output（R5·A.2）；"
           "agg 读模型未落该列（99 §2.12），暂不可出数",
           "日/井", "吨",
           dispute="配产版本切换日双值行（D4 待 Owner）", version=1,
           calibers=({"key": "A", "name": "配产版本当日值", "default": True},),
           default_caliber="A"),
        _m(205, "油压（MPa）", "油压",
           "日产计量的油压——源 oil_production_daily.oil_pressure（R5·A.2）；"
           "agg 读模型绑定列 agg.fct_daily_metering.oil_pressure（99 §2.12）",
           "日/井", "MPa", version=1,
           calibers=({"key": "A", "name": "计量直取日值", "default": True},),
           default_caliber="A"),
        # —— petro 十五行（METRIC_SEEDS 照抄；grain/unit＝M3 口径字段组投影）——
        _m(1, "★产量完成率", "产量完成率",
           "Σ实际产油 ÷ Σ计划配产 × 100%", "月/区块·油田", "%",
           dispute="计划版本切换日双值"),
        _m(2, "★有效产量（两支口径）", "有效产量",
           "开井日历折算 / 检修剔除", "月", "吨",
           dispute="跨月检修切割", calibers=(_CAL_A, _CAL_B), default_caliber="A"),
        _m(3, "☆自然递减率", "自然递减率",
           "月：1 − q_t / q_(t−1)（扣新井与措施增油）；年化：指数拟合 q(t)=q_i·e^(−Dt)",
           "月·年", "%", dispute="措施扣除口径"),
        _m(4, "☆综合递减率", "综合递减率",
           "不扣措施的对比期递减", "月·年", "%", dispute="与自然递减率混用事故"),
        _m(5, "☆综合含水率", "综合含水率",
           "Q_w ÷（Q_o＋Q_w）× 100%", "月", "%",
           dispute="化验 vs 计量打架"),
        _m(6, "☆注采比 β", "注采比 β",
           "月注水量 ÷ 月产液量（体积折算）", "月", "无量纲",
           dispute="折算系数按区块"),
        _m(7, "☆累积亏空", "累积亏空",
           "Σ注水 − Σ产液", "累计", "方", dispute="—"),
        _m(8, "☆措施有效率 η", "措施有效率",
           "N_y ÷ N_z × 100%（有效井次 ÷ 总井次）", "批次", "%",
           dispute="\"有效\"判据"),
        _m(9, "☆措施有效期 T", "措施有效期",
           "t₂ − t₁（天）", "单井·措施", "天", dispute="30% 行缺失"),
        _m(10, "☆递减增油", "递减增油",
           "受效油井实际产油 − 按 d_a 拟合基线 q₀(1−d_a)^t；多井受效按劈分系数"
           "（Σ=1）分摊；多措施叠加以主要措施为主",
           "井组·年", "吨", status=("生效中", "待联席裁决"),
           dispute="一数多源争议之最（事故 7）"),
        _m(11, "★商品量", "商品量",
           "脱水稳定后净重（扣自用油输差）", "月", "吨",
           dispute="与井口口径天然不等"),
        _m(12, "☆机采系统能效", "机采系统能效",
           "系统级 / 单元级 / 设备级三级＋统计限值（优良 / 合格）", "月", "%",
           dispute="分组限值"),
        _m(13, "☆检泵周期", "检泵周期",
           "本次检泵日 − 上次检泵日", "单井", "天", dispute="—"),
        _m(14, "☆抽油机时率", "抽油机时率",
           "Σ开井天数 ÷ Σ日历天 × 100%", "月", "%", dispute="—"),
        _m(15, "☆桶油增产成本", "桶油增产成本",
           "措施总投入 ÷ 折算增油量（桶，6.29 桶/m³）", "批次", "元/桶",
           dispute="经营 × 技术联席"),
    )
    terms: tuple[TermRow, ...] = (
        TermRow(1, "老完成率", "禁用词", "v1 口径（不含自用油折算），2024 年废弃",
                "禁用（替代：产量完成率）", "禁用词", 1, None),
        TermRow(2, "剔检产量", "别名 → 净产量", "剔除检修井口径的产量（即净产量）。",
                "有效", "有效", 1, date(2027, 12, 31)),
        TermRow(3, "有效产量", "一词两译",
                "需修饰词消歧的产量词：开井日历支 / 剔检支，两支口径并列，"
                "单说「有效产量」必须追问修饰词。",
                "有效", "有效", 1, date(2027, 6, 30)),
        TermRow(4, "躺井", "黑话 → 停产待检泵",
                "作业区口语，指停产待检泵的井（及该检修事件）。",
                "有效（限作业区语境）", "有效（限作业区语境）", 1, date(2026, 12, 31)),
        TermRow(5, "时率", "缩写 → 抽油机时率",
                "「抽油机时率」的缩写；= Σ开井时长/Σ日历时长×100（见指标 14）。",
                "有效", "有效", 1, date(2027, 6, 30)),
        TermRow(6, "水淹层", "术语", "驱替前沿到达的高含水层段",
                "有效", "有效", 1, date(2028, 12, 31)),
        TermRow(7, "递减增油", "术语",
                "措施后增产油量=（实际产量−递减基线产量）×劈分系数；基线 "
                "q₀(1−dₐ)^t 拟合参数设定书未给。含口径争议注记：事故 7「一数多源」"
                "争议、待联席裁决。",
                "有效（待联席裁决）", "有效（待联席裁决）", 1, date(2027, 3, 31)),
        TermRow(8, "存水率", "术语", "注入水留存地层比例（物质平衡用）。",
                "有效", "有效", 1, None),  # 长期
        TermRow(9, "配注合格率", "术语", "分层实注 / 配注 达标井次占比",
                "有效", "有效", 1, date(2027, 12, 31)),
        TermRow(10, "三多四难", "治理热词",
                "数据库多、平台多、孤立应用多 / 共享难、复用难、开发难、协同难",
                "有效（引用马涛）", "有效（引用马涛）", 1, None),  # 长期（引用类）
        TermRow(11, "日产液", "别名 → 日产液量", "作业区口语缩写",
                "有效（已届满 · 命中带漂移标注）", "有效（已届满）", 1,
                date(2026, 6, 30)),  # 已届满（2026-06-30）——漂移标注演示源
    )
    objects: tuple[ObjectRow, ...] = (
        ObjectRow(1, "井", "井号 / 井别 / 投产日 / 状态机", "草案", None),
        ObjectRow(2, "井筒", "段 / 射孔 / 防砂", "草案", None),
        ObjectRow(3, "区块", "§5 未列属性", "草案", None),
        ObjectRow(4, "油田", "§5 未列属性", "草案", None),
        ObjectRow(5, "平台", "§5 未列属性", "草案", None),
        ObjectRow(6, "设备", "§5 未列属性", "草案", None),
        ObjectRow(7, "措施", "§5 未列属性", "草案", None),
        ObjectRow(8, "化验样", "§5 未列属性", "草案", None),
        ObjectRow(9, "受效关系",
                  "注水井 → 受效油井，多对多；属性＝劈分系数（Σ=1）、响应起始日"
                  "——系数劈分是强制要求，设定书 §5", "草案", None),
        ObjectRow(10, "配注层", "§5 未列属性", "草案", None),
    )
    relations: tuple[RelationRow, ...] = (
        RelationRow(1, "井 —隶属→ 区块 —隶属→ 油田", "井属于哪个区块，区块属于哪个油田"),
        RelationRow(2, "平台 —承载→ 井", "井装在哪个平台上"),
        RelationRow(3, "注水井 —受效→ 油井", "哪口注水井的注水，效果落在哪口油井上"),
        RelationRow(4, "措施 —作用于→ 井", "压裂 / 酸化等措施做在哪口井上"),
        RelationRow(5, "化验样 —取样自→ 井", "化验的水样取自哪口井"),
    )
    families, families_version = load_relation_families()
    return LedgerSnapshot(
        label="问数组台账态（20 指标/11 术语/10 对象/5 关系）",
        metrics=metrics, terms=terms, objects=objects, relations=relations,
        aliases=_GLOSSARY_ALIASES, families=families, families_version=families_version,
    )
