"""domains.dataops.quality.domain —— E2 质检台管理面领域语义（厚：合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/E2-数据质量台.md v0.5，只引路径不复制
正文；实现选型不在冻结范围）：
- 端点 1/2：规则列表/启停——停用＝任务跳过不删；规则判据权威源＝本体仓 bohai 域
  M3 规则（ontology/bohai/m3-rule-model.yaml，E2 行为约定 9；本文件只读引用语义，
  判据文本固化在 DP-05 迁移 0015 种子，不二次维护）。
- 端点 6/7：问题单五态状态机——分发(0)→认领(1)→整改(2)→复核(3)→关闭(4)；
  复核**仅登记待复扫**（v0.5 降级：自动复扫挂观察）；复扫＝人工触发
  ``action:"rescan"``（复扫不是流转，lane 不变）；关闭守卫＝verify 复扫全绿
  或 close_note 免修原因，二者皆无 422 拒绝；关闭为终态，再流转 409。
- 端点 8：三 tier 水位——promise=T-1 常量，达标/落后 N 天判定后端算（本文件
  freshness_judgment）；汇总层展示名「汇总层（问数用）」（合同示例冻结形）。
- 端点 9：隔离区 append-only 读——坏行 payload+rule_no+batch_id 永不改写；
  整批拒收落批次级记录；告警类规则不产生隔离行。
- 挂单语义（v0.2/v0.5）：同一问题按（规则＋对象＋数据日期）去重——重复命中
  不新建、追加既有问题单 hit_count+1；在途单（认领/整改/复核中）跨轮不清。
  本域只落服务端语义（register_hit——M-05b 执行通道为触发源）。

B1：本模块禁 import fastapi/starlette。B12：审计写口归 security.audit（api 层
编排——retrieval 先例）；本文件只持语义与错误类型，不触 DB。
rescan 执行缝：增量复扫走数据面质检通道（E2 端点 7 注记）——通道接线归 M-05b；
本域以 ``RescanExecutor`` callable 承缝（B9 同款运行期只见 callable），缺省
未接＝QualityTaskChannelDeferredError（501 诚实壳，不 mock 假复扫结论）。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

# ---------- 五态状态机（合同端点 6/7 冻结值） ----------

LANES: tuple[str, ...] = ("分发", "认领", "整改", "复核", "关闭")
LANE_DISTRIBUTION = 0  # 分发（初始态——建单即此态，责任岗按规则配置自动分派）
LANE_CLAIMED = 1  # 认领
LANE_FIXING = 2  # 整改
LANE_REVIEW = 3  # 复核（仅登记待复扫——v0.5 人工触发复扫）
LANE_CLOSED = 4  # 关闭（终态）

RESCAN_ACTION = "rescan"  # 端点 7 请求体可选动作（P2-02 前端已同步同形）

# 复扫全绿结论固定文案（verify.note 机器可判哨兵——回填与关闭守卫共用本常量，
# M-05b 真通道回填同词表；「仍有命中」结论携带明细非固定串）。
RESCAN_GREEN_NOTE = "复扫全绿——修正批次未再命中"


def rescan_note(green: bool, detail: str | None) -> str:
    """复扫结论 → verify.note（全绿＝固定哨兵；仍有命中＝明细随行）。"""
    if green:
        return RESCAN_GREEN_NOTE
    return f"仍有命中：{detail or '明细见隔离区（按 issue_id 过滤）'}"


def is_verify_green(verify: VerifyView | None) -> bool:
    """verify 复扫全绿判定（关闭守卫半边——close_note 免修路径在 service）。"""
    return verify is not None and verify.note == RESCAN_GREEN_NOTE


def next_lane(current: int) -> int:
    """五态线性推进的唯一合法目标态（分发→认领→整改→复核→关闭；无回退）。"""
    if current < LANE_DISTRIBUTION or current > LANE_CLOSED:
        raise QualityParamError(f"问题单态越界：{current}（合法 0-4）")
    return current + 1


# ---------- 挂单去重键（v0.2/v0.5——规则＋对象＋数据日期） ----------

DEDUPE_KEY_MAX_LEN = 128  # quality_issue.dedupe_key 列宽（DP-05 0015）


def build_dedupe_key(rule_no: int, object_key: str, data_date: str) -> str:
    """挂单去重键：规则＋对象＋数据日期（技术列 uq_quality_issue_dedupe_key）。

    object_key＝问题对象标识（井号/批次号等，触发源给定）；data_date＝数据日期
    ISO 串。超列宽即参数错（400）——不静默截断（截断会造出假同单）。
    """
    key = f"{rule_no}|{object_key}|{data_date}"
    if len(key) > DEDUPE_KEY_MAX_LEN:
        raise QualityParamError(
            f"挂单去重键超长（{len(key)}>{DEDUPE_KEY_MAX_LEN}）：{key}"
        )
    return key


# ---------- 复扫执行缝（增量复扫走数据面质检通道——通道接线归 M-05b） ----------


@dataclass(frozen=True, slots=True)
class RescanRequest:
    """复扫请求（服务端 → 执行通道）：单号＋命中规则号（通道自寻修正批次）。"""

    issue_id: str
    rule_no: int


@dataclass(frozen=True, slots=True)
class RescanOutcome:
    """复扫结论（执行通道 → 服务端）：修正批次标识＋是否全绿＋命中明细摘要。"""

    batch: str
    green: bool
    detail: str | None = None


RescanExecutor = Callable[[RescanRequest], Awaitable[RescanOutcome]]


# ---------- 水位 T-1 判定（端点 8——承诺 T-1＝昨天的数今天要能看到） ----------

WATER_PROMISE = "T-1"
WATER_TIER_ORDER: tuple[str, ...] = ("原始层", "清洗层", "汇总层")
WATER_LAYER_DISPLAY: dict[str, str] = {
    "原始层": "原始层",
    "清洗层": "清洗层",
    "汇总层": "汇总层（问数用）",  # 合同端点 8 示例冻结形（问数用表标注）
}
FRESHNESS_OK_TAG = "达标（承诺 T-1）"
FRESHNESS_LATE_TAG = "落后 {n} 天 · 超期"
COLOR_OK = "green"
COLOR_LATE = "gold"


def freshness_judgment(
    data_date: date, today: date
) -> tuple[str, str, int]:
    """T-1 判定（纯函数）：→ (tag, color, 落后天数)。

    基准＝T-1（today−1）：data_date ≥ T-1 即达标（承诺 T-1/green）；否则
    落后 N 天＝T-1 基准日 − data_date（合同端点 8 示例：基准 09-14 对
    data_date 09-11 → 落后 3 天 · 超期/gold）。
    """
    baseline = today - timedelta(days=1)
    late = (baseline - data_date).days
    if late <= 0:
        return FRESHNESS_OK_TAG, COLOR_OK, 0
    return FRESHNESS_LATE_TAG.format(n=late), COLOR_LATE, late


# ---------- 读写面值对象（store 行 → service 投影 → api 逐字段） ----------


@dataclass(frozen=True, slots=True)
class RuleView:
    """规则列表行（端点 1 DTO；autoFix 合同冻结 camelCase，其余 snake）。"""

    no: int
    kind: str
    rule: str
    crit: str
    enabled: bool
    action: str
    auto_fix: bool


@dataclass(frozen=True, slots=True)
class RuleToggleReceipt:
    """规则启停回执（端点 2 → 200 {no, enabled}）。"""

    no: int
    enabled: bool


@dataclass(frozen=True, slots=True)
class QrowView:
    """隔离/拦截明细行（qrows——该单对应坏行/被拒批次：位置＋说明）。"""

    loc: str | None
    note: str | None


@dataclass(frozen=True, slots=True)
class VerifyView:
    """整改与复验（verify：修正批次标识＋复扫结论）。"""

    batch: str
    note: str


@dataclass(frozen=True, slots=True)
class IssueView:
    """问题单列表行（端点 6 DTO——ai_note 服务端投影规则判据，v0.5 降级）。"""

    id: str
    lane: int
    rule_no: int
    hit_count: int
    title: str | None
    desc: str | None
    owner: str | None
    qrows: list[QrowView]
    ai_note: str | None
    verify: VerifyView | None
    close_note: str | None


@dataclass(frozen=True, slots=True)
class IssueListPage:
    """问题单列表页（lanes 常量＋分页预留信封——v0.5 page/pageSize/total）。"""

    lanes: tuple[str, ...]
    items: list[IssueView]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True, slots=True)
class TransitionReceipt:
    """流转回执（端点 7 → 200 {id, lane, state, verify}；rescan 同形 lane 不变）。"""

    issue_id: str
    lane: int
    verify: VerifyView | None

    @property
    def state(self) -> str:
        """五态展示名（LANES[lane]——合同冻结值）。"""
        return LANES[self.lane]


@dataclass(frozen=True, slots=True)
class HitReceipt:
    """挂单语义回执（register_hit——M-05b 触发源消费）：attached＝挂既有单。"""

    issue_id: str
    attached: bool
    hit_count: int
    lane: int


@dataclass(frozen=True, slots=True)
class FreshnessView:
    """水位行（端点 8 DTO——layer 展示名＋to 展示串＋后端判定 tag/color）。"""

    layer: str
    to: str
    promise: str
    tag: str
    color: str


@dataclass(frozen=True, slots=True)
class QuarantineView:
    """隔离区行（端点 9 DTO——payload 原样；created_at 展示串 R2）。"""

    batch_id: str
    rule_no: int
    action: str
    loc: str | None
    payload: dict[str, Any]
    issue_id: str | None
    created_at: str


# ---------- 错误类型（映射归 api/errors.py——00 §3 错误包） ----------


class QualityParamError(Exception):
    """入参形状非法（00 §3.2 400；code=quality_param_invalid）。"""


class QualityRuleNotFoundError(Exception):
    """规则不存在（404；code=quality_rule_not_found——PATCH 未知规则号）。"""


class QualityIssueNotFoundError(Exception):
    """问题单不存在（404；code=quality_issue_not_found）。"""


class QualityIssueStateError(Exception):
    """状态机冲突（409；code=quality_issue_state）——终态再流转/非复核态复扫。"""


class QualityCloseBlockedError(Exception):
    """关闭守卫拒收（合同端点 7 冻结 422；code=quality_close_not_verified）——
    verify 复扫全绿与 close_note 免修原因二者皆无。"""


class QualityTaskChannelDeferredError(Exception):
    """任务/复扫执行通道未接通（501 端点壳——执行通道归 M-05b，不 mock 假任务）。"""
