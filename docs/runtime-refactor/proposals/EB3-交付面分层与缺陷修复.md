# EB3 交付面分层 + 缺陷修复批（Owner 2026-10-17 裁决）

> 前置裁决：①正文=LLM 回复原文；②程序追加内容（分源块/引用块/血缘五要素）**不进正文**，走结构化增补面（前端重设计后消费）；③评分=正文＋增补面合并判；④B1 核验前缀三件套全修；⑤C1 判分加"人话维度"；⑥97 题全量补跑；⑦L04-23 fail-closed、L04-18「前N→排名」按推荐修。
> **本轮不做前端**（Owner：前端页面需要重新设计，旁路展示随重设计落地）。增补面先把帧+落库通道备好。

## D1 增补面（supplement）通道
- transport 新增帧型 **`supplement`**（EVENT_KINDS 十二值→十三值，同批入 specs/transport.md＋frames 闸＋测试）：载荷 `{block, text}`，`block` 闭世界四值：`split`（多来源分源列明）／`attribution`（跨源归属）／`citations`（引用清单）／`lineage`（血缘五要素全文）。
- 落库：run 行增 `supplements` 列（JSON 数组，同 answer 先例），`GET /api/v2/chat/runs` 回读携带。
- 发射点：orchestration 收口（verification 改写后的 draft 定稿后），把四类块从正文剥出按原序入 supplement 帧。

## D2 四类块从正文剥除（answering/verification 面）
- answering 收口段（`answering/core.py` 约 :555-568）：「引用：」块→`citations`；「互不一致——各来源说法如下…」块→`split`；分源归属块→`attribution`。剥除后 **state.answer/正文不再含这些块**（specs/answering.md 行为 6/12 相关行改述：块入增补面＝交付完成，正文只留模型稿）。
- verification 确定性分源块（`verification/core.py:216-236` split_block/attribution_block）：**不再写进 state.draft**，改返回 supplements 列表由编排层发射。
- 血缘五要素护栏：核验步检测正文中的血缘五要素行（特征：`② 来源表`/`⑤ 收口注记`/五要素连续段）→ 整段剥入 `lineage` 增补面；单行「口径说明」（≤2 行、带 [n] 引标）保留在正文。

## D3 核验前缀三件套（verification/core.py）
1. **豁免两类**：(a) 引擎披露行——与血缘 payload/引擎注记一致的窗/截断/限量句（判据：行内含窗 ISO 区间或「封顶/截断/LIMIT/未覆盖」且与材料披露行事实一致）；(b) 组头行——行尾「：」或其后紧邻行带引标的数据表头。
2. **真无据断言按规格行为 3 删句**（不贴「未找到」前缀；审计走 verdict 帧 supported/rewritten 计数＋过程档案，禁静默=verdict 如实计数即不静默）。
3. 行集题组头允许组引标：`answering` 合同「禁汇总引标」句改为「数据行禁汇总引标；组头允许 `[m]–[n]` 组引标」——specs/prompts.md 逐字同步。
- REWRITE_PREFIX 常量退役或改用于审计注记（不进正文）。

## D4 缺陷四修
1. **L04-23 fail-closed**（`appv2/query/` 或 execution 计划面）：问句指标无注册绑定（如「日产水量」）→ **禁止回落相近列**（liquid_output 等），走「无注册指标」如实路径（检索问答链/如实拒答）。测试钉： liquid_output 不得出现在为该问产出的 plan/SQL 中。
2. **L04-18 前N→排名**：V2 计划面补确定性规则——问句显式「前 N」且 metric 已注册 → ranking=true/desc＋limit=N（V1 build_query_plan 同语义，照抄其行为不照抄代码）。
3. **D-诱9**：决策发射 malformed_matches 连发→recursion 35 触顶 run failed。修：决策相位对**同一 malformed 内容**重试上限（≤2）＋超限 fail-closed 收敛（budget_converged 带材料直答，不 run_failed）。
4. **NQ-D2**：理解步应答 route 越界闭世界 → 按理解步 schema 拒修正回路（流水 67 已有恰一次重试）兜住：route 非法→拒因三段带路重试一次，仍非法→收敛拒答（不 run_failed 零交付）。

## D5 评分规程（C1）
- 判分 prompt 增「人话维度」：正文自相矛盾/前缀误伤/机器块刷屏（若剥除未尽）→ 记 ⚠️ 病灶；不影响诚实域判定。
- 评分面＝正文＋supplement 帧合并（血缘/分源/引用在增补面在场即算交付）。

## D6 人话维度判据＋白话化批（Owner 2026-10-17 补充裁决）
- **判分"人话维度"三查**：①正文自相矛盾/前缀误伤/机器块残留；②**术语裸奔**——系统行话首次出现无白话注解（台账/口径/水位/绑定/召回/送窗/锚定/闭世界…）；③拒答/降级/收敛/拦停时**未先一句白话解释问题涉及的概念**就直接甩系统话术。
- **白话化锚例**（EB4 文案批的真源）：台账→"平台登记的名录"；口径→"这个数是按什么规则算的"；水位→"数据目前更新到哪一天"；窗→"统计的时间段"；绑定→"登记/关联"；新鲜度闸拦停→"这个时间段的数据还没更新到库里，查不了"。
- **EB4 范围**：ANSWER_REQUIREMENTS 增条款（术语首现一句白话注解＋拒答先科普一句）＋确定性系统文案白话化过一遍（notice/拒答/降级三段形——注意 gold 锚含旧措辞，需逐条对账改锚或保留术语+注解形）＋回归。本轮 EB3 复跑不动（避免与 EB3 缺陷修复测量混淆）。

## 不做
- 前端旁路展示（等页面重设计）；P4 送窗裁剪；D 项其余（build_query_plan 整体收回）。
- EB4 白话化（D6）——本轮跑完后单独立批。
