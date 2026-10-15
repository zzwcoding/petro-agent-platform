# RT-W4-01b · understanding（-B）——直答结构核验（闭世界判据）＋fail-closed 默认

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/understanding.md`（状态「已定稿」——前置满足）
Touches modules: `understanding`（本票在 -A 已落骨架 `appv2/runtimev2/understanding/` 上实现 -B 半面；规格「触及的模块」表另声明 prompts／parsing／gate／bookkeeping／gateway_adapter／state／tools 七关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」；本块＝链序第 1 位（understanding，次位 clarification）
复审强度: 50% 抽查（eng/03 §五 流水 48 规则；W4 行 A 列含 `understanding`——该表降级保留的规则原文「A 列抽 50%」，双队制已废止、A/B 分配只余复审强度语义，波序与块归属不变）
前置: ① 规格定稿（`specs/understanding.md` 已定稿——已满足）；② 波次前置：**W1＋W2＋W3 全收波**（同理 -A）；③ **票内前置：RT-W4-01a 收票**——`interpret(state)` 签名、`Understanding`／`Direct` 两型、三区装配、解析链路与按 `route` 分派链路在位后本票才动工（-B 不新建骨架、不新增模型调用链路）；④ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）
阻塞: **RT-W4-01a 收票**（-A 未收票则 -B 不动工）｜被阻塞: W5 `orchestration`（eng/03 §一依赖图：orchestration → 七个业务相位——本块 5 行与其 -A 11 行共同构成 W4 understanding 的出口判据「新规格钉绿」）

## 任务

按 `specs/understanding.md` 实现 -B 半面：**直答结构核验的闭世界判据**（≥1 位连续阿拉伯数字形（含全角、含小数／百分号／千分位）｜指标名录集合成员｜结构卡集合成员，任一命中即判不合格）→ **不合格退回 `route="full"` 的 `Understanding` ＋过程档案一条「直答退回」注记**（不抛错、不静默、不直答收口）；**路由默认 fail-closed**（拿不准／可能有关／灰区一律走完整流程，只有确定无关的寒暄类才直答）；**样例＝固定示例集三则**（不加边界对照例）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

**拆分理由（承 -A 票「拆分理由」节，同一条）**：本块规格「验收测试」表 16 行 > 15 行上限（小票制判据：票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇）→ 拆 -A／-B。**-A**＝骨架＋接口＋核心行为簇（装配／解析／路由闭世界／分派／事件／信号）＋**本块全部织网钉**（pin-26）；**-B**＝剩余行为簇（直答结构核验＋fail-closed 默认＋样例集）＋【边界集】【保留集】两行。本票 5 行 ≤15、必读 5 份 ≤6，聚焦「直答认可与退回」这一行为簇；两票同包顺序施工（-B 前置＝-A 收票），不并行。

先读:（5 份；其余引用面随用随查、不入必读）`specs/understanding.md` 全文（136 行；本票相关面＝行为 5／10／11、接口「直答退回不抛错」行、验收表行序 3／4／14／15／16、风险 1／2）；`specs/modules.md` `## understanding` 卡（:130–:147，测试计划行原文「直答／完整流程分流（拿不准走完整流程）；直答含数据或事实断言即退回；候选须出自名录」）；`specs/tools.md`（`semantic_query` 名录面与 `table_schema` 结构卡发现面——直答核验两闭世界的真源，只经公开面）；`specs/bookkeeping.md`（直答退回注记的写入点 `note`——写口单点面）；`specs/state.md`（状态形状与读题结论字段的消费面）
（另：`specs/prompts.md` 的样例集契约、`specs/gate.md` 的入口闸结论随用随查——两者不入必读清单。）

框架红线: **无点名框架**（本模块不引入任何框架）；**不得直接 import `langgraph`／`langchain`**（框架只许在 `orchestration`）——对应闸 **R5b 契约**
边界红线: ① **闭世界核验只许结构判定**——数字形判定与集合成员判定（AST 豁免面内），禁词表／正则猜语义；本票新增代码不得使 -A 票落地的 `::no_lexicon_or_regex_in_understanding` 转红；② 模型调用仍只经 `bookkeeping.call_model`（R7）——本块不直引 `gateway_adapter`／`appv2.infra.llm_client`、不自建客户端；③ **只经 `tools` 公开面**取名录与结构卡（R6），不直引 knowledge／query／retrieval 引擎；④ 退回口径**唯一**：`route="full"` 的 `Understanding` ＋过程档案一条「直答退回」——不抛错（不借 `UnderstandingParseError` 表达）、不静默丢弃、不直答收口；⑤ 不落盘（落盘归 `persistence`）；⑥ 不直改状态字段（写口单点归 `bookkeeping`）；⑦ 相位互不 import（R1）

## 票面对象（specs/understanding.md「验收测试」表逐行转抄——本票 5 行：规格表行序 3／4／14／15／16）

〔来源：specs/understanding.md「验收测试」表 :96–:111，逐行原文；`#` 列＝规格表行序（与 -A 票同一行序、不重编），逐字转抄、未改一字；余 11 行（行序 1／2／5／6／7／8／9／10／11／12／13）归 RT-W4-01a〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 3 | 寒暄句（道谢／道别）→ route=direct，文本不含数据或事实断言 | `tests/domains/test_v2_understanding.py::direct_on_greeting` | specs/understanding.md:98 |
| 4 | route=direct 但文本命中闭世界 → 不合格，退回 full | `tests/domains/test_v2_understanding.py::direct_with_assertion_rejected` | specs/understanding.md:99 |
| 14 | 路由默认 fail-closed：拿不准／可能有关 → 完整流程；灰区（我能问什么／预测明年油价）→ 完整流程 | `tests/domains/test_v2_understanding.py::route_defaults_fail_closed` | specs/understanding.md:109 |
| 15 | 【边界集】**名录内**指标名／**结构卡内**表名／全角数字 → 直答判不合格 | `tests/domains/test_v2_understanding.py::direct_boundary_cases_rejected` | specs/understanding.md:110 |
| 16 | 【保留集】寒暄仍走 direct；route=full 的既有候选校验行为不变 | `tests/domains/test_v2_understanding.py::retention_non_direct_unchanged` | specs/understanding.md:111 |

> 测试文件归属（据规格逐行原文的标识路径照录）：本块验收测试绑**新建** `tests/domains/test_v2_understanding.py`（与 -A 票同一文件、同一批用例集——本票在 -A 已建文件上追加，不另起文件）；旧码测试本批不改。

## 测试网钉（specs/understanding.md「与闸的挂钩表」pin 行逐行转抄，0 行——本块唯一 pin 行随 RT-W4-01a 落地）

〔来源：specs/understanding.md「与闸的挂钩表」:127–:136——本表内 pin 行只有 1 行（pin-26 行），已随 `RT-W4-01a-understanding.md`「测试网钉」节转抄并落地；本票**零 pin 行、不重复转抄**（同一 pin 行两处转抄＝两处真源必漂移——照 `RT-W4-05b-execution.md` 同款纪律）〕

- 归块注：pin-26 落点＝行为 9，属 -A 行为簇（`::assembled_once_raw_not_in_dialogue`）。本票的「直答退回」注记**必须写进过程档案、不得写进 `dialogue`**——与 pin-26 渲染面同口径；本票侧不产新钉，只承该口径。
- 本块规格挂钩表内其余行（R5b／R6／R7 三闸行、spec gate 两行、三测试行、人审行）非 pin 行——其中 `::direct_with_assertion_rejected`（现状「待实现」）由本票「票面对象」行 4 承接。

## 施工要点（specs/understanding.md「行为约定」节骨架＋接口节——file:line 锚＋一句话；本票只覆盖 -B 行为簇）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/understanding.md:73–:77 | 行为 5 直答结构核验（闭世界判据） | `route="direct"` 且 `text` 命中下列任一闭世界即判不合格 → 退回 `route="full"`：**数值**＝≥1 位连续阿拉伯数字形（含全角；小数／百分号／千分位一并算命中）；**指标名**＝属指标名录集合（经 `tools` 的 `semantic_query` 取得的名录／别名面）；**表名**＝属结构卡集合（`tools` 的 `table_schema` 发现面）；**闭世界外的生词不算命中**（结构判据，不做语义猜测）（`::direct_with_assertion_rejected`／`::direct_boundary_cases_rejected`） |
| specs/understanding.md:57 | 接口定义 直答退回不抛错 | 结构核验不合格 → 返回 `route="full"` 的 `Understanding`，并在过程档案记一条「直答退回」（本块唯一合法回退口径——不抛 `UnderstandingParseError`、不静默、不直答） |
| specs/understanding.md:82 | 行为 10 样例＝固定示例集 | 多部分题／口语映射题／判断纠错题三则（真源 `walk/04-理解-读题步.md` §一「三则样例」＋`walk/裁决表.md` §04-C）；**不加边界对照例** |
| specs/understanding.md:83 | 行为 11 默认倾向 fail-closed | 理解判「可能有关／含糊／拿不准」→ 走**完整流程**；只有**确定无关**（寒暄／道谢／道别）才直答；**灰区归属**：系统自身能力问句（我能问什么）与预测类（明年油价）→ 归**完整流程**（真源 `walk/05-理解-定路由.md` §七 第 3 条与灰区归属）（`::direct_on_greeting`／`::route_defaults_fail_closed`／`::retention_non_direct_unchanged`） |

结构锚：specs/understanding.md:45–53 两型定义（`Understanding`／`Direct` 的 `route` 为定型常量 Literal、**不设类定义默认值**——缺必填字段即抛 `UnderstandingParseError`）；:55 `route` 闭世界（合法值仅 `"full"`｜`"direct"`）；:60–65 框架与依赖红线（无点名框架／经 `bookkeeping.call_model` 单点发起／不直引 `langgraph`／只经 `tools` 公开面）；:117–:119 风险 1／2（JSON 字段集变更牵连三消费面「候选白名单闸／理解旁白灰条／直答通道」同批改；第 5 条滑成语义判断的对策＝判据锁闭世界＋AST 机检，**豁免面＝形态处理**——先例 `tests/domains/test_v2_four_phase.py:446`）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋关联行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单——表内明写归本块的行〕

> **（无）**——本块规格与 `understanding` 模块在 §三 9 行内零明写归块行（逐行核对结论见 RT-W4-01a「织网义务」节）。关联行 B5（帧协议级时序）的产出面＝`text` 事件，属 -A 票面；**-B 不产帧、不落 §三 钉**。

- 本票织网义务＝L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 挂账登记（不静默吞掉）：规格「与闸的挂钩表」末行「『不做什么』的纯范围排除（不做澄清／查数等）」现状＝**人审**（原因：纯范围排除没有形状／存在性／退出码判据，接不上闸；能降维的部分由边界闸 R1 覆盖）——本票交付时按人审口径自述范围排除，不冒充机检覆盖。

验收: 以下判据逐条全绿为过——
- 「票面对象」5 行逐行实现为 `tests/domains/test_v2_understanding.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】【保留集】两行）；
- -A 票 11 行同文件回归绿（本票改动不得使既有用例转红）；
- 本块 pin-26 渲染面口径自守：退回注记入过程档案、`dialogue` 零写入（-A 用例 `::assembled_once_raw_not_in_dialogue` 复跑绿）；
- 边界闸 R1／R5b／R6／R7 在 `lint-imports --config tools/importlinter_v2.toml` 下绿；AST 机检 `::no_lexicon_or_regex_in_understanding` 绿（本票新增代码无词表／正则）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-01b 完成，产物 `appv2/runtimev2/understanding/`（-B 半面），偏差: 有/无（有则逐条列），测试: pytest 摘要（含 -A 11 行回归）＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
