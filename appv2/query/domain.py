"""query.domain —— 六站链纯语义件（V1 确定性行为移植；specs/query.md 接口定义）。

V1 问数链（M-06 状态机六站链）的确定性语义在本模块单点承载——词面解析
（时间/条数/排名/外表）、LIMIT 收口（F14）、血缘卡五要素（F13）、新鲜度闸
话术（E2 T-1 渲染面）、缺参反问与外表审批合同文案，全部照 V1 合同值移植
（app/domains/chat/domain.py 以行为为准重实现——禁止整文件搬运，本文件只收
本模块消费的件，词表/话术逐字对齐）。

schema 定稿（票面点名随本票）：
- QueryPlan＝五源槽位计划草案（specs/query.md 接口定义
  ``{metric_slot, window_start, window_end, limit, ranking, direction}``＋
  展示注记 window_label/is_default＋越集外表集＋行级身份；window 两槽同 None
  ＝问句时间窗不可定（「最近」类模糊词）→引擎 need_clarify）；
- QueryOutcome＝六联合态（rows+lineage｜freshness_block｜unbound_degrade｜
  need_clarify｜external_table_approval｜refuse——kind 闭世界，构造即定型）；
- PlanCheck＝validate 结论（ok＋拒因——FX-13/窗界的白名单面）。

零 I/O、零第三方依赖（B1——IO 归 engine/executor；指标绑定目录与 Evidence
经 appv2.knowledge 公开接口取，不造第二份 MEASURE_COLUMNS）。
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from appv2.knowledge import Evidence

# ---------- 排名方向（V1 R1——白名单二值，执行侧按二值分派 ORDER BY） ----------

DIRECTION_ASC = "asc"
DIRECTION_DESC = "desc"

# F14 LIMIT 收口合同值（票 79/85：没写补默认 50、超 200 截到 200、只封顶不抬底）。
QUERY_DEFAULT_LIMIT = 50
QUERY_LIMIT_CAP = 200

# 汇总型（aggregate）整窗合计行的口径标注（V2-71 整窗 SUM 单行——L5·02 病灶修复②）：
# 该行无井位列（答案表只有合计列），材料/行内容必须写实标注口径，不写井位空段冒充
# 单井行（材料块空段跳过规则下会渲染成无井行）。行内容前缀与 locator 口径键同源于
# 本常量（tools.handlers 单点消费——不各写一份）。
WINDOW_TOTAL_SCOPE_NOTE = "整窗合计·全井"

# 血缘④批次前缀（血线行格式单源——tools 侧读回该前缀取行集可寻址 handle 同源）。
WATERMARK_BATCH_PREFIX = "批次 "

# 钉入窗长上限（V1 R6-03 票内定案）：366 天＝快路确定性时间词函数可产出的最大窗
# （「去年」全历年，闰年 366 天）——封野值，不触常规形。
PLAN_WINDOW_MAX_DAYS = 366

# agg 星型读模型三表（99 §2.12/D6 star_model 合同值——问数链 SELECT 唯一落点；
# join 结构即注册合同值：事实表组合 PK well_id+prod_date 挂两维 PK 连）。
STAR_TABLES: tuple[str, ...] = (
    "agg.fct_daily_metering", "agg.dim_well", "agg.dim_date",
)
STAR_SOURCE_NOTE = (
    "agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」"
    "——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）"
    "⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）"
)

# 外表别名 → 表名（F14 唯一 interrupt 触发场景＝erp_well_register 越集审批；
# 别名「井位台账」在册＝Q11 病灶修复点——别名进选表命中集，external_table_ask
# 红变绿；外表登记册随 D3 白名单批落，本表只收合同演示样本，不新增业务事实）。
EXTERNAL_TABLE_ALIASES: dict[str, str] = {
    "erp_well_register": "erp_well_register",
    "井位台账": "erp_well_register",
}

# extable 审批卡与收场话术（A1 帧 15/answer kind=extable 合同形状——话术照抄
# prototype stateGates.jsx ExtableFlow 原文，V1 同源）。
EXTABLE_SCENE = "extable"
EXTABLE_TITLE = "外表引用审批"
EXTABLE_REASON_TEMPLATE = "查询引用选表命中集之外的外表：{tables}（执行前表引用比对命中——F14）"
EXTABLE_IMPACT = "批准＝链恢复续跑（只读执行，生产库未动）；驳回＝权限拒答零重试（不自动改写 SQL）"
EXTABLE_REJECT_NOTICE_TEMPLATE = (
    "不予执行，且不自动改写 SQL 重试。处理方式：请数据 Owner 先将 {table} "
    "登记进可用表白名单（安全与权限设置），再重新提问。"
)
EXTABLE_APPROVED_FOOTNOTE_TEMPLATE = (
    "审批留痕（单号 {approval_id}，可回溯）；只读执行，生产库未动。"
)

# 缺参反问（askback 时间窗三选一——choices＝补参候选，无默认项：缺的是用户
# 事实；候选与问句照抄 prototype blocked.jsx AskbackFlow 原文，V1 同源）。
MISSING_SUBTYPE = "missing"
ASKBACK_TIME_QUESTION = (
    "「最近」指哪个时间窗？① 近 3 天 ② 近 30 天 ③ 本月至今——选好后我按审定口径取数。"
)
ASKBACK_TIME_CHOICES: tuple[str, ...] = ("近 3 天", "近 30 天", "本月至今")

# 血缘解释链五要素键（A1 lineage DTO——F13 票 80/85「五要素与『（权限注入）』
# 独立成行是合同值不可改」）。
LINEAGE_KEY_CALIBER = "① 口径"
LINEAGE_KEY_SOURCE = "② 来源表"
LINEAGE_KEY_FILTER = "③ 过滤条件"
LINEAGE_KEY_PERMISSION = "　└（权限注入）"
LINEAGE_KEY_WATERMARK = "④ 数据截至批次"
LINEAGE_KEY_CLOSING = "⑤ 收口注记"

# 行级权限预埋期注记（M-01 两步缝消费面——「无权的数据查不出来，不是打码」；
# 真分权只换谓词生产实现，注入点形状冻结）。
ROW_FILTER_PREEMBEDDED_NOTE = (
    "数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉"
    "（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）"
)

# 新鲜度闸话术（V1 E2 语义渲染面——T-1 判定在水位读缝供给侧算好，本模块只渲染）。
FRESHNESS_UNKNOWN_NOTE = "汇总层水位未回写——批次截至未知（如实标注，不造达标假象）"
FRESHNESS_REJECT_TEMPLATE = (
    "新鲜度闸拦停：汇总层数据水位＝{data_date}（{tag}）——查询窗「{label}」"
    "尚无已出数数据，不返回空数冒充。催办：源表催办走「考核与质量 → 问题单」。"
)
FRESHNESS_CLAMP_NOTE_TEMPLATE = (
    "比对：数据水位 {data_date} 早于查询窗上沿——已按最近可用日改绑出数"
    "（数据截至 {data_date}，{tag}；其后日期未出数，不冒充新数据）"
)

# 六联合态 kind 闭世界（specs/query.md 接口定义——六联合态逐一枚举）。
OUTCOME_ROWS = "rows"  # 权威表＋血缘卡（血缘五要素:口径/来源表/过滤/水位/收口）
OUTCOME_FRESHNESS_BLOCK = "freshness_block"  # 拦停（水位日期,窗标签,is_default）
OUTCOME_UNBOUND_DEGRADE = "unbound_degrade"  # 降级（指标 Evidence,依据）
OUTCOME_NEED_CLARIFY = "need_clarify"  # 缺参反问（候选窗三选一）
OUTCOME_EXTERNAL_TABLE_APPROVAL = "external_table_approval"  # 越集审批（外表名,ASK 素材）
OUTCOME_REFUSE = "refuse"  # 拒答（原因）
OUTCOME_KINDS: frozenset[str] = frozenset(
    {
        OUTCOME_ROWS,
        OUTCOME_FRESHNESS_BLOCK,
        OUTCOME_UNBOUND_DEGRADE,
        OUTCOME_NEED_CLARIFY,
        OUTCOME_EXTERNAL_TABLE_APPROVAL,
        OUTCOME_REFUSE,
    }
)

# ---------- 确定性词面解析（V1 词表逐字——时间/条数/排名三词族） ----------

_CN_NUMERALS: dict[str, int] = {
    "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}
_RECENT_N_RE = re.compile(r"(?:最近|近)\s*([0-9]+|[一二两三四五六七八九十]+)\s*天")
_VAGUE_TIME_RE = re.compile(r"最近|近期|近日")
_LIMIT_TOP_RE = re.compile(r"(?:前|TOP|top)\s*([0-9]+|[一二两三四五六七八九十]+)")
_LIMIT_MOUTH_RE = re.compile(r"([0-9]+|[一二两三四五六七八九十]+)\s*口")
_RANKING_RE = re.compile(r"最高|最低|最大|最小|排名|TOP|top|前\s*[0-9一二两三四五六七八九十]")
_ASC_RANKING_RE = re.compile(r"最低|最小|最少")


def _cn_int(raw: str) -> int | None:
    raw = raw.strip()
    if raw.isdigit():
        return int(raw)
    return _CN_NUMERALS.get(raw)


def parse_row_limit(question: str) -> int | None:
    """问句显式条数解析（确定性——「前3/TOP3/三口」；没写返回 None＝默认 50）。

    只解析不收口：>200 的截断在 effective_limit（F14 收口注记要区分「没写」与
    「写了超限」两态）。V1 同名函数同语义。
    """
    for pattern in (_LIMIT_TOP_RE, _LIMIT_MOUTH_RE):
        match = pattern.search(question)
        if match is not None:
            value = _cn_int(match.group(1))
            if value is not None and value > 0:
                return value
    return None


def effective_limit(requested: int | None) -> int:
    """LIMIT 收口（F14 合同值：没写补默认 50、超 200 截到 200、只封顶不抬底）。"""
    value = QUERY_DEFAULT_LIMIT if requested is None else requested
    return min(value, QUERY_LIMIT_CAP)


def is_ranking_question(question: str) -> bool:
    """排名型问句信号（「最高/TOP/前N」——模板走 GROUP BY 井合计排序）。"""
    return _RANKING_RE.search(question) is not None


def parse_ranking_direction(question: str) -> str:
    """排名方向解析（V1 R1——「最低/最小/最少」词面→升序；其余含未识别→降序默认）。"""
    if _ASC_RANKING_RE.search(question) is not None:
        return DIRECTION_ASC
    return DIRECTION_DESC


# ---------- 时间窗（半开区间 [start, end)——SQL 装配与血缘卡③共用单源形状） ----------


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """问数时间窗（V1 同名形状原样——label 人话标签、is_default 默认窗标注）。"""

    start: date
    end: date
    label: str
    is_default: bool = False


def parse_time_window(
    question: str, *, today: date
) -> tuple[str, TimeWindow | None]:
    """时间窗解析（确定性时间词函数——V1 同名函数同语义同词表）。

    - ("ok", window)：显式时间词命中；
    - ("vague", None)：「最近/近期/近日」无量化——缺参反问（三选一，不猜数）；
    - ("missing", None)：无时间词——调用方走默认窗（最近 30 天）并标注「默认」。
    """
    recent = _RECENT_N_RE.search(question)
    if recent is not None:
        value = _cn_int(recent.group(1))
        if value is not None and value > 0:
            return "ok", TimeWindow(
                start=today - timedelta(days=value), end=today,
                label=f"近 {value} 天",
            )
    if _VAGUE_TIME_RE.search(question) is not None:
        return "vague", None
    if "上个月" in question or "上月" in question:
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        end = today.replace(day=1)
        return "ok", TimeWindow(start, end, "上个月")
    if "本月" in question or "这个月" in question:
        start = today.replace(day=1)
        return "ok", TimeWindow(start, today, "本月至今")
    if "昨天" in question:
        day = today - timedelta(days=1)
        return "ok", TimeWindow(day, today, "昨天")
    if "前天" in question:
        day = today - timedelta(days=2)
        return "ok", TimeWindow(day, day + timedelta(days=1), "前天")
    if "今天" in question:
        return "ok", TimeWindow(today, today + timedelta(days=1), "今天")
    if "今年" in question:
        start = today.replace(month=1, day=1)
        return "ok", TimeWindow(start, today, "今年")
    if "去年" in question:
        start = today.replace(month=1, day=1).replace(year=today.year - 1)
        end = today.replace(month=1, day=1)
        return "ok", TimeWindow(start, end, "去年")
    return "missing", None


def default_time_window(*, today: date) -> TimeWindow:
    """默认时间窗（最近 30 天——无显式时间词时；is_default 驱动标注「默认」）。"""
    return TimeWindow(
        start=today - timedelta(days=30), end=today,
        label="最近 30 天（默认）", is_default=True,
    )


def resolve_askback_window(choice: str, *, today: date) -> TimeWindow | None:
    """askback 选项 → 时间窗（resume 补参的确定性落点；未知选项 None）。"""
    if choice == "近 3 天":
        return TimeWindow(today - timedelta(days=3), today, "近 3 天")
    if choice == "近 30 天":
        return TimeWindow(today - timedelta(days=30), today, "近 30 天")
    if choice == "本月至今":
        return TimeWindow(today.replace(day=1), today, "本月至今")
    return None


def fill_window_label(window: TimeWindow) -> TimeWindow:
    """空标签窗填实（V2-22——P-013 疑点 4 裁决落地）。

    真模型计划草案不带 window_label（schema 可选键）时，血缘③/拦停话术渲染
    空标签（「时间＝ [s, e)」标签位空串带多余空格）。无标签草案按半开区间
    [start, end) 的含端日期机械补标（start～end−1 天）——不猜词面（「去年/
    近 N 天」归规划步词面解析），显式窗/默认窗/改绑窗三形态统一在此单点填实；
    有标签原样返回（fixture 链恒带标签——零影响）。
    """
    if window.label:
        return window
    return TimeWindow(
        start=window.start,
        end=window.end,
        label=(
            f"{window.start.isoformat()}～"
            f"{(window.end - timedelta(days=1)).isoformat()}"
        ),
        is_default=window.is_default,
    )


def detect_external_tables(question: str) -> tuple[str, ...]:
    """问句点名的选表命中集之外外表（F14 越集比对触发源——确定性别名比对）。

    别名表＝EXTERNAL_TABLE_ALIASES（「井位台账」在册——Q11 病灶修复点：别名
    进选表命中集，越集审批可达）。
    """
    seen: list[str] = []
    for alias, table in EXTERNAL_TABLE_ALIASES.items():
        if alias.casefold() in question.casefold() and table not in seen:
            seen.append(table)
    return tuple(seen)


# ---------- schema 定稿（票面点名：QueryPlan／QueryOutcome 六联合态） ----------

QueryResultColumn = tuple[str, str]  # 表卡列 (dataIndex, title)——执行缝列序投影


@dataclass(frozen=True, slots=True)
class QueryPlan:
    """问数查询计划（N7.1/N7.3 确定性解析产物——runtime 规划步的落点形状）。

    五源槽位（specs/query.md 接口定义六键）＋展示注记＋越集外表集＋行级身份；
    全字段由确定性解析产出（零模型调用——派生字段 measure_column/unit/
    limit_effective 由引擎单源重推导，不进计划草案）。window 两槽同 None＝
    时间窗不可定（「最近」类模糊词——引擎 need_clarify）；两槽须同缺同在，
    半开区间要求 start < end（构造即拒）。aggregate ∧ ranking 同真＝计划形态
    非法（构造即拒——排名题合计在排名首行值里，程序侧不猜不代选）。
    """

    metric_slot: str  # 剥法纯名（C1 台账槽位——注册指标声明）
    window_start: date | None  # None（与 window_end 同）＝模糊时间——缺参反问
    window_end: date | None
    limit: int | None  # 问句显式条数（None＝没写；引擎按 F14 收口，草案值不直用）
    ranking: bool  # 排名型（GROUP BY 井＋ORDER BY 合计）｜明细型
    aggregate: bool = False  # 汇总型（V2-71——整窗 SUM 库内算单行返回；明细 50 上限不动）
    direction: str = DIRECTION_DESC  # asc/desc 白名单二值（R1：最低类问句升序）
    window_label: str = ""  # 人话标签（「去年」「最近 30 天（默认）」——血缘③/拦停话术）
    is_default: bool = False  # 无显式时间词的默认窗（答案与血缘卡必须标注「默认」）
    external_tables: tuple[str, ...] = ()  # 选表命中集之外的外表（N7.4c 越集比对触发源）
    actor: str = ""  # 行级注入身份（两步缝第一步——执行缝消费）

    def __post_init__(self) -> None:
        if (self.window_start is None) != (self.window_end is None):
            raise ValueError(
                f"QueryPlan.window 半窗非法：start={self.window_start!r} end={self.window_end!r}"
                "——两槽同缺同在（None＝模糊时间缺参反问）"
            )
        if self.window_start is not None and self.window_end is not None:
            if self.window_start >= self.window_end:
                raise ValueError(
                    f"QueryPlan.window 非半开区间（start={self.window_start.isoformat()} ≥ "
                    f"end={self.window_end.isoformat()}）——半开区间 [start, end) 要求 start < end"
                )
        if self.direction not in (DIRECTION_ASC, DIRECTION_DESC):
            raise ValueError(
                f"QueryPlan.direction 非 {DIRECTION_ASC}/{DIRECTION_DESC} 二值：{self.direction!r}"
            )
        if self.limit is not None and self.limit < 1:
            raise ValueError(f"QueryPlan.limit 必须 ≥1 或 None（没写），得到 {self.limit!r}")
        # V2-71 汇总型 ∧ 排名型互斥（L5·02 病灶修复：pg_executor 早退分支先于
        # ranking 命中，「最高的井是哪口、合计多少」被整窗 SUM 单行答成无井号行）
        # ——同真即拒，程序侧不猜不代选：排名题的合计在排名首行值里。
        if self.aggregate and self.ranking:
            raise ValueError(
                "QueryPlan 计划形态非法：aggregate 与 ranking 互斥——"
                "排名题合计在排名首行值里：aggregate=false"
                "（整窗 SUM 单行无井位行，排名问句须 ranking-only 发射）"
            )

    @property
    def window(self) -> TimeWindow | None:
        """窗形投影（引擎内部消费——None＝模糊时间）。"""
        if self.window_start is None or self.window_end is None:
            return None
        return TimeWindow(
            start=self.window_start, end=self.window_end,
            label=self.window_label, is_default=self.is_default,
        )


@dataclass(frozen=True, slots=True)
class PlanCheck:
    """validate 结论（白名单/一致性/窗界——ok=False 时 reason 携拒因）。"""

    ok: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class LineageLine:
    """血缘卡一行（key＝五要素合同键＋权限注入行；value＝合同话术行）。"""

    key: str
    value: str


@dataclass(frozen=True, slots=True)
class QueryOutcome:
    """问数链输出六联合态（specs/query.md 接口定义——kind 闭世界构造即定型）。

    每联合态只消费自己的字段组（classmethod 构造器逐态定型，零发明态）：
    - rows：columns/rows/lineage/rebind_notice（改绑注记——仅窗跨水位时在位）；
    - freshness_block：watermark_date/window_label/is_default/message（零数值行）；
    - unbound_degrade：evidence（指标 Evidence）/basis（依据含台账口径原文）；
    - need_clarify：clarify_question/choices（askback 时间窗三选一）；
    - external_table_approval：external_tables/ask（审批卡 ASK 素材）；
    - refuse：reason（拒因——未注册/窗界越界/零行如实回报）。
    """

    kind: str  # OUTCOME_* 六闭世界
    # —— rows 联合态 ——
    columns: tuple[tuple[str, str], ...] | None = None
    rows: tuple[dict[str, Any], ...] | None = None
    lineage: tuple[LineageLine, ...] | None = None
    rebind_notice: str | None = None
    # —— freshness_block 联合态 ——
    watermark_date: date | None = None
    window_label: str | None = None
    is_default: bool | None = None
    message: str | None = None
    # —— unbound_degrade 联合态 ——
    evidence: Evidence | None = None
    basis: str | None = None
    # —— need_clarify 联合态 ——
    clarify_question: str | None = None
    choices: tuple[str, ...] | None = None
    # —— external_table_approval 联合态 ——
    external_tables: tuple[str, ...] | None = None
    ask: Mapping[str, Any] | None = None
    # —— refuse 联合态 ——
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in OUTCOME_KINDS:
            raise ValueError(
                f"QueryOutcome.kind 越界（六联合态闭世界 {sorted(OUTCOME_KINDS)}）：{self.kind!r}"
            )

    @classmethod
    def rows_with_lineage(
        cls,
        *,
        columns: tuple[tuple[str, str], ...],
        rows: tuple[dict[str, Any], ...],
        lineage: tuple[LineageLine, ...],
        rebind_notice: str | None = None,
    ) -> QueryOutcome:
        return cls(
            kind=OUTCOME_ROWS, columns=columns, rows=rows, lineage=lineage,
            rebind_notice=rebind_notice,
        )

    @classmethod
    def freshness_block(
        cls, *, watermark_date: date, window_label: str, is_default: bool, message: str
    ) -> QueryOutcome:
        return cls(
            kind=OUTCOME_FRESHNESS_BLOCK, watermark_date=watermark_date,
            window_label=window_label, is_default=is_default, message=message,
        )

    @classmethod
    def unbound_degrade(cls, *, evidence: Evidence, basis: str) -> QueryOutcome:
        return cls(kind=OUTCOME_UNBOUND_DEGRADE, evidence=evidence, basis=basis)

    @classmethod
    def need_clarify(
        cls, *, question: str, choices: tuple[str, ...]
    ) -> QueryOutcome:
        return cls(
            kind=OUTCOME_NEED_CLARIFY, clarify_question=question, choices=choices,
        )

    @classmethod
    def external_table_approval(
        cls, *, tables: tuple[str, ...], ask: Mapping[str, Any]
    ) -> QueryOutcome:
        return cls(
            kind=OUTCOME_EXTERNAL_TABLE_APPROVAL, external_tables=tables, ask=ask,
        )

    @classmethod
    def refuse(cls, *, reason: str) -> QueryOutcome:
        return cls(kind=OUTCOME_REFUSE, reason=reason)


# ---------- 计划装配与可执行形状 ----------


@dataclass(frozen=True, slots=True)
class SqlPlan:
    """可执行计划（引擎单源重推导产物——measure_column/unit/收口条数已定）。

    执行缝（QueryExecutor）唯一入参形状；V1「计划」的执行侧角色（模板装配
    已核、LIMIT 已收口、窗口已改绑）。
    """

    metric_slot: str
    measure_column: str  # agg 计量列（MEASURE_COLUMNS 绑定——引擎经 knowledge 单源推导）
    unit: str
    window: TimeWindow
    limit_effective: int  # F14 收口后值（只封顶不抬底）
    ranking: bool
    direction: str  # asc/desc 白名单二值分派 ORDER BY，非字符串拼接
    aggregate: bool = False  # V2-71 汇总型（整窗 SUM 单行；互斥由 QueryPlan 构造把守）
    actor: str = ""


def build_query_plan(
    *, metric_slot: str, question: str, today: date, actor: str = ""
) -> QueryPlan:
    """N7.1/N7.3 确定性计划装配（V1 同名函数同语义——前提＝指标锚已定）。

    指标槽位由调用方锚定（路由/指标候选归 runtime——N5 语义不进本模块）；
    时间窗/条数/排名/越集外表全部确定性词面解析。模糊时间（「最近」）→
    window 两槽 None（引擎 need_clarify）；无时间词→默认窗＋标注「默认」。
    """
    status, window = parse_time_window(question, today=today)
    if status == "vague":
        parsed: TimeWindow | None = None  # 缺参反问——不猜数
    else:
        parsed = window if window is not None else default_time_window(today=today)
    return QueryPlan(
        metric_slot=metric_slot,
        window_start=parsed.start if parsed is not None else None,
        window_end=parsed.end if parsed is not None else None,
        limit=parse_row_limit(question),
        ranking=is_ranking_question(question),
        direction=parse_ranking_direction(question),
        window_label=parsed.label if parsed is not None else "",
        is_default=parsed.is_default if parsed is not None else False,
        external_tables=detect_external_tables(question),
        actor=actor,
    )


def check_plan_window_bounds(window: TimeWindow, *, today: date) -> None:
    """窗界校验（V1 R6-03 check_pinned_window_bounds 同语义——越界 ValueError）。

    - end ≤ today：窗尾不落未来（未来端点窗＝静默返空数据冒充出数）；
    - 窗长 ≤ PLAN_WINDOW_MAX_DAYS（366 天）：与快路「去年」最大窗对齐——
      封任意大区间的野值。
    """
    if window.end > today:
        raise ValueError(
            f"窗界越界：window.end={window.end.isoformat()} 晚于今日 "
            f"{today.isoformat()}——未来窗不代猜不冒充（R6-03 窗界校验）"
        )
    days = (window.end - window.start).days
    if days > PLAN_WINDOW_MAX_DAYS:
        raise ValueError(
            f"窗界越界：窗长 {days} 天超上限 {PLAN_WINDOW_MAX_DAYS} 天"
            "（与快路「去年」最大窗对齐——R6-03 窗界校验）"
        )


def render_plan_sql(plan: SqlPlan) -> str:
    """计划 → 展示 SQL（N7.3 模板——执行走参数化 Core，展示串才用字面日期；
    两处同源自 SqlPlan 单点渲染。V1 render_plan_sql 同形——agg 三表 join 即
    注册合同值）。"""
    measure = f"m.{plan.measure_column}"
    window_cond = (
        f"m.prod_date >= '{plan.window.start.isoformat()}' "
        f"AND m.prod_date < '{plan.window.end.isoformat()}'"
    )
    joins = (
        "FROM agg.fct_daily_metering m\n"
        "  JOIN agg.dim_well w ON w.well_id = m.well_id\n"
        "  JOIN agg.dim_date d ON d.date = m.prod_date"
    )
    if plan.ranking:
        order = "ASC" if plan.direction == DIRECTION_ASC else "DESC"  # 白名单二值分派
        total = f"SUM({measure}) AS {plan.metric_slot}合计（{plan.unit}）"
        return (
            f"SELECT w.well_id AS 井号, w.block_name AS 区块, {total}\n"
            f"{joins}\n"
            f"WHERE {window_cond}\n"
            "GROUP BY w.well_id, w.block_name\n"
            f"ORDER BY SUM({measure}) {order}\n"
            f"LIMIT {plan.limit_effective}"
        )
    return (
        f"SELECT m.well_id AS 井号, w.block_name AS 区块, m.prod_date AS 日期, "
        f"{measure} AS {plan.metric_slot}（{plan.unit}）\n"
        f"{joins}\n"
        f"WHERE {window_cond}\n"
        f"ORDER BY m.prod_date, m.well_id\n"
        f"LIMIT {plan.limit_effective}"
    )


# ---------- 血缘卡五要素行（F13——keys 合同值不可改） ----------


def lineage_caliber_line(*, metric_name: str, unit: str, def_text: str) -> str:
    """血缘卡①口径（注册指标声明先行——台账名/单位/口径照抄，R4 占位句兜底）。"""
    body = def_text.strip() if def_text else ""
    if not body:
        body = "台账未登记口径声明"
    return f"{metric_name}（单位：{unit}）——指标台账注册声明：{body}，口径随答案标注"


def lineage_source_line() -> str:
    """血缘卡②来源表（照抄 A1 lineage DTO 示例句式——机器名冻结）。"""
    return STAR_SOURCE_NOTE


def lineage_filter_line(window: TimeWindow) -> str:
    """血缘卡③过滤条件主体（只声明真实下推的过滤——时间窗；区块过滤随行级权限批）。"""
    line = (
        f"时间＝{window.label} "
        f"[{window.start.isoformat()}, {window.end.isoformat()})"
    )
    if window.is_default:
        line += "（默认窗——问句无显式时间，已标注）"
    return line


def lineage_permission_line(actor: str) -> str:
    """血缘卡权限注入行（M-01 两步缝——预埋期恒真形状，V1 同文）。"""
    return (
        f"{ROW_FILTER_PREEMBEDDED_NOTE}"
        f"（actor＝{actor} · 落点 agg.fct_daily_metering——谓词随执行并语句）"
    )


def lineage_watermark_line(
    *, data_date: date | None, promise: str | None, tag: str | None, batch_id: str | None
) -> str:
    """血缘卡④数据截至批次（水位读面消费——水位未回写如实缺行）。"""
    if data_date is None:
        return "—（水位未回写——如实缺行，不造达标假象）"
    body = f"汇总层水位 {data_date.isoformat()}（承诺 {promise or 'T-1'} · {tag or '—'}）"
    if batch_id:
        body = f"{WATERMARK_BATCH_PREFIX}{batch_id} · {body}"
    return body


def lineage_closing_line(
    *, limit_requested: int | None, limit_effective: int, aggregate: bool = False
) -> str:
    """血缘卡⑤收口注记（F14 LIMIT 收口——区分「没写默认」与「显式/超限截断」）。

    汇总型分支如实（L5·02 病灶修复③）：整窗 SUM 库内算的 SQL 无 LIMIT，⑤注记
    不得无条件写「LIMIT 50」（血缘与真 SQL 同源——注记不冒充没写过的收口条）。
    """
    if aggregate:
        return (
            "整窗 SUM·无行限量——汇总型在库内算合计单行返回，不套行数 LIMIT"
            "（明细/排名形的没写补默认 50、超 200 截到 200 只封顶不抬底，与本分支无关）"
        )
    line = (
        f"LIMIT {limit_effective}"
        "——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"
    )
    if limit_requested is not None and limit_requested > QUERY_LIMIT_CAP:
        line += f"（问句条数 {limit_requested}——已按上限截到 {QUERY_LIMIT_CAP}）"
    elif limit_requested is not None:
        line += f"（问句显式条数 {limit_requested}——只封顶不抬底）"
    return line


# ---------- 外表审批 ASK 素材（A1 帧 15 合同形状） ----------


def build_extable_ask(plan: QueryPlan, *, approval_id: str) -> dict[str, Any]:
    """extable 审批卡 ASK 素材（A1 帧 15 合同形状——wire 键零剥除负担）。"""
    tables = "、".join(plan.external_tables)
    return {
        "approval_id": approval_id,
        "scene": EXTABLE_SCENE,
        "title": EXTABLE_TITLE,
        "reason": EXTABLE_REASON_TEMPLATE.format(tables=tables),
        "impact": EXTABLE_IMPACT,
        "audit_hint": f"外表 {tables}",
    }
