"""「如实上报」机读信号面——notice ＋ step payload（`specs/understanding.md`「不降级与静默禁令」）。

真源：任何「如实上报」（**候选违约／解析失败**／直答退回〔-B 承接〕）**必须产生机读信号**：
step payload 字段 ＋ notice（类型取自事件闭世界 `synth/S6-事件与帧目录.md`）；**合法降级路径＝
无**——不许静默（红线 `arch/P7a-交接包与挂账清单.md` A-P7a-37「不许静默」）。

- **报告步**：异常面**补记一条**报告步（`bookkeeping.record_step`，状态 `failed` 如实），其
  `payload` 即「step payload 字段」的载体。**常规路径零补记步**——模型调用的步记录由
  `bookkeeping.call_model` **单点统一记账**（每次调用一条），本块**不为同一调用重复记账**
  （W4 通用须知：相位不得对同一调用再记一条步，否则步序翻倍）。
- **通知**：经唯一写口 `bookkeeping.notice` 落 `state.notices`（恰三键）；`type` 取值见
  `constants`（闭世界 `NOTICE_TYPES` 无专属值，取语义最近的既有值——登记见票面回报）。
  帧面不由本块发射（发帧归 `transport`、批次协调归 `orchestration`——`specs/bookkeeping.md`
  「不做什么」表与 `specs/understanding.md` 触及面同口径）。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from appv2.runtimev2.bookkeeping import notice, record_step
from appv2.runtimev2.persistence import STEP_STATUS_FAILED
from appv2.runtimev2.state import RunState
from appv2.runtimev2.understanding.constants import (
    NOTICE_CANDIDATE_VIOLATION,
    NOTICE_PARSE_FAILURE,
    PAYLOAD_CANDIDATES_KEY,
    PAYLOAD_EVENT_CANDIDATE_VIOLATION,
    PAYLOAD_EVENT_KEY,
    PAYLOAD_EVENT_PARSE_FAILURE,
    PAYLOAD_OFFENDERS_KEY,
    PAYLOAD_PHASE_KEY,
    PAYLOAD_RAW_EXCERPT_KEY,
    PHASE,
    REPORT_STEP_KIND,
)
from appv2.runtimev2.understanding.errors import excerpt


def _report(
    state: RunState,
    *,
    event: str,
    notice_type: str,
    title: str,
    content: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """机读信号两件套：报告步（payload 携如实字段）＋ notice（恰三键）——顺序固定、只追加。"""
    fields = {PAYLOAD_PHASE_KEY: PHASE, PAYLOAD_EVENT_KEY: event, **payload}
    record_step(
        state,
        kind=REPORT_STEP_KIND,
        title=title,
        status=STEP_STATUS_FAILED,
        payload=fields,
    )
    notice(state, type=notice_type, content=content)
    return fields


def report_candidate_violation(
    state: RunState, offenders: Sequence[str], candidates: Sequence[str]
) -> dict[str, Any]:
    """候选违约如实上报（行为 8 红线）：名录外名字**不静默丢弃**——候选原样保留并点名上报。

    `payload.metric_candidates`＝**全量候选**（如实），`payload.offenders`＝名录外者（逐字点名）；
    `notice.content` 同步点名（人读面）——两处同一次判定产物，不各自生成。
    """
    names = "、".join(offenders)
    title = f"理解候选违约：名录外 {len(offenders)} 个"
    content = f"理解步指标候选出现名录外名字（{names}）——判违约，如实上报，不静默丢弃。"
    return _report(
        state,
        event=PAYLOAD_EVENT_CANDIDATE_VIOLATION,
        notice_type=NOTICE_CANDIDATE_VIOLATION,
        title=title,
        content=content,
        payload={
            PAYLOAD_CANDIDATES_KEY: list(candidates),
            PAYLOAD_OFFENDERS_KEY: list(offenders),
        },
    )


def report_parse_failure(state: RunState, raw: str) -> dict[str, Any]:
    """解析失败如实上报（行为 7＋「不降级」节）：抛错之前先落机读信号（不静默）。

    `payload.raw_excerpt`＝原始应答片段（截断可见，同 `UnderstandingParseError.excerpt` 口径）；
    `notice.content` 携同一片段——两处同源（同一次 `excerpt`）。
    """
    excerpt_text = excerpt(raw)
    return _report(
        state,
        event=PAYLOAD_EVENT_PARSE_FAILURE,
        notice_type=NOTICE_PARSE_FAILURE,
        title="理解解析失败：应答不合 schema",
        content=f"读题应答不合 schema（不静默降级）：{excerpt_text}",
        payload={PAYLOAD_RAW_EXCERPT_KEY: excerpt_text},
    )


__all__ = ["report_candidate_violation", "report_parse_failure"]
