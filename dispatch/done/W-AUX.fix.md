# W-AUX 修复拍（停线裁决 C——辅助检索＋叙述生成以旁注帧呈现；只补裁决项）

任务：补完施工方案第 2 件（辅助检索＋叙述生成），解读段呈现形态按 L0 裁决 **C＝notice 旁注帧**（零合同变更，复用既有 notice 机制——P2-03 状态标注先例）〔来源：W-AUX.dev.md 停线判定＋三出路＋Owner 选 C〕。

施工方案：

1. **辅助检索**：query_chain N7.5 只读执行后（行数>0）——用原问句复用检索链双路召回（同域函数级复用，零新缝）取辅助片段（小 topK，如 4 支）；检索无片段（报告库空）→ 纯表格回答自然降级零报错。
2. **叙述生成**：辅助片段＋表格数据进 gateway.complete（caller `chat.query.narrate`，照 chat.query.rewrite 惯例）生成解读段——提示词三约束：**数值一律以表格为准（片段数值不采）**／引用标注 cN／不得虚构。
3. **旁注帧呈现**：解读段以 **notice 帧**输出（照既有 notice 机制；位置与帧序按帧合同现状施工并回报说明）。
4. L0 预裁决四条（随票施工/登记）：
   - 接续范围：降级接续仅限三路出不了数路径（N7.1/N7.4a/N7.6 零行）——N7.5 执行缝未装配路径维持如实现状，登记——归属：M-06 后续打磨批；
   - free 兜底无引用回答＝双重无果处理 → 判据确认；
   - 接续路沿用检索链既有行为（含 P1F-06 改写澄清触发）→ 确认为预期交互，登记；
   - A1 册「解读槽位」正式化 → 登记——归属：阶段 3 合同对齐批。

先读：W-AUX.dev.md（停线判定与三出路证据）；chains.py query_chain 现场与 retrieval 召回复用点；既有 notice 机制（P2-03 先例）；teach A1 册 notice 帧形状。

框架红线：LLM 走 gateway.complete 单点。

边界红线：只动 chat 域（chains/service 及测试）；分支 `fix/w-aux-query-narrate` 追加 commit（rev-list=2）；禁 `git add -A`；Owner 私产不碰。

验收：以下全达才算过。
1. TDD 红先：辅助检索/旁注帧各自红；转绿后——有片段→notice 帧含 cN 引用且**表格数值不变（变异：片段含假数值→断言表格/血缘卡数值原样）**；无片段→纯表格零报错。
2. caller 计费留痕断言（chat.query.narrate）；帧序合法性对照 A1 帧合同。
3. 全量 pytest 数字（885+83 基线不跌）；ruff/mypy/lint-imports/两闸绿。
4. rev-list=2（ce38179＋本拍）。
5. rev.md 末节追加处置行（出路 C→已实现/SHA；四条预裁决记录）。

审查节点：不挂——增量小且有停线证据链，L0（单窗口）按 diff＋断言验收。

回报：按 PROTOCOL 写 `dispatch/results/W-AUX.fix.md`。
