# RT-W2-01b · persistence——V2 存储归档（-B：守门与红线面／元／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/persistence.md`（状态「已定稿」——前置满足）
Touches modules: `persistence`（本票只填 persistence 剩余行为簇：审计守门／业务表零写／行级口守门／截断与失败面／元／边界·保留集；形状与公开面以 `RT-W2-01a-persistence.md` 为唯一真源）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「只追加可重放」半句）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」，分配理由整行原文：「出口/计费/替身＝慢漏型缺陷，必须稳」）｜复审强度: 100%（eng/03 §五：A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/persistence.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：persistence → state）；③ **`RT-W2-01a-persistence.md` 收票**（同包顺序施工、同包不并行——票间纪律）
阻塞: `RT-W2-01a-persistence.md`（-b 前置＝-a 收票）｜被阻塞: W3 收波判据的一部分（间接）；编排块（W5）消费本块检查点三表行级口

## 任务

接 `RT-W2-01a-persistence.md` 落地的骨架，填 `appv2/runtimev2/persistence/` 的**剩余行为簇**：审计四要素与 action 闭世界两道守门、业务表零写（INV-2）探针、检查点三表行级口守门、黑匣子键白名单、截断可见与写失败 fail-closed、程序侧零判断零模型红线，以及边界集／保留集两行。

**本票＝persistence 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **20 行**，超 15 行上限 → 切 -A／-B；本票收**剩余 10 行**＝规格表第 6、7、8、13、14、16、17、18、19、20 行（守门与红线面／元／边界·保留集）；前 10 行与**本块 3 条 pin 行**（pin-12／pin-28／pin-30）全在 -a，本票零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。

**形状归属（切分注）**：`RunStore`／五张行投影／检查点三表行级读写口／`AuditRecord` 签名（真源 `recon/J`）由 -a 落地为本票唯一真源；本票只加守门与红线行为、**不改形状**（改形状＝回 -a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （4 份）`specs/persistence.md` 全文（十节版式，行为 5–7、11、13–15 与验收表第 6–8、13–14、16–20 行为本票面）；`specs/modules.md` `## persistence` 卡（签名与三处卡级澄清以卡为准）；`docs/runtime-refactor/recon/J-存储留痕与网关缝.md`（黑匣子键白名单 R-J-02／审计 action 七值 R-J-05／截断长度 R-J-06·R-J-60·R-J-62 真源）；`docs/runtime-refactor/eng/04-测试网设计.md` §三·§五（§三 无 persistence 明写行的事实在本票「织网义务」节逐字转抄，施工期不必另开）。

框架红线: LangGraph／LangChain 框架类型零出现（检查点 saver `BaseCheckpointSaver` 一族归 `orchestration`，本块只出框架无关表与读写入口）——对应闸 R5b 契约
边界红线: ① 模型出口零接触（R7）；② 不直引引擎（R6）；③ DB 只经 `infra.db`、时间只经 `infra.clock`、审计只经 `security.audit`（无专属闸→人审＋AST 降维断言登记待补）；④ 不引包内其它块（只依赖 `state`——无专属闸→人审＋AST import 白名单登记待补）；⑤ 业务数据零写入（INV-2）：簿记表前缀 `agent_v2_*` 是唯一写面——对应测试 `::no_business_table_write`；⑥ **禁手写替代**：检查点三表写入只经 -a 落地的五个行级口，不得在别处直连表；不得改 -a 已定的 `RunStore`／五张行投影／`AuditRecord` 形状另立第二套；⑦ 审计行不可改写：无更新／删除路径（行 2 双证面在 -a，本票新增写入面不得引入任何原地改路径）

## 票面对象（specs/persistence.md「验收测试」表逐行转抄——本票 10 行：规格表第 6、7、8、13、14、16、17、18、19、20 行）

〔来源：specs/persistence.md「验收测试」表 :165–:184（本票取自 :170–:172、:177–:178、:180–:184），逐行原文；`#` 列＝规格表行序（与 -a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 6 | 审计四要素缺项判失败 | `tests/domains/test_v2_persistence.py::audit_four_elements_required` | specs/persistence.md:170 |
| 7 | 审计 action 七值闭世界＋`agent_v2.` 前缀 | `tests/domains/test_v2_persistence.py::audit_action_closed_world` | specs/persistence.md:171 |
| 8 | 业务表零写（探针注入判失败） | `tests/domains/test_v2_persistence.py::no_business_table_write` | specs/persistence.md:172 |
| 13 | 检查点三表的写操作全经五个行级口（编排块 saver 不直连表） | `tests/domains/test_v2_persistence.py::saver_writes_only_via_port_functions` | specs/persistence.md:177 |
| 14 | 黑匣子键白名单闭世界（越界键判失败） | `tests/domains/test_v2_persistence.py::blackbox_keys_closed_world` | specs/persistence.md:178 |
| 16 | 截断必带可见标记 | `tests/domains/test_v2_persistence.py::truncation_visible` | specs/persistence.md:180 |
| 17 | 写失败 fail-closed：抛错且无部分行、无静默缺口 | `tests/domains/test_v2_persistence.py::write_failure_fail_closed` | specs/persistence.md:181 |
| 18 | 本块零判断零模型（AST 扫描） | `tests/domains/test_v2_persistence.py::no_judgement_or_model_in_persistence` | specs/persistence.md:182 |
| 19 | 【边界集】空 payload／超长事实／坏 ref／旧版本记录 → 各落对应分支 | `tests/domains/test_v2_persistence.py::boundary_empty_huge_badref_legacy` | specs/persistence.md:183 |
| 20 | 【保留集】常规落盘读回与未触发边界时的行为不变 | `tests/domains/test_v2_persistence.py::retention_normal_roundtrip_unchanged` | specs/persistence.md:184 |

> 测试文件归属（spec :186 节尾原注照抄）：本票 10 行与 -a 的 10 行同落**同一个新建文件** `tests/domains/test_v2_persistence.py`；旧码测试本批不改。

## 测试网钉（本块 3 条 pin 行已在 `RT-W2-01a-persistence.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-12 ↔ 行 10、pin-28 ↔ 行 11、pin-30 ↔ 行 15——三条钉的机检用例全在 -a；本票 10 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -a 一处。

## 施工要点（specs/persistence.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/persistence.md:142 | 行为 5 审计四要素齐备 | 主体／意图／事实／结果缺项判失败（Owner 裁决 `walk/16` §七 Q-C） |
| specs/persistence.md:143 | 行为 6 审计 action 闭世界 | 七值、恒 `agent_v2.*` 前缀（真源 `recon/J` R-J-05）；计数唯一口径＝action 七值（`agent-loop` 行为 8 陈旧「四事件」口径已就地改述） |
| specs/persistence.md:144 | 行为 7 业务数据零写入 | 全部写入落 `agent_v2_*` 簿记表；探针注入判失败 |
| specs/persistence.md:148 | 行为 11 黑匣子键白名单闭世界 | `record` 键 ⊆ 白名单（真源 `recon/J` R-J-02）；新增状态键须同批入列 |
| specs/persistence.md:150 | 行为 13 截断必可见 | 审计 facts ≤120 字符、黑匣子单行摘要 ≤96、分面 title 30/60、digest 80、source 40（真源 `recon/J` R-J-06／R-J-60／R-J-62） |
| specs/persistence.md:151 | 行为 14 落盘失败 fail-closed | 写失败上抛、不半写；发帧实施口是 transport、批次协调归 orchestration |
| specs/persistence.md:152 | 行为 15 本块零判断 | 无词表／正则语义判定、无模型调用（AST 扫描） |
| specs/persistence.md:183 | 行 19 边界集 | 空 payload／超长事实／坏 ref／旧版本记录四形各落对应分支 |
| specs/persistence.md:184 | 行 20 保留集 | 常规落盘读回与未触发边界时的行为不变 |

结构锚：specs/persistence.md:33 接口定义（形状真源＝-a 已落地；本票只加行为、不改形状）；:127–:134 框架与依赖红线（R5b/R7/R6 挂闸＋三条无专属闸面的降维 AST 断言）；:154–:159 不降级与静默禁令（合法降级路径＝无；审计不可改写）。卡级澄清②照抄（`specs/modules.md` `## persistence`）：「**「只读 DB」的准确含义**——**业务数据面只读**（INV-2 全程只读）；**簿记表 `agent_v2_*` 是本块唯一写面**（表名前缀隔离）。」

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单，B1–B7b/B7 逐行核对〕

- **§三盲区表无 persistence 行**（B1→bookkeeping、B2→orchestration、B2b→preconditions、B3→预算、B4→gate、B5→transport、B6→挂起恢复、B7b→gateway_adapter、B7→tools——按实抄呈报，不硬凑）。
- 转抄注（防两处漂移）：该事实逐字转抄只在本票一处；`RT-W2-01a-persistence.md` 只留指针、不重复转抄。
- 本票织网义务＝① 本票 10 行对应用例落网；②「测试网钉」3 钉（pin-12／pin-28／pin-30）归 -a（本票只留指针）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_persistence.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 6–8、13–14、16–20）；
- INV-2 探针（`::no_business_table_write`）与行级口守门（`::saver_writes_only_via_port_functions`）两道核心防线绿；
- 审计两道守门绿：四要素缺项判失败（行 6）＋action 七值闭世界与 `agent_v2.` 前缀（行 7）；
- 截断可见（行 16）＋写失败 fail-closed（行 17）＋黑匣子键白名单闭世界（行 14）绿；
- AST 红线断言 `::no_judgement_or_model_in_persistence` 绿（无词表／正则语义判定、无模型调用）；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 形状单点：`RunStore`／五张行投影／检查点三表行级口／`AuditRecord` 仍以 -a 落地的为唯一真源，本票不改形状（改形状＝回 -a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-01b 完成，产物 `appv2/runtimev2/persistence/`（剩余行为簇：守门与红线面／元／边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
