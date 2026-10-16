# EB2 答案面瘦身与友好化（Owner 2026-10-17 拍板"直接改"）

> 背景：Owner 两问——①上下文应只放 LLM 需要的数据（SQL/引用证据等应结构化直传前端，不该塞上下文让模型复述）②前端最终答案乱七八糟、不友好。
> 审计底稿：agent-147（A 装配／B 帧管道／C 前端／D 规格测试全图，file:line 见会话）。

## 决策（逐条可执行）

### D1 血缘卡不进 LLM 材料段，浓缩「口径行」进窗（材料面瘦身）
- `lineage` 观察（五要素：①口径②来源表③过滤④批次⑤收口）是**用户核验元数据**，模型答题不需要全文；现状权威族恒全量渲染（`materials.py:63-65`）→ 被模型整段复述进答案（真机 `L4/100…sse:867`「注记：- 口径：…- 窗口：…- 限量：…」）。
- 改法：`context/materials.py` 渲染时跳过 lineage 的**全文**；改为合成**一行口径行**进材料段（放在血缘卡原位）：`【口径】{①口径原文}｜来源：{②来源表}`；LIMIT 触顶时追加 `｜本次封顶前 N 行`。
- 口径行的原料要**结构化**：`execution/core.py:1084-1097` 发射 lineage 观察时把五要素存观察的 payload（如 `locator.payload={"lineage":{...五要素...}}`，键名自定但须进 transport 帧载荷透传前端）；`materials.py` 从 payload 取①②合成，**禁从五要素文本串解析**（脆）。
- 血缘卡**仍 observation 帧全量下发**（前端核验面不受损）——只不进 LLM 窗。
- 引擎注记（降级/拦停/未绑定，`answering/degradation.py:246-269`）**保留进窗**（模型如实转述所必需，非"数据"是"判定"）。
- 材料披露行（截断，`materials.py:99-105`）保留。

### D2 合同文本钉死「核验元数据不进答案正文」（answering 规格）
- `prompts/constants.py` ANSWER_REQUIREMENTS（族⑥）末尾**追加第八条**（逐字）：
  「核验元数据（血缘卡五要素、来源表、数据批次）不写进答案正文——它们在界面『引用与口径』侧栏逐字展示；答案只在用户需要时带一句口径（如单位）。」
- ANSWER_DRAFT_CONTRACT 中「引擎的 LIMIT 截断注记如实转述进答案」**保留**（截断是用户必须知道的交付事实）。
- specs/prompts.md 行为 2 七条逐字稿同步为八条；`tests/domains/test_v2_prompts.py::_ANSWER_REQUIREMENTS_VERBATIM` 同步。`specs/answering.md` 行为 10 表述同步（以 prompts 合同为唯一真源，条数 7→8）。
- 不动：引标纪律（逐条断言带 [n]）、分源列明、引擎注记转述——citation 联动与诚实域的根基。

### D3 工程块段头去工程腔（verification/answering 确定性追加面）
- `verification/rules.py:279-291` split_block 段头：`多来源不一致——分源列明（禁止无出处调和）：` → `各来源说法如下，按来源分别列出：`
- `verification/rules.py:372-395` attribution_block 段头：`跨源归属审——分源列明（题眼锚：{anchor}；禁止无出处调和）：` → `按来源归属如下（题眼：{anchor}）：`
- answering 收口段（`answering/core.py:555-568`）「引用：」块保留；其「互不一致」分源块段头与 split_block 同改（单源文本单点，不许两处定义）。
- specs/verification.md 行为 3/4/5 的段头逐字同步；钉段头的测试（`test_contradiction_split_not_merged`、`test_cross_oilfield_attribution_paired` 等）同步改。

### D4 前端答案友好化（web/）
- 答案渲染从 `pre-wrap` 纯文本升级：**marked lexer → React 元素**（只用 lexer token，自己映射 React 元素——html token 忽略，天然免注入；支持 paragraph/strong/em/list/list_item/table/code/heading，其余降级纯文本）。新增依赖 `marked`（`npm install marked`，lexer-only 用法）。
- 正文 `[n]` 引标正则 `\[(\d+)\]` → 可点击锚点：点击打开引用抽屉并高亮对应 index 条目（复用现有 Drawer `:653-667`）。
- notice/citation/抽屉现有结构不动；血缘卡展示=引用抽屉内 observation 配对（现状已通）。
- 测试：`web/src/landing/a1v2Reducer.test.js` 风格补渲染组件测试（粗体/列表/引标点击至少各一）。

### D5 判分口径适配（评分代理用，本次随批登记）
- 血缘卡在场判据：从「答案文本含血缘」改为「帧级在场」（observation 帧含血缘五要素）即算交付。
- 答案正文精简不判降档；窗口/截断声明仍需（一行即可）。
- 诚实四要素（明示说无/零编造/指向可得/不推卸）与反题口诀不变。

## 不做（记档）
- citation 帧补 kind/片段定位（transport 闭世界变更，风险大，index 配对已够用）→ 阶段 7。
- 新立「查询明细」独立面板（血缘经引用抽屉已可达）→ 前端后续批。
- 材料面送窗裁剪（P4）——原样挂评测后。
