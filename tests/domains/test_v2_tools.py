"""V2-05 tools 工具层验收——specs/tools.md「验收测试」表五条逐条落测（1:1 同名）
＋两条对齐项钉测（V2-02/V2-04 收口时归属本票落实的两条）。

五条对应（票面验收表）：
- descriptors_readonly：四工具 descriptors 齐、全 readonly=True（INV-2 工具层落点
  ——registry 拒绝注册 readonly!=True 的工具；registry 公开面零写出口）；
  渐进披露四字段（名称/一句话用途/参数 schema/只读声明）；semantic_query 的
  description 载对齐项①合同语义（术语卡优先＋metric_by_name 补取可出数指标、
  双落并列返回）。
- bad_args_notouch_engine：参数先经 args_schema 校验——不合→failed(bad_args)
  引擎零调用（三引擎调用计数全零）；data_query 草案先经 query.validate——
  不过→failed(bad_args, 校验理由) 且 run 零调用；plan_draft 非法日期/缺必填/
  越参/族越界/二参同给——全部 schema/装配层拒，引擎零触。
- error_taxonomy：引擎异常统一三分类——超时→retryable；上游 4xx 类→bad_args；
  网关 UpstreamRejected→bad_args／UpstreamUnavailable→retryable（V2-18/C6 补支
  ——真实网关异常形不带 status_code，类型面判定）；5xx/其余上游抖动→retryable；
  越权→refused；query 闸拒（refuse 联合态）→refused。
- query_outcome_mapping：query 六联合态→ToolResult 逐态映射——rows+lineage→
  ok＋observations(权威表 scope=agg＋血缘卡)；freshness_block/unbound_degrade→
  ok＋闸依据观察＋notice 素材；need_clarify/external_table_approval→ask＋
  AskFrame（clarify/external_table_approval 两形态）；refuse→failed(refused)。
- observation_provenance：每支 Observation 来源链完整——台账行（sem_*#行 id）、
  权威表行（表名＋行键机读 locator）、fragment→report→library 三级链＋
  window_note 截断声明（真引擎装配：InMemoryKnowledgeStore＋QueryEngine
  （CsvSnapshotExecutor）＋RetrievalEngine（内存片段库＋LocalHashEmbedder））。

两条对齐项钉测：
- semantic_dual_landing（对齐自 V2-02 收口疑点 3）：「日产液」跨 kind 歧义名
  →evidence() 术语卡优先（#11 届满词条卡在前）＋metric_by_name 补取可出数指标
  （别名归一→#202 日产液量 bound 在后），双落并列返回；纯指标名去重单卡；
  未命中如实 notice。
- anchors_contract（对齐自 V2-04 收口疑点 4）：doc_retrieve 的 anchors/
  family_hints/budget 逐字进 RetrievalNeed（P-003 已定实现＝并入关键词腿检索
  单元＋编号保送——工具层参数契约与之一致）；graph_query 的 anchors 并入实体
  匹配问针（锚定语义的图谱侧投影，真引擎端到端：锚名只在 anchors 提名时边
  可达）——V2-97（D7）注册面摘除后改直调 handler 面钉契约（代码保留、引擎
  零改）。

V2-97（D7）两条（图谱腿/compound 精排摘暴露面）：
- graph_query_not_registered：`graph_query` 不在工具注册面（descriptors 名单
  零该名；registry.call 判「未知工具」bad_args、图谱引擎零调用）。
- graph_leg_code_kept：GraphSource 协议／compound 精排件（`_llm_rerank`／
  `_batch_order`／`_doc_confidence`＋提示词常量）仍在册（AST 存在性），模块注
  携 `DEBT(V2-97)` 标记（去向＝接线决策票）。

fixture＝问数组台账态快照（appv2.knowledge 公开接口）＋题册绑定 CSV 快照
（CsvSnapshotExecutor）＋V2-04 同源真报告片段抽样（三支，出处链逐字）；时钟
注入固定执行日 2026-10-08、水位 2026-08-31（与 V2-03 验收底座同款）。假引擎
adapter（FakeKnowledgeStore/FakeQueryEngine/FakeRetrievalEngine）即 P-006
runtime 票复用件。本票零 LLM 调用（工具层纯转发——精排/嵌入归引擎缝）。
"""

from __future__ import annotations

import ast
import dataclasses
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.infra.llm_client import UpstreamRejected, UpstreamUnavailable
from appv2.knowledge import Evidence, InMemoryKnowledgeStore, question_array_snapshot
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_FILTER,
    LINEAGE_KEY_PERMISSION,
    LINEAGE_KEY_SOURCE,
    LINEAGE_KEY_WATERMARK,
    CsvSnapshotExecutor,
    LineageLine,
    QueryEngine,
    QueryOutcome,
    WatermarkFace,
)
from appv2.retrieval import (
    FAMILY_ALL,
    FragmentRecord,
    GraphEdgeRecord,
    InMemoryFragmentLibrary,
    LocalHashEmbedder,
    RetrievalEngine,
)
from appv2.tools import (
    ASK_CLARIFY,
    ASK_EXTERNAL_TABLE_APPROVAL,
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    CATEGORY_RETRYABLE,
    DATA_QUERY,
    DOC_RETRIEVE,
    FETCH_REPORT,
    FETCH_SECTION,
    GRAPH_QUERY,
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
    SCHEMA_PROBE,
    SEMANTIC_QUERY,
    STATUS_ASK,
    STATUS_FAILED,
    STATUS_OK,
    FakeKnowledgeStore,
    FakeQueryEngine,
    FakeRetrievalEngine,
    FakeUpstreamRejection,
    Tool,
    ToolContext,
    ToolDescriptor,
    ToolRegistry,
    ToolResult,
)
from appv2.tools.handlers import graph_query as graph_query_handler

# 执行日钉 2026-10-08、水位 2026-08-31（V2-03/V2-04 验收底座同款——不吃墙上时钟）。
TODAY = date(2026, 10, 8)
WATERMARK = date(2026, 8, 31)
CTX = ToolContext(actor="dev-u1", budget=4)

# data_query 合法草案（引擎零触测试与闸拒测试共用基形）。
_VALID_DRAFT: dict[str, Any] = {"metric_slot": "日产油量", "ranking": False}


def _evidence(
    element_id: str, kind: str, *, source: str, binding_state: str = "unbound"
) -> Evidence:
    return Evidence(
        element_id=element_id,
        kind=kind,
        value=f"要素{element_id}：测试口径卡",
        source=source,
        version="1",
        freshness="",
        scope="日",
        binding_state=binding_state,
    )


def _registry(
    *,
    knowledge: FakeKnowledgeStore | None = None,
    query: FakeQueryEngine | None = None,
    retrieval: FakeRetrievalEngine | None = None,
) -> tuple[ToolRegistry, FakeKnowledgeStore, FakeQueryEngine, FakeRetrievalEngine]:
    """假引擎装配的 registry（三缝调用计数全量可断言——零触测试的被观测面）。"""
    kb = knowledge if knowledge is not None else FakeKnowledgeStore()
    q = query if query is not None else FakeQueryEngine()
    r = retrieval if retrieval is not None else FakeRetrievalEngine()
    return ToolRegistry(knowledge=kb, query=q, retrieval=r), kb, q, r


def _by_kind(result: ToolResult, kind: str) -> list[Any]:
    return [obs for obs in result.observations if obs.locator.get("kind") == kind]


# ---------- 验收①：四工具 descriptors 齐、全 readonly（INV-2 工具层落点） ----------


async def test_descriptors_readonly() -> None:
    registry, _kb, _q, _r = _registry()
    descriptors = registry.descriptors()
    # 六工具齐、注册序＝spec 顺序（specs/tools.md 接口定义节列序＋V2-96 两新工具
    # ＋V2-31 发现工具 table_schema 殿后）。V2-97（D7）：graph_query 已摘除注册面（不在册）。
    assert [d.name for d in descriptors] == [
        SEMANTIC_QUERY,
        DATA_QUERY,
        DOC_RETRIEVE,
        FETCH_SECTION,
        FETCH_REPORT,
        SCHEMA_PROBE,
    ]
    # 全 readonly=True（INV-2）＋渐进披露恰四字段（名称/描述/参数 schema/只读声明）。
    for descriptor in descriptors:
        assert descriptor.readonly is True
        assert {f.name for f in dataclasses.fields(descriptor)} == {
            "name",
            "description",
            "args_schema",
            "readonly",
        }
    schema_of = {d.name: d.args_schema for d in descriptors}
    # 参数 schema 逐工具契约（与 specs/tools.md「四工具」行一致——V2-97 后
    # graph_query 不在注册面，其 schema 契约面归 handler 保留件，见
    # graph_leg_code_kept／anchors_contract）。
    assert set(schema_of[SEMANTIC_QUERY]["properties"]) == {"question", "element_name"}
    assert set(schema_of[DATA_QUERY]["properties"]) == {"plan_draft"}
    assert set(schema_of[DOC_RETRIEVE]["properties"]) == {
        "question",
        "anchors",
        "family_hints",
    }
    # plan_draft 形状＝QueryPlan 草案（schema 真源在 query 卡——工具层只引用不另造）。
    plan_props = schema_of[DATA_QUERY]["properties"]["plan_draft"]["properties"]
    assert set(plan_props) == {
        "metric_slot",
        "window_start",
        "window_end",
        "limit",
        "ranking",
        "direction",
        "window_label",
        "is_default",
        "external_tables",
        "aggregate",  # V2-71 汇总型（聚合下推——整窗 SUM 库内算）
    }
    # family_hints 值域＝四族闭世界（retrieval FAMILY_ALL 透传，不造第二份）。
    assert schema_of[DOC_RETRIEVE]["properties"]["family_hints"]["items"]["enum"] == list(
        FAMILY_ALL
    )
    # 对齐项①合同语义落在 description（渐进披露的用途行——测试钉死）。
    semantic_desc = next(d for d in descriptors if d.name == SEMANTIC_QUERY).description
    assert "术语卡" in semantic_desc
    assert "metric_by_name" in semantic_desc
    assert "双落并列" in semantic_desc
    # registry 拒绝注册 readonly!=True 的工具（行为约定 1）。
    rogue = Tool(
        descriptor=ToolDescriptor(
            name="rogue", description="写工具", args_schema={}, readonly=False
        ),
        handler=_noop,
    )
    try:
        registry.register(rogue)
    except ValueError as exc:
        assert "readonly" in str(exc)
    else:
        raise AssertionError("readonly!=True 的工具未被 registry 拒绝")
    # 重名拒绝（注册表确定性）。
    try:
        registry.register(
            Tool(
                descriptor=ToolDescriptor(
                    name=SEMANTIC_QUERY, description="重名", args_schema={}
                ),
                handler=_noop,
            )
        )
    except ValueError:
        pass
    else:
        raise AssertionError("重名工具未被 registry 拒绝")
    # INV-2 工具层落点：registry 公开面零写出口（register 只进注册表，不触数据）。
    assert {n for n in vars(ToolRegistry) if not n.startswith("_")} == {
        "register",
        "descriptors",
        "call",
    }


async def _noop(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    return ToolResult.ok(())


# ---------- V2-97（D7）：图谱腿/compound 精排摘暴露面（注册面摘除、代码保留） ----------


async def test_graph_query_not_registered() -> None:
    """V2-97（D7）｜`graph_query` 从工具注册面摘除——模型不再白耗一次匹配/执行。

    闭世界断言：`descriptors()` 名单零 `graph_query`；registry.call 该名判
    「未知工具」bad_args（不是 schema 拒）；图谱引擎零调用（摘除＝路径不在）。
    """
    registry, _kb, _q, r = _registry()
    names = [descriptor.name for descriptor in registry.descriptors()]
    assert names == [
        SEMANTIC_QUERY,
        DATA_QUERY,
        DOC_RETRIEVE,
        FETCH_SECTION,
        FETCH_REPORT,
        SCHEMA_PROBE,
    ]
    assert GRAPH_QUERY not in names
    result = await registry.call(GRAPH_QUERY, {"question": "受效关系如何"}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None
    assert result.error.category == CATEGORY_BAD_ARGS
    assert "未知工具" in result.error.message
    assert result.observations == ()
    assert r.graph_calls == 0  # 注册面外——图谱面零触（模型不再白耗）


def test_graph_leg_code_kept() -> None:
    """V2-97（D7）｜图谱腿/compound 精排实现代码保留＋模块注携 `DEBT(V2-97)`。

    AST 存在性（不删代码）：`GraphSource` 协议在 `retrieval/source.py`；
    compound 精排编排件（`_llm_rerank`／`_batch_order`／`_doc_confidence`）与
    提示词常量在 `retrieval/engine.py`；`graph_query` handler 在 tools/handlers.py。
    DEBT 标记（去向＝接线决策票）在三个保留件的模块注里在案——摘除只摘暴露面。
    """
    root = Path(__file__).resolve().parents[2]
    source_path = root / "appv2" / "retrieval" / "source.py"
    engine_path = root / "appv2" / "retrieval" / "engine.py"
    handlers_path = root / "appv2" / "tools" / "handlers.py"

    source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, ast.ClassDef) and node.name == "GraphSource"
        for node in ast.walk(source_tree)
    ), "GraphSource 协议被删（V2-97 明令代码保留）"

    engine_tree = ast.parse(engine_path.read_text(encoding="utf-8"))
    functions = {
        node.name
        for node in ast.walk(engine_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {"_llm_rerank", "_batch_order", "_doc_confidence"} <= functions, (
        "compound 精排编排件被删（V2-97 明令代码保留）"
    )
    assigned = {
        target.id
        for node in ast.walk(engine_tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert {"BATCH_RERANK_SYSTEM_PROMPT", "DOC_CONF_SYSTEM_PROMPT"} <= assigned, (
        "精排提示词常量被删（V2-97 明令代码保留）"
    )

    handlers_tree = ast.parse(handlers_path.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "graph_query"
        for node in ast.walk(handlers_tree)
    ), "graph_query handler 被删（V2-97 明令代码保留）"

    # 模块注 DEBT 标记在案（标签形态可被 tools/debt_markers.py 的 DEBT_TAG 解析）。
    for path in (source_path, engine_path, handlers_path):
        assert "DEBT(V2-97)" in path.read_text(encoding="utf-8"), (
            f"{path.name} 缺 DEBT(V2-97) 标记（去向＝接线决策票）"
        )


# ---------- 验收②：schema 拒＝引擎零调用（bad_args 不触引擎） ----------


async def test_bad_args_notouch_engine() -> None:
    registry, kb, q, r = _registry()
    cases: list[tuple[str, dict[str, Any]]] = [
        ("不存在的工具", {"whatever": 1}),
        (SEMANTIC_QUERY, {}),  # 既无 question 也无 element_name
        (SEMANTIC_QUERY, {"question": "x", "element_name": "y"}),  # 二参互斥——同给即拒
        (SEMANTIC_QUERY, {"question": "x", "越参": 1}),  # additionalProperties 拒
        (DATA_QUERY, {"plan_draft": {"ranking": True}}),  # 缺 metric_slot
        (DATA_QUERY, {"/缺外层": _VALID_DRAFT}),  # 缺 plan_draft 键
        (
            DATA_QUERY,
            {
                "plan_draft": {
                    "metric_slot": "日产油量",
                    "ranking": True,
                    "window_start": "2026-13-01",  # 非法 ISO 日期——装配层拒
                    "window_end": "2026-12-31",
                }
            },
        ),
        (DOC_RETRIEVE, {"anchors": ["W-09"]}),  # 缺 question
        (DOC_RETRIEVE, {"question": "x", "family_hints": ["nope"]}),  # 族越界（enum 拒）
        # V2-97：graph_query 已摘除注册面——不在本表（工具不在册＝未知工具，
        # 判据归 test_graph_query_not_registered）。
    ]
    for name, args in cases:
        result = await registry.call(name, args, CTX)
        assert result.status == STATUS_FAILED, (name, result)
        assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
        assert result.observations == ()  # 拒时不携带任何观察素材
    # 引擎零调用：三缝调用计数全零（schema/装配层拒——不触引擎）。
    assert (kb.evidence_calls, kb.metric_calls) == (0, 0)
    assert (q.validate_calls, q.run_calls) == (0, 0)
    assert (r.retrieve_calls, r.graph_calls) == (0, 0)
    # data_query 草案合法但 validate 不过（指标不在台账）→failed(bad_args, 校验理由)，
    # run 零调用（validate 是合同内的前置面——「内部先调 query.validate」）。
    q.ledger_metric_slots = {"日产液量"}  # 假台账面：日产油量不在册
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    assert "不在指标台账" in (result.error.message or "")
    assert q.validate_calls == 1 and q.run_calls == 0
    # FX-13 指标替换封堵经 ctx.metric_candidates 转发：候选集外→bad_args，run 零调用。
    q.ledger_metric_slots = {"日产油量", "油压"}  # 两指标都在册——拒因只来自候选集
    ctx_fx = ToolContext(actor="dev-u1", budget=4, metric_candidates=("日产油量",))
    result = await registry.call(
        DATA_QUERY,
        {"plan_draft": {"metric_slot": "油压", "ranking": False}},
        ctx_fx,
    )
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    assert "候选集" in (result.error.message or "")
    assert q.validate_calls == 2 and q.run_calls == 0


# ---------- 验收③：错误三分类（超时→retryable；4xx→bad_args；闸拒→refused） ----------


async def test_error_taxonomy() -> None:
    registry, _kb, q, _r = _registry()
    # 超时→retryable（asyncio.TimeoutError 在 3.12 即 TimeoutError——含异步超时）。
    q.run_error = TimeoutError("上游查询超时")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_RETRYABLE
    assert result.error.hint is not None and "重试" in result.error.hint
    # 上游 4xx 类→bad_args（请求侧错误——修参重试）。
    q.run_error = FakeUpstreamRejection(422, "上游参数拒绝")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    assert "422" in (result.error.message or "")
    # 上游 5xx 类→retryable（上游抖动——不归参数错）。
    q.run_error = FakeUpstreamRejection(503, "上游暂不可用")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_RETRYABLE
    # 真实网关异常族（V2-18/C6 补支：Upstream 族不带 status_code 属性——duck 型
    # 判不到，按网关切换判据类型面投影三分类，防接线变化后三分类失真）。
    # UpstreamRejected（4xx/429 业务性拒绝）→bad_args（上游 4xx 类语义）。
    q.run_error = UpstreamRejected("petro-main", "上游拒绝 422: BadRequestError")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    assert "上游拒绝" in (result.error.message or "")
    # UpstreamUnavailable（网络错/超时/5xx）→retryable（上游抖动语义）。
    q.run_error = UpstreamUnavailable("petro-main", "网络错/超时: APIConnectionError")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_RETRYABLE
    assert "重试" in (result.error.hint or "")
    # 越权→refused（不重试）。
    q.run_error = PermissionError("无权口径")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_REFUSED
    # 闸拒（query refuse 联合态）→refused，message＝拒因原样。
    q.run_error = None
    q.outcome = QueryOutcome.refuse(reason="查无数据——如实回报，不编数。")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_REFUSED
    assert result.error.message == "查无数据——如实回报，不编数。"
    assert q.run_calls == 7  # 七枪全走到 run（validate 过闸后执行）
    q.outcome = None


# ---------- V2-22 钉测：429 限流→retryable（与网关层重试分层不冲突） ----------


async def test_429_rate_limit_retryable() -> None:
    """V2-22 钉测（P-012 疑点 1 裁决）：429 限流系临时性——loop 同参重试有意义。

    双面同判：duck 型面认 status_code 属性（真实 HTTP 形与 FakeUpstreamRejection
    桩同判）、类型面认网关 UpstreamRejected（B6 出口不带 status_code——reason
    由 llm_client 单源格式化「上游拒绝 {status}:」前缀识别）；429 单列→
    retryable，非 429 的 4xx 语义不变（bad_args——请求侧错误修参重试）。分层
    注记：工具层同参重试与网关层重试/切备是两层语义，互不冲突（hint 钉死）。
    """
    registry, _kb, q, _r = _registry()
    # duck 型面：status_code=429→retryable，hint 携分层注记（网关层重试不冲突）。
    q.run_error = FakeUpstreamRejection(429, "上游限流")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_RETRYABLE
    assert "429" in (result.error.message or "")
    assert "网关" in (result.error.hint or "")
    assert "重试" in (result.error.hint or "")
    # 类型面：UpstreamRejected 内的 429 限流（reason 前缀「上游拒绝 429:」）→retryable。
    q.run_error = UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_RETRYABLE
    assert "429" in (result.error.message or "")
    assert "网关" in (result.error.hint or "")
    # 非 429 的 4xx 语义不变（两型同验——请求侧错误仍 bad_args 修参重试）。
    q.run_error = UpstreamRejected("petro-main", "上游拒绝 422: BadRequestError")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    q.run_error = FakeUpstreamRejection(422, "上游参数拒绝")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    # 无状态形 UpstreamRejected（形状错族——reason 不带状态前缀）不误判 429。
    q.run_error = UpstreamRejected("petro-main", "vectors 形状不可解析")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.error is not None and result.error.category == CATEGORY_BAD_ARGS
    q.run_error = None


# ---------- 验收④：query 六联合态→ToolResult 逐态映射（含 AskFrame 形态） ----------


def _rows_outcome(*, rebind_notice: str | None = None) -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
        rebind_notice=rebind_notice,
    )


async def test_query_outcome_mapping() -> None:
    registry, _kb, q, _r = _registry()

    # —— rows+lineage → ok＋observations(权威表 scope=agg＋血缘卡) ——
    q.outcome = _rows_outcome()
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_OK and result.error is None and result.ask is None
    row_obs = _by_kind(result, "agg_row")
    assert len(row_obs) == 1
    assert row_obs[0].scope == "agg"  # specs/tools.md 行为约定 4：权威表 scope=agg
    assert row_obs[0].source_id == "N-01"
    assert "agg.fct_daily_metering" in row_obs[0].source
    assert row_obs[0].locator["table"] == "agg.fct_daily_metering"  # 表名机读
    assert "21.16" in row_obs[0].content
    lineage_obs = _by_kind(result, "lineage")
    assert len(lineage_obs) == 1
    assert LINEAGE_KEY_CALIBER in lineage_obs[0].content
    assert LINEAGE_KEY_WATERMARK in lineage_obs[0].content

    # —— rows＋改绑注记 → notice 素材随行 ——
    q.outcome = _rows_outcome(rebind_notice="已按最近可用日改绑出数（不冒充新数据）")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    rebind = _by_kind(result, "notice")
    assert len(rebind) == 1 and rebind[0].locator["notice_type"] == "rebind"
    assert "改绑" in rebind[0].content

    # —— freshness_block → ok＋闸依据观察（水位/窗标签/默认窗标注如实携带，零数值） ——
    q.outcome = QueryOutcome.freshness_block(
        watermark_date=WATERMARK,
        window_label="本月至今",
        is_default=False,
        message="新鲜度闸拦停：汇总层数据水位＝2026-08-31……",
    )
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_OK
    notices = _by_kind(result, "notice")
    assert len(notices) == 1 and notices[0].locator["notice_type"] == "freshness_block"
    assert notices[0].locator["watermark_date"] == "2026-08-31"
    assert notices[0].locator["window_label"] == "本月至今"
    assert notices[0].content == "新鲜度闸拦停：汇总层数据水位＝2026-08-31……"
    assert _by_kind(result, "agg_row") == []  # 零数值行

    # —— unbound_degrade → ok＋闸依据 Evidence 观察＋notice（依据原文） ——
    q.outcome = QueryOutcome.unbound_degrade(
        evidence=_evidence("203", "metric", source="sem_metric#203"),
        basis="指标「含水率」在册但未绑定汇总层（agg）计量列——零数值。",
    )
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_OK
    cards = _by_kind(result, "metric")
    assert len(cards) == 1 and cards[0].source_id == "203"
    assert cards[0].locator["binding_state"] == "unbound"
    notices = _by_kind(result, "notice")
    assert len(notices) == 1 and notices[0].locator["notice_type"] == "unbound_degrade"
    assert notices[0].content == "指标「含水率」在册但未绑定汇总层（agg）计量列——零数值。"

    # —— need_clarify → status=ask＋AskFrame(kind=clarify) ——
    q.outcome = QueryOutcome.need_clarify(
        question="「最近」指哪个时间窗？① 近 3 天 ② 近 30 天 ③ 本月至今——选好后我按审定口径取数。",
        choices=("近 3 天", "近 30 天", "本月至今"),
    )
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_ASK and result.error is None
    assert result.ask is not None and result.ask.kind == ASK_CLARIFY
    assert result.ask.prompt.startswith("「最近」指哪个时间窗")
    assert result.ask.options == ("近 3 天", "近 30 天", "本月至今")

    # —— external_table_approval → status=ask＋AskFrame(kind=external_table_approval) ——
    q.outcome = QueryOutcome.external_table_approval(
        tables=("erp_well_register",),
        ask={
            "approval_id": "APP-1008-erp_well_register",
            "scene": "extable",
            "title": "外表引用审批",
            "reason": (
                "查询引用选表命中集之外的外表：erp_well_register"
                "（执行前表引用比对命中——F14）"
            ),
            "impact": (
                "批准＝链恢复续跑（只读执行，生产库未动）；"
                "驳回＝权限拒答零重试（不自动改写 SQL）"
            ),
            "audit_hint": "外表 erp_well_register",
        },
    )
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_ASK
    frame = result.ask
    assert frame is not None and frame.kind == ASK_EXTERNAL_TABLE_APPROVAL
    assert "erp_well_register" in frame.prompt
    assert frame.options == ("批准", "驳回")
    assert frame.detail is not None  # 审批卡素材随帧（approval_id 供 resume 留痕）
    assert frame.detail["approval_id"] == "APP-1008-erp_well_register"

    # —— refuse → failed(refused) ——
    q.outcome = QueryOutcome.refuse(reason="指标不在指标台账——不在目录不代答")
    result = await registry.call(DATA_QUERY, {"plan_draft": _VALID_DRAFT}, CTX)
    assert result.status == STATUS_FAILED
    assert result.error is not None and result.error.category == CATEGORY_REFUSED
    q.outcome = None


# ---------- 验收⑤：Observation 来源链完整（台账行/表名机读/fragment→report→library） ----------

_LIB = ("lib-comp-a", "渤中34-5完井工程库", "completion")
_RPT_A = ("rpt-a", "A-W11井完井工程报告")
_LIB_M = ("lib-monthly-b", "渤中34-5躺井月报库", "monthly")
_RPT_M = ("rpt-m", "B-渤中34-5油田躺井治理与检泵作业月报-202608")


def _frag(fid: str, lib: tuple[str, str, str], rpt: tuple[str, str], text: str) -> FragmentRecord:
    return FragmentRecord(
        fragment_id=fid,
        report_id=rpt[0],
        report=rpt[1],
        section="第四章 4.2 防砂方式与参数",
        library_id=lib[0],
        library=lib[1],
        family=lib[2],
        text=text,
    )


async def _provenance_library() -> InMemoryFragmentLibrary:
    """三支真报告片段（逐字摘自 V2-04 同源 fixture——出处链逐字可核）。"""
    seeds = [
        _frag(
            "f-a1",
            _LIB,
            _RPT_A,
            "防砂方式：精密冲缝筛管适度防砂（不砾石充填）。筛管类型：精密冲缝筛管"
            "（Star-PS 型）；防砂精度：150 微米（0.15 毫米）。",
        ),
        _frag(
            "f-m2",
            _LIB_M,
            _RPT_M,
            "本月渤中 34-5 油田平均开井数 156 口，当月发生躺井 7 井次，躺井率 4.5%，"
            "抽油机时率 94.2%。",
        ),
    ]
    embedder = LocalHashEmbedder()
    vectors = await embedder.embed([seed.text for seed in seeds])
    frags = [
        dataclasses.replace(seed, embedding=vector)
        for seed, vector in zip(seeds, vectors, strict=True)
    ]
    return InMemoryFragmentLibrary(frags)


async def _real_registry() -> ToolRegistry:
    """真引擎装配（knowledge/query/retrieval 全真缝——来源链端到端核验）。"""
    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    query = QueryEngine(
        knowledge=knowledge,
        executor=CsvSnapshotExecutor(),
        waterline=lambda: WatermarkFace(
            data_date=WATERMARK, promise="T-1", tag="落后 38 天（超期）"
        ),
        today=lambda: TODAY,
    )
    retrieval = RetrievalEngine(
        library=await _provenance_library(), embedder=LocalHashEmbedder()
    )
    return ToolRegistry(knowledge=knowledge, query=query, retrieval=retrieval)


async def test_observation_provenance() -> None:
    registry = await _real_registry()
    # —— 权威表行：来源链＝表名＋行键机读（locator.table/well_id/prod_date） ——
    result = await registry.call(
        DATA_QUERY,
        {
            "plan_draft": {
                "metric_slot": "日产油量",
                "ranking": False,
                "window_start": "2025-09-01",
                "window_end": "2025-09-03",
                "limit": 5,
            }
        },
        CTX,
    )
    assert result.status == STATUS_OK
    row_obs = _by_kind(result, "agg_row")
    assert len(row_obs) == 5  # 两日窗 172 行——LIMIT 5 收口
    assert row_obs[0].source_id == "N-01@2025-09-01"  # 行键＝井@日（明细行机读身份）
    assert "21.16" in row_obs[0].content  # 首行 N-01 21.16 吨（V2-03 钉值）
    for obs in row_obs:
        assert obs.scope == "agg"
        assert obs.source and obs.source_id  # 来源链（表名）与行键逐支在场
        assert obs.locator["table"] == "agg.fct_daily_metering"
        assert obs.locator["well_id"]
        assert obs.locator["prod_date"].count("-") == 2  # 机读日期（ISO 形）
        assert obs.version is None and obs.freshness == ""  # 行级无版本/时效承载——零发明
    # 血缘卡观察：五要素＋权限注入行齐（ctx.actor 注入——身份只从 ctx 进）。
    lineage_obs = _by_kind(result, "lineage")
    assert len(lineage_obs) == 1
    for key in (
        LINEAGE_KEY_CALIBER,
        LINEAGE_KEY_SOURCE,
        LINEAGE_KEY_FILTER,
        LINEAGE_KEY_PERMISSION,
        LINEAGE_KEY_WATERMARK,
        LINEAGE_KEY_CLOSING,
    ):
        assert key in lineage_obs[0].content
    assert "dev-u1" in lineage_obs[0].content
    # 结构化载荷（2026-10-17 EB2 D1）：五要素按合同键随观察走＋限量面触顶事实
    # （本发射 plan.limit＝5、交付 5 行＝触顶）。
    payload = lineage_obs[0].locator[LOCATOR_PAYLOAD_KEY]
    assert set(payload[LINEAGE_PAYLOAD_KEY]) == {
        LINEAGE_KEY_CALIBER,
        LINEAGE_KEY_SOURCE,
        LINEAGE_KEY_FILTER,
        LINEAGE_KEY_PERMISSION,
        LINEAGE_KEY_WATERMARK,
        LINEAGE_KEY_CLOSING,
    }
    assert payload[LINEAGE_LIMIT_KEY] == {
        LINEAGE_LIMIT_HIT_KEY: True,
        LINEAGE_LIMIT_ROWS_KEY: 5,
    }

    # —— 台账行：来源链＝sem_*#行 id＋element_id 机读 ——
    semantic = await registry.call(SEMANTIC_QUERY, {"element_name": "日产油量"}, CTX)
    assert semantic.status == STATUS_OK
    card = _by_kind(semantic, "metric")
    assert len(card) == 1
    assert card[0].source == "sem_metric#201"
    assert card[0].source_id == "201"
    assert card[0].locator["element_id"] == "201"
    assert card[0].locator["binding_state"] == "bound"

    # —— 检索观察：fragment→report→library 三级链逐支完整＋window_note 截断声明 ——
    doc = await registry.call(
        DOC_RETRIEVE, {"question": "完井防砂方式与防砂精度", "family_hints": ["completion"]}, CTX
    )
    assert doc.status == STATUS_OK
    frag_obs = [o for o in doc.observations if o.locator.get("kind") == "fragment"]
    assert frag_obs, "检索观察为空——来源链断"
    for obs in frag_obs:
        assert obs.source_id  # fragment 级
        assert obs.source  # report 级
        assert obs.locator["library"]  # library 级
        assert obs.locator["fragment_id"] == obs.source_id
        assert obs.locator["report"] == obs.source
        assert obs.locator["section"]
        assert obs.scope in FAMILY_ALL  # family 标注（库 biz_template 透传）
    notes = _by_kind(doc, "notice")
    assert len(notes) == 1 and "共检索到" in notes[0].content and "用进了答案" in notes[0].content


# ---------- 对齐项①：跨 kind 歧义名＝术语卡优先＋可出数指标补取，双落并列 ----------


async def test_semantic_dual_landing() -> None:
    knowledge = InMemoryKnowledgeStore(question_array_snapshot(), today=TODAY)
    registry, _kb, _q, _r = _registry(knowledge=knowledge)
    # 「日产液」：既是届满术语（sem_term#11）又是可出数指标的别名落点（日产液量 #202）。
    result = await registry.call(SEMANTIC_QUERY, {"element_name": "日产液"}, CTX)
    assert result.status == STATUS_OK
    assert len(result.observations) == 2  # 双落并列
    term_card, metric_card = result.observations[0], result.observations[1]
    # 术语卡优先在前（词条卡一等材料语义——evidence() 顺序原样）。
    assert term_card.source_id == "11"
    assert term_card.source.startswith("sem_term#")
    assert term_card.locator["kind"] == "term"
    assert term_card.locator["binding_state"] == "expired"
    assert "已届满" in term_card.freshness
    # metric_by_name 补取可出数指标在后（别名归一日产液→日产液量——bound 可出数）。
    assert metric_card.source_id == "202"
    assert metric_card.source.startswith("sem_metric#")
    assert "经别名归一（日产液→日产液量）" in metric_card.source
    assert metric_card.locator["binding_state"] == "bound"
    assert metric_card.locator["kind"] == "metric"
    # 去重：纯指标名只落一张卡（evidence 与 metric_by_name 同落点不重复）。
    single = await registry.call(SEMANTIC_QUERY, {"element_name": "日产油量"}, CTX)
    assert len(single.observations) == 1
    assert single.observations[0].source_id == "201"
    # 未命中如实：notice 观察（零编造）。
    miss = await registry.call(SEMANTIC_QUERY, {"question": "不存在的要素xyz"}, CTX)
    assert miss.status == STATUS_OK
    assert len(miss.observations) == 1
    assert miss.observations[0].locator.get("notice_type") == "no_hit"


# ---------- 对齐项②：anchors 参数契约与 P-003 实现一致（含图谱侧端到端） ----------


async def test_anchors_contract() -> None:
    # （a）doc_retrieve：anchors/family_hints/ctx.budget 逐字进 RetrievalNeed
    #     （P-003 已定实现＝并入关键词腿检索单元＋编号保送——工具层只做契约转发）。
    registry, _kb, _q, fake_ret = _registry()
    await registry.call(
        DOC_RETRIEVE,
        {"question": "完井防砂", "anchors": ["W-09"], "family_hints": ["completion"]},
        ToolContext(actor="dev-u1", budget=7),
    )
    need = fake_ret.needs[-1]
    assert need.anchors == ("W-09",)
    assert need.family_hints == ("completion",)
    assert need.budget == 7  # 送窗预算从 ctx 进（不从 args——调度策略归调用方）
    # graph_query 同契约（V2-97 后不在注册面——直调保留 handler 钉契约）：
    # anchors 逐字进 RetrievalNeed.anchors。
    await graph_query_handler(
        {"question": "转注受效", "anchors": ["Y-16"]}, CTX, retrieval=fake_ret
    )
    assert fake_ret.needs[-1].anchors == ("Y-16",)
    assert fake_ret.graph_calls == 1

    # （b）真引擎端到端：图谱面锚定消费＝锚名并入实体匹配问针——锚名只在 anchors
    #     提名时边可达（V1 S1 锚定语义的图谱侧投影）。
    anchor_frag = _frag("f-y4", _LIB, _RPT_A, "注水井 Y-16 井计划 2026 年 12 月转注。")
    library = InMemoryFragmentLibrary(
        [anchor_frag],
        edges=[
            GraphEdgeRecord(
                entity_from="Y-16",
                rel="转注受效",
                entity_to="Y-21",
                evidence="注水井 Y-16 井计划 2026 年 12 月转注，预计 Y-21 井受效",
                chunk_id="f-y4",
                report_id=_RPT_A[0],
                report=_RPT_A[1],
                library_id=_LIB[0],
                library=_LIB[1],
                family=_LIB[2],
            )
        ],
    )
    real_engine = RetrievalEngine(
        library=library, embedder=LocalHashEmbedder(), graph=library
    )  # 内存库双面一对象（V2-04 同款——片段语料＋图谱源）
    without = await graph_query_handler(
        {"question": "受效关系如何"}, CTX, retrieval=real_engine
    )
    assert _by_kind(without, "graph") == []  # 问针无实体名——零边
    with_anchor = await graph_query_handler(
        {"question": "受效关系如何", "anchors": ["Y-16"]}, CTX, retrieval=real_engine
    )
    edges = _by_kind(with_anchor, "graph")
    assert len(edges) == 1  # 锚名进问针——边可达
    assert edges[0].source_id == "f-y4"
    assert edges[0].source == "A-W11井完井工程报告"
    assert edges[0].locator["library"] == "渤中34-5完井工程库"
