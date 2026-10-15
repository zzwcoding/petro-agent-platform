"""网关桥：模型调用唯一出口桥、限流退避、测试替身、评测时钟

模块卡见 specs/modules.md 的 `## gateway_adapter` 一节；架构图见 docs/architecture-v3.html。
【接口待规格回写】正式十节规格尚未写（阶段 3 在途）：当前只落卡面 Seam 点名的
测试替身（剧本化 completer——eng/04-测试网设计.md §五「织网步骤 1」地基件）；
生产桥（真实出口桥/限流退避）与评测时钟随阶段 3 规格落锤，公开面以规格为准，
本包根不预置自创面。
"""

from appv2.runtimev2.gateway_adapter.fake import ScriptedCompleter

__all__ = ["ScriptedCompleter"]
