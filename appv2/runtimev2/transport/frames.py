"""帧对象与信封（wire 面单元＝本块交付物；形状真源 `specs/transport.md` 接口定义节）。

三层语义各自单点：

- **帧名闭世界**（行为 1）：`SseEvent.event` ∈ `EVENT_KINDS ∪ WIRE_FRAMES`（十二值），越界
  **构造期即抛错**（fail-closed，不静默丢弃、不降级为默认类）。
- **载荷透传**（行为 6）：`data` ＝发射方 payload 原样（零裁剪零改名）；**唯一改造＝`verdict`
  帧注入 `subtype`**（判据单点：含 `status` 键 → `final`，否则 → `verify`；键集越出契约时判
  `verify` 且原键如实透传）。`step`／`text`／`tool`／`observation`／`citation` 的键集归发射方，
  本块不校键、不补键、不删键。
- **三类定形载荷把守**（行为 7／8／9，越界即拒）：`notice` 恰三键 `{type, gates, content}` 且
  `type` ∈ `NOTICE_TYPES`（**缺 `type` 即拒**——取消旧码隐式兜底）；`ask` 恰
  `{frame: {kind, prompt, options, detail}, run_id}` 且 `kind` ∈ `ASK_FRAME_KINDS`；`error`
  恰二键 `{code, message}`（稳定话术面：原始异常文本只进内部留痕，键集定形使它无安放之处）。

信封字节形（行为 2）：恒「`id: <int>` ＋换行＋ `event: <str>` ＋换行＋ `data: <json>` ＋换行
＋空行」三行＋空行；`json.dumps(ensure_ascii=False, default=str)`——中文不转义，非 JSON 原语
（`Decimal`／`date` 等）兜底为字符串而不炸流。`id:` 行的取值＝`frame.seq`（行为 4：事件帧
`id`＝自身 `seq`；wire 帧 `seq` 即「最后已消费事件 `seq`」，见 `bus` 模块注）。
"""

import json
from dataclasses import dataclass
from typing import Any

from appv2.runtimev2.transport.constants import (
    _FRAME_EVENTS,
    _VERDICT_FINAL,
    _VERDICT_VERIFY,
    ASK_FRAME_KINDS,
    NOTICE_TYPES,
)


def _joined(values: frozenset[str]) -> str:
    """闭世界取值逐字拼接（报错文案随集合生成，不写死条数）。"""
    return "／".join(sorted(values))


def _check_notice(payload: dict[str, Any]) -> None:
    """行为 7：通知恰三键＋分型闭世界（缺键／多键／缺 `type`／越界 `type` 各判失败）。"""
    if set(payload) != {"type", "gates", "content"}:
        keys = _joined(frozenset(payload)) or "（无键）"
        raise ValueError(
            f"notice 载荷必须恰三键 type／gates／content（行为 7；实为 {keys}）"
        )
    notice_type = payload["type"]
    if notice_type not in NOTICE_TYPES:
        raise ValueError(
            "notice.type 越界（闭世界 NOTICE_TYPES 二十二值＝"
            f"{_joined(NOTICE_TYPES)}；缺 type 即拒，无隐式兜底）：{notice_type!r}"
        )


def _check_ask(payload: dict[str, Any]) -> None:
    """行为 8：ask 帧形状齐备＋`kind` 闭世界。"""
    if set(payload) != {"frame", "run_id"}:
        keys = _joined(frozenset(payload)) or "（无键）"
        raise ValueError(f"ask 载荷必须恰二键 frame／run_id（行为 8；实为 {keys}）")
    frame = payload["frame"]
    if not isinstance(frame, dict) or set(frame) != {"kind", "prompt", "options", "detail"}:
        keys = _joined(frozenset(frame)) if isinstance(frame, dict) else type(frame).__name__
        raise ValueError(
            f"ask 载荷的 frame 必须恰四键 kind／prompt／options／detail（行为 8；实为 {keys}）"
        )
    kind = frame["kind"]
    if kind not in ASK_FRAME_KINDS:
        raise ValueError(
            f"ask.frame.kind 越界（闭世界 ASK_FRAME_KINDS 二值＝{_joined(ASK_FRAME_KINDS)}）："
            f"{kind!r}"
        )


def _check_error(payload: dict[str, Any]) -> None:
    """行为 9：`error` 载荷定形恰二键（`code`＝稳定错误码、`message`＝稳定话术）。

    键集定形即脱敏的形状面：原始异常文本（堆栈／内部路径／SQL）没有可安放的键位。
    """
    if set(payload) != {"code", "message"}:
        keys = _joined(frozenset(payload)) or "（无键）"
        raise ValueError(
            f"error 载荷定形必须恰二键 code／message（行为 9；实为 {keys}）"
        )


@dataclass(frozen=True, slots=True)
class SseEvent:
    """帧（wire 面单元）：`{seq, event, data}`。

    `seq`＝全流单调游标（跨段不重启、重放不位移）——与载荷内步序号 `seq` **同名不同义**
    （后者＝步记录序号，真源 `specs/persistence.md` `StepRecord.seq`；本字段真源＝行为 3）。
    `event` ∈ 十二值闭世界（行为 1）。`data`＝载荷（透传；唯一改造＝`verdict` 注入 `subtype`）。
    """

    seq: int
    event: str
    data: dict[str, Any]

    def __post_init__(self) -> None:
        if self.event not in _FRAME_EVENTS:
            raise ValueError(
                "SseEvent.event 越界（闭世界＝EVENT_KINDS ∪ WIRE_FRAMES 十二值＝"
                f"{_joined(_FRAME_EVENTS)}；越界构造期即抛错，行为 1）：{self.event!r}"
            )
        raw: object = self.data  # 运行期把守（调用方可绕过注解传非映射——载荷面 fail-closed）
        if not isinstance(raw, dict):
            raise ValueError(
                f"SseEvent.data 必须为 dict（载荷透传面）：{type(raw).__name__}"
            )
        payload: dict[str, Any] = dict(raw)  # 载荷快照：发射方后续改写不进历史（重放不位移）
        if self.event == "notice":
            _check_notice(payload)
        elif self.event == "ask":
            _check_ask(payload)
        elif self.event == "error":
            _check_error(payload)
        elif self.event == "verdict":
            # 唯一允许的载荷改造（行为 6）：判据单点＝载荷含 `status` 键 → `final`，否则 → `verify`
            # （键集越出契约时同样判 `verify`，原键如实透传）。
            payload["subtype"] = (
                _VERDICT_FINAL if "status" in payload else _VERDICT_VERIFY
            )
        object.__setattr__(self, "data", payload)


def envelope(frame: SseEvent) -> str:
    """帧信封字节形（行为 2）：恒三行＋空行；中文不转义；非 JSON 原语兜底为字符串。

    `id:` 行＝`frame.seq`（行为 4 的落地形：两类帧的 `seq` 语义不同，见 `bus` 模块注）。
    """
    payload = json.dumps(frame.data, ensure_ascii=False, default=str)
    return f"id: {frame.seq}\nevent: {frame.event}\ndata: {payload}\n\n"


# 帧实体与信封都在本模块单点实现（禁手写第二套帧通路：`api` 只做渲染，不自建帧对象／信封）。
__all__ = ["SseEvent", "envelope"]
