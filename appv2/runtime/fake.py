"""runtime.fake —— 剧本化 completer（modules.md runtime 卡点名的测试 adapter）。

ScriptedCompleter：按 caller 分流的应答罐头——每个 caller 一条回答队列（多轮
replay：同 caller 第二次调用取队列第二条，末条驻留），全部调用留痕（caller＋
messages 全量捕获——断言面）。P-006 runtime 侧五条验收与 P-007 api 测试复用
同一件。

只读（INV-2）：应答罐头不改注入剧本；调用计数是观测面不是写路径。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from appv2.infra.gateway import Completion


class ScriptedCompleter:
    """剧本化 completer——caller 分流＋逐 caller 回答队列（多轮 replay）。"""

    def __init__(
        self,
        script: Mapping[str, Sequence[str]],
        *,
        alias: str = "petro-main",
    ) -> None:
        self._script = {caller: list(replies) for caller, replies in script.items()}
        self._alias = alias
        self.calls: list[tuple[str, list[dict[str, str]]]] = []
        self._serial = 0

    async def complete(
        self,
        alias: str,
        messages: list[dict[str, str]],
        *,
        caller: str,
        **params: Any,
    ) -> Completion:
        """按 caller 取剧本应答（队列耗尽＝装配缺应答当场暴露——不静默兜底）。"""
        self.calls.append((caller, [dict(m) for m in messages]))
        self._serial += 1
        queue = self._script.get(caller)
        if not queue:
            raise AssertionError(
                f"ScriptedCompleter 剧本耗尽：caller={caller!r} 未剧本化应答"
            )
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        return Completion(
            content=reply,
            prompt_tokens=sum(len(str(m.get("content", ""))) for m in messages) // 4,
            completion_tokens=len(reply) // 4,
            usage_estimated=False,
            call_id=f"call-scripted-{self._serial}",
            cost_yuan=0.0,
            fallback=False,
            served_alias=alias or self._alias,
        )
