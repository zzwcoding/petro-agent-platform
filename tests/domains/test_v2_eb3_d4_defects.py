"""EB3 D4 缺陷回归（2026-10-17）——两帧题面原句重演（ScriptedCompleter）＋ 计划面规则对读。

覆盖（真源＝`docs/runtime-refactor/proposals/EB3-交付面分层与缺陷修复.md` D4；验收行落
`specs/execution.md` 行为 15／验收表 与 `specs/understanding.md` 行为 13 尾／验收表）：

1. **D4.1＝L04-23 fail-closed**（题面原句「去年各井日产水量是多少？」；真机证据
   `eval/results/frames/EB2G2-L04-23.json`＋`logs/llm_calls/20261017.jsonl` run-b233b245：模型把
   问句问及的**未注册指标**「日产水量」换成在册相近代用品「日产液量」，一路走到 `data_query` 按
   `liquid_output` 交付出数）：**新行为**＝计划面闸拒（不派遣、引擎零调用、无 SQL），拒因回喂后
   模型换链——落检索问答链如实说明，run `completed` 不零交付。
2. **D4.2＝L04-18「前 N」→排名**（题面原句「去年日产油量明细前 200 行」；真机证据
   `EB2G2-L04-18.json`：计划 `ranking=false`／`limit=200` → 落明细＋LIMIT，golden 钉
   ranking=true/desc）：**新行为**＝计划面确定性归一为 `ranking=true`／`direction=desc`／
   `limit=200`（V1 `build_query_plan` 同语义）。
3. **计划面规则对读件**（漂移看守）：`execution.plan_face` 与真源件 `appv2.query.domain` 的
   `parse_row_limit`／`is_ranking_question`／`parse_ranking_direction` 在同一题面电池上逐点相等
   ——R6 隔断下的「两处各持字面」不漂移（本件是那条纪律的机器看守）。
"""

from __future__ import annotations

import json
from typing import Any

from appv2.infra.clock import freeze
from appv2.query import domain as query_domain
from appv2.runtimev2.execution.plan_face import (
    PLAN_FACE_PASS,
    PLAN_FACE_REFUSE_MISMATCH,
    PLAN_FACE_REFUSE_UNGROUNDED,
    explicit_row_limit,
    plan_face_rules,
    question_metric_slots,
    ranking_direction,
)
from appv2.runtimev2.persistence import (
    MemoryTables,
    configure_audit_sink,
    configure_tables,
)
from appv2.runtimev2.persistence import RunStore as V2RunStore
from appv2.tools import ledger_facts
from tests.domains.test_v2_four_phase import (
    V2LedgerPort,
    v2_decision_turn,
    v2_decompose,
    v2_ledger_dump,
    v2_ledger_note,
    v2_matches,
    v2_registry,
    v2_run,
    v2_runtime,
    v2_steps,
    wire_ledger_projection,
)
from tests.domains.test_v2_react_loop import _fragment_obs, _retrieval_with, _rows_outcome

# ── 题面原句（逐字取自两帧 blackbox 记录——不改造、不缩写）──────────────────────────
# EB2G2-L04-23（golden：无台账注册→不入六站链→检索如实说明）
L0423_QUESTION = "去年各井日产水量是多少？"
# EB2G2-L04-18（golden：前 N→排名模板·条 200 生效）
L0418_QUESTION = "去年日产油量明细前 200 行"

# 真机失败形（模型原话——`logs/llm_calls/20261017.jsonl`：理解把「日产水量」读成候选「日产液量」；
# 定案把计划指标换成在册的「日产液量」/「日产油量」）
L0423_UNDERSTAND = json.dumps(
    {"route": "full", "text": "理解：问去年各井的日产水量。", "metric_candidates": ["日产液量"]},
    ensure_ascii=False,
)


class CapturingEngine:
    """剧本化问数引擎（真源＝`tools.fake.FakeQueryEngine` 的观测面扩写）。

    记录 **validate/run 两面**的入参计划（执行到引擎＝真 SQL 生成面；本件以「引擎零调用／入参
    计划逐键」为 plan/SQL 面的机读判据），run 恒吐罐头行集。
    """

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.validate_calls = 0
        self.run_calls = 0
        self.plans: list[Any] = []
        self.ledger_metric_slots = {"日产油量", "日产液量", "油压", "含水率", "配产量"}

    def validate(self, plan: Any, *, candidates: Any = None) -> Any:
        from appv2.query import PlanCheck

        self.validate_calls += 1
        self.plans.append(plan)
        return PlanCheck(ok=True, reason=None)

    def run(self, plan: Any, *, approved_tables: tuple[str, ...] = ()) -> Any:
        self.run_calls += 1
        self.plans.append(plan)
        return self.outcome


# ── D4.1 链级回归：未注册指标不放相近列出数（EB2G2-L04-23 题面原句）──────────────


async def test_d41_l0423_unregistered_metric_fail_closed() -> None:
    """D4.1｜问句指标未注册（「日产水量」）→ 禁回落相近列交付——计划面闸拒＋换链如实路径。

    失败形重演（真机 run-b233b245）：理解候选＝「日产液量」（相近代用品）、定案计划
    `metric_slot="日产液量"`——旧形一路到 `data_query` 按 `liquid_output` 出数交付。

    新行为两面：①**该问产出的 plan/SQL 中不得出现回落列**——引擎（SQL 生成面的唯一入口）
    `validate/run` **零调用**（计划面闸拒在派遣前拦下，零 SQL）；②**走「无注册指标」如实路径**
    ——拒因回喂后模型换链到检索问答链（doc_retrieve 出材料），run `completed` 有交付。
    """
    dump = v2_ledger_dump()
    round1 = v2_decision_turn(
        clarify=v2_decompose(
            subtask_id="s1",
            question=L0423_QUESTION,
            ledger_notes=v2_ledger_note(dump, "日产液量"),  # 台账三段对账过——病灶不在该闸
            chain="data",
        ),
        toolmatch=v2_matches(
            {
                "id": "s1",
                "chain": "data",
                "tool": "data_query",
                "mention_mode": "executed",
                "plan": {
                    "metric_slot": "日产液量",
                    "ranking": False,
                    "window_start": "2025-01-01",
                    "window_end": "2026-01-01",
                },
            }
        ),
    )
    round2 = v2_decision_turn(  # 拒因回喂 → 模型换链（如实路径：检索问答链）
        clarify=v2_decompose(
            subtask_id="s1",
            question=L0423_QUESTION,
            ledger_notes="无台账命中｜未绑定｜null~null",
            chain="knowledge",
        ),
        toolmatch=v2_matches(
            {
                "id": "s1",
                "chain": "knowledge",
                "tool": "doc_retrieve",
                "mention_mode": "executed",
                "retrieval_need": {"question": L0423_QUESTION},
            }
        ),
    )
    script = {
        "understand": [L0423_UNDERSTAND],
        "decision": [*round1, *round2],
        "answer": ["材料未披露去年各井日产水量，如实说明 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = CapturingEngine(_rows_outcome())
    retrieval = _retrieval_with(_fragment_obs("材料中并未披露各井日产水量。", "frag-01"))
    configure_tables(MemoryTables())
    configure_audit_sink(lambda _row: None)
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(
            script=script, registry=v2_registry(engine=engine, retrieval=retrieval)
        )
        events = await v2_run(runtime, L0423_QUESTION)
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )

    # ① 该问产出的 plan/SQL 中不得出现回落列：引擎（SQL 生成面）**零调用**
    assert engine.validate_calls == 0 and engine.run_calls == 0 and engine.plans == []
    # ② 拒因如实（机读留痕：步 payload 的 gate／拒因＋notice——不静默）
    rejects = [
        row
        for row in v2_steps(run_id, "execution")
        if (row.payload or {}).get("gate") == "plan_face_metric"
    ]
    assert len(rejects) == 1
    assert rejects[0].payload["rejected"] is True
    assert "日产液量" in rejects[0].payload["reject_reason"]
    assert rejects[0].payload["error"] is None  # 工具未执行（非失败档）
    assert rejects[0].payload["args"]["plan_draft"]["metric_slot"] == "日产液量"
    rejected_notices = [
        event.data["content"]
        for event in events
        if event.event == "notice" and event.data["type"] == "decision_rejected"
    ]
    assert rejected_notices and "计划面闸拒" in rejected_notices[0]
    # ③ 如实路径落地：换链后的检索链真出材料，run 收口 completed（零失败、非零交付）
    assert events[-2].data["status"] == "completed"
    state = V2RunStore().load(run_id)
    assert [sub["chain"] for sub in state.tool_matches] == ["knowledge"]
    assert state.observations, "检索链未出材料——如实路径未落地"
    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed"


# ── D4.2 链级回归：「前 N」→排名（EB2G2-L04-18 题面原句）─────────────────────────


async def test_d42_l0418_front_n_ranking_normalized() -> None:
    """D4.2｜显式「前 N」＋metric 已注册 → `ranking=true`／desc／`limit=N`（V1 同语义）。

    失败形重演（真机 run-9ffada52）：计划 `ranking=false`／`limit=200` → 落明细＋LIMIT（golden 钉
    ranking=true/desc）。新行为＝计划面确定性归一；归一后的草案即**派遣载荷与指纹面**（引擎入参
    逐键可见——plan/SQL 面机读判据），并留一条过程档案注记（人读面）。
    """
    dump = v2_ledger_dump()
    script = {
        "understand": [
            json.dumps(
                {
                    "route": "full",
                    "text": "理解：列出去年日产油量明细的前 200 行。",
                    "metric_candidates": ["日产油量"],
                },
                ensure_ascii=False,
            )
        ],
        "decision": v2_decision_turn(
            clarify=v2_decompose(
                subtask_id="s1",
                question=L0418_QUESTION,
                ledger_notes=v2_ledger_note(dump, "日产油量"),
                chain="data",
            ),
            toolmatch=v2_matches(
                {
                    "id": "s1",
                    "chain": "data",
                    "tool": "data_query",
                    "mention_mode": "executed",
                    "plan": {
                        "metric_slot": "日产油量",
                        "ranking": False,
                        "aggregate": False,
                        "window_start": "2025-01-01",
                        "window_end": "2026-01-01",
                        "limit": 200,
                    },
                },
                )
            ),
        "answer": ["N-01 井 2025-09-01 日产油量 21.16 吨 [1]。"],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    engine = CapturingEngine(_rows_outcome())
    with freeze("2026-10-08T09:00:00"):
        runtime, _completer = v2_runtime(script=script, registry=v2_registry(engine=engine))
        events = await v2_run(runtime, L0418_QUESTION)
        run_id = next(
            event.data["run_id"] for event in reversed(events) if "run_id" in event.data
        )

    assert events[-2].data["status"] == "completed"
    # 引擎入参计划＝归一后草案（V1 build_query_plan 同语义：前 N→ranking/desc/limit=N）
    assert engine.plans, "引擎未被调用（前 N 归一链未走到执行面）"
    plan = engine.plans[0]
    assert plan.metric_slot == "日产油量"
    assert plan.ranking is True
    assert plan.direction == "desc"
    assert plan.limit == 200
    # 编排面状态字段（state.tool_matches）仍是模型原话——计划面归一只动派遣载荷（登记见票面）
    state = V2RunStore().load(run_id)
    assert state.tool_matches[0]["plan"]["ranking"] is False
    # 归一留痕（过程档案一条——人读面；args 即机读面）
    titles = [entry["title"] for entry in state.process_notes]
    assert titles.count("计划面归一（前 N→排名）") == 1


# ── D4.3 链级回归：同形拒因连发 → 熔断触界收敛（EB2-D-诱9 题面原句）─────────────


# 题面原句（逐字取自 `eval/results/frames/EB2-D-诱9.json` 对应的真机受理题；不改造、不缩写）
DY9_QUESTION = (
    "按台账口径，8 月 5 口检泵井的检泵周期最长的是哪口井、多少天？"
    "最短的比它短多少天？这 5 口井的检泵作业费合计多少万元？"
)
# 真机读题应答（帧内 `answer_text` 逐字＝理解步 `text`——同批同题）
DY9_UNDERSTAND = json.dumps(
    {
        "route": "full",
        "text": (
            "理解：按台账口径，问①8月5口检泵井中检泵周期最长的是哪口井及其天数；"
            "②该最长周期与5口井中最短周期的差值（最短比最长短多少天）；"
            "③这5口井检泵作业费的合计金额（万元）。"
        ),
        "metric_candidates": ["检泵周期"],
    },
    ensure_ascii=False,
)
# 真机失败形＝发射不可解析（帧内两个拒因形严逐字：「输出中没有任何以左花括号起始的 JSON
# 对象」＝malformed_matches／「缺 matches（非空数组——组内每个子问题恰一条）」＝缺配）
_DY9_MALFORMED = "这不是 JSON 对象（无左花括号——只有解释文字）"
_DY9_NO_MATCHES = "{}"


async def _dy9_run(decision_script: list[str]) -> tuple[list[Any], Any]:
    """D-诱9 题面重演装配：读题命中 ＋ 澄清分解一条子问题 ＋ 给定决策剧本（拒因连发）。"""
    dump = v2_ledger_dump()
    script = {
        "understand": [DY9_UNDERSTAND],
        "decision": [
            v2_decompose(
                subtask_id="s1",
                question=DY9_QUESTION,
                ledger_notes=v2_ledger_note(dump, "检泵周期"),
                chain="data",
            ),
            *decision_script,
        ],
    }
    wire_ledger_projection(V2LedgerPort(dump))
    configure_tables(MemoryTables())
    configure_audit_sink(lambda _row: None)
    with freeze("2026-10-08T09:00:00"):
        runtime, completer = v2_runtime(script=script)
        events = await v2_run(runtime, DY9_QUESTION)
        run_id = next(event.data["run_id"] for event in reversed(events) if "run_id" in event.data)
    return events, (completer, V2RunStore().load(run_id), run_id)


async def test_d43_dy9_same_shape_rejections_fuse_instead_of_run_failed() -> None:
    """D4.3｜同形 malformed 连发 → 熔断触界收敛（真机旧形：68 步撞框架递归 35 → `run_failed`）。

    旧形根因（`eval/results/frames/EB2-D-诱9.json`＝`run-4c83211c`）：自环
    `NODE_TOOLMATCH → NODE_TOOLMATCH` 不经澄清入口，**轮数闸在该路上到不了**（自环不计轮），
    同形拒因连发一路撞框架 recursion limit 35 → `run_failed`、整 run 零交付（68 步、
    `Recursion limit of 35 reached without hitting a stop condition`）。

    新行为＝本相位自持同形拒因熔断：每次拒因占一轮＋拒因回喂 `decision_error`；同形拒因
    （`kind`＋逐字拒文）既有次数 ≥ 2 时**显式触界**（`rounds` 顶到 `Budget.rounds`）→
    `bookkeeping.converge` 落 `budget_converged` ＋ 材料如实收口 ＋ `status=completed`；
    收敛后入口返**收敛让位形**（零模型调用）。
    """
    events, (completer, state, run_id) = await _dy9_run([_DY9_MALFORMED] * 3)

    # ① 收口如实：run `completed`，零 `run_failed`（旧形正是这一条红）
    assert events[-2].data["status"] == "completed"
    notice_types = [str(entry.get("type")) for entry in state.notices]
    assert "run_failed" not in notice_types, notice_types
    # ② 熔断触界如实留痕：收敛注记在场且 gates 指名轮数键
    converged = [
        entry for entry in state.notices if entry.get("type") == "budget_converged"
    ]
    assert len(converged) == 1, notice_types
    assert converged[0]["gates"] == ["rounds"]
    # ③ 模型调用面收敛：同形熔断＝恰 3 次决策调用（旧形＝68 步里数十次）
    counts = completer.counts()
    assert counts == {"understand": 1, "decision": 4}, counts  # 澄清 1 ＋ 决策 3
    titles = [str(step.title) for step in v2_steps(run_id)]
    assert titles.count("工具匹配熔断（同形拒因第 3 次）：触界收敛") == 1
    assert titles.count("前置条件机：s1=refuse（unregistered_metric）") == 1
    assert len(v2_steps(run_id)) < 20, "熔断后仍长了（旧形 68 步）"
    # ④ 交付面非空：如实收敛正文（材料面在场、如实说明未取得材料）
    row = V2RunStore().run(run_id)
    assert row is not None and row.status == "completed"
    assert state.answer.startswith("（预算触界收敛——rounds")
    assert "材料清单：" in state.answer
    assert row.answer and "预算触界收敛" in row.answer


async def test_d43_dy9_mixed_rejection_shapes_fuse_at_fifth() -> None:
    """D4.3｜真机夹发形（malformed ×2 ＋ 缺配 ×3）→ 第 5 次拒因熔断（同形计数按形分组）。

    帧内夹发序逐字：malformed_matches ×2 → 缺配 ×3 → …（交替／成簇连发）。同形判据＝
    `kind`＋逐字拒文：异形不入同一计数（故第 5 次拒因＝第三种「缺配」同形第 3 次才熔断）——
    本件即「夹发形不逃熔断」的机器证据（旧形该序一路跑到 recursion 35）。
    """
    events, (completer, state, run_id) = await _dy9_run(
        [_DY9_MALFORMED, _DY9_MALFORMED, _DY9_NO_MATCHES, _DY9_NO_MATCHES, _DY9_NO_MATCHES]
    )

    assert events[-2].data["status"] == "completed"
    assert "run_failed" not in [str(entry.get("type")) for entry in state.notices]
    assert completer.counts() == {"understand": 1, "decision": 6}, completer.counts()
    rejected_kinds = [
        entry["content"].split("）")[0].split("（")[-1]
        for entry in state.notices
        if entry.get("type") == "decision_rejected" and "工具匹配发射被拒" in entry["content"]
    ]
    assert rejected_kinds == [
        "malformed_matches",
        "malformed_matches",
        "缺配",
        "缺配",
        "缺配",
    ], rejected_kinds
    assert [entry["type"] for entry in state.notices].count("budget_converged") == 1
    assert len(v2_steps(run_id)) < 20, "夹发形熔断后仍长了（旧形 68 步）"


# ── 计划面规则单元面（含 R6 隔断下的漂移看守）─────────────────────────────────────
def _keys() -> dict[str, str]:
    return dict(ledger_facts(v2_ledger_dump()).keys)


def test_plan_face_metric_grounding_branches() -> None:
    """计划面接地闸三分支：注册面带锚→放行；问句无注册面→拒（未注册）；注册面不符→拒（回落）。"""
    keys = _keys()
    # 问句的台账注册面（集合成员判定——台账可见面逐字出现在问句）
    assert question_metric_slots("去年各井日产水量是多少？", keys) == frozenset()
    assert question_metric_slots("去年各井日产油量是多少？", keys) == frozenset({"日产油量"})
    # 病灶形：问句无注册面（问句指标在册无绑定）＋计划用在册相近代用品 → 拒
    ungrounded = plan_face_rules(
        question=L0423_QUESTION,
        plan={"metric_slot": "日产液量"},
        ledger_keys=keys,
        metric_registered=True,
    )
    assert ungrounded.decision == PLAN_FACE_REFUSE_UNGROUNDED
    assert ungrounded.rejected and "日产液量" in ungrounded.reason
    # 注册面在场但计划指标不在其中 → 拒（回落相近列）
    mismatch = plan_face_rules(
        question="去年各井日产油量是多少？",
        plan={"metric_slot": "日产液量"},
        ledger_keys=keys,
        metric_registered=True,
    )
    assert mismatch.decision == PLAN_FACE_REFUSE_MISMATCH
    # 注册面在场且计划指标命中 → 放行（原计划零改写）
    ok = plan_face_rules(
        question="去年各井日产油量是多少？",
        plan={"metric_slot": "日产油量", "ranking": False},
        ledger_keys=keys,
        metric_registered=True,
    )
    assert ok.decision == PLAN_FACE_PASS and dict(ok.plan) == {
        "metric_slot": "日产油量",
        "ranking": False,
    }
    # 台账未接线（退化世界）→ 闸静默（不硬拒；先例＝preconditions 空台账不硬拒全量）
    silent = plan_face_rules(
        question=L0423_QUESTION,
        plan={"metric_slot": "日产液量"},
        ledger_keys={},
        metric_registered=True,
    )
    assert silent.decision == PLAN_FACE_PASS
    # 计划指标不在台账 → 本闸不接（判拒归既有台账校验面）
    not_registered = plan_face_rules(
        question=L0423_QUESTION,
        plan={"metric_slot": "日产水量"},
        ledger_keys=keys,
        metric_registered=False,
    )
    assert not_registered.decision == PLAN_FACE_PASS


def test_plan_face_front_n_rewrite_and_aggregate_guard() -> None:
    """「前 N」归一三分支：显式前 N→归一；无数目词→零改动；汇总型（aggregate）→不造互斥违例。"""
    keys = _keys()
    plan = {"metric_slot": "日产油量", "ranking": False, "limit": None}
    rewritten = plan_face_rules(
        question=L0418_QUESTION, plan=plan, ledger_keys=keys, metric_registered=True
    )
    assert rewritten.decision == PLAN_FACE_PASS
    assert dict(rewritten.plan) == {
        "metric_slot": "日产油量",
        "ranking": True,
        "limit": 200,
        "direction": "desc",
    }
    # 欠数问句（无显式「前 N」）→ 零改动（不猜、不补默认）
    plain = plan_face_rules(
        question="去年各井日产油量是多少？",
        plan=plan,
        ledger_keys=keys,
        metric_registered=True,
    )
    assert dict(plain.plan) == plan
    # 汇总型 ∧ 前 N → 不归一（V2-71 `QueryPlan` aggregate∧ranking 互斥把守——本块不造违例）
    aggregate = plan_face_rules(
        question="去年各井日产油量合计前 200",
        plan={"metric_slot": "日产油量", "aggregate": True, "ranking": False},
        ledger_keys=keys,
        metric_registered=True,
    )
    assert dict(aggregate.plan) == {
        "metric_slot": "日产油量",
        "aggregate": True,
        "ranking": False,
    }


_FRONT_N_BATTERY: tuple[str, ...] = (
    "去年日产油量明细前 200 行",
    "排名前 5 的井",
    "TOP3",
    "top 12 井",
    "各井日产油量",
    "最近 30 天各井日产油量明细",
    "前",
    "前三",
    "前 0 井",
    "井位台账里日产油量最高的井是哪口？",
)

# **已登记的可分叉面（不判相等——见测试 docstring）**：V1 `parse_row_limit` 另收「N 口」独立形，
# 本轮归一触发面**只收「前 N」／「TOP N」**（EB3-D4.2 钉面逐字：「显式「前 N」＋metric 已注册」），
# 故「N 口」类字面两边**有意不同判**——是否随批补收 N 口形，登记呈主窗。第二行＝V1 正则的
# **误收形**（「8 月 5 口检泵井」的「5 口」是井数、非条数——`specs/query.md` 风险条点名的
# V1 词面正则陷阱；本块不收、V1 收 5）。
_V1_ONLY_LIMIT_FORMS: tuple[tuple[str, int], ...] = (
    ("上个月产量最高的三口井", 3),
    ("去年两口井的日产油量", 2),
    ("8 月 5 口检泵井的检泵周期最长的是哪口井？", 5),
)

_NON_FRONT_N_FORMS: tuple[str, ...] = (
    "各井日产油量",
    "井位台账里日产油量最高的井是哪口？",
    "最近 30 天各井日产油量明细",
)


def test_plan_face_rules_drift_guard_against_query_domain() -> None:
    """对读件（漂移看守）：`execution.plan_face` 与真源件 `appv2.query.domain` 逐点相等。

    R6 隔断使 runtimev2 相位不得直引 `appv2.query`，故本块按「两处各持字面」体例承载 V1 合同值
    ——本件是那条纪律的**机器看守**：字面漂移即红（`specs/execution.md` 行为 15 的检测手段）。

    **对读面＝重叠域**：条数解析在「前 N」／「TOP N」族与全部**非触发**题面上必须两边同判；
    方向解析全程同判。**已登记分叉面**（有意不同判）：V1 另收「N 口」独立形——本块触发面按
    EB3-D4.2 钉面只收「前 N」／「TOP N」（`_V1_ONLY_LIMIT_FORMS` 逐对断在案——补收与否呈主窗）。
    排名词面的另半面（`is_ranking_question` 的 最高/最低/最大/最小/排名）：本块**不用**——那半面
    归模型与既有面（汇总型问句 ∧ 强制 ranking 会撞 V2-71 `QueryPlan` 互斥把守），故只对
    「前 N／TOP N」形断言真源件同判。
    """
    for question in _FRONT_N_BATTERY:
        assert explicit_row_limit(question) == query_domain.parse_row_limit(question), question
        assert ranking_direction(question) == query_domain.parse_ranking_direction(
            question
        ), question
    for question in _NON_FRONT_N_FORMS:
        assert explicit_row_limit(question) == query_domain.parse_row_limit(question), question
    for question in ("去年日产油量明细前 200 行", "排名前 5 的井", "TOP3"):
        assert query_domain.is_ranking_question(question) is True, question
    # 分叉面逐对在案（V1 收 N 口、本块不收——字面不同判是登记事实，非漂移）
    for question, expected in _V1_ONLY_LIMIT_FORMS:
        assert query_domain.parse_row_limit(question) == expected, question
        assert explicit_row_limit(question) is None, question
