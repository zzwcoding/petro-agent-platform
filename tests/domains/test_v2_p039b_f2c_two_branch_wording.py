"""P-039b/V2-42 F2c 措辞两分支校准钉测（票面四验收的钉面）。

背景（P-039 批 16 题数-反1 ✅→❌ 归因——疑点①裁决：措辞再修非判分口径）：
附 2 末句「无时间词的数据链问题＝默认近 30 天直发，禁反问时间窗」一刀切，
把拍板⑥「模糊时间词→缺参反问」合法路径锁死。V2-42 校准＝末句整句替换为
两分支拆开稿（只许替换末句，其余一字不动——V2-41 施工红线不破）。

票面验收钉测落点：
- 替换逐字（char 相等）：附 2 末句＝V2-42 票面稿（char-level 全等）＋旧末句
  整句退场（无双合同面）；
- 现有合同措辞零删改钉：新末句还原回旧末句＝P-039 版 CLARIFY_CONTRACT 全文
  char-level 全等（「只许替换末句，其余一字不动」的机检形）；
- 数-反1 剧本钉：模糊时间词（最近）＝窗双 null 发射——clarify 零反问、零直发，
  引擎缺参反问兜底（ASKBACK_TIME_QUESTION 三选一帧在场）→resume 收口；
- A-正7 形钉：无时间词默认近 30 天锚定直发零反问（不回退——两分支不得混淆）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from appv2.query import (
    ASKBACK_TIME_CHOICES,
    ASKBACK_TIME_QUESTION,
    QueryOutcome,
)
from appv2.runtime import AskChoice, AskRequest, RunStore
from appv2.runtime.guide import CLARIFY_CONTRACT
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    drain,
    make_runtime,
)
from tests.domains.test_v2_four_phase import (
    LEDGER_DUMP,
    FourPhaseEngine,
    _step_payloads,
)
from tests.domains.test_v2_r1c_window_recall import RECALL_CLAUSE
from tests.domains.test_v2_react_loop import _rows_outcome

# ---------- V2-42 票面逐字稿（char 相等基准——增删一字即红） ----------

# tickets/v2/V2-42-F2c措辞两分支校准.md「整句替换为」引块去折行逐字（char 相等）。
V2_42_LAST_SENTENCE = (
    "无时间词的数据链问题＝默认近 30 天直发，禁反问时间窗；模糊时间词（最近/"
    "近期/前段时间类）＝窗双 null 发射，由引擎缺参反问兜底（三选一合法形，"
    "拍板⑥）——两分支不得混淆。"
)

# P-039 版附 2 末句（被整句替换退场的旧句——零删改钉的还原件）。
P039_OLD_LAST_SENTENCE = (
    "无时间词的数据链问题＝默认近 30 天直发，禁反问时间窗（窗双 null 由引擎缺参反问兜底）。"
)

# ---------- V2-52 辅助模式合同改型面（P-051b——零删改钉的随动还原件） ----------

# V2-52 附 A 目录逐字稿＋finalize 直答行（追加段——还原时整段剥除；与
# guide.py 施工基准同源，char 相等。V2-53 随动：faq 尾行与 finalize 直答行
# 按 V2-53 附 A 逐字稿改型，本件随之更新——剥除还原法不变）。
V252_DIRECTORY_AND_FINALIZE = (
    "可用探查（discover，全 run ≤10 次，已用 {discover_used} 次）：\n"
    "- semantic_query：本体口径/绑定/届满细节钻取（开局台账已全量，仅细节用）\n"
    "- table_schema：表结构钻取（agg/sem/kb 分区）\n"
    "- faq_lookup：FAQ 现成问答库——问句有现成标准答案时加速/互证；\n"
    "  命中条目作观察材料进上下文——有探查观察在场方可 finalize，不够继续检索\n"
    '- 定稿直答：{"action": "finalize"}——仅当本 run 已有探查观察'
    "（discover 命中条目）时可用：系统按观察材料起草带引用的答案"
    "（秒答形，不走检索执行）。零探查观察发射 finalize＝非法发射，程序拒回并要求改发。"
    "台账常驻注入是字典不是数据——指标/术语在台账＝知道名字与定义，不等于数值在手，"
    "注入不进交付面；要数值先 discover 钻取或 decompose 分解走检索执行。\n"
)

# 钻取行改型（发射闭世界升三工具＋预算语移入目录头——还原回 P-039 两工具形）。
V252_DISCOVER_LINE = (
    '- 钻取：{"action": "discover", "discovers": [{"tool": "semantic_query"|'
    '"table_schema"|"faq_lookup", "args": {...}}]}——1~2 支。开局已给全台账，'
    "禁猜词敲门：只作口径/绑定细节钻取，不答「能不能出数」。\n"
)
P039_DISCOVER_LINE = (
    '- 钻取：{"action": "discover", "discovers": [{"tool": "semantic_query"|'
    '"table_schema", "args": {...}}]}——1~2 支；全 run ≤{max_discover_run} 次'
    "（已用 {discover_used} 次）。开局已给全台账，禁猜词敲门：只作口径/绑定细节"
    "钻取，不答「能不能出数」。\n"
)

# P-039 版 CLARIFY_CONTRACT 全文（master adb4321 appv2/runtime/guide.py 逐字取下
# ——零删改钉的还原基准：现合同把新末句还原回旧末句必须与它 char-level 全等）。
P039_CLARIFY_CONTRACT = (
    "【相位①·业务澄清】只输出一个 JSON 对象（可围栏）。三动作：\n"
    '- 分解：{"action": "decompose", "question_group": {"subtasks": '
    '[{"id": "s1", "question": "子问题原文", "ledger_notes": "〈精确指标 slot 名〉'
    '〈绑定态〉〈锚定窗〉", "chain": "data"|"knowledge", "tool": '
    '"data_query"|"doc_retrieve"}]}}——子问题 ≤{max_subtasks} 个；每个子问题可独立'
    "映射一条工具链（粒度＝一个指标×一个窗×一个对象集）；单一诉求不分解（单子"
    "问题组）；ledger_notes 必带——从下方台账全量块逐字转抄，不改写不杜撰。\n"
    '- 钻取：{"action": "discover", "discovers": [{"tool": "semantic_query"|'
    '"table_schema", "args": {...}}]}——1~2 支；全 run ≤{max_discover_run} 次'
    "（已用 {discover_used} 次）。开局已给全台账，禁猜词敲门：只作口径/绑定细节"
    "钻取，不答「能不能出数」。\n"
    '- 反问：{"action": "ask", "ask": {"prompt": "...", "options": ["…"]}}'
    "——2~4 个选项；仅限两种白场：无场景词＋阈值判断形（口径支待用户选），"
    "或目标/对象/口径真歧义（用户补一句话即可解——拍板⑥澄清分级②）。\n"
    "发射判据：台账命中＋窗已定＝分解完毕，禁再 discover；对称面——窗可锚定＝"
    "禁 ask（时间词按窗词锚定表可解析即锚定发射；无时间词→默认近 30 天；模糊"
    "时间词→窗双 null 发射由引擎缺参反问；窗内无数据由引擎新鲜度闸拦停/改绑并"
    "注记——不预判、不对窗/粒度反问）。\n"
    "knowledge 链规则：问文档所载内容（非台账指标的数值取数）＝单子问题组直发"
    "（chain=knowledge, tool=doc_retrieve）——不问范围、不问载体（全库检索"
    "是合同口径，路由建议已代选库）、不问口径支；口径支歧义不归本相位——"
    "由前置条件机按 caliber_key 三态处理（双口径并列或阈值反问）；检索式"
    "问题没有「窗」概念——缺窗不是歧义、不构成反问白场；无时间词的数据链"
    "问题＝默认近 30 天直发，禁反问时间窗（窗双 null 由引擎缺参反问兜底）。"
)


def test_v242_last_sentence_replaced_verbatim_char_equal() -> None:
    """验收①替换逐字（char 相等）：附 2 末句＝V2-42 票面稿；旧末句整句退场。

    位置随动（V2-46 R1c——P-045 派工单批准的回捞白场逐字稿追加在合同尾部）：
    本句不再是合同末句，但仍在 R1c 追加段之前（追加不插入既有段）。"""
    assert V2_42_LAST_SENTENCE in CLARIFY_CONTRACT  # 替换稿逐字在场
    assert len(V2_42_LAST_SENTENCE) == 90  # 票面稿字数（char 相等的计数面）
    assert P039_OLD_LAST_SENTENCE not in CLARIFY_CONTRACT  # 旧末句退场（无双合同面）
    # 追加不插入：V2-42 末句在前、V2-46 回捞白场逐字稿收尾。
    assert CLARIFY_CONTRACT.index(V2_42_LAST_SENTENCE) < CLARIFY_CONTRACT.index(
        RECALL_CLAUSE
    )
    assert CLARIFY_CONTRACT.endswith(RECALL_CLAUSE)


def test_v242_zero_deletion_restoring_old_sentence_reproduces_p039() -> None:
    """验收①零删改钉（V2-52 随动升版——P-051b 辅助模式返工的合法合同变更）：
    新末句还原回旧末句＋剥 V2-52 目录/finalize 追加段＋钻取行还原两工具形＋
    四动作还原三动作＋剥 V2-46 回捞白场追加段＝P-039 版合同全文 char-level
    全等。受保护面不变：knowledge 链规则/发射判据/反问白场段一字不动——V2-52
    改型只许落在动作闭世界行/钻取行/目录与 finalize 追加段。"""
    restored = (
        CLARIFY_CONTRACT.replace(V2_42_LAST_SENTENCE, P039_OLD_LAST_SENTENCE)
        .replace(V252_DIRECTORY_AND_FINALIZE, "")
        .replace(V252_DISCOVER_LINE, P039_DISCOVER_LINE)
        .replace("四动作：", "三动作：")
    )
    assert restored.removesuffix(RECALL_CLAUSE) == P039_CLARIFY_CONTRACT
    assert len(P039_CLARIFY_CONTRACT) == 1066  # P-039 版合同字数不变（基准面）


def test_v242_two_branch_wording_both_present() -> None:
    """两分支措辞各就各位：无时间词默认锚定面不回退＋模糊时间词发射面新增。"""
    assert "无时间词的数据链问题＝默认近 30 天直发，禁反问时间窗" in CLARIFY_CONTRACT
    assert "模糊时间词（最近/近期/前段时间类）＝窗双 null 发射" in CLARIFY_CONTRACT
    assert "由引擎缺参反问兜底（三选一合法形，拍板⑥）" in CLARIFY_CONTRACT
    assert "两分支不得混淆" in CLARIFY_CONTRACT


# ---------- 数-反1 剧本钉（验收②——模糊时间词零直发→反问帧在场） ----------

_UNDERSTAND = "理解：数据问句。\n指标候选：日产油量"


async def _run_all(runtime: Any, question: str) -> list[Any]:
    handle = await runtime.ask(AskRequest(question=question, actor=ACTOR))
    return await drain(handle)


async def test_v242_fuzzy_time_word_window_null_askback_frame_present(
    tmp_path: Path,
) -> None:
    """数-反1 剧本钉：「最近」＝窗双 null 发射——clarify 零反问、零直发，
    引擎缺参反问兜底（三选一合法形帧在场）；resume 选窗收口。"""
    engine = FourPhaseEngine([
        QueryOutcome.need_clarify(
            question=ASKBACK_TIME_QUESTION, choices=ASKBACK_TIME_CHOICES
        ),
        _rows_outcome(),
    ])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "最近各井日产油量怎么样？",
             "ledger_notes": "日产油量｜bound｜模糊时间词——窗双 null 发射（V2-42）",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": None, "window_end": None},
    }]}, ensure_ascii=False)
    clarify_r2 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "近 30 天各井日产油量",
             "ledger_notes": "日产油量｜bound｜窗已答（近 30 天）", "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r2 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1, clarify_r2, toolmatch_r2],
        "v2.runtime.answer": ["N-01 21.16[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "最近各井日产油量怎么样？")
        asks = [e.data for e in events if e.event == "ask"]
        assert asks, "模糊时间词零反问——数-反1 形复现（直发＝❌）"
        assert asks[-1]["frame"]["prompt"] == ASKBACK_TIME_QUESTION  # 引擎兜底（非 clarify 反问）
        assert asks[-1]["frame"]["options"] == list(ASKBACK_TIME_CHOICES)  # 三选一合法形（拍板⑥）
        # 零直发：挂起态在场（ask 后无终稿——run 停 waiting_ask）。
        store = RunStore(db)
        run_row = await store.get_run(asks[-1]["run_id"])
        assert run_row is not None and run_row.status == "waiting_ask"
        steps = await store.list_steps(asks[-1]["run_id"])
        clarify_steps = _step_payloads(steps, "clarify")
        assert clarify_steps[0]["emission"]["action"] == "decompose"  # clarify 未反问窗
        toolmatch = _step_payloads(steps, "toolmatch")[0]
        plan = toolmatch["emission"]["matches"][0]["plan"]
        assert plan["window_start"] is None and plan["window_end"] is None  # 窗双 null 发射
        # 用户选定窗——续跑收口（答案册：resume 后行为如实记录不判）。
        handle = await runtime.resume(asks[-1]["run_id"], AskChoice(value="近 30 天"))
        events2 = await drain(handle)
        assert events2[-1].data["status"] == "completed"
    finally:
        await db.dispose()


async def test_v242_no_time_word_default_window_direct_dispatch(tmp_path: Path) -> None:
    """A-正7 形钉：无时间词＝默认近 30 天锚定直发——零 ask 帧完成（不回退）。"""
    engine = FourPhaseEngine([_rows_outcome()])
    clarify_r1 = json.dumps({
        "action": "decompose",
        "question_group": {"subtasks": [
            {"id": "s1", "question": "各井日产油量是多少？",
             "ledger_notes": "日产油量｜bound｜无时间词——默认近 30 天直发（V2-42）",
             "chain": "data"},
        ]},
    }, ensure_ascii=False)
    toolmatch_r1 = json.dumps({"matches": [{
        "id": "s1", "chain": "data", "tool": "data_query", "plan": {
            "metric_slot": "日产油量", "ranking": False,
            "window_start": "2026-08-01", "window_end": "2026-08-31"},
    }]}, ensure_ascii=False)
    script: dict[str, Sequence[str]] = {
        "v2.runtime.understand": [_UNDERSTAND],
        "v2.runtime.decision": [clarify_r1, toolmatch_r1],
        "v2.runtime.answer": ["N-01 21.16[1]。"],
    }
    runtime, _completer, db = await make_runtime(
        tmp_path, engine=engine, script=script,
        four_phase=True, ledger_dump=lambda: dict(LEDGER_DUMP),
    )
    try:
        events = await _run_all(runtime, "各井日产油量是多少？")
        assert events[-1].data["status"] == "completed"
        assert not [e for e in events if e.event == "ask"], "无时间词题出现反问帧（A-正7 形回退）"
        assert engine.run_calls == 1  # 默认窗锚定直发（引擎真执行一次）
        store = RunStore(db)
        toolmatch = _step_payloads(
            await store.list_steps(events[-1].data["run_id"]), "toolmatch"
        )[0]
        plan = toolmatch["emission"]["matches"][0]["plan"]
        assert plan["window_start"] == "2026-08-01"  # 默认近 30 天锚定（非窗双 null）
        assert plan["window_end"] == "2026-08-31"
    finally:
        await db.dispose()
