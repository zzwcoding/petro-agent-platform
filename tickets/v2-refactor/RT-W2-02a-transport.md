# RT-W2-02a · transport——V2 事件通路（-A：骨架＋接口＋闭世界与游标主干）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/transport.md`（状态「已定稿」——前置满足）
Touches modules: `transport`（本票建 transport 本体骨架与公开面：`SseEvent`／`EventBus`／`envelope`／五个闭世界常量族；规格「触及的模块」表另声明 state／orchestration／api 三关联侧，归各自票承接）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「帧/游标单调」半句）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」——transport 归 A，归队理由：契约已被规格钉死＋B5 回放钉兜底；已按 eng/03 §五 终表对齐）｜复审强度: 100%（A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/transport.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：transport → state）
阻塞: W1 state 收波（RT-W1-01a/b）｜被阻塞: `RT-W2-02b-transport.md`（同包顺序施工——-b 前置＝-a 收票）；W5 orchestration（总线持有方）；`api` 块消费帧与游标语义

## 任务

按 `specs/transport.md` 新建 `appv2/runtimev2/transport/`：页面能看到的**唯一出口**——runtime 九类事件与 wire 三帧的闭世界、帧信封字节形、**全流单调游标**、断线续推与载荷透传。事件的本体在各发射方，**本块只管「出去的那一帧长什么样、怎么编号、怎么续」**。

**本票＝transport 的 -A 票（骨架＋接口＋闭世界与游标主干＋本块全部 3 条 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **18 行**，超 15 行上限 → 切 -A／-B 两票。本票收 **10 行**＝规格表第 1–10 行（事件名与通知分型两处闭世界／帧信封字节形／全流单调游标与续推／载荷透传／`ask` 帧与 `done`／`error` 分流）＋ **3 条 pin 行全量**（pin-29／pin-09／pin-04，逐字转抄见「测试网钉」节）；剩余 **8 行**＝规格表第 11–18 行（收口／消费者／元／边界·保留集行）归 `RT-W2-02b-transport.md`。两票同包**顺序施工**（同包不并行）：本票出骨架与公开面、闭世界与游标主干与全部 pin 行；-b 只填收口与消费者行为簇、不另立第二套形状。

**骨架／接口归属（切分注）**：`SseEvent`／`EventBus`（`emit`／`stream`／`close`／`closed`）／`envelope` ＋五个闭世界常量族（`EVENT_KINDS`／`WIRE_FRAMES`／`NOTICE_TYPES`／`VERDICT_SUBTYPES`／`ASK_FRAME_KINDS`，见 `specs/modules.md` `## transport` 卡）全在本票——-b 不得改形状与取值（改形状＝回本票或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/transport.md` 全文（十节版式）；`specs/modules.md` `## transport` 卡（签名以卡为准，含卡级修正「per-run `EventBus`」与归位登记「`notice.type` 取值闭世界在本卡」）；`docs/runtime-refactor/synth/S6-事件与帧目录.md`（九类／三帧／瘦指针七键真源）；`docs/runtime-refactor/synth/S3-口径裁决清单.md`（C-05 九类口径／C-10 blackbox 收正）；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`（帧键集与 T-P9a1 接缝事实）。本票「测试网钉」「织网义务」两节已把所引行逐字转抄，施工期不必另开。

框架红线: 无点名框架（本块不引入任何框架）——对应闸 R5b 契约
边界红线: ① 不引包内其它块（本块只依赖 `state` 的类型名——无专属闸→人审＋AST 断言登记待补）；② 模型出口零接触（R7）；③ 不直引引擎（R6）；④ 禁手写替代（帧对象／信封／游标只在本块实现，`api` 只做渲染——无专属闸→人审＋「信封实现单点断言」登记待补）；⑤ 帧不承载业务判断（不读词表、不判语义、不改写载荷内容——测试 `::payload_passthrough_no_rewrite`）

## 票面对象（specs/transport.md「验收测试」表逐行转抄——本票 10 行：规格表第 1–10 行）

〔来源：specs/transport.md「验收测试」表 :106–:123（本票取自 :106–:115），逐行原文；`#` 列＝规格表行序，-b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 事件名闭世界（九 runtime ＋ 三 wire ＝十二值）；越界构造抛错 | `tests/domains/test_v2_transport.py::event_kinds_closed_world` | specs/transport.md:106 |
| 2 | `EVENT_KINDS` 九类全列导出面（含 `blackbox`） | `tests/domains/test_v2_transport.py::blackbox_kind_exported` | specs/transport.md:107 |
| 3 | 帧信封恒三行＋空行；中文不转义；非原语不炸流 | `tests/domains/test_v2_transport.py::envelope_bytes_stable` | specs/transport.md:108 |
| 4 | 游标全流单调：跨段不重启、重放不位移 | `tests/domains/test_v2_transport.py::cursor_monotonic_global` | specs/transport.md:109 |
| 5 | 信封 `id`：事件帧＝自身 `seq`、wire 帧＝最后已消费事件 `seq`（尚未消费任何事件时＝-1；不推进游标） | `tests/domains/test_v2_transport.py::frame_id_equals_cursor` | specs/transport.md:110 |
| 6 | 断线续推不重不漏（后缀逐帧相等） | `tests/domains/test_v2_transport.py::resume_no_dup_no_gap` | specs/transport.md:111 |
| 7 | 载荷透传零裁剪；verdict 唯一改造＋两形闭世界 | `tests/domains/test_v2_transport.py::payload_passthrough_no_rewrite` | specs/transport.md:112 |
| 8 | 通知恰三键＋`NOTICE_TYPES` 二十二值闭世界（越界／缺键／多键／缺 `type` 判失败） | `tests/domains/test_v2_transport.py::notice_three_keys_closed_world` | specs/transport.md:113 |
| 9 | `ask` 帧形状齐备＋`kind` 闭世界；挂起后照发 `done` | `tests/domains/test_v2_transport.py::ask_frame_shape_and_done_after_ask` | specs/transport.md:114 |
| 10 | 正常 `done`／异常 `error`；`error` 不含原始异常文本 | `tests/domains/test_v2_transport.py::done_error_split_no_raw_exception` | specs/transport.md:115 |

> 测试文件归属（spec :125 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_transport.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/transport/`，与现状 `appv2/runtime/events.py` 的旧码测试形状不同）；旧码测试本批不改。

## 测试网钉（specs/transport.md「与闸的挂钩表」pin 行逐行转抄——本块全 3 钉，全在本票）

〔来源：specs/transport.md「与闸的挂钩表」:158–:160，逐行原文〕

1. **pin-29（P0）**｜挂起→resume 的**帧面**（`ask` 帧 kind 闭世界＋挂起后照发 `done`）——**闭环面挂 `specs/agent-loop.md`**｜测试 `::ask_frame_shape_and_done_after_ask`｜现状：待织网（阶段 5）
2. **pin-09（P1）**｜**材料截断披露的帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内（披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`）｜测试 `::notice_three_keys_closed_world`｜现状：待织网（阶段 5）
3. **pin-04（P0）**｜**发射 JSON 不进答案面的帧形面**：`emission_strip` 通知的帧形（`type` ∈ `NOTICE_TYPES` 闭世界、载荷恰三键 `{type, gates, content}`）归本块；剥离行为面归 `specs/answering.md` 行为 11｜测试 `::notice_three_keys_closed_world`｜现状：待织网（阶段 5）

- 共载注（拆票对账观察）：pin-04 与 pin-09 的测试列同载于 `::notice_three_keys_closed_world` 一根测试——一测载两钉，织网时两钉断言面都须在该测内可指认。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 3 条 pin 行只落本票一处；`RT-W2-02b-transport.md` 零 pin 行、只留归属指针。

## 施工要点（specs/transport.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/transport.md:79 | 行为 1 事件名闭世界十二值 | `SseEvent.event` ∈ `EVENT_KINDS ∪ WIRE_FRAMES`；越界构造期即抛错（fail-closed） |
| specs/transport.md:80 | 行为 2 帧信封字节形恒定 | 恒「id＋event＋data」三行＋空行；`ensure_ascii=False`；非 JSON 原语兜底为字符串不炸流 |
| specs/transport.md:81 | 行为 3 游标全流单调 | `seq` 由总线历史长度唯一决定、0 起严格递增；跨段不重启、重放不位移（Owner 裁决 `walk/裁决表.md` §01-A） |
| specs/transport.md:82 | 行为 4 信封 `id:` 行＝最后已消费事件 seq | 事件帧 `id`＝自身 `seq`；wire 三帧不推进游标、`id` 写最后已消费事件 `seq`（尚无＝-1） |
| specs/transport.md:83 | 行为 5 断线续推不重不漏 | `cursor`＝下一帧 `seq`（排他起点）；换算＝`cursor = id + 1`，两类帧同式 |
| specs/transport.md:84 | 行为 6 载荷透传零裁剪 | `data`＝payload 原样；唯一改造＝`verdict` 帧注入 `subtype`（含 `status` 键→`final`，否则→`verify`） |
| specs/transport.md:85 | 行为 7 通知恰三键且分型闭世界 | `{type, gates, content}` 恰三键；`type` ∈ 二十二值（本规格自立·码面实测）；取消隐式兜底——缺 `type` 即拒 |
| specs/transport.md:86 | 行为 8 ask 帧形状与 kind 闭世界 | 载荷 `{frame: {kind, prompt, options, detail}, run_id}`；挂起铁律：`ask` 帧之后照发 `done` |
| specs/transport.md:87 | 行为 9 流末恒发 done／自身异常发 error | `done` 载荷 `{run_id}`；`error` 载荷恰二键 `{code, message}`（稳定话术，不给原始异常文本） |
| specs/transport.md:88 | 行为 10 blackbox 帧恒发且是流末业务帧 | 收口段恒发一帧（`stored` 布尔区分写库成败）；瘦指针七键；全文入库不入帧 |

结构锚：specs/transport.md:34 接口定义（**`SseEvent`／`EventBus`／`envelope`／五个闭世界常量族签名与取值真源逐族标注＝本票交付物**）；:68–:75 框架与依赖红线（R5b/R7/R6 挂闸＋两条人审降维面）；:95–:100 不降级与静默禁令（合法降级路径＝无；失败披露走 `notice{type:"run_failed"}`＋正常 `done`，帧通路自身异常才发 `error`）。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单〕

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- 归块注（拆票 mapping，待主窗对账确认）：B5 的钉源载体＝`eval/results/frames/`（L3 golden 回放钉）；eng/04 §五 step 1 已说明 harness 只辖 leg JSONL，§七挂账原文照抄：「harness 只辖 leg JSONL；`eval/results/frames/*.json`（单对象 frames 数组）是另一载体，L3 钉若要消费需另加解析形（登记待 L3 开工时定）」——B5 落钉前须先定该解析形。
- 转抄注（防两处漂移）：该 B5 行逐字转抄只在本票一处；`RT-W2-02b-transport.md` 只留指针、不重复转抄。
- 本票织网义务＝① B5 golden 回放钉（织网工序第 3 步「盲区补钉」，与 W2 施工可并行——eng/04 头注）；②「测试网钉」3 钉（pin-29／pin-09／pin-04）对应用例落网（本块 pin 行全量承载于本票）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_transport.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–10）；
- 「测试网钉」3 钉对应用例在场且绿（pin-29／pin-04 为 P0 承重钉；pin-04 与 pin-09 共载一测，两钉断言面均须可指认）；
- 骨架与公开面按卡面签名齐备（`SseEvent`／`EventBus`／`envelope`＋五族常量，取值真源逐族按卡与规格）；
- `NOTICE_TYPES` 二十二值闭世界与「恰三键」断言绿（`::notice_three_keys_closed_world`——本规格自立取值真源）；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-02a 完成，产物 `appv2/runtimev2/transport/`（骨架＋接口＋闭世界与游标主干），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
