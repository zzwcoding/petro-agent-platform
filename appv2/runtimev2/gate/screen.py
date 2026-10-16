"""安全阀判定（纯函数：文本 → 命中结论；三族先命先断、命中即返）。

【迁移】现状载体＝`appv2/runtime/graph.py` `_n0_intent_word_gate` 及族内三 matcher
（L1390-L1468）；真源 `docs/runtime-refactor/recon/B2-档案渲染与安全闸族.md`
R-B2-09／R-B2-11／R-B2-12／R-B2-13；`specs/gate.md` 行为 1–5。

差异点（`specs/gate.md`「V2 定案差异点表」内两处，差异点表外零偏离）：
② 写意图命中槽值**只携对象词**（V1 返回 `(动词, 对象)`、动词在消费侧即弃——本层动词分量不携）；
③ 命中路径**零台账 I/O**（V1 `_n0_refuse` 的补写不复刻——本层零 I/O）。

入参纪律（`specs/gate.md` 接口定义节）：纯文本进出（**零 state 字段读**、无数值面）；零时钟、
零随机、零 I/O、零模型、零事件发射、零状态写——任意 `str` 入参（含空串）恒返回两态之一
（`Refusal`｜`None`），**不抛业务错**。命中＝结构早退（非判据）；漏判由执行层兜（本块不承载红线）。
"""

from appv2.runtimev2.gate.constants import (
    INJECTION_ANSWER_TEMPLATE,
    INJECTION_PATTERNS,
    OUTBOUND_ANSWER,
    OUTBOUND_CHANNELS,
    OUTBOUND_VERBS,
    WRITE_ANSWER_TEMPLATE,
    WRITE_TARGETS,
    WRITE_VERBS,
)
from appv2.runtimev2.gate.models import Refusal


def _injection_hit(question: str) -> str | None:
    """注入特征字面匹配（V1 同构——casefold 折叠；返回列表序首个命中的模式原形）。"""
    folded = question.casefold()
    return next((p for p in INJECTION_PATTERNS if p.casefold() in folded), None)


def _outbound_hit(question: str) -> str | None:
    """外发词面命中（动词＋通道同句共现——返回通道词，未命中 None）。"""
    if not any(v in question for v in OUTBOUND_VERBS):
        return None
    return next((c for c in OUTBOUND_CHANNELS if c in question), None)


def _write_hit(question: str) -> str | None:
    """写意图词面命中（写动词＋写对象共现——返回对象词〔差异点②：动词分量不携〕，未命中 None）。

    取序：动词按列表序取首个在场者（无外显面〔实现细节〕）、对象按列表序取首个命中者＝可观测面。
    """
    for verb in WRITE_VERBS:
        if verb not in question:
            continue
        target = next((t for t in WRITE_TARGETS if t in question), None)
        if target is not None:
            return target
    return None


def screen(text: str) -> Refusal | None:
    """入口安全阀：三族按固定序（注入→外发→写意图）判定、**第一命中即返**；皆未命中 → `None`。

    命中即不放行（固定话术拒答收口——判定与话术出自本块，早退位次与落账归入口消费方）。
    """
    feature = _injection_hit(text)
    if feature is not None:
        return Refusal(
            family="injection",
            hit=feature,
            content=INJECTION_ANSWER_TEMPLATE.format(feature=feature),
        )
    channel = _outbound_hit(text)
    if channel is not None:
        return Refusal(family="outbound", hit=channel, content=OUTBOUND_ANSWER)
    target = _write_hit(text)
    if target is not None:
        return Refusal(
            family="write",
            hit=target,
            content=WRITE_ANSWER_TEMPLATE.format(target=target),
        )
    return None
