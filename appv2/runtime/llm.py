"""runtime.llm —— 自写 ChatModel adapter（ADR-0002 红线②单点）。

GatewayChatModel（langchain BaseChatModel 子类）＝langgraph 六节点与
appv2 gateway.complete 之间的唯一桥：全部模型调用经本 adapter 走 gateway
complete（caller 归因逐调用保留＝`v2.runtime.<step>`——B6 记账/预算/审计
原样收口），禁止 langchain 自带 provider 直连（不 import 任何 provider 类）。

Completer＝gateway.complete 的结构性缝（生产传真 GatewayService——MiniMax
真引擎；测试传 ScriptedCompleter 剧本件）。消息形状双面转换单点
（BaseMessage→gateway dict；Completion→AIMessage＋usage 归位）。params 面
携 caller＋run_id（V2-33——run 归属随调用上行进 spend 账本）。
"""

from __future__ import annotations

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
        completion = await self.completer.complete(
            self.alias, gateway_messages, caller=self.caller, run_id=self.run_id
        )
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
