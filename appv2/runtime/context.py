"""runtime.context —— Context Builder＋Manifest（specs/agent-loop.md 行为约定 2）。

模型每次调用前经 ContextBuilder 确定性编译（ADR-0006/V2-38 消息历史簿记形态）：

- 簿记：消息列表＝[system]＋RunState.history＋当前 user 轮——understand/decision/
  answer 的调用与输出、工具执行台账（参数 → 结果：N 行／分型拒因：校验拒／
  暂不可用／闸拒）、拒因回
  喂、用户澄清/审批回收全部由图节点写入 history；后续每步在完整历史上续写，
  不再每步把 run 状态重序列化成单条 user（伪多轮形态退役——P-026 复测 9/16 题
  同参重投的根因即「模型没有记忆自己做过的事」）；
- 材料：观察材料段（[n] 引标视图）随当前轮渲染（decision/answer 步）——引标＝
  全局观察序号（RunState.observations 稳定序），模型面与答案引用同一套序号
  （fail-closed 引用的机读底座，语义零漂移）；notice 类观察仍不进模型面；
- 排序：材料信任级稳定序（agg 权威表 > 台账 > 检索）——同序保持入栈序（确定性）；
- 预算：双层——观察材料 max_observations 支截断＋历史 token 预算
  （max_context_tokens，chars/4 估算；超限确定性截断＝首问轮与当前轮保留、
  最旧中间轮先弃），两处截断均显式写进 Manifest.selected_reason（不静默）。

CompiledContext{messages, manifest}——manifest 七字段随 step 存档（过程态簿记）；
token_count 按 chars/4 估算（与网关记账兜底同口径），计全消息实量。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from appv2.runtime.state import Manifest, RunState
from appv2.tools.ledger import RESIDENT_BLOCK_BEGIN, RESIDENT_BLOCK_END

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
# 历史 token 预算合同值（chars/4 估算口径；测试可收窄——合同值不因测试改动）。
DEFAULT_MAX_CONTEXT_TOKENS = 12000

SYSTEM_PROMPT = (
    "你是油田数据问答助手。红线：1) 每条事实断言必须带 [n] 引标指向给定观察，"
    "无据不得断言；2) 材料含多个来源（不同报告／油田／井）时逐个来源分别作答——"
    "即使各源不冲突也要分别列出，不得只取其一，也不以反问代替作答；作答后仍有未"
    "覆盖的来源要如实点名（便于用户补充检索）；禁止无出处调和；3) 只依据给定观察"
    "回答，观察未覆盖的部分如实说明未找到。"
)

# V2-53 附 B 逐字稿（台账全量块的「字典不是数据」头注——常驻块 BEGIN 标记后
# 首行，位于 BEGIN/END 标记之间：历史簿记 _slim_resident 整块收窄自动覆盖）。
LEDGER_DICT_NOTE = (
    "（台账全量是字典不是数据：本块只载指标/术语/对象的定义、粒度与绑定态，"
    "不载任何数值——「在台账」不等于「数值在手」；数值一律经检索执行取得，"
    "禁止仅凭本块 finalize 定稿。）"
)


@dataclass(frozen=True, slots=True)
class CompiledContext:
    """确定性编译产物（messages 进模型；manifest 随 step 存档——过程态簿记）。

    messages＝[system, *历史轮（RunState.history 截断后）, 当前 user 轮]——
    多轮对话形态（ADR-0006）；图节点经 messages[-1] 取回当前轮原样落史。
    """

    messages: list[dict[str, str]]
    manifest: Manifest


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（locator.kind 确定性映射单点）。"""
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _fit_history(
    turns: list[dict[str, str]], max_tokens: int
) -> tuple[list[dict[str, str]], int]:
    """历史 token 预算截断（确定性——token 预算/截断策略单点，V2-38 任务 4）。

    首问轮（turns[0]——对话源头）与当前轮（turns[-1]）恒保留；超限时最旧的
    中间轮先弃，直至入预算或只剩两轮。返回（保留轮, 弃置数）。
    """
    def _total(items: list[dict[str, str]]) -> int:
        return sum(_estimate_tokens(str(item.get("content", ""))) for item in items)

    if _total(turns) <= max_tokens:
        return turns, 0
    kept = list(turns)
    dropped = 0
    while len(kept) > 2 and _estimate_tokens(
        "".join(str(item.get("content", "")) for item in kept)
    ) > max_tokens:
        kept.pop(1)
        dropped += 1
    return kept, dropped


@dataclass(slots=True)
class ContextBuilder:
    """确定性编译管线（簿记→材料渲染→双层预算→引用化——行为约定 2 的单点实现）。"""

    max_observations: int = DEFAULT_MAX_OBSERVATIONS
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
    system_prompt: str = SYSTEM_PROMPT

    def compile(
        self,
        run_state: RunState,
        *,
        step: str,
        instruction: str,
        with_material: bool = True,
        extra_sources: list[dict[str, str]] | None = None,
    ) -> CompiledContext:
        """编译某步的模型上下文（纯函数——不触网、不改状态）。

        instruction＝当前 user 轮正文（任务/指令段）；with_material＝是否随轮
        渲染观察材料段（understand 步 False——理解任务不消费材料）。多轮形态：
        消息列表＝[system]＋历史轮（token 预算截断后）＋当前轮。
        extra_sources＝常驻注入块（V2-34 词典层第 1 轮全量注入——每块
        {source_type, source_id, label, content}，渲染进当前轮＋Manifest
        source_type 记 ledger_dump 族来源行；非懒加载——注入不依赖未命中）。
        """
        current = instruction
        extra = list(extra_sources or [])
        if extra:
            extra_blocks = [
                f"【{item.get('label', item.get('source_type', ''))}】\n"
                f"{item.get('content', '')}"
                for item in extra
            ]
            # 常驻注入整块（ledger_dump 族——首尾标记供历史簿记收窄：常驻材料
            # 不重复入史，防多轮 token 放大；非懒加载——每轮常驻在场）。
            current += (
                "\n\n" + RESIDENT_BLOCK_BEGIN + "\n"
                + LEDGER_DICT_NOTE + "\n"
                + "\n\n".join(extra_blocks) + "\n" + RESIDENT_BLOCK_END
            )
        if with_material:
            # 过滤：notice 类观察不进模型面（元信息走 notice 事件，非断言素材）。
            material = [
                obs for obs in run_state.observations
                if (obs.get("locator") or {}).get("kind") != "notice"
            ]
            # 排序：信任级稳定序（同序保持入栈序——确定性不抖动）。
            ordered = sorted(
                enumerate(material), key=lambda pair: _TRUST_RANK.get(trust_of(pair[1]), 9)
            )
            # V2-61 分承载体预算：权威/台账承载体（agg_row/lineage/metric/term/…）
            # 是引擎封顶输出（agg 行集 limit_effective ≤ QUERY_LIMIT_CAP=200 引擎侧
            # 已截；台账卡 ≤ discover 预算 10 支量级），装配不再重复封顶——Owner
            # 2026-10-12 裁决「出口明细 ≤50＝系统设定」的落实面；检索承载体
            # （fragment/graph）体量无上界，保留支数帽（token 安全面）。
            authority = [pair for pair in ordered if trust_of(pair[1]) != TRUST_REPORT]
            reports = [pair for pair in ordered if trust_of(pair[1]) == TRUST_REPORT]
            truncated = len(reports) > self.max_observations
            ordered = authority + reports[: self.max_observations]
            # 引用化：[n]＝全局观察序号（1 起）——模型面与答案引用同一套序号。
            blocks: list[str] = []
            source_types: list[str] = []
            source_ids: list[str] = []
            versions: list[str | None] = []
            trust_levels: list[str] = []
            for _, obs in ordered:
                index = int(obs["index"])
                trust = trust_of(obs)
                # V2-64 出处随材料：信任级｜报告名（source）｜本体标签（well）——
                # 让模型分得清每支材料属于哪个报告/对象（缺省逐段省略，零漂移）。
                origin = str(obs.get("source") or "").strip()
                well = str(obs.get("well") or "").strip()
                label = "｜".join(part for part in (trust, origin, well) if part)
                blocks.append(f"[{index}]（{label}）{obs.get('content', '')}")
                source_types.append(str((obs.get("locator") or {}).get("kind", "")))
                source_ids.append(str(obs.get("source_id", "")))
                versions.append(obs.get("version"))
                trust_levels.append(trust)
            current += (
                "\n\n观察材料：\n" + ("\n".join(blocks) if blocks else "（无）")
                + (
                    f"\n（材料披露：检索片段共 {len(reports)} 支，本轮渲染前 "
                    f"{min(len(reports), self.max_observations)} 支——未渲染片段不在"
                    "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）"
                    if truncated
                    else ""
                )
            )
            material_reason = (
                f"步骤 {step}：信任级降序稳定排序；权威 {len(authority)} 支全量；"
                + (
                    f"检索片段帽 {self.max_observations} 支截断"
                    f"（{min(len(reports), self.max_observations)}/{len(reports)}）"
                    if truncated
                    else f"检索片段 {len(reports)} 支全量"
                )
                + f"（合计入选 {len(ordered)}/{len(material)}）"
            )
            material_total = len(material)
            material_rendered = len(ordered)
            material_truncated = truncated
        else:
            source_types, source_ids, versions, trust_levels = [], [], [], []
            material_reason = f"步骤 {step}：理解步零材料渲染"
            material_total = 0
            material_rendered = 0
            material_truncated = False
        if extra:
            # 常驻注入块入 Manifest（R3 证据面——ledger_dump 族来源行）。
            source_types.extend(str(item.get("source_type", "")) for item in extra)
            source_ids.extend(str(item.get("source_id", "")) for item in extra)
            versions.extend(None for _ in extra)
            trust_levels.extend(str(item.get("trust_level", TRUST_LEDGER)) for item in extra)
            material_reason += (
                f"；词典层常驻注入 {len(extra)} 块（ledger_dump 族——第 1 轮全量，"
                "非懒加载：注入不依赖未命中）"
            )
        # 消息历史簿记＋token 预算截断（ADR-0006——在完整历史上续写）。
        turns = [*run_state.history, {"role": "user", "content": current}]
        kept, dropped = _fit_history(turns, self.max_context_tokens)
        messages = [{"role": "system", "content": self.system_prompt}, *kept]
        reason = material_reason
        if dropped or _estimate_tokens(
            "".join(str(m.get("content", "")) for m in kept)
        ) > self.max_context_tokens:
            reason += (
                f"；token 预算 {self.max_context_tokens} 截断：历史 "
                f"{len(turns)} 轮→{len(kept)} 轮（弃 {dropped}，首问轮与当前轮保留）"
            )
        manifest = Manifest(
            source_type=source_types,
            source_id=source_ids,
            version=versions,
            trust_level=trust_levels,
            selected_reason=reason,
            # token 实量＝全消息拼接后 chars/4（与网关记账兜底同口径）。
            token_count=_estimate_tokens(
                "".join(str(m.get("content", "")) for m in messages)
            ),
            # V2-61 材料承载分形记账（三机检字段——附 B）。
            material_total=material_total,
            material_rendered=material_rendered,
            material_truncated=material_truncated,
        )
        return CompiledContext(messages=messages, manifest=manifest)
