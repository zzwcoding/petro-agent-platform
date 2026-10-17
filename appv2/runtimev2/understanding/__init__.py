"""读题：装配任务书 → 模型读 → 解析；定路由（模型判、程序机械分派、直答过结构核验）

模块卡见 `specs/modules.md` 的 `## understanding` 一节；规格见 `specs/understanding.md`（形状与
行为真源）；架构图见 docs/architecture-v3.html。包根即公开面（R2：消费方只经
`appv2.runtimev2.understanding` 消费，深层子模块私有）：

- `interpret(state, *, bus, watermark="")`——读题一步（卡面签名 `def interpret(state: RunState) ->
  Understanding | Direct`；两个关键词注入面见 `interpret` 模块注：`bus`＝编排块持有的 per-run
  总线、`watermark`＝水位文本注入〔B14 零时钟接触〕）；
- `UnderstandingParseError`——错误族形状位（携原始应答片段；**2026-10-17 EB3 D4.4 起退出本支
  出口**：两读皆不合 schema 改走**收敛拒答**——类型保留供消费面兼容，本块不再抛它）；
- `Understanding`／`Direct`——返回值定型载荷（**形状单点在 `parsing`**，此处只作签名面再导出，
  本块零第二定义——`specs/parsing.md` 行为 12）。

本半面（RT-W4-01a）落地行为簇：任务书三区装配与「每 run 只装配一次」／数据区活体投影现取／
统一 JSON 严格解析（不降级）／`route` 闭世界定型／程序只按 `route` 机械分派／单出口互斥／候选
出自名录对账／理解文本 `text` 事件（`kind=understanding`）／如实上报机读信号（notice ＋
step payload）、模型原话只为过程档案与链上留痕（钉 `pin-26` 渲染面）。
**schema 拒回喂重试恰一次（行为 13，2026-10-16 补·流水 67；2026-10-17 EB3 D4.4 改尾）**：首读不合
schema → 向链尾追加拒因载荷（`feedback.schema_feedback`——【拒因】取 `parsing.
understanding_schema_feedback` 的诊断出口、【期望形】＋尾行）→ 同相位再读一次 → **仍拒＝收敛拒答**
（`bookkeeping.direct_answer` 落拒答正文 ＋ 返回该 `Direct`——run 收口 `completed`，**不判 `failed`、
不零交付**；真机证据 `eval/results/frames/EB2-NQ-D2.json`）。上限恰一次；不补默认、不取默认路由。

-B 半面（RT-W4-01b）落地行为簇：**直答结构核验的闭世界判据**（数值形／名录内指标名／结构卡内
表名——`closure.direct_assertion_hits`，形态处理零语义）→ 命中即**退回 `route="full"` 的
`Understanding` ＋过程档案一条「直答退回」注记 ＋ 如实上报两件套**（不抛错、不静默、不直答
收口）；**路由默认 fail-closed（行为 11）**＝给模型的判断原则（交付面＝装配进任务书的指令区合同
与题干段收束句），程序侧零词面判据、只按 `route` 分派；**样例集**＝固定三则（`prompts` 单点字面，
本块零第二份合同文本）。`gate` 命中收口的执行面（入口安全阀结论的消费）本块**未落**——票面无该面
（登记见票面回报，不自行发明）。

依赖面（规格「框架与依赖红线」）：模型调用经 `bookkeeping.call_model` 单点发起（R7 ＋「无旁路」）；
只经 `tools` 公开面接触世界（R6）；不引框架（R5b）、不引引擎、不直引模型出口、不 import 旧码
（R5）；相位互不 import（R1）；不落盘；闭世界取值越界一律 fail-closed 抛错，**合法降级路径＝无**。
"""

from appv2.runtimev2.parsing import Direct, Understanding
from appv2.runtimev2.understanding.errors import UnderstandingParseError
from appv2.runtimev2.understanding.interpret import interpret

__all__ = ["Direct", "Understanding", "UnderstandingParseError", "interpret"]
