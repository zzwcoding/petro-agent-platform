"""F2 收敛面缺陷回归（2026-10-17）——预算触界带材料直答（两件之一）。

真源：`specs/agent-loop.md` 行为 7（触界即收敛的**零材料兜底轮**，2026-10-17 F2 补）＋
`specs/bookkeeping.md` 行为 12／13（收敛落地面与材料面同源）。

真机证据（两帧＝EB4 终判「新病灶 2：预算触界零交付×2」）：

- `eval/results/frames/EB4-A-正8.json`（`run-13c166e9`；题面见本件 `F2_A8_QUESTION`）：
  澄清 r1／r2／r3 三发连拒（每次拒因照耗轮）→ `rounds` 顶到上限 3 → 澄清入口就地收敛 → 材料面为零
  → 交付只剩「（预算触界收敛——rounds；未取得可交付材料，如实说明；材料清单：无）」——整题空答
  （同题 EB3 有交付：检索走通、23 条观察逐条交付）。
- `eval/results/frames/EB4-D-诱10.json`（`run-b7df65f5`；题面见 `F2_DY10_QUESTION`）：同形（澄清
  r1／r2／r3 三发连拒→到顶→零材料纯话术）。

根因＝**收敛发生的时刻**：两个形都死在「澄清相位拒因回炉吃满轮预算、run 尚未执行任何工具」——
熔断形之所以「带已获材料直答」，只因它在工具匹配相位之后触界（材料已在手）；收敛渲染面本身两形
同源（`bookkeeping.converge`），有材料时逐条如实交付（旧形帧 `P024BW-数-*` 即此形）。**修法**
（`orchestration/graph._material_round_due`）＝到顶那一次**让位恰一轮**（上一发被拒＝有回喂可用的
重决策机会），让 run 先把这一轮跑完取材料；有材料时照旧就地收敛（带材料直答）；仍拒＝`rounds`
超顶 → 收敛（**恰一轮**上界）。
"""

from __future__ import annotations

from typing import Any

from appv2.infra.clock import freeze
from appv2.runtimev2.bookkeeping import converge
from appv2.runtimev2.orchestration.graph import _material_round_due
from appv2.runtimev2.persistence import RunStore as V2RunStore
from appv2.runtimev2.state import Budget, RunState, check_limits
from tests.domains.test_v2_four_phase import (
    V2_UNDERSTAND,
    V2LedgerPort,
    V2QueueEngine,
    v2_data_match,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
    wire_ledger_projection,
)
from tests.domains.test_v2_react_loop import _rows_outcome

# ── 题面原句（逐字取自两帧 blackbox 记录——不改造、不缩写）────────────────────────
F2_A8_QUESTION = "邻井 W-07 井初期日产油多少？现在呢？"
F2_DY10_QUESTION = (
    "有人说渤中34-5 油田三季度自然递减率是 6.1%、综合递减率是 4.6%，对吗？"
    "这两项同比各变了多少个百分点？分别是什么原因？"
)
# 真机拒因原话（`eval/results/frames/EB4-A-正8.json` 步标题逐字节选）
F2_R3_REJECT_TITLE = "action 缺失或越界（ask/decompose/discover/finalize 四值）：None"
F2_CAP = 3
_F2_BAD_NOTE = "不存在的指标名｜已绑定｜2025-09-01~2025-09-03"  # 槽位对账未过（真机 r1 形）
_F2_OUT_OF_WORLD = '{"action": "fly"}'  # 发射越界（真机 r3 形——照耗轮）
_F2_ANSWER = "s1：N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"
F2_MATERIAL_TEXT = "21.16"
# ── NQ-M3 帧原话（F2 第二件；逐字同 `tests/domains/test_v2_understanding.py` 的同形面）────────
# 题面原句取自 `eval/results/frames/EB4-NQ-M3.json` blackbox；应答原话取自
# `logs/llm_calls/20261017.jsonl` `run-e318723a`（两次 understand 记录逐字同形＝**围栏包裹**）
F2_NQ_M3_QUESTION = (
    '"本油田本月电潜泵生产井的躺井井次和检泵作业井次分别是多少？请从第一章和第二章分别给出。"'
    "若报告中不存在该口径，请引用报告明示的句子说明前提为什么不成立，并说明本月的躺井井次、"
    "检泵作业井次实际发生在什么井型上。"
)
_F2_NQ_M3_RAW = (
    "```json\n"
    '{"route": "full", "text": "理解：问本油田本月电潜泵生产井的躺井井次和检泵作业井次各是多少，'
    "要求从第一章和第二章分别给出；若报告中不存在该口径，则引用报告明示句子说明前提不成立，"
    '并说明本月躺井井次与检泵作业井次实际发生在什么井型上。", "metric_candidates": []}\n'
    "```"
)


def _cap_state(**overrides: Any) -> RunState:
    """触界态 fixture：轮数到顶（`rounds == Budget.rounds`）＋上一发被拒（拒因回喂在场）。"""
    values: dict[str, Any] = {
        "run_id": "run-f2-01",
        "question": F2_A8_QUESTION,
        "actor": "laowang",
        "budget": Budget(rounds=F2_CAP),
        "rounds": F2_CAP,
        "decision_error": f"澄清 r3 被拒：{F2_R3_REJECT_TITLE}",
    }
    values.update(overrides)
    return RunState(**values)


def _converged_answer(**overrides: Any) -> str:
    """同形快照另起一份跑一次收敛落地，取正文（材料面与兜底判据的**同源**对读面）。"""
    clone = _cap_state(**overrides)
    converge(clone)
    return clone.answer


def _decision_script() -> list[str]:
    """真机形剧本：三发连拒（照耗轮，`rounds` 到顶）＋兜底轮改对（拒因回喂后分解定案）＋匹配。"""
    note = v2_ledger_note(v2_ledger_dump(), "日产油量")
    return [
        v2_decompose(
            subtask_id="s1", question="各井日产油量", ledger_notes=_F2_BAD_NOTE, chain="data"
        ),
        _F2_OUT_OF_WORLD,
        _F2_OUT_OF_WORLD,
        v2_decompose(
            subtask_id="s1",
            question="2025-09-01 到 09-03 各井日产油量",
            ledger_notes=note,
            chain="data",
        ),
        v2_matches(
            v2_data_match(subtask_id="s1", slot="日产油量", start="2025-09-01", end="2025-09-03")
        ),
    ]


def _wire_ledger() -> None:
    wire_ledger_projection(V2LedgerPort(v2_ledger_dump()))


def _obs_row(source_id: str) -> dict[str, Any]:
    """已入栈观察行（材料面第一来源的最小形：`source_id` ＋ `content`）。"""
    return {"source_id": source_id, "content": f"N-01 井 {F2_MATERIAL_TEXT} 吨"}


def _carried_result(source_id: str) -> dict[str, Any]:
    """末次工具结果投影（材料面第二来源：结果自带 `observations`）。"""
    return {
        "status": "ok",
        "observations": [{"source_id": source_id, "content": f"Y-23 井 {F2_MATERIAL_TEXT}"}],
        "ask": None,
        "error": None,
    }


# ---------- 1 判据面：零材料兜底轮四判据 ＋ 材料面同源 ----------


def test_f2_material_round_judgement_four_criteria() -> None:
    """`_material_round_due` 四判据（全中才让位）——面面皆有其反面可判。

    ①拒因回炉入口（`decision_error` 在场）②零材料 ③上一发照耗轮（`budget_reject_streak == 0`）
    ④仅轮数键命中且恰好到顶。反面逐一：非回炉入口（零预算形＝首入即触界）／有材料／免轮拒／
    段时长硬闸同命中／超顶（兜底轮已给过）。
    """
    base = _cap_state()
    assert _material_round_due(base, check_limits(base)) is True
    # ① 非回炉入口（零预算形＝首入即触界）不让位
    fresh = _cap_state(decision_error="")
    assert _material_round_due(fresh, check_limits(fresh)) is False
    # ② 有材料（已入栈观察）不让位
    with_obs = _cap_state(observations=[_obs_row("src-obs-1")])
    assert _material_round_due(with_obs, check_limits(with_obs)) is False
    # ②′ 材料面第二来源（末次工具结果自带观察）同判
    with_carried = _cap_state(last_result=_carried_result("src-last-1"))
    assert _material_round_due(with_carried, check_limits(with_carried)) is False
    # ③ 免轮拒（首拒免轮三类）不欠轮 → 不让位（兼钉「恰一轮」上界）
    free = _cap_state(budget_reject_streak=1)
    assert _material_round_due(free, check_limits(free)) is False
    # ④′ 段时长硬闸同命中 → 不让位
    both = _cap_state(budget=Budget(rounds=F2_CAP, seconds=1.0))
    two_hits = check_limits(both, elapsed_seconds=5.0)
    assert [hit.limit for hit in two_hits.hit] == ["rounds", "seconds"]
    assert _material_round_due(both, two_hits) is False
    # ④″ 已超顶（兜底轮已给过）→ 收敛
    over = _cap_state(rounds=F2_CAP + 1)
    assert _material_round_due(over, check_limits(over)) is False


def test_f2_material_face_co_sourced() -> None:
    """材料面**同源**（不漂移）：兜底判据的「有／无」↔ 收敛正文的材料清单，两处同判。

    三形逐一（零材料／已入栈观察／末次工具结果自带观察）：判据判「无」时正文报「材料清单：无」；
    判据判「有」时正文**逐条如实交付**该材料（正文与注记两处的标识集合仍由 `bookkeeping` 单点
    生成——本件只钉「两处对同一状态给同一是非」）。
    """
    assert "材料清单：无" in _converged_answer()
    obs_answer = _converged_answer(observations=[_obs_row("src-obs-1")])
    assert "已取得材料 1 条" in obs_answer and "src-obs-1" in obs_answer
    assert F2_MATERIAL_TEXT in obs_answer
    carried_answer = _converged_answer(last_result=_carried_result("src-last-1"))
    assert "src-last-1" in carried_answer


# ---------- 2 真机形重演：预算触界不再空答 ----------


async def test_f2_a8_shape_cap_grace_round_delivers_material() -> None:
    """A-正8 形重演（澄清三发连拒吃满轮预算→零材料）→ 兜底轮跑完 → `completed` **有正文带材料**。

    剧本形逐点对齐真机（`EB4-A-正8.json`）：澄清 r1 槽位对账未过（照耗轮）→ r2／r3 发射越界
    （照耗轮，`rounds` 到顶）→ **兜底轮**（带拒因回喂改对）分解定案 → 工具匹配 → 前置 → 执行取数。
    判据：零 `budget_converged`（旧形死点）、正文非纯收敛话术、材料（工具观察帧＋入栈观察）在场。
    """
    _wire_ledger()
    script = {"understand": [V2_UNDERSTAND], "decision": _decision_script(), "answer": [_F2_ANSWER]}
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(
            script=script,
            registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
            budget=Budget(rounds=F2_CAP),
        )
        events = await v2_run(runtime, F2_A8_QUESTION)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    answer = V2RunStore().run(run_id).answer or ""
    # ① 收敛**未发生**：兜底轮把这一轮跑完（旧形此处＝「材料清单：无」纯话术）
    assert state.budget_hit == []
    assert "预算触界收敛" not in answer
    # ② 有正文：真作答（材料在正文，非收敛话术）＋ 交付正文帧在场
    assert F2_MATERIAL_TEXT in answer
    assert any(
        event.event == "text" and str(event.data.get("content", "")).strip() for event in events
    )
    # ③ 带材料：工具观察入栈**且**观察帧出流（交付面双证）
    assert any(F2_MATERIAL_TEXT in str(row.get("content")) for row in state.observations)
    obs_frames = [event.data for event in events if event.event == "observation"]
    assert any(F2_MATERIAL_TEXT in str(item.get("content")) for item in obs_frames)
    # ④ 模型调用面可复算：understand 1 ＋ 三发连拒 3 ＋ 兜底轮 1 ＋ 匹配 1 ＋ 作答 1
    assert completer.counts() == {"understand": 1, "decision": 5, "answer": 1}


async def test_f2_dy10_shape_cap_grace_round_delivers_material() -> None:
    """D-诱10 形重演（同形机制、题面取该帧原句）→ `completed` **有正文带材料**。

    同机制的第二个真机形（本批「两题」的另一半）：题面逐字取 `EB4-D-诱10.json` 的 blackbox 记录。
    """
    _wire_ledger()
    script = {"understand": [V2_UNDERSTAND], "decision": _decision_script(), "answer": [_F2_ANSWER]}
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script,
            registry=v2_registry(engine=V2QueueEngine([_rows_outcome()])),
            budget=Budget(rounds=F2_CAP),
        )
        events = await v2_run(runtime, F2_DY10_QUESTION)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    answer = V2RunStore().run(run_id).answer or ""
    assert state.budget_hit == [] and "预算触界收敛" not in answer
    assert F2_MATERIAL_TEXT in answer


async def test_f2_grace_round_granted_once_then_converges_with_pure_wording() -> None:
    """兜底轮**恰一轮**上界：兜底轮再被拒 → `rounds` 超顶 → 收敛（零材料＝纯收敛话术）。

    真机形（三发连拒到顶）＋兜底轮仍拒 ⇒ 仍零材料（无物可发）→ 票面「零材料才用纯收敛话术」；
    判据＝拒因回炉再拒使 `rounds` 溢顶，第 5 次决策永不再发生（兜底不重开自旋洞）。
    """
    _wire_ledger()
    script = {
        "understand": [V2_UNDERSTAND],
        "decision": [*_decision_script()[:3], _F2_OUT_OF_WORLD],
        "answer": [],
    }
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script, budget=Budget(rounds=F2_CAP))
        events = await v2_run(runtime, F2_DY10_QUESTION)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    answer = V2RunStore().run(run_id).answer or ""
    assert state.budget_hit == ["rounds"]
    assert int(state.rounds) == F2_CAP + 1  # 兜底轮占轮 → 超顶（上界可复算）
    converged = [entry for entry in state.notices if entry.get("type") == "budget_converged"]
    assert len(converged) == 1 and converged[0]["gates"] == ["rounds"]
    assert "未取得可交付材料" in answer and "材料清单：无" in answer
    assert completer.counts() == {"understand": 1, "decision": 4}


# ---------- 3 NQ-M3 形端到端：理解面收敛拒答**有正文**（非零交付；F2 第二件） ----------


async def test_f2_nq_m3_fenced_reply_run_completes_with_text() -> None:
    """NQ-M3 形端到端：两次读题应答皆**围栏包裹** → 收敛拒答 → run `completed` **非零交付**。

    真机帧 `EB4-NQ-M3.json`＝`run-e318723a`（两读原话逐字同形，见
    `tests/domains/test_v2_understanding.py::test_f2_nq_m3_frame_fenced_reply_converges_with_text`）。
    判据：①`blackbox.status == "completed"`（旧形曾整 run 零交付／`failed`）；②交付正文帧在场且
    非空（拒答正文＝确定性文案，统一收敛句＋材料面如实）；③零 `run_failed` notice；④模型调用面＝
    understand 恰 2 次（回喂恰一次）。
    """
    script = {
        "understand": [_F2_NQ_M3_RAW, _F2_NQ_M3_RAW],
        "decision": [],
        "answer": [],
    }
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script)
        events = await v2_run(runtime, F2_NQ_M3_QUESTION)
    assert events[-1].event == "blackbox" and events[-1].data["status"] == "completed"
    run_id = events[-1].data["run_id"]
    state = V2RunStore().load(run_id)
    texts = [event.data["content"] for event in events if event.event == "text"]
    answer = V2RunStore().run(run_id).answer or ""
    # ① 非零交付：交付正文帧一帧、正文非空且＝落库答案（直答旁路收口）
    assert texts and texts[-1].strip()
    assert texts[-1] == answer
    assert "没能完全读懂这道题，请补充说明" in answer
    assert "已获材料：无" in answer
    # ② 收口形：直答旁路（`draft`＝交付正文＋`draft_kind="direct"`）＋ 零 `run_failed`
    assert state.draft == answer and state.draft_kind == "direct"
    assert "run_failed" not in [str(entry.get("type")) for entry in state.notices]
    # ③ 上限恰一次
    assert completer.counts() == {"understand": 2}
