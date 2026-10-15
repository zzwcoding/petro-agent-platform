"""runtimev2.gateway_adapter.fake —— 剧本化 completer（模块卡 Seam 点名的测试替身）。

ScriptedCompleter：按 caller 分流的应答罐头——每个 caller 一条回答队列（多轮
replay：同 caller 第二次调用取队列第二条，末条驻留），全部调用留痕（caller＋
messages 全量捕获——断言面）。等价能力承接旧 appv2/runtime/fake.py（R5：旧码
只读参考、不引）——存量离线测试改接线的地基件（eng/04-测试网设计.md §五步骤 1：
gateway_adapter 测试替身＋leg 回放 harness 两件地基）。

接口面（2026-10-15 随阶段 3 规格回写，与 specs/modules.md 的 `## gateway_adapter`
卡逐字对齐）：
- `async def complete(messages, *, caller, run_id) -> ModelReply`——与生产桥**同面**；
- 回执 `ModelReply` 的用量字段由剧本件按字符数粗算填充（离线确定性、零网络；
  上游未上报的 `cached_tokens` 恒 0——与钉 `pin-25` 同口径）；
- 观测面：`calls`／`counts()`／`messages_of(caller)`（只读，不改注入剧本）；
- `default` 兜底（可选）：未剧本化 caller 在 default 在场时回 default（调用照留痕
  ——兜底不静默丢）；default 未设时当场 AssertionError——「剧本耗尽当场暴露」纪律。

只读（INV-2 同款）：应答罐头不改注入剧本（构造即拷贝）；调用计数/留痕是观测面，
不是写路径。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelReply:
    """一次模型调用的回执（形状真源＝规格接口定义；用量字段供调用记账）。"""

    content: str
    caller: str
    run_id: str
    alias: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    usage_estimated: bool = True
    duration_ms: int = 0
    error: str | None = None


class ScriptedCompleter:
    """剧本化 completer——caller 分流＋逐 caller 回答队列（多轮 replay）。"""

    def __init__(
        self,
        script: Mapping[str, Sequence[str]],
        *,
        default: str | None = None,
        alias: str = "",
    ) -> None:
        self._script = {caller: list(replies) for caller, replies in script.items()}
        self._default = default
        self._alias = alias
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    async def complete(
        self,
        messages: Sequence[Mapping[str, str]],
        *,
        caller: str,
        run_id: str = "",
    ) -> ModelReply:
        """按 caller 取剧本应答；未剧本化且无 default＝当场暴露（不静默兜底）。"""
        self.calls.append((caller, [dict(m) for m in messages]))
        queue = self._script.get(caller)
        if not queue:
            if self._default is None:
                raise AssertionError(
                    f"ScriptedCompleter 剧本耗尽：caller={caller!r} 未剧本化应答"
                    "（default 兜底未设——当场暴露，不静默）"
                )
            content = self._default
        else:
            content = queue.pop(0) if len(queue) > 1 else queue[0]
        prompt_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return ModelReply(
            content=content,
            caller=caller,
            run_id=run_id,
            alias=self._alias,
            prompt_tokens=prompt_chars // 4,
            completion_tokens=len(content) // 4,
            cached_tokens=0,
            usage_estimated=True,
        )

    def counts(self) -> dict[str, int]:
        """per-caller 调用计数桶（观测面——机读断言用，零写路径）。"""
        buckets: dict[str, int] = {}
        for caller, _messages in self.calls:
            buckets[caller] = buckets.get(caller, 0) + 1
        return buckets

    def messages_of(self, caller: str) -> list[list[dict[str, str]]]:
        """指定 caller 的逐轮消息回看（第 n 轮＝第 n 次调用的 messages 副本列）。"""
        return [list(messages) for hit_caller, messages in self.calls if hit_caller == caller]
