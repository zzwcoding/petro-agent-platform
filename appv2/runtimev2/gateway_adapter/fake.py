"""runtimev2.gateway_adapter.fake —— 剧本化 completer（模块卡 Seam 点名的测试替身）。

ScriptedCompleter：按 caller 分流的应答罐头——每个 caller 一条回答队列（多轮
replay：同 caller 第二次调用取队列第二条，末条驻留），全部调用留痕（caller＋
messages 全量捕获——断言面）。等价能力承接旧 appv2/runtime/fake.py（R5：旧码
只读参考、不引）——48 个存量离线测试改接线的地基件（eng/04-测试网设计.md §五
步骤 1：gateway_adapter 测试替身＋leg 回放 harness 两件地基）。

与旧件的能力差异：
- 公开面按卡收窄：`complete(messages, caller) -> str`（旧件
  `complete(alias, messages, *, caller, **params) -> Completion`——alias/params/
  run_id 盖章面随阶段 3 规格定，不在本替身自创）；
- default 兜底（可选）：未剧本化 caller 在 default 在场时回 default（调用照
  留痕——兜底不静默丢）；default 未设时当场 AssertionError——「剧本耗尽当场
  暴露」纪律与旧件一致。

【接口待规格回写】gateway_adapter 的正式十节规格尚未写（阶段 3 在途）：本替身
按 specs/modules.md gateway_adapter 卡「公开接口」实现为同步 `def`；规格若定
async／增补 params 面，随规格回写同步调整本件与包根导出。

只读（INV-2 同款）：应答罐头不改注入剧本（构造即拷贝）；调用计数/留痕是观测面
不是写路径。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class ScriptedCompleter:
    """剧本化 completer——caller 分流＋逐 caller 回答队列（多轮 replay）。"""

    def __init__(
        self,
        script: Mapping[str, Sequence[str]],
        *,
        default: str | None = None,
    ) -> None:
        self._script = {caller: list(replies) for caller, replies in script.items()}
        self._default = default
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def complete(self, messages: Sequence[Mapping[str, str]], caller: str) -> str:
        """按 caller 取剧本应答；未剧本化且无 default＝当场暴露（不静默兜底）。"""
        self.calls.append((caller, [dict(m) for m in messages]))
        queue = self._script.get(caller)
        if not queue:
            if self._default is None:
                raise AssertionError(
                    f"ScriptedCompleter 剧本耗尽：caller={caller!r} 未剧本化应答"
                    "（default 兜底未设——当场暴露，不静默）"
                )
            return self._default
        return queue.pop(0) if len(queue) > 1 else queue[0]

    def counts(self) -> dict[str, int]:
        """per-caller 调用计数桶（观测面——机读断言用，零写路径）。"""
        buckets: dict[str, int] = {}
        for caller, _messages in self.calls:
            buckets[caller] = buckets.get(caller, 0) + 1
        return buckets

    def messages_of(self, caller: str) -> list[list[dict[str, str]]]:
        """指定 caller 的逐轮消息回看（第 n 轮＝第 n 次调用的 messages 副本列）。"""
        return [list(messages) for hit_caller, messages in self.calls if hit_caller == caller]
