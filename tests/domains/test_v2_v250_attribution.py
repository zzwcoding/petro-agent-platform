"""V2-50 族 C 归属校验治理钉测（P-049——anchors 确定性注入＋引标源↔题眼一致性审）。

票面验收四钉的落测（tickets/v2/V2-50-族C归属校验治理.md 逐字）：

- anchors 注入钉：问句含 W-11→anchors 必含 W-11（代码注入——模型不填也填／
  模型填错不覆盖注入项）；实体词闭世界匹配＝井号词面（precondition 单井点名
  同款形）＋油田名/平台名闭世界规范名（glossary 别名表投影——台账无承载列的
  同源单点）＋报告号数字核（被闭世界实体名包含才注入——日期噪声不注入）；
  两条执行路径（legacy decision 发射／四相位 toolmatch 定案）注入后 anchors
  到达 RetrievalNeed（FakeRetrievalEngine 捕获断言）。
- 归属审钉：A-正1 形（双源同窗消费错源）→一致性审拦下→分源列明或如实说无
  （verify_draft 带 anchors 时对被引检索片段按「出处名＋内容↔题眼锚」二分，
  跨源→分源列明块；runtime 面 notice attribution_split＋verdict.attribution
  机读锚）。
- 不误伤钉：无实体题（anchors 空）行为零变化；数据链行级观察（agg_row/lineage）
  不入归属审辖域；引标源/内容与题眼锚对齐→零追加块。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.retrieval import Observation as RetrievalObservation
from appv2.retrieval import RetrievalBundle
from appv2.runtime import AskRequest, RunStore
from appv2.runtime.graph import verify_draft
from appv2.tools import (
    FakeRetrievalEngine,
    entity_anchor_tokens,
    inject_retrieval_anchors,
)
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import LEDGER_DUMP
from tests.domains.test_v2_react_loop import _rows_outcome

# ---------- ①注入钉：实体锚解析（闭世界匹配——确定性零模型） ----------


def test_entity_anchor_well_number_injected() -> None:
    # 注入钉逐字：问句含 W-11→anchors 必含 W-11。
    assert entity_anchor_tokens("W-11 井生产套管的尺寸与下深是多少？") == ("W-11",)


def test_entity_anchor_field_canonical_and_numeric_core() -> None:
    # 油田名闭世界：规范名（紧凑形）与空格别名形都命中→注入规范名＋报告号数字核。
    anchors = entity_anchor_tokens("渤中34-8 油田一季度注采调整里 3 月配注是多少？")
    assert "渤中34-8油田" in anchors
    assert "34-8" in anchors
    # 别名形（台账登记的空格形）同样命中。
    anchors_b = entity_anchor_tokens("渤中 34-5 油田三季度注采比是多少？")
    assert "渤中34-5油田" in anchors_b
    assert "34-5" in anchors_b


def test_entity_anchor_date_token_not_injected() -> None:
    # 闭世界门：2025-11 不被任何闭世界实体名包含（防日期噪声）——不注入。
    assert "2025-11" not in entity_anchor_tokens("2025-11 投产的井有哪些？")


def test_entity_anchor_platform_alias_form() -> None:
    # 平台名别名形（GLS-PETRO-012 修饰形）命中→注入规范名。
    assert "CEP-C平台" in entity_anchor_tokens("CEP-C 生产平台有几口井？")


def test_entity_anchor_empty_question() -> None:
    # 无实体题：零锚（归属审与注入双双静默——不误伤钉的解析半边）。
    assert entity_anchor_tokens("近 7 天各井日产液量是多少？") == ()


def test_entity_anchor_multi_well_question() -> None:
    # 近名多井题（NQ-M8/W-41·Y-41 形）：两井号都注入——题眼锚全集。
    anchors = entity_anchor_tokens("Y-41 井本月断裂躺井了吗？W-41 是哪口井？")
    assert "Y-41" in anchors and "W-41" in anchors


# ---------- ①注入钉：retrieval_need 合并（模型可增补不可清空） ----------


def test_inject_anchors_model_empty() -> None:
    # 模型不填也填：无 anchors 键→注入项在场。
    need = {"question": "W-11 井生产套管的尺寸与下深是多少？"}
    merged = inject_retrieval_anchors(need)
    assert merged["anchors"] == ["W-11"]
    assert merged["question"] == need["question"]


def test_inject_anchors_model_wrong_not_overwrite() -> None:
    # 模型填错不覆盖注入项：注入项在前保留，模型锚增补续后。
    need = {
        "question": "W-11 井生产套管的尺寸与下深是多少？",
        "anchors": ["Y-21"],
    }
    merged = inject_retrieval_anchors(need)
    assert merged["anchors"] == ["W-11", "Y-21"]


def test_inject_anchors_model_same_dedup() -> None:
    # 模型与注入重合→去重不重复。
    need = {"question": "W-11 井生产套管的尺寸与下深是多少？", "anchors": ["W-11"]}
    assert inject_retrieval_anchors(need)["anchors"] == ["W-11"]


def test_inject_anchors_no_entity_no_change() -> None:
    # 无实体题：模型锚原样保留（注入零添项）。
    need = {"question": "近 7 天各井日产液量是多少？", "anchors": ["日产液量"]}
    assert inject_retrieval_anchors(need)["anchors"] == ["日产液量"]


def test_inject_anchors_does_not_mutate_input() -> None:
    need = {"question": "W-11 井生产套管的尺寸与下深是多少？"}
    inject_retrieval_anchors(need)
    assert "anchors" not in need  # 入参副本纪律（INV-2 同款——不改注入物）


# ---------- ①注入钉：runtime 两执行路径（anchors 到达 RetrievalNeed） ----------

_W11_QUESTION = "W-11 井生产套管的尺寸与下深是多少？"
_DECISION_W11_KNOWLEDGE = json.dumps(
    {
        "action": "execute",
        "task_type": "knowledge",
        "retrieval_need": {"question": _W11_QUESTION, "family_hints": ["completion"]},
    },
    ensure_ascii=False,
)
_UNDERSTAND_W11 = "理解：问 W-11 井生产套管。\n指标候选：无"
_ANSWER_W11 = "W-11 井生产套管下深 2462.0 米[1]。"


def _bundle_obs(text: str, fragment_id: str, report: str) -> RetrievalObservation:
    """检索片段观察（真链形态——handlers._retrieval_observation 同构出处链）。"""
    return RetrievalObservation(
        kind="fragment",
        text=text,
        snippet=text[:80],
        score=0.9,
        leg="keyword",
        family="completion",
        fragment_id=fragment_id,
        report_id=f"rep-{fragment_id}",
        report=report,
        library_id="lib-completion",
        library="完井工程库",
        section="1.2 井身结构",
        locator={"library": "完井工程库", "report": report},
    )


def _bundle_with(*obs: RetrievalObservation) -> FakeRetrievalEngine:
    return FakeRetrievalEngine(
        bundle=RetrievalBundle(
            observations=list(obs), window_note=f"召回 {len(obs)} 支/送窗 {len(obs)} 支"
        )
    )


async def test_decision_path_injects_anchors(tmp_path: Path) -> None:
    # legacy decision 路径：模型不填 anchors→注入项到达 RetrievalNeed。
    retrieval = _bundle_with(
        _bundle_obs(
            "1.2 井身结构（实钻）：生产套管下深 2462.0 米。",
            "f-w11-1",
            "《A-W11井完井工程报告》",
        )
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND_W11],
        "v2.runtime.decision": [_DECISION_W11_KNOWLEDGE, '{"action": "finalize"}'],
        "v2.runtime.answer": [_ANSWER_W11],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        retrieval=retrieval,
    )
    try:
        handle = await runtime.ask(AskRequest(question=_W11_QUESTION, actor=ACTOR))
        await drain(handle)
        assert retrieval.needs, "doc_retrieve 未触达"
        need = retrieval.needs[0]
        # 注入钉逐字：模型不填也填——W-11 到达检索需求锚。
        assert "W-11" in need.anchors
    finally:
        await db.dispose()


async def test_toolmatch_path_injects_anchors(tmp_path: Path) -> None:
    # 四相位 toolmatch 路径：匹配定案不带 anchors→注入项随定案到达 RetrievalNeed
    # （TOOLMATCH_TWO s2 未填 anchors——W-111 代码注入，FakeRetrievalEngine 捕获）。
    from tests.domains.test_v2_four_phase import (
        CLARIFY_GROUP_DATA_KNOWLEDGE,
        TOOLMATCH_TWO,
    )

    retrieval = _bundle_with(
        _bundle_obs(
            "W-111 井采用酸压完井，投产初期日产油 291 方。",
            "frag-w111-1",
            "W-111 井完井报告",
        )
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [
            "理解：既要数值也要报告佐证。\n指标候选：日产油量"
        ],
        "v2.runtime.decision": [CLARIFY_GROUP_DATA_KNOWLEDGE, TOOLMATCH_TWO],
        "v2.runtime.answer": (
            "子任务 s1：2025-09-01 各井日产油量 N-01 为 21.16 吨 [1]。\n"
            "子任务 s2：W-111 井完井报告记载投产初期日产油 291 方 [3]。"
        ),
    }
    runtime, _completer, db = await make_runtime(
        tmp_path,
        engine=QueueQueryEngine([_rows_outcome()]),
        script=script,
        retrieval=retrieval,
        four_phase=True,
        ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        handle = await runtime.ask(
            AskRequest(
                question=(
                    "2025 年 9 月 1 日到 3 日的日产油量，"
                    "以及 W-111 井完井报告里的投产初期日产油"
                ),
                actor=ACTOR,
            )
        )
        await drain(handle)
        knowledge_needs = [
            need for need in retrieval.needs if "W-111" in need.question
        ]
        assert knowledge_needs, "knowledge 链检索未触达"
        # 注入钉逐字：s2 匹配定案未填 anchors——W-111 代码注入到达检索需求。
        assert "W-111" in knowledge_needs[0].anchors
    finally:
        await db.dispose()


# ---------- ②归属审钉：verify_draft 引标源↔题眼一致性审（单元面） ----------


def _w11_table_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "content": "1.2 井身结构（实钻）　生产套管　9-5/8″　下深 2462.0 米",
        "source": "《A-W11井完井工程报告》",
        "source_id": "f-w11-1",
        "version": None,
        "freshness": "",
        "scope": "completion",
        "locator": {
            "kind": "fragment",
            "library": "完井工程库",
            "report": "《A-W11井完井工程报告》",
        },
    }


def _y21_table_obs(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "content": "1.2 井身结构（实钻）　生产套管　9-5/8″　下深 2680.4 米",
        "source": "《Y-21井完井工程报告》",
        "source_id": "f-y21-1",
        "version": None,
        "freshness": "",
        "scope": "completion",
        "locator": {
            "kind": "fragment",
            "library": "完井工程库",
            "report": "《Y-21井完井工程报告》",
        },
    }


# A-正1 帧形（Q14）：双源同窗、消费错源——W-11 题眼引 Y-21 表值。
_A1_DRAFT = "W-11 井生产套管下深 2680.4 米[2]。"


def test_verify_attribution_cross_source_listed() -> None:
    # 归属审钉：A-正1 形→一致性审拦下→分源列明（两源各自带出处列出）。
    text, rewritten, cited, split = verify_draft(
        _A1_DRAFT, [_w11_table_obs(1), _y21_table_obs(2)], anchors=("W-11",)
    )
    assert rewritten == 0  # 数值支撑判定不受归属审影响（INV-1 语义不变）
    assert cited == [2]
    assert split is False  # INV-4 矛盾池不误收（subject 不同的两源）
    assert "跨源归属审" in text
    assert "分源列明" in text
    assert "W-11" in text  # 题眼锚在场
    assert "《A-W11井完井工程报告》" in text  # 对齐源列出
    assert "《Y-21井完井工程报告》" in text  # 跨源源列出


def test_verify_attribution_aligned_citation_no_block() -> None:
    # 引标源与题眼锚对齐（出处名含 W-11）→零追加块。
    text, rewritten, cited, split = verify_draft(
        "W-11 井生产套管下深 2462.0 米[1]。",
        [_w11_table_obs(1)],
        anchors=("W-11",),
    )
    assert rewritten == 0 and cited == [1] and split is False
    assert "跨源归属审" not in text


def test_verify_attribution_content_aligned_no_block() -> None:
    # 出处名不含锚但被引内容含锚（B-正3 形：月报行文点名 W-22）→对齐零追加。
    obs = {
        "index": 1,
        "content": "4.1 杆断分析：W-22 井狗腿度 4.2°/30m，杆柱弯曲偏磨集中。",
        "source": "《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        "source_id": "f-b22-1",
        "version": None,
        "freshness": "",
        "scope": "monthly",
        "locator": {
            "kind": "fragment",
            "library": "月报库",
            "report": "《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        },
    }
    text, rewritten, cited, _split = verify_draft(
        "W-22 井杆断根因是狗腿度 4.2°/30m[1]。",
        [obs],
        anchors=("W-22",),
    )
    assert rewritten == 0 and cited == [1]
    assert "跨源归属审" not in text


def test_verify_attribution_no_anchors_zero_drift() -> None:
    # 不误伤钉：无实体题（anchors 空）输出与旧实现逐字节一致（零追加块）。
    observations = [_w11_table_obs(1), _y21_table_obs(2)]
    baseline = verify_draft(_A1_DRAFT, observations)
    anchored = verify_draft(_A1_DRAFT, observations, anchors=())
    assert baseline == anchored
    assert "跨源归属审" not in baseline[0]


def test_verify_attribution_data_rows_out_of_scope() -> None:
    # 数据链行级观察（agg_row）不入归属审辖域（行级事实按 井@日 独立键——
    # 混合组 data 链引标零误伤）。
    obs = {
        "index": 1,
        "content": "井号=N-01；区块=渤南；日期=2025-09-01；日产油量（吨）=21.16",
        "source": "agg.fct_daily_metering",
        "source_id": "N-01@2025-09-01",
        "version": None,
        "freshness": "",
        "scope": "agg",
        "locator": {"kind": "agg_row", "table": "agg.fct_daily_metering"},
    }
    text, rewritten, cited, _split = verify_draft(
        "N-01 井 2025-09-01 日产油量 21.16 吨[1]。",
        [obs],
        anchors=("W-111",),
    )
    assert rewritten == 0 and cited == [1]
    assert "跨源归属审" not in text


def test_verify_attribution_no_aligned_material_says_none() -> None:
    # 「如实说无」半边：窗内全为跨源材料（目标报告缺席）→分源列明＋如实声明。
    text, _rewritten, cited, _split = verify_draft(
        _A1_DRAFT, [_y21_table_obs(2)], anchors=("W-11",)
    )
    assert cited == [2]
    assert "跨源归属审" in text
    assert "《Y-21井完井工程报告》" in text
    assert "窗内无对齐题眼锚" in text


def test_verify_attribution_aligned_material_uncited_note() -> None:
    # 对齐材料在窗但未进答案引用→注记点名（题眼归属按出处核对）。
    text, _rewritten, _cited, _split = verify_draft(
        _A1_DRAFT, [_w11_table_obs(1), _y21_table_obs(2)], anchors=("W-11",)
    )
    assert "未进答案引用" in text


# ---------- ②归属审钉：runtime 全链（notice＋verdict 机读锚） ----------


async def test_verify_node_attribution_notice_and_verdict(tmp_path: Path) -> None:
    # A-正1 形全链：双源同窗、草稿消费错源→答案面分源列明块＋notice＋verdict。
    retrieval = _bundle_with(
        _bundle_obs(
            "1.2 井身结构（实钻）：生产套管下深 2462.0 米。",
            "f-w11-1",
            "《A-W11井完井工程报告》",
        ),
        _bundle_obs(
            "1.2 井身结构（实钻）：生产套管下深 2680.4 米。",
            "f-y21-1",
            "《Y-21井完井工程报告》",
        ),
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND_W11],
        "v2.runtime.decision": [_DECISION_W11_KNOWLEDGE, '{"action": "finalize"}'],
        "v2.runtime.answer": ["W-11 井生产套管下深 2680.4 米[2]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=_W11_QUESTION, actor=ACTOR))
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "跨源归属审" in answer  # 分源列明块进答案面
        assert "《Y-21井完井工程报告》" in answer
        notices = [e.data for e in events if e.event == "notice"]
        assert any(n.get("type") == "attribution_split" for n in notices)
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts
        attribution = verdicts[0].get("attribution") or {}
        assert "W-11" in (attribution.get("anchors") or [])
        assert 2 in (attribution.get("cross") or [])
    finally:
        await db.dispose()


async def test_verify_node_no_entity_question_zero_drift(tmp_path: Path) -> None:
    # 不误伤钉（全链半边）：无实体题（无锚）→无归属审块、无 notice、verdict
    # attribution.cross 空。
    retrieval = _bundle_with(
        _bundle_obs(
            "口径说明：日产油量为班次合计日口径，单位吨。",
            "f-cal-1",
            "《口径说明卡》",
        )
    )
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问口径。\n指标候选：日产油量"],
        "v2.runtime.decision": [
            json.dumps(
                {
                    "action": "execute",
                    "task_type": "knowledge",
                    "retrieval_need": {"question": "日产油量的口径是什么"},
                },
                ensure_ascii=False,
            ),
            '{"action": "finalize"}',
        ],
        "v2.runtime.answer": ["日产油量为班次合计日口径，单位吨[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script,
        retrieval=retrieval,
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="日产油量的口径是什么", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert "跨源归属审" not in (run.answer or "")
        notices = [e.data for e in events if e.event == "notice"]
        assert not any(n.get("type") == "attribution_split" for n in notices)
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts
        attribution = verdicts[0].get("attribution") or {}
        assert attribution.get("cross") == []
    finally:
        await db.dispose()
