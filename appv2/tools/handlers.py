"""tools.handlers —— 五工具实现（engines 只读包装；specs/tools.md「四工具」行
＋V2-31 发现工具扩展 table_schema）。

五工具＝三引擎公开接口的包装＋白名单结构卡（零引擎逻辑——specs/tools.md「不做
什么」）：
- semantic_query（question｜element_name）→ knowledge.evidence＋metric_by_name
  ——跨 kind 歧义名（「日产液」类）双落并列：evidence() 结果优先（术语卡一等
  材料语义，在前）＋metric_by_name 补取可出数指标（别名归一落点，element_id
  去重后并列在后）——V2-02 挂账对齐项①，合同语义在 semantic_query 的
  ToolDescriptor.description 载明并由 tests/domains/test_v2_tools.py 钉死；
- data_query（plan_draft）→ query.validate 先行（不过＝failed(bad_args, 校验
  理由)，run 零调用），过闸后 run——六联合态→ToolResult 逐态映射（行为约定
  4，_outcome_to_result 单点）；行级身份只从 ctx.actor 进（args 不设 actor——
  伪造面收口）；FX-13 候选集从 ctx.metric_candidates 逐字转发；
- doc_retrieve（question, anchors?, family_hints?）→ retrieval.retrieve——
  anchors/family_hints/ctx.budget 逐字进 RetrievalNeed（P-003 已定实现＝并入
  关键词腿检索单元＋编号保送——V2-04 挂账对齐项②的参数契约面）；
- graph_query（question, anchors?）→ retrieval.graph——anchors 并入实体匹配
  问针（锚定语义的图谱侧投影；引擎 face 按 question 子串匹配实体，锚名只在
  anchors 提名时可达，测试端到端钉死）。

观察装配单点：_evidence_observation（台账卡）、_rows_observations（权威表行
scope=agg＋血缘卡＋改绑 notice）、_bundle_to_result（检索支出处链＋window_note
截断声明）——每支 Observation 来源链必带、locator 机读（INV-1 输入）。

引擎缝：QueryFace/RetrievalFace 结构性 Protocol（生产传真引擎，测试与 P-006
runtime 传 fake.adapter 假引擎）；knowledge 直接用 KnowledgeStore 抽象基类
（V2-02 定稿 seam）。本模块零 LLM 调用（精排/嵌入归引擎缝——B6 出口已在
引擎内收口）。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any, Protocol

from appv2.knowledge import Evidence, KnowledgeStore, SemanticQuery
from appv2.query import (
    DIRECTION_DESC,
    LINEAGE_KEY_WATERMARK,
    OUTCOME_EXTERNAL_TABLE_APPROVAL,
    OUTCOME_FRESHNESS_BLOCK,
    OUTCOME_NEED_CLARIFY,
    OUTCOME_REFUSE,
    OUTCOME_ROWS,
    OUTCOME_UNBOUND_DEGRADE,
    STAR_TABLES,
    WATERMARK_BATCH_PREFIX,
    WINDOW_TOTAL_SCOPE_NOTE,
    PlanCheck,
    QueryOutcome,
    QueryPlan,
    effective_limit,
)
from appv2.retrieval import (
    FAMILY_ALL,
    NOTE_MISSING_SOURCES,
    RetrievalBundle,
    RetrievalNeed,
    anchor_seat_tokens,
)
from appv2.retrieval import (
    Observation as RetrievalObservation,
)
from appv2.tools.argscheck import ArgsError
from appv2.tools.schema import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
    AskFrame,
    Observation,
    Tool,
    ToolContext,
    ToolDescriptor,
    ToolResult,
)
from appv2.tools.well_ids import roster_entries, roster_lookup

# ---------- 工具名闭世界（注册序＝specs/tools.md 接口定义节列序＋V2-31 发现工具） ----------

SEMANTIC_QUERY = "semantic_query"
DATA_QUERY = "data_query"
DOC_RETRIEVE = "doc_retrieve"
GRAPH_QUERY = "graph_query"
SCHEMA_PROBE = "table_schema"
FAQ_LOOKUP = "faq_lookup"

# ---------- faq_lookup 辅助读面缝（V2-52 辅助模式——结构性 Protocol） ----------


class FaqLookupFace(Protocol):
    """FAQ 现成问答库读面（PgFaqStore.similar 同形——serve 归一精确命中）。"""

    def similar(self, question: str, top: int = 3) -> Sequence[Any]: ...

# ---------- 引擎缝（结构性 Protocol——只认公开接口两面） ----------


class QueryFace(Protocol):
    """问数引擎面（QueryEngine validate＋run——specs/modules.md query 卡原形）。"""

    def validate(
        self, plan: QueryPlan, *, candidates: Iterable[str] | None = None
    ) -> PlanCheck: ...

    def run(
        self, plan: QueryPlan, *, approved_tables: tuple[str, ...] = ()
    ) -> QueryOutcome: ...


class RetrievalFace(Protocol):
    """检索引擎面（RetrievalEngine retrieve＋graph——specs/modules.md retrieval 卡）。"""

    async def retrieve(self, need: RetrievalNeed) -> RetrievalBundle: ...

    async def graph(self, need: RetrievalNeed) -> RetrievalBundle: ...


# ---------- args_schema（参数契约——数据面 schema 真源在各自引擎卡，工具层只引用） ----------

_SEMANTIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "question 与 element_name 二选一（同给同缺均拒）",
    "properties": {
        "question": {
            "type": "string",
            "minLength": 1,
            "description": "语义问句（走台账精确名/别名归一匹配，未命中如实回执）",
        },
        "element_name": {
            "type": "string",
            "minLength": 1,
            "description": "台账要素精确名（指标/术语/对象/关系/族标注）",
        },
    },
    "additionalProperties": False,
}

_DATA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "plan_draft": {
            "type": "object",
            "description": (
                "问数计划草案（QueryPlan 草案形——schema 真源在 query 卡，"
                "工具层只引用；window 两槽同缺同在＝模糊时间缺参反问）"
            ),
            "properties": {
                "metric_slot": {"type": "string", "minLength": 1},
                "window_start": {"type": ["string", "null"], "description": "ISO 日期（含）"},
                "window_end": {"type": ["string", "null"], "description": "ISO 日期（不含）"},
                "limit": {"type": ["integer", "null"], "minimum": 1},
                "ranking": {"type": "boolean"},
                "aggregate": {
                    "type": "boolean",
                    "description": "汇总型（V2-71——整窗 SUM 库内算单行返回）",
                },
                "direction": {"type": "string", "enum": ["asc", "desc"]},
                "window_label": {"type": "string"},
                "is_default": {"type": "boolean"},
                "external_tables": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                },
            },
            "required": ["metric_slot", "ranking"],
            "additionalProperties": False,
        }
    },
    "required": ["plan_draft"],
    "additionalProperties": False,
}

_DOC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 1},
        "anchors": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "@ 锚定资产名——并入关键词腿检索单元＋编号保送（P-003 已定实现）",
        },
        "family_hints": {
            "type": "array",
            "items": {"type": "string", "enum": list(FAMILY_ALL)},
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

_GRAPH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string", "minLength": 1},
        "anchors": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "description": "@ 锚定资产名——并入实体匹配问针（锚定语义的图谱侧投影）",
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

_SCHEMA_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "area": {
            "type": "string",
            "enum": ["agg", "sem", "kb"],
            "description": "探查范围（缺省＝全白名单：agg 三表＋sem 五账＋kb 片段清单）",
        },
        "table": {
            "type": "string",
            "minLength": 1,
            "description": "表/账名（如 agg.fct_daily_metering／sem_metric）——"
                           "白名单外如实告知不开放",
        },
        "well": {
            "type": "string",
            "minLength": 1,
            "description": "井号查值（如 W-11／w-11——按 RULE-PETRO-005 归一后比对 "
                           "agg.dim_well 名录；不在册如实回执，不猜最近井）",
        },
    },
    "additionalProperties": False,
}

_FAQ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "minLength": 1,
            "description": "原问句或子问题（FAQ 现成问答库归一精确匹配）",
        },
    },
    "required": ["question"],
    "additionalProperties": False,
}

# ---------- descriptors（渐进披露：名称/说明书/参数 schema/只读声明） ----------
# 说明书三件套（何时用／不能做什么／参数示例——`specs/tools.md` 行为 6，Owner 2026-10-15
# 裁定「要」）：`description` 即模型选工具时看到的全部依据，选得准的第一因；三件逐工具写全，
# 不另加选型规则。原文案一字未删（只在尾部追加三件）。

_SEMANTIC_DESCRIPTION = (
    "语义台账查询：按要素名或问句查指标/术语/对象/关系/族标注的口径卡（只读）。"
    "跨 kind 歧义名（如「日产液」既是术语又是可出数指标的别名落点）：台账 "
    "evidence() 结果优先（术语卡一等材料语义，在前），并组合 metric_by_name "
    "补取可出数指标卡，双落并列返回；question 与 element_name 二选一。"
    "\n何时用：问某指标/术语/对象/关系/族标注「是什么、怎么定义、现行名叫什么、绑定态如何」，"
    "或要素名有歧义要拿口径卡时。"
    "\n不能做什么：不出数（不返回任何数值）、不回文档原文、不写台账。"
    "\n参数示例：{\"element_name\": \"日产油量\"}；{\"question\": \"日产液是什么指标\"}。"
)
_DATA_DESCRIPTION = (
    "权威问数：接收问数计划草案 plan_draft，先经确定性校验（query.validate），"
    "过闸后只读执行，返回权威表（scope=agg）＋血缘卡观察；新鲜度拦停/在册未"
    "绑定降级以闸依据观察＋notice 素材如实返回（零数值不冒充），缺参反问与外"
    "表越集审批转 ask 帧。只读，不自由生成 SQL。"
    "\n何时用：要取数（明细/排名/汇总的权威数值）且能给出查询计划草案时"
    "（metric_slot 与 ranking 必填，排名题 ranking=true 并给 direction）。"
    "\n不能做什么：不自由生成 SQL、不做自然语言直接转 SQL；指标不在册/未绑定、窗界越界、"
    "缺参一律由确定性校验拦停（不返回空数冒充）。"
    "\n参数示例：{\"plan_draft\": {\"metric_slot\": \"日产油量\", \"ranking\": false}}。"
)
_DOC_DESCRIPTION = (
    "文档检索：问句双路召回＋供给窗（可带 anchors 锚定资产名——并入关键词腿"
    "检索单元与编号保送通道；family_hints 族提示驱动供给分池），观察带 "
    "fragment→report→library 出处链与截断显式 window_note。只读。"
    "\n何时用：问题的依据在文档/报告里（制度、规范、报告的表述与算式），而不是台账口径或数据表时。"
    "\n不能做什么：不返回台账口径卡、不返回数据库数值；family_hints 只许族机器名，不写中文名。"
    "\n参数示例：{\"question\": \"1.3 节关于杆柱的算式\", \"anchors\": [\"杆柱\", \"1.3 节\"]}。"
)
_GRAPH_DESCRIPTION = (
    "图谱查询：问句点名实体的一跳邻域边（可带 anchors 锚定资产名——并入实体"
    "匹配问针），边出处 fail-closed 锚校验，观察带 library/报告出处。只读。"
    "\n何时用：要问关系（某实体的一跳邻域边、上下游与归属关系）时。"
    "\n不能做什么：不做多跳遍历、不返回台账口径卡与数据表数值；边出处锚校验不过即如实回执。"
    "\n参数示例：{\"question\": \"渤中 34-8 与哪些平台相连\", \"anchors\": [\"渤中 34-8\"]}。"
)
# V2-31 拍板④：发现工具探查范围＝agg 三表＋sem 五账＋kb 片段清单；raw/lake
# 湖表不开放（白名单外只如实告知，永不给探查卡）。
_SCHEMA_DESCRIPTION = (
    "表结构探查（发现工具）：查数据资产的结构卡——agg 三表（fct_daily_metering"
    " 日产计量事实表/dim_well 井维/dim_date 日期维）、sem 五账（指标/术语/对象/"
    "关系/族标注台账）、kb 片段清单（检索库分族）。dim_well 卡随附【井号名录】"
    "（agg.dim_well 现读·按区块分组·共 N 口）——数据井册看得见；井号查值走 well "
    "参数（井号归一后比对名录，变体写法同判）。白名单外（raw/lake 湖表等）"
    "不在探查范围——如实告知不开放。只读，零 SQL。"
    "\n何时用：先看舱面——不知道有哪些表/账/族、字段叫什么时；或要核"
    "「某井号在不在数据井册」（dim_well 卡看名录全量，well 参数取单元格查值）。"
    "\n不能做什么：零 SQL、不取数（井号查值只答在不在册，不返回产量数值）；"
    "白名单外（raw/lake 湖表等）不给探查卡，只如实告知不开放；名录查值不猜"
    "最近井——不在册即如实回执。"
    "\n参数示例：{\"scope\": \"agg\"}；{\"table\": \"agg.fct_daily_metering\"}；"
    "{\"well\": \"W-11\"}。"
)
# V2-52 辅助模式（附 B）：faq 命中条目作辅助材料进上下文（locator.kind=faq_aux），
# 不进血缘卡（非断言素材源）、不进任何闸的判面；sufficiency 由模型判。
_FAQ_DESCRIPTION = (
    "FAQ 现成问答库查询（发现工具）：问句归一精确匹配服务中条目（标准问/相似"
    "问——相似问优先），命中条目作辅助材料返回（Q/A 形），问句有现成标准答案"
    "时可据此直答或与检索互证；未命中如实回执不阻断。只读。"
    "\n何时用：问句像现成问答（有标准问/相似问条目）时，先取辅助材料。"
    "\n不能做什么：命中条目只作辅助材料——不进血缘卡、不作权威数值断言、不阻断主链。"
    "\n参数示例：{\"question\": \"日产液量怎么算\"}。"
)

# 阈值常量钉死（附 B——THRESHOLD：score ≥ 阈值才消费；读面精确命中恒满分，
# 向量相似路未接线，阈下形态在读面不存在）。
FAQ_AUX_THRESHOLD = 1.0
# 单次调用返回条目上限（附 B——top=3）。
FAQ_TOP_N = 3

# 权威表行来源链（agg 星型读模型事实表——表名机读单点）。
_AGG_SOURCE = STAR_TABLES[0]

# 整窗合计行 handle 前缀（V2-71 汇总型无井位行——`agg_window_sum:{批次}` 形；
# 见 `_window_sum_handle`）。
WINDOW_SUM_HANDLE_PREFIX = "agg_window_sum"

# ---------- 表结构白名单卡（拍板④范围真源——列值全部仓内合同值投影） ----------
# agg 列值源＝query.pg_executor Core 轻声明（DDL 真源＝Alembic 0014）；计量列
# 绑定与单位源＝knowledge.domain.MEASURE_COLUMNS（冻结三绑定）；sem 账面源＝
# knowledge.pg_store 轻声明（DDL 真源＝Alembic 0002/0019）；kb 族源＝
# retrieval.domain.FAMILY_ALL。零发明：本表是读面合同值的发现层投影。

_AGG_CARDS: tuple[str, ...] = (
    "表 agg.fct_daily_metering（日产计量事实表·PK well_id+prod_date）："
    "well_id（井号）、prod_date（日期·查询窗端）、oil_output（日产油量·吨）、"
    "liquid_output（日产液量·方）、oil_pressure（油压·MPa）、batch_id（数据批次）、"
    "quality_flag（质量标记）——问数计划（data_query）唯一取数事实表",
    "表 agg.dim_well（井维度·PK well_id）：well_id（井号）、block_name（区块）、"
    "field_name（油田）",
    "表 agg.dim_date（日期维度·PK date）：date（日期）、month（月）、quarter（季）",
)
# V2-35 数据面盘点回写（卡跟真库走）：sem 四账卡补齐读面投影列——原卡漏列
# id/原名（metric）、状态键/版本（term）、版本（object）、id（relation）四类读面
# 消费列（快照 MetricRow/TermRow/ObjectRow/RelationRow 在投）；台账管理列
# （owner/source/mark/modifiers/ambiguous/时间戳）非读面消费、照投影口径不进卡。
# 逐字段核对表＝tickets/v2/V2-35.数据面盘点.md §1；agg 三卡/kb 卡核对零差异未动。
_SEM_CARDS: tuple[str, ...] = (
    "账 sem_metric（指标台账）：id/原名/slot_name/定义/粒度/单位/状态/争议注记/版本"
    "/口径支/默认口径——semantic_query(question 或 element_name) 查口径卡，绑定指标"
    "才可出数（日产油量→oil_output·吨／日产液量→liquid_output·方／油压→oil_pressure·MPa）",
    "账 sem_term（术语台账）：id/term/类型/定义/状态/状态键/版本/届满——术语卡经 "
    "semantic_query 查",
    "账 sem_object（对象台账）：id/obj/属性/状态/版本（未落版为空）——对象卡经 "
    "semantic_query 查",
    "账 sem_relation（关系台账）：id/rel/读法——关系卡经 semantic_query 查",
    "账 族标注（本体导出物·随台账读面 families）：关系组的族标注——semantic_query 按"
    "导出物名查",
)
_KB_CARDS: tuple[str, ...] = (
    "库 kb 片段清单（检索库·doc_retrieve 检索面）：报告级/片段级两级；分族 "
    "completion（完井报告）/monthly（月报）/dynamic（动态）/blank（空族）——"
    "retrieval_need.family_hints 可按族提示分池",
)


def _card_names(card: str) -> tuple[str, ...]:
    """卡头名两形态提取（P-024b 审查 S1——按名查询的单点判据）。

    卡头合同形「表/账/库 名（…」：名后必跟全角括号（旧实现按 `f"表 {table} "`
    要求表名后跟半角空格——agg 三卡全数失配误判不开放；kb 组「库 …（」形无匹配
    模式）。提取出全名与短名（去 schema 前缀）两形态供精确名匹配：
    表 agg.fct_daily_metering（…）→（agg.fct_daily_metering, fct_daily_metering）；
    账 sem_metric（…）→（sem_metric,）；库 kb 片段清单（…）→（kb 片段清单,）。
    """
    head = card.split("（", 1)[0]
    parts = head.split(" ", 1)
    name = parts[1].strip() if len(parts) == 2 else parts[0].strip()
    names = [name]
    if "." in name:
        names.append(name.rsplit(".", 1)[-1])
    return tuple(names)


# ---------- dim_well 卡【井号名录】段（2026-10-17 流水 70——discover 现读，非常驻注入） ----------
# 病灶（真机 run-e1b6ff1e）：dim_well 卡只给结构不给行值，120 口井号锁在软失败域闸
# 内部（`appv2/query/pg_wells.py`），模型「主体在不在」只能猜/反问。改法：名录随
# dim_well 卡在 **discover 响应**里现读（**非常驻**——台账常驻块的卡片段
# `ledger.ALL_SCHEMA_CARDS` 取自静态 `_AGG_CARDS`，本段不落常驻，常驻块零增重）；
# 井号查值走 `well` 参数（归一比对，见 `tools.well_ids`）。体量纪律：卡面超标即
# 截断＋「共 N 口」计数随行（120 口量级 ≈1KB 实测装得下）。

# 静态卡里 dim_well 那张（按名取——不靠元组下标，零漂移）。
_DIM_WELL_CARD: str = next(
    card for card in _AGG_CARDS if "dim_well" in _card_names(card)
)
_WELL_ROSTER_TABLE = "agg.dim_well"
_WELL_ROSTER_HEAD = "【井号名录】共 {total} 口·dim_well（agg.dim_well 现读·按区块分组）："
_WELL_ROSTER_EMPTY = "（现读为空——数据面无井档行）"
_WELL_ROSTER_FAILED = "【井号名录】现读失败（{error}）——本次不给名录（如实告知，不猜）"
_WELL_ROSTER_BLOCK_UNKNOWN = "未标区块"
_WELL_ROSTER_WELL_SEP = "、"
_WELL_ROSTER_GROUP_SEP = "；"
_WELL_ROSTER_KV_SEP = "："
_WELL_ROSTER_TRUNC = "…（名录超限，只列前 {limit} 口）"
_WELL_ROSTER_MAX = 240


class WellRosterFace(Protocol):
    """井名录取值缝（Callable[[], Sequence[tuple[well_id, block_name]]] 形）。

    生产注入＝`appv2.query.production_well_roster`（agg.dim_well 直读）；缺省
    None＝未接线（卡面照静态形——零漂移）。**每次调用现读**（零缓存——井档随
    数据面刷新即新；本缝不给装配期快照）。
    """

    def __call__(self) -> Sequence[tuple[str, str]]: ...


def _well_roster_rows(
    well_roster: WellRosterFace,
) -> tuple[tuple[tuple[str, str], ...], str]:
    """名录现读（→（行集, 失败说明））；读面异常原样承载（不静默吞、不冒充空名录）。"""
    try:
        return tuple(well_roster()), ""
    except Exception as exc:  # 读面异常如实上报（零发明面）
        return (), f"{exc}"


def _well_roster_section_of(rows: tuple[tuple[str, str], ...]) -> str:
    """名录段正文（按区块分组、全角分隔、计数随行；超限截断＋计数照报）。"""
    entries = roster_entries(rows)
    head = _WELL_ROSTER_HEAD.format(total=len(entries))
    if not entries:
        return head + _WELL_ROSTER_EMPTY
    listed = entries[:_WELL_ROSTER_MAX]
    groups: dict[str, list[str]] = {}
    for well_id, block_name in listed:
        groups.setdefault(block_name or _WELL_ROSTER_BLOCK_UNKNOWN, []).append(well_id)
    body = _WELL_ROSTER_GROUP_SEP.join(
        f"{block}{_WELL_ROSTER_KV_SEP}{_WELL_ROSTER_WELL_SEP.join(sorted(well_ids))}"
        for block, well_ids in sorted(groups.items())
    )
    tail = (
        ""
        if len(listed) == len(entries)
        else _WELL_ROSTER_TRUNC.format(limit=_WELL_ROSTER_MAX)
    )
    return f"{head}{body}{tail}"


def _well_roster_section(well_roster: WellRosterFace) -> str:
    """名录段正文（现读一次——读面异常如实承载，不冒充空名录）。"""
    rows, error = _well_roster_rows(well_roster)
    if error:
        return _WELL_ROSTER_FAILED.format(error=error)
    return _well_roster_section_of(rows)


def _dim_well_card(well_roster: WellRosterFace | None) -> str:
    """dim_well 卡（接线时随附【井号名录】段；未接线＝静态卡逐字零漂移）。"""
    if well_roster is None:
        return _DIM_WELL_CARD
    return f"{_DIM_WELL_CARD}\n{_well_roster_section(well_roster)}"


def _schema_cards(
    area: str | None, table: str | None, *, well_roster: WellRosterFace | None = None
) -> list[Observation]:
    """白名单卡→观察列（kind=schema——发现面素材；白名单外如实告知不开放）。

    dim_well 卡随附【井号名录】段（名录缝接线时现读——非常驻注入）。"""
    area_cards: dict[str, tuple[str, ...]] = {
        "agg": _AGG_CARDS,
        "sem": _SEM_CARDS,
        "kb": _KB_CARDS,
    }
    if table:
        for group in area_cards.values():
            for card in group:
                if table in _card_names(card):  # 全名/短名精确匹配（S1 修复）
                    if card is _DIM_WELL_CARD:
                        return [_schema_observation(_dim_well_card(well_roster))]
                    return [_schema_observation(card)]
        return [
            _notice_observation(
                content=(
                    f"表 {table} 不在探查白名单（agg 三表＋sem 五账＋kb 片段清单；"
                    "raw/lake 湖表不开放）——只可探查白名单内资产结构。"
                ),
                notice_type="schema_not_allowed",
                source="table_schema 白名单闸",
                source_id=table,
            )
        ]
    if area is not None:
        cards: tuple[str, ...] | None = area_cards.get(area)
        if cards is None:
            return [
                _notice_observation(
                    content=(
                        f"未知探查范围 {area!r}（允许 agg/sem/kb——白名单⑥；"
                        "raw/lake 湖表不开放）"
                    ),
                    notice_type="schema_not_allowed",
                    source="table_schema 白名单闸",
                )
            ]
        return [
            _schema_observation(
                _dim_well_card(well_roster) if card is _DIM_WELL_CARD else card
            )
            for card in cards
        ]
    return [
        _schema_observation(
            _dim_well_card(well_roster) if card is _DIM_WELL_CARD else card
        )
        for cards in area_cards.values()
        for card in cards
    ]


def _well_lookup_observations(
    name: str, well_roster: WellRosterFace | None
) -> list[Observation]:
    """井号查值（RULE-PETRO-005 归一后名录成员判定）：dim_well 卡＋在册/不在册如实。

    命中＝观察（locator.kind=well_lookup，source_id＝归一井号——机读可对账）；
    不在册＝notice no_hit（**不猜最近井**）；名录不可得（未接线/现读失败）＝
    notice well_roster_unavailable（如实告知无法查证，不静默冒充空名录）。

    名录**恰读一次**（卡面名录段与判据同源同一行集——同一响应内不自相矛盾）。
    """
    if well_roster is None:
        return [
            _schema_observation(_DIM_WELL_CARD),
            _notice_observation(
                content=f"井号名录读缝未接线：无法查证 {name} 在不在册（如实告知，不猜）",
                notice_type="well_roster_unavailable",
                source="table_schema 井号名录读面",
                source_id="well_roster_unavailable",
            ),
        ]
    rows, error = _well_roster_rows(well_roster)
    if error:
        return [
            _schema_observation(_DIM_WELL_CARD),
            _notice_observation(
                content=(
                    f"井号名录现读失败（{error}）——无法查证 {name} 在不在册"
                    "（如实告知，不猜）"
                ),
                notice_type="well_roster_unavailable",
                source="table_schema 井号名录读面",
                source_id="well_roster_unavailable",
            ),
        ]
    observations = [
        _schema_observation(f"{_DIM_WELL_CARD}\n{_well_roster_section_of(rows)}")
    ]
    hit = roster_lookup(name, rows)
    if hit is None:
        observations.append(
            _notice_observation(
                content=(
                    f"井号未命中名录：{name}（agg.dim_well 现读名录无此井——"
                    "如实告知不在册，不猜最近井）"
                ),
                notice_type="no_hit",
                source="table_schema 井号名录读面",
                source_id="no_hit",
            )
        )
        return observations
    well_id, block_name = hit
    observations.append(
        Observation(
            content=(
                f"井号在册：{well_id}（区块 "
                f"{block_name or _WELL_ROSTER_BLOCK_UNKNOWN}）——归一比对命中 "
                f"agg.dim_well 名录（共 {len(roster_entries(rows))} 口）"
            ),
            source="table_schema 井号名录读面",
            source_id=well_id,
            version=None,  # 井档无版本承载——零发明
            freshness="",  # 时效在数据面水位面——井册行级不重复标注
            scope="schema",
            locator={
                "kind": "well_lookup",
                "table": _WELL_ROSTER_TABLE,
                "well_id": well_id,
                "block_name": block_name,
            },
        )
    )
    return observations


def _schema_observation(card: str) -> Observation:
    return Observation(
        content=card,
        source="table_schema 白名单读面",
        source_id=card.split("：", 1)[0],
        version=None,
        freshness="",
        scope="schema",
        locator={"kind": "schema", "area": "whitelist"},
    )


# ---------- 装配（registry 构造期调用——引擎缝注入闭包） ----------


def build_tools(
    *,
    knowledge: KnowledgeStore,
    query: QueryFace,
    retrieval: RetrievalFace,
    faq: FaqLookupFace | None = None,
    well_roster: WellRosterFace | None = None,
) -> list[Tool]:
    """五工具装配（注册序＝specs/tools.md 列序＋V2-31 发现工具殿后；全部 readonly=True）。

    faq＝FAQ 现成问答库读缝（V2-52 辅助模式——提供时注册 faq_lookup 发现工具，
    缺省 None＝不在册：faq_* 缝未接线的装配零漂移）。
    well_roster＝井名录取值缝（2026-10-17 流水 70——table_schema 的 dim_well 卡
    名录段与 `well` 查值消费；缺省 None＝未接线：卡面照静态形、查值如实告知
    不可得，零漂移）。
    """
    async def _semantic(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await semantic_query(args, ctx, knowledge=knowledge)

    async def _data(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await data_query(args, ctx, query=query)

    async def _doc(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await doc_retrieve(args, ctx, retrieval=retrieval)

    async def _graph(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return await graph_query(args, ctx, retrieval=retrieval)

    async def _schema(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return table_schema(args, ctx, well_roster=well_roster)

    tools = [
        Tool(
            descriptor=ToolDescriptor(
                name=SEMANTIC_QUERY,
                description=_SEMANTIC_DESCRIPTION,
                args_schema=_SEMANTIC_SCHEMA,
            ),
            handler=_semantic,
        ),
        Tool(
            descriptor=ToolDescriptor(
                name=DATA_QUERY,
                description=_DATA_DESCRIPTION,
                args_schema=_DATA_SCHEMA,
            ),
            handler=_data,
        ),
        Tool(
            descriptor=ToolDescriptor(
                name=DOC_RETRIEVE,
                description=_DOC_DESCRIPTION,
                args_schema=_DOC_SCHEMA,
            ),
            handler=_doc,
        ),
        Tool(
            descriptor=ToolDescriptor(
                name=GRAPH_QUERY,
                description=_GRAPH_DESCRIPTION,
                args_schema=_GRAPH_SCHEMA,
            ),
            handler=_graph,
        ),
        Tool(
            descriptor=ToolDescriptor(
                name=SCHEMA_PROBE,
                description=_SCHEMA_DESCRIPTION,
                args_schema=_SCHEMA_SCHEMA,
            ),
            handler=_schema,
        ),
    ]
    if faq is not None:

        async def _faq(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
            return await faq_lookup(args, ctx, faq=faq)

        tools.append(
            Tool(
                descriptor=ToolDescriptor(
                    name=FAQ_LOOKUP,
                    description=_FAQ_DESCRIPTION,
                    args_schema=_FAQ_SCHEMA,
                ),
                handler=_faq,
            )
        )
    return tools


# ---------- 工具一：semantic_query ----------


async def semantic_query(
    args: dict[str, Any], ctx: ToolContext, *, knowledge: KnowledgeStore
) -> ToolResult:
    """语义台账查询（evidence() 优先＋metric_by_name 补取，双落并列去重）。"""
    question = args.get("question")
    element_name = args.get("element_name")
    if (question is None) == (element_name is None):
        raise ArgsError("question 与 element_name 须二选一（同给同缺均拒）")
    text = str(element_name if element_name is not None else question).strip()
    evidences = knowledge.evidence(SemanticQuery(text=text))
    observations = [_evidence_observation(evidence) for evidence in evidences]
    seen = {evidence.element_id for evidence in evidences}
    metric = knowledge.metric_by_name(text)
    if metric is not None and metric.element_id not in seen:
        observations.append(_evidence_observation(metric))  # 对齐项①补取位
    if not observations:
        observations.append(
            _notice_observation(
                content=f"台账未命中：{text}（精确名与别名归一均未命中——请核对要素名）",
                notice_type="no_hit",
                source="sem_* 台账读面",
                source_id="no_hit",
            )
        )
    return ToolResult.ok(observations)


def _evidence_observation(evidence: Evidence) -> Observation:
    """台账卡→统一观察（content←value、source_id←element_id、locator←source）。"""
    return Observation(
        content=evidence.value,
        source=evidence.source,
        source_id=evidence.element_id,
        version=evidence.version,
        freshness=evidence.freshness,
        scope=evidence.scope,
        locator={
            "kind": evidence.kind,
            "element_id": evidence.element_id,
            "source": evidence.source,
            "binding_state": evidence.binding_state,
        },
    )


# ---------- 工具二：data_query ----------


async def data_query(
    args: dict[str, Any], ctx: ToolContext, *, query: QueryFace
) -> ToolResult:
    """权威问数（plan_draft 先经 query.validate——不过＝bad_args，run 零调用）。

    放行态随行（V2-52 越集续跑全通道）：ctx.approved_tables 传引擎——已批表
    放行续跑，未批子集照旧挂审批（审批不再二循环）。
    """
    plan = _plan_from_draft(args["plan_draft"], actor=ctx.actor)
    check = query.validate(plan, candidates=ctx.metric_candidates)
    if not check.ok:
        return ToolResult.failed(
            CATEGORY_BAD_ARGS,
            check.reason or "计划校验未过",
            hint="按校验理由修 plan_draft 后重试（校验拒＝引擎未执行）",
        )
    return _outcome_to_result(query.run(plan, approved_tables=ctx.approved_tables), plan=plan)


def _plan_from_draft(draft: Mapping[str, Any], *, actor: str) -> QueryPlan:
    """草案→QueryPlan（日期解析/构造校验失败＝ArgsError→bad_args；身份只从 ctx 进）。"""
    try:
        start_raw = draft.get("window_start")
        end_raw = draft.get("window_end")
        window_start = date.fromisoformat(str(start_raw)) if start_raw is not None else None
        window_end = date.fromisoformat(str(end_raw)) if end_raw is not None else None
        return QueryPlan(
            metric_slot=str(draft["metric_slot"]),
            window_start=window_start,
            window_end=window_end,
            limit=draft.get("limit"),
            ranking=bool(draft["ranking"]),
            aggregate=bool(draft.get("aggregate", False)),
            direction=str(draft.get("direction") or DIRECTION_DESC),
            window_label=str(draft.get("window_label") or ""),
            is_default=bool(draft.get("is_default", False)),
            external_tables=tuple(draft.get("external_tables") or ()),
            actor=actor,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ArgsError(f"plan_draft 装配失败：{exc}") from exc


def _outcome_to_result(outcome: QueryOutcome, *, plan: QueryPlan | None = None) -> ToolResult:
    """六联合态→ToolResult 逐态映射（specs/tools.md 行为约定 4 单点）。

    `plan`＝本发射的定案计划（可选；行联合态的限量面判据——血缘载荷的 LIMIT
    触顶事实。缺位＝如实不判触顶，零猜测）。
    """
    if outcome.kind == OUTCOME_ROWS:
        return ToolResult.ok(_rows_observations(outcome, plan=plan))
    if outcome.kind == OUTCOME_FRESHNESS_BLOCK:
        return ToolResult.ok(
            (
                _notice_observation(
                    content=outcome.message or "",
                    notice_type=OUTCOME_FRESHNESS_BLOCK,
                    source="汇总层水位读面",
                    extra={
                        "watermark_date": (
                            outcome.watermark_date.isoformat()
                            if outcome.watermark_date is not None
                            else ""
                        ),
                        "window_label": outcome.window_label or "",
                        "is_default": "true" if outcome.is_default else "false",
                    },
                ),
            )
        )
    if outcome.kind == OUTCOME_UNBOUND_DEGRADE:
        observations: list[Observation] = []
        if outcome.evidence is not None:
            observations.append(_evidence_observation(outcome.evidence))
        observations.append(
            _notice_observation(
                content=outcome.basis or "",
                notice_type=OUTCOME_UNBOUND_DEGRADE,
                source="query 引擎降级依据",
            )
        )
        return ToolResult.ok(observations)
    if outcome.kind == OUTCOME_NEED_CLARIFY:
        return ToolResult.ask_frame(
            AskFrame(
                kind=ASK_CLARIFY,
                prompt=outcome.clarify_question or "",
                options=tuple(outcome.choices or ()),
            )
        )
    if outcome.kind == OUTCOME_EXTERNAL_TABLE_APPROVAL:
        ask_card = dict(outcome.ask or {})
        # V2-52 越集续跑通道：表名集随卡（additive 键——放行名单回填的机读面，
        # runtime 批准落点经 detail.tables 进 approved_ids 随行重判/放行）。
        if outcome.external_tables:
            ask_card["tables"] = [str(t) for t in outcome.external_tables]
        return ToolResult.ask_frame(
            AskFrame(
                kind=ASK_EXTERNAL_TABLE_APPROVAL,
                prompt=str(ask_card.get("reason", "")),
                options=("批准", "驳回"),
                detail=ask_card or None,
            )
        )
    if outcome.kind == OUTCOME_REFUSE:
        return ToolResult.failed(
            CATEGORY_REFUSED,
            outcome.reason or "闸拒",
            hint="口径/数据闸拒——不重试，按拒因如实转用户",
        )
    raise ValueError(f"未知 QueryOutcome.kind：{outcome.kind!r}（六联合态闭世界外）")


def _window_sum_handle(outcome: QueryOutcome) -> str:
    """整窗合计行的可寻址 handle（形 `agg_window_sum:{批次}`——批次缺位如实留白）。

    批次读面＝血缘④行前缀（`WATERMARK_BATCH_PREFIX` 单源——血线行非本块自写文本，
    按同一常量读回）；水位未回写／批次未回填时 handle 只到前缀（不编批次号冒充
    可寻址）。**汇总型专属**：井位行不走本径（行键＝井号）。
    """
    for line in outcome.lineage or ():
        if line.key != LINEAGE_KEY_WATERMARK:
            continue
        tail = line.value.removeprefix(WATERMARK_BATCH_PREFIX)
        if tail == line.value:  # 无批次前缀（水位未回写——如实缺行）
            break
        batch = tail.split(" · ", 1)[0].strip()
        if batch:
            return f"{WINDOW_SUM_HANDLE_PREFIX}:{batch}"
        break
    return WINDOW_SUM_HANDLE_PREFIX


def _rows_observations(
    outcome: QueryOutcome, *, plan: QueryPlan | None = None
) -> list[Observation]:
    """权威表＋血缘卡→观察列（行级表名出处＋locator 机读行键；scope=agg）。

    两种行形分派（V2-71 汇总型——L5·02 病灶修复②）：井位行＝既有 `{井号}@{日期}`
    行键＋`well_id`/`prod_date` locator；整窗 SUM 单行（无井位键）＝**不写空井位列
    冒充单井行**，行内容前置「整窗合计·全井」确定性口径标注（域层常量单源）＋行键
    用行集 handle（`agg_window_sum:{批次}`——可寻址）。

    血缘卡观察除正文（五要素逐行原文）外携**结构化载荷** `locator.payload`（2026-10-17
    EB2：键名单点＝schema 的 `LOCATOR_PAYLOAD_KEY` 族；五要素子键＝血缘行合同键本身，
    限量面按 `plan` 判触顶）——材料面据此合成口径行、帧面透传前端，两处都不解析正文文本串。
    """
    observations: list[Observation] = []
    columns = outcome.columns or ()
    keys = [data_index for data_index, _title in columns]
    titles = [title for _data_index, title in columns]
    for row in outcome.rows or ():
        content = "；".join(
            f"{title}={_cell(row.get(key))}" for key, title in zip(keys, titles, strict=True)
        )
        if "well_id" in row:
            well_id = str(row.get("well_id", ""))
            prod_date = row.get("prod_date")
            locator = {"kind": "agg_row", "table": _AGG_SOURCE, "well_id": well_id}
            source_id = well_id
            if prod_date is not None:
                locator["prod_date"] = str(prod_date)
                source_id = f"{well_id}@{prod_date}"
        else:
            # 整窗合计行（汇总型——无井位键）：行键＝行集 handle（可寻址），
            # locator 标口径面（不设 `well_id` 键——零空串冒充井位），行内容
            # 前置口径标注（单行不是某口井的行，行面自明）。
            handle = _window_sum_handle(outcome)
            locator = {
                "kind": "agg_row",
                "table": _AGG_SOURCE,
                "window_total": WINDOW_TOTAL_SCOPE_NOTE,
                "handle": handle,
            }
            source_id = handle
            content = f"{WINDOW_TOTAL_SCOPE_NOTE}；{content}"
        observations.append(
            Observation(
                content=content,
                source=_AGG_SOURCE,
                source_id=source_id,
                version=None,  # 行级无版本承载——零发明
                freshness="",  # 时效在血缘卡④水位行——行级不重复标注
                scope="agg",  # specs/tools.md 行为约定 4：权威表 scope=agg
                locator=locator,
            )
        )
    if outcome.lineage:
        limit_hit = _limit_hit(outcome, plan)
        observations.append(
            Observation(
                content="\n".join(f"{line.key} {line.value}" for line in outcome.lineage),
                source=" ⋈ ".join(STAR_TABLES),
                source_id="lineage",
                version=None,
                freshness="",
                scope="agg",
                locator={
                    "kind": "lineage",
                    "table": _AGG_SOURCE,
                    LOCATOR_PAYLOAD_KEY: {
                        LINEAGE_PAYLOAD_KEY: {
                            line.key: line.value for line in outcome.lineage
                        },
                        LINEAGE_LIMIT_KEY: {
                            LINEAGE_LIMIT_HIT_KEY: limit_hit,
                            # 未触顶＝零行数（不报无关数——消费面按触顶位判尾缀）
                            LINEAGE_LIMIT_ROWS_KEY: (
                                len(outcome.rows or ()) if limit_hit else 0
                            ),
                        },
                    },
                },
            )
        )
    if outcome.rebind_notice:
        observations.append(
            _notice_observation(
                content=outcome.rebind_notice,
                notice_type="rebind",
                source="汇总层水位读面",
            )
        )
    return observations


def _limit_hit(outcome: QueryOutcome, plan: QueryPlan | None) -> bool:
    """血缘载荷的 LIMIT 触顶事实（明细/排名形交付行数触顶——整窗 SUM 型无行数 LIMIT 恒否）。

    「触顶」＝本次交付行数达有效限量（`effective_limit(plan.limit)`——F14 收口值，
    单点＝`appv2.query`）。`plan` 缺位（装配面未随行计划）＝如实 False（不猜触顶）。
    """
    if plan is None or plan.aggregate:
        return False
    return len(outcome.rows or ()) >= effective_limit(plan.limit)


def _cell(value: Any) -> str:
    return "" if value is None else str(value)


def _notice_observation(
    *,
    content: str,
    notice_type: str,
    source: str,
    source_id: str | None = None,
    extra: Mapping[str, str] | None = None,
) -> Observation:
    """notice 素材观察（闸依据/截断声明/未命中——locator.kind=notice 机读分型）。"""
    locator = {"kind": "notice", "notice_type": notice_type}
    if extra:
        locator.update(extra)
    return Observation(
        content=content,
        source=source,
        source_id=source_id if source_id is not None else notice_type,
        version=None,
        freshness="",
        scope="",
        locator=locator,
    )


# ---------- 工具三/四：doc_retrieve 与 graph_query ----------


async def doc_retrieve(
    args: dict[str, Any], ctx: ToolContext, *, retrieval: RetrievalFace
) -> ToolResult:
    """文档检索（anchors/family_hints/ctx.budget 逐字进 RetrievalNeed——对齐项②契约）。"""
    need = RetrievalNeed(
        question=str(args["question"]),
        anchors=tuple(args.get("anchors") or ()),
        family_hints=tuple(args.get("family_hints") or ()),
        budget=ctx.budget,
    )
    return _bundle_to_result(await retrieval.retrieve(need))


async def graph_query(
    args: dict[str, Any], ctx: ToolContext, *, retrieval: RetrievalFace
) -> ToolResult:
    """图谱查询（anchors 并入实体匹配问针——引擎 face 按问针子串匹配实体名）。"""
    question = str(args["question"])
    anchors = tuple(args.get("anchors") or ())
    needle = question if not anchors else f"{question} {' '.join(anchors)}"
    need = RetrievalNeed(question=needle, anchors=anchors, budget=ctx.budget)
    return _bundle_to_result(await retrieval.graph(need))


# ---------- 工具五：table_schema（V2-31 发现工具——白名单⑥结构卡） ----------


def table_schema(
    args: dict[str, Any], ctx: ToolContext, *, well_roster: WellRosterFace | None = None
) -> ToolResult:
    """表结构探查（白名单卡静态投影＋dim_well 卡【井号名录】段现读；拍板④：raw/lake 不开放）。

    三形互斥：`area`／`table`（卡面）与 `well`（井号查值——归一比对名录，
    2026-10-17 流水 70）。查值形只看 dim_well 名录（结构卡随行），命中/不在册
    一律如实（不猜最近井）。
    """
    area = args.get("area")
    table = args.get("table")
    well = args.get("well")
    if area is not None and table is not None:
        raise ArgsError("area 与 table 二选一（同给不收）")
    if well is not None and (area is not None or table is not None):
        raise ArgsError(
            "well 与 area/table 二选一（井号查值只看 dim_well 名录——同给不收）"
        )
    if well is not None:
        return ToolResult.ok(_well_lookup_observations(str(well), well_roster))
    return ToolResult.ok(_schema_cards(
        str(area) if area is not None else None,
        str(table).strip() if table is not None else None,
        well_roster=well_roster,
    ))


# ---------- 工具六：faq_lookup（V2-52 辅助模式——附 B 执行语义） ----------


async def faq_lookup(
    args: dict[str, Any], ctx: ToolContext, *, faq: FaqLookupFace
) -> ToolResult:
    """FAQ 现成问答库查询（附 B 伪代码的执行件落位——施工基准照抄）：

    归一（NFKC＋剥全部标点——knowledge.normalize_faq_question 单点）→读面
    相似问优先取 top →阈值（FAQ_AUX_THRESHOLD）与禁用条目（disabled）剔除 →
    命中＝辅助材料观察（locator.kind=faq_aux、source_id=faq_entry:<id>、
    content＝逐条「Q：标准问 / A：答案」——不进血缘卡，不进任何闸的判面，
    sufficiency 由模型判）；未命中＝机读 note「FAQ 库无命中」如实（空集，
    不阻断继续检索）。
    """
    question = str(args.get("question") or "").strip()
    if not question:
        raise ArgsError("缺 question（原问句或子问题必填）")
    hits = [
        hit
        for hit in faq.similar(question, top=FAQ_TOP_N)
        if float(getattr(hit, "score", 0.0)) >= FAQ_AUX_THRESHOLD
        and not getattr(hit, "disabled", False)
    ]
    if not hits:
        return ToolResult.ok([
            _notice_observation(
                content=f"FAQ 库无命中（{question}）——现成问答库未收该问句，"
                        "请按台账/检索继续",
                notice_type="no_hit",
                source="faq_* 读面",
                source_id="no_hit",
            )
        ])
    observations = [
        Observation(
            content=f"Q：{hit.question} / A：{hit.answer}",
            source="faq_entry",
            source_id=f"faq_entry:{hit.entry_id}",
            version=None,
            freshness="",  # FAQ 库无时效承载——零发明
            scope="faq",
            locator={"kind": "faq_aux", "entry_id": str(hit.entry_id)},
        )
        for hit in hits
    ]
    return ToolResult.ok(observations)


def _missing_sources_segment(window_note: str) -> str:
    """未纳入来源段提取（V2-46 R1c——window_note 载未纳入名单时的「检索窗注记」素材面）。

    build_window_note（retrieval.domain 组装单点）的该段措辞＝本模块 import 的
    单点常量 `NOTE_MISSING_SOURCES`（V2-82e 起措辞归用户语——「以下来源因数量
    限制未纳入：〈来源名列〉」），段界＝「；」或串尾（扩席实录等 extra 段在其后）。
    无该段＝空串（零注记——旧形零漂移）。
    """
    marker = NOTE_MISSING_SOURCES
    position = window_note.find(marker)
    if position < 0:
        return ""
    rest = window_note[position:]
    cut = rest.find("；")
    return rest if cut < 0 else rest[:cut]


def recall_relevant(question: str, missing_note: str) -> bool:
    """缺位回捞相关面（V2-46 R1c——回捞白场合同条件「本问题组相关报告/章节
    在列」的确定性机读；零模型词面判定，anchor_seat_tokens 同款先例）。

    问句资产 token（井号/报告号等编号形——纯数字与语义词不作判据，防保底
    泛化）任一命中缺位注记文本＝相关在列；问句无资产 token 或零命中＝名单
    与题面无表面关联（机器不为噪声名单开回炉轮——保守面：名单可见性不受
    影响，模型面照常）。零 LLM、零 IO。
    """
    content = missing_note.casefold()
    return any(
        token.casefold() in content for token in anchor_seat_tokens(question)
    )


def _bundle_to_result(bundle: RetrievalBundle) -> ToolResult:
    """供给窗→观察列（每支出处链逐支透传＋window_note 截断声明 notice）。

    V2-46 R1c：未纳入来源名单在场（window_note 载 `NOTE_MISSING_SOURCES` 段）时
    追加**非 notice 类**「检索窗注记」观察（locator.kind=window_miss——未进窗
    名单＋原因）：名单模型可见，回捞白场（CLARIFY_CONTRACT 追加段）的触发
    信号。notice 过滤机制零改动——window_miss 是新增观察类，不经 notice
    通道（notice 面照旧：window_note 截断声明仍走原通道）。
    """
    observations = [_retrieval_observation(obs) for obs in bundle.observations]
    observations.append(
        _notice_observation(
            content=bundle.window_note,
            notice_type="window_note",
            source="检索供给窗声明（截断显式）",
        )
    )
    missing = _missing_sources_segment(bundle.window_note)
    if missing:
        observations.append(
            Observation(
                content=f"检索窗注记：{missing}",
                source="检索供给窗声明（缺位名单）",
                source_id="window_miss",
                version=None,
                freshness="",
                scope="",
                locator={"kind": "window_miss"},
            )
        )
    return ToolResult.ok(observations)


def _retrieval_observation(obs: RetrievalObservation) -> Observation:
    """检索观察→统一观察（fragment→report→library 出处链原样＋kind 分型）。"""
    locator = {str(key): str(value) for key, value in obs.locator.items()}
    locator["kind"] = obs.kind  # fragment | graph
    return Observation(
        content=obs.text,
        source=obs.report,  # report 级
        source_id=obs.fragment_id or "",  # fragment 级（图谱无锚边＝空串如实）
        version=None,
        freshness="",
        scope=obs.family,  # family 标注（库 biz_template 透传）
        locator=locator,  # library 级＋section/fragment_id 机读
        well=obs.well,  # V2-64 切片本体标签透传（缺省 None）
    )
