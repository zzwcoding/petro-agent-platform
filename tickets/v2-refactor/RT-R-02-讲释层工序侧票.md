# RT-R-02 · 讲释层工序侧票：定稿同批产人话讲释＋存量 16 块回补

状态: **草案（待主窗派工）** ｜ 类型: 工序侧票——**不属 17 块模块票册、不入五波序**，挂在阶段 3 六步工序「定稿」批之内（作为定稿的同批动作，不改六步骨架）
所属工序: `docs/runtime-refactor/规划.md` §五 步骤 1（阶段 3 收尾：定稿同批产讲释）
版式样张（真源）: `docs/runtime-refactor/explain/understanding-讲释.md`（2026-10-16 主窗试产，Owner 已验货通过）

## 任务

① **回补批**：为已定稿 16 块各产一份讲释，落 `docs/runtime-refactor/explain/<块名>-讲释.md`——清单（均为 `specs/` 已定稿）：understanding／clarification／tool_matching／preconditions／execution／answering／verification／agent-loop／state／persistence／transport／gateway_adapter／bookkeeping／prompts／parsing／context。
② **gate 块免回补**：gate 未定稿，随其定稿批按本票版式产讲释（挂接窗 B 收尾流程，归主窗派工）。
③ **术语小词典独立成篇**：`docs/runtime-refactor/explain/GLOSSARY-人话词典.md`——从样张第三节抽出，16 块共用；各讲释的「术语小词典」节改为指针引它。
④ **版式固化**：每份讲释按票面附 1 样张的五要素组织——①这块在业务上干什么 ②逐条讲行为约定（三行式：原文要点带锚→人话意思→为什么重要） ③术语小词典（或指针） ④全景位置 ⑤自检三问。

> 逐字稿载体（AGENTS.md 6b）：本票「五要素」「头部声明」「为什么分级」均见票面附 1 样张逐字（样张为仓内已提交真源，指针即载体）；施工子代理对版式五要素与头部声明只许照抄，偏离即停报 L0，不自行裁量。

先读: 票面附 1 `docs/runtime-refactor/explain/understanding-讲释.md`（版式真源）；所产每块的 `specs/<块名>.md` 全文＋其 `docs/runtime-refactor/spec-review/<块名>-评审.md`；`docs/runtime-refactor/eng/02-规格防漂移要求.md`（派生视图防漂移定位）；AGENTS.md 硬纪律 6b；所涉 walk 节点（各规格「来源」节自列）

框架红线: 无（纯文档票，零代码零框架零依赖）
边界红线: ① 只产 `docs/runtime-refactor/explain/` 下新文档，**零触碰** `specs/`、`walk/`、`appv2/`、`tools/`、测试树——真源一个标点都不许动；② 每份头部**必须**带派生视图声明（逐字见票面附 1 样张头顶引用块），缺声明＝判废重写；③ 「为什么重要」只许讲到规格层（样张第三节惯例）；裁决级取舍故事**只指路**（「真源在 walk/裁决表.md §XX」式），**不许展开讲古**——展开即越界；④ 外文锚/闸号不许进正文（「R7 契约」这类只许翻译成「机器守的依赖方向规则」级人话，样张第三节惯例）

## 票面附 1：版式样张＝`docs/runtime-refactor/explain/understanding-讲释.md`（已提交真源）

五要素与纪律以该文件逐字为准，此处只钉其骨架（与样张逐字一致）：

> **本文是派生视图，不是真源。** 真源＝`specs/<块名>.md`……规格改，本文即废；本文与规格冲突，以规格为准。写给人看，给机检看的断言一条都不在这里。

> 三行讲一条：原文要点（带规格锚）→ 人话意思 → 为什么重要。

> 「为什么」分两级：规格里查得到的直接讲；裁决级真理由不复制、只指路到 `walk/裁决表.md`。

验收: 以下判据逐条全绿为过——
- 16 份讲释＋1 份 GLOSSARY 在场（路径＝`docs/runtime-refactor/explain/<块名>-讲释.md`／`GLOSSARY-人话词典.md`），gate 讲释除外（随其定稿批另票）；
- 每份头部派生视图声明逐字与票面附 1 引用块一致（17 份逐字比对：16＋GLOSSARY）；
- 每份「逐条讲行为约定」的条数与对应规格「行为约定」节条数相等（逐块清点，N/N）；
- 每份含「自检三问」节（样张第五节惯例）；
- `git diff --stat` 显示零触碰真源（`specs/`、`walk/`、`appv2/`、`tools/`、测试树均无 diff）；
- `.venv/bin/python tools/ticket_shape_check.py tickets/v2-refactor/RT-R-02-讲释层工序侧票.md` 绿。

回报: 完成后回主窗——「RT-R-02 完成，产物 explain/ 下 17 份，偏差: 有/无（有则逐条列），头部声明逐字比对: 17/17 过，行为条数清点: <块名>=<n/n> 全列」。对版式五要素或头部声明任何偏离即停笔停报 L0，不落盘。
