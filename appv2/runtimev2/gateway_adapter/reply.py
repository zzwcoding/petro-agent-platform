"""gateway_adapter.reply —— 一次模型调用的回执（`ModelReply`，**块级单一定义**）。

规格 `specs/gateway_adapter.md` 接口定义把 `ModelReply` 列为本块回执类型（十字段）；
织网地基期它**暂寄居**替身件 `fake.py`（承重件先落地），阶段 5 生产桥落地时**迁至本件**
（非替身模块）——替身改为 import（**禁两处各定义一套**：本件／`fake.py`／包根同一对象）。
形状（字段名／顺序／缺省值）随迁不改——与 `fake.py` 旧定义逐字同形。

字段面要点（真源＝规格接口定义与行为约定）：
- `content` 应答正文（**失败尝试时为空串**）；`error` 非 None＝失败尝试（失败也留痕）；
- `cached_tokens` 上游未上报时 **=0**（不缺口、不省略——钉 `pin-25` 的回执面）；
- `run_id` 逐调用盖章（计费可对账——钉 `pin-28` 的调用盖章面）；
- `alias` 实际服务的模型别名（路由结果，随回执返回——调用方不传）；
- `usage_estimated`＝「用量是估的不是实测」的机读信号（**不得恒定值**——规格行为 10）。
"""

from __future__ import annotations

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
