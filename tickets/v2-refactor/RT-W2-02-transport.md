# RT-W2-02 · transport——V2 事件通路

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/transport.md`（状态「已定稿」——前置满足）
Touches modules: `transport`（本票只建 transport 本体；规格「触及的模块」表另声明 state／orchestration／api 三关联侧，归各自票承接）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「帧/游标单调」半句）
施工队: A 队（eng/03 §五 终表 W2 行 A 队列＝「persistence／transport／prompts／parsing」——transport 归 A，归队理由：契约已被规格钉死＋B5 回放钉兜底；已按 eng/03 §五 终表对齐）｜复审强度: 100%（A 队收波 100% 过独立复审；复审网在 L0 直派）
前置: ① 规格定稿（`specs/transport.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（eng/03 §一依赖图：transport → state）
阻塞: W1 state 收波（RT-W1-01）｜被阻塞: W5 orchestration（总线持有方）；`api` 块消费帧与游标语义

## 任务

按 `specs/transport.md` 新建 `appv2/runtimev2/transport/`：页面能看到的**唯一出口**——runtime 九类事件与 wire 三帧的闭世界、帧信封字节形、**全流单调游标**、断线续推与载荷透传。事件的本体在各发射方，**本块只管「出去的那一帧长什么样、怎么编号、怎么续」**。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: `specs/transport.md` 全文（十节版式）；`specs/modules.md` `## transport` 卡（签名以卡为准）；`docs/runtime-refactor/synth/S6-事件与帧目录.md`（九类／三帧／瘦指针七键真源）；`docs/runtime-refactor/synth/S3-口径裁决清单.md`（C-05 九类口径／C-10 blackbox 收正）；`docs/runtime-refactor/iface/P9a1-端点与帧通路.md`（帧键集与 T-P9a1 接缝事实）；`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二／§五；`docs/runtime-refactor/eng/04-测试网设计.md` §三／§五／§七；AGENTS.md 硬纪律 6b（逐字稿纪律）

框架红线: 无点名框架（本块不引入任何框架）——对应闸 R5b 契约
边界红线: ① 不引包内其它块（本块只依赖 `state` 的类型名——无专属闸→人审＋AST 断言登记待补）；② 模型出口零接触（R7）；③ 不直引引擎（R6）；④ 禁手写替代（帧对象／信封／游标只在本块实现，`api` 只做渲染——无专属闸→人审＋「信封实现单点断言」登记待补）；⑤ 帧不承载业务判断（不读词表、不判语义、不改写载荷内容——测试 `::payload_passthrough_no_rewrite`）

## 票面对象（specs/transport.md「验收测试」表逐行转抄，18 行）

〔来源：specs/transport.md「验收测试」表 :106–:123，逐行原文〕

| # | 验收标准（原文） | 对应测试（原文标识） |
|---|---|---|
| 1 | 事件名闭世界（九 runtime ＋ 三 wire ＝十二值）；越界构造抛错 | `tests/domains/test_v2_transport.py::event_kinds_closed_world` |
| 2 | `EVENT_KINDS` 九类全列导出面（含 `blackbox`） | `tests/domains/test_v2_transport.py::blackbox_kind_exported` |
| 3 | 帧信封恒三行＋空行；中文不转义；非原语不炸流 | `tests/domains/test_v2_transport.py::envelope_bytes_stable` |
| 4 | 游标全流单调：跨段不重启、重放不位移 | `tests/domains/test_v2_transport.py::cursor_monotonic_global` |
| 5 | 信封 `id`：事件帧＝自身 `seq`、wire 帧＝最后已消费事件 `seq`（尚未消费任何事件时＝-1；不推进游标） | `tests/domains/test_v2_transport.py::frame_id_equals_cursor` |
| 6 | 断线续推不重不漏（后缀逐帧相等） | `tests/domains/test_v2_transport.py::resume_no_dup_no_gap` |
| 7 | 载荷透传零裁剪；verdict 唯一改造＋两形闭世界 | `tests/domains/test_v2_transport.py::payload_passthrough_no_rewrite` |
| 8 | 通知恰三键＋`NOTICE_TYPES` 二十二值闭世界（越界／缺键／多键／缺 `type` 判失败） | `tests/domains/test_v2_transport.py::notice_three_keys_closed_world` |
| 9 | `ask` 帧形状齐备＋`kind` 闭世界；挂起后照发 `done` | `tests/domains/test_v2_transport.py::ask_frame_shape_and_done_after_ask` |
| 10 | 正常 `done`／异常 `error`；`error` 不含原始异常文本 | `tests/domains/test_v2_transport.py::done_error_split_no_raw_exception` |
| 11 | `blackbox` 帧恰一帧、在 `done` 之前、只出瘦指针 | `tests/domains/test_v2_transport.py::blackbox_pointer_frame_last` |
| 12 | 多消费者各自独立游标与收束（不靠一次性哨兵） | `tests/domains/test_v2_transport.py::multi_consumer_independent_cursor` |
| 13 | `close` 幂等；关闭后 `emit` 抛错 | `tests/domains/test_v2_transport.py::close_idempotent_rejects_after` |
| 14 | 帧面无截断类帧名 | `tests/domains/test_v2_transport.py::no_truncation_frame` |
| 15 | 任何帧不携带堆栈／路径／SQL 片段 | `tests/domains/test_v2_transport.py::no_internal_leak_in_frames` |
| 16 | 本块零判断零模型（AST 扫描） | `tests/domains/test_v2_transport.py::no_judgement_or_model_in_transport` |
| 17 | 【边界集】零事件 run／单帧 run／超长载荷／关闭后再发 → 各落对应分支 | `tests/domains/test_v2_transport.py::boundary_empty_single_huge_closed` |
| 18 | 【保留集】常规多帧 run 的帧序与载荷行为不变 | `tests/domains/test_v2_transport.py::retention_normal_stream_unchanged` |

> 测试文件归属（spec :125 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_transport.py`（本块是阶段 2 新划的公共层块 `appv2/runtimev2/transport/`，与现状 `appv2/runtime/events.py` 的旧码测试形状不同）；旧码测试本批不改。

## 测试网钉（specs/transport.md「与闸的挂钩表」pin 行逐行转抄，3 钉）

〔来源：specs/transport.md「与闸的挂钩表」:158–:160，逐行原文〕

1. **pin-29（P0）**｜挂起→resume 的**帧面**（`ask` 帧 kind 闭世界＋挂起后照发 `done`）——**闭环面挂 `specs/agent-loop.md`**｜测试 `::ask_frame_shape_and_done_after_ask`｜现状：待织网（阶段 5）
2. **pin-09（P1）**｜**材料截断披露的帧面**：`material_truncated` 帧必发且其 `type` 在闭世界内（披露行为面挂 `specs/answering.md`、字段面挂 `specs/state.md`）｜测试 `::notice_three_keys_closed_world`｜现状：待织网（阶段 5）
3. **pin-04（P0）**｜**发射 JSON 不进答案面的帧形面**：`emission_strip` 通知的帧形（`type` ∈ `NOTICE_TYPES` 闭世界、载荷恰三键 `{type, gates, content}`）归本块；剥离行为面归 `specs/answering.md` 行为 11｜测试 `::notice_three_keys_closed_world`｜现状：待织网（阶段 5）

共载注（拆票对账观察）：pin-04 与 pin-09 的测试列同载于 `::notice_three_keys_closed_world` 一根测试——一测载两钉，织网时两钉断言面都须在该测内可指认。

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
| specs/transport.md:89 | 行为 11 多消费者各自独立游标与收束 | 各自 `cursor` 读取互不抢占；收束由「已关闭且无新帧」判定，不靠一次性哨兵 |
| specs/transport.md:90 | 行为 12 close 幂等＋关闭后拒发 | 两次 `close` 无异常；`close` 后 `emit` 抛错 |
| specs/transport.md:91 | 行为 13 无「截断重放」帧 | 帧面无 `replay_truncated` 类帧；缓冲无该 run 由 `api` 开流前诚实拒 |
| specs/transport.md:92 | 行为 14 帧内不出现原始异常与内部路径 | 无堆栈／模块路径／SQL 片段（无对应钉，登记为人审面） |
| specs/transport.md:93 | 行为 15 本块零判断零模型 | 无词表／正则语义判定、无模型调用、无落盘（AST 扫描） |

结构锚：specs/transport.md:34 接口定义（`SseEvent`／`EventBus`／`envelope`／五个闭世界常量族签名与取值真源逐族标注）；:68–75 框架与依赖红线（R5b/R7/R6 挂闸＋两条人审降维面）；:95–100 不降级与静默禁令（合法降级路径＝无；失败披露走 `notice{type:"run_failed"}`＋正常 `done`，帧通路自身异常才发 `error`）。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单〕

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

- 归块注（拆票 mapping，待主窗对账确认）：B5 的钉源载体＝`eval/results/frames/`（L3 golden 回放钉）；eng/04 §五 step 1 已说明 harness 只辖 leg JSONL，§七挂账原文照抄：「harness 只辖 leg JSONL；`eval/results/frames/*.json`（单对象 frames 数组）是另一载体，L3 钉若要消费需另加解析形（登记待 L3 开工时定）」——B5 落钉前须先定该解析形。
- 本票织网义务＝① B5 golden 回放钉（织网工序第 3 步「盲区补钉」，与 W2 施工可并行——eng/04 头注）；②「测试网钉」3 钉（pin-29／pin-09／pin-04）对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五）。

验收: 以下判据逐条全绿为过——
- 「票面对象」18 行逐行实现为 `tests/domains/test_v2_transport.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行）；
- 「测试网钉」3 钉对应用例在场且绿（pin-29／pin-04 为 P0 承重钉）；
- `NOTICE_TYPES` 二十二值闭世界与「恰三键」断言绿（`::notice_three_keys_closed_world`——本规格自立取值真源）；
- 边界闸 R5b／R6／R7 在 `lint-imports` 双配置下绿；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-02 完成，产物 `appv2/runtimev2/transport/`，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
