"""schema 拒回喂载荷（`specs/understanding.md` 行为 13——三段带路、零模型调用；2026-10-16 补·
流水 67）。

体例照澄清相位拒因载荷（`specs/clarification.md` 接口定义「错误契约」的【拒因】／【期望形】／
尾行）：读题 schema 拒 **不直接判死**——先过**确定性引号自修一次**（受理编排单点在
`parsing.parse_with_quote_repair`，修好＝受理；见 `interpret`），仍不合格才向链尾追加本载荷、
同相位再读一次（上限**恰一次**，钉死防环）；仍拒方走**收敛拒答**（`interpret._converge_refusal`——
2026-10-17 EB3 D4.4 起不再抛 `UnderstandingParseError`）。

三段（「\\n」连接成单段文本，段文本全在 `constants`）：

1. 【拒因】＝**具体不合项**（缺必填字段／字段类型不符／`route` 越界——取 `parsing` 诊断面
   `understanding_schema_feedback` 的唯一诊断出口：本模块**不判 schema**，只套骨架）；
2. 【期望形】＝理解面输出契约两形＋`metric_candidates` 无命中＝空数组（照合同与样例集）；
3. 尾行＝修正指令（只改不合项、重发一个 JSON）。

本模块**零模型调用、零 IO、零语义判断、零状态写入**：入参＝拒因正文（调用方已取），出厂＝载荷
文本（调用方经 `bookkeeping.append_message` 追加链尾——本模块不触状态、不落档案）。
"""

from __future__ import annotations

from appv2.runtimev2.understanding.constants import (
    FEEDBACK_EXPECTED,
    FEEDBACK_JOIN,
    FEEDBACK_REASON,
    FEEDBACK_TAIL,
)


def schema_feedback(reason: str) -> str:
    """三段拼装：【拒因】{具体不合项} ＋【期望形】… ＋ 尾行（「\\n」三段连接）。

    载荷**自足**（自带整套回喂语——链上直投，无外层壳、不二次套壳；同澄清面对账载荷「自带壳体
    原样透传」纪律，真源 `specs/prompts.md` 行为 16④叠字修复）。`reason` 为空串＝诊断面未给不合项
    （合格形不该走到本支——调用方只在 `parse_understanding` 返 `None` 之后调）；**不猜不编**：
    照实落空串。
    """
    return FEEDBACK_JOIN.join(
        [FEEDBACK_REASON.format(reason=reason), FEEDBACK_EXPECTED, FEEDBACK_TAIL]
    )
