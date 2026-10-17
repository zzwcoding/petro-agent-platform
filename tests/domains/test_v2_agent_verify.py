"""V2-06 runtime 核验步验收——specs/agent-loop.md「验收测试」表 verify 侧两条 1:1 同名落测。

- unsupported_claim_rewritten：核验步逐条检查阐述草稿的断言有 Observation 支撑；
  无支撑断言改写为「未找到（材料未披露）」＋notice——禁止无据断言进答案（INV-1）；
- contradiction_split_source：多来源矛盾时答案必须分源列明（各标出处）或显式声明
  歧义；禁止无出处调和（INV-4）；
- citation_on_unrelated_line_rewritten（P-006b·R9 反例钉测）：引标在界但断言与被引
  观察「无关」（观察中的数值未被断言文本复述）＝无支撑——改写/拒，非行级引标即过。

骨架版核验规则（确定性断言级支撑，细化批可换更强实现——语义不破）：
- 草稿逐行、逐引标抽取其辖断言文本（行首/上一引标到本引标之间）；断言级支撑判定＝
  被引观察 content 中的每个数值 token 须被该断言文本复述——引标贴无关行（材料数值
  行内找不到）＝无据断言，整行改写「未找到（材料未披露）：〈原文〉」＋notice，
  该引标不收进引用集（INV-1——禁止无据断言进答案）；
- V2-23 豁免（表格/血缘卡观察承载）：agg_row/lineage 卡是权威观察本身（非断言
  素材）——引它们只须复述至少一个数值 token（P-015 数-明1 实测：行内容含日期/
  区块随行数值，「全数值复述」把整张明细表吞成「未找到」；零重叠仍改写——R9
  反例不回退）；改写只管自由文本断言行——无引标且无数字的结构行（标题/表头/
  分隔线）原样保留；
- 矛盾判定：被引观察中，同一 subject（台账卡取内容首段「名称」；agg_row 行级
  事实按 井@日 键独立，不入跨源矛盾池）出现 ≥2 支且值不同→强制分源列明块
  （逐支带 [n] 出处）＋notice——禁止无出处调和。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from appv2.knowledge import Evidence
from appv2.query import (
    LINEAGE_KEY_CALIBER,
    LINEAGE_KEY_CLOSING,
    LINEAGE_KEY_WATERMARK,
    LineageLine,
    QueryOutcome,
)
from appv2.runtime import (
    AskRequest,
    RunEvent,
    RunStore,
)
from appv2.runtime.graph import _ANSWER_INSTRUCTION, verify_draft
from appv2.tools import FakeKnowledgeStore
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    DECISION_FINALIZE,
    QueueQueryEngine,
    drain,
    make_runtime,
)


def _rows_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=({"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
        ),
    )

# 台账证据（同一要素名两套口径——吨 vs 方，跨源矛盾的被控源）。
_EVIDENCE_TON = Evidence(
    element_id="201",
    kind="metric",
    value="日产油量：21 吨/日（口径卡）",
    source="sem_metric#201",
    version="1",
    freshness="",
    scope="日",
    binding_state="bound",
)
_EVIDENCE_CUBIC = Evidence(
    element_id="301",
    kind="metric",
    value="日产油量：8824.4 方/日（口径卡）",
    source="sem_metric#301",
    version="2",
    freshness="",
    scope="日",
    binding_state="bound",
)

# 决策发射罐头（V2-31——发现语义卡/带表计划/定稿）。
_DECISION_SEMANTIC = (
    '{"action": "discover", "discovers": '
    '[{"tool": "semantic_query", "args": {"element_name": "日产油量"}}]}'
)
_DECISION_TABLED = (
    '{"action": "execute", "task_type": "data", '
    '"plan": {"metric_slot": "日产油量", "ranking": false, '
    '"window_start": "2025-01-01", "window_end": "2026-01-01", "limit": 50}}'
)


def _semantic_script(draft: str) -> dict[str, Sequence[str]]:
    return {
        "v2.runtime.understand": ["理解：问日产油量口径。\n指标候选：无"],
        "v2.runtime.decision": [_DECISION_SEMANTIC, DECISION_FINALIZE],
        "v2.runtime.answer": [draft],
    }


def _notices(events: list[RunEvent]) -> list[dict[str, Any]]:
    return [e.data for e in events if e.event == "notice"]


# ---------- 验收④：无据断言删句＋notice（INV-1；EB3 D3） ----------


async def test_unsupported_claim_rewritten(tmp_path: Path) -> None:
    """行 23｜断言无 Observation 支撑→verify **删句**＋notice（**收口侧**断言）。

    本行落 `orchestration` 的收口面（`RT-W5-01c` 行 23）：四相位真链跑完（澄清→匹配→过闸→批量→
    汇总→核验→收口），**「提交完成的是本块」**——`verify` 相位把无据断言删去（2026-10-17 EB3 D3：
    删句、不贴前缀）并出 `notice`（其规格行为 3），本块据 `Verdict` 收口：终态 run 行的 `answer`
    是**删改后**的答案，机读信号（`verdict` 帧改写计数＋`notice` 分型）同批在场。
    """
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    draft = (
        "N-01 井 2025-09-01 日产油量 21.16 吨 [1]。\n"
        "全油田 86 口井昨日均超产 50 吨。"
    )
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [
            v2.v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2.v2_matches(
                v2.v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": [draft],
    }
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    engine = v2.V2QueueEngine([v2._rows_outcome()])
    from appv2.infra.clock import freeze

    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(script=script, registry=v2.v2_registry(engine=engine))
        events = await v2.v2_run(runtime, "2025 年 9 月 1 日到 3 日的日产油量")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    row = v2.V2RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    answer = row.answer or ""
    # 有据行保留（引标 [1] 在界——Observation 支撑）＋无据行**整行离场**（EB3 D3：删句不留残句）
    assert "21.16" in answer
    assert "86 口井" not in answer
    assert "未找到（材料未披露）" not in answer
    # 增补面随行（EB3 D1）：本 run 无矛盾无跨源 → 恰引用清单一条（正文零程序块）
    assert [entry["block"] for entry in row.supplements] == ["citations"]
    assert "引用：" in row.supplements[0]["text"]
    assert "引用：" not in answer
    supplement_frames = [event for event in events if event.event == "supplement"]
    assert [frame.data["block"] for frame in supplement_frames] == ["citations"]
    # 机读信号（verify 步拦截的 notice 分型 ＋ verdict(verify) 帧的改写计数）
    notices = [event.data for event in events if event.event == "notice"]
    assert any(item.get("type") == "unsupported_claim" for item in notices)
    verify_frames = [
        event.data
        for event in events
        if event.event == "verdict" and event.data.get("subtype") == "verify"
    ]
    assert verify_frames and verify_frames[0]["rewritten"] == 1


# ---------- 验收⑤：矛盾两来源→答案分源列明各带 citation（INV-4） ----------


async def test_contradiction_split_source(tmp_path: Path) -> None:
    """行 24｜矛盾两来源→答案分源列明各带 citation（INV-4）（**收口侧**断言）。

    同 row 23 的落法（`RT-W5-01c` 行 24）：两口径卡（同 subject 两个值）经台账钻取进观察面，汇总
    草稿两支并列；`verify` 相位把矛盾**分源列明**（逐支带 `[n]` 出处、禁止无出处调和），本块据
    `Verdict` 收口——终态答案携分源列明块与两支出处，`contradiction_split` notice 同批在场。
    """
    from tests.domains import test_v2_four_phase as v2

    dump = v2.v2_ledger_dump()
    note = v2.v2_ledger_note(dump, "日产油量")
    discover = json.dumps(
        {
            "action": "discover",
            "discovers": [{"tool": "semantic_query", "args": {"element_name": "日产油量"}}],
        },
        ensure_ascii=False,
    )
    draft = "日产油量口径为 21 吨/日 [1]；另一口径卡记 8824.4 方/日 [2]。"
    script = {
        "understand": [v2.V2_UNDERSTAND],
        "decision": [
            discover,
            v2.v2_decompose(
                subtask_id="s1",
                question="2025-09-01 到 09-03 各井日产油量",
                ledger_notes=note,
                chain="data",
            ),
            v2.v2_matches(
                v2.v2_data_match(
                    subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03"
                )
            ),
        ],
        "answer": [draft],
    }
    v2.wire_ledger_projection(v2.V2LedgerPort(dump))
    knowledge = FakeKnowledgeStore(evidence_hits=[_EVIDENCE_TON, _EVIDENCE_CUBIC])
    engine = v2.V2QueueEngine([v2._rows_outcome()])
    from appv2.infra.clock import freeze

    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2.v2_runtime(
            script=script, registry=v2.v2_registry(engine=engine, knowledge=knowledge)
        )
        events = await v2.v2_run(runtime, "日产油量的口径是什么")
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    row = v2.V2RunStore().run(run_id)
    assert row is not None
    answer = row.answer or ""
    # 分源列明块出场（INV-4：各标出处，禁止无出处调和）——两支逐支带 [n] 与来源；
    # EB3 D2：块入**增补面**（正文只留模型稿），故块文本随 `row.supplements`／`supplement` 帧在场。
    # 本 run 两块同现：verify 侧分源块（`各来源说法如下…`）＋ answering 收口侧「互不一致」分源块
    # ＋ 分源列明归属块（两出处）＋ 引用清单——按产出序入列（EB3 D2 原序）。
    supplement_frames = [event.data for event in events if event.event == "supplement"]
    assert [frame["block"] for frame in supplement_frames] == [
        "split",
        "split",
        "attribution",
        "citations",
    ]
    assert [entry["block"] for entry in row.supplements] == [
        frame["block"] for frame in supplement_frames
    ]  # 帧面与落库面同序同源
    face = "\n".join(entry["text"] for entry in row.supplements)
    # 2026-10-17 EB4b：归属块段头白话化（旧「分源列明（逐源归属——…）」→「按来源分别列出
    # （每条结论都标出它来自哪个来源）：」）——取本块段头独有子串（「各来源说法如下，按来源分别
    # 列出」是 verify 侧 split 块头，不作本块判据）。
    assert "每条结论都标出它来自哪个来源" in face  # 归属块段头（行为 17 分源列明）
    assert "互不一致" in face  # 行为 6 的「互不一致」标
    assert "[1] sem_metric#201 · 201：日产油量：21 吨/日" in face
    assert "[2] sem_metric#301 · 301：日产油量：8824.4 方/日" in face
    assert "每条结论都标出它来自哪个来源" not in answer  # 正文零程序块
    assert "sem_metric#201" not in answer
    notices = [event.data for event in events if event.event == "notice"]
    assert any(item.get("type") == "contradiction_split" for item in notices)
    verify_frames = [
        event.data
        for event in events
        if event.event == "verdict" and event.data.get("subtype") == "verify"
    ]
    assert verify_frames and verify_frames[0]["split"] == 1


# ---------- 验收⑤补（R9 反例钉测）：引标贴无关行被改写/拒 ----------


async def test_citation_on_unrelated_line_rewritten(tmp_path: Path) -> None:
    # 引标 [1] 在界，但断言文本与被引观察无关（观察中的数值 21.16/井号 01 未被
    # 行内复述——行内只有无据数值 86/50）：断言级支撑判「无据」，整行改写——
    # 行级「引标在界即过」的骨架规则已收口（P-006b·R9，INV-1）。
    draft = "全油田 86 口井昨日均超产 50 吨[1]。"
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问日产油量。\n指标候选：日产油量"],
        "v2.runtime.decision": [
            '{"action": "execute", "task_type": "data", '
            '"plan": {"metric_slot": "日产油量", "ranking": false, '
            '"window_start": "2025-09-01", "window_end": "2025-09-03", "limit": 5}}',
            DECISION_FINALIZE,
        ],
        "v2.runtime.answer": [draft],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="2025 年 9 月 1 日到 3 日的日产油量", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        # 无关行改写「未找到（材料未披露）」——引标贴无关行过不了（INV-1）。
        assert "86 口井" in answer
        assert "未找到（材料未披露）" in answer
        assert "21.16" not in answer  # 观察数值未被复述——不进答案与引用块
        # notice＋verdict：改写计数 1；无支撑引标不收进引用集（引用块零列出——
        # verdict.cited 仍空，R9 语义不变）。
        notices = _notices(events)
        assert any(n.get("type") == "unsupported_claim" for n in notices)
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts and verdicts[0]["rewritten"] == 1
        assert verdicts[0]["cited"] == []
        assert "引用：" not in answer  # 引用块不收无支撑引标（R9 不变）
        # citation 帧行为变化（V2-48 citation 落账——L0 追认注记）：改写行保留的
        # 悬空 [1] 仍在答案面（INV-1 改写不剥引标），V2-48 起 [n]↔citation 帧
        # 同步（悬空形清零）——帧照发（帧集＝支撑集 ∪ 答案面合法 [n]），
        # 「citation 零发」旧钉由 V2-48 票面验收「citation 落账钉」取代；本钉
        # 核心判据（改写/引用集不含/答案无被引数值）全部保持。
        citation_frames = [e for e in events if e.event == "citation"]
        assert [int(e.data["index"]) for e in citation_frames] == [1]
    finally:
        await db.dispose()


# ---------- V2-23：表格/血缘卡观察承载豁免断言级改写（verify_draft 直测） ----------


def _agg_row_obs(index: int, well_id: str, value: str) -> dict[str, Any]:
    """agg 行观察（真实链形态——handlers._rows_observations 同构：内容含日期/区块
    随行数值，行内数值 token 不止键值本身）。"""
    return {
        "index": index,
        "content": f"井号={well_id}；区块=渤南；日期=2025-09-01；日产油量（吨）={value}",
        "source": "agg.fct_daily_metering",
        "source_id": f"{well_id}@2025-09-01",
        "version": None,
        "freshness": "",
        "scope": "agg",
        "locator": {
            "kind": "agg_row",
            "table": "agg.fct_daily_metering",
            "well_id": well_id,
        },
    }


_LINEAGE_CONTENT = (
    "① 口径 日产油量（单位：吨）——口径声明\n"
    "④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1）\n"
    "⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"
)


def _lineage_obs(index: int = 3) -> dict[str, Any]:
    return {
        "index": index,
        "content": _LINEAGE_CONTENT,
        "source": "agg.fct_daily_metering",
        "source_id": "lineage",
        "version": None,
        "freshness": "",
        "scope": "agg",
        "locator": {"kind": "lineage", "table": "agg.fct_daily_metering"},
    }


def test_verify_draft_table_rows_carrying_observations_kept() -> None:
    # 数-明1 P-015 实测形：表格行转述权威行（行内容含日期/区块随行数值，行内只复述
    # 键值）——豁免「全数值复述」改写；无引标数字断言行照改；非断言结构行保留。
    observations = [_agg_row_obs(1, "N-01", "21.16"), _agg_row_obs(2, "N-02", "30.79")]
    draft = (
        "## 答案\n"
        "\n"
        "全油田 86 口井昨日均超产 50 吨。\n"
        "\n"
        "| 井号 | 日产油量（吨） | 引标 |\n"
        "|------|---------------|------|\n"
        "| N-01 | 21.16 | [1] |\n"
        "| N-02 | 30.79 | [2] |\n"
    )
    text, rewritten, cited, split = verify_draft(draft, observations)
    assert rewritten == 1  # 恰无引标数字断言行一支
    assert cited == [1, 2]  # 表格行引标收进引用集
    assert "| N-01 | 21.16 | [1] |" in text  # 表格行原样保留（无「未找到」前缀）
    assert "| 井号 | 日产油量（吨） | 引标 |" in text  # 表头/分隔线＝结构行照旧
    assert "|------|---------------|------|" in text
    assert "## 答案" in text and "未找到（材料未披露）：## 答案" not in text
    assert "未找到（材料未披露）：全油田 86 口井" in text  # 无引标数字断言照改（INV-1）
    assert split is False


def test_verify_draft_carrier_zero_overlap_still_rewritten() -> None:
    # 豁免有底：表格行/血缘卡引挂零重叠的无关断言照改（R9 反例在承载豁免下不回退）。
    observations = [_agg_row_obs(1, "N-01", "21.16"), _lineage_obs(2)]
    text, rewritten, cited, _split = verify_draft(
        "| 全油田 86 口井均超产 50 吨 | [1] |\n口径存疑待核[2]。",
        observations,
    )
    assert rewritten == 2  # 表格形态的无据行与自由文本无据行同判
    assert cited == []
    assert "未找到（材料未披露）：| 全油田 86 口井均超产 50 吨 | [1] |" in text
    assert "未找到（材料未披露）：口径存疑待核[2]。" in text


def test_verify_draft_lineage_card_carrier_free_text_kept() -> None:
    # 血缘卡（lineage）同豁免域：自由文本行引血缘卡只须复述任一数值 token——
    # 「全数值复述」对大杂烩卡（口径/批次/水位/LIMIT 全在）形同必吞（V2-23）。
    text, rewritten, cited, _split = verify_draft(
        "明细按 LIMIT 50 收口[3]；未覆盖部分如实声明。",
        [_lineage_obs(3)],
    )
    assert rewritten == 0
    assert cited == [3]
    assert "LIMIT 50 收口[3]" in text


# ---------- P-024b 审查 S2：fragment（kb 检索片段）并入观察承载豁免域 ----------


_FRAGMENT_CONTENT = (
    "射孔参数：枪型 102 枪，相位 60°，孔密 16 孔/米，射孔总厚度 60 米，"
    "射孔总孔数 786 孔，平均每米 12.4 孔，压裂车组 28.0 MPa，"
    "替浆量 448 方，测试产量 486 方，井温 21.75 ℃。"
)


def _fragment_obs(index: int = 1) -> dict[str, Any]:
    """kb 检索片段观察（真链形态——handlers._retrieval_observation 同构：长片段
    数值 token 十余个，「全数值复述」判据形同必吞——P-024 run-a2961c64 实测
    支撑 0｜改写 10）。"""
    return {
        "index": index,
        "content": _FRAGMENT_CONTENT,
        "source": "W-111 井完井报告",
        "source_id": "frag-w111-01",
        "version": None,
        "freshness": "",
        "scope": "completion",
        "locator": {
            "library": "完井工程库",
            "report": "W-111 井完井报告",
            "kind": "fragment",
        },
    }


def test_verify_draft_fragment_carrier_any_numeric_overlap_kept() -> None:
    # fragment 并入承载豁免（P-020 同款形）：转述片段任一数值 token 重叠即支撑——
    # 逐行转述长片段不再被「全数值复述」整行清成「未找到」（S2 修复钉）。
    text, rewritten, cited, _split = verify_draft(
        "W-111 井射孔总孔数 786 孔[1]，采用 102 枪。",
        [_fragment_obs(1)],
    )
    assert rewritten == 0
    assert cited == [1]
    assert "射孔总孔数 786 孔[1]" in text
    assert "未找到（材料未披露）" not in text


def test_verify_draft_fragment_zero_overlap_still_rewritten() -> None:
    # 豁免仍有底（R9 反例不回退）：引挂 fragment 但断言与片段数值零重叠——照改。
    text, rewritten, cited, _split = verify_draft(
        "W-111 井投产初期日产油 291 方[1]。",
        [_fragment_obs(1)],
    )
    assert rewritten == 1
    assert cited == []
    assert "未找到（材料未披露）：W-111 井投产初期日产油 291 方[1]。" in text


# ---------- V2-23：全链两测——表格明细进答案＋收口注记确定性随行 ----------


def _rows_with_closing_outcome() -> QueryOutcome:
    return QueryOutcome.rows_with_lineage(
        columns=(("well_id", "井号"), ("日产油量（吨）", "日产油量（吨）")),
        rows=(
            {"well_id": "N-01", "日产油量（吨）": Decimal("21.16")},
            {"well_id": "N-02", "日产油量（吨）": Decimal("30.79")},
        ),
        lineage=(
            LineageLine(key=LINEAGE_KEY_CALIBER, value="日产油量（单位：吨）——口径声明"),
            LineageLine(key=LINEAGE_KEY_WATERMARK, value="汇总层水位 2026-08-31"),
            LineageLine(
                key=LINEAGE_KEY_CLOSING,
                value=(
                    "LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，"
                    "只封顶不抬底"
                ),
            ),
        ),
    )


_TABLE_DRAFT = (
    "## 答案\n"
    "\n"
    "材料仅覆盖 2025-09-01 单日（未及全窗——如实声明）。\n"
    "\n"
    "| 井号 | 日产油量（吨） | 引标 |\n"
    "|------|---------------|------|\n"
    "| N-01 | 21.16 | [1] |\n"
    "| N-02 | 30.79 | [2] |\n"
)


async def test_table_answer_survives_verify(tmp_path: Path) -> None:
    # 数-明1 P-015 帧存档同形草稿走全链：六步走完且答案是表格明细——不再整表被
    # 吞成「未找到」（P-015 实测 rewritten=34/支撑 0 的假绿根因）。
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问日产油量明细。\n指标候选：日产油量"],
        "v2.runtime.decision": [_DECISION_TABLED, DECISION_FINALIZE],
        "v2.runtime.answer": [_TABLE_DRAFT],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_with_closing_outcome()]), script=script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="去年各井每天的日产油量是多少", actor=ACTOR)
        )
        events = await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        # 表格行原样进答案（无「未找到」前缀）——内容级断言（票面验收②形状）。
        assert "| N-01 | 21.16 | [1] |" in answer
        assert "| N-02 | 30.79 | [2] |" in answer
        assert "未找到（材料未披露）：|" not in answer  # 表格行零改写
        assert "## 答案" in answer  # 结构行不再被改写挂前缀
        # 无引标数字断言行照改（INV-1 不豁免）。
        assert "未找到（材料未披露）：材料仅覆盖 2025-09-01 单日" in answer
        # 收口注记确定性随行（血缘⑤ LIMIT 收口——截断不静默）。
        assert "收口注记" in answer and "LIMIT 50" in answer
        # 引用集含两表格行引标（citation 事件带出处链）。
        citations = [e.data for e in events if e.event == "citation"]
        assert [c["index"] for c in citations] == [1, 2]
        verdicts = [e.data for e in events if e.event == "verdict"]
        assert verdicts and verdicts[0]["rewritten"] == 1  # 恰无引标数字行一支
        assert verdicts[0]["cited"] == [1, 2]
    finally:
        await db.dispose()


async def test_closing_note_not_duplicated_when_draft_carries_it(tmp_path: Path) -> None:
    # 草稿自带收口注记（引血缘卡）时答案不重复追加（恰好一次）。
    draft = _TABLE_DRAFT + "\n明细按⑤ 收口注记 LIMIT 50 收口[3]。\n"
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": ["理解：问日产油量明细。\n指标候选：日产油量"],
        "v2.runtime.decision": [_DECISION_TABLED, DECISION_FINALIZE],
        "v2.runtime.answer": [draft],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_with_closing_outcome()]), script=script
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(
            AskRequest(question="去年各井每天的日产油量是多少", actor=ACTOR)
        )
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        answer = run.answer or ""
        assert "收口注记 LIMIT 50 收口[3]" in answer  # 草稿行原样保留（血缘卡豁免）
        assert answer.count("收口注记") == 1  # 恰一次——不重复追加
    finally:
        await db.dispose()


class FakeQueryEngineStub:
    """semantic 路径占位引擎（data_query 不被触——plan 选了 semantic_query）。"""

    def validate(self, plan: Any, *, candidates: Any = None) -> Any:
        raise AssertionError("semantic 路径不得触 data_query")

    def run(self, plan: Any, *, approved_tables: tuple[str, ...] = ()) -> Any:
        raise AssertionError("semantic 路径不得触 data_query")


# ---------- V2-54：INV-1 核验辖域治理（空辖域兜底＋窗内对齐放行） ----------
# 病因＝_assertion_chunks 辖域切分缺陷：邻接引标 [1][20] 的第二辖域为零宽空串、
# 行首引标的辖域为「- 」符号串——空壳辖域必判无据，整行误盖「未找到（材料未
# 披露）：」前缀（Q15 65 帧/394 行主机理）。修三层：①空壳辖域整行重判；
# ②窗内对齐放行（全部数字在窗内任一观察 content 出现）；③真无据照旧盖章。


def _frag_carrier(index: int, content: str) -> dict[str, Any]:
    """fragment 载体观察（真链 handlers._retrieval_observation 同构——测试钉）。"""
    return {
        "index": index,
        "content": content,
        "source": "《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        "source_id": f"frag-v254-{index}",
        "version": None,
        "freshness": "",
        "scope": "monthly",
        "locator": {
            "kind": "fragment",
            "library": "月报库",
            "report": "《B-渤中34-5油田躺井治理与检泵作业月报-202608》",
        },
    }


def test_verify_v254_t1_adjacent_citations_empty_scope_whole_line_kept() -> None:
    # T1 邻接引标放行（修前必挂形反转）：[1][20] 连写时 [20] 辖域＝零宽空串——
    # 修一剥引标整行重判（两引标观察均 fragment 载体且含 512／52.3）→零改写。
    observations = [
        _frag_carrier(1, "W-21 井本周期检泵周期 512 天，上周期 486 天。"),
        _frag_carrier(20, "W-21 井本次检泵作业费用 52.3 万元（含合准）。"),
    ]
    text, rewritten, cited, _split = verify_draft(
        "W-21 井检泵周期为 512 天，作业费用为 52.3 万元 [1][20]",
        observations,
    )
    assert rewritten == 0
    assert cited == [1, 20]
    assert "W-21 井检泵周期为 512 天，作业费用为 52.3 万元 [1][20]" in text
    assert "未找到（材料未披露）" not in text


def test_verify_v254_t2_line_head_citation_dash_scope_whole_line_kept() -> None:
    # T2 行首引标放行：「- [12] …」辖域＝「- 」符号串必死形——修一剥引标整行
    # 重判（agg_row 载体含 210）→零改写、引标收账。
    text, rewritten, cited, _split = verify_draft(
        "- [12] W-11 210 吨", [_agg_row_obs(12, "W-11", "210")]
    )
    assert rewritten == 0
    assert cited == [12]
    assert "- [12] W-11 210 吨" in text
    assert "未找到（材料未披露）" not in text


def test_verify_v254_t3_true_no_evidence_still_stamped() -> None:
    # T3 真无据照旧盖章（修三钉——行为零变化）：断言数字窗内零观察可寻→
    # 照旧盖「未找到（材料未披露）：」前缀（前缀逐字相等）。
    text, rewritten, cited, _split = verify_draft(
        "全油田年产液 999.9 万方 [1]", [_agg_row_obs(1, "N-01", "21.16")]
    )
    assert rewritten == 1
    assert cited == []
    assert "未找到（材料未披露）：全油田年产液 999.9 万方 [1]" in text


def test_verify_v254_t4_window_aligned_pass_not_credited() -> None:
    # T4 窗内对齐放行不计功（修二钉）：引标 [1] 自身观察不含 77.7（原支撑路径
    # 不过）、另一窗内观察含全部数字 → 行保留、cited 不增、改写数不增。
    observations = [
        _frag_carrier(1, "W-31 井检泵周期 512 天，卧式采油树。"),
        _frag_carrier(2, "12 月 W-51 井计划配注 77.7 方。"),
    ]
    text, rewritten, cited, _split = verify_draft(
        "12 月计划配注 77.7 方 [1]", observations
    )
    assert rewritten == 0
    assert cited == []  # 放行不计 cited——指歪的路牌不记功
    assert "12 月计划配注 77.7 方 [1]" in text
    assert "未找到（材料未披露）" not in text


def test_verify_v254_t5_citation_index_itself_not_evidence() -> None:
    # T5 引标序号不作数（防自证）：剥引标后断言零数字 → 窗内对齐恒不放行，
    # 照旧盖章（引标编号自身救不了无据断言）。
    text, rewritten, cited, _split = verify_draft(
        "该井为本年度标杆井 [1]", [_fragment_obs(1)]
    )
    assert rewritten == 1
    assert cited == []
    assert "未找到（材料未披露）：该井为本年度标杆井 [1]" in text


def test_verify_v254_t6_non_assertion_lines_regression() -> None:
    # T6 非断言行回归：无引标无数字行／空行照旧原样保留（零改写零前缀）。
    draft = "## 答案\n\n| 井号 | 日产油量 |\n|---|---|"
    text, rewritten, cited, _split = verify_draft(draft, [])
    assert rewritten == 0
    assert cited == []
    assert text == draft


def test_verify_v254_t7_existing_support_paths_zero_regression() -> None:
    # T7 既有支撑路径零回归（三面：正常辖域全数字复述判法／分源列明块／归属审
    # 块——行为零变化；既有测试全绿即证，本测为同面公开行为钉）。
    # ① 正常辖域全数值复述：非载体观察全部数值 token 被复述→行保留引标收账。
    plain = {
        "index": 1,
        "content": "W-11 井生产套管下深 2462.0 米",
        "source": "《A-W11井完井工程报告》",
        "source_id": "f-w11-1",
        "version": None,
        "freshness": "",
        "scope": "completion",
        "locator": {"kind": "table", "report": "《A-W11井完井工程报告》"},
    }
    text, rewritten, cited, split = verify_draft(
        "W-11 井生产套管下深 2462.0 米[1]。", [plain]
    )
    assert rewritten == 0 and cited == [1] and split is False
    assert "未找到（材料未披露）" not in text
    # ② 分源列明块：同 subject 值不同的两被引 fragment→INV-4 块照常追加。
    pair = [
        _frag_carrier(1, "自然递减率：4.6%（三季度）"),
        _frag_carrier(2, "自然递减率：6.1%（另一口径）"),
    ]
    text2, rewritten2, cited2, split2 = verify_draft(
        "自然递减率为 4.6% [1]，另一口径为 6.1% [2]。", pair
    )
    assert split2 is True and rewritten2 == 0 and cited2 == [1, 2]
    assert "多来源不一致——分源列明（禁止无出处调和）：" in text2
    # ③ 归属审块：anchors 非空且引标源与题眼对齐→零追加块（行为零变化）。
    text3, rewritten3, cited3, split3 = verify_draft(
        "W-11 井生产套管下深 2462.0 米[1]。", [plain], anchors=("W-11",)
    )
    assert rewritten3 == 0 and cited3 == [1] and split3 is False
    assert "跨源归属审" not in text3


# ---------- V2-69：占位符 [n] 串台治理（核验步剥占位符整行重判） ----------
# 病因＝答案指令占位符 [n] 被模型照抄进答案行；_CITE_RE 只认数字引标，行内又
# 无数字时该行被判「结构行」原样放行——核验 supported=0 照发（rag 题实锤）。
# 修＝行含 [n] 剥占位符整行重判：数字引标全支撑→保留并收账；窗内对齐→保留
# 不收账；仍无据→改写「未找到（材料未披露）：」（占位符不进答案面）。


def test_verify_v269_t1_placeholder_no_evidence_rewritten() -> None:
    # T1 占位符行无据：剥 [n] 后行内无数字（窗内对齐恒不放行、亦无数字引标）
    # →照旧盖章「未找到（材料未披露）：」，占位符不进答案面；改写计 1、零收账。
    text, rewritten, cited, _split = verify_draft(
        "术语表对「躺井」的定义：停产待检泵[n]",
        [_frag_carrier(1, "W-21 井本周期检泵周期 512 天。")],
    )
    assert rewritten == 1
    assert cited == []
    assert "未找到（材料未披露）：术语表对「躺井」的定义：停产待检泵" in text
    assert "[n]" not in text


def test_verify_v269_t2_placeholder_window_aligned_kept_not_credited() -> None:
    # T2 占位符行窗内对齐：剥 [n] 后断言数字（01/21.16）全在窗内观察 content
    # 出现→行保留（[n] 已剥）、放行不计 cited、改写数不增。
    text, rewritten, cited, _split = verify_draft(
        "N-01 井日产油量 21.16 吨[n]", [_agg_row_obs(1, "N-01", "21.16")]
    )
    assert rewritten == 0
    assert cited == []
    assert "N-01 井日产油量 21.16 吨" in text
    assert "[n]" not in text
    assert "未找到（材料未披露）" not in text


def test_verify_v269_t3_placeholder_mixed_numeric_citation_supported() -> None:
    # T3 占位符＋数字引标混合：[1][n] 连写——剥 [n] 后 [1] 辖域支撑（agg_row
    # 载体任一数值 token 重叠）→保留且 [n] 剥净、cited 收 1、改写数不增。
    text, rewritten, cited, _split = verify_draft(
        "合计 21.16 吨[1][n]", [_agg_row_obs(1, "N-01", "21.16")]
    )
    assert rewritten == 0
    assert cited == [1]
    assert "合计 21.16 吨[1]" in text
    assert "[n]" not in text
    assert "未找到（材料未披露）" not in text


def test_verify_v269_t4_zero_drift_numeric_support_rewrite_structural_line() -> None:
    # T4 零漂移锚（修三钉——行为零变化）：纯数字引标三形与改前一致（既有
    # V2-54 T2/T3/T6 同形即锚，本测为占位符分支旁路面的同形公开钉）。
    # ① 纯数字引标支撑：行保留＋引标收账。
    text1, rewritten1, cited1, _s1 = verify_draft(
        "N-01 井日产油量 21.16 吨[1]。", [_agg_row_obs(1, "N-01", "21.16")]
    )
    assert rewritten1 == 0 and cited1 == [1]
    assert "N-01 井日产油量 21.16 吨[1]。" in text1
    assert "未找到（材料未披露）" not in text1
    # ② 纯数字引标无据：照旧盖章（前缀逐字相等——悬空 [1] 照旧留存）。
    text2, rewritten2, cited2, _s2 = verify_draft(
        "全油田年产液 999.9 万方 [1]", [_agg_row_obs(1, "N-01", "21.16")]
    )
    assert rewritten2 == 1 and cited2 == []
    assert "未找到（材料未披露）：全油田年产液 999.9 万方 [1]" in text2
    # ③ 结构行（表头/分隔线）：无引标无数字→原样保留（零改写零前缀）。
    draft3 = "| 井号 | 日产油量 |\n|---|---|"
    text3, rewritten3, cited3, _s3 = verify_draft(draft3, [])
    assert rewritten3 == 0 and cited3 == [] and text3 == draft3


def test_verify_v269_t5_answer_instruction_citation_discipline_taught() -> None:
    # T5 指令教学钉：答案起草合同含「引用记号纪律」教学句（V2-69 逐字追加段
    # ——视野内有序号写序号、确无可引序号一个记号都不写、禁止占位符进答案）。
    assert "引用记号纪律" in _ANSWER_INSTRUCTION
    assert "禁止把本指令的占位符" in _ANSWER_INSTRUCTION
