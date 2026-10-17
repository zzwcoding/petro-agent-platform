"""V2-52 五站缺口迁移批——辅助模式返工钉测（P-051b，TDD 红先绿后）。

返工基准＝tickets/v2/V2-52-五站缺口迁移批.md v2 票面（Owner 辅助模式拍板）＋
P-051 中途审查四件裁决（等效补齐×2/追认×2）：

- 快车道拆除钉：fast_lane_verdict 判定面（understand 入口确定性直出＋定义形
  词条卡直出）整体移除（非注记留死）；仅服务它的 LedgerFacts terms 投影随拆；
  词条卡语义由「开局台账注入＋semantic_query」承载；
- faq_lookup 辅助钉（附 B）：归一 NFKC＋剥全部标点（审查①等效补齐）/相似问
  优先/THRESHOLD 阈值/禁用条目剔除；进 discover 闭世界，命中条目作辅助材料
  （locator.kind=faq_aux）进上下文观察流——模型 finalize 直答（零 doc_retrieve
  秒答形）或 decompose 继续，二者皆合法；未命中＝机读 note 如实不阻断；
- 辅助不触发闸钉：faq 材料在窗时 precondition 各闸零新增触发（纯增料）；
- N1 钉（附 C——唯一代码前置例外）：禁问→零执行＋audit 行（agent_v2.refused）
  在场；豁免词面 V1 等效补齐（审查②——元问五词同句共现＋引号全内含）＋豁免
  必留 audit 行（agent_v2.ban_exempt）；快车道拆除后普通问零误伤零新增延迟；
- 越集续跑钉：批准→续跑出数（P-051 已绿，随合并保留——接口不变）；
- 审查清偿钉：过时注记改型（S3——schema/precondition A2 裁决措辞随实现同步）
  ＋真引擎放行态闸函数级直钉（S4——落 test_v2_query.py）。

判定面全部纯固定代码零 LLM；运行面 N1 挂 understand 入口（先于一切解析——
V1 W-F19 0 号位语义的 ReAct 形承载）；faq_lookup 执行件在 tools 层（注册制，
world 接触只经 ToolRegistry.call 受控行动链）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from appv2.infra.db import ConnectionManager, DatabaseSpec
from appv2.infra.security.store import AuditLog
from appv2.knowledge import PgFaqStore, normalize_faq_question
from appv2.query import QueryOutcome
from appv2.runtime import AskChoice, AskRequest, RunStore
from appv2.runtime.guide import CLARIFY_CONTRACT
from appv2.runtime.subtask import parse_question_group
from appv2.tools import (
    FAQ_AUX_THRESHOLD,
    FAQ_LOOKUP,
    ToolRegistry,
    ledger_facts,
)
from appv2.tools.handlers import faq_lookup as faq_lookup_handler
from appv2.tools.precondition import is_ban_exempt
from appv2.tools.schema import ToolContext
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import LEDGER_DUMP
from tests.domains.test_v2_react_loop import (
    _fragment_obs,
    _retrieval_with,
    _rows_outcome,
)

TODAY = date(2026, 10, 8)

# ---------- 词典层底座：系统级台账行（行值誊自 PG sem_term 种子，零业务发明） ----------

_SYS_TERMS: list[dict[str, Any]] = [
    {
        "term": "老完成率", "banned": True, "freshness": "—（已禁用）",
        "value": "老完成率（禁用词 · 禁用（替代：产量完成率））："
                 "v1 口径（不含自用油折算），2024 年废弃",
        "source_id": "1",
    },
    {
        "term": "躺井", "banned": False, "freshness": "2026-12-31",
        "value": "躺井（黑话 → 停产待检泵 · 有效（限作业区语境））：作业区口语",
        "source_id": "4",
    },
    {
        "term": "日产液", "banned": False, "freshness": "2026-06-30（已届满）",
        "value": "日产液（别名 → 日产液量 · 有效（已届满））：作业区口语缩写",
        "source_id": "11",
    },
    {
        "term": "递减增油", "banned": False, "freshness": "2027-03-31",
        "value": "递减增油（术语 · 有效（待联席裁决））：见指标 10（含口径争议注记）",
        "source_id": "7",
    },
]


def _sys_dump() -> dict[str, Any]:
    """问数组台账 dump＋系统级术语行（N1 闸判定输入——行值零发明）。"""
    dump = json.loads(json.dumps(LEDGER_DUMP, ensure_ascii=False))
    dump["terms"] = [dict(row) for row in _SYS_TERMS]
    return dump


# ---------- 剧本 FAQ 读面（生产＝PgFaqStore.similar——测试按同形回罐头） ----------


class _FaqFace:
    """FaqLookupFace 剧本件（similar 同形——hits 罐头出列）。"""

    def __init__(self, hits: Sequence[Any] = ()) -> None:
        self._hits = list(hits)
        self.calls: list[tuple[str, int]] = []

    def similar(self, question: str, top: int = 3) -> list[Any]:
        self.calls.append((question, top))
        return list(self._hits)


def _faq_hit(
    entry_id: str, question: str, answer: str, *, score: float = 1.0,
    disabled: bool = False,
) -> Any:
    """FaqAuxHit 形罐头（duck——生产为冻结 dataclass）。"""

    class _Hit:
        pass

    hit = _Hit()
    hit.entry_id = entry_id
    hit.question = question
    hit.answer = answer
    hit.matched = question
    hit.score = score
    hit.disabled = disabled
    return hit


# ---------- 单测：N1 豁免词面（V1 DE-03 等效补齐——审查②） ----------


def test_ban_exempt_meta_question_forms() -> None:
    """元问形：五词（旧称/以前叫/现在叫/还叫/原名）与命中词同句共现＝豁免。"""
    assert is_ban_exempt("老完成率现在叫什么", "老完成率")
    assert is_ban_exempt("以前叫老完成率的指标现在叫什么", "老完成率")
    assert is_ban_exempt("老完成率还叫这个名吗", "老完成率")
    assert is_ban_exempt("老完成率的原名是什么", "老完成率")
    assert is_ban_exempt("顺便问下老完成率的原名是什么", "老完成率")


def test_ban_exempt_quote_forms() -> None:
    """引用形：命中词每次出现都在引号对内＝豁免（四形引号闭世界）。"""
    assert is_ban_exempt("「老完成率」是什么口径？", "老完成率")
    assert is_ban_exempt("按「老完成率」口径给我出数", "老完成率")
    assert is_ban_exempt("按“老完成率”口径给我出数", "老完成率")
    assert is_ban_exempt("问一下'老完成率'的现状", "老完成率")


def test_ban_exempt_not_exempt_forms() -> None:
    """不豁免形：裸写/一次裸写即不豁免/跨句拼接不放行（V1 FX-03/R1-07 等效）。"""
    assert not is_ban_exempt("老完成率是多少？", "老完成率")
    # 定义形裸写（什么是老完成率？——无元问词/非全引号）＝不豁免（V1 同拦）。
    assert not is_ban_exempt("什么是老完成率？", "老完成率")
    assert not is_ban_exempt("按老完成率口径给我出数", "老完成率")
    # 一次裸写即不豁免（窄豁免不放松）。
    assert not is_ban_exempt("老完成率怎么算？是「老完成率」这个吧", "老完成率")
    # 跨句拼接形不放行（同句以分句符判定）。
    assert not is_ban_exempt("老完成率是多少？顺便问下这词原名是啥", "老完成率")
    assert not is_ban_exempt("老完成率怎么算；这词的旧称是啥", "老完成率")


# ---------- 单测：faq 归一（NFKC＋剥全部标点——审查①等效补齐） ----------


def test_normalize_faq_question_v1_equivalent() -> None:
    """归一升全：NFKC 全半角折叠＋casefold＋剥全部标点/空白（V1 normalize_text
    等效——全角「Ｎ－０２」与半角「N-02」、带标点与剥标点同判）。"""
    assert (
        normalize_faq_question("Ｎ－０２ 井，是什么时候投产的？")
        == normalize_faq_question("N-02井是什么时候投产的")
    )
    assert normalize_faq_question("Ｎ－０２ 井，是什么时候投产的？") == (
        "n02井是什么时候投产的"
    )
    # 归一单点保留：空串入空串出（未命中面照旧）。
    assert normalize_faq_question("？？？") == ""


# ---------- 单测：PgFaqStore.similar（相似问优先/禁用剔除/top 上限） ----------

_FAQ_DDL = (
    """CREATE TABLE faq_entry (
        id VARCHAR(32) PRIMARY KEY, question TEXT NOT NULL,
        answer TEXT NOT NULL, status VARCHAR(16) NOT NULL)""",
    """CREATE TABLE faq_similar_question (
        id INTEGER PRIMARY KEY, entry_id VARCHAR(32) NOT NULL, text TEXT NOT NULL)""",
)

_FAQ_SEED = [
    # faq-3：标准问与相似问都能命中「躺井啥意思」形——相似问优先序的比对面。
    (
        "faq-3", "「躺井」是什么意思？",
        "停产待检泵，作业区口语（限作业区语境；Owner：采油工艺所）", "serve",
    ),
    ("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。", "serve"),
    # faq-7：标准问归一后同形命中（另一条目——相似问优先序的第二比对面）。
    ("faq-7", "躺井啥意思", "faq-7 标准问直配。", "serve"),
    ("faq-8", "「老完成率」是什么口径？", "已禁用——现行口径为产量完成率。", "disabled"),
    # faq-9：负例条目（`status='negative'`／`is_negative`）——与 disabled 同族剔除，
    # 「不该答的问题」永不参与命中（pin-21 禁用词剔除的负例面，2026-10-17 EB5b）。
    ("faq-9", "帮我预测明年油价", "（负例：不回答。库里登记为「不该答的问题」）", "negative"),
]


async def _faq_db(tmp_path: Path) -> ConnectionManager:
    spec = DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "faq.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )
    db = ConnectionManager([spec])
    async with db.session() as session:
        for ddl in _FAQ_DDL:
            await session.execute(text(ddl))
        for entry_id, question, answer, status in _FAQ_SEED:
            await session.execute(
                text("INSERT INTO faq_entry (id, question, answer, status)"
                     " VALUES (:id, :q, :a, :s)"),
                {"id": entry_id, "q": question, "a": answer, "s": status},
            )
        await session.execute(
            text("INSERT INTO faq_similar_question (id, entry_id, text)"
                 " VALUES (1, 'faq-3', '躺井啥意思')"),
        )
    return db


def _spec_of(tmp_path: Path) -> DatabaseSpec:
    return DatabaseSpec(
        name="primary", role="primary", driver="sqlite", host="", port=0,
        database=str(tmp_path / "faq.db"), user="", password="",
        pool_size=2, max_overflow=1,
    )


async def test_pg_faq_similar_priority_and_serve_only(tmp_path: Path) -> None:
    """similar 读面：相似问先于标准问（V1 match_index 序——审查①）；disabled
    不进命中集；未命中空集如实；归一跨全半角/标点命中。"""
    db = await _faq_db(tmp_path)
    try:
        store = PgFaqStore.from_specs(_spec_of(tmp_path))
        # 相似问优先：faq-3 相似问与 faq-7 标准问归一同形——faq-3 在前。
        hits = store.similar("躺井啥意思？", top=3)
        assert [h.entry_id for h in hits] == ["faq-3", "faq-7"]
        assert hits[0].score >= FAQ_AUX_THRESHOLD and not hits[0].disabled
        # 标准问命中（NFKC＋剥标点等效——全角/标点变体同判）。
        hits = store.similar("Ｎ－０２井，是什么时候投产的？", top=3)
        assert [h.entry_id for h in hits] == ["faq-4"]
        assert hits[0].answer == "2019-06-15 投产。"
        # disabled 不消费；未命中空集。
        assert store.similar("「老完成率」是什么口径？", top=3) == []
        assert store.similar("随便问一句", top=3) == []
        # top 上限收口（命中面不超过 top）。
        assert len(store.similar("躺井啥意思？", top=1)) == 1
    finally:
        await db.dispose()


# ---------- 单测：faq_lookup 五站链四形（pin-21 专属钉：归一／相似问优先／剔除／直答） ----------


async def test_pin21_faq_five_station_chain_four_forms(tmp_path: Path) -> None:
    """pin-21（faq 五站链，`docs/runtime-refactor/eng/04a-应钉行为清单.md` 行 21）四形归口钉。

    行为在 tools 存量面（`FaqLookupFace`：`PgFaqStore.similar` ＋ `handlers.faq_lookup`），
    runtimev2 零落点是已裁定状态（eng/04a 归属注记）——本件把四形收在一处（既有两件为本面的
    明细钉：`::test_normalize_faq_question_v1_equivalent`＝①、`::test_pg_faq_similar_priority_and_serve_only`
    ＝①②③ 明细、`::test_station_faq_aux_finalize_direct`＝④ 端到端）：

    ① **NFKC 归一**（全半角／标点变体同判）；② **相似问优先**（相似问条目先于标准问）；
    ③ **禁用词剔除**（`disabled` 与 **负例** `negative` 两面都不入命中集）；④ **命中直答**：命中
    条目作辅助材料观察（`locator.kind=faq_aux`／`source_id=faq_entry:<id>`），答案面可据此直答
    ——`秒回零模型`形已随 P-051b 拆除、按 A-P4b-63「FAQ 命中直答或检索路径均可」判）。
    判据零 LLM 纯固定代码。
    """
    db = await _faq_db(tmp_path)
    try:
        store = PgFaqStore.from_specs(_spec_of(tmp_path))
        # ① NFKC 归一：全半角＋标点变体与标准问同判
        assert [h.entry_id for h in store.similar("Ｎ－０２井，是什么时候投产的？")] == ["faq-4"]
        # ② 相似问优先：相似问命中条目先于标准问命中条目
        assert [h.entry_id for h in store.similar("躺井啥意思？")] == ["faq-3", "faq-7"]
        # ③ 禁用词剔除：disabled（老完成率）与 negative（不该答的问题）两面皆不入命中集
        assert store.similar("「老完成率」是什么口径？") == []
        assert store.similar("帮我预测明年油价") == []
        # ④ 命中直答：命中条目作辅助材料观察（答案面可直答所问）
        face = _FaqFace(
            [_faq_hit("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。")]
        )
        result = await faq_lookup_handler(
            {"question": "N-02 井是什么时候投产的？"}, _ctx(), faq=face
        )
        assert result.status == "ok"
        (obs,) = result.observations
        assert obs.locator["kind"] == "faq_aux" and obs.source_id == "faq_entry:faq-4"
        assert "A：2019-06-15 投产。" in obs.content
    finally:
        await db.dispose()


# ---------- 单测：faq_lookup 执行件（附 B——辅助材料观察/机读 note/阈值剔除） ----------


def _ctx() -> ToolContext:
    return ToolContext()


async def test_faq_lookup_handler_aux_material() -> None:
    """命中→辅助材料观察：locator.kind=faq_aux、source_id=faq_entry:<id>、
    content=逐条「Q：标准问 / A：答案」。"""
    face = _FaqFace([
        _faq_hit("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。"),
    ])
    result = await faq_lookup_handler(
        {"question": "N-02 井是什么时候投产的？"}, _ctx(), faq=face
    )
    assert result.status == "ok" and result.ask is None and result.error is None
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.locator["kind"] == "faq_aux"
    assert obs.source_id == "faq_entry:faq-4"
    assert "Q：N-02 井是什么时候投产的？" in obs.content
    assert "A：2019-06-15 投产。" in obs.content


async def test_faq_lookup_handler_miss_note_and_filters() -> None:
    """未命中→机读 note「FAQ 库无命中」（no_hit 分型）；阈下/禁用条目不消费。"""
    face = _FaqFace([])
    result = await faq_lookup_handler({"question": "随便问"}, _ctx(), faq=face)
    assert result.status == "ok"
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.locator == {"kind": "notice", "notice_type": "no_hit"}
    assert "FAQ 库无命中" in obs.content
    # 阈下（score < FAUX_THRESHOLD）与 disabled 条目被剔除→同样如实 note。
    face = _FaqFace([
        _faq_hit("faq-9", "近名问", "阈下条目", score=0.5),
        _faq_hit("faq-8", "禁用条目", "disabled 条目", disabled=True),
    ])
    result = await faq_lookup_handler({"question": "近名问"}, _ctx(), faq=face)
    assert result.status == "ok"
    assert len(result.observations) == 1
    assert result.observations[0].locator.get("notice_type") == "no_hit"


async def test_faq_lookup_handler_args_and_registry() -> None:
    """缺 question＝bad_args（registry 统一调出口三分类封套）；registry 带
    faq 缝→faq_lookup 注册在册（发射闭世界生效），不带→不在册。"""
    from appv2.tools import (
        FakeKnowledgeStore,
        FakeQueryEngine,
        FakeRetrievalEngine,
    )

    registry = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
        faq=_FaqFace(),
    )
    result = await registry.call(FAQ_LOOKUP, {}, ToolContext())
    assert result.status == "failed" and result.error is not None
    assert result.error.category == "bad_args"
    # 注册面：带 faq→在册；缺省→不在册（既有五工具零漂移）。
    def _names(reg: ToolRegistry) -> list[str]:
        return [d.name for d in reg.descriptors()]

    assert FAQ_LOOKUP in _names(registry)
    without_faq = ToolRegistry(
        knowledge=FakeKnowledgeStore(),
        query=FakeQueryEngine(),
        retrieval=FakeRetrievalEngine(),
    )
    assert FAQ_LOOKUP not in _names(without_faq)


# ---------- 单测：合同目录指路（附 A char 相等）＋发射闭世界＋finalize 合法 ----------

# 附 A 逐字稿（V2-53 附 A 随动改型——tickets/v2/V2-53-零观察定稿治理.md 附 A
# char 相等，禁改一字）。
_APPENDIX_A = (
    "可用探查（discover，全 run ≤10 次，已用 {discover_used} 次）：\n"
    "- semantic_query：本体口径/绑定/届满细节钻取（开局台账已全量，仅细节用）\n"
    "- table_schema：表结构钻取（agg/sem/kb 分区）\n"
    "- faq_lookup：FAQ 现成问答库——问句有现成标准答案时加速/互证；\n"
    "  命中条目作观察材料进上下文——有探查观察在场方可 finalize，不够继续检索"
)


def test_clarify_contract_directory_verbatim() -> None:
    """目录钉：三工具词面指路在合同（char 相等）＋faq_lookup 在发射闭世界。"""
    assert _APPENDIX_A in CLARIFY_CONTRACT
    from appv2.runtime.graph import DISCOVER_TOOLS

    assert FAQ_LOOKUP in DISCOVER_TOOLS
    assert {"semantic_query", "table_schema", "faq_lookup"} <= DISCOVER_TOOLS


def test_clarify_finalize_emission_legal() -> None:
    """消费规则：clarify 相位 finalize 直答合法（解析闭世界收口）；faq_lookup
    discover 发射通过 schema 校验。"""
    emission = parse_question_group('{"action": "finalize"}')
    assert not isinstance(emission, str)
    assert emission.kind == "finalize"
    emission = parse_question_group(
        '{"action": "discover", "discovers": '
        '[{"tool": "faq_lookup", "args": {"question": "N-02 井什么时候投产的？"}}]}'
    )
    assert not isinstance(emission, str)
    assert emission.discovers[0]["tool"] == "faq_lookup"


# ---------- 单测：快车道拆除（代码移除——非注记留死） ----------


def test_fast_lane_dismantled() -> None:
    """拆除钉：fast_lane_verdict 判定面/词条卡直出件/terms 投影全 absent。"""
    import appv2.tools as tools_pkg
    from appv2.tools import precondition

    for name in (
        "fast_lane_verdict",
        "FastLaneClosure",
        "extract_definition_term",
        "FAST_LANE_BANNED",
        "FAST_LANE_TERM_CARD",
        "TermFact",
    ):
        assert not hasattr(tools_pkg, name), f"tools 公开面残留 {name}"
        assert not hasattr(precondition, name), f"precondition 残留 {name}"
    # LedgerFacts terms 投影随拆（dataclass 字段闭世界无 terms）。
    import dataclasses

    facts_fields = {f.name for f in dataclasses.fields(ledger_facts({}))}
    assert "terms" not in facts_fields
    # graph 快车道直出件移除。
    from appv2.runtime import graph

    assert not hasattr(graph, "_fast_lane_closure")
    assert not hasattr(graph, "_FAST_LANE_TITLES")


def test_annotations_follow_implementation() -> None:
    """审查③清偿钉（S3）：A2 裁决注记与实现同步——「不走引擎 approved_tables」
    反话措辞绝迹，放行态随执行进引擎的新措辞在场。"""
    import inspect

    from appv2.tools import precondition, schema

    schema_source = inspect.getsource(schema)
    precondition_source = inspect.getsource(precondition)
    for source in (schema_source, precondition_source):
        assert "不走引擎 approved_tables" not in source  # 反话措辞绝迹
        assert "随执行进引擎" in source  # 新措辞（放行态随 data_query 进引擎）在场
    # C1 顺手注记（state.extable_rounds——骨架上限 1 反话改型）。
    from appv2.runtime import state as state_mod

    state_source = inspect.getsource(state_mod)
    assert "骨架上限 1" not in state_source


# ---------- 端到端钉测①：faq 命中→辅助材料进上下文→finalize 直答（秒答形） ----------


async def test_station_faq_aux_finalize_direct(tmp_path: Path) -> None:
    """辅助语义钉：clarify 发射 faq_lookup→辅助材料进上下文→模型 finalize
    直答——零 doc_retrieve 秒答形（检索引擎零调用）。"""
    dump = _sys_dump()
    script = {
        "v2.runtime.understand": ["理解：问 N-02 井投产日期。\n指标候选：无"],
        "v2.runtime.decision": [
            json.dumps({
                "thought": "问句像 FAQ——先查现成问答库",
                "action": "discover",
                "discovers": [{
                    "tool": "faq_lookup",
                    "args": {"question": "N-02 井是什么时候投产的？"},
                }],
            }, ensure_ascii=False),
            '{"thought": "FAQ 命中足够", "action": "finalize"}',
        ],
        "v2.runtime.answer": ["N-02 井 2019-06-15 投产 [1]。"],
    }
    retrieval = _retrieval_with(_fragment_obs("干扰片段——不应被消费", "f-noise"))
    faq = _FaqFace([
        _faq_hit("faq-4", "N-02 井是什么时候投产的？", "2019-06-15 投产。"),
    ])
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        retrieval=retrieval, faq=faq,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="N-02 井是什么时候投产的？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "2019-06-15 投产" in (run.answer or "")
        # 零 doc_retrieve 秒答形（检索引擎零调用——辅助材料 finalize 直答）。
        assert retrieval.retrieve_calls == 0
        # 辅助材料在窗：答案引标 [1] 指向 faq 辅助观察（citation 同源）。
        citations = [e.data for e in events if e.event == "citation"]
        assert any(
            c.get("source_id") == "faq_entry:faq-4" for c in citations
        )
        # 模型参与判定（秒答形非零模型直出——sufficiency 由模型判）。
        assert completer.counts().get("v2.runtime.understand") == 1
        assert completer.counts().get("v2.runtime.decision") == 2
        assert completer.counts().get("v2.runtime.answer") == 1
        # faq 读缝消费在案（执行件经 registry 受控行动链）。
        assert faq.calls == [("N-02 井是什么时候投产的？", 3)]
    finally:
        await db.dispose()


# ---------- 端到端钉测②：faq 未命中→机读 note→继续检索零阻断 ----------


async def test_station_faq_miss_note_then_retrieve(tmp_path: Path) -> None:
    """未命中→「FAQ 库无命中」如实 note→模型 decompose 继续——knowledge 链
    doc_retrieve 照常执行（零阻断）。"""
    dump = _sys_dump()
    clarify = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "W-111 井投产初期日产油是多少",
             "ledger_notes": "日产油量｜bound｜无", "chain": "knowledge"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "W-111 井投产初期日产油是多少"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问 W-111 井初期日产油。\n指标候选：无"],
        "v2.runtime.decision": [
            json.dumps({
                "thought": "先查 FAQ",
                "action": "discover",
                "discovers": [{
                    "tool": "faq_lookup",
                    "args": {"question": "W-111 井投产初期日产油是多少"},
                }],
            }, ensure_ascii=False),
            clarify,
            toolmatch,
        ],
        "v2.runtime.answer": ["W-111 井投产初期日产油 291 方 [1]。"],
    }
    retrieval = _retrieval_with(
        _fragment_obs("W-111 井采用酸压完井，投产初期日产油 291 方。", "f-1")
    )
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        retrieval=retrieval, faq=_FaqFace(),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="W-111 井投产初期日产油是多少？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 未命中如实 note 在场（机读 no_hit 分型）。
        notices = [e.data for e in events if e.event == "notice"]
        assert any(
            n.get("type") == "no_hit" and "FAQ 库无命中" in str(n.get("content", ""))
            for n in notices
        )
        # 继续检索零阻断：doc_retrieve 真执行＋答案引报告材料。
        assert retrieval.retrieve_calls == 1
        assert "291" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- 端到端钉测③：faq 材料在窗时 precondition 各闸零新增触发 ----------


async def test_station_faq_material_triggers_no_gates(tmp_path: Path) -> None:
    """辅助不触发闸钉：faq 命中条目答案携禁用词＋未申报外表名——材料在窗，
    子问题过闸零新增触发（纯增料，不进任何闸的判面）。"""
    dump = _sys_dump()
    clarify = json.dumps({
        "thought": "先查 FAQ 互证",
        "action": "discover",
        "discovers": [{
            "tool": "faq_lookup",
            "args": {"question": "老完成率是怎么算的"},
        }],
    }, ensure_ascii=False)
    decompose = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
             "ledger_notes": "日产油量｜bound｜2025-09-01~2025-09-03",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问 9 月上旬日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": [clarify, decompose, toolmatch],
        "v2.runtime.answer": ["各井日产油量 N-01 为 21.16 吨 [1]。"],
    }
    faq = _FaqFace([
        _faq_hit(
            "faq-8", "老完成率是怎么算的",
            "老完成率按 erp_secret_x 表口径……",  # 材料携禁用词＋外表名（干扰设计）
        ),
    ])
    engine = QueueQueryEngine([_rows_outcome()])
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        faq=faq,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025-09-01 到 09-03 各井日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 零挂起零拒答（材料在窗不触发越集审批/禁用词拒——纯增料）。
        assert not [e for e in events if e.event == "ask"]
        notices = [e.data for e in events if e.event == "notice"]
        assert not [n for n in notices if n.get("type") == "refused"]
        # 正常出数（前置各闸零新增触发——data 链照常执行）。
        assert engine.run_calls == 1
        assert "21.16" in (run.answer or "")
    finally:
        await db.dispose()


# ---------- 端到端钉测④：N1 硬终止（裸写/定义形裸写）＋审计留痕 ----------


async def test_station_n1_bare_question_refused_with_audit(tmp_path: Path) -> None:
    """N1 钉：禁问（老完成率是多少？）→零执行＋audit 行（agent_v2.refused）
    在场——附 C code_first_gate 语义（快车道拆除后 N1 原位保留）。"""
    dump = _sys_dump()
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [], "v2.runtime.decision": []},
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="老完成率是多少？", actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "老完成率" in answer and "产量完成率" in answer  # 拒因带替代词
        assert "21.16" not in answer  # 零数值（硬终止不冒充出数）
        assert completer.counts() == {}  # 先于一切解析——零模型调用
        notices = [e.data for e in events if e.event == "notice"]
        refused = [n for n in notices if n.get("type") == "refused"]
        assert len(refused) == 1  # 机读分型恰一条（审计同源面）
        # 审计留痕：拒答收口一行（security.audit 唯一写口——B12）。
        rows = await _audit_rows(db)
        assert [row.action for row in rows] == [
            "agent_v2.run_created", "agent_v2.refused",
        ]
    finally:
        await db.dispose()


async def test_station_n1_definition_form_refused(tmp_path: Path) -> None:
    """审查②等效补齐分叉实例（V1 对齐）：定义形裸写「什么是老完成率？」——
    V1 拦停（无元问词/裸写）；快车道词条卡直出已拆除，本形照 V1 拦停。"""
    dump = _sys_dump()
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]),
        script={"v2.runtime.understand": [], "v2.runtime.decision": []},
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="什么是老完成率？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "已废弃" in answer and "产量完成率" in answer  # 拒答形（非词条卡直出）
        assert "作业区口语" not in answer and "词条卡" not in answer
        assert completer.counts() == {}  # 零模型（先于一切解析）
        notices = [e.data for e in events if e.event == "notice"]
        assert len([n for n in notices if n.get("type") == "refused"]) == 1
        rows = await _audit_rows(db)
        assert [row.action for row in rows] == [
            "agent_v2.run_created", "agent_v2.refused",
        ]
    finally:
        await db.dispose()


# ---------- 端到端钉测⑤：N1 豁免（元问/引用形）放行＋豁免审计行 ----------


async def test_station_n1_quote_form_exempt_with_audit(tmp_path: Path) -> None:
    """审查②清偿钉：引用形（「老完成率」是什么口径？——每次出现均在引号内）
    豁免放行（不拦停）＋豁免必留 audit 行（agent_v2.ban_exempt）＋零 refused。"""
    dump = _sys_dump()
    clarify = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "「老完成率」是什么口径？",
             "ledger_notes": "老完成率｜禁用词｜无", "chain": "knowledge"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "「老完成率」是什么口径？"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问「老完成率」一词的口径。\n指标候选：无"],
        "v2.runtime.decision": [clarify, toolmatch],
        "v2.runtime.answer": ["「老完成率」是已禁用的旧口径，现行口径为产量完成率 [1]。"],
    }
    retrieval = _retrieval_with(
        _fragment_obs("老完成率为 2024 年废弃口径，现行口径为产量完成率。", "f-1")
    )
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="「老完成率」是什么口径？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        # 豁免放行：子问题知识链照常检索执行（不拦停不拒答）。
        assert retrieval.retrieve_calls == 1
        notices = [e.data for e in events if e.event == "notice"]
        assert not [n for n in notices if n.get("type") == "refused"]
        # 豁免机读 notice 在场（禁用标注＋现行口径随行）。
        exempt = [n for n in notices if n.get("type") == "ban_exempt"]
        assert len(exempt) == 1
        assert "老完成率" in str(exempt[0].get("content"))
        assert "产量完成率" in str(exempt[0].get("content"))
        # 豁免必留 audit 行（写入序＝时序：创建→豁免→收口）。
        rows = await _audit_rows(db)
        assert [row.action for row in rows] == [
            "agent_v2.run_created", "agent_v2.ban_exempt", "agent_v2.run_completed",
        ]
        assert completer.counts().get("v2.runtime.understand") == 1
    finally:
        await db.dispose()


async def test_station_n1_meta_form_exempt_with_audit(tmp_path: Path) -> None:
    """审查②分叉实例（V1 对齐）：元问形「老完成率现在叫什么？」——V1 放行；
    豁免放行＋audit 行在场。"""
    dump = _sys_dump()
    clarify = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "老完成率现在叫什么？",
             "ledger_notes": "老完成率｜禁用词｜无", "chain": "knowledge"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "knowledge", "tool": "doc_retrieve",
         "retrieval_need": {"question": "老完成率现在叫什么？"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问旧称谓的现行叫法。\n指标候选：无"],
        "v2.runtime.decision": [clarify, toolmatch],
        "v2.runtime.answer": ["「老完成率」现叫「产量完成率」[1]。"],
    }
    retrieval = _retrieval_with(
        _fragment_obs("老完成率已废弃，现行口径为产量完成率。", "f-1")
    )
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
        retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="老完成率现在叫什么？", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert retrieval.retrieve_calls == 1  # 放行检索（V1 等效——豁免路照走）
        notices = [e.data for e in events if e.event == "notice"]
        assert not [n for n in notices if n.get("type") == "refused"]
        assert any(n.get("type") == "ban_exempt" for n in notices)
        rows = await _audit_rows(db)
        assert "agent_v2.ban_exempt" in [row.action for row in rows]
        assert "agent_v2.refused" not in [row.action for row in rows]
    finally:
        await db.dispose()


# ---------- 端到端钉测⑥：普通问零误伤零新增延迟（N1 闸静默） ----------


async def test_station_plain_question_gate_silent(tmp_path: Path) -> None:
    """快车道拆除后普通问零误伤：N1 闸静默——understand 照常恰一次调用，
    零快车道直出（无 faq 直出/词条卡/拒答 notice）。V2-53 随动：剧本首发射
    零探查 finalize 被拒回闸拦（拒因回喂）→模型改发分解继续（新合法流）。"""
    dump = _sys_dump()
    decompose = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "2025-09-01 到 09-03 各井日产油量",
             "ledger_notes": "日产油量｜bound｜窗 2025-09-01~2025-09-03", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03"}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": ['{"thought": "定稿", "action": "finalize"}',
                                decompose, toolmatch],
        "v2.runtime.answer": ["各井日产油量 N-01 为 21.16 吨 [1]。"],
    }
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    try:
        handle = await runtime.ask(
            AskRequest(question="2025-09-01 到 09-03 各井日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        assert completer.counts().get("v2.runtime.understand") == 1  # 闸静默零直出
        notices = [e.data for e in events if e.event == "notice"]
        assert not [
            n for n in notices
            if n.get("type") in {"refused", "faq_direct", "term_card"}
        ]
    finally:
        await db.dispose()


# ---------- 端到端钉测⑦：越集续跑全通道（保留件——P-051 已绿随合并） ----------


class ApprovalProbeEngine(QueueQueryEngine):
    """剧本引擎——逐次出列＋捕获 run 收到的放行态（approved_tables 断言面）。"""

    def __init__(self, outcomes: Sequence[QueryOutcome]) -> None:
        super().__init__(outcomes)
        self.approved_seen: list[tuple[str, ...]] = []

    def run(self, plan: Any, *, approved_tables: tuple[str, ...] = ()) -> QueryOutcome:
        self.approved_seen.append(tuple(approved_tables))
        return super().run(plan, approved_tables=approved_tables)


async def test_station_extable_resume_full_channel(tmp_path: Path) -> None:
    """数-察2 形全通道钉：前置闸审批→批准→引擎侧闸审批→批准→前置重判→
    批量重执行（放行态进引擎）→出数收口（附 D 保留件——接口不变）。"""
    ask_outcome = QueryOutcome.external_table_approval(
        tables=("erp_well_register",),
        ask={
            "approval_id": "APP-0831-erp_well_register",
            "reason": (
                "查询引用选表命中集之外的外表：erp_well_register"
                "（执行前表引用比对命中——F14）"
            ),
            "impact": "批准＝链恢复续跑（只读执行，生产库未动）",
            "audit_hint": "外表 erp_well_register",
        },
    )
    engine = ApprovalProbeEngine([ask_outcome, _rows_outcome()])
    dump = _sys_dump()
    clarify = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "井位台账关联的日产油量",
             "ledger_notes": "日产油量｜bound｜外表关联", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch = json.dumps({"matches": [
        {"id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2025-09-01", "window_end": "2025-09-03",
            "external_tables": ["erp_well_register"]}},
    ]}, ensure_ascii=False)
    script = {
        "v2.runtime.understand": ["理解：问井位台账关联的日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": [clarify, toolmatch],
        "v2.runtime.answer": ["各井日产油量 N-01 为 21.16 吨 [1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(dump),
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="外表越集续跑题", actor=ACTOR)
        )
        events = await drain(handle)
        asks = [e.data for e in events if e.event == "ask"]
        assert len(asks) == 1  # 首段：前置闸审批帧
        precond_approval = asks[-1]["frame"]["detail"]["approval_id"]
        run_id = asks[-1]["run_id"]
        # ——第一次批准 → 前置重判放行 → 批量触发引擎侧闸（第二道审批帧）。——
        handle = await runtime.resume(
            run_id, AskChoice(value="批准", approval_id=precond_approval)
        )
        events2 = await drain(handle)
        asks2 = [e.data for e in events2 if e.event == "ask"]
        assert len(asks2) == 1  # 引擎侧审批帧在场
        engine_frame = asks2[-1]["frame"]
        assert engine_frame["kind"] == "external_table_approval"
        assert engine_frame["detail"]["tables"] == ["erp_well_register"]
        engine_approval = engine_frame["detail"]["approval_id"]
        run_row = await store.get_run(run_id)
        assert run_row is not None and run_row.status == "waiting_ask"
        # ——第二次批准 → 续跑全通道：前置重判→批量重执行（放行态）→出数收口。——
        handle = await runtime.resume(
            run_id, AskChoice(value="批准", approval_id=engine_approval)
        )
        events3 = await drain(handle)
        final = events3[-1].data
        assert final["status"] == "completed"
        run_row = await store.get_run(run_id)
        assert run_row is not None and "21.16" in (run_row.answer or "")
        assert engine.run_calls == 2  # 首执行挂起＋批准后续跑恰一次
        assert any("erp_well_register" in seen for seen in engine.approved_seen[1:])
        assert "如实收口不冒充" not in (run_row.answer or "")
    finally:
        await db.dispose()


# ---------- 审计读面（断言辅助——audit_log 只读投影） ----------


async def _audit_rows(db: ConnectionManager) -> list[AuditLog]:
    async with db.readonly() as session:
        return (
            (await session.execute(select(AuditLog).order_by(AuditLog.id)))
            .scalars()
            .all()
        )
