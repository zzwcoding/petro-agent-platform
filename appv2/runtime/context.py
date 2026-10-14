"""runtime.context —— Context Builder＋Manifest（specs/agent-loop.md 行为约定 2）。

模型每次调用前经 ContextBuilder 确定性编译（V2-79a 三层分离——ADR-0006 修订）：

- 簿记：消息列表＝[system]＋RunState.dialogue（自然对话层——user 原话/assistant
  终稿/澄清审批回收原文）＋当前 user 轮。任务书/指令/材料**现拼现用、用完即弃、
  不入史**（任务书入史＝旧反模式，V2-79 拆除）；模型过程原话（理解两行式、
  决策 JSON）与工具台账不进对话层，以 process_notes 结构化档案承载（graph 侧），
  需要时按需有界渲染进当前指令；
- 材料：观察材料段（[n] 引标视图）随当前轮渲染（decision/answer 步）——引标＝
  全局观察序号（RunState.observations 稳定序），模型面与答案引用同一套序号
  （fail-closed 引用的机读底座，语义零漂移）；notice 类观察仍不进模型面；
- 排序：材料信任级稳定序（agg 权威表 > 台账 > 检索）——同序保持入栈序（确定性）；
- 预算：双层——观察材料 max_observations 支截断＋对话层 compaction（V2-79d：
  视窗 token 预算 DEFAULT_DIALOGUE_VIEW_TOKENS=4000，chars/4 估算；超限旧轮对
  规则摘要化＝问原文＋答首行，近期窗全量保留，摘要以 system 消息置顶；压缩
  只作用模型视图——原史在 checkpoint 全量可查），压缩显式写进
  Manifest.selected_reason（不静默）。

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

# compaction 摘要行取材上限（V2-79d——问原文/答首行单行截断）。
_SUMMARY_HEAD_CAP = 120

DEFAULT_MAX_OBSERVATIONS = 24
# 对话层视窗 token 预算（V2-79d compaction——方案 §3.6 建议值 4000；独立于任务书
# 预算；chars/4 估算口径；测试可收窄——合同值不因测试改动）。
DEFAULT_DIALOGUE_VIEW_TOKENS = 4000

SYSTEM_PROMPT = (
    "你是油田生产数据的查询与解读系统——回答问题、给出数据与事实；执行类诉求"
    "（写入、修改、删除、发送、订阅提醒）不在系统之内，如实说明并引导线下流程。"
    "红线：1) 每条事实断言必须带 [n] 引标指向给定观察，无据不得断言；"
    "2) 材料含多个来源（不同报告／油田／井）时逐个来源分别作答——即使各源不冲突"
    "也要分别列出，不得只取其一，也不以反问代替作答；作答后仍有未覆盖的来源要如实"
    "点名（便于用户补充检索）；禁止无出处调和。逐源作答只用于材料确实覆盖了所问内"
    "容的情形：材料里没有用户所问的信息时，简短如实说明未找到、缺的是什么、下一步"
    "怎么办即可——不逐源转述与所问无关的材料；用户点名了具体主体（某口井／某区块／"
    "某油田）而材料未覆盖该主体时，只说明未找到并请用户确认（可给名字最相近的候选）。"
    "3) 只依据给定观察回答，观察未覆盖的部分如实说明未找到。"
)

# V2-53 附 B 逐字稿（台账全量块的「字典不是数据」头注——常驻块 BEGIN 标记后
# 首行，位于 BEGIN/END 标记之间；V2-79a 起当前轮不入史，块随当轮渲染、无收窄面）。
LEDGER_DICT_NOTE = (
    "（台账全量是字典不是数据：本块只载指标/术语/对象的定义、粒度与绑定态，"
    "不载任何数值——「在台账」不等于「数值在手」；数值一律经检索执行取得，"
    "禁止仅凭本块 finalize 定稿。）"
)


@dataclass(frozen=True, slots=True)
class CompiledContext:
    """确定性编译产物（messages 进模型；manifest 随 step 存档——过程态簿记）。

    messages＝[system, *RunState.dialogue（截断后）, 当前 user 轮]——
    多轮对话形态（ADR-0006 修订：任务书/指令/材料随当前轮现拼，不入史）。
    """

    messages: list[dict[str, str]]
    manifest: Manifest


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（locator.kind 确定性映射单点）。"""
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _head_line(text: str, cap: int = _SUMMARY_HEAD_CAP) -> str:
    """摘要行取材（首行＋单行上限截断——规则抽取的确定性取材单点）。"""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line[:cap]


def _compact_dialogue(
    turns: list[dict[str, str]], budget: int
) -> tuple[list[dict[str, str]], str | None]:
    """对话层 compaction（V2-79d——方案 §3.6 长对话治理；规则抽取零模型成本）。

    超预算旧轮对摘要化（user→问原文／assistant→答首行），近期窗全量保留；
    压缩只作用于模型视图——checkpoint 原史零覆盖（完整对话可查）。返回
    （保留轮, 前情摘要｜None）：总量入预算＝(原轮, None) 零漂移；保留窗从尾部
    向前累积、至少 1 轮（最新轮恒在场——哪怕单轮超预算，对话锚不丢）。
    摘要以 system 消息置顶（装配在 compile——序列合法性：system,system,user/assistant…）。
    """
    def _total(items: list[dict[str, str]]) -> int:
        return sum(_estimate_tokens(str(item.get("content", ""))) for item in items)

    if _total(turns) <= budget:
        return turns, None
    kept: list[dict[str, str]] = []
    total = 0
    index = len(turns) - 1
    while index >= 0:
        turn = turns[index]
        cost = _estimate_tokens(str(turn.get("content", "")))
        if kept and total + cost > budget:
            break  # 保留窗满（至少保 1 轮——最新轮无条件在场）
        kept.append(turn)
        total += cost
        index -= 1
    kept.reverse()
    older = turns[: index + 1]
    if not older:  # 单巨轮独占预算——无旧轮可压，原样放行（不静默丢锚）
        return turns, None
    lines = ["（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）"]
    for turn in older:
        role = str(turn.get("role", "user"))
        content = str(turn.get("content", ""))
        lines.append(
            f"问：{_head_line(content)}" if role == "user" else f"答：{_head_line(content)}"
        )
    return kept, "\n".join(lines)


@dataclass(slots=True)
class ContextBuilder:
    """确定性编译管线（簿记→材料渲染→双层预算→引用化——行为约定 2 的单点实现）。"""

    max_observations: int = DEFAULT_MAX_OBSERVATIONS
    dialogue_view_tokens: int = DEFAULT_DIALOGUE_VIEW_TOKENS
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
        消息列表＝[system]＋对话层轮（token 预算截断后）＋当前轮——当前轮用完
        即弃不入史（V2-79a 三层分离）。
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
        # 对话层 compaction（V2-79d——方案 §3.6）：超预算旧轮对规则摘要化（零模型
        # 成本），近期窗全量保留；压缩只作用于模型视图，checkpoint 原史零覆盖；
        # 当前轮不入史（V2-79a）。
        kept, summary = _compact_dialogue(
            run_state.dialogue, self.dialogue_view_tokens
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        if summary is not None:
            # 前情摘要置顶（序列合法：system,system,user/assistant…——裁剪红线）。
            messages.append({"role": "system", "content": summary})
        messages.extend(kept)
        messages.append({"role": "user", "content": current})
        reason = material_reason
        if summary is not None:
            reason += (
                f"；对话层 compaction：{len(run_state.dialogue)} 轮→保留 "
                f"{len(kept)} 轮＋前情摘要（预算 {self.dialogue_view_tokens}，"
                "原史在会话档案全量可查）"
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
