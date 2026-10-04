"""domains.wells 纯语义单测——合同常量收编行＋归一化＋合并视图＋403/404 闸。

合同锚：A2-井档案.md v0.2（常量表/DTO 节/行为规则 1）；纯函数面——无 DB、
无框架（B1）。PG16 集成（fixture 井数据走 midplatform 实连）见
test_wells_contract_pg.py；API 形状见 tests/api/test_wells_api.py。
"""

import pytest

from app.domains.security import ForbiddenError
from app.domains.wells import (
    CHAIN_TABS,
    CHANGE_TICKET_STATUSES,
    DEVICE_STATUS_VALUES,
    DEVICE_TYPES,
    MEASURE_TYPES,
    PLANE_VALUES,
    RECORD_KINDS,
    WELL_KIND_BY_CODE,
    WELL_STATUS_VALUES,
    EventView,
    MeasureView,
    OverhaulView,
    WellNotFoundError,
    build_events,
    device_foot_for,
    device_snapshot_for,
    foot_note_for,
    measure_demo_copy,
    measure_foot_for,
    normalize_well_id,
    quality_notes_for,
    resolve_visible_well,
    tail_for,
)

# ---------- (b) 合同常量断言（A2 v0.2 常量表——值域冻结，注源随行） ----------


def test_contract_constants_well_domain() -> None:
    """井别码/井状态四枚举（设定书 §A.1——常量表两行）。"""
    assert WELL_KIND_BY_CODE == {"EW": "采油", "IW": "注水"}
    assert WELL_STATUS_VALUES == ("生产中", "停产", "检修", "待弃置")


def test_contract_constants_ledger_enums() -> None:
    """措施/设备类型枚举＋纪录合并类型三值＋关系链五页签（页面规格 §A2 F2）。"""
    assert MEASURE_TYPES == ("压裂", "酸化", "补孔", "调剖")
    assert DEVICE_TYPES == ("电泵", "螺杆泵", "加热炉")
    assert RECORD_KINDS == ("措施", "检修", "状态变更")
    assert CHAIN_TABS == ("纪录", "措施", "设备", "检修", "变动")


def test_contract_constants_change_ticket() -> None:
    """变动单状态四枚举＋面三枚举（F47 四态三面——投影展示值域）。"""
    assert CHANGE_TICKET_STATUSES == ("待审批", "已执行", "已驳回", "已撤回")
    assert PLANE_VALUES == ("数据面", "配置面", "语义面")


def test_contract_constants_v02_collected_rows() -> None:
    """v0.2 收编两行（开放问题 5 关单——Owner 2026-10-04 拍板）：设备状态三枚举
    ＝展示常量不回推导台账字段；措施效果列口径＝演示粒度文案常量。"""
    assert DEVICE_STATUS_VALUES == ("运行中", "停机检修", "随井停用")
    # 口径落地面：result 取冻结演示文案（不回推 §A.5 incr_oil_annual）——
    # copy 表存在且值形为（content, result）文案对
    copy = measure_demo_copy("N-02", "2025-09-06", "酸化")
    assert copy == ("近井地带解堵酸化", "日增油约 3 吨，三个月后回落")


# ---------- well_id 归一化（合同常量表——设定书 §4 规则 7） ----------


@pytest.mark.parametrize(
    ("raw_id", "expected"),
    [("N2", "N-02"), ("N-2", "N-02"), ("N-02", "N-02"), ("N11", "N-11"),
     ("N-6", "N-06"), ("N-21", "N-21"), ("", ""), ("X-01", "X-01")],
)
def test_normalize_well_id(raw_id: str, expected: str) -> None:
    assert normalize_well_id(raw_id) == expected


# ---------- 端点 2 冻结派生（foot_note/quality_notes） ----------


def test_foot_note_by_kind() -> None:
    """卡底注记服务端按井别派生：注水井＝冻结文案、采油井/缺省＝null。"""
    assert foot_note_for("IW") == '注水井无日产油记录，"产量最高"类排名自动排除本井。'
    assert foot_note_for("EW") is None
    assert foot_note_for(None) is None


def test_quality_notes_n11_only() -> None:
    """红字质量备注：仅 N-11 两条（逐字照抄合同 JSON），其余井空数组。"""
    notes = quality_notes_for("N-11")
    assert notes == [
        '台账状态"停产"与产量表 9-14 仍有开井 6.5 小时记录并存（状态滞后，已提示数据岗）。',
        (
            '产量表单位误录：9-14 日产油 12.40"方"'
            "（按渤中密度 0.89 t/m³ 折算 ≈11.04 吨，已提示数据岗）。"
        ),
    ]
    assert quality_notes_for("N-02") == []
    assert quality_notes_for("N-99") == []


# ---------- 端点 3 页签尾注与 tail（通版公式＋前缀变体＋待装配如实标注） ----------


def test_feet_generic_and_variants() -> None:
    assert measure_foot_for("N-02") == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert device_foot_for("N-02") == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    # N-06 措施尾注前缀变体（逐字照抄）；设备尾注通版
    assert measure_foot_for("N-06") == (
        "注水井措施以调剖为主（类型枚举：压裂 / 酸化 / 补孔 / 调剖）"
    )
    assert device_foot_for("N-06") == "设备类型枚举：电泵 / 螺杆泵 / 加热炉"
    # N-11 设备尾注前缀变体；措施尾注通版（措施 0 行照显——常驻尾注）
    assert measure_foot_for("N-11") == "措施类型枚举：压裂 / 酸化 / 补孔 / 调剖"
    assert device_foot_for("N-11") == (
        "检泵作业对象＝抽油设备（类型枚举：电泵 / 螺杆泵 / 加热炉）"
    )
    # 非演示井恒通版
    assert measure_foot_for("N-99") == measure_foot_for("N-02")
    assert device_foot_for("N-99") == device_foot_for("N-02")


def test_tail_assembled_annotation() -> None:
    """tail＝受效关系「待装配」如实标注（N-06——不洗白）＋追溯结论（N-11）；
    无冻结演示值的井＝null。"""
    assert tail_for("N-06") == (
        "关系：N-06 —受效→ 受效油井（劈分系数 Σ=1）——受效井清单未装配"
    )
    assert tail_for("N-11") == (
        "追溯结论：本井停产环节＝检泵作业（检修台账）；措施层无在案记录。遍历深度为受控参数"
    )
    assert tail_for("N-02") is None
    assert tail_for("N-99") is None


def test_device_snapshot_enum_domain() -> None:
    """设备行快照：status 全落设备状态三枚举值域（收编行①）；note 含停机原因
    码新旧归一文案（§A.7/§4 规则 8）；非演示井空。"""
    for well_id in ("N-02", "N-06", "N-11"):
        for row in device_snapshot_for(well_id):
            assert row.status in DEVICE_STATUS_VALUES
    n11 = {row.key: row for row in device_snapshot_for("N-11")}
    assert n11["d1"].status == "停机检修"
    assert n11["d1"].note == "本次检泵作业对象；停机原因编码：新 BELT（旧 R3＝皮带断）"
    assert n11["d2"].status == "随井停用"
    assert device_snapshot_for("N-99") == ()


def test_measure_demo_copy_keys() -> None:
    """措施冻结文案按（井, 作业日, 措施类型）取；无冻结值行＝None（如实留空）。"""
    assert measure_demo_copy("N-02", "2026-03-18", "调剖") == (
        "主力层段调剖，调整吸水剖面", "综合含水降 1.2 个点",
    )
    assert measure_demo_copy("N-06", "2023-05-18", "调剖") == (
        "井组调剖", "受效油井组见效（响应起始日随台账）",
    )
    assert measure_demo_copy("N-02", "2020-01-01", "压裂") is None
    assert measure_demo_copy("N-99", "2026-03-18", "调剖") is None


# ---------- 403/404 闸（行为规则 1②③——纯语义三分支） ----------


class _Row:
    """闸判别用的占位行（闸只看「在/不在」，不触行内容）。"""


def test_gate_visible_passthrough() -> None:
    row = _Row()
    assert resolve_visible_well(row, object(), "N-02") is row


def test_gate_exists_but_denied_403() -> None:
    """过滤内查无＋库内实有＝存在但无权 → 403（ForbiddenError——security 同源）。"""
    with pytest.raises(ForbiddenError):
        resolve_visible_well(None, _Row(), "N-02")


def test_gate_absent_404() -> None:
    """过滤内外皆无＝世界里根本没有 → 404（WellNotFoundError）。"""
    with pytest.raises(WellNotFoundError):
        resolve_visible_well(None, None, "N-99")


# ---------- 端点 3 纪录合并视图（服务端编排——合同倒序全序） ----------


def _m(key: str, date: str, mtype: str, content: str | None, result: str | None) -> MeasureView:
    return MeasureView(key=key, date=date, type=mtype, content=content, result=result)


def _o(key: str, start: str, end: str, job: str, impact: str, batch: str) -> OverhaulView:
    return OverhaulView(
        key=key, date_start=start, date_end=end, job=job, impact=impact, batch=batch
    )


def test_build_events_n02_full_order() -> None:
    """N-02 倒序全序＝m1→m2→o1→m3→m4→m5（合同端点 3 注——排序键：措施作业日/
    检修完工日；检修行 outcome 拼批次；date_end 仅检修行携带）。"""
    measures = [
        _m("m1", "2026-03-18", "调剖", "主力层段调剖，调整吸水剖面", "综合含水降 1.2 个点"),
        _m("m2", "2025-09-06", "酸化", "近井地带解堵酸化", "日增油约 3 吨，三个月后回落"),
        _m("m3", "2024-06-12", "补孔", "Ⅱ油组补孔", "日增油约 5 吨"),
        _m("m4", "2023-04-20", "压裂", "主力层重复压裂", "日增油约 8 吨，递减较快"),
        _m("m5", "2022-08-15", "调剖", "笼统注水条件下调剖", "综合含水降 0.8 个点"),
    ]
    overhauls = [
        _o(
            "o1", "2024-10-09", "2024-10-11", "检泵（泵轴更换）",
            "影响产量约 18 吨", "批次 20241012-T2",
        ),
    ]
    events = build_events(measures, overhauls, [])
    assert [e.key for e in events] == ["m1", "m2", "o1", "m3", "m4", "m5"]
    assert all(e.kind == "措施" for e in events[:2])
    assert events[2].kind == "检修"
    assert events[2].date == "2024-10-09"
    assert events[2].date_end == "2024-10-11"
    assert events[2].outcome == "影响产量约 18 吨 · 批次 20241012-T2"
    assert events[2].title == "检泵（泵轴更换）"
    # 措施行 title＝「类型 · 内容」、outcome＝效果列、无 date_end
    assert events[0].title == "调剖 · 主力层段调剖，调整吸水剖面"
    assert events[0].outcome == "综合含水降 1.2 个点"
    assert all(e.date_end is None for e in events if e.kind == "措施")


def test_build_events_measure_without_content() -> None:
    """内容缺省措施行（台账列形缺口）：title＝仅类型、outcome 随 result 缺省。"""
    events = build_events([_m("m1", "2026-01-01", "酸化", None, None)], [], [])
    assert events[0].title == "酸化"
    assert events[0].outcome is None


def test_build_events_status_changes_with_warning() -> None:
    """状态变更行：按发生日并入倒序、outcome＝警示文案（N-11 形——s2 最新在
    前、源键 s{id} 保持源锚）。"""
    status = [
        EventView(
            key="s1", kind="状态变更", date="2026-08-30", date_end=None,
            title='台账状态变更为"停产"',
            outcome="状态滞后：9-14 产量表仍有开井 6.5 小时记录，已提示数据岗。",
        ),
        EventView(
            key="s2", kind="状态变更", date="2026-09-07", date_end=None,
            title="检泵结束，作业区申请复产",
            outcome='档案状态仍记"停产"：复产待确认，状态滞后自 9-07 起。',
        ),
    ]
    overhauls = [
        _o("o1", "2026-08-28", "2026-09-06", "检泵", "影响产量约 210 吨", "批次 20260911-T3"),
    ]
    events = build_events([], overhauls, status)
    assert [e.key for e in events] == ["s2", "o1", "s1"]
    assert events[0].outcome == '档案状态仍记"停产"：复产待确认，状态滞后自 9-07 起。'
    assert events[2].kind == "状态变更"


def test_build_events_empty() -> None:
    """空台账：合并视图空（页面空态文案「近一年无措施 / 检修 / 状态变更记录」
    由前端照抄渲染——服务端只返空数组）。"""
    assert build_events([], [], []) == []
