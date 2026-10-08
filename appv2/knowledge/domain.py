"""knowledge.domain —— Knowledge Evidence 语义读面的 schema 与判定逻辑。

specs/knowledge.md 接口定义节的两 schema 随本模块定稿（票面点名）：
- SemanticQuery＝{text, kinds?: set[metric|term|object|relation|family]}；
- Evidence＝{element_id, kind, value, source, version, freshness, scope, binding_state}。

binding_state 三态（V1 语义原样承载，specs/knowledge.md 行为约定 3「判定逻辑
原样移植，不得臆造」）：
- bound＝绑定 agg 计量列可出数——判定真源＝MEASURE_COLUMNS 冻结三绑定
  （V1 app/domains/chat/domain.py 注册目录原样：日产油量→oil_output／
  日产液量→liquid_output／油压→oil_pressure，M-06 冻结）；
- unbound＝在册未绑定（走降级）——台账在册而不在绑定目录的指标，以及
  本就无计量列绑定面的术语/对象/关系/族标注；
- expired＝届满漂移——term_expiry 派生（V1 app/domains/semantics/domain.py
  term_expiry 原样移植：禁用词压过届满、到日即标 expires_at <= today）。

本模块零 I/O、零第三方依赖（纯 stdlib dataclass）——供 store/snapshot 与
后续 query（unbound_degrade 依据 Evidence）共同消费。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# ---------- SemanticQuery kinds 闭世界（五类——specs/knowledge.md 接口定义） ----------

KIND_METRIC = "metric"
KIND_TERM = "term"
KIND_OBJECT = "object"
KIND_RELATION = "relation"
KIND_FAMILY = "family"
KIND_ALL: frozenset[str] = frozenset(
    {KIND_METRIC, KIND_TERM, KIND_OBJECT, KIND_RELATION, KIND_FAMILY}
)

# ---------- binding_state 三值 ----------

BINDING_BOUND = "bound"  # 绑定 agg 计量列可出数
BINDING_UNBOUND = "unbound"  # 在册未绑定（走降级）
BINDING_EXPIRED = "expired"  # 届满漂移


@dataclass(frozen=True, slots=True)
class SemanticQuery:
    """语义查询（evidence 入参——specs/knowledge.md 接口定义节定稿形状）。

    text＝查询文本（空串＝浏览态：返回 kinds 内全部要素的 Evidence）；
    kinds＝种类过滤（None＝全五类；值域闭世界 KIND_ALL——越界 ValueError，
    C1 端点 11 slots domain 同款纪律，构造即拒不进店）。
    """

    text: str
    kinds: frozenset[str] | None = None

    def __post_init__(self) -> None:
        if self.kinds is not None:
            unknown = self.kinds - KIND_ALL
            if unknown:
                raise ValueError(
                    f"SemanticQuery.kinds 越界（值域 {sorted(KIND_ALL)}）: {sorted(unknown)}"
                )


@dataclass(frozen=True, slots=True)
class Evidence:
    """Knowledge Evidence（sem_* 台账读成 agent 可消费的证据行）。

    字段语义（specs/knowledge.md 接口定义节；tools.md Observation 同形位——
    content←value、source_id←element_id、locator←source 的机读映射在工具层）：
    - element_id：台账行 id 的字符串承载（sem_metric#201 行记「201」；族标注行
      ＝本体导出物 relation_types.json 行 id）；
    - value：人话内容串（口径/定义/读法/族标注——机械拼装零发明，各账行字段
      原文内嵌）；
    - source：来源链 locator（表名#行 id 形，机读）；别名命中时如实追加
      「经别名归一（X→Y）」（specs/knowledge.md 行为约定 2）；
    - version：台账行版本（sem_relation 无版本列→None；族标注行＝导出物
      schema_version）；
    - freshness：台账时效标注串（术语＝term_expiry 展示串族——「2026-06-30
      （已届满）」「长期」「—（已禁用）」；台账无时效承载的种类＝空串，
      不发明标注）；
    - scope：统计粒度域（指标 grain——日/井等，plan 语境消费；其余空串）；
    - binding_state：三态判定（本模块 BINDING_*，推导真源见模块 docstring）。
    """

    element_id: str
    kind: str
    value: str
    source: str
    version: str | None
    freshness: str
    scope: str
    binding_state: str


# ---------- V1 MEASURE_COLUMNS 冻结三绑定（原样移植——判定真源单点） ----------

# 注册指标声明 → agg 计量列绑定（V1 app/domains/chat/domain.py MEASURE_COLUMNS
# 原样：99 §2.12 沿源口径 §A.2——oil_output 吨/liquid_output 方/oil_pressure MPa）。
# 台账行 slot_name 不在目录＝在册未绑定（含水率/配产量等）——走降级解释链，
# 不假绑定（问数组 F 族钉死的降级路径本读面侧真相源）。
MEASURE_COLUMNS: dict[str, tuple[str, str]] = {
    "日产油量": ("oil_output", "吨"),
    "日产液量": ("liquid_output", "方"),
    "油压": ("oil_pressure", "MPa"),
}


def metric_binding_state(slot_name: str) -> str:
    """指标 binding_state 判定（slot_name ∈ MEASURE_COLUMNS 键集→bound，否则 unbound）。

    可出数指标＝MEASURE_COLUMNS 键集（注册目录即投影，不造第二份可出数清单
    ——V1 同口径）。
    """
    return BINDING_BOUND if slot_name in MEASURE_COLUMNS else BINDING_UNBOUND


def term_expiry(status_key: str, expires_at: date | None, today: date) -> tuple[bool, str]:
    """术语有效期读侧派生：(expired, expires_display)——V1 semantics.domain 同名函数原样。

    expired＝到日即标（expires_at <= today，含当日）；展示串派生序：禁用词
    「—（已禁用）」→ 无期「长期」（引用类追加后缀）→ 已届满「<ISO>（已届满）」
    → 其余 ISO 原样。R2：派生串不入库、不参与计算（V1 同款）。
    """
    if status_key == "禁用词":
        return False, "—（已禁用）"
    if expires_at is None:
        suffix = "（引用类）" if status_key == "有效（引用马涛）" else ""
        return False, f"长期{suffix}"
    expired = expires_at <= today
    display = f"{expires_at.isoformat()}（已届满）" if expired else expires_at.isoformat()
    return expired, display


def term_binding_state(status_key: str, expires_at: date | None, today: date) -> str:
    """术语 binding_state 判定（届满→expired；其余在册未绑定——术语无计量列绑定面）。"""
    expired, _display = term_expiry(status_key, expires_at, today)
    return BINDING_EXPIRED if expired else BINDING_UNBOUND
