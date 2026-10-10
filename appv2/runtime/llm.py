"""runtime.llm —— 自写 ChatModel adapter（ADR-0002 红线②单点）。

GatewayChatModel（langchain BaseChatModel 子类）＝langgraph 六节点与
appv2 gateway.complete 之间的唯一桥：全部模型调用经本 adapter 走 gateway
complete（caller 归因逐调用保留＝`v2.runtime.<step>`——B6 记账/预算/审计
原样收口），禁止 langchain 自带 provider 直连（不 import 任何 provider 类）。

Completer＝gateway.complete 的结构性缝（生产传真 GatewayService——MiniMax
真引擎；测试传 ScriptedCompleter 剧本件）。消息形状双面转换单点
（BaseMessage→gateway dict；Completion→AIMessage＋usage 归位）。params 面
携 caller＋run_id（V2-33——run 归属随调用上行进 spend 账本）。

429 降级（V2-40）：_agenerate 对 completer.complete 装 429 退避重试≤3 次
（5s/20s/60s＋±10% 抖动，env GATEWAY_429_RETRIES/GATEWAY_429_BACKOFF 可
覆写）——判定与 registry duck 面同口径；非 429 原样上抛零行为变化；耗尽
后原异常上抛（run_failed 拒因语义不变）；每次重试 logger 留痕（次数/等待
时长）。registry.py:41 预留的「网关层重试/切备」分层位自此落码（工具层
同参重试与网关层重试是两层语义，互不冲突）。
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Any, Protocol, runtime_checkable

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from appv2.infra.gateway import Completion

# runtime 各模型调用的 caller 归因前缀（B6 记账 caller 列的 runtime 段）。
CALLER_PREFIX = "v2.runtime"

# ---------- V2-40 统一调用 429 降级（LLM 主调用链唯一触网口的退避重试） ----------

_RETRY_LOGGER = logging.getLogger(__name__)

# 退避参数缺省（票面：重试 ≤3 次，等待 5s/20s/60s；env 可覆写）。
GATEWAY_429_RETRIES_DEFAULT = 3
GATEWAY_429_BACKOFF_DEFAULT: tuple[float, ...] = (5.0, 20.0, 60.0)
GATEWAY_429_JITTER = 0.1  # 每次等待 ±10% 抖动（防限流窗口整点同步重撞）


def _configured_retries() -> int:
    """重试次数＝模块常量缺省，env GATEWAY_429_RETRIES（非负整数）覆写。

    调用时读取（非 import 时冻结）——env 变更即刻生效，测试可注入。
    """
    raw = os.environ.get("GATEWAY_429_RETRIES", "").strip()
    if not raw:
        return GATEWAY_429_RETRIES_DEFAULT
    try:
        return max(0, int(raw))
    except ValueError:
        return GATEWAY_429_RETRIES_DEFAULT


def _configured_backoff() -> tuple[float, ...]:
    """退避等待序列（秒）＝缺省 5/20/60，env GATEWAY_429_BACKOFF 逗号分隔覆写。"""
    raw = os.environ.get("GATEWAY_429_BACKOFF", "").strip()
    if not raw:
        return GATEWAY_429_BACKOFF_DEFAULT
    try:
        values = tuple(float(piece) for piece in raw.split(",") if piece.strip())
    except ValueError:
        return GATEWAY_429_BACKOFF_DEFAULT
    return values or GATEWAY_429_BACKOFF_DEFAULT


def _is_rate_limited(exc: BaseException) -> bool:
    """429 判定（与 registry.classify_exception duck 面同口径——V2-22 两面共用）。

    结构化面：异常携 status_code==429（真实 HTTP 形与测试桩同判）；文本面：
    异常消息/reason 含「429」（网关 UpstreamRejected 的 reason 由
    llm_client.classify_upstream_failure 单源格式化「上游拒绝 429:」——同仓
    内单源判据）。其余异常一律不重试。
    """
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status == 429:
        return True
    text = f"{getattr(exc, 'reason', '') or ''} {exc}"
    return "429" in text


async def _backoff_sleep(seconds: float) -> None:
    """退避等待缝（测试注入本函数即零真等——V2-40 验收「退避可测」）。"""
    await asyncio.sleep(seconds)


def _jittered(seconds: float) -> float:
    """等待时长加 ±10% 小抖动（防上游限流窗口整点同步重撞）。"""
    return seconds * (1.0 + random.uniform(-GATEWAY_429_JITTER, GATEWAY_429_JITTER))


@runtime_checkable
class Completer(Protocol):
    """gateway.complete 结构性缝（同形 GatewayService.complete——B6 唯一出口）。"""

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        caller: str,
        **params: Any,
    ) -> Completion: ...


_ROLE_BY_TYPE: dict[str, str] = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
}


def _message_to_dict(message: BaseMessage) -> dict[str, str]:
    role = _ROLE_BY_TYPE.get(message.type)
    if role is None:
        raise ValueError(f"不支持的 BaseMessage 类型：{message.type!r}")
    return {"role": role, "content": str(message.content)}


class GatewayChatModel(BaseChatModel):
    """自写 ChatModel adapter——全部 LLM 调用经 gateway.complete 的单点（红线②）。

    caller 归因：每个图节点持一个本 adapter 实例（caller=`v2.runtime.<step>`），
    网关账本逐调用可归因（B6 语义原样）。alias 传空＝网关按 routing.default 路由。
    run_id 归属盖章（V2-33）：GraphRunExecutor per-run 模型副本落值（executor._deps
    ——共享模型零变异），逐调用随 completer 协议 params 面上行进网关记账 run_id
    列；非 run 语境直建＝空串（网关归一 NULL，账本列不落空串）。
    """

    completer: Any  # Completer（runtime_checkable Protocol——pydantic arbitrary 型）
    caller: str
    alias: str = ""
    run_id: str = ""  # run 归属盖章（executor per-run 落值——spend 账本归属链）

    @property
    def _llm_type(self) -> str:
        return "gateway-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError("runtime 只走异步面（ainvoke）——同步生成不支持")

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        gateway_messages = [_message_to_dict(message) for message in messages]
        # V2-40：429 退避重试（首调＋≤3 重试）只在此包裹——非 429 原样上抛
        # 零行为变化；耗尽后原异常上抛（run_failed 拒因语义不变——诚实失败
        # 不冒充成功）；每次重试 logger 留痕（次数/等待时长，可溯）。
        retries = _configured_retries()
        backoff = _configured_backoff()
        completion: Completion | None = None
        for attempt in range(retries + 1):
            try:
                completion = await self.completer.complete(
                    self.alias, gateway_messages, caller=self.caller, run_id=self.run_id
                )
                break
            except Exception as exc:
                if not _is_rate_limited(exc) or attempt >= retries:
                    raise
                wait = _jittered(backoff[min(attempt, len(backoff) - 1)])
                _RETRY_LOGGER.warning(
                    "429 退避重试：caller=%s 第 %d/%d 次，等待 %.2fs（异常：%s）",
                    self.caller,
                    attempt + 1,
                    retries,
                    wait,
                    exc,
                )
                await _backoff_sleep(wait)
        assert completion is not None  # 循环出口必经 break（交付）或 raise——类型收窄
        message = AIMessage(
            content=completion.content,
            additional_kwargs={
                "call_id": completion.call_id,
                "served_alias": completion.served_alias,
                "cost_yuan": completion.cost_yuan,
                "fallback": completion.fallback,
            },
            response_metadata={
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "usage_estimated": completion.usage_estimated,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=message)])
