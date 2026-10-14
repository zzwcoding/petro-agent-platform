"""runtime.context —— 材料渲染面＋信任级映射（V2-80h 起 compile 已退役）。

上下文装配不再经逐轮编译：对话链（RunState.messages，只追加）即上下文，
各 LLM 节点直接整链调用（相邻调用互为前缀——KV 缓存本源形态）。本模块余：

- 材料：观察材料段（[n] 引标视图）渲染（answer 步消费）——引标＝全局观察
  序号（RunState.observations 稳定序），模型面与答案引用同一套序号
  （fail-closed 引用的机读底座，语义零漂移）；notice 类观察不进模型面；
- 排序：材料信任级稳定序（agg 权威表 > 台账 > 检索）——同序保持入栈序（确定性）；
- 预算：观察材料 max_observations 支截断（截断显式披露，不静默）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


def trust_of(observation: dict[str, Any]) -> str:
    """观察信任级（locator.kind 确定性映射单点）。"""
    kind = str((observation.get("locator") or {}).get("kind", ""))
    return _KIND_TRUST.get(kind, TRUST_REPORT)




# ---------- 材料段渲染器（V2-80h——compile 退役后材料段的唯一渲染位） ----------


def render_materials(
    observations: list[dict[str, Any]], *, max_observations: int
) -> tuple[str, dict[str, Any]]:
    """观察材料→（[n] 引标视图文本，截断元数据）——原 compile 材料段逐字搬迁。"""
    material = [
        obs for obs in observations
        if (obs.get("locator") or {}).get("kind") != "notice"
    ]
    ordered = sorted(
        enumerate(material), key=lambda pair: _TRUST_RANK.get(trust_of(pair[1]), 9)
    )
    authority = [pair for pair in ordered if trust_of(pair[1]) != TRUST_REPORT]
    reports = [pair for pair in ordered if trust_of(pair[1]) == TRUST_REPORT]
    truncated = len(reports) > max_observations
    ordered = authority + reports[:max_observations]
    blocks: list[str] = []
    for _, obs in ordered:
        index = int(obs["index"])
        trust = trust_of(obs)
        origin = str(obs.get("source") or "").strip()
        well = str(obs.get("well") or "").strip()
        label = "｜".join(part for part in (trust, origin, well) if part)
        blocks.append(f"[{index}]（{label}）{obs.get('content', '')}")
    text = (
        "\n观察材料：\n" + ("\n".join(blocks) if blocks else "（无）")
        + (
            f"\n（材料披露：检索片段共 {len(reports)} 支，本轮渲染前 "
            f"{min(len(reports), max_observations)} 支——未渲染片段不在"
            "本轮视野，不得对其断言；权威行集与台账卡已全量渲染。）"
            if truncated
            else ""
        )
    )
    return text, {
        "material_truncated": truncated,
        "material_rendered": len(ordered),
        "material_total": len(material),
    }



@dataclass(slots=True)
class ContextBuilder:
    """材料渲染配置面（V2-80h——compile 退役后只余 max_observations 消费缝）。"""

    max_observations: int = DEFAULT_MAX_OBSERVATIONS

