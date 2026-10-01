"""domains.semantics.domain —— 语义台账投影模型、占位行种子常量与同步校验规则。

真源与投影分工（ADR-0004 + 对齐矩阵 alignment/bohai-to-platform.md + 98 §3.7）：
- 真源＝ontology/petro/ 七模型 YAML（schemaVersion 1.1.0 钉版）；DB 行＝同步投影。
- 同步器投影规则：本体承载的字段（指标 mark/grain/unit/modifiers/ambiguous 口径
  字段组、元素锚）从 YAML 读出投影；台账展示串（术语/指标的 def·name·owner·
  source·status、对象/关系/白名单/占位行全文）**照抄 C1 合同现值**（C1 合同
  「11 术语/15 指标/10 对象/5 关系/4 白名单/10 工作流/3 Action 逐条注源照抄页面」
  ——B 侧真源；对齐矩阵 §2 逐行对账）。
- 占位行种子（本票「本体不建、照 C1 现值种子导入」清单，源 ontology/petro/
  manifest.json deferredAdditions）：工作流 wf3–wf10 八条、白名单 #2（date_dim
  非业务实体）、Action 三条（平台受控写入合同，八模型无登记位——m2 头注承载）；
  另含 M3 指标 15 桶油增产成本占位（dispute「经营 × 技术联席」如实投影）与
  M3 指标 11 商品量事实承载型行（无计算规则——对齐矩阵 §6 发现 3）。
- 台账行禁手工改（B4/ADR-0004）；行变更一律落 sem_ledger_revision 版本轴。
- 本体无承载、C1 演示值如实标注的行值（版本 v1/v3、有效期日期）按 C1 合同
  「无设定书直锚的演示值如实标注」条款照抄（对齐矩阵裁决项 e/g：expires_at
  本体不承载——F60 机器判消费面在平台侧）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

# ---------- 钉版契约（98 §3.7 sync_from_ontology_repo） ----------

SCHEMA_VERSION_PIN = "1.1.0"  # petro-ontology manifest 契约轴（低于拒同步/补丁位兼容读）


class OntologySchemaUnsupported(Exception):
    """schema_version 低于钉版（major.minor < 1.1）——拒同步（98 §3.7 钉版纪律）。"""


class OntologyDriftError(Exception):
    """petro/ YAML 与投影常量锚校验不过（元素缺失/名称漂移）——同步失败不静默。"""


@dataclass(frozen=True, slots=True)
class SyncReport:
    """sync_from_ontology_repo 回执（98 §3.7 同步口返回形状）。"""

    ref: str
    schema_version: str
    counts: dict[str, int] = field(default_factory=dict)
    revisions_appended: int = 0
    rows_unchanged: int = 0
    warnings: list[str] = field(default_factory=list)


def assert_schema_version(manifest_version: str, requested: str) -> None:
    """钉版契约校验：major.minor 必须等于 1.1；补丁位兼容读（低于拒同步）。

    requested＝调用方声明的内容版本（MR 合入事件携带）；manifest_version＝
    本体仓 manifest.schemaVersion 现值——两处逐字一致才放行。
    """
    for label, value in (("manifest", manifest_version), ("请求", requested)):
        parts = value.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise OntologySchemaUnsupported(f"{label} schemaVersion 形状非法: {value!r}")
    pin = tuple(int(p) for p in SCHEMA_VERSION_PIN.split(".")[:2])
    for label, value in (("manifest", manifest_version), ("请求", requested)):
        major, minor = (int(p) for p in value.split(".")[:2])
        if (major, minor) < pin:
            raise OntologySchemaUnsupported(
                f"{label} schemaVersion {value} 低于钉版 {SCHEMA_VERSION_PIN}——拒同步"
                f"（98 §3.7：低于钉版拒同步、补丁位兼容读）"
            )
        if (major, minor) > pin:
            raise OntologySchemaUnsupported(
                f"{label} schemaVersion {value} 高于钉版 {SCHEMA_VERSION_PIN}——"
                f"本体仓 schema 升级须先仓后同步器联合变更（ontology/AGENTS.md 纪律 4）"
            )
    if manifest_version != requested:
        raise OntologyDriftError(
            f"schemaVersion 不一致：manifest={manifest_version} 请求={requested}"
        )


# ---------- slot_name 剥法（服务端单点——C1 端点 3 metricLabel 合同化；票 93） ----------

_STRIP_MARK = re.compile(r"^[★☆]")
_PAREN_TAIL = re.compile(r"（[^）]*）$")
_MARK_TAIL = re.compile(r"\s+[ηT]$")


def metric_slot_name(name: str) -> str:
    """台账原名 → 槽位纯名（剥首 ★/☆ → 剥尾括注（…）→ 剥尾 η/T；β 保留）。

    剥法只在本函数执行一次（C1 端点 3/4 同字段同源；下游禁止自留拷贝——票 93）。
    """
    stripped = _STRIP_MARK.sub("", name)
    stripped = _PAREN_TAIL.sub("", stripped)
    return _MARK_TAIL.sub("", stripped).strip()


# ---------- 种子行形状（投影载荷——payload/行 dict 的键＝99 §2.8 列名） ----------


@dataclass(frozen=True, slots=True)
class SeedRow:
    """单条种子行：域键（99 §2.8 表）＋行载荷＋本体锚（元素 id 列表，供 YAML 校验）。"""

    domain: str  # term/metric/object/relation/whitelist/workflow/action
    row_id: str
    payload: dict[str, Any]
    ontology_refs: tuple[str, ...] = ()


def _term(
    row_id: int, *, term: str, type_: str, def_: str, status: str, status_key: str,
    owner: str, expires_at: date | None,
) -> SeedRow:
    return SeedRow(
        "term", str(row_id),
        {"term": term, "type": type_, "def": def_, "status": status,
         "status_key": status_key, "owner": owner, "source": "设定书 §6",
         "version": 1, "expires_at": expires_at},
        (f"GLS-PETRO-{row_id:03d}",),
    )


def _metric(
    row_id: int, *, name: str, def_: str, status: list[str], owner: str, source: str,
    dispute: str | None, m3_ref: str | None, grain: str | None = None,
    unit: str | None = None, calibers: list[dict[str, Any]] | None = None,
    default_caliber: str | None = None,
) -> SeedRow:
    payload: dict[str, Any] = {
        "name": name, "def": def_, "status": status, "owner": owner,
        "source": source, "dispute": dispute, "m3_ref": m3_ref, "version": 3,
    }
    if grain is not None:  # 仅无 M3 锚行（#11 事实承载型 / #15 占位）按 C1 拆分携带
        payload["grain"] = grain
        payload["unit"] = unit
    if calibers is not None:
        payload["calibers"] = calibers
        payload["default_caliber"] = default_caliber
    return SeedRow("metric", str(row_id), payload, () if m3_ref is None else (m3_ref,))


def _object(row_id: int, obj: str, attr: str | None, ref: str) -> SeedRow:
    return SeedRow(
        "object", str(row_id),
        {"obj": obj, "attr": attr, "status": "草案", "owner": None,
         "source": "设定书 §5", "version": None},
        (ref,),
    )


def _relation(row_id: int, rel: str, read: str, refs: tuple[str, ...]) -> SeedRow:
    return SeedRow(
        "relation", str(row_id), {"rel": rel, "read": read, "source": "设定书 §5"}, refs
    )


def _whitelist(
    row_id: int, *, left: str, right: str, verdict: str, tables: str, how: str,
    refs: tuple[str, ...],
) -> SeedRow:
    return SeedRow(
        "whitelist", str(row_id),
        {"left_table": left, "right_table": right, "verdict": verdict,
         "tables": tables, "how": how, "version": 1},
        refs,
    )


_WF1_STEPS = [
    "拉完成率与构成（产油 / 开井数 / 时率）",
    "分解：新井贡献 / 老井递减 / 措施增油 / 停产影响（用指标 3 / 8 / 10）",
    "归因分支：地质——含水上升？工程——检泵停产？管理——配产调整？",
    "下钻受效关系与检修台账",
    "生成归因报告",
]
_WF2_STEPS = [
    "定口径（递减增油）",
    "有效性判定",
    "技术指标计算（指标 8–10）",
    "受效判断",
    "劈分系数",
    "增油核算",
    "桶油成本",
    "归档进\"已验证指标\"证据",
]
_META_FULL = "未落（如实标注）· 草案（待 Owner 审定）· v1。"
_META_DRAFT = "未落（如实标注）· 草案 · —。"


def _workflow(
    wf_id: str, name: str, *, status: str, account: str | None, source: str | None,
    trigger: str | None, steps: list[str] | None, defaults: str | None,
    confirm: str | None, contract: str | None, card_source: str | None, meta: str,
    refs: tuple[str, ...],
) -> SeedRow:
    card: dict[str, Any] = {
        "trigger": trigger, "steps": steps, "defaults": defaults,
        "confirm": confirm, "contract": contract, "source": card_source, "meta": meta,
    }
    return SeedRow(
        "workflow", wf_id,
        {"name": name, "status": status, "account": account, "source": source,
         "card": card, "version": 1 if "v1" in meta else None},
        refs,
    )


# ---------- sem_term 种子（11 条——C1 端点 2 逐条照抄；GLS-PETRO-001~011 锚） ----------
# expires_at：本体 GLS 无承载（对齐矩阵裁决项 g：F60 机器判消费面在平台侧）——
# C1 现值种子（合同声明「无设定书直锚的演示值如实标注」）；过期派生不落列（F60）。

TERM_SEEDS: tuple[SeedRow, ...] = (
    _term(1, term="老完成率", type_="禁用词", def_="v1 口径（不含自用油折算），2024 年废弃",
          status="禁用（替代：产量完成率）", status_key="禁用词", owner="开发室",
          expires_at=None),
    _term(2, term="剔检产量", type_="别名 → 净产量", def_="剔除检修井口径",
          status="有效", status_key="有效", owner="开发室", expires_at=date(2027, 12, 31)),
    _term(3, term="有效产量", type_="一词两译", def_="需修饰词消歧（开井日历 / 剔检）",
          status="有效", status_key="有效", owner="开发室", expires_at=date(2027, 6, 30)),
    _term(4, term="躺井", type_="黑话 → 停产待检泵", def_="作业区口语",
          status="有效（限作业区语境）", status_key="有效（限作业区语境）",
          owner="采油工艺所", expires_at=date(2026, 12, 31)),
    _term(5, term="时率", type_="缩写 → 抽油机时率", def_="见指标 14",
          status="有效", status_key="有效", owner="采油工艺所",
          expires_at=date(2027, 6, 30)),
    _term(6, term="水淹层", type_="术语", def_="驱替前沿到达的高含水层段",
          status="有效", status_key="有效", owner="地质研究所",
          expires_at=date(2028, 12, 31)),
    _term(7, term="递减增油", type_="术语", def_="见指标 10（含口径争议注记）",
          status="有效（待联席裁决）", status_key="有效（待联席裁决）",
          owner="采油工艺所", expires_at=date(2027, 3, 31)),
    _term(8, term="存水率", type_="术语", def_="注入水留存地层比例（物质平衡用）",
          status="有效", status_key="有效", owner="开发室", expires_at=None),  # 长期
    _term(9, term="配注合格率", type_="术语", def_="分层实注 / 配注 达标井次占比",
          status="有效", status_key="有效", owner="采油工艺所",
          expires_at=date(2027, 12, 31)),
    _term(10, term="三多四难", type_="治理热词",
          def_="数据库多、平台多、孤立应用多 / 共享难、复用难、开发难、协同难",
          status="有效（引用马涛）", status_key="有效（引用马涛）", owner="语义 Owner",
          expires_at=None),  # 长期（引用类）
    # 页面增补行（漂移标注演示源＝PRD F60/U09 A1.13-15；GLS-PETRO-011 别名「日产液」锚
    # ——Owner 2026-09-29 裁决「日产液=日产液量同义词」，add 提案 OWNER-ADD-011）。
    _term(11, term="日产液", type_="别名 → 日产液量", def_="作业区口语缩写",
          status="有效（已届满 · 命中带漂移标注）", status_key="有效（已届满）",
          owner="开发室", expires_at=date(2026, 6, 30)),  # 已届满（2026-06-30）
)

# ---------- sem_metric 种子（15 条——C1 端点 3/4 现值；口径结构字段从 M3 YAML 投影） ----------
# 字段分工：name/def/status/owner/source/dispute＝C1 现值照抄；grain/unit/modifiers/
# ambiguous 由 enrich_metric_seeds() 从锚定 M3 规则的口径字段组（schema 1.3.0 裁决 e）
# 读出投影；mark/slot_name 由台账原名派生（剥法单点）。m3_ref 为空两条：
# #11 商品量＝事实承载型（无计算规则——承载 AGG-PETRO-008.netWeight＋QR-PETRO-003
# 出口，对齐矩阵 §6 发现 3）；#15 桶油增产成本＝deferredAdditions 占位（分子素材缺，
# dispute「经营 × 技术联席」如实投影）——grain/unit 取 C1「粒度 · 单位」合并串拆分。

_CALIBER_A = {
    "key": "A", "name": "开井日历折算", "default": True,
    "desc": ("按开井日历折算出数。跨月检修的井（例：N-11 检泵 2026-08-28→09-06）"
             "在 8 月、9 月各按开井情况计入——两支口径的分歧点就是「跨月检修切割」。"),
}
_CALIBER_B = {
    "key": "B", "name": "检修剔除", "default": False,
    "desc": ("把检修井剔除后再算净产量——别名「剔检产量」。"
             "同一口 N-11，在 9 月的数里不计入检修这段。"),
}

METRIC_SEEDS: tuple[SeedRow, ...] = (
    _metric(1, name="★产量完成率", def_="Σ实际产油 ÷ Σ计划配产 × 100%",
            status=["生效中"], owner="开发室", source="A.2 日产计量＋配产表",
            dispute="计划版本切换日双值", m3_ref="RULE-PETRO-009"),
    _metric(2, name="★有效产量（两支口径）", def_="开井日历折算 / 检修剔除",
            status=["生效中"], owner="开发室", source="A.2 日产计量＋A.4 检修台账",
            dispute="跨月检修切割", m3_ref="RULE-PETRO-019",
            calibers=[_CALIBER_A, _CALIBER_B], default_caliber="A"),
    _metric(3, name="☆自然递减率",
            def_="月：1 − q_t / q_(t−1)（扣新井与措施增油）；年化：指数拟合 q(t)=q_i·e^(−Dt)",
            status=["生效中"], owner="开发室", source="A.2 日产计量",
            dispute="措施扣除口径", m3_ref="RULE-PETRO-013"),
    _metric(4, name="☆综合递减率", def_="不扣措施的对比期递减",
            status=["生效中"], owner="开发室", source="A.2 日产计量",
            dispute="与自然递减率混用事故", m3_ref="RULE-PETRO-014"),
    _metric(5, name="☆综合含水率", def_="Q_w ÷（Q_o＋Q_w）× 100%",
            status=["生效中"], owner="开发室", source="A.2 日产计量＋A.6 化验",
            dispute="化验 vs 计量打架", m3_ref="RULE-PETRO-010"),
    _metric(6, name="☆注采比 β", def_="月注水量 ÷ 月产液量（体积折算）",
            status=["生效中"], owner="采油工艺所", source="A.3 注水日报＋A.2 日产计量",
            dispute="折算系数按区块", m3_ref="RULE-PETRO-011"),
    _metric(7, name="☆累积亏空", def_="Σ注水 − Σ产液",
            status=["生效中"], owner="开发室", source="A.3 注水日报＋A.2 日产计量",
            dispute="—", m3_ref="RULE-PETRO-012"),
    _metric(8, name="☆措施有效率 η", def_="N_y ÷ N_z × 100%（有效井次 ÷ 总井次）",
            status=["生效中"], owner="采油工艺所", source="A.5 措施台账",
            dispute="\"有效\"判据", m3_ref="RULE-PETRO-034"),
    _metric(9, name="☆措施有效期 T", def_="t₂ − t₁（天）",
            status=["生效中"], owner="采油工艺所", source="A.5 措施台账",
            dispute="30% 行缺失", m3_ref="RULE-PETRO-015"),
    _metric(10, name="☆递减增油",
            def_=("受效油井实际产油 − 按 d_a 拟合基线 q₀(1−d_a)^t；多井受效按劈分系数"
                  "（Σ=1）分摊；多措施叠加以主要措施为主"),
            status=["生效中", "待联席裁决"], owner="采油工艺所（开发室联席）",
            source="A.2＋A.5＋受效关系", dispute="一数多源争议之最（事故 7）",
            m3_ref="RULE-PETRO-018"),
    _metric(11, name="★商品量", def_="脱水稳定后净重（扣自用油输差）",
            status=["生效中"], owner="销售计量站", source="A.8 月度结算",
            dispute="与井口口径天然不等", m3_ref=None, grain="月", unit="吨"),
    _metric(12, name="☆机采系统能效",
            def_="系统级 / 单元级 / 设备级三级＋统计限值（优良 / 合格）",
            status=["生效中"], owner="采油工艺所", source="A.7 设备状态",
            dispute="分组限值", m3_ref="RULE-PETRO-035"),
    _metric(13, name="☆检泵周期", def_="本次检泵日 − 上次检泵日",
            status=["生效中"], owner="采油工艺所", source="A.4 检修台账",
            dispute="—", m3_ref="RULE-PETRO-016"),
    _metric(14, name="☆抽油机时率", def_="Σ开井天数 ÷ Σ日历天 × 100%",
            status=["生效中"], owner="采油工艺所", source="A.2 日产计量",
            dispute="—", m3_ref="RULE-PETRO-017"),
    _metric(15, name="☆桶油增产成本", def_="措施总投入 ÷ 折算增油量（桶，6.29 桶/m³）",
            status=["生效中"], owner="采油工艺所＋财务", source="A.5 措施台账＋ERP",
            dispute="经营 × 技术联席", m3_ref=None, grain="批次", unit="元/桶"),
)

# 一词两译歧义行 id（C1 合同常量：仅 #2 ambiguous=true，M3 锚 RULE-PETRO-019）。
AMBIGUOUS_METRIC_ID = "2"

# ---------- sem_object 种子（10 行——C1 端点 5 现值；M1 聚合锚） ----------
# 对象名＝§5 实体短名（C1 对象账行）；M1 聚合名差（设备↔设备状态记录等）由对齐
# 矩阵 §2.3 逐行对账（[复用-direct·形状注记]），本体锚用 AGG id 承载。

OBJECT_SEEDS: tuple[SeedRow, ...] = (
    _object(1, "井", "井号 / 井别 / 投产日 / 状态机", "AGG-PETRO-001"),
    _object(2, "井筒", "段 / 射孔 / 防砂", "AGG-PETRO-011"),
    _object(3, "区块", "§5 未列属性", "AGG-PETRO-010"),
    _object(4, "油田", "§5 未列属性", "AGG-PETRO-012"),
    _object(5, "平台", "§5 未列属性", "AGG-PETRO-013"),
    _object(6, "设备", "§5 未列属性", "AGG-PETRO-007"),
    _object(7, "措施", "§5 未列属性", "AGG-PETRO-005"),
    _object(8, "化验样", "§5 未列属性", "AGG-PETRO-006"),
    _object(9, "受效关系",
            "注水井 → 受效油井，多对多；属性＝劈分系数（Σ=1）、响应起始日"
            "——系数劈分是强制要求，设定书 §5",
            "AGG-PETRO-009"),
    _object(10, "配注层", "§5 未列属性", "AGG-PETRO-014"),
)

# ---------- sem_relation 种子（5 条——C1 端点 6 现值；M1 关联/关系实体锚） ----------
# #1 的井—隶属→区块段为 AGG-PETRO-001.blockName 属性承载（引用化悬置，M1 头注），
# 油田段＝ASSOC-PETRO-008；#3 经受效关系实体展开（ASSOC-006/007 两条一对多）。

RELATION_SEEDS: tuple[SeedRow, ...] = (
    _relation(1, "井 —隶属→ 区块 —隶属→ 油田", "井属于哪个区块，区块属于哪个油田",
              ("ASSOC-PETRO-008",)),
    _relation(2, "平台 —承载→ 井", "井装在哪个平台上", ("ASSOC-PETRO-009",)),
    _relation(3, "注水井 —受效→ 油井", "哪口注水井的注水，效果落在哪口油井上",
              ("AGG-PETRO-009", "ASSOC-PETRO-006", "ASSOC-PETRO-007")),
    _relation(4, "措施 —作用于→ 井", "压裂 / 酸化等措施做在哪口井上",
              ("ASSOC-PETRO-004",)),
    _relation(5, "化验样 —取样自→ 井", "化验的水样取自哪口井", ("ASSOC-PETRO-005",)),
)

# ---------- sem_join_whitelist 种子（4 行——C1 端点 7 现值；白名单默认拒绝语义） ----------
# #2＝deferredAdditions 占位行（date_dim 中台维表非业务实体，本体不建——裁决项 f）；
# #3/#4 的判据真源在 M1 description/RULE-PETRO-002（对齐矩阵 §2.5 逐行对账）。

WHITELIST_SEEDS: tuple[SeedRow, ...] = (
    _whitelist(1, left="oil_production_daily", right="well_info", verdict="可以",
               tables="日产计量 oil_production_daily ⋈ 井档案 well_info",
               how="用井号连", refs=("ASSOC-PETRO-001",)),
    _whitelist(2, left="oil_production_daily", right="date_dim", verdict="可以",
               tables="日产计量 oil_production_daily ⋈ 日期维表 date_dim",
               how="按日期连", refs=()),  # 占位行（deferredAdditions——date_dim 非本体元素）
    _whitelist(3, left="oil_production_daily", right="fluid_test", verdict="默认不给",
               tables="日产计量 oil_production_daily ⋈ 化验样 fluid_test",
               how="须井号＋取样日期双键＋时间容差，经清洗层视图中转",
               refs=("AGG-PETRO-006", "RULE-PETRO-002")),
    _whitelist(4, left="oil_production_daily", right="water_injection_daily",
               verdict="默认不给",
               tables="日产计量 oil_production_daily ⋈ 注水日报 water_injection_daily（直连）",
               how="须经\"受效关系\"这个对象中转，不许硬拼",
               refs=("AGG-PETRO-003", "AGG-PETRO-009")),
)

# ---------- sem_workflow 种子（10 条——C1 端点 8/9 现值） ----------
# wf1/wf2 锚 FLOW-PETRO-001/002（M6 剧本 1/2；登记卡步骤与 M6 activities 语义对齐
# ——对齐矩阵 §2.6）；wf3–wf10＝deferredAdditions 占位行（照 C1 现值导入，五要件
# 如实缺项）。registered_items＝五要件非空数（读时由 card 派生——单一事实源）。

WORKFLOW_SEEDS: tuple[SeedRow, ...] = (
    _workflow("wf1", "《产量下滑归因》", status="登记", account="产量分析",
              source="设定书 §7", trigger="听到\"为什么下滑\"类问题开工。",
              steps=_WF1_STEPS,
              defaults="时间窗默认最近 30 天、范围默认全区块，并明确标注\"默认\"。",
              confirm="置信度高→少问人；低→必须人工确认档位（设定书 §7）。",
              contract="结论＋证据链＋数据版本，三样齐才算答完。",
              card_source="设定书 §7", meta=_META_FULL, refs=("FLOW-PETRO-001",)),
    _workflow("wf2", "《注水井措施评估》", status="草案", account=None,
              source="报告《注水井措施评估》· 设定书 §7", trigger=None,
              steps=_WF2_STEPS, defaults=None, confirm=None,
              contract="第⑧步归档进\"已验证指标\"证据（半截登记，待补全）。",
              card_source="报告《注水井措施评估》· 设定书 §7", meta=_META_FULL,
              refs=("FLOW-PETRO-002",)),
    _workflow("wf3", "《档案质量体检》", status="草案", account=None, source=None,
              trigger="周期体检 + 问答人工指令承接（低风险自动档）。", steps=None,
              defaults=None, confirm=None,
              contract="低风险类：不碰计量数字，自动执行并留审计。",
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf4", "《复产确认检查》", status="草案", account=None, source=None,
              trigger="表间矛盾监控：检修完成＋产量表有行＋档案状态停产。", steps=None,
              defaults=None, confirm=None,
              contract="高风险：出变动单挂起，等人工终审。",
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf5", "《低产井措施筛查》", status="草案", account=None, source=None,
              trigger=None, steps=None, defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf6", "《机采井工况诊断》", status="草案", account=None, source=None,
              trigger=None, steps=None, defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf7", "《区块注采平衡评估》", status="草案", account=None, source=None,
              trigger=None, steps=None, defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf8", "《幻觉拦截周报》", status="草案", account=None, source=None,
              trigger="周期回放：幻觉误放率超阈值 → 出配置变动单。", steps=None,
              defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf9", "《平台运行周报》", status="草案", account=None, source=None,
              trigger=None, steps=None, defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
    _workflow("wf10", "《月度统计对账》", status="草案", account=None, source=None,
              trigger=None, steps=None, defaults=None, confirm=None, contract=None,
              card_source=None, meta=_META_DRAFT, refs=()),
)

# ---------- sem_action 种子（3 条——C1 端点 10 现值；m2 头注合同登记承载） ----------
# 平台 Action＝受控写入合同（与 M2 源侧业务动作两族并立不互迁——裁决项 f 尾注）；
# 八模型无 Action 登记位，本体承载＝petro/m2-behavior-model.yaml 头注（同步器校验
# 三个注册名在 m2 头注逐字在案）。

ACTION_SEEDS: tuple[SeedRow, ...] = (
    SeedRow("action", "update_well_remark",
            {"register_name": "update_well_remark", "business_name": "更新井备注"}),
    SeedRow("action", "adjust_production_plan",
            {"register_name": "adjust_production_plan", "business_name": "调整配产"}),
    SeedRow("action", "adjust_injection_volume",
            {"register_name": "adjust_injection_volume", "business_name": "配注上调"}),
)

# 语义层全量版本种子（C1 端点 1 semantic.current 演示值同源——C3 合同同口径；
# 版本推进只归治理链发布事务，同步器投影不推全量版本）。
SEMANTIC_CURRENT_SEED = "v37"

# ---------- 本体锚校验（YAML ↔ 种子常量双向对账——锚不上即同步失败） ----------


def _gls_names(glossary: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """GLS 元素 id → {term} ∪ aliases 名称集（术语锚的成员校验域）。"""
    names: dict[str, tuple[str, ...]] = {}
    for entry in glossary.get("terms") or []:
        names[str(entry["id"])] = (
            str(entry["term"]),
            *(str(a) for a in entry.get("aliases") or []),
        )
    return names


def _m1_ids(m1: dict[str, Any]) -> set[str]:
    """M1 全部元素 id（聚合 + 关联）——对象/关系/白名单锚的存在性校验域。"""
    ids = {str(a["id"]) for a in m1.get("aggregates") or []}
    ids |= {str(a["id"]) for a in m1.get("aggregate_associations") or []}
    return ids


def _m3_rules(m3: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(r["id"]): r for r in m3.get("rules") or []}


def validate_against_ontology(
    models: dict[str, dict[str, Any]], raw_text: dict[str, str]
) -> list[str]:
    """种子常量 × petro/ YAML 逐锚校验——返回漂移告警列表；锚不上抛 OntologyDriftError。

    models＝按模型键的解析结果（glossary/m1/m3/m6/m2）；raw_text＝文件原文
    （m2 头注 Action 登记承载的字面校验域）。
    """
    warnings: list[str] = []
    gls = _gls_names(models["glossary"])
    m1 = _m1_ids(models["m1"])
    m3 = _m3_rules(models["m3"])
    m6_names = {
        str(flow["id"]): str(flow["name"]) for flow in models["m6"].get("flows") or []
    }

    for seed in TERM_SEEDS:
        ref = seed.ontology_refs[0]
        if ref not in gls:
            raise OntologyDriftError(f"术语锚缺失：{ref} 不在 glossary-model.yaml")
        if seed.payload["term"] not in gls[ref]:
            raise OntologyDriftError(
                f"术语名漂移：{seed.payload['term']!r} 不在 {ref} 的 term/aliases 内"
            )

    for seed in METRIC_SEEDS:
        m3_ref = seed.payload.get("m3_ref")
        if m3_ref is not None:
            rule = m3.get(str(m3_ref))
            if rule is None:
                raise OntologyDriftError(f"指标锚缺失：{m3_ref} 不在 m3-rule-model.yaml")
            if rule.get("ruleType") != "CALCULATION":
                raise OntologyDriftError(f"指标锚 {m3_ref} 非 CALCULATION 规则")
        elif seed.row_id == "11":
            if "AGG-PETRO-008" not in m1:
                raise OntologyDriftError("事实承载型指标 #11 的承载对象 AGG-PETRO-008 缺失")
        # #15＝deferredAdditions 占位（M3 无规则为预期；dispute 如实投影）。
    if "RULE-PETRO-019" not in m3:
        raise OntologyDriftError("一词两译锚 RULE-PETRO-019 缺失")

    for seed in OBJECT_SEEDS:
        missing = [ref for ref in seed.ontology_refs if ref not in m1]
        if missing:
            raise OntologyDriftError(f"对象锚缺失：{missing} 不在 m1-object-model.yaml")
    for seed in RELATION_SEEDS:
        missing = [ref for ref in seed.ontology_refs if ref not in m1]
        if missing:
            raise OntologyDriftError(f"关系锚缺失：{missing} 不在 m1-object-model.yaml")
    for seed in WHITELIST_SEEDS:
        for ref in seed.ontology_refs:
            if ref.startswith("RULE-"):
                if ref not in m3:
                    raise OntologyDriftError(
                        f"白名单规则锚缺失：{ref} 不在 m3-rule-model.yaml"
                    )
            elif ref not in m1:
                raise OntologyDriftError(f"白名单对象锚缺失：{ref} 不在 m1-object-model.yaml")

    for seed in WORKFLOW_SEEDS:
        for ref in seed.ontology_refs:
            if ref not in m6_names:
                raise OntologyDriftError(f"工作流锚缺失：{ref} 不在 m6-flow-model.yaml")
            if m6_names[ref].strip("《》") not in seed.payload["name"]:
                raise OntologyDriftError(
                    f"工作流名漂移：{ref}={m6_names[ref]!r} 与 {seed.payload['name']!r} 不对齐"
                )

    m2_header = raw_text.get("m2", "")
    for seed in ACTION_SEEDS:
        if seed.row_id not in m2_header:
            warnings.append(
                f"Action 注册名 {seed.row_id} 未在 m2 头注逐字在案（deferredAdditions 承载漂移）"
            )
    return warnings


def registered_items(card: dict[str, Any]) -> int:
    """登记项计数 n/5＝五要件非空数（C1 合同常量；来源/负责人·状态·版本行不计数）。"""
    five_items = ("trigger", "steps", "defaults", "confirm", "contract")
    return sum(1 for key in five_items if card.get(key))


# ---------- M3 口径字段组投影（schema 1.3.0 裁决 e：粒度/单位/修饰词/歧义＝本体内容） ----------


def enrich_metric_seeds(m3_rules: dict[str, dict[str, Any]]) -> tuple[list[SeedRow], list[str]]:
    """指标种子行 × M3 口径字段组——grain/unit/modifiers/ambiguous 从 YAML 读出投影。

    C1 现值（name/def/status/owner/source/dispute）保持照抄；m3_ref 锚定规则
    缺口径字段组（老 schema）即漂移失败。#11/#15 无 M3 锚（事实承载型/占位行），
    grain/unit 已在种子常量按 C1「粒度 · 单位」合并串拆分携带。
    返回 (补充后的种子行, 漂移告警)。
    """
    enriched: list[SeedRow] = []
    warnings: list[str] = []
    for seed in METRIC_SEEDS:
        payload = dict(seed.payload)
        m3_ref = payload.get("m3_ref")
        if m3_ref is not None:
            rule = m3_rules.get(str(m3_ref))
            if rule is None:
                raise OntologyDriftError(f"指标锚缺失：{m3_ref} 不在 m3-rule-model.yaml")
            for field_name in ("grain", "unit"):
                if rule.get(field_name) is None:
                    raise OntologyDriftError(
                        f"指标 {m3_ref} 缺口径字段 {field_name}（schema 1.3.0 裁决 e 字段组）"
                    )
                payload[field_name] = rule[field_name]
            payload["modifiers"] = rule.get("modifiers")
            payload["ambiguous"] = bool(rule.get("ambiguous", False))
            # 口径支名三处一致校验（P1-01b 统一后的看守闸）：M3 calibers（本体真源）
            # vs C1 口径卡名（种子常量，台账 calibers 照抄 C1 结构）——名字集不一致
            # 才告警（真漂移不静默）；一致即零告警（P1-01 挂账的口径名差已收口）。
            if rule.get("calibers") and payload.get("calibers"):
                m3_names = {str(name) for name in rule["calibers"]}
                c1_names = {str(c["name"]) for c in payload["calibers"]}
                if m3_names != c1_names:
                    warnings.append(
                        f"指标 {m3_ref} 的 M3 口径支名 {sorted(m3_names)} 与 C1 口径卡名 "
                        f"{sorted(c1_names)} 不一致——台账 calibers 照抄 C1 现值"
                        f"（对齐矩阵 §5 问题 5 同族差集）"
                    )
        # mark/slot_name 一并入 payload——投影口径字典与 DB 行同键（幂等比对）。
        name = str(payload["name"])
        payload["mark"] = name[0] if name[:1] in ("★", "☆") else None
        payload["slot_name"] = metric_slot_name(name)
        enriched.append(SeedRow(seed.domain, seed.row_id, payload, seed.ontology_refs))
    return enriched, warnings


# ---------- 读侧展示串派生（00 R2 先例：expires_display/grain_display 不落列——P1-01b） ----------


def metric_grain_display(grain: str, unit: str) -> str:
    """粒度·单位读侧拼装串（C1 端点 3 页签列形；sem_metric.grain/unit 存储值不动——裁决 e）。

    拼装口径＝C1 合同「合并串＝grain + ' · ' + unit」；唯一渲染差：M3 真源把
    维度并进粒度的斜杠形（如 #1「月/区块·油田」）转 C1 列形括注族
    「月（按区块 / 油田）」——P1-01b 裁决：本体存储值不动、展示串读侧拼装。
    """
    if "/" in grain:
        base, dims = grain.split("/", 1)
        grain_part = f"{base}（按{' / '.join(dims.split('·'))}）"
    else:
        grain_part = grain
    return f"{grain_part} · {unit}"


def term_expiry(status_key: str, expires_at: date | None, today: date) -> tuple[bool, str]:
    """术语有效期读侧派生：(expired, expires_display)（F60 到日即标＋C1 展示串族）。

    expired＝到日即标（expires_at <= today——含当日）；展示串派生规则（复现 C1
    全部现值）：禁用词「—（已禁用）」→ 无期「长期」（引用类追加后缀）→ 已届满
    「<ISO>（已届满）」→ 其余 ISO 原样。R2：派生串不入库、不参与计算。
    """
    if status_key == "禁用词":
        return False, "—（已禁用）"
    if expires_at is None:
        suffix = "（引用类）" if status_key == "有效（引用马涛）" else ""
        return False, f"长期{suffix}"
    expired = expires_at <= today
    display = f"{expires_at.isoformat()}（已届满）" if expired else expires_at.isoformat()
    return expired, display
