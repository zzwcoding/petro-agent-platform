"""程序对象 ask 的恢复腿路由钉测（V2-82b · A13——真机 `run-3a5e7dba`／EB6 B-正6）。

**病灶取证**（`logs/llm_calls/20261017.jsonl` 该 run 的 9 次 decision 调用＋
`eval/results/frames/EB6-B-正6.json`）：程序判定 ask（对象歧义门）→ resume 选「都要（分源对比）」
→ 澄清分解 2 子问题被受理 → 前置条件机 s1（data 链「检泵周期」在册未绑定＝**换链触发**）与
s2（knowledge 链**放行**）**双 allow** → 状态本该「**可执行支先进批量**（部分结果先行）」却
**整组回炉①澄清**；回炉轮模型侧无回炉由头（增量条五件皆空）＋`discover` 被 `question_group`
在场禁掉＋零观察禁 `finalize` ⇒ 连烧轮预算、`citations` 空＝空交付。

**根因**＝`orchestration.graph._route_after_precondition` 把「本腿有新计点」当回炉判据（布尔），
**未按支排除换链触发支**——V1／recon `F-前置条件机.md` §11c（`chain_pending` 非空**且**
`executable` 空 → 回炉①）与 §11e（`executable` 非空 → 批量执行）两支被并成一支。修复后判据＝
`allow` 里排除**本次新触发者**：可执行支非空 → 批量执行；唯「纯触发组」才回炉①。

**同构断言**（`test_plain_ask_resume_leg_same_phase_sequence`）：普通澄清 ask（LLM 反问）恢复腿与
程序 ask 恢复腿的步序**逐条相同**——本病灶**不**是「程序 ask 专属恢复路径」（同一题走普通 ask
恢复腿同样复现、修复后同样出环进执行；两腿差只在**首腿**：程序 ask 腿零澄清 LLM 调用）。

素材链同产线：台账投影＝`v2_ledger_dump`（真快照）；油田实例读缝＝替身 raw 值集（生产＝
`query.production_field_instances`，归一同 `tools.oilfield_instances`）。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from appv2.infra.clock import freeze
from appv2.runtimev2.clarification.constants import ASK_KIND_CLARIFY
from appv2.runtimev2.context import wire_ledger_projection
from appv2.runtimev2.persistence import MemoryTables
from appv2.runtimev2.state import ALL_FIELDS_OPTION, ALL_FIELDS_SENTINEL
from appv2.runtimev2.state import AskChoice as V2AskChoice
from tests.domains.test_v2_four_phase import (
    V2LedgerPort,
    V2RunStore,
    v2_ask_frames,
    v2_data_match,
    v2_knowledge_match,
    v2_ledger_dump,
    v2_matches,
    v2_registry,
    v2_resume,
    v2_run,
    v2_runtime,
)
from tests.domains.test_v2_react_loop import _fragment_obs, _retrieval_with

# 题面（真机同题）：术语/指标「检泵周期」——台账 grain＝单井 ⇒ 对象歧义门要求主体
_QUESTION = "近三年 8 月平均检泵周期的变化趋势？"
_UNDERSTAND_NO_SUBJECT = json.dumps(
    {
        "route": "full",
        "text": "理解：问近三年各月平均检泵周期的变化趋势。",
        "metric_candidates": ["检泵周期"],
        "subjects": [],
        "terms": ["检泵周期"],
    },
    ensure_ascii=False,
)

_NOTES = "检泵周期｜未绑定｜2024-08-01~2026-09-01"


def _decompose(*subtasks: dict[str, Any]) -> str:
    return json.dumps(
        {"action": "decompose", "question_group": {"subtasks": list(subtasks)}},
        ensure_ascii=False,
    )


# r1 混合组（真机同形）：s1＝data 链「检泵周期」（在册未绑定 ⇒ 换链触发）；s2＝knowledge 链
_DECOMPOSE_R1 = _decompose(
    {
        "id": "s1",
        "question": "近三年 8 月平均检泵周期是多少？",
        "ledger_notes": _NOTES,
        "chain": "data",
        "tool": "data_query",
    },
    {
        "id": "s2",
        "question": "近三年 8 月平均检泵周期的变化趋势，报告里怎么说？",
        "ledger_notes": _NOTES,
        "chain": "knowledge",
        "tool": "doc_retrieve",
    },
)
# r2 回炉（V1 同款：触发支随失败子集回炉①改链重决策——s1 换 knowledge 链，同 id 只留最新）
_DECOMPOSE_R2 = _decompose(
    {
        "id": "s1",
        "question": "近三年 8 月平均检泵周期（据拒因提示换检索链）",
        "ledger_notes": _NOTES,
        "chain": "knowledge",
        "tool": "doc_retrieve",
    }
)


def _matches_r1() -> str:
    return v2_matches(
        v2_data_match(subtask_id="s1", slot="检泵周期", start="2024-08-01", end="2026-09-01"),
        v2_knowledge_match(subtask_id="s2", question="近三年 8 月平均检泵周期趋势"),
    )


def _matches_r2() -> str:
    return v2_matches(
        v2_knowledge_match(subtask_id="s1", question="近三年 8 月平均检泵周期（换链后检索）")
    )


# 普通澄清 ask（LLM 反问）腿的发射——同构对照用（同一题、同一后续剧本）
_LLM_ASK = json.dumps(
    {
        "action": "ask",
        "ask": {"prompt": "要查哪个油田？", "options": ["渤中油田", "渤南油田"]},
    },
    ensure_ascii=False,
)

_ANSWER = "s1：近三年 8 月平均检泵周期据月报所载 [1]；s2：同源趋势材料 [1]。"


def _raw_face() -> tuple[str, ...]:
    """油田实例读缝（生产读面原形：raw 值集——归一归编排侧 tools 面）。"""
    return ("渤中油田", "渤南油田", "渤西油田")


def _script(*, decision: Sequence[str], understand: Sequence[str]) -> dict[str, Sequence[str]]:
    return {"understand": list(understand), "decision": list(decision), "answer": [_ANSWER]}


def _decision_script(extra_first: str | None = None) -> list[str]:
    """决策剧本：r1（分解＋匹配）→ r2（回炉分解＋匹配）；`extra_first`＝普通腿首腿的 LLM 反问。"""
    items = [_DECOMPOSE_R1, _matches_r1(), _DECOMPOSE_R2, _matches_r2()]
    return items if extra_first is None else [extra_first, *items]


def _retrieval() -> Any:
    return _retrieval_with(
        _fragment_obs(
            "渤中油田近三年 8 月平均检泵周期据月报所载（2024-08／2025-08／2026-08）。",
            "frag-jbq",
        )
    )


def _steps_of(run_id: str) -> list[Any]:
    return V2RunStore().steps(run_id)


def _execute_rows(run_id: str) -> list[tuple[str, str]]:
    """执行步（子问题 → 状态）——批量执行真被触达的机读面（非执行步不列）。"""
    rows: list[tuple[str, str]] = []
    for row in _steps_of(run_id):
        payload = row.payload or {}
        if row.step != "execute" or not payload.get("subtask_id"):
            continue
        rows.append((str(payload["subtask_id"]), str(payload.get("status") or "")))
    return rows


def _phase_after_precondition(run_id: str) -> str:
    """前置条件机（末条）之后的首个相位（步 payload 的 `phase`）——「出环去哪」的机读面。

    无相位（模型调用步）——回炉轮的字段面，如实回 `model`。
    """
    rows = _steps_of(run_id)
    index = max(
        idx
        for idx, row in enumerate(rows)
        if (row.payload or {}).get("phase") == "precondition"
    )
    for row in rows[index + 1 :]:
        payload = row.payload or {}
        phase = payload.get("phase")
        if phase:
            return str(phase)
        if row.title.startswith("模型调用"):
            return "model"
    return ""


def _resume_leg_titles(run_id: str) -> list[str]:
    """恢复腿步序（`澄清回收` 步起算——挂起腿与恢复腿的分界，跨腿比较用）。

    回收步 title 携用户所选原话（两腿选择不同文本），故该步归一为定值后再比（比较的是相位序）。
    """
    titles = [str(row.title) for row in _steps_of(run_id)]
    start = next(
        (index for index, title in enumerate(titles) if title.startswith("澄清回收")), None
    )
    assert start is not None, titles
    return ["澄清回收", *titles[start + 1 :]]


async def _run_subject_ask_leg(tables: Any) -> tuple[str, dict[str, Any], Any, Any]:
    """程序 ask 腿：理解（无主体）→ 弹 ask（零澄清 LLM）→ resume 选「都要（分源对比）」→ 跑完。"""
    retrieval = _retrieval()
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=_script(decision=_decision_script(), understand=[_UNDERSTAND_NO_SUBJECT]),
            registry=v2_registry(retrieval=retrieval),
            field_instances=_raw_face,
            tables=tables,
        )
        events = await v2_run(runtime, _QUESTION)
        frames = v2_ask_frames(events)
        assert len(frames) == 1  # 程序判定 ask（一次也不发起澄清 LLM）
        assert completer.counts() == {"understand": 1}
        run_id = frames[0]["run_id"]
        await v2_resume(runtime, run_id, V2AskChoice(kind="clarify", choice=ALL_FIELDS_OPTION))
    return run_id, frames[0]["frame"], completer, retrieval


async def test_subject_ask_resume_mixed_group_exits_to_execution() -> None:
    """A13 主钉：程序 ask 恢复腿遇「换链触发支＋可执行支」混合组 → **出环进批量执行**，非空交付。

    四面断言：①前置条件机之后**首个相位＝execution**（V1「部分结果先行」——不再整组回炉①），
    可执行支 s2 真执行；②触发支 s1 随批量回炉一次（bad_args ⇒ 换 knowledge 链）后真执行、同 id
    只留最新，两支结果都进汇总；③恢复腿决策调用恰 4 次＝两轮×两发（零烧轮；真机病灶的形态是
    前置条件机之后连烧 3 轮澄清、零材料收口）；④收口 `completed`、`answer` 非空、`citations`
    非空（非空交付）。
    """
    subject_run, frame, completer, retrieval = await _run_subject_ask_leg(MemoryTables())

    # 挂起帧四键齐备（transport 把守的既有形状）＋选项＝示例实例＋「都要」
    assert set(frame) == {"kind", "prompt", "options", "detail"}
    assert frame["kind"] == ASK_KIND_CLARIFY
    assert frame["options"] == ["渤中油田", "渤南油田", "渤西油田", ALL_FIELDS_OPTION]

    state = V2RunStore().load(subject_run)
    assert state.subjects == (ALL_FIELDS_SENTINEL,)  # 恢复腿映射（票面产物面）
    assert state.pending_subject_options == ()

    # ①出环进执行：前置条件机之后首个相位＝execution（可执行支 s2 与触发支 s1 同批执行）
    assert _phase_after_precondition(subject_run) == "execution"
    assert _execute_rows(subject_run) == [
        ("s1", "failed"),  # r1：触发支照 allow 进批量（引擎绑定校验拒——如实留痕）
        ("s2", "ok"),  # r1：可执行支真检索（部分结果先行）
        ("s1", "ok"),  # r2：换链后真检索
    ]
    assert retrieval.retrieve_calls == 2  # r1 的 s2 ＋ r2 的 s1
    results = {row["id"]: row["status"] for row in state.subtask_results}
    assert results == {"s1": "ok", "s2": "ok"}  # 同 id 只留最新（回炉后 s1 账目覆盖 r1）

    # ②零烧轮：恢复腿决策调用恰 4 次（r1 分解＋匹配、r2 回炉分解＋匹配）；作答恰一发
    assert completer.counts() == {"understand": 1, "decision": 4, "answer": 1}
    assert [row.title for row in _steps_of(subject_run) if "被拒" in str(row.title)] == []

    # ③非空交付
    answer_rows = [row for row in _steps_of(subject_run) if row.step == "answer"]
    assert answer_rows and answer_rows[-1].payload["citations"]
    assert state.status == "completed"
    assert state.answer and state.answer.strip()
    assert state.observations  # 材料面非空（非「零材料」收敛壳）


async def test_plain_ask_resume_leg_same_phase_sequence() -> None:
    """同构钉：普通澄清 ask（LLM 反问）恢复腿与程序 ask 恢复腿**步序逐条相同**。

    本病灶不在「程序 ask 专属恢复路径」——同一题走普通 ask 恢复腿同样复现（修复前两者都整组回炉
    烧轮）；两腿差只在首腿：程序 ask 腿零澄清 LLM 调用，普通 ask 腿首腿多一次澄清决策调用。
    """
    tables = MemoryTables()
    subject_run, _frame, _completer, _retrieval_engine = await _run_subject_ask_leg(tables)

    retrieval = _retrieval()
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=_script(
                decision=_decision_script(extra_first=_LLM_ASK),
                understand=[_UNDERSTAND_NO_SUBJECT],
            ),
            registry=v2_registry(retrieval=retrieval),
            tables=tables,
        )  # field_instances 缺省＝程序门不出声（普通 LLM 反问腿）
        events = await v2_run(runtime, _QUESTION)
        frames = v2_ask_frames(events)
        assert frames and frames[-1]["frame"]["kind"] == ASK_KIND_CLARIFY
        plain_run = frames[-1]["run_id"]
        await v2_resume(runtime, plain_run, V2AskChoice(kind="clarify", choice="渤南油田"))

    assert _resume_leg_titles(subject_run) == _resume_leg_titles(plain_run)
    assert _phase_after_precondition(plain_run) == "execution"
    assert _execute_rows(plain_run) == [("s1", "failed"), ("s2", "ok"), ("s1", "ok")]
    assert V2RunStore().load(plain_run).status == "completed"
    # 首腿多一次澄清决策调用（LLM 反问）
    assert completer.counts() == {"understand": 1, "decision": 5, "answer": 1}
