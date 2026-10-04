"""domains.wells.domain —— 井档案域合同常量、冻结演示文案、读模型视图与纯语义。

合同锚（真源 teach-petro-agent/specs/api/A2-井档案.md v0.2——只引路径不复制正文；
本文件冻结值＝常量表两行收编＋DTO 节演示文案逐字照抄，行为规则 5「样本业务
事实零新增、不改值不加戏」）：
- 合同常量：井别码 EW=采油/IW=注水（设定书 §A.1）、井状态四枚举、措施/设备
  类型枚举、纪录合并类型三值、关系链五页签、变动单状态四枚举、面三枚举、
  设备状态三枚举（v0.2 收编——展示常量不回推导台账字段，开放问题 5 关单）、
  措施效果列口径（v0.2 收编——result＝演示粒度文案常量，不回推 §A.5
  incr_oil_annual）、well_id 归一化（N2/N-2→N-02，设定书 §4 规则 7）。
- 端点 2 卡底注记按井别派生（注水井=冻结文案、采油井=None）；quality_notes＝
  合同冻结红字数组（仅 N-11 两条——E2 井维度关联键挂 E2 批，开放问题 2 关单）。
- 端点 3 页签尾注（measure_foot/device_foot）＝通版公式＋N-06/N-11 前缀变体
  逐字照抄；tail＝受效关系「待装配」如实标注（N-06）与追溯结论（N-11）冻结
  文案——well_effect_relation 待装配（99 §2.3），装配批启用后本形状不变。
- 行为规则 1：403/404 双向分清（直调越权 403/不存在 404——开放问题 6 裁决；
  预埋期谓词恒真 → 403 分支不可达，形状照写）。

B1：本模块禁 import fastapi/starlette；B14：纯读域无时钟消费。
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.domains.security import ForbiddenError

# ---------- 合同常量（A2 v0.2 常量表——不可改，注源照抄） ----------

WELL_KIND_BY_CODE: dict[str, str] = {"EW": "采油", "IW": "注水"}  # 设定书 §A.1 well_type
WELL_STATUS_VALUES: tuple[str, ...] = ("生产中", "停产", "检修", "待弃置")  # §A.1 current_status
MEASURE_TYPES: tuple[str, ...] = ("压裂", "酸化", "补孔", "调剖")  # §A.5 · 页面尾注
DEVICE_TYPES: tuple[str, ...] = ("电泵", "螺杆泵", "加热炉")  # §A.7 equip_type · 页面尾注
RECORD_KINDS: tuple[str, ...] = ("措施", "检修", "状态变更")  # 页面规格 §A2 F2（events.kind）
CHAIN_TABS: tuple[str, ...] = ("纪录", "措施", "设备", "检修", "变动")  # 页面规格 §A2 F2
CHANGE_TICKET_STATUSES: tuple[str, ...] = ("待审批", "已执行", "已驳回", "已撤回")  # F47 四态
PLANE_VALUES: tuple[str, ...] = ("数据面", "配置面", "语义面")  # F47 三面
# v0.2 收编行①：设备状态三枚举——展示常量，不回推导 §A.7 台账字段（开放问题 5 关单）
DEVICE_STATUS_VALUES: tuple[str, ...] = ("运行中", "停机检修", "随井停用")
# v0.2 收编行②：措施效果列口径——result＝演示粒度文案常量（"日增油约 X 吨…"粒度），
# 不回推 §A.5 incr_oil_annual 年度增油字段（开放问题 5 关单）——本口径即「result 列
# 取冻结演示文案」的实现依据，见 _MEASURE_DEMO_COPY。
# 停机原因码（新旧并存）：新 BELT（旧 R3＝皮带断）——展示按映射表归一（§A.7/§4 规则 8）。
STOP_REASON_NORMALIZATION = "新 BELT（旧 R3＝皮带断）"

# well_id 归一化（合同常量表——设定书 §4 规则 7：N2/N-2→N-02；路径参数一律用
# 归一化后主键，未归一化形态服务端归一处理、不另设错误码）。
_NORM_WELL_ID = re.compile(r"^[Nn]-?(\d{1,2})$")


def normalize_well_id(raw_id: str) -> str:
    """well_id 归一化：N2/N-2→N-02（两位零填充）；非井号形态原样返回。"""
    rid = (raw_id or "").strip()
    matched = _NORM_WELL_ID.match(rid)
    if matched:
        return f"N-{int(matched.group(1)):02d}"
    return rid


# ---------- 错误（404＝世界里没有——接口层映射错误包 well_not_found） ----------


class WellNotFoundError(Exception):
    """井不存在（归一化后无此主键）——A2 错误码草案 404。"""


def resolve_visible_well(
    filtered: object | None, unfiltered: object | None, well_id: str
) -> object:
    """直调越权闸（行为规则 1②③，纯函数——三分支可单测）。

    行级过滤内查无＋库内实有＝存在但无权 → ForbiddenError（403，security
    同源异常——接口层既有映射）；过滤内外皆无＝世界里根本没有 → 404。
    预埋期谓词恒空（M-01 with_row_filter 恒真）→ 403 分支不可达，形状照写
    （开放问题 6 裁决：未来真分权启用时不改读面）。返回值语义＝已确认可见
    的档案行（调用方持有具体行类型）。
    """
    if filtered is not None:
        return filtered
    if unfiltered is not None:
        raise ForbiddenError(
            f"井 {well_id} 不在当前角色数据域内——直调越权（行级权限，403 留给直调）"
        )
    raise WellNotFoundError(f"井不存在（归一化后无此主键）：{well_id}")


# ---------- 冻结演示文案（逐字照抄 A2 v0.2 DTO 节与 A2.jsx 种子——注源随行） ----------

# 端点 2 foot_note：服务端按井别派生（注水井＝冻结文案；采油井＝null）。
FOOT_NOTE_INJECTION = '注水井无日产油记录，"产量最高"类排名自动排除本井。'


def foot_note_for(kind_code: str | None) -> str | None:
    """卡底注记派生（端点 2 foot_note——「产量最高」类排名排除口径与 A1 问数同源）。"""
    return FOOT_NOTE_INJECTION if kind_code == "IW" else None


# 端点 2 quality_notes：红字质量备注（仅 N-11 两条——状态滞后/单位误录；其余井
# 空数组）。来源锚：§A.1 状态滞后 × §A.2 9-14 矛盾行；§A.2 12.40方 × §2.2 渤中
# 0.89 t/m³ × §4 规则 3。与 E2 问题单同源——井维度关联键挂 E2 批（开放问题 2 关单）。
_QUALITY_NOTES_COPY: dict[str, tuple[str, ...]] = {
    "N-11": (
        '台账状态"停产"与产量表 9-14 仍有开井 6.5 小时记录并存（状态滞后，已提示数据岗）。',
        (
            '产量表单位误录：9-14 日产油 12.40"方"'
            "（按渤中密度 0.89 t/m³ 折算 ≈11.04 吨，已提示数据岗）。"
        ),
    ),
}


def quality_notes_for(well_id: str) -> list[str]:
    """红字质量备注数组（演示口径只读摘要先行——关联键待 E2 批）。"""
    return list(_QUALITY_NOTES_COPY.get(well_id, ()))


# 端点 3 页签枚举尾注：通版公式＋随井前缀变体（N-06 措施/N-11 设备——演示值
# 逐字照抄；非演示井恒通版，变体扩随合同变更记录）。
MEASURE_FOOT_GENERIC = f"措施类型枚举：{' / '.join(MEASURE_TYPES)}"
DEVICE_FOOT_GENERIC = f"设备类型枚举：{' / '.join(DEVICE_TYPES)}"
_FOOT_VARIANTS: dict[str, dict[str, str]] = {
    "N-06": {"measure": "注水井措施以调剖为主（类型枚举：压裂 / 酸化 / 补孔 / 调剖）"},
    "N-11": {"device": "检泵作业对象＝抽油设备（类型枚举：电泵 / 螺杆泵 / 加热炉）"},
}


def measure_foot_for(well_id: str) -> str:
    """措施页签尾注全文（页面以 foot 全文渲染，前端不自行拼装业务文案）。"""
    return _FOOT_VARIANTS.get(well_id, {}).get("measure", MEASURE_FOOT_GENERIC)


def device_foot_for(well_id: str) -> str:
    """设备页签尾注全文（同上）。"""
    return _FOOT_VARIANTS.get(well_id, {}).get("device", DEVICE_FOOT_GENERIC)


# 端点 3 tail：受效关系「待装配」如实标注（N-06——不洗白，装配批启用
# well_effect_relation 后本形状不变）＋追溯结论（N-11——F45 遍历深度受控参数）。
_TAIL_COPY: dict[str, str] = {
    "N-06": "关系：N-06 —受效→ 受效油井（劈分系数 Σ=1）——受效井清单未装配",
    "N-11": "追溯结论：本井停产环节＝检泵作业（检修台账）；措施层无在案记录。遍历深度为受控参数",
}


def tail_for(well_id: str) -> str | None:
    """关系链底部尾注（随井；无冻结演示值的井＝null）。"""
    return _TAIL_COPY.get(well_id)


# 措施台账演示文案（content/result——§A.5 落表列形无此两列：result 按收编行②
# ＝冻结演示文案承载、content 同为页面种子文案；键＝（归一化井号, 作业日, 措施
# 类型）。台账扩列装配批只换本表数据源，DTO 与投影零改动。
_MEASURE_DEMO_COPY: dict[tuple[str, str, str], tuple[str, str]] = {
    ("N-02", "2026-03-18", "调剖"): ("主力层段调剖，调整吸水剖面", "综合含水降 1.2 个点"),
    ("N-02", "2025-09-06", "酸化"): ("近井地带解堵酸化", "日增油约 3 吨，三个月后回落"),
    ("N-02", "2024-06-12", "补孔"): ("Ⅱ油组补孔", "日增油约 5 吨"),
    ("N-02", "2023-04-20", "压裂"): ("主力层重复压裂", "日增油约 8 吨，递减较快"),
    ("N-02", "2022-08-15", "调剖"): ("笼统注水条件下调剖", "综合含水降 0.8 个点"),
    ("N-06", "2026-07-22", "调剖"): ("P1 层调剖，控制单层突进", "P1 实注占比回落 5 个点"),
    ("N-06", "2025-12-15", "调剖"): ("笼统注水改分层分注前调剖", "为 2026-01 三层分注投运做准备"),
    ("N-06", "2024-09-10", "调剖"): ("P2 层调剖", "P2 吸水剖面改善"),
    ("N-06", "2023-05-18", "调剖"): ("井组调剖", "受效油井组见效（响应起始日随台账）"),
}


def measure_demo_copy(
    well_id: str, job_date: str, measure_type: str | None
) -> tuple[str, str] | None:
    """措施行 content/result 冻结文案（无冻结值的行＝None——台账列形缺口如实留空）。"""
    return _MEASURE_DEMO_COPY.get((well_id, job_date, measure_type or ""))


# 设备台账演示快照（设备行整行冻结——§A.7 落表 equip_status 现供给无井关联列
# 〔DP-03 DDL 注记「列缺疑点已登记」〕，按井取行装配批随中台扩列启用；status
# 取值域＝设备状态三枚举，note 含停机原因码新旧归一文案〔§4 规则 8〕）。
@dataclass(frozen=True, slots=True)
class DeviceSnapshotRow:
    key: str
    type: str
    status: str
    since: str
    note: str


_DEVICE_DEMO_SNAPSHOT: dict[str, tuple[DeviceSnapshotRow, ...]] = {
    "N-02": (
        DeviceSnapshotRow(
            key="d1", type="电泵", status="运行中", since="2021-04-12",
            note="2021 年换泵更新；上次保养 2026-06-02",
        ),
        DeviceSnapshotRow(
            key="d2", type="加热炉", status="运行中", since="2019-09-01",
            note="冬季高负荷、夏季低负荷",
        ),
    ),
    "N-06": (
        DeviceSnapshotRow(
            key="d1", type="电泵", status="运行中", since="2020-01-20",
            note="注水泵；泵压字段未采录（台账缺口）",
        ),
        DeviceSnapshotRow(
            key="d2", type="加热炉", status="运行中", since="2020-01-20",
            note="注水管线伴热",
        ),
    ),
    "N-11": (
        DeviceSnapshotRow(
            key="d1", type="螺杆泵", status="停机检修", since="2020-03-11",
            note="本次检泵作业对象；停机原因编码：新 BELT（旧 R3＝皮带断）",
        ),
        DeviceSnapshotRow(
            key="d2", type="加热炉", status="随井停用", since="2020-03-11",
            note="停产期间停用，复产后视情况投运",
        ),
    ),
}


def device_snapshot_for(well_id: str) -> tuple[DeviceSnapshotRow, ...]:
    """设备行演示快照（无冻结值的井＝空——「本井无设备行」空态由前端照抄渲染）。"""
    return _DEVICE_DEMO_SNAPSHOT.get(well_id, ())


# ---------- 读模型视图（端点 DTO 的领域半边——接口层逐字段投影） ----------


@dataclass(frozen=True, slots=True)
class WellSummary:
    """端点 1 列表行（下拉 option 所需字段响应全携带——拼装是前端展示层职责）。"""

    well_id: str
    well_name: str | None
    well_kind: str | None
    well_kind_code: str | None
    block_name: str | None
    current_status: str | None
    remark: str | None


@dataclass(frozen=True, slots=True)
class WellProfile:
    """端点 2 档案明细（8 字段＝井号/井名/井别/投产/平台/区块/状态/备注＋红字＋卡底）。"""

    well_id: str
    well_name: str | None
    well_kind: str | None
    well_kind_code: str | None
    first_prod_date: str | None
    platform: str | None
    block_name: str | None
    current_status: str | None
    remark: str | None
    quality_notes: list[str]
    foot_note: str | None


@dataclass(frozen=True, slots=True)
class MeasureView:
    """措施台账行（落表＝映射卡之 well_measures：measure_type/job_date→type/date）。"""

    key: str
    date: str
    type: str | None
    content: str | None
    result: str | None


@dataclass(frozen=True, slots=True)
class DeviceView:
    """设备台账行（status∈设备状态三枚举——v0.2 收编常量值域）。"""

    key: str
    type: str
    status: str
    since: str
    note: str


@dataclass(frozen=True, slots=True)
class OverhaulView:
    """检修台账行（落表＝well_overhaul 原名对应——99 §2.3 wells 读面）。"""

    key: str
    date_start: str | None
    date_end: str | None
    job: str | None
    impact: str | None
    batch: str | None


@dataclass(frozen=True, slots=True)
class EventView:
    """纪录合并视图行（kind∈纪录合并类型三值；date_end 仅检修行携带）。"""

    key: str
    kind: str
    date: str | None
    date_end: str | None
    title: str | None
    outcome: str | None


@dataclass(frozen=True, slots=True)
class ChainCounts:
    """五页签计数（changes＝变动页签计数，与端点 4 total 同源同值）。"""

    events: int
    measures: int
    devices: int
    overhauls: int
    changes: int


@dataclass(frozen=True, slots=True)
class ChainView:
    """端点 3 关系链读模型（合并视图＋三台账＋计数＋尾注——前端零拼算）。"""

    well_id: str
    counts: ChainCounts
    measure_types: list[str]
    device_types: list[str]
    measure_foot: str
    device_foot: str
    events: list[EventView]
    measures: list[MeasureView]
    devices: list[DeviceView]
    overhauls: list[OverhaulView]
    tail: str | None


@dataclass(frozen=True, slots=True)
class ChangeTicketItem:
    """变动投影行六字段（行为规则 4——「提出」列＝proposer＋time 拼装，DTO 六字段）。"""

    id: str
    status: str
    plane: str
    short: str
    proposer: str
    time: str


@dataclass(frozen=True, slots=True)
class ChangeTicketProjection:
    """端点 4 只读投影（主单在 A3——本页无任何写操作端点）。"""

    well_id: str
    items: list[ChangeTicketItem]
    total: int


def build_events(
    measures: Sequence[MeasureView],
    overhauls: Sequence[OverhaulView],
    status_changes: Sequence[EventView],
) -> list[EventView]:
    """「纪录」页签＝服务端合并视图（合同端点 3 events 节）。

    措施按作业日（date）、检修按完工日（date_end）、状态变更按发生日（date）
    统一时间键**倒序**合并；排序服务端完成，前端零编排。措施行 title＝
    「类型 · 内容」（内容缺省＝仅类型）、outcome＝效果列；检修行 outcome＝
    「影响 · 批次」拼装（缺段跳过）；状态变更行 outcome＝警示文案（可 null）。
    稳定排序：同键行保持「措施→检修→状态变更」入序（确定性全序）。
    """
    staged: list[tuple[str, EventView]] = []
    for m in measures:
        title = f"{m.type} · {m.content}" if m.content else m.type
        staged.append(
            (
                m.date,
                EventView(
                    key=m.key, kind="措施", date=m.date, date_end=None,
                    title=title, outcome=m.result,
                ),
            )
        )
    for o in overhauls:
        outcome = " · ".join(part for part in (o.impact, o.batch) if part) or None
        staged.append(
            (
                o.date_end or o.date_start or "",
                EventView(
                    key=o.key, kind="检修", date=o.date_start, date_end=o.date_end,
                    title=o.job, outcome=outcome,
                ),
            )
        )
    for s in status_changes:
        staged.append((s.date or "", s))
    staged.sort(key=lambda pair: pair[0], reverse=True)  # ISO 日期串字典序＝时间序
    return [event for _sort_key, event in staged]
