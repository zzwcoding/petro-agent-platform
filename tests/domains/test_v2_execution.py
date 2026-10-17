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

本票（-05a）验收＝规格表第 1–7、10、12、13、15、16 行；-B 票（`RT-W4-05b-execution.md`）续用
同一行序补第 8、9、11、14、17、18、19 行（见文件末「-B 票：闭世界与红线面／记账与机读信号／
边界·保留集」节——闭世界越界、两条 AST 红线、逐调用记账、机读信号三键、边界集与保留集）。

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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import appv2.runtimev2.execution as execution
from appv2.runtimev2.execution import (
    BIG_RESULT_THRESHOLD_CHARS,
    ERROR_CATEGORIES,
    EXEC_STATUS_FAILED,
    EXEC_STATUS_KINDS,
    EXEC_STATUS_NEED_INPUT,
    EXEC_STATUS_OK,
    GATE_EMPTY_PROBE,
    GATE_SAME_PARAM_REPLAY,
    MISSING_SOURCE_REASON,
    PAYLOAD_ARGS_FINGERPRINT_KEY,
    PAYLOAD_ARGS_KEY,
    PAYLOAD_CONSUMES_ROUND_KEY,
    PAYLOAD_ERROR_CATEGORY_KEY,
    PAYLOAD_ERROR_KEY,
    PAYLOAD_ERROR_REASON_KEY,
    PAYLOAD_GATE_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_REF_KEY,
    PAYLOAD_REJECT_REASON_KEY,
    PAYLOAD_ROW_COUNT_KEY,
    PAYLOAD_SUBTASK_ID_KEY,
    PAYLOAD_TOOL,
    PAYLOAD_VOLATILE_KEY,
    PHASE,
    ROWSET_OBSERVATION_KINDS,
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
    LINEAGE_LIMIT_HIT_KEY,
    LINEAGE_LIMIT_KEY,
    LINEAGE_LIMIT_ROWS_KEY,
    LINEAGE_PAYLOAD_KEY,
    LOCATOR_PAYLOAD_KEY,
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


# ── 行 12a：observation 帧载荷透传结构化载荷（2026-10-17 EB2 D1）──────────────────


async def test_observation_frame_carries_structured_payload() -> None:
    """观察自带 `locator.payload` → 帧载荷原样透传（前端核验面）；无载荷＝零该键。

    血缘卡五要素全文仍随 `content` 全量下发（材料面瘦身只作用于模型窗——本帧面判据
    与 `specs/context.md` 血缘口径行同批，2026-10-17 EB2 D1）。
    """
    payload = {
        LINEAGE_PAYLOAD_KEY: {
            "① 口径": "日产油量（单位：吨）——指标台账注册声明",
            "② 来源表": "agg.fct_daily_metering",
        },
        LINEAGE_LIMIT_KEY: {LINEAGE_LIMIT_HIT_KEY: True, LINEAGE_LIMIT_ROWS_KEY: 3},
    }
    lineage = ToolObservation(
        content="① 口径 日产油量（单位：吨）\n② 来源表 agg.fct_daily_metering",
        source="agg.fct_daily_metering",
        source_id="lineage",
        version=None,
        freshness="",
        scope="agg",
        locator={
            "kind": "lineage",
            "table": "agg.fct_daily_metering",
            LOCATOR_PAYLOAD_KEY: payload,
        },
    )
    registry = _ScriptedRegistry(
        {DATA_QUERY: [_Reply(result=_ok(_tool_obs("s1 行"), lineage))]}
    )
    _outcome, bus = _run(_state([_data_match("s1")]), registry)
    frames = await _event_frames(bus, "observation")

    # 血缘支＝携载荷支；行级支无载荷（加性键——不补键不删键）
    with_payload = [frame for frame in frames if LOCATOR_PAYLOAD_KEY in frame]
    assert len(with_payload) == 1
    assert with_payload[0][LOCATOR_PAYLOAD_KEY] == payload  # 原样透传（零裁剪零改名）
    assert "① 口径" in str(with_payload[0]["content"])  # 全文照旧随帧（前端核验面不受损）


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


# ════════════════════════════════════════════════════════════════════════════════
# -B 票（RT-W4-05b-execution.md）：闭世界与红线面／记账与机读信号／边界·保留集
# 规格表行序 8／9／11／14／17／18／19（与 -05a 同一行序，不重编）
# ════════════════════════════════════════════════════════════════════════════════


# ── 越界值载体（绕开 `tools` 面构造期把守——本块两处闭世界把守面的探针）─────────────


@dataclass(slots=True)
class _RawError:
    """工具错误读形替身（`category`／`message`——只作读面，不挂 `tools` 面构造期闭世界）。"""

    category: str
    message: str


@dataclass(slots=True)
class _RawResult:
    """工具结果读形替身（`status`／`error`／`observations`／`ask`——同 `ToolResult` 读法）。"""

    status: str
    error: _RawError | None = None
    observations: tuple[Any, ...] = ()
    ask: None = None


def _raw_result(status: str, *, category: str | None = None) -> Any:
    """造一枚越界值回执（`category` 缺省＝status 越界形）。"""
    error = None if category is None else _RawError(category=category, message="越界档探针")
    return _RawResult(status=status, error=error)


def _rejects(build: Callable[[], object]) -> None:
    """闭世界越界必须判失败（fail-closed：不猜、不取默认、不落哨兵值）。"""
    try:
        build()
    except ValueError:
        return
    raise AssertionError("闭世界越界未判失败")


_BAD_STATUSES: tuple[Any, ...] = ("done", "OK", "success", "refuse", "ok ", "", None)
_BAD_CATEGORIES: tuple[Any, ...] = ("timeout", "retry", "bad-args", "REFUSED", "refused ", "", None)


# ── 行 8：`exec_status`／`category` 越界取值 → 判失败 ──────────────────────────────


def test_enums_closed_world() -> None:
    """行 8｜两处闭世界：取值集逐字 ＋ 越界构造即拒 ＋ 工具面越界值判失败（不猜、不取默认）。"""
    assert EXEC_STATUS_KINDS == {"ok", "failed", "need_input"}
    assert ERROR_CATEGORIES == {"retryable", "bad_args", "refused"}
    # 闭世界取值全体可构造（三三皆收）
    for status in sorted(EXEC_STATUS_KINDS):
        assert SubtaskExec("s1", status, False, None, None, None).exec_status == status
    for category in sorted(ERROR_CATEGORIES):
        assert ErrorClass(category, "拒因如实").category == category
    # `exec_status` 越界 → 判失败（形状面把守）
    for bad in _BAD_STATUSES:
        _rejects(lambda bad=bad: SubtaskExec("s1", bad, False, None, None, None))
    # `category` 越界 → 判失败（形状面把守）
    for bad in _BAD_CATEGORIES:
        _rejects(lambda bad=bad: ErrorClass(bad, "拒因如实"))

    # 工具面回来的越界取值同样判失败（运行时把守）——不把未知档归默认档
    bad_category = _ScriptedRegistry(
        {DATA_QUERY: [_Reply(result=_raw_result("failed", category="timeout"))]}
    )
    _rejects(lambda: _run(_state([_data_match("s1")]), bad_category))
    bad_status = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_raw_result("done"))]})
    _rejects(lambda: _run(_state([_data_match("s1")]), bad_status))


# ── 行 9：程序侧无词表／正则语义判断（AST 扫描本模块）────────────────────────────


_LEXICON_STR_METHODS = {
    "startswith",
    "endswith",
    "lower",
    "upper",
    "casefold",
    "split",
    "partition",
    "count",
}


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _lexicon_violations(tree: ast.Module) -> list[str]:
    """词表形探测（字面集合含汉字串即词表形）；非空转由伪造树咬合验证。"""
    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        for item in node.elts:
            if (
                isinstance(item, ast.Constant)
                and isinstance(item.value, str)
                and _has_cjk(item.value)
            ):
                findings.append(f"L{node.lineno} 字面集合含汉字串（语义词表形）")
    return findings


def _imported_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_no_lexicon_or_regex_in_execution() -> None:
    """行 9｜程序侧无词表／正则语义判断（AST 扫描本模块；豁免面＝形态处理／集合成员判定）。"""
    sources = sorted(_EXECUTION_DIR.glob("*.py"))
    assert sources, "扫描面为空"
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = path.name
        modules = _imported_modules(tree)
        assert "re" not in modules and "regex" not in modules, f"{where} 引入正则面"
        assert not any(
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "re"
            for node in ast.walk(tree)
        ), f"{where} 使用 re.*"
        assert _lexicon_violations(tree) == [], f"{where}: {_lexicon_violations(tree)}"
        for node in ast.walk(tree):
            # 豁免面一：集合成员判定——成员判据只见闭世界常量／结构字符集（非 ASCII 字面判＝词面判）
            if isinstance(node, ast.Compare) and any(
                isinstance(op, (ast.In, ast.NotIn)) for op in node.ops
            ):
                for operand in (node.left, *node.comparators):
                    if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
                        assert operand.value.isascii(), f"{where}:{node.lineno} 非结构字符集判据"
            # 豁免面二：形态处理——词面判方法（前缀／后缀／大小写折叠／切分）零使用
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in _LEXICON_STR_METHODS, (
                    f"{where}:{node.lineno} 词面判方法 {node.func.attr}"
                )
    # 豁免面本体＝形态值集与闭世界取值集（`locator.kind` 形态值／执行状态／失败分类）——非语义词表
    assert ROWSET_OBSERVATION_KINDS == {"agg_row"}
    assert all(
        value.isascii()
        for value in ROWSET_OBSERVATION_KINDS | EXEC_STATUS_KINDS | ERROR_CATEGORIES
    )
    # 探测器非空转：伪造词表／汉字成员判／词面判方法即被咬
    assert _lexicon_violations(ast.parse('WORDS = ["明细", "排名"]\n')) != []
    assert _lexicon_violations(ast.parse('if kind in ("明细", "排名"):\n    pass\n')) != []
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _LEXICON_STR_METHODS
        for node in ast.walk(ast.parse('text.startswith("理解：")\n'))
    )


# ── 行 11：大结果落引用只经 `persistence` 公开面（无直连符号）──────────────────────


# 直连符号族（对象存储客户端／裸 DB driver——规格「框架与依赖红线」逐字点名两面）
_DIRECT_STORAGE_MODULES = (
    "boto3",
    "botocore",
    "minio",
    "oss2",
    "s3fs",
    "fsspec",
    "gcsfs",
    "azure.storage",
    "google.cloud.storage",
    "asyncpg",
    "psycopg",
    "psycopg2",
    "pymysql",
    "MySQLdb",
    "sqlalchemy",
    "sqlite3",
    "aiosqlite",
    "pymongo",
    "redis",
    "cx_Oracle",
    "oracledb",
    "pyodbc",
    "clickhouse_driver",
    "snowflake",
    "neo4j",
    "duckdb",
)
_DIRECT_STORAGE_SYMBOLS = (
    "create_engine",
    "put_object",
    "get_object",
    "copy_object",
    "list_objects",
    "remove_object",
    "S3Client",
    "Minio",
)


def _storage_findings(tree: ast.Module) -> list[str]:
    """直连存储面探测：直连模块／persistence 深层子模块／直连符号／存储接触面越界调用。"""
    findings: list[str] = []
    for module in sorted(_imported_modules(tree)):
        if module.split(".")[0] in _DIRECT_STORAGE_MODULES:
            findings.append(f"直连存储模块 {module}")
        elif module.startswith("appv2.runtimev2.persistence") and (
            module != "appv2.runtimev2.persistence"
        ):
            findings.append(f"直引 persistence 深层子模块 {module}")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _DIRECT_STORAGE_SYMBOLS:
            findings.append(f"L{node.lineno} 直连符号 {node.attr}")
        # 存储接触面＝注入的 `persistence` 公开面：本块只 `put_ref`（不自建落盘旁路）
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "store"
            and node.func.attr != "put_ref"
        ):
            findings.append(f"L{node.lineno} 存储接触面越界 store.{node.func.attr}")
    return findings


def test_no_direct_storage_symbols() -> None:
    """行 11｜大结果落引用只经 `persistence` 公开面（无直连符号：对象存储客户端／裸 DB driver）。"""
    sources = sorted(_EXECUTION_DIR.glob("*.py"))
    assert sources, "扫描面为空"
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert _storage_findings(tree) == [], f"{path.name}: {_storage_findings(tree)}"
    # 正面面：唯一存储依赖＝`persistence` **包根**（公开面单点——深层子模块零直引）
    imported: set[str] = set()
    for path in sources:
        imported |= _imported_modules(ast.parse(path.read_text(encoding="utf-8")))
    assert "appv2.runtimev2.persistence" in imported, "存储依赖不在扫描面（用例空转）"
    # 探测器非空转：直连客户端／裸 driver／persistence 深层子模块即被咬
    assert _storage_findings(ast.parse("import boto3\n")) != []
    assert _storage_findings(ast.parse("import sqlite3\n")) != []
    assert _storage_findings(ast.parse("client.put_object(Bucket='b', Key='k')\n")) != []
    deep = _storage_findings(
        ast.parse("from appv2.runtimev2.persistence.blobs import Bucket\n")
    )
    assert deep != []
    assert _storage_findings(ast.parse("store.read_ref(handle)\n")) != []


# ── 行 14：每次记账字段齐（参数／行数／拒因）─────────────────────────────────────


def test_per_call_accounting() -> None:
    """行 14｜每次工具调用记参数／回来多少行／或被拒原因——逐调用一条账、可事后复算。"""
    plan_args = {"plan_draft": {"metric_slot": "日产油量", "ranking": False}}
    need_args = {"question": "渤中34-8 井史", "anchors": ["BZ34-8"]}
    matches = [_data_match("s1"), _knowledge_match("s2"), _data_match("s3")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok(_tool_obs("行1"), _tool_obs("行2"))),  # s1：回来两行
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游限流")),  # s3 首投
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游限流")),  # s3 同参重跑
            ],
            DOC_RETRIEVE: [_Reply(result=_failed(CATEGORY_BAD_ARGS, "plan 字段错"))],  # s2
        }
    )
    state = _state(matches)
    outcome, _bus = _run(state, registry)
    tool_steps = [
        dict(entry["payload"]) for entry in state.steps if PAYLOAD_TOOL in entry["payload"]
    ]
    # 逐调用一条账：s1 一条、s2 一条、s3 首投＋重跑各一条（重跑不吞首投账）
    assert len(tool_steps) == 4
    for payload in tool_steps:
        # 三字段齐（键恒在场——缺值≠缺键）
        assert PAYLOAD_ARGS_KEY in payload
        assert PAYLOAD_ARGS_FINGERPRINT_KEY in payload
        assert PAYLOAD_ROW_COUNT_KEY in payload
        assert PAYLOAD_REJECT_REASON_KEY in payload
        # 可事后复算：参数指纹＝参数逐字重算
        assert payload[PAYLOAD_ARGS_FINGERPRINT_KEY] == payload_fingerprint(
            payload[PAYLOAD_ARGS_KEY]
        )

    s1_step = next(p for p in tool_steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "s1")
    assert s1_step[PAYLOAD_ARGS_KEY] == plan_args  # 参数逐字
    assert s1_step[PAYLOAD_ROW_COUNT_KEY] == 2  # 回来多少行
    assert s1_step[PAYLOAD_REJECT_REASON_KEY] is None  # 无拒因

    s2_step = next(p for p in tool_steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "s2")
    assert s2_step[PAYLOAD_ARGS_KEY] == need_args
    assert s2_step[PAYLOAD_ROW_COUNT_KEY] is None
    assert s2_step[PAYLOAD_REJECT_REASON_KEY] == "plan 字段错"
    assert s2_step[PAYLOAD_ERROR_KEY] == {
        PAYLOAD_ERROR_CATEGORY_KEY: CATEGORY_BAD_ARGS,
        PAYLOAD_ERROR_REASON_KEY: "plan 字段错",
    }

    s3_steps = [p for p in tool_steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "s3"]
    # 首投账＋重跑账（重跑步不复发 attempts）
    assert [p.get("attempts") for p in s3_steps] == [1, None]
    assert all(p[PAYLOAD_ARGS_KEY] == plan_args for p in s3_steps)  # 同参重跑＝参数逐字相同
    assert all(p[PAYLOAD_ROW_COUNT_KEY] is None for p in s3_steps)
    assert all(p[PAYLOAD_REJECT_REASON_KEY] == "上游限流" for p in s3_steps)
    assert state.tool_retries == {DATA_QUERY: 1}  # 重跑额度如实计账
    # 账目面与结论面同源：s1 两行／s3 失败的账目可复算（行为 7 的「可事后复算」）
    accounts = _by_id(outcome)
    assert accounts["s1"].row_count == 2
    assert accounts["s3"].error is not None and accounts["s3"].error.reason == "上游限流"


# ── 行 17：机读信号在场（落引用／失败／缺参）─────────────────────────────────────


async def test_execution_signal_present() -> None:
    """行 17｜落引用／失败／缺参三面必产机读信号——`observation`／`tool` 事件 ＋ 步 payload 的
    `row_count`／`ref.handle`／`error.reason` 三键（规格「不降级与静默禁令」节逐字）。"""
    huge = "片段正文\n" * 40 + "y" * _HUGE
    registry = _ScriptedRegistry(
        {
            DOC_RETRIEVE: [
                _Reply(
                    result=_ok(
                        _tool_obs(huge, source="报告R9→库L9", source_id="frag-9", kind="fragment")
                    )
                ),
                _Reply(result=_ask()),
            ],
            DATA_QUERY: [_Reply(result=_failed(CATEGORY_REFUSED, "台账无据——闸拒"))],
        }
    )
    matches = [_knowledge_match("material"), _data_match("refused"), _knowledge_match("missing")]
    state = _state(matches)
    store = RunStore(MemoryTables())
    outcome, bus = _run(state, registry, store=store)
    accounts = _by_id(outcome)
    steps = [dict(entry["payload"]) for entry in state.steps]

    # 三键恒在场（机检可判「每一步都有」——缺值≠缺键）
    assert steps
    for payload in steps:
        assert PAYLOAD_ROW_COUNT_KEY in payload
        assert PAYLOAD_REF_KEY in payload
        assert PAYLOAD_ERROR_KEY in payload

    # 落引用面：`observation` 帧 ＋ 步 payload 的 `ref.handle`（可寻址——未静默丢弃）
    material_step = next(p for p in steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "material")
    ref = accounts["material"].ref
    assert ref is not None
    assert material_step[PAYLOAD_REF_KEY]["handle"] == ref.handle  # 步面／子问题账同源同值
    assert material_step[PAYLOAD_ROW_COUNT_KEY] == 1  # 观察行数（行为 7 记账面）
    # 原文行数（`MaterialRef.row_count` 原义）与观察行数两回事
    assert material_step[PAYLOAD_REF_KEY]["row_count"] == ref.row_count
    assert store.read_ref(ref.handle).decode("utf-8") == huge  # handle 可读回（未静默丢弃）
    frames = await _event_frames(bus, "observation")
    assert [frame["index"] for frame in frames] == [1]
    assert [frame["source"] for frame in frames] == ["报告R9→库L9"]
    assert [frame["content"] for frame in frames] == [material_step[PAYLOAD_REF_KEY]["summary"]]

    # 失败面：`tool` 帧 ＋ 步 payload 的 `error.reason`（与子问题账同源同值）
    refused_step = next(p for p in steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "refused")
    assert refused_step[PAYLOAD_ERROR_KEY] == {
        PAYLOAD_ERROR_CATEGORY_KEY: CATEGORY_REFUSED,
        PAYLOAD_ERROR_REASON_KEY: "台账无据——闸拒",
    }
    assert refused_step[PAYLOAD_REJECT_REASON_KEY] == refused_step[PAYLOAD_ERROR_KEY][
        PAYLOAD_ERROR_REASON_KEY
    ]  # 记账面与机读面同变量（不构第二套语义）
    assert accounts["refused"].error is not None
    assert accounts["refused"].error.reason == "台账无据——闸拒"
    tool_frames = await _event_frames(bus, "tool")
    assert [frame["status"] for frame in tool_frames] == ["ok", "failed", "ask"]
    assert tool_frames[1]["message"] == "台账无据——闸拒"

    # 缺参面：`ask` 帧 ＋ `pending_ask` ＋ 步 payload（挂起不是失败——`error` 留 None）
    missing_step = next(p for p in steps if p.get(PAYLOAD_SUBTASK_ID_KEY) == "missing")
    assert missing_step["status"] == "ask"  # 步面＝工具三态（挂起档）
    assert missing_step[PAYLOAD_ROW_COUNT_KEY] is None
    assert missing_step[PAYLOAD_REF_KEY] is None
    assert missing_step[PAYLOAD_ERROR_KEY] is None
    assert accounts["missing"].exec_status == EXEC_STATUS_NEED_INPUT  # 子问题档＝闭世界三值
    assert accounts["missing"].error is None
    assert state.pending_ask is not None
    assert [frame["frame"]["kind"] for frame in await _event_frames(bus, "ask")] == [ASK_CLARIFY]


# ── 行 18：【边界集】空结果／超大结果／限流失败／缺参 → 各自落到对应分支 ────────────


async def test_boundary_empty_huge_ratelimit_needinput() -> None:
    """行 18｜【边界集】四形各落对应分支、互不阻断（空结果／超大结果／限流失败／缺参）。"""
    huge = "边界正文\n" * 30 + "z" * _HUGE
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok()),  # 空结果
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游限流")),  # 限流首投
                _Reply(result=_failed(CATEGORY_RETRYABLE, "上游限流")),  # 限流同参重跑
            ],
            DOC_RETRIEVE: [
                _Reply(
                    result=_ok(
                        _tool_obs(huge, source="报告B→库B", source_id="frag-b", kind="fragment")
                    )
                ),
                _Reply(result=_ask()),
            ],
        }
    )
    matches = [
        _data_match("empty"),
        _knowledge_match("huge"),
        _data_match("ratelimit"),
        _knowledge_match("needinput"),
    ]
    state = _state(matches)
    store = RunStore(MemoryTables())
    outcome, bus = _run(state, registry, store=store)
    accounts = _by_id(outcome)

    # 空结果支：过程判 ok、业务判未答上（两档各自如实）
    assert accounts["empty"].exec_status == EXEC_STATUS_OK
    assert accounts["empty"].answered is False
    assert accounts["empty"].row_count == 0
    assert accounts["empty"].ref is None and accounts["empty"].error is None

    # 超大结果支：落引用（窗口只留摘要＋引用＋行数）＋可寻址＋披露
    assert accounts["huge"].exec_status == EXEC_STATUS_OK
    assert accounts["huge"].ref is not None
    assert store.read_ref(accounts["huge"].ref.handle).decode("utf-8") == huge

    # 限流失败支：retryable 档、只重跑一次、拒因如实
    assert accounts["ratelimit"].exec_status == EXEC_STATUS_FAILED
    assert accounts["ratelimit"].error is not None
    assert accounts["ratelimit"].error.category == CATEGORY_RETRYABLE
    assert "限流" in accounts["ratelimit"].error.reason
    assert state.tool_retries == {DATA_QUERY: 1}

    # 缺参支：`need_input` ＋ 挂起（不是失败）
    assert accounts["needinput"].exec_status == EXEC_STATUS_NEED_INPUT
    assert accounts["needinput"].error is None
    assert state.pending_ask is not None and state.pending_ask["kind"] == ASK_CLARIFY

    # 四形各落各支、同批互不阻断（不炸整批）
    assert [item.exec_status for item in outcome.subtasks] == [
        EXEC_STATUS_OK,
        EXEC_STATUS_OK,
        EXEC_STATUS_FAILED,
        EXEC_STATUS_NEED_INPUT,
    ]
    assert [item["type"] for item in state.notices] == ["material_truncated", "subtask_failed"]
    assert [frame["status"] for frame in await _event_frames(bus, "tool")] == [
        "ok",
        "ok",
        "failed",
        "ask",
    ]


# ── 行 19：【保留集】全成功时无额外信号、无回炉行为不变 ───────────────────────────


async def test_retention_all_ok_unchanged() -> None:
    """行 19｜【保留集】全成功批次：零额外信号（通知／拒／截断／闸／回喂／轮）＋回炉行为不变。"""
    matches = [_data_match("s1"), _knowledge_match("s2")]
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [_Reply(result=_ok(_tool_obs("行1"), _tool_obs("行2")))],
            DOC_RETRIEVE: [
                _Reply(result=_ok(_tool_obs("小片段", source="报告R→库L", kind="fragment")))
            ],
        }
    )
    state = _state(matches)
    outcome, bus = _run(state, registry)

    # 全成功：两账 ok、无失败／挂起、材料与答复各自如实
    assert [item.exec_status for item in outcome.subtasks] == [EXEC_STATUS_OK, EXEC_STATUS_OK]
    assert all(item.error is None and item.answered for item in outcome.subtasks)
    assert [item.row_count for item in outcome.subtasks] == [2, 1]
    assert [item.ref for item in outcome.subtasks] == [None, None]  # 小结果不落引用

    # 无额外信号：零通知／零回喂／零轮／零闸／零空手／零重试／零挂起
    assert state.notices == []
    assert state.decision_error == ""
    assert state.rounds == 0
    assert state.empty_probes == []
    assert state.tool_retries == {}
    assert state.pending_ask is None
    assert _gate_steps(state, GATE_EMPTY_PROBE) == []
    assert _gate_steps(state, GATE_SAME_PARAM_REPLAY) == []
    assert [frame["status"] for frame in await _event_frames(bus, "tool")] == ["ok", "ok"]
    # 三键在场且值诚实（无引用／无失败＝值 None，不是缺键）
    for payload in (dict(entry["payload"]) for entry in state.steps):
        assert payload[PAYLOAD_ROW_COUNT_KEY] is not None
        assert payload[PAYLOAD_REF_KEY] is None
        assert payload[PAYLOAD_ERROR_KEY] is None
        assert payload[PAYLOAD_REJECT_REASON_KEY] is None
    assert len(state.executed_payloads) == 2  # 成功实录（回炉比对面）

    # 回炉行为不变：重入不重跑、步面／通知面／轮面全静、实录不增（成功结果保留）
    carried = _ScriptedRegistry()
    rerun_state = _state(matches, subtask_results=list(state.subtask_results))
    rerun, _bus2 = _run(rerun_state, carried)
    assert carried.calls == []  # 成功不重跑
    assert rerun.observations == []  # 不重放已完成部分
    assert [item.exec_status for item in rerun.subtasks] == [EXEC_STATUS_OK, EXEC_STATUS_OK]
    assert [item.row_count for item in rerun.subtasks] == [2, 1]  # 账目沿用
    assert rerun_state.steps == []  # 回炉轮零新步
    assert rerun_state.notices == [] and rerun_state.decision_error == ""
    assert rerun_state.rounds == 0 and rerun_state.tool_retries == {}
    assert rerun_state.executed_payloads == []


# ── 织网义务①：B1 执行步半面的 L1 特征钉（不占规格表行序）────────────────────────


def test_execution_step_channel_normalized_form() -> None:
    """B1 执行步半面｜每步通道值归一形：步号连续 ＋ 三键恒在场 ＋ 值域形归一（全步种同形）。

    〔织网义务①（`RT-W4-05b-execution.md`）：B1「公共位与结果归一」的执行步半面 L1 特征钉——
    本块写出的每步通道值恒成归一形（供 checkpoint 快照／帧流对账），与两闸／失败／缺参／落引用
    全步种一致。〕
    """
    huge = "归一形正文\n" * 30 + "x" * _HUGE
    matches = [
        _data_match("ok"),
        _data_match("refused"),
        _knowledge_match("replay"),
        _knowledge_match("huge", question="渤中34-8 井史·大结果素材"),
    ]
    group = {
        "subtasks": [
            {"id": "ok", "question": "q", "ledger_notes": "注"},
            {"id": "refused", "question": "q", "ledger_notes": "注"},
            {"id": "replay", "question": "q", "ledger_notes": "注"},
            {"id": "huge", "question": "q", "ledger_notes": "注"},
            {"id": "gate_refuse", "question": "q", "ledger_notes": "注"},
            {"id": "gate_ask", "question": "q", "ledger_notes": "注"},
        ]
    }
    verdicts = [
        {"subtask_id": "ok", "decision": "allow"},
        {"subtask_id": "refused", "decision": "allow"},
        {"subtask_id": "replay", "decision": "allow"},
        {"subtask_id": "huge", "decision": "allow"},
        {"subtask_id": "gate_refuse", "decision": "refuse", "reason": {"human_text": "台账无据"}},
        {"subtask_id": "gate_ask", "decision": "ask", "reason": {"prompt": "请选口径"}},
    ]
    replay_need = {"question": "渤中34-8 井史", "anchors": ["BZ34-8"]}
    registry = _ScriptedRegistry(
        {
            DATA_QUERY: [
                _Reply(result=_ok(_tool_obs("行"))),
                _Reply(result=_failed(CATEGORY_REFUSED, "台账无据——闸拒")),
            ],
            DOC_RETRIEVE: [
                _Reply(
                    result=_ok(
                        _tool_obs(huge, source="报告C→库C", source_id="frag-c", kind="fragment")
                    )
                )
            ],
            SEMANTIC_QUERY: [_Reply(result=_ok())],
        }
    )
    state = _state(
        matches,
        question_group=group,
        precondition_verdicts=verdicts,
        executed_payloads=list(emission_fingerprints(None, replay_need)),  # 同参重投闸拦
        empty_probes=[discover_fingerprint(SEMANTIC_QUERY, {"question": "空手过"})],
        pending_discovers=[{"tool": SEMANTIC_QUERY, "args": {"question": "空手过"}}],
        resume_choices=[{"kind": ASK_CLARIFY, "choice": "近一月"}],
    )
    store = RunStore(MemoryTables())
    outcome, _bus = _run(state, registry, store=store)

    # 步号连续（公共位取号归一——`record_step` 内置取号，调用方零手加偏移）
    assert [entry["seq"] for entry in state.steps] == list(range(1, len(state.steps) + 1))
    # 全步种在场：恢复守卫／空手闸拒／成功／失败／同参重投闸拒／落引用／前置闸拒／前置 ask
    assert {str(entry["phase"]) for entry in state.process_notes} == {"tool"}
    assert any(entry["payload"].get(PAYLOAD_GATE_KEY) for entry in state.steps)
    assert any(entry["payload"].get(PAYLOAD_REF_KEY) for entry in state.steps)
    step_ids = {entry["payload"].get(PAYLOAD_SUBTASK_ID_KEY) for entry in state.steps}
    assert {"ok", "refused", "huge", "gate_refuse", "gate_ask"} <= step_ids
    gate_steps = [
        entry["payload"] for entry in state.steps if entry["payload"].get(PAYLOAD_GATE_KEY)
    ]
    assert {payload[PAYLOAD_GATE_KEY] for payload in gate_steps} == {
        GATE_EMPTY_PROBE,
        GATE_SAME_PARAM_REPLAY,
    }  # 两闸发射级拒步皆在场（拒步不带 subtask_id——两闸共享落地形，-05a 原样）
    assert _by_id(outcome)["huge"].ref is not None  # 落引用步实到（非空转）

    for entry in state.steps:
        payload = entry["payload"]
        assert payload[PAYLOAD_PHASE_KEY] == PHASE  # 相位面归一
        assert {PAYLOAD_ROW_COUNT_KEY, PAYLOAD_REF_KEY, PAYLOAD_ERROR_KEY} <= set(payload)
        assert payload[PAYLOAD_ROW_COUNT_KEY] is None or isinstance(
            payload[PAYLOAD_ROW_COUNT_KEY], int
        )
        ref = payload[PAYLOAD_REF_KEY]
        assert ref is None or set(ref) == {"handle", "summary", "row_count"}
        error = payload[PAYLOAD_ERROR_KEY]
        assert error is None or set(error) == {
            PAYLOAD_ERROR_CATEGORY_KEY,
            PAYLOAD_ERROR_REASON_KEY,
        }
        if isinstance(error, Mapping):
            assert error[PAYLOAD_ERROR_CATEGORY_KEY] in ERROR_CATEGORIES
            assert error[PAYLOAD_ERROR_REASON_KEY]
        # 归一形不变式：引用面与失败面互斥（一派遣要么落引用、要么落失败档）
        assert not (ref is not None and error is not None)
        if payload.get(PAYLOAD_GATE_KEY):  # 发射级拒＝工具未执行（三键值诚实为 None）
            assert ref is None and error is None
            assert payload[PAYLOAD_ROW_COUNT_KEY] is None
            assert payload[PAYLOAD_REJECT_REASON_KEY]


# ── 行为 16：收敛态零派遣（2026-10-17 EB3 D4.3）──────────────────────────────────


async def test_budget_hit_zero_dispatch() -> None:
    """行为 16｜收敛态零派遣：`budget_hit` 非空 → 零派遣、零工具调用、零步、零 `tool` 帧。

    收敛让位形（`specs/tool_matching.md` 接口定义「收敛让位形」）经编排既有路由会走到本相位
    （知识链支过闸为空却可能落「放行」）——本闸即兜该口：材料直答已在途（`bookkeeping.converge`
    落 `draft`），收敛态新支必不派遣（`specs/execution.md` 行为 16）。
    """
    matches = [_data_match("s1"), _knowledge_match("s2")]
    registry = _ScriptedRegistry({DATA_QUERY: [_Reply(result=_ok(_tool_obs("行")))]})
    state = _state(
        matches,
        pending_discovers=[{"tool": SEMANTIC_QUERY, "args": {"question": "空手形"}}],
    )
    state.budget_hit = ["rounds"]  # 触界收敛在途（同形拒因熔断落地形）
    steps_before = list(state.steps)

    bus = EventBus()
    outcome = execute(state, bus=bus, registry=registry)

    assert outcome.observations == [] and outcome.subtasks == []
    assert registry.calls == [], "收敛态仍派遣了工具"
    assert state.steps == steps_before, "收敛态零派遣须零步（收敛留痕归 bookkeeping.converge）"
    assert state.observations == []
    assert await _event_frames(bus, "tool") == [], "收敛态发 tool 帧（零动作面被破）"
