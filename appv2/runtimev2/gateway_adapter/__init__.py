"""网关桥：模型调用唯一出口桥、限流退避、测试替身、评测时钟

模块卡见 specs/modules.md 的 `## gateway_adapter` 一节；架构图见 docs/architecture-v3.html。
公开面以规格为准（`specs/gateway_adapter.md`；签名以卡为准）：

- 生产桥（2026-10-16 阶段 5，RT-W2-03a 落地）：`complete`（模块级唯一出口面）＋
  `GatewayBridge`（实作：经 `infra` 供应商出口发起、重试只对可重试类、耗尽原异常上抛）
  ＋ `set_completer`（显式注入缝：生产注入本桥、测试注入同面替身——离线零触网）
  ＋ `failure_reply`（失败尝试的回执单点：`error` 非 None、`content` 空串）；
- 回执与替身：`ModelReply`（**块级单一定义**在 `reply.py`——阶段 5 迁出替身件，
  替身只 import）／`ScriptedCompleter`（测试替身，`async complete(messages, *, caller, run_id)`）；
- 评测冻结时钟：`frozen_date` ＋ `EVAL_FROZEN_DATE_DEFAULT`／`EVAL_FROZEN_DATE_REAL`
  （env 键 `EVAL_FROZEN_DATE_ENV`——生产装配路径不读，只经显式注入缝）。
"""

from appv2.runtimev2.gateway_adapter.bridge import (
    GatewayBridge,
    complete,
    failure_reply,
    set_completer,
)
from appv2.runtimev2.gateway_adapter.eval_clock import (
    EVAL_FROZEN_DATE_DEFAULT,
    EVAL_FROZEN_DATE_ENV,
    EVAL_FROZEN_DATE_REAL,
    frozen_date,
)
from appv2.runtimev2.gateway_adapter.fake import ScriptedCompleter
from appv2.runtimev2.gateway_adapter.reply import ModelReply

__all__ = [
    "EVAL_FROZEN_DATE_DEFAULT",
    "EVAL_FROZEN_DATE_ENV",
    "EVAL_FROZEN_DATE_REAL",
    "GatewayBridge",
    "ModelReply",
    "ScriptedCompleter",
    "complete",
    "failure_reply",
    "frozen_date",
    "set_completer",
]
