"""runtime.context —— Context Builder＋Manifest（specs/agent-loop.md 行为约定 2）。

模型每次调用前经 ContextBuilder 确定性编译：过滤→排序→预算→引用化——
- 过滤：notice 类观察（locator.kind=notice，闸依据/截断声明等元信息）不进模型面；
- 排序：信任级稳定序（agg 权威表 > 台账 > 检索）——同序保持入栈序（确定性）；
- 预算：max_observations 截断（截断显式写进 Manifest.selected_reason）；
- 引用化：[n] 引标＝全局观察序号（RunState.observations 稳定序），模型面与
  答案引用同一套序号（fail-closed 引用的机读底座）。

CompiledContext{messages, manifest}——manifest 七字段随 step 存档（过程态簿记）；
token_count 按 chars/4 估算（与网关记账兜底同口径）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from appv2.runtime.state import Manifest, RunState

# 信任级（骨架版确定性映射——细化批可调，语义不破：权威表最高）。
TRUST_AGG = "authoritative"
TRUST_LEDGER = "ledger"
TRUST_REPORT = "report"

_KIND_TRUST: dict[str, str] = {
    "agg_row": TRUST_AGG,
    "lineage": TRUST_AGG,
    "metric": TRUST_LEDGER,
    "term": TRUST_LEDGER,
    "object": TRUST_LEDGER,
    "relation": TRUST_LEDGER,
    "family_annotation": TRUST_LEDGER,
    "fragment": TRUST_REPORT,
    "graph": TRUST_REPORT,
    "notice": "notice",
}
_TRUST_RANK: dict[str, int] = {TRUST_AGG: 0, TRUST_LEDGER: 1, TRUST_REPORT: 2}

DEFAULT_MAX_OBSERVATIONS = 24

SYSTEM_PROMPT = (
    "你是油田数据问答助手。红线：1) 每条事实断言必须带 [n] 引标指向给定观察，"
    "无据不得断言；2) 多来源不一致时逐源列明，禁止无出处调和；3) 只依据给定观察"
    "回答，观察未覆盖的部分如实说明未找到。"
)


@dataclass(frozen=True, slots=True)
class CompiledContext:
    """确定性编译产物（messages 进模型；manifest 随 step 存档——过程态簿记）。"""

    messages: list[dict[str, str]]
    manifest: Manifest


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（locator.kind 确定性映射单点）。"""
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


@dataclass(slots=True)
class ContextBuilder:
    """确定性编译管线（过滤→排序→预算→引用化——行为约定 2 的单点实现）。"""

    max_observations: int = DEFAULT_MAX_OBSERVATIONS
    system_prompt: str = SYSTEM_PROMPT

    def compile(
        self,
        run_state: RunState,
        *,
        step: str,
        instruction: str,
    ) -> CompiledContext:
        """编译某步的模型上下文（纯函数——不触网、不改状态）。"""
        # 过滤：notice 类观察不进模型面（元信息走 notice 事件，非断言素材）。
        material = [
            obs for obs in run_state.observations
            if (obs.get("locator") or {}).get("kind") != "notice"
        ]
        # 排序：信任级稳定序（同序保持入栈序——确定性不抖动）。
        ordered = sorted(
            enumerate(material), key=lambda pair: _TRUST_RANK.get(trust_of(pair[1]), 9)
        )
        # 预算：截断显式（manifest selected_reason 载明）。
        truncated = len(ordered) > self.max_observations
        ordered = ordered[: self.max_observations]
        # 引用化：[n]＝全局观察序号（1 起）——模型面与答案引用同一套序号。
        blocks: list[str] = []
        source_types: list[str] = []
        source_ids: list[str] = []
        versions: list[str | None] = []
        trust_levels: list[str] = []
        for _, obs in ordered:
            index = int(obs["index"])
            trust = trust_of(obs)
            blocks.append(f"[{index}]（{trust}）{obs.get('content', '')}")
            source_types.append(str((obs.get("locator") or {}).get("kind", "")))
            source_ids.append(str(obs.get("source_id", "")))
            versions.append(obs.get("version"))
            trust_levels.append(trust)
        user_content = (
            f"问题：{run_state.question}\n"
            f"理解：{run_state.understanding or '（未产出）'}\n"
            f"观察材料：\n" + ("\n".join(blocks) if blocks else "（无）") +
            f"\n\n任务：{instruction}"
        )
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]
        reason = (
            f"步骤 {step}：信任级降序稳定排序；"
            + (f"预算 {self.max_observations} 支截断（{len(ordered)}/{len(material)}）"
               if truncated else f"全量入选（{len(ordered)} 支）")
        )
        manifest = Manifest(
            source_type=source_types,
            source_id=source_ids,
            version=versions,
            trust_level=trust_levels,
            selected_reason=reason,
            token_count=_estimate_tokens(messages[0]["content"] + messages[1]["content"]),
        )
        return CompiledContext(messages=messages, manifest=manifest)
