"""V2-33 服务侧 run_id 盖章——调用面钉测（runtime 侧）。

链路合同（tickets/v2/V2-33）：GraphRunExecutor per-run 模型副本携 run 号
（executor._deps 盖章——共享模型字典零变异，并发 run 各持副本无交叉）→
GatewayChatModel._agenerate 把 run_id 进 completer 协议 params 面（无条件携——
空串＝无 run 语境，gateway 侧归一 NULL 列）→ GatewayService._settle 写账。

本文件钉「调用面逐调用携 run_id」一环；gateway 写账钉测在
tests/infra/test_v2_gateway_runid.py，rerun 归集面钉测在 tests/tools/test_rerun_spend.py，
真账本实证走 RUNTIME_SMOKE（tests/api/test_v2_runtime_smoke_real.py ⑤ 节）。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from langchain_core.messages import HumanMessage

from appv2.runtime import AskChoice, AskRequest, RunStore, ScriptedCompleter
from appv2.runtime.llm import GatewayChatModel
from tests.domains.test_v2_agent_loop import (
    ACTOR,
    ANSWER_DRAFT_CITED,
    DECISION_FINALIZE,
    DECISION_WINDOWED,
    HAPPY_QUESTION,
    HAPPY_SCRIPT,
    UNDERSTAND_DATA,
    QueueQueryEngine,
    drain,
    make_runtime,
)
from tests.domains.test_v2_react_loop import DECISION_ASK_TARGET, _rows_outcome

# 挂起→恢复全剧本：ask 发射→挂起→resume→带窗执行→finalize→起草（单 runtime 两段）。
_CLARIFY_SCRIPT: dict[str, Sequence[str]] = {
    "v2.runtime.understand": [UNDERSTAND_DATA],
    "v2.runtime.decision": [DECISION_ASK_TARGET, DECISION_WINDOWED, DECISION_FINALIZE],
    "v2.runtime.answer": [ANSWER_DRAFT_CITED],
}


async def test_gateway_chat_model_carries_run_id_param() -> None:
    """adapter 单测：run_id 落值的模型逐调用把 run_id 进 completer 协议 params。"""
    completer = ScriptedCompleter({"v2.runtime.understand": ["理解：x\n指标候选：无"]})
    model = GatewayChatModel(
        completer=completer, caller="v2.runtime.understand", alias="", run_id="run-abc123"
    )
    await model.ainvoke([HumanMessage(content="问句")])
    assert completer.params, "completer 未捕获调用 params"
    assert completer.params[0].get("run_id") == "run-abc123"


async def test_gateway_chat_model_default_run_id_empty_string() -> None:
    """缺省（非 run 语境直建）＝空串照传——调用形确定（gateway 归一 NULL，不落空串列）。"""
    completer = ScriptedCompleter({"v2.runtime.understand": ["理解：x\n指标候选：无"]})
    model = GatewayChatModel(completer=completer, caller="v2.runtime.understand", alias="")
    await model.ainvoke([HumanMessage(content="问句")])
    assert completer.params[0].get("run_id") == ""


async def test_executor_stamps_every_model_call_with_run_id(tmp_path: Path) -> None:
    """ask 全链：每个模型调用的 run_id 与本 run session 号全等（acceptance 主链）。"""
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle)
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "completed"
        assert completer.calls, "剧本 completer 零调用——装配断"
        assert completer.params, "completer 未捕获 params（fake 观测面缺位）"
        assert len(completer.params) == len(completer.calls)
        assert handle.run_id.startswith("run-")
        assert all(p.get("run_id") == handle.run_id for p in completer.params), (
            f"模型调用 run_id 盖章不齐：{[p.get('run_id') for p in completer.params]}"
        )
    finally:
        await db.dispose()


async def test_stamp_tracks_each_run_not_stuck(tmp_path: Path) -> None:
    """同 runtime 先后两 run：前段调用章＝run1、后段＝run2——per-run 副本非首跑钉死。"""
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=HAPPY_SCRIPT
    )
    try:
        handle_a = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle_a)
        calls_after_a = len(completer.calls)
        handle_b = await runtime.ask(AskRequest(question=HAPPY_QUESTION, actor=ACTOR))
        await drain(handle_b)
        assert handle_a.run_id != handle_b.run_id
        first_segment = completer.params[:calls_after_a]
        second_segment = completer.params[calls_after_a:]
        assert first_segment and second_segment
        assert all(p.get("run_id") == handle_a.run_id for p in first_segment)
        assert all(p.get("run_id") == handle_b.run_id for p in second_segment)
    finally:
        await db.dispose()


async def test_resume_segment_carries_same_run_id(tmp_path: Path) -> None:
    """澄清挂起→resume：恢复段模型调用章与本 run session 号全等（恢复路径不脱章）。"""
    runtime, completer, db = await make_runtime(
        tmp_path, engine=QueueQueryEngine([_rows_outcome()]), script=_CLARIFY_SCRIPT
    )
    store = RunStore(db)
    try:
        handle = await runtime.ask(AskRequest(question="日产油量", actor=ACTOR))
        suspended = await drain(handle)
        assert any(e.event == "ask" for e in suspended), "澄清 ask 帧未发出——挂起路径断"
        run = await store.get_run(handle.run_id)
        assert run is not None and run.status == "waiting_ask"
        resumed = await runtime.resume(handle.run_id, AskChoice(value="N-01 井"))
        await drain(resumed)
        final = await store.get_run(handle.run_id)
        assert final is not None and final.status == "completed"
        assert completer.params
        assert all(p.get("run_id") == handle.run_id for p in completer.params), (
            f"恢复段盖章不齐：{[p.get('run_id') for p in completer.params]}"
        )
    finally:
        await db.dispose()
