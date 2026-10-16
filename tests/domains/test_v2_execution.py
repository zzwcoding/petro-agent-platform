"""RT-W4-05a execution 验收——`specs/execution.md`「验收测试」表 12 行逐行落测（1:1 同名）。

12 行对应（规格表 `specs/execution.md:103–:118` 原序、标识逐字；-B 票续用同一行序不重编）：
- 行 1 `parallel_and_stable_seq`：只读子问题并行执行；观察编号按定序分配（两次运行同序）；
- 行 2 `success_not_rerun`：已成功子问题不重发工具调用（指纹命中）；
- 行 3 `failure_classified_retry_subset_only`：失败分类三档 → **只重跑 `retryable`**；
  `refused`（前置闸拒）终局不回炉（**pin-16 的承接面**——本块只出回炉触发面：失败子集＋分类）；
- 行 4 `big_result_ref_only`：行集类不落引用（全量行随观察交付、丢行＝0）；非行集大结果落引用
  （窗口只留摘要＋引用＋行数、不留全文）——**pin-08 执行侧落点**；
- 行 5 `material_ref_addressable`：引用可寻址（handle 能读回原文）；
- 行 6 `exec_status_vs_answered_separated`：`exec_status="ok"` 但 `answered=False` 时如实分开记；
- 行 7 `need_input_suspend_resume_guard`：缺参 → `need_input` ＋ 挂起；恢复时重取易变环境量、
  不重放已完成部分；
- 行 10 `discover_tool_event_emitted`：发现步由本块发起只读调用并发射 `tool` 事件（发射单元 M5）；
- 行 12 `observation_requires_source`：观察缺出处 → 判失败；
- 行 13 `one_failure_does_not_abort_batch`：单子问题失败不阻断其余（不炸整批）；
- 行 15 `empty_probe_fingerprint_emission_reject`：同参空手重发 → 发射级拒（不执行工具、不占探查
  预算）；首拒免轮、第 2 次起占轮；异参不拒（门开着）——**pin-06 专钉**；
- 行 16 `same_param_replay_dispatch_gate`：dispatch 前查同参指纹簿——全支皆在实录＝拦（拒因回喂
  模型重决策；首拦免轮、连续第 2 次起占轮）、任一支新参＝放行。

本票另两条自有面（非规格表行）：
- `card_signature_and_six_shapes`：骨架与公开面按卡面签名（`execute(state) -> ExecutionOutcome`）
  ＋六形状齐（规格 :35–:60）；
- `no_bypass_on_public_faces`：无手写替代（工具只在注入的 `tools` 公开面上走、不触模型面／引擎／
  框架）。
另有边界／保留两形与公开面单点三条自证（不占规格表行序）。

真源：`specs/execution.md`（已定稿）／卡 `specs/modules.md` `## execution`；接缝＝`tools` 公开面
（`ToolRegistry.call`／`ToolResult`／`Observation`／`AskFrame`）＋`transport.EventBus`＋
`persistence.RunStore` 三处注入面。
"""

from __future__ import annotations

import ast
import asyncio
import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import appv2.runtimev2.execution as execution
from appv2.runtimev2.execution import (
    BIG_RESULT_THRESHOLD_CHARS,
    EXEC_STATUS_FAILED,
    EXEC_STATUS_KINDS,
    EXEC_STATUS_NEED_INPUT,
    EXEC_STATUS_OK,
    GATE_EMPTY_PROBE,
    GATE_SAME_PARAM_REPLAY,
    MISSING_SOURCE_REASON,
    PAYLOAD_CONSUMES_ROUND_KEY,
    PAYLOAD_GATE_KEY,
    PAYLOAD_ROW_COUNT_KEY,
    PAYLOAD_SUBTASK_ID_KEY,
    PAYLOAD_VOLATILE_KEY,
    ErrorClass,
    ExecutionOutcome,
    MaterialRef,
    Observation,
    SubtaskExec,
    execute,
)
from appv2.runtimev2.parsing import (
    CHAIN_DATA,
    CHAIN_KNOWLEDGE,
    discover_fingerprint,
    emission_fingerprints,
    payload_fingerprint,
)
from appv2.runtimev2.persistence import MemoryTables, RunStore, UnknownHandleError
from appv2.runtimev2.state import Budget, RunState
from appv2.runtimev2.transport import EventBus, SseEvent
from appv2.tools import (
    ASK_CLARIFY,
    CATEGORY_BAD_ARGS,
    CATEGORY_REFUSED,
    CATEGORY_RETRYABLE,
    DATA_QUERY,
    DOC_RETRIEVE,
    SEMANTIC_QUERY,
    AskFrame,
    ToolContext,
    ToolResult,
)
from appv2.tools import (
    Observation as ToolObservation,
)

_EXECUTION_DIR = Path(execution.__file__).parent
_HUGE = BIG_RESULT_THRESHOLD_CHARS + 100


# ── 工具面测试替身（Seam＝`tools` 公开面：`async def call(name, args, ctx) -> ToolResult`）──


@dataclass(slots=True)
class _Reply:
    """一条剧本应答（`yields`＝让出事件循环次数——并发面交错与完成序调序用）。"""

    result: ToolResult | None = None
    raises: Exception | None = None
    yields: int = 0


class _ScriptedRegistry:
    """剧本化工具面替身——与 `tools` 公开面同调用形；可观测调用序、并发重叠与完成序。"""

    def __init__(self, script: Mapping[str, Sequence[_Reply]] | None = None) -> None:
        self._script: dict[str, list[_Reply]] = {
            name: list(replies) for name, replies in (script or {}).items()
        }
        self.calls: list[tuple[str, dict[str, Any], ToolContext]] = []
        self.completions: list[str] = []
        self.open = 0
        self.max_open = 0

    async def call(self, name: str, args: Mapping[str, Any], ctx: ToolContext) -> ToolResult:
        self.calls.append((name, dict(args), ctx))
        queue = self._script.get(name)
        if not queue:  # 未剧本化即当场暴露（不静默兜底）
            raise AssertionError(f"未剧本化的工具调用：{name!r} args={dict(args)!r}")
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        self.open += 1
        self.max_open = max(self.max_open, self.open)
        try:
            for _ in range(reply.yields):
                await asyncio.sleep(0)
            if reply.raises is not None:
                raise reply.raises
            if reply.result is None:
                raise AssertionError("剧本应答缺结果——测试装配错")
            return reply.result
        finally:
            self.open -= 1
            self.completions.append(payload_fingerprint(dict(args)))

    def called_tools(self) -> list[str]:
        return [name for name, _args, _ctx in self.calls]


def _tool_obs(
    content: str,
    *,
    source: str = "agg_oil_daily",
    source_id: str = "BZ34-8",
    kind: str = "agg_row",
) -> ToolObservation:
    return ToolObservation(
        content=content,
        source=source,
        source_id=source_id,
        version=None,
        freshness="",
        scope="agg",
        locator={"kind": kind, "table": source},
    )


def _ok(*observations: ToolObservation) -> ToolResult:
    return ToolResult.ok(observations)


def _failed(category: str, message: str) -> ToolResult:
    return ToolResult.failed(category, message, hint="测试剧本")


def _ask() -> ToolResult:
    return ToolResult.ask_frame(
        AskFrame(kind=ASK_CLARIFY, prompt="请补充时间窗", options=("近一月", "近一年"))
    )


# ── 状态与场景装配 ──────────────────────────────────────────────────────────────


def _data_match(subtask_id: str, slot: str = "日产油量") -> dict[str, Any]:
    return {
        "id": subtask_id,
        "chain": CHAIN_DATA,
        "tool": DATA_QUERY,
        "plan": {"metric_slot": slot, "ranking": False},
    }


def _knowledge_match(subtask_id: str, question: str = "渤中34-8 井史") -> dict[str, Any]:
    return {
        "id": subtask_id,
        "chain": CHAIN_KNOWLEDGE,
        "tool": DOC_RETRIEVE,
        "retrieval_need": {"question": question, "anchors": ["BZ34-8"]},
    }


def _state(
    matches: Sequence[Mapping[str, Any]],
    *,
    verdicts: Mapping[str, str] | None = None,
    **overrides: Any,
) -> RunState:
    """场景状态：问题组支 = 匹配支，前置判定由 `verdicts` 给（缺省全部放行）。"""
    decisions = dict(verdicts or {})
    state = RunState(
        run_id="run-rt-w4-05a",
        question="测试题",
        question_group={
            "subtasks": [
                {
                    "id": str(match["id"]),
                    "question": f"子问题 {match['id']}",
                    "ledger_notes": "注",
                }
                for match in matches
            ]
        },
        tool_matches=[dict(match) for match in matches],
        precondition_verdicts=[
            {
                "subtask_id": str(match["id"]),
                "decision": decisions.get(str(match["id"]), "allow"),
            }
            for match in matches
        ],
    )
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def _run(
    state: RunState,
    registry: _ScriptedRegistry,
    *,
    store: RunStore | None = None,
) -> tuple[ExecutionOutcome, EventBus]:
    bus = EventBus()
    outcome = execute(state, bus=bus, registry=registry, store=store)
    return outcome, bus


async def _event_frames(bus: EventBus, event: str) -> list[dict[str, Any]]:
    """按事件名取本流帧载荷（收束后读全量；信封与游标面归 transport 自测）。"""
    bus.close()
    frames: list[SseEvent] = [frame async for frame in bus.stream(0)]
    return [frame.data for frame in frames if frame.event == event]


def _by_id(outcome: ExecutionOutcome) -> dict[str, SubtaskExec]:
    return {item.subtask_id: item for item in outcome.subtasks}


def _gate_steps(state: RunState, gate: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for entry in state.steps:
        payload = entry.get("payload")
        if isinstance(payload, Mapping) and payload.get(PAYLOAD_GATE_KEY) == gate:
            out.append(dict(payload))
    return out


# ── 行 1：只读并行执行；观察编号按定序分配（两次运行同序）──────────────────────────


async def test_parallel_and_stable_seq() -> None:
    """并行面（同处一个事件循环）＋定序面（编号按子问题定序，与完成顺序解耦）。"""
    matches = [_data_match("s1"), _knowledge_match("s2"), _data_match("s3", slot="日产液量")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok(_tool_obs("s1 行")), yields=3),  # 首个派遣、最后完成
                _Reply(result=_ok(_tool_obs("s3 行")), yields=1),
            ],
            DOC_RETRIEVE: [
                _Reply(result=_ok(_tool_obs("s2 片段", kind="fragment")), yields=1)
            ],
        }
    )
    state = _state(matches)
    outcome, bus = _run(state, registry)

    assert registry.max_open == 3  # 三支并行（串行实现 max_open 恒 1）
    plan_args = payload_fingerprint({"plan_draft": {"metric_slot": "日产油量", "ranking": False}})
    assert registry.completions[0] != plan_args  # 首个完成者不是首个派遣支
    assert registry.completions[-1] == plan_args  # s1 最后完成
    # 编号仍按子问题定序分配：s1＝[1]、s2＝[2]、s3＝[3]（与完成顺序无关）
    assert [item.seq for item in outcome.observations] == [1, 2, 3]
    assert [item.content for item in outcome.observations] == ["s1 行", "s2 片段", "s3 行"]
    assert [row["index"] for row in state.observations] == [1, 2, 3]
    assert [frame["index"] for frame in await _event_frames(bus, "observation")] == [1, 2, 3]

    # 两次运行同序（换完成序、不换入参）
    mirror = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok(_tool_obs("s1 行"))),
                _Reply(result=_ok(_tool_obs("s3 行")), yields=2),
            ],
            DOC_RETRIEVE: [_Reply(result=_ok(_tool_obs("s2 片段", kind="fragment")))],
        }
    )
    mirrored_state = _state(matches)
    mirrored, _bus = _run(mirrored_state, mirror)
    assert mirror.completions[-1] != registry.completions[-1]  # 完成序已换
    assert [item.content for item in mirrored.observations] == ["s1 行", "s2 片段", "s3 行"]
    assert [row["index"] for row in mirrored_state.observations] == [1, 2, 3]


# ── 行 2：已成功子问题不重发工具调用（指纹命中）──────────────────────────────────


def test_success_not_rerun() -> None:
    """第二趟：指纹命中 → 零工具调用、账目沿用（不重放已完成部分）；参数变了＝新尝试。"""
    matches = [_data_match("s1"), _knowledge_match("s2")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok(_tool_obs("s1 行")))],
            DOC_RETRIEVE: [_Reply(result=_ok(_tool_obs("s2 片段", kind="fragment")))],
        }
    )
    state = _state(matches)
    first, _bus = _run(state, registry)
    assert [item.exec_status for item in first.subtasks] == [EXEC_STATUS_OK, EXEC_STATUS_OK]
    assert len(registry.calls) == 2

    carried = _ScriptedRegistry()
    second, _bus2 = _run(
        _state(matches, subtask_results=list(state.subtask_results)), carried
    )
    assert carried.calls == []  # 指纹命中——不重发工具调用
    assert [item.exec_status for item in second.subtasks] == [EXEC_STATUS_OK, EXEC_STATUS_OK]
    assert all(item.answered for item in second.subtasks)
    assert [item.row_count for item in second.subtasks] == [1, 1]
    assert second.observations == []  # 不重放（观察不重复回流）

    # 指纹未命中（参数已变）＝新尝试：只重跑该支
    changed = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("s1 新行")))]})
    changed_outcome, _bus3 = _run(
        _state(
            [_data_match("s1", slot="日产液量"), _knowledge_match("s2")],
            subtask_results=list(state.subtask_results),
        ),
        changed,
    )
    assert changed.called_tools() == [DATA_QUERY]
    assert _by_id(changed_outcome)["s1"].row_count == 1


# ── 行 3：失败分类三档 → 只重跑 `retryable`；`refused` 终局不回炉（pin-16 承接面）──


def test_failure_classified_retry_subset_only() -> None:
    """三档分类写明文；`retryable` 重跑恰一次，`bad_args`／`refused` 不重跑；refused 终局。"""
    matches = [_data_match("s1"), _knowledge_match("s2"), _data_match("s3")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游抖动")),  # s1 首投
                _Reply(result=_failed(CATEGORY_REFUSED, "台账无据——闸拒")),  # s3
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游抖动")),  # s1 重跑（仍失败）
            ],
            DOC_RETRIEVE: [_Reply(result=_failed(CATEGORY_BAD_ARGS, "plan 字段错"))],
        }
    )
    state = _state(matches)
    outcome, _bus = _run(state, registry)
    accounts = _by_id(outcome)

    assert [accounts["s1"].error.category, accounts["s2"].error.category] == [  # type: ignore[union-attr]
        CATEGORY_RETRYABLE,
        CATEGORY_BAD_ARGS,
    ]
    assert accounts["s3"].error.category == CATEGORY_REFUSED  # type: ignore[union-attr]
    assert all(item.exec_status == EXEC_STATUS_FAILED for item in outcome.subtasks)
    assert all(item.error is not None and item.error.reason for item in outcome.subtasks)
    # 只重跑 retryable：s1＝首投＋重跑一次；s2／s3 各一次（bad_args／refused 不原地重投）
    assert registry.called_tools() == [DATA_QUERY, DOC_RETRIEVE, DATA_QUERY, DATA_QUERY]
    assert state.tool_retries == {DATA_QUERY: 1}

    # pin-16 承接面：本块只出**回炉触发面**（失败子集＋三档分类机读在场）
    failed_subset = {
        item.subtask_id: item.error.category
        for item in outcome.subtasks
        if item.exec_status == EXEC_STATUS_FAILED and item.error is not None
    }
    assert failed_subset == {
        "s1": CATEGORY_RETRYABLE,
        "s2": CATEGORY_BAD_ARGS,
        "s3": CATEGORY_REFUSED,
    }
    # 「恰 1 次为界」的计数面不落本档（钉本体＝ preconditions 侧 ::rewire_once_then_refuse）
    assert state.chain_switch_marks == {}

    # refused（前置闸拒）终局不回炉：产物账如实标 refused；失败不记成功实录（永不再投）
    records = {str(item["id"]): item for item in state.subtask_results}
    assert records["s3"]["status"] == CATEGORY_REFUSED
    assert records["s1"]["status"] == CATEGORY_RETRYABLE
    assert state.executed_payloads == []

    # 回炉轮（只带失败子集）：只重跑 retryable；成功不重跑、同参 bad_args 零新信息被拦、
    # refused 终局零调用（行为 3 全档语义的机检面）
    rerun = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("s1 回炉行")))]})
    rerun_outcome, _bus2 = _run(
        _state(
            matches,
            subtask_results=list(state.subtask_results),
            tool_retries=dict(state.tool_retries),
        ),
        rerun,
    )
    assert rerun.called_tools() == [DATA_QUERY]  # 只重跑 retryable（s1）
    after = _by_id(rerun_outcome)
    assert after["s1"].exec_status == EXEC_STATUS_OK  # 重跑成功（成功结果保留面）
    assert after["s2"].error.category == CATEGORY_BAD_ARGS  # type: ignore[union-attr]
    assert after["s3"].error.category == CATEGORY_REFUSED  # type: ignore[union-attr]


# ── 行 4：行集全量交付（丢行＝0）／非行集大结果落引用（pin-08 执行侧）─────────────


def test_big_result_ref_only() -> None:
    """行集题全量行随观察交付（永不落引用）；非行集超阈落引用：窗口只留摘要＋引用＋行数。"""
    rows = [_tool_obs(f"井{i}=产量{i}", source_id=f"well-{i}") for i in range(50)]
    rows.append(_tool_obs("超长行 " + "x" * _HUGE))  # 单条行集观察远超大阈——照样不落引用
    huge = "片段正文\n" * 40 + "y" * _HUGE
    expected_rows = sum(1 for line in huge.splitlines() if line.strip())
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok(*rows))],
            DOC_RETRIEVE: [
                _Reply(
                    result=_ok(
                        _tool_obs(
                            huge,
                            source="报告R1→库L1",
                            source_id="frag-1",
                            kind="fragment",
                        )
                    )
                )
            ],
        }
    )
    state = _state([_data_match("rows"), _knowledge_match("doc")])
    store = RunStore(MemoryTables())
    outcome, _bus = _run(state, registry, store=store)

    rowset = [row for row in state.observations if row["locator"]["kind"] == "agg_row"]
    assert len(rowset) == len(rows)  # 丢行＝0（引擎返回多少行就交付多少行）
    assert all("ref" not in row for row in rowset)  # 行集题不落引用
    assert rowset[-1]["content"] == "超长行 " + "x" * _HUGE  # 全量原文随观察交付

    material = next(row for row in state.observations if row["locator"]["kind"] == "fragment")
    assert material["content"] != huge  # 窗口不留全文
    assert material["content"] == material["ref"]["summary"]  # 只留摘要
    assert material["ref"]["row_count"] == expected_rows  # 行数如实

    promised = [item for item in outcome.observations if item.ref is not None]
    assert len(promised) == 1
    assert promised[0].content is None  # 大结果只带引用
    assert promised[0].ref is not None
    assert _by_id(outcome)["doc"].ref.handle == promised[0].ref.handle  # type: ignore[union-attr]
    # 披露义务：落引用必披露（截断与落引用必披露——行为 4）
    assert [item["type"] for item in state.notices] == ["material_truncated"]


# ── 行 5：引用可寻址（handle 能读回原文）───────────────────────────────────────


def test_material_ref_addressable() -> None:
    """`handle` 读回原文逐字节相同；坏 handle 抛错（写了找不回＝等于静默丢材料）。"""
    original = "长正文\n" * 30 + "z" * _HUGE
    registry = _ScriptedRegistry(
        {
            DOC_RETRIEVE: [
                _Reply(
                    result=_ok(
                        _tool_obs(
                            original,
                            source="报告R2→库L2",
                            source_id="frag-2",
                            kind="fragment",
                        )
                    )
                )
            ]
        }
    )
    state = _state([_knowledge_match("doc")])
    store = RunStore(MemoryTables())
    outcome, _bus = _run(state, registry, store=store)

    ref = _by_id(outcome)["doc"].ref
    assert isinstance(ref, MaterialRef)
    assert store.read_ref(ref.handle).decode("utf-8") == original
    assert state.observations[-1]["ref"]["handle"] == ref.handle  # 行内引用同源同值
    try:
        store.read_ref("blob-" + "0" * 64)
    except UnknownHandleError:
        pass
    else:  # pragma: no cover - 坏 handle 必须抛错
        raise AssertionError("坏 handle 未抛错——引用可寻址性失效")


# ── 行 6：`exec_status="ok"` 但 `answered=False` 时如实分开记 ──────────────────────


def test_exec_status_vs_answered_separated() -> None:
    """空结果：过程判 ok、业务判未答上——两字段各自如实，不互相冒充。"""
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok())],  # 空结果（零观察）
            DOC_RETRIEVE: [_Reply(result=_ok(_tool_obs("片段", kind="fragment")))],
        }
    )
    outcome, _bus = _run(_state([_data_match("empty"), _knowledge_match("hit")]), registry)
    accounts = _by_id(outcome)

    assert accounts["empty"].exec_status == EXEC_STATUS_OK
    assert accounts["empty"].answered is False  # 分开记：ok ≠ answered
    assert accounts["empty"].row_count == 0
    assert accounts["hit"].exec_status == EXEC_STATUS_OK
    assert accounts["hit"].answered is True


# ── 行 7：缺参 → `need_input` ＋ 挂起；恢复时重取易变环境量、不重放已完成部分 ────────


async def test_need_input_suspend_resume_guard() -> None:
    """挂起面（`need_input` ＋ `ask` 帧 ＋ `pending_ask`）＋恢复面（重取活体量、不重放）。"""
    matches = [_data_match("done"), _knowledge_match("missing")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok(_tool_obs("done 行")))],
            DOC_RETRIEVE: [_Reply(result=_ask())],
        }
    )
    state = _state(matches)
    outcome, bus = _run(state, registry)
    accounts = _by_id(outcome)

    assert accounts["missing"].exec_status == EXEC_STATUS_NEED_INPUT
    assert accounts["missing"].answered is False
    assert accounts["missing"].error is None  # 挂起不是失败
    assert accounts["done"].exec_status == EXEC_STATUS_OK
    assert state.pending_ask is not None and state.pending_ask["kind"] == ASK_CLARIFY
    assert [frame["frame"]["kind"] for frame in await _event_frames(bus, "ask")] == [ASK_CLARIFY]
    # 挂起支不入产物账（恢复后随批重入——不重放已完成部分）
    assert [item["id"] for item in state.subtask_results] == ["done"]

    # 恢复段：用户选择回填 ＋ 活体环境量变化（外表放行态／候选集由调用方现取）
    resume = _state(matches, subtask_results=list(state.subtask_results))
    resume.resume_choices = [{"kind": ASK_CLARIFY, "choice": "近一月"}]
    resume.approved_ids = ["ext-table-1"]
    resume.metric_candidates = ["日产油量"]
    resume_registry = _ScriptedRegistry(
        {DOC_RETRIEVE: [_Reply(result=_ok(_tool_obs("补参后片段", kind="fragment")))]}
    )
    resumed, _bus2 = _run(resume, resume_registry)

    # 重取面：恢复步落机读读数（活体现取——放行态／候选集／预算三项可机检）
    guard = resume.steps[0]
    assert guard["title"] == "恢复重取易变环境量"
    readings = guard["payload"][PAYLOAD_VOLATILE_KEY]
    assert readings["approved_tables"] == ["ext-table-1"]
    assert readings["metric_candidates"] == ["日产油量"]
    assert readings["budget"] == 6 * 2
    # 不重放已完成部分：done 零调用；挂起支按**新**环境量重投
    assert resume_registry.called_tools() == [DOC_RETRIEVE]
    assert resume_registry.calls[0][2].approved_tables == ("ext-table-1",)
    assert resume_registry.calls[0][2].metric_candidates == ("日产油量",)
    assert _by_id(resumed)["done"].exec_status == EXEC_STATUS_OK
    assert _by_id(resumed)["missing"].exec_status == EXEC_STATUS_OK


# ── 行 10：发现步由本块发起只读调用并发射 `tool` 事件（发射单元 M5）───────────────


async def test_discover_tool_event_emitted() -> None:
    """发现步：本块发起只读调用 ＋ 发 `tool` 帧（键集＝S6 §一 tool 行）＋ 探查预算记账。"""
    registry = _ScriptedRegistry(
        {
            SEMANTIC_QUERY: [
                _Reply(result=_ok(_tool_obs("台账条目", source="sem_metric", kind="metric")))
            ]
        }
    )
    state = RunState(run_id="run-discover", question="q")
    state.pending_discovers = [{"tool": SEMANTIC_QUERY, "args": {"question": "日产油量"}}]
    outcome, bus = _run(state, registry)

    assert registry.called_tools() == [SEMANTIC_QUERY]
    frames = await _event_frames(bus, "tool")
    assert len(frames) == 1
    assert set(frames[0]) == {"tool", "status", "seq", "message"}
    assert frames[0]["tool"] == SEMANTIC_QUERY
    assert frames[0]["status"] == "ok"
    assert frames[0]["seq"] == 1
    assert state.discover_used == 1
    assert state.pending_discovers == []
    assert [row["locator"]["kind"] for row in state.observations] == ["metric"]
    assert outcome.subtasks == []


# ── 行 12：观察缺出处 → 判失败 ──────────────────────────────────────────────────


def test_observation_requires_source() -> None:
    """缺出处：形状构造与回流两路皆判失败（fail-closed——INV-1 的输入）。"""
    try:
        Observation(seq=1, content="正文", ref=None, source="   ")
    except ValueError as exc:
        assert "缺出处" in str(exc)
    else:  # pragma: no cover - 形状面必须 fail-closed
        raise AssertionError("缺出处的观察被收下——INV-1 输入失守")

    registry = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("行", source="")))]})
    try:
        _run(_state([_data_match("s1")]), registry)
    except ValueError as exc:
        assert MISSING_SOURCE_REASON in str(exc)
    else:  # pragma: no cover - 回流面必须 fail-closed
        raise AssertionError("回流段收下了缺出处的观察——判失败面失效")


# ── 行 13：单子问题失败不阻断其余（不炸整批）──────────────────────────────────────


async def test_one_failure_does_not_abort_batch() -> None:
    """三支两成：失败支如实记，另两支照常回流（工具调用抛错也不炸整批）。"""
    matches = [_data_match("a"), _knowledge_match("b"), _data_match("c")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok(_tool_obs("a 行"))),
                _Reply(result=_failed(CATEGORY_REFUSED, "口径闸拒")),
            ],
            DOC_RETRIEVE: [_Reply(raises=ValueError("上游炸了"))],  # 工具调用抛错
        }
    )
    state = _state(matches)
    outcome, bus = _run(state, registry)
    accounts = _by_id(outcome)

    assert len(outcome.subtasks) == 3  # 一一对应（一支不落）
    assert accounts["a"].exec_status == EXEC_STATUS_OK
    assert accounts["a"].answered is True
    assert accounts["c"].exec_status == EXEC_STATUS_FAILED
    assert accounts["c"].error.category == CATEGORY_REFUSED  # type: ignore[union-attr]
    assert accounts["b"].exec_status == EXEC_STATUS_FAILED
    assert accounts["b"].error is not None and "上游炸了" in accounts["b"].error.reason
    assert [frame["status"] for frame in await _event_frames(bus, "tool")] == [
        "ok",
        "failed",
        "failed",
    ]
    assert [frame["index"] for frame in await _event_frames(bus, "observation")] == [1]


# ── 行 15：同参空手重发 → 发射级拒（pin-06 专钉）─────────────────────────────────


def test_empty_probe_fingerprint_emission_reject() -> None:
    """空手闸三面：发射级拒（不执行工具／不占预算）＋轮语义＋异参不拒（门开着）。"""
    args = {"question": "日产油量"}
    fingerprint = discover_fingerprint(SEMANTIC_QUERY, args)
    registry = _ScriptedRegistry({SEMANTIC_QUERY: [_Reply(result=_ok())]})

    state = RunState(run_id="run-probe", question="q")
    state.empty_probes = [fingerprint]  # 该工具同参**已空手**（上一轮探查未命中）
    state.pending_discovers = [{"tool": SEMANTIC_QUERY, "args": dict(args)}]
    first, _bus = _run(state, registry)

    assert registry.calls == []  # 发射级拒：不执行工具
    assert state.discover_used == 0  # 不占探查预算
    assert state.rounds == 0  # 首拒免轮
    assert first.observations == []
    payload = _gate_steps(state, GATE_EMPTY_PROBE)[0]
    assert payload[PAYLOAD_CONSUMES_ROUND_KEY] is False
    assert payload["reject_reason"]
    assert state.decision_error == payload["reject_reason"]  # 拒因回喂模型重决策
    assert state.notices[-1]["type"] == "same_param_replay"

    # 第 2 次同参空手重发：起占轮（自旋收敛）
    state.pending_discovers = [{"tool": SEMANTIC_QUERY, "args": dict(args)}]
    _second, _bus2 = _run(state, registry)
    assert registry.calls == []
    assert state.rounds == 1
    assert _gate_steps(state, GATE_EMPTY_PROBE)[-1][PAYLOAD_CONSUMES_ROUND_KEY] is True

    # 异参不拒（门开着）：换参＝新尝试，真执行；空结果仍记空手指纹（本轮零新增非 notice 观察）
    other = {"question": "日产液量"}
    state.pending_discovers = [{"tool": SEMANTIC_QUERY, "args": other}]
    outcome, _bus3 = _run(state, registry)
    assert registry.called_tools() == [SEMANTIC_QUERY]
    assert state.discover_used == 1
    assert state.rounds == 1  # 放行不占轮
    assert discover_fingerprint(SEMANTIC_QUERY, other) in state.empty_probes
    assert outcome.observations == []


# ── 行 16：同参重投闸（全支皆在实录＝拦／任一支新参＝放行）───────────────────────


def test_same_param_replay_dispatch_gate() -> None:
    """重投闸：全支在实录＝拦（拒因回喂＋首拦免轮／第 2 次起占轮）；任一支新参＝放行。"""
    plan = {"metric_slot": "日产油量", "ranking": False}
    need = {"question": "渤中34-8 井史", "anchors": ["BZ34-8"]}
    match = {
        "id": "s1",
        "chain": CHAIN_DATA,
        "tool": DATA_QUERY,
        "plan": plan,
        "retrieval_need": need,
    }
    fingerprints = emission_fingerprints(plan, need)
    assert len(fingerprints) == 2  # 发射支两枚（plan 支在前）

    registry = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("行")))]})
    state = _state([match], executed_payloads=list(fingerprints))  # 全支皆在实录
    outcome, _bus = _run(state, registry)

    assert registry.calls == []  # 拦：不执行工具
    assert state.rounds == 0  # 首拦免轮
    payload = _gate_steps(state, GATE_SAME_PARAM_REPLAY)[0]
    assert payload[PAYLOAD_CONSUMES_ROUND_KEY] is False
    assert state.decision_error == payload["reject_reason"]  # 拒因回喂模型重决策
    blocked = _by_id(outcome)["s1"]
    assert blocked.exec_status == EXEC_STATUS_FAILED
    assert blocked.error is not None and blocked.error.category == CATEGORY_BAD_ARGS
    assert blocked.answered is False

    # 连续第 2 次拦：起占轮
    _second, _bus2 = _run(state, registry)
    assert registry.calls == []
    assert state.rounds == 1
    assert _gate_steps(state, GATE_SAME_PARAM_REPLAY)[-1][PAYLOAD_CONSUMES_ROUND_KEY] is True

    # 任一支新参＝放行（门开着）：实录只含 plan 支，retrieval_need 支为**新参**
    half = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("放行行")))]})
    half_state = _state([match], executed_payloads=[fingerprints[0]])
    half_outcome, _bus3 = _run(half_state, half)
    assert half.called_tools() == [DATA_QUERY]
    assert _by_id(half_outcome)["s1"].exec_status == EXEC_STATUS_OK
    assert set(half_state.executed_payloads) == set(fingerprints)  # 成功执行→全支入实录


# ── 自有面一：骨架与公开面按卡面签名＋六形状齐 ───────────────────────────────────


def test_card_signature_and_six_shapes() -> None:
    """`execute(state) -> ExecutionOutcome`（卡面签名）＋六形状字段面（规格 :35–:60）。"""
    tree = ast.parse((_EXECUTION_DIR / "core.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "execute"
    )
    assert [argument.arg for argument in function.args.args] == ["state"]
    assert {argument.arg for argument in function.args.kwonlyargs} == {
        "bus",
        "registry",
        "store",
    }

    assert [f.name for f in dataclasses.fields(ExecutionOutcome)] == ["observations", "subtasks"]
    assert [f.name for f in dataclasses.fields(SubtaskExec)] == [
        "subtask_id",
        "exec_status",
        "answered",
        "error",
        "row_count",
        "ref",
    ]
    assert [f.name for f in dataclasses.fields(ErrorClass)] == ["category", "reason"]
    assert [f.name for f in dataclasses.fields(MaterialRef)] == ["handle", "summary", "row_count"]
    assert [f.name for f in dataclasses.fields(Observation)] == ["seq", "content", "ref", "source"]
    assert EXEC_STATUS_KINDS == {EXEC_STATUS_OK, EXEC_STATUS_FAILED, EXEC_STATUS_NEED_INPUT}

    # 两处闭世界越界即判失败（不猜、不取默认）
    for build in (
        lambda: SubtaskExec("s", "done", True, None, None, None),
        lambda: ErrorClass("timeout", "r"),
    ):
        try:
            build()
        except ValueError:
            continue
        raise AssertionError("闭世界越界未判失败")


# ── 自有面二：无手写替代（不自建工具旁路／不触模型面与引擎面）────────────────────


def test_no_bypass_on_public_faces() -> None:
    """本块 import 面：只经 `tools` 公开面接触世界；不引模型面／引擎／框架。"""
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(_EXECUTION_DIR.glob("*.py"))
    )
    tree = ast.parse(source)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    assert "appv2.tools" in modules  # 工具面＝公开面单点（R6）
    forbidden = ("appv2.knowledge", "appv2.query", "appv2.retrieval", "appv2.runtime.", "langgraph")
    assert not [module for module in modules if module.startswith(forbidden)]
    assert not [module for module in modules if module.startswith("langchain")]
    assert not [module for module in modules if module == "appv2.infra.llm_client"]


# ── 边界／保留／公开面自证（不占规格表行序）────────────────────────────────────


async def test_boundary_need_input_empty_and_timeout_do_not_abort() -> None:
    """边界三形（空结果／超时／缺参）各落对应分支且互不阻断（不炸整批面）。"""
    matches = [_data_match("empty"), _knowledge_match("ask"), _data_match("slow")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok()),
                _Reply(raises=TimeoutError()),
                _Reply(raises=TimeoutError()),
            ],
            DOC_RETRIEVE: [_Reply(result=_ask())],
        }
    )
    state = _state(matches)
    state.budget = Budget(tool_timeout=0.01)
    outcome, bus = _run(state, registry)
    accounts = _by_id(outcome)

    assert accounts["empty"].exec_status == EXEC_STATUS_OK
    assert accounts["empty"].answered is False
    assert accounts["ask"].exec_status == EXEC_STATUS_NEED_INPUT
    assert accounts["slow"].exec_status == EXEC_STATUS_FAILED
    assert accounts["slow"].error is not None
    assert accounts["slow"].error.category == CATEGORY_RETRYABLE
    assert len(state.steps) == 4  # 三支派遣步 ＋ 超时支重跑一步（逐调用如实留痕）
    assert {str(item["phase"]) for item in state.process_notes} == {"tool"}
    assert [frame["status"] for frame in await _event_frames(bus, "tool")] == [
        "ok",
        "ask",
        "failed",
    ]
    # 首投＋重跑两次调用各有账（行为 7 每次记账）——重跑步不复发 tool 帧（帧面仍一支一帧）
    assert [entry["payload"].get("attempts") for entry in state.steps] == [None, None, 1, None]


def test_retention_normal_batch_unchanged() -> None:
    """保留集：全成功批次零额外信号（无回炉、无拒、无截断披露）且账目齐。"""
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok(_tool_obs("s1 行")))],
            DOC_RETRIEVE: [_Reply(result=_ok(_tool_obs("s2 片段", kind="fragment")))],
        }
    )
    state = _state([_data_match("s1"), _knowledge_match("s2")])
    outcome, _bus = _run(state, registry)

    assert [item.exec_status for item in outcome.subtasks] == [EXEC_STATUS_OK, EXEC_STATUS_OK]
    assert state.notices == []  # 全成功＝零通知
    assert state.decision_error == ""  # 无回炉行为不变
    assert state.rounds == 0
    assert state.empty_probes == []
    assert state.tool_retries == {}
    assert _gate_steps(state, GATE_EMPTY_PROBE) == []
    assert _gate_steps(state, GATE_SAME_PARAM_REPLAY) == []
    assert [item["status"] for item in state.subtask_results] == ["ok", "ok"]
    # 账目面：逐支参数指纹／行数／拒因在场（记账可事后复算）
    for entry in state.steps:
        payload = entry["payload"]
        assert payload[PAYLOAD_SUBTASK_ID_KEY]
        assert payload["args_fingerprint"]
        assert payload[PAYLOAD_ROW_COUNT_KEY] == 1
        assert payload["reject_reason"] is None
    assert payload_fingerprint({"plan_draft": {"metric_slot": "日产油量", "ranking": False}}) in {
        entry["payload"]["args_fingerprint"] for entry in state.steps
    }


def test_execution_public_face_is_package_root() -> None:
    """公开面单点：消费方只经包根（R2）——六形状＋入口＋两闭世界皆在 `__all__` 内。"""
    exported = set(execution.__all__)
    required = {
        "execute",
        "ExecutionOutcome",
        "SubtaskExec",
        "ErrorClass",
        "MaterialRef",
        "Observation",
        "EXEC_STATUS_KINDS",
        "ERROR_CATEGORIES",
        "GATE_EMPTY_PROBE",
        "GATE_SAME_PARAM_REPLAY",
        "BIG_RESULT_THRESHOLD_CHARS",
    }
    assert required <= exported
