"""网关桥：模型调用唯一出口桥、限流退避、测试替身、评测时钟

模块卡见 specs/modules.md 的 `## gateway_adapter` 一节；架构图见 docs/architecture-v3.html。
【接口已随规格回写（2026-10-15，阶段 3）】公开面以规格为准：
- `ModelReply`／`ScriptedCompleter`（测试替身，`async complete(messages, *, caller, run_id)`）；
- 生产桥（真实出口桥／限流退避）与评测时钟的实现落 **阶段 5**（本仓纪律「网没织好不开写」），
  故本包根此刻**只导出替身与其回执类型**，不预置自创面。
"""

from appv2.runtimev2.gateway_adapter.fake import ModelReply, ScriptedCompleter

__all__ = ["ModelReply", "ScriptedCompleter"]
