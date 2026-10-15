# RT-W2-02b · transport——V2 事件通路（-B：收口／消费者／元／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/transport.md`（状态「已定稿」——前置满足）
Touches modules: `transport`（本票只填 transport 剩余行为簇：流末收口／多消费者／关闭语义／红线与元／边界·保留集；形状与五个闭世界常量族以 `RT-W2-02a-transport.md` 为唯一真源）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「帧/游标单调」半句）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」——transport 归 A，归队理由：契约已被规格钉死＋B5 回放钉兜底；已按 eng/03 §五 终表对齐）｜复审强度: 100%（A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/transport.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：transport → state）；③ **`RT-W2-02a-transport.md` 收票**（同包顺序施工、同包不并行——票间纪律）
阻塞: `RT-W2-02a-transport.md`（-b 前置＝-a 收票）｜被阻塞: W5 orchestration（总线持有方）；`api` 块消费帧与游标语义

## 任务

接 `RT-W2-02a-transport.md` 落地的骨架，填 `appv2/runtimev2/transport/` 的**剩余行为簇**：收口段 `blackbox` 帧与流末纪律、多消费者各自独立游标与收束、`close` 幂等与关闭后拒发、帧面两条红线（无截断帧、不泄内部痕迹）、程序侧零判断零模型，以及边界集／保留集两行。

**本票＝transport 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **18 行**，超 15 行上限 → 切 -A／-B；本票收**剩余 8 行**＝规格表第 11–18 行（收口／消费者／关闭语义／红线与元／边界·保留集行）；前 10 行与**本块 3 条 pin 行**（pin-29／pin-09／pin-04）全在 -a，本票零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。

**形状归属（切分注）**：`SseEvent`／`EventBus`／`envelope` 与五个闭世界常量族（取值真源逐族按卡与规格）由 -a 落地为本票唯一真源；本票只加收口与消费者行为、**不改形状与取值**（改形状＝回 -a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （4 份）`specs/transport.md` 全文（十节版式；行为 11–15 与验收表第 11–18 行为本票面）；`specs/modules.md` `## transport` 卡（签名与卡级修正以卡为准：`EventBus.close`／`closed` 语义）；`docs/runtime-refactor/synth/S6-事件与帧目录.md`（九类／三帧／瘦指针七键真源——行 11 收口帧与行 14 帧名闭世界的对照基准）；`docs/runtime-refactor/eng/04-测试网设计.md` §三·§五·§七（§三 B5 行与 §七 挂账转抄落 -a、本票只留指针，§七 harness 载体事实）。本票「织网义务」节已把所引行逐字转抄，施工期不必另开。

框架红线: 无点名框架（本块不引入任何框架）——对应闸 R5b 契约
边界红线: ① 不引包内其它块（本块只依赖 `state` 的类型名——无专属闸→人审＋AST 断言登记待补）；② 模型出口零接触（R7）；③ 不直引引擎（R6）；④ 禁手写替代（帧对象／信封／游标只在本块实现，`api` 只做渲染——无专属闸→人审＋「信封实现单点断言」登记待补）；⑤ 帧不承载业务判断（不读词表、不判语义、不改写载荷内容——测试 `::payload_passthrough_no_rewrite`）；⑥ **禁手写替代（续）**：不得改 -a 已定的 `SseEvent`／`EventBus`／`envelope` 形状与五闭世界常量族取值另立第二套；收口帧不得新造帧名（行 14 帧名闭世界）；⑦ 不另立第二套游标（收束语义只经 -a 落地的 `EventBus.close`／`closed` 表达，不引一次性哨兵）

## 票面对象（specs/transport.md「验收测试」表逐行转抄——本票 8 行：规格表第 11–18 行）

〔来源：specs/transport.md「验收测试」表 :106–:123（本票取自 :116–:123），逐行原文；`#` 列＝规格表行序（与 -a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 11 | `blackbox` 帧恰一帧、在 `done` 之前、只出瘦指针 | `tests/domains/test_v2_transport.py::blackbox_pointer_frame_last` | specs/transport.md:116 |
| 12 | 多消费者各自独立游标与收束（不靠一次性哨兵） | `tests/domains/test_v2_transport.py::multi_consumer_independent_cursor` | specs/transport.md:117 |
| 13 | `close` 幂等；关闭后 `emit` 抛错 | `tests/domains/test_v2_transport.py::close_idempotent_rejects_after` | specs/transport.md:118 |
| 14 | 帧面无截断类帧名 | `tests/domains/test_v2_transport.py::no_truncation_frame` | specs/transport.md:119 |
| 15 | 任何帧不携带堆栈／路径／SQL 片段 | `tests/domains/test_v2_transport.py::no_internal_leak_in_frames` | specs/transport.md:120 |
| 16 | 本块零判断零模型（AST 扫描） | `tests/domains/test_v2_transport.py::no_judgement_or_model_in_transport` | specs/transport.md:121 |
| 17 | 【边界集】零事件 run／单帧 run／超长载荷／关闭后再发 → 各落对应分支 | `tests/domains/test_v2_transport.py::boundary_empty_single_huge_closed` | specs/transport.md:122 |
| 18 | 【保留集】常规多帧 run 的帧序与载荷行为不变 | `tests/domains/test_v2_transport.py::retention_normal_stream_unchanged` | specs/transport.md:123 |

> 测试文件归属（spec :125 节尾原注照抄）：本票 8 行与 -a 的 10 行同落**同一个新建文件** `tests/domains/test_v2_transport.py`；旧码测试本批不改。

## 测试网钉（本块 3 条 pin 行已在 `RT-W2-02a-transport.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-29 ↔ 行 9、pin-09／pin-04 ↔ 行 8——三条钉的机检用例全在 -a；本票 8 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -a 一处。

## 施工要点（specs/transport.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/transport.md:88 | 行为 10 blackbox 帧恒发且是流末业务帧 | 收口段恒发一帧（`stored` 布尔区分写库成败）；瘦指针七键；全文入库不入帧——行 11 的「恰一帧、在 `done` 之前」即本行为的行为面 |
| specs/transport.md:89 | 行为 11 多消费者各自独立游标与收束 | 各自 `cursor` 读取互不抢占；收束由「已关闭且无新帧」判定，不靠一次性哨兵 |
| specs/transport.md:90 | 行为 12 close 幂等＋关闭后拒发 | 两次 `close` 无异常；`close` 后 `emit` 抛错 |
| specs/transport.md:91 | 行为 13 无「截断重放」帧 | 帧面无 `replay_truncated` 类帧；缓冲无该 run 由 `api` 开流前诚实拒 |
| specs/transport.md:92 | 行为 14 帧内不出现原始异常与内部路径 | 无堆栈／模块路径／SQL 片段（无对应钉，登记为人审面） |
| specs/transport.md:93 | 行为 15 本块零判断零模型 | 无词表／正则语义判定、无模型调用、无落盘（AST 扫描） |
| specs/transport.md:122 | 行 17 边界集 | 零事件 run／单帧 run／超长载荷／关闭后再发四形各落对应分支 |
| specs/transport.md:123 | 行 18 保留集 | 常规多帧 run 的帧序与载荷行为不变 |

结构锚：specs/transport.md:34 接口定义（形状与五族常量真源＝-a 已落地，本票只加行为、**不改形状与取值**）；:68–:75 框架与依赖红线（R5b/R7/R6 挂闸＋两条人审降维面）；:95–:100 不降级与静默禁令（合法降级路径＝无；失败披露走 `notice{type:"run_failed"}`＋正常 `done`，帧通路自身异常才发 `error`——本票行 13 的 `close` 语义不得引入静默兜底）。

## 织网义务（eng/04-测试网设计.md §三 归本块行——本票只留指针）

- 归块行 **B5**（帧协议级时序）逐字转抄落 `RT-W2-02a-transport.md`「织网义务」节（防两处真源漂移，转抄见该票）；本票不重复转抄。
- eng/04 §七 挂账事实（本票先读含 §七，施工期对照用）：「harness 只辖 leg JSONL；`eval/results/frames/*.json`（单对象 frames 数组）是另一载体，L3 钉若要消费需另加解析形（登记待 L3 开工时定）」——B5 落钉前须先定该解析形；其钉归 -a。
- 本票织网义务＝① 本票 8 行对应用例落网；②「测试网钉」3 钉（pin-29／pin-09／pin-04）归 -a（本票只留指针）；③ B5 行的 L1／L3 钉归 -a（本票只留指针）；④ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」8 行逐行实现为 `tests/domains/test_v2_transport.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 11–18）；
- 收口帧纪律绿（行 11 恰一帧、在 `done` 之前、只出瘦指针）＋多消费者独立游标与收束（行 12，不靠一次性哨兵）＋`close` 幂等与关闭后拒发（行 13）；
- 帧面两条红线绿：无截断类帧名（行 14）＋不携带堆栈／路径／SQL 片段（行 15，无对应钉、人审面）；
- AST 红线断言 `::no_judgement_or_model_in_transport` 绿（无词表／正则语义判定、无模型调用、无落盘）；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 形状单点：`SseEvent`／`EventBus`／`envelope` 与五闭世界常量族仍以 -a 落地的为唯一真源，本票不改形状与取值（改形状＝回 -a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-02b 完成，产物 `appv2/runtimev2/transport/`（剩余行为簇：收口／消费者／元／边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
