"""V2-40 统一 LLM 调用 429 降级——GatewayChatModel._agenerate 退避重试钉测。

链路合同（tickets/v2/V2-40-统一调用429降级.md）：全仓唯一 LLM 触网口
`GatewayChatModel._agenerate`（B6 单出口 completer.complete 包裹面）装 429
退避重试——429 判定与 registry duck 面同口径（异常消息/reason 含 429，或
结构化 status_code==429）→ 退避重试 ≤3 次（5s/20s/60s＋小抖动；模块常量可
env 覆写 GATEWAY_429_RETRIES / GATEWAY_429_BACKOFF）；非 429 异常原样上抛
零行为变化；重试耗尽后原异常上抛（run_failed 拒因语义不变——诚实失败不
冒充成功）；每次重试日志留痕（次数/等待时长）可溯。

退避等待走模块缝 `_backoff_sleep`——测试注入即零真等；env 覆写经
monkeypatch.setenv（调用时读取，非 import 时冻结）。

**B7b 存量改写（eng/04 §三 B7b 行，落 RT-W2-03a）**：本件「非 429 不重试」钉原含
「网络错一次即抛」断言，与新 `gateway_adapter` 规格行为 6「网络错可重试」语义相抵
（复审⑦ V5）——该半面按新规格改写，可重试断言归新块验收件
`tests/domains/test_v2_gateway_adapter.py::retry_only_on_retryable`；本件只看守旧码
（`appv2/runtime/llm.py`）仍成立的「非 429 且非可切备类＝一次即抛」。
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.messages import HumanMessage

import appv2.runtime.llm as llm_module
from appv2.infra.gateway import Completion
from appv2.infra.llm_client import UpstreamRejected
from appv2.runtime.llm import GatewayChatModel

CALLER = "v2.runtime.understand"
RETRY_LOGGER = "appv2.runtime.llm"


def _completion(content: str = "理解：x\n指标候选：无") -> Completion:
    return Completion(
        content=content,
        prompt_tokens=4,
        completion_tokens=4,
        usage_estimated=False,
        call_id="call-test-429",
        cost_yuan=0.0,
        fallback=False,
        served_alias="petro-main",
    )


class _Status429Error(Exception):
    """duck 型面桩——带结构化 status_code=429（真实 HTTP 形同判）。"""

    def __init__(self) -> None:
        super().__init__("HTTP 429: rate limited")
        self.status_code = 429


class _ScriptedFailureCompleter:
    """按次序抛错的剧本 completer——第 n 次调用抛 failures[n-1]，其后交付。"""

    def __init__(self, failures: Sequence[Exception]) -> None:
        self._failures = list(failures)
        self.calls = 0

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        caller: str,
        **params: Any,
    ) -> Completion:
        self.calls += 1
        if self.calls <= len(self._failures):
            raise self._failures[self.calls - 1]
        return _completion()


@pytest.fixture()
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """退避等待注入面——记录每次等待时长，零真等。"""
    recorded: list[float] = []

    async def _instant_sleep(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(llm_module, "_backoff_sleep", _instant_sleep, raising=False)
    return recorded


def _model(completer: _ScriptedFailureCompleter) -> GatewayChatModel:
    return GatewayChatModel(completer=completer, caller=CALLER, alias="")


async def test_429_twice_then_success_three_calls_one_delivery(
    sleeps: list[float],
) -> None:
    """429 连抛 2 次后成功＝调用 3 次恰一次交付；退避按 5s/20s 等待（±10% 抖动）。"""
    completer = _ScriptedFailureCompleter(
        [_Status429Error(), UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError")]
    )
    result = await _model(completer).agenerate([[HumanMessage(content="日产油量")]])
    assert completer.calls == 3, f"应重试至第 3 次成功，实调 {completer.calls} 次"
    # 恰一次交付（两连败后第三次成功——LLMResult generations[0][0] 原样出）。
    assert result.generations[0][0].message.content == "理解：x\n指标候选：无"
    # 退避等待可测：两次等待落在 5s/20s 的 ±10% 抖动带内，零真等。
    assert len(sleeps) == 2
    assert 4.5 <= sleeps[0] <= 5.5
    assert 18.0 <= sleeps[1] <= 22.0


async def test_persistent_429_exhausts_four_calls_original_exc_reraised(
    sleeps: list[float],
) -> None:
    """持续 429＝4 次调用（首调＋3 重试）后原异常上抛——run_failed 语义不变。"""
    failures = [
        UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError") for _ in range(4)
    ]
    completer = _ScriptedFailureCompleter(failures)
    with pytest.raises(UpstreamRejected) as excinfo:
        await _model(completer).ainvoke([HumanMessage(content="日产油量")])
    assert completer.calls == 4, f"应打满首调＋3 重试，实调 {completer.calls} 次"
    assert excinfo.value is failures[3], "耗尽后必须原异常上抛（不得换形/包装）"
    assert len(sleeps) == 3
    assert 4.5 <= sleeps[0] <= 5.5
    assert 18.0 <= sleeps[1] <= 22.0
    assert 54.0 <= sleeps[2] <= 66.0


async def test_non_429_no_retry_single_call(sleeps: list[float]) -> None:
    """非 429 异常不重试＝调用 1 次、原异常上抛、零退避等待。

    **B7b 存量改写（eng/04 §三 B7b 行，落 RT-W2-03a）**：本钉原断言含「网络错
    （`UpstreamUnavailable`）一次即抛」——与新 `gateway_adapter` 规格行为 6
    「网络错可重试」**语义相抵**（复审⑦ V5），故该半面按新规格改写：网络错／超时／
    5xx 的**可重试断言**归 `tests/domains/test_v2_gateway_adapter.py::retry_only_on_retryable`
    （新块唯一出口面管辖）；本件只留旧码确实不重试的类别（非 429 且非可切备类）。
    """
    failure = ValueError("计划或参数错误")
    completer = _ScriptedFailureCompleter([failure])
    with pytest.raises(ValueError) as excinfo:
        await _model(completer).ainvoke([HumanMessage(content="日产油量")])
    assert completer.calls == 1, "ValueError 不应重试"
    assert excinfo.value is failure
    assert sleeps == [], "非 429 零退避等待"


async def test_retry_leaves_log_trace(
    sleeps: list[float], caplog: pytest.LogCaptureFixture
) -> None:
    """重试留痕断言在场：每次重试日志携 429、重试序号（1/3）与等待时长。"""
    completer = _ScriptedFailureCompleter(
        [_Status429Error(), UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError")]
    )
    with caplog.at_level(logging.WARNING, logger=RETRY_LOGGER):
        await _model(completer).ainvoke([HumanMessage(content="日产油量")])
    traces = [r.getMessage() for r in caplog.records if r.name == RETRY_LOGGER]
    assert len(traces) == 2, f"两次重试应各留一条痕，实得 {len(traces)} 条"
    assert all("429" in text for text in traces)
    assert any("1/3" in text for text in traces), "首条留痕应携重试序号 1/3"
    assert any("2/3" in text for text in traces), "次条留痕应携重试序号 2/3"
    assert any(f"等待 {sleeps[0]:.2f}s" in text for text in traces), "留痕应携等待时长"


async def test_env_overrides_retry_count_and_backoff(
    sleeps: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    """模块常量可 env 覆写：GATEWAY_429_RETRIES=1／GATEWAY_429_BACKOFF=0.25。"""
    monkeypatch.setenv("GATEWAY_429_RETRIES", "1")
    monkeypatch.setenv("GATEWAY_429_BACKOFF", "0.25")
    completer = _ScriptedFailureCompleter(
        [UpstreamRejected("petro-main", "上游拒绝 429: RateLimitError") for _ in range(2)]
    )
    with pytest.raises(UpstreamRejected):
        await _model(completer).ainvoke([HumanMessage(content="日产油量")])
    assert completer.calls == 2, "覆写后＝首调＋1 重试"
    assert sleeps == [pytest.approx(0.25, rel=0.1)]  # 唯一等待＝覆写值（±10% 抖动带）
