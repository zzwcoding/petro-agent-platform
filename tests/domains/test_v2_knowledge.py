"""V2-02 knowledge 语义读面验收——specs/knowledge.md「验收测试」表六条逐条落测。

六条对应（票面验收表，1:1 同名）：
- metric_exact_hit：指标精确命中→Evidence 带口径/binding_state=bound
  （日产油量——0019 种子 #201，冻结三绑定在册，口径支/粒度/单位随 value）。
- alias_canonicalize：别名（如 CEP-D 修饰形）归一命中且 source 注明「经别名归一」
  （台账内可命中对＝日产液→日产液量；CEP-D 修饰形验证别名表在位＋规范名不在
  台账时如实 None 不猜——specs/knowledge.md 行为约定 2 命中顺序第三态）。
- unbound_flagged：在册未绑定指标（含水率/配产量）→binding_state=unbound
  （V1 MEASURE_COLUMNS 冻结三绑定原样——二十指标恰三条 bound）。
- expired_flagged：届满术语→expired＋日期＋指引（日产液＝台账 #11，
  2026-06-30 届满、现口径指引「日产液量」随 type 在 value；禁用词压过届满、
  未到期不标——V1 term_expiry 派生序原样）。
- families_complete：families 覆盖三族标注（completion/monthly/dynamic）＋
  relation group 透传（本体导出物 config/relation_types.json 的 group 键原样）。
- readonly_inv2：全程只读（INV-2 断言）——四接口跑遍后快照深比对零变、
  返回容器为副本（外部改写不渗入）、seam 无写方法。

fixture＝问数组台账态（eval/answers/问数组-题目与答案.md「数据真源与版本绑定」：
20 指标/11 术语/10 对象/5 关系——手建快照，真库不在场；seam 级
InMemoryKnowledgeStore）。时钟注入固定 today（届满判定确定性，不吃墙上时钟）。
"""

from copy import deepcopy
from datetime import date

import pytest

from appv2.knowledge import (
    BINDING_BOUND,
    BINDING_EXPIRED,
    BINDING_UNBOUND,
    KIND_FAMILY,
    KIND_METRIC,
    KIND_OBJECT,
    KIND_RELATION,
    KIND_TERM,
    InMemoryKnowledgeStore,
    SemanticQuery,
    question_array_snapshot,
)

# 执行日钉 2026-10-08（票面日期）：日产液 2026-06-30 已届、躺井 2026-12-31 未届
# ——届满判定的两侧例都吃同一固定时钟，测试不随执行日漂移。
TODAY = date(2026, 10, 8)


def _store() -> InMemoryKnowledgeStore:
    return InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)


# ---------- 验收①：指标精确命中→Evidence 带口径/binding_state=bound ----------


def test_metric_exact_hit() -> None:
    store = _store()
    # 槽位名精确命中（台账 slot_name——问数链指标候选名同域）。
    ev = store.metric_by_name("日产油量")
    assert ev is not None
    assert ev.kind == KIND_METRIC
    assert ev.element_id == "201"
    assert ev.binding_state == BINDING_BOUND  # 冻结三绑定在册——可出数
    assert ev.version == "1"
    assert ev.scope == "日/井"  # 统计粒度域（plan 语境消费）
    # Evidence 带口径：定义含 agg 绑定列＋口径支名（C1 口径声明投影）。
    assert "agg.fct_daily_metering.oil_output" in ev.value
    assert "班次合计日口径" in ev.value
    # 台账原名（含括注尾缀）同命中一行。
    assert store.metric_by_name("日产油量（吨）") == ev
    # 台账无名——如实 None（不猜）。
    assert store.metric_by_name("不存在的指标") is None


# ---------- 验收②：别名归一命中且 source 注明 ----------


def test_alias_canonicalize() -> None:
    store = _store()
    # 别名表在位：票面点名 CEP-D 修饰形（GLS-PETRO-013 批——八键之两键）。
    aliases = store.aliases()
    assert aliases["CEP-D 生产平台"] == "CEP-D平台"
    assert aliases["CEP-D 井口平台"] == "CEP-D平台"
    # 命中顺序第二态：精确名未中→别名归一→命中，source 如实注「经别名归一」。
    ev = store.metric_by_name("日产液")
    assert ev is not None
    assert ev.kind == KIND_METRIC
    assert ev.element_id == "202"  # 归一落点＝日产液量（slot_name）
    assert ev.binding_state == BINDING_BOUND
    assert "经别名归一" in ev.source
    assert "日产液→日产液量" in ev.source
    # CEP-D 修饰形归一后的规范名不在 sem_* 台账——如实 None（行为约定 2 第三态）。
    assert store.metric_by_name("CEP-D 生产平台") is None
    # evidence 面同款归一（术语别名净产量→剔检产量，kind 过滤下仍命中）。
    hits = store.evidence(SemanticQuery(text="净产量", kinds=frozenset({KIND_TERM})))
    assert len(hits) == 1
    assert hits[0].element_id == "2"
    assert "经别名归一" in hits[0].source
    assert "净产量→剔检产量" in hits[0].source


# ---------- 验收③：在册未绑定指标→binding_state=unbound ----------


def test_unbound_flagged() -> None:
    store = _store()
    water = store.metric_by_name("含水率")
    assert water is not None
    assert water.binding_state == BINDING_UNBOUND  # 在册未绑定 agg 计量列
    assert water.element_id == "203"
    assert "暂不可出数" in water.value  # 台账原注随口径如实携带
    plan = store.metric_by_name("配产量")
    assert plan is not None
    assert plan.binding_state == BINDING_UNBOUND
    # 冻结三绑定全量核对：二十指标恰三条 bound（日产油量/日产液量/油压），
    # 其余十七条在册未绑定——「绑定目录即投影，不造第二份可出数清单」。
    metrics = store.evidence(SemanticQuery(text="", kinds=frozenset({KIND_METRIC})))
    assert len(metrics) == 20
    bound = {ev.element_id for ev in metrics if ev.binding_state == BINDING_BOUND}
    assert bound == {"201", "202", "205"}
    assert sum(1 for ev in metrics if ev.binding_state == BINDING_UNBOUND) == 17


# ---------- 验收④：届满术语→expired＋日期＋指引 ----------


def test_expired_flagged() -> None:
    store = _store()
    hits = store.evidence(SemanticQuery(text="日产液", kinds=frozenset({KIND_TERM})))
    assert len(hits) == 1  # 精确名先于别名——命中台账 #11 术语行本体
    ev = hits[0]
    assert ev.binding_state == BINDING_EXPIRED
    assert "2026-06-30（已届满）" in ev.freshness  # 届满日期（V1 展示串族）
    assert "日产液量" in ev.value  # 现口径指引（type＝别名 → 日产液量）
    # V1 term_expiry 派生序原样：禁用词压过届满（老完成率→已禁用，非 expired）。
    banned = store.evidence(SemanticQuery(text="老完成率", kinds=frozenset({KIND_TERM})))
    assert len(banned) == 1
    assert banned[0].binding_state == BINDING_UNBOUND
    assert "已禁用" in banned[0].freshness
    # 未到期不标届满（躺井 2026-12-31 > today）。
    live = store.evidence(SemanticQuery(text="躺井", kinds=frozenset({KIND_TERM})))
    assert len(live) == 1
    assert live[0].binding_state == BINDING_UNBOUND
    assert "已届满" not in live[0].freshness


# ---------- 验收⑤：families 覆盖三族标注＋relation group 透传 ----------


def test_families_complete() -> None:
    store = _store()
    families = store.families()
    # 本体导出物十行关系族标注透传（config/relation_types.json group 键原样）。
    assert set(families) == {
        "隶属", "承载", "受效", "作用于", "取样自",
        "下入", "射孔", "坐封", "配注", "加装",
    }
    assert families["隶属"] == ["completion", "monthly", "dynamic"]
    assert families["受效"] == ["monthly", "dynamic"]
    assert families["加装"] == ["monthly"]
    covered = {family for groups in families.values() for family in groups}
    assert covered == {"completion", "monthly", "dynamic"}  # 三族全覆盖
    # 族标注也是 evidence 消费面（kind=family——doc_retrieve 供给策略语境）。
    hits = store.evidence(SemanticQuery(text="射孔", kinds=frozenset({KIND_FAMILY})))
    assert len(hits) == 1
    assert hits[0].version == "1.1.0"  # 本体导出物 schema_version 随行
    assert "completion" in hits[0].value
    # kinds 闭世界：未知种类构造即拒（C1 slots domain 同款纪律）。
    with pytest.raises(ValueError, match="kinds"):
        SemanticQuery(text="射孔", kinds=frozenset({"nope"}))


# ---------- 验收⑥：全程只读（INV-2 断言） ----------


def test_readonly_inv2() -> None:
    snapshot = question_array_snapshot()
    store = InMemoryKnowledgeStore(snapshot, today=TODAY)
    before = deepcopy(snapshot)
    # 四接口跑遍（含命中/未命中/别名/浏览各态）。
    assert store.metric_by_name("日产油量") is not None
    assert store.metric_by_name("日产液") is not None
    assert store.metric_by_name("CEP-D 生产平台") is None
    assert store.metric_by_name("不存在的指标") is None
    assert store.evidence(SemanticQuery(text="躺井")) != []
    assert store.evidence(SemanticQuery(text="", kinds=frozenset({KIND_FAMILY}))) != []
    assert store.aliases() != {}
    assert store.families() != {}
    # fixture 台账态计数钉死（验收④：问数组台账态 20 指标/11 术语/10 对象/
    # 5 关系——浏览态逐类清点；族标注行＝导出物十行）。
    expected_counts = {
        KIND_METRIC: 20,
        KIND_TERM: 11,
        KIND_OBJECT: 10,
        KIND_RELATION: 5,
        KIND_FAMILY: 10,
    }
    for kind, expected in expected_counts.items():
        browse = store.evidence(SemanticQuery(text="", kinds=frozenset({kind})))
        assert len(browse) == expected, f"{kind} 台账态计数漂移：{len(browse)}≠{expected}"
    # 快照深比对零变（零写副作用——台账行禁手工改的读面侧镜像）。
    assert snapshot == before
    # 返回容器是副本：外部改写不渗入店内状态。
    aliases = store.aliases()
    aliases["污染键"] = "x"
    assert "污染键" not in store.aliases()
    families = store.families()
    families["隶属"].append("bad")
    assert "bad" not in store.families()["隶属"]
    # seam 无写方法（KnowledgeStore 四接口只读面——INV-2 的形状断言）。
    mutators = ("add", "update", "delete", "upsert", "insert", "save", "clear")
    assert not any(hasattr(store, name) for name in mutators)
