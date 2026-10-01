"""domains.gateway.domain —— 网关域语义（厚：路由/熔断/记账/演练合同语义在此闭环）。

合同锚（真源在 teach-petro-agent/specs/api/，只引路径不复制正文）：
- D1-模型与线路.md：7 条端点形状、config 四参数边界（allowedFails 1–10 /
  cooldownSeconds 10–600 / numRetries 0–5 / requestTimeout 5–120）、
  spend-logs 数据形状红线（token 两整数/毫秒整数/元数值，禁拼好的展示串）、
  演练三连（202 受理/轮询/历史；重入 409；done 落两笔账——备用记账行＋
  演练历史行；consecutive_fails/cooldown_sec 取当前配置值）、演练即真实流量。
- 98 §3.12 gateway 卡：complete（运行时唯一 LLM 出口——B6）、models、
  gateway_config、save_gateway_config（写回热加载；返回快照为唯一真值）、
  spend_logs、start_drill、drill、drill_history。
- ADR-0003 裁决 13（椒图蓝本）：切换判据＝网络错/超时/5xx 切备、4xx/429
  不切；per-attempt 超时；熔断触顶＝改路由不拒绝（降级组 petro-lite）、
  在途照跑完、进程生命周期内单向置位不自动恢复。
- D5-追踪与花费.md §8/9（阈值合同值，判据消费方＝本域 complete）：双阈值
  ＝单次 0.05 元＋累计 800 元/月（GATEWAY_BUDGET）；D1 v0.2（D5 撤页归并批）
  预算双阈值并入端点 2/3 config 族（>=0 校验、直接保存即生效、对后续调用生效
  不回溯）＋端点 8 spend-stats 聚合读面（caller 归因列聚合基础，存量可空归
  unattributed 桶）。
- 00 §5（异步任务双态 running|done、节点四态 wait|process|finish|error）、
  §13 档①（config 直改即生效——对后续调用生效，不回溯在途）、§14-R1
  （字段 snake_case——本端点即真实接线）。

B1：本文件不 import fastapi/starlette/DB/LLM——路由状态机、成本公式、
参数校验、演练节点文案都是纯语义；IO 归 store（PG）/service（编排）。
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

from app.infra.config import ModelEntry

# ---------- 调用参数（D1 端点 2/3——数值边界即合同值） ----------

ParamKey = Literal["allowed_fails", "cooldown_seconds", "num_retries", "request_timeout"]


@dataclass(frozen=True, slots=True)
class Completion:
    """complete() 的业务应答（运行时唯一 LLM 出口的返回——98 §3.12 卡首行）。"""

    content: str
    prompt_tokens: int
    completion_tokens: int
    usage_estimated: bool  # True＝上游无 usage，chars/4 估算（椒图蓝本）
    call_id: str  # 账本调用号（call-；错误包 trace_id 同族——00 §3.1）
    cost_yuan: float
    fallback: bool  # True＝由备用别名应答（请求别名冷却/被摘除）
    served_alias: str

# (下限, 上限)——D1 合同冻结；400 错误体 detail 的人话区间由此拼装。
PARAM_LIMITS: dict[ParamKey, tuple[int, int]] = {
    "allowed_fails": (1, 10),
    "cooldown_seconds": (10, 600),
    "num_retries": (0, 5),
    "request_timeout": (5, 120),
}
PARAM_ORDER: tuple[ParamKey, ...] = (
    "allowed_fails",
    "cooldown_seconds",
    "num_retries",
    "request_timeout",
)


class GatewayConfigError(Exception):
    """配置参数越界（D1 400：错误体带字段名与允许区间——detail 由 api 层取 constraints）。"""

    def __init__(self, violations: list[tuple[str, str]]) -> None:
        self.violations = violations  # [(字段路径, 允许区间), ...]
        super().__init__("；".join(f"{f} 允许 {r}" for f, r in violations))


def _validate_param(params: Mapping[str, int]) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for key in PARAM_ORDER:
        if key not in params:
            continue
        low, high = PARAM_LIMITS[key]
        value = params[key]
        if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
            violations.append((f"params.{key}", f"{low}–{high}"))
    return violations


@dataclass(frozen=True, slots=True)
class GatewayParams:
    """网关调用参数快照（models.yaml `gateway:` 段的域视图；快照为唯一真值）。"""

    allowed_fails: int = 2
    cooldown_seconds: int = 60
    num_retries: int = 3
    request_timeout: int = 30

    def as_mapping(self) -> dict[str, int]:
        return {key: getattr(self, key) for key in PARAM_ORDER}

    @classmethod
    def validated(cls, params: Mapping[str, int]) -> GatewayParams:
        """越界即拒（GatewayConfigError 携字段与允许区间——D1 400 语义）。"""
        violations = _validate_param(params)
        if violations:
            raise GatewayConfigError(violations)
        base = cls().as_mapping()
        return cls(**{**base, **{k: int(v) for k, v in params.items()}})


@dataclass(frozen=True, slots=True)
class GatewayParamsView:
    """配置读写快照（D1 端点 2/3：params（四 yaml 参数）＋预算双阈值＋yaml 全文；快照为唯一真值）。

    预算双阈值（D1 v0.2 扩段）不入 models.yaml——DB 单例行承载（99 §2.13），
    熔断判据每次 complete 现读，保存即对后续调用生效。
    """

    params: GatewayParams
    budget: BudgetThresholds
    yaml: str  # models.yaml 全文（密钥保持 ${VAR} 占位符，不落明文）


# ---------- 记账（调用粒度账本唯一——99 §2.13；金额公式＝Owner 裁决） ----------


@dataclass(frozen=True, slots=True)
class PriceSpec:
    """单价（元/百万 token）——models.yaml `prices.default`（Owner 2026-09-29 裁决）。"""

    input_per_mtok: float = 1.0
    output_per_mtok: float = 3.0


def cost_yuan(input_tokens: int, output_tokens: int, prices: PriceSpec) -> float:
    """记账金额公式（Owner 裁决）：input/1e6*输入单价 + output/1e6*输出单价（元）。"""
    return (
        input_tokens / 1_000_000 * prices.input_per_mtok
        + output_tokens / 1_000_000 * prices.output_per_mtok
    )


def estimate_tokens(text: str) -> int:
    """无 usage 兜底估算（椒图蓝本：chars/4）。"""
    return len(text) // 4


@dataclass(frozen=True, slots=True)
class SpendView:
    """记账流水的 D1 读面投影（数据形状红线：整数毫秒/两整数 token/元数值）。"""

    id: str  # call- 机器短 id（00 §1.5）
    time: datetime
    model_key: str  # main | backup
    alias: str
    input_tokens: int
    output_tokens: int
    first_ms: int
    total_ms: int
    cost_yuan: float
    fallback: bool  # True＝本次由备用模型应答（主用冷却期内）
    note: str
    caller: str | None = None  # 调用方归因（D1 v0.2：枚举不封闭；存量行可空→聚合归 unattributed）


@dataclass(frozen=True, slots=True)
class SpendFilter:
    """spend-logs 筛选（D1 端点 4 query；HTTP 形参 range 避开内建名——98 卡注）。"""

    model: str = "all"  # all | main | backup
    range: str = "all"  # all | today | 7d
    keyword: str | None = None  # 匹配调用号/备注

    def validated(self) -> SpendFilter:
        if self.model not in ("all", "main", "backup"):
            raise GatewayConfigError([("model", "all|main|backup")])
        if self.range not in ("all", "today", "7d"):
            raise GatewayConfigError([("range", "all|today|7d")])
        return self

    def since(self, at: datetime) -> datetime | None:
        """range → 时间下界（today＝当日零点；7d＝7×24h 前；all＝不限）。"""
        if self.range == "today":
            return at.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.range == "7d":
            return at - timedelta(days=7)
        return None


@dataclass(frozen=True, slots=True)
class SpendLogPage:
    """分页信封（R3：total＝当前筛选条件总数；page/page_size 回显）。"""

    items: list[SpendView]
    total: int
    page: int
    page_size: int


# ---------- 花费聚合/趋势（D1 端点 8——D5 撤页归并批；账本唯一真源聚合投影） ----------

STATS_GROUP_BYS: tuple[str, ...] = ("caller", "model", "day", "month")
STATS_RANGES: tuple[str, ...] = ("all", "7d", "30d", "12m")
UNATTRIBUTED = "unattributed"  # 存量未归因流水（caller 为空）聚合桶名——D1 v0.2 合同值


@dataclass(frozen=True, slots=True)
class SpendStatsFilter:
    """端点 8 筛选（group_by/range 与端点 4 的 model/range **不同族**——统计窗最小 7 天）。"""

    group_by: str = "caller"
    range: str = "all"  # all | 7d | 30d | 12m

    def validated(self) -> SpendStatsFilter:
        if self.group_by not in STATS_GROUP_BYS:
            raise GatewayConfigError([("group_by", "|".join(STATS_GROUP_BYS))])
        if self.range not in STATS_RANGES:
            raise GatewayConfigError([("range", "|".join(STATS_RANGES))])
        return self

    def since(self, at: datetime) -> datetime | None:
        """range → 时间下界（7d/30d＝N×24h；12m＝365d——mock RANGE_MS 同源口径；all＝不限）。"""
        days = {"7d": 7, "30d": 30, "12m": 365}.get(self.range)
        return None if days is None else at - timedelta(days=days)


@dataclass(frozen=True, slots=True)
class SpendStatsRow:
    """聚合单行（bucket＝caller 值/model_key/day/month；alias 仅 model 维度承载）。"""

    bucket: str
    alias: str | None  # model 维度：与 model_list 同源的别名（账本行 alias 代表值）
    calls: int
    fallback_calls: int
    input_tokens: int
    output_tokens: int
    cost_yuan: float


@dataclass(frozen=True, slots=True)
class SpendStatsSums:
    """窗口合计（全量不随分页截断——页面「期间合计」行拼装）。"""

    calls: int
    fallback_calls: int
    cost_yuan: float


@dataclass(frozen=True, slots=True)
class SpendStatsPage:
    """聚合读面信封（caller/model 按 cost_yuan 降序分页；day/month 升序全量、分页忽略）。"""

    group_by: str
    range: str
    items: list[SpendStatsRow]
    sums: SpendStatsSums
    total: int
    page: int
    page_size: int


def new_call_id() -> str:
    """调用号（机器短 id 族 call-；D1 示例 call-8c31 同族，8 hex 保唯一 PK）。"""
    return f"call-{uuid.uuid4().hex[:8]}"


# ---------- 路由与熔断状态机（进程内运行态；账本才是持久真源） ----------

ModelRole = Literal["main", "backup"]
DEGRADE_GROUP = "lite"  # 熔断降级组（ADR-0003：触顶改路由不拒绝——降级组 petro-lite）


@dataclass
class AliasHealth:
    """单别名运行态：连续失败计数＋冷却窗口（LiteLLM Router allowed_fails/cooldown_time 语义）。"""

    consecutive_fails: int = 0
    cooldown_until: datetime | None = None

    def in_cooldown(self, at: datetime) -> bool:
        return self.cooldown_until is not None and at < self.cooldown_until


@dataclass
class RouterState:
    """别名健康表＋熔断位（进程生命周期内单向置位、不自动恢复——F2 改注合同值）。

    五信号统计源口径（D1 v0.2 专节登记，P1-10）：miss（检索落空）/ambiguous
    （多候选澄清）/rewrite（改写重问）/error（报错）/feedback（用户反馈）五
    信号的运行态计数，归 gateway 域运行时采集（complete 出口心跳采样点＝本域
    _settle/NoAvailableRoute 收口路径）；D1 运行态徽标消费 RouterState（本类
    status 三态——端点 1 页头徽标已消费，不重复造）。计数达阈值自动归一成诊断
    schema 进 C2 提案池＝服务端内部动作，不经页面端点（C2 阶段 2 落地批接线）。
    """

    health: dict[str, AliasHealth] = field(default_factory=dict)
    fuse_latched: bool = False  # 熔断位：True 后所有调用改路由降级组（在途照跑完）

    def _of(self, alias: str) -> AliasHealth:
        return self.health.setdefault(alias, AliasHealth())

    def in_cooldown(self, alias: str, at: datetime) -> bool:
        health = self._of(alias)
        if health.in_cooldown(at):
            return True
        if health.cooldown_until is not None:  # 冷却过期即恢复可选（成功再清零计数）
            health.cooldown_until = None
            health.consecutive_fails = 0
        return False

    def record_failure(
        self, alias: str, allowed_fails: int, cooldown_seconds: int, at: datetime
    ) -> bool:
        """连续失败 +1；达到 allowed_fails → 进冷却窗口。返回是否本次触发冷却。"""
        health = self._of(alias)
        health.consecutive_fails += 1
        if health.consecutive_fails >= allowed_fails:
            health.cooldown_until = at + timedelta(seconds=cooldown_seconds)
            return True
        return False

    def record_success(self, alias: str) -> None:
        health = self._of(alias)
        health.consecutive_fails = 0
        health.cooldown_until = None

    def route_candidates(
        self,
        fallback_order: list[str],
        *,
        groups: Mapping[str, str],
        requested: str,
        at: datetime,
    ) -> list[str]:
        """候选序：requested 优先、其余按 fallback_order；冷却中跳过；熔断＝仅降级组。

        熔断改路由不拒绝：降级组里一个可用别名都没有时，宁可返回空列表让
        调用失败，也不把非降级组别名放进来（降级语义单向）。
        """
        ordered = [requested] + [a for a in fallback_order if a != requested]
        if self.fuse_latched:
            ordered = [a for a in ordered if groups.get(a) == DEGRADE_GROUP]
        return [a for a in ordered if not self.in_cooldown(a, at)]

    def status(
        self, default_alias: str, fallback_order: Sequence[str], at: datetime
    ) -> Literal["running", "degraded", "down"]:
        """网关运行态三态（D1 页头徽标）——全仓判定单源，消费方只调不重推导。

        - down：fallback_order 内全部别名冷却中（含主用——全线路不可用；
          空序不判 down）；degraded：主用冷却中（备用承载中）；running：主用可用。
        """
        if fallback_order and all(self.in_cooldown(a, at) for a in fallback_order):
            return "down"
        if self.in_cooldown(default_alias, at):
            return "degraded"
        return "running"


# ---------- 模型清单投影（D1 端点 1：models[] 与注册表一一对应） ----------


@dataclass(frozen=True, slots=True)
class ModelView:
    """model_list 单行（D1 端点 1 合同列形；key/role 由路由段派生）。"""

    key: str  # main | backup
    name: str
    alias: str
    role: ModelRole
    access: str
    note: str


@dataclass(frozen=True, slots=True)
class ModelRegistryView:
    """网关运行态＋模型清单（页头徽标消费 gateway.status——D1 端点 1）。"""

    gateway_status: Literal["running", "degraded", "down"]
    models: list[ModelView]


def project_models(
    entries: Sequence[ModelEntry],
    routing_default: str,
    fallback_order: list[str],
    status: Literal["running", "degraded", "down"],
) -> ModelRegistryView:
    """注册表 → D1 投影：default＝main，fallback_order 其余＝backup（key 同 role）。"""
    models: list[ModelView] = []
    for entry in entries:
        role: ModelRole = "main" if entry.alias == routing_default else "backup"
        models.append(
            ModelView(
                key=role,
                name=entry.name or entry.model,
                alias=entry.alias,
                role=role,
                access=entry.access or f"{entry.provider} 兼容接口",
                note=entry.note,
            )
        )
    # fallback_order 之外的散模型不进 D1 面（models[] 与 model_list 一一对应）；
    # default 与 fallback_order[0] 同名是常态——先去重再定序。
    aliases = [routing_default] + [a for a in fallback_order if a != routing_default]
    ordered = [m for a in aliases for m in models if m.alias == a]
    ordered += [m for m in models if m not in ordered]
    return ModelRegistryView(gateway_status=status, models=ordered)


# ---------- 演练（故障演练状态机——D1 端点 5/6/7；ADR：演练＝平台侧开关临时摘主模型路由） ----------

NODE_WAIT = "wait"
NODE_PROCESS = "process"
NODE_FINISH = "finish"
NODE_ERROR = "error"


@dataclass(slots=True)
class DrillNode:
    """节点步进（00 §5.3 四态，与 antd Steps 对齐；note 服务端组装、前端零拼装）。"""

    key: str
    label: str
    state: str = NODE_WAIT
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "state": self.state, "note": self.note}


@dataclass(frozen=True, slots=True)
class FallbackDetail:
    """切换留痕（D1 result.fallback；consecutive_fails/cooldown_sec 取当前配置值——合同原文）。"""

    time: str
    event: str  # 恒 "fallback_triggered"
    request_alias: str
    failed_deploy: str  # 被摘的主模型部署（provider/model）
    failover_target: str  # 备用部署（provider/model）
    consecutive_fails: int
    cooldown_sec: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "event": self.event,
            "request_alias": self.request_alias,
            "failed_deploy": self.failed_deploy,
            "failover_target": self.failover_target,
            "consecutive_fails": self.consecutive_fails,
            "cooldown_sec": self.cooldown_sec,
        }


@dataclass(frozen=True, slots=True)
class DrillResult:
    """演练结果（done 后落 result jsonb：conclusion＋fallback＋ledgerRow）。"""

    conclusion: str
    fallback: FallbackDetail
    ledger_row: SpendView

    def as_dict(self) -> dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "fallback": self.fallback.as_dict(),
            "ledger_row": {
                "id": self.ledger_row.id,
                "time": self.ledger_row.time.strftime("%Y-%m-%dT%H:%M:%S"),
                "model_key": self.ledger_row.model_key,
                "input_tokens": self.ledger_row.input_tokens,
                "output_tokens": self.ledger_row.output_tokens,
                "first_ms": self.ledger_row.first_ms,
                "total_ms": self.ledger_row.total_ms,
                "cost_yuan": self.ledger_row.cost_yuan,
                "fallback": self.ledger_row.fallback,
                "note": self.ledger_row.note,
                "caller": self.ledger_row.caller,
            },
        }


@dataclass(frozen=True, slots=True)
class DrillProgress:
    """演练轮询读面（D1 端点 6：status 双态 running|done；result 仅 done 后有值）。"""

    drill_id: str
    status: Literal["running", "done"]
    nodes: list[dict[str, str]]
    result: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class DrillSummary:
    """演练历史行（D1 端点 7：[{id, time, summary}] 倒序；summary 含阈值与冷却参数）。"""

    id: str
    time: datetime
    summary: str


@dataclass(frozen=True, slots=True)
class DrillHandle:
    """受理回执（D1 端点 5：202 {drillId}）。"""

    drill_id: str


def new_drill_id() -> str:
    """演练任务号（机器短 id 族 drill-；00 §1.5）。"""
    return f"drill-{uuid.uuid4().hex[:8]}"


def build_drill_nodes(allowed_fails: int) -> list[DrillNode]:
    """演练节点列：N 次注入失败＋主备切换＋记账落账（节奏由服务端任务驱动）。"""
    nodes = [
        DrillNode(key=f"fail{i}", label=f"第 {i} 次调用失败（注入）")
        for i in range(1, allowed_fails + 1)
    ]
    nodes.append(DrillNode(key="fallback", label="主备切换 · 备用应答"))
    nodes.append(DrillNode(key="ledger", label="记账落账（备用应答行 fallback=true）"))
    return nodes


DRILL_PROMPT = "故障演练心跳——请原样回答：线路正常"


class DrillNotFoundError(Exception):
    """演练任务不存在（D1 404：轮询已过期/不存在的 id）。"""


class DrillConflictError(Exception):
    """演练重入（D1 409：已有进行中任务；前端按钮禁用是兜底，不依赖此码）。"""


class ConfigWriteError(Exception):
    """配置写回/热加载失败（D1 500：需回滚提示——api 层映射错误包）。"""


class NoAvailableRoute(Exception):
    """无可用线路（全部候选别名冷却中/降级组无可用别名——调用方稍后重试）。"""

    def __init__(self, alias: str) -> None:
        self.alias = alias
        super().__init__(f"请求别名 {alias!r} 无可用线路（候选冷却中或降级组不可用）")


# ---------- 预算双阈值（D1 v0.2 端点 2/3 config 族扩段；判据消费方＝complete 熔断） ----------


@dataclass(frozen=True, slots=True)
class BudgetThresholds:
    """花费双阈值（gateway_budget_config 单例行的域视图；F2 改注合同值 0.05/800）。

    单笔管一次调用（per_call_cost_limit）、累计管全月总额（gateway_budget）——
    触顶＝熔断位单向置位→改路由降级组 petro-lite（改路由不拒绝、在途照跑完）；
    保存即对后续调用生效（不回溯已完调用），DB 承载（99 §2.13 单例行）。
    """

    per_call_cost_limit_yuan: float
    gateway_budget_yuan_per_month: float

    def as_mapping(self) -> dict[str, float]:
        return {
            "per_call_cost_limit_yuan": self.per_call_cost_limit_yuan,
            "gateway_budget_yuan_per_month": self.gateway_budget_yuan_per_month,
        }

    @classmethod
    def validated(cls, values: Mapping[str, Any]) -> BudgetThresholds:
        """越界即拒（>=0；负数/非数值/布尔冒充 → GatewayConfigError 携字段与区间）。"""
        violations: list[tuple[str, str]] = []
        for key in ("per_call_cost_limit_yuan", "gateway_budget_yuan_per_month"):
            value = values.get(key)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value < 0
            ):
                violations.append((f"params.{key}", ">=0"))
        if violations:
            raise GatewayConfigError(violations)
        return cls(
            per_call_cost_limit_yuan=float(values["per_call_cost_limit_yuan"]),
            gateway_budget_yuan_per_month=float(values["gateway_budget_yuan_per_month"]),
        )


def default_note(caller: str, note: str | None) -> str:
    """备注缺省＝调用方标识（keyword 可检索；显式 note 优先）。"""
    return note if note else caller
