# RT-W1-01a · state——V2 运行状态与限额（-A：骨架＋接口＋形状与状态语义＋受理载荷面）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/state.md`（状态「已定稿」——前置满足）
Touches modules: `state`（本票建 state 本体骨架与公开面：八类形状签名＋状态字段语义＋受理与回执载荷；规格「触及的模块」表另声明 bookkeeping／orchestration 两消费侧，归各自票承接）
波次: W1（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W1 行：全体地基——本波出口判据「字段读写矩阵逐字段在场；限额机制单点、数值只引预算表；R4 绿」）
施工队: A 队（eng/03 §五 W1 行 A 队＝state，分配理由原文：「关键路径求快；钉最密（S5 字段矩阵＋pin-22/23/24/26），网兜得住」）｜复审强度: 100%（eng/03 §五：A 队收波 100% 过独立复审；复审网在 L0 直派，复审代理报告直送主窗）
前置: ① 规格定稿（`specs/state.md` 已定稿——已满足）；② 波次前置：无（W1 为首波）
阻塞: 无（W1 首票）｜被阻塞: `RT-W1-01b-state.md`（同包顺序施工——-b 前置＝-a 收票）；W2 各票波次前置＝「W1 state 收波」（persistence／transport 两包各 -a／-b 两票、gateway_adapter，票号以主窗 manifest 为准）；RT-W3-01a/b/c-bookkeeping 经 gateway_adapter 间接依赖本票

## 任务

按 `specs/state.md` 新建 `appv2/runtimev2/state/`：运行状态字段形状、模型调用 Manifest、受理与回执载荷、闭世界常量族、限额参数表与触界**判定**——**纯数据形状＋纯计算，零行为分支、零模型调用、零落盘、零业务语义判断**；写函数零供给（共享写口归 bookkeeping，见其规格）。

**本票＝state 的 -A 票（骨架＋接口＋形状与状态语义＋受理载荷面＋本块全部 6 条 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **19 行**，超 15 行上限 → 切 -A／-B 两票。本票收 **10 行**＝规格表第 1–8、15、16 行（字段形状与状态语义／旧检查点读入／受理载荷与 Manifest 投影）＋ **6 条 pin 行全量**（pin-22／pin-23／pin-24／pin-26／pin-29／pin-30，逐字转抄见「测试网钉」节）；剩余 **9 行**＝规格表第 9、10、11、12、13、14、17、18、19 行（常量族与限额触界面／元／边界·保留集）归 `RT-W1-01b-state.md`。两票同包**顺序施工**（同包不并行）：本票出骨架与公开面，-b 只填常量族与限额触界行为簇、不另立第二套形状。

**骨架／接口归属（切分注）**：八类形状签名（真源 `recon/I2a`：`RunState`／`Manifest`／`AskRequest`／`AskChoice`／`RunHandle`／`Budget`／`Convergence`／`LimitHit`）＋缺省值面全在本票——-b 不得改形状（改形状＝回本票或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （4 份）`specs/state.md` 全文（十节版式）；`specs/modules.md` `## state` 卡（签名以卡为准）；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（字段集真源）；`docs/runtime-refactor/eng/04-测试网设计.md` §三·§五（§三 归块行转抄落 -b、本票只留指针，§五 L2 纪律原文）——本票「测试网钉」「织网义务」两节已把所引行逐字转抄，施工期不必另开。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（specs/state.md「框架与依赖红线」首条）
边界红线: ① 不 import runtimev2 内任何其它块（R4，本块是最底层数据形状，防环）；② 模型出口零接触＝R7（不直引 `appv2.infra.llm_client`）＋R4（不引 `gateway_adapter`）**两闸合覆盖**；③ 不直引引擎（R6）；④ 外部依赖只许 `infra`（身份对象 `Actor` 类型——无专属闸，人审＋四闸降维）；⑤ `SseEvent` 只许以字符串前向引用指向 `transport`，不自建第二套帧形状

## 票面对象（specs/state.md「验收测试」表逐行转抄——本票 10 行：规格表第 1–8、15、16 行）

〔来源：specs/state.md「验收测试」表 :135–:153（本票取自 :135–:142、:149–:150），逐行原文；`#` 列＝规格表行序，-b 票续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 字段集与 `synth/S5` 矩阵一致（集合比较） | `tests/domains/test_v2_state.py::field_set_matches_matrix` | specs/state.md:135 |
| 2 | 不可变载荷全 `frozen+slots`、`RunState` 可变 | `tests/domains/test_v2_state.py::mutability_split` | specs/state.md:136 |
| 3 | 全字段 JSON 可投影（跨进程恢复无损前提） | `tests/domains/test_v2_state.py::state_json_projectable` | specs/state.md:137 |
| 4 | `messages` 只追加：相邻调用互为前缀延伸 | `tests/domains/test_v2_state.py::messages_append_only_prefix` | specs/state.md:138 |
| 5 | 相位合同一次性：回炉轮不重发、标记幂等 | `tests/domains/test_v2_state.py::contracts_appended_idempotent` | specs/state.md:139 |
| 6 | 对话层纯度：`dialogue` 条目 `origin` 全部落在来源闭世界内（不混层） | `tests/domains/test_v2_state.py::dialogue_layer_purity` | specs/state.md:140 |
| 7 | 追问播种＝前轮终链整链承接（跨 run 前缀延伸） | `tests/domains/test_v2_state.py::followup_seeds_full_chain` | specs/state.md:141 |
| 8 | 旧检查点如实读入（不抛错、对话通道空显、`schema_version` 如实） | `tests/domains/test_v2_state.py::legacy_checkpoint_read_honest` | specs/state.md:142 |
| 15 | 受理三形态互斥、`AskChoice` 两枚举闭世界 | `tests/domains/test_v2_state.py::ask_payload_shape_closed_world` | specs/state.md:149 |
| 16 | `Manifest.as_dict` 全键恒出＋列表拷贝语义 | `tests/domains/test_v2_state.py::manifest_all_keys_and_copy` | specs/state.md:150 |

> 测试文件归属（spec :155 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_state.py`（`state` 是阶段 2 新划的公共层块 `appv2/runtimev2/state/`，与现状 `appv2/runtime/state.py` 所在的旧码测试形状不同）；既有旧码测试本批不改。

## 测试网钉（specs/state.md「与闸的挂钩表」pin 行逐行转抄——本块全 6 钉，全在本票）

〔来源：specs/state.md「与闸的挂钩表」:186–:191，逐行原文〕

1. **pin-22（P0）**｜`RunState.messages` 只追加不改写（本块的**字段契约面**）｜测试 `::messages_append_only_prefix`｜现状：待织网（阶段 5）；循环行为面同钉挂 `specs/agent-loop.md`
2. **pin-23（P0）**｜追问播种＝前轮终链整链承接（**状态字段面**）｜测试 `::followup_seeds_full_chain`｜现状：待织网（阶段 5）；播种动作面同钉挂 `specs/agent-loop.md`
3. **pin-24**｜相位合同一次性（`contracts_appended`）｜测试 `::contracts_appended_idempotent`｜现状：待织网（阶段 5）
4. **pin-26**｜对话层纯度（`dialogue`／`process_notes` 不混层）｜测试 `::dialogue_layer_purity`｜现状：待织网（阶段 5）；渲染面同钉挂 `specs/understanding.md`
5. **pin-30（P2）**｜旧 run **状态字段读入**如实（`schema_version` 如实、`dialogue` 无业务写）——注：**钉文原两面＝compaction／黑匣子回放**（`eng/04a` pin-30 原文），本规格仅承接**状态字段读入面**（延伸挂法）；**回放面**挂 `specs/persistence.md`（行为 12，分工互认）；**compaction 半面**归 `context`（`synth/S1` H6／V2-79d）——**已登记于 `specs/context.md` 行为 9**（2026-10-16 收词：原「该规格尚未定稿，**待 `context` 规格（窗 B 编写）定稿时登记**」系时点表述，已过时——context 已定稿并登记）｜测试 `::legacy_checkpoint_read_honest`｜现状：待织网（阶段 5）
6. **pin-29（P0）**｜`AskChoice` 的 `kind` 判别字段（**形状面**）｜**闭环面挂 `specs/agent-loop.md`**；本块测试 `::ask_payload_shape_closed_world`｜现状：待织网（阶段 5）

- 钉的字段面分工（spec :198 原注照抄，防双头）：`pin-09`（`Manifest.material_truncated` 的**字段面**←本块；材料截断披露行为面←`specs/answering.md`）｜`pin-15`（连续反问上限的**参数键面**←本块；到顶截断与挂起不计轮行为面←`specs/clarification.md`）｜`pin-28`（`run_id` 的**字段面**←本块；全盖章与计费对账面←`specs/agent-loop.md`）——三钉由**他块挂行为面**、本块只承载**字段／参数键面**，故不重复挂行为测。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 6 条 pin 行只落本票一处；`RT-W1-01b-state.md` 零 pin 行、只留归属指针。

## 施工要点（specs/state.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/state.md:107 | 行为 1 字段集单点 | 字段集＝`synth/S5` 矩阵全量，断言集合比较相等（不判顺序） |
| specs/state.md:108 | 行为 2 两类形态 | `RunState` 可变；`Manifest`／`AskRequest`／`AskChoice`／`RunHandle`／`Budget`／`Convergence`／`LimitHit` 全 `frozen=True, slots=True` |
| specs/state.md:109 | 行为 3 状态可投影 | 全字段 JSON 原语（唯一例外 `RunHandle.stream`——非状态字段） |
| specs/state.md:110 | 行为 4 `messages` 只追加（钉 pin-22，P0） | 相邻调用互为前缀延伸（`后[:-len(尾段)] == 前`）；任何替换／重排历史条＝判失败 |
| specs/state.md:111 | 行为 5 相位合同一次性（钉 pin-24） | 回炉轮不重发、`contracts_appended` 标记写入幂等 |
| specs/state.md:112 | 行为 6 对话层纯度（钉 pin-26） | `dialogue` 条目形态 `{role, content, origin}`、origin 三值闭世界＋origin↔role 一致性不变量；写口＝bookkeeping `append_dialogue`，本块只定条目形状、不提供写函数 |
| specs/state.md:113 | 行为 7 追问播种（钉 pin-23，P0） | 前轮检查点终链整条为前缀（不裁剪、不摘要化），再接新问 |
| specs/state.md:114 | 行为 8 旧检查点如实读入（钉 pin-30 状态字段面） | 读入不抛错、`schema_version` 取读入态、`dialogue` 零业务写（AST＋行为双证）；「回放面」分工归 persistence 行为 12 |
| specs/state.md:120 | 行为 14 受理三形态互斥（钉 pin-29 形状面） | `resume_run_id` 与 `followup_run_id` 同在场抛错；`AskChoice.kind`／`decision` 越界抛错 |
| specs/state.md:121 | 行为 15 Manifest 全键恒出 | `as_dict()` 全键＋列表值返回拷贝（改返回值不改原对象） |

结构锚：specs/state.md:31 接口定义（**八类形状签名与缺省面＝本票交付物**，真源 `recon/I2a`）；:96–:103 框架与依赖红线（R4/R5b/R6/R7 挂闸与人审降维面）；:124–:129 不降级与静默禁令（合法降级路径＝无；唯一允许的「降级」＝旧检查点读入）。

## 织网义务（eng/04-测试网设计.md §三 归本块行——本票只留指针）

- 归块行 **B3**（H8 预算四限额边界）逐字转抄落 `RT-W1-01b-state.md`「织网义务」节（防两处真源漂移，转抄见该票）；本票不重复转抄。
- 钉级核对（母票原文照抄，归块切分不变）：eng/03 §二 W1 行所列「pin-22/23/24/26」与上表 6 钉中 4 钉吻合；pin-29／pin-30 为规格挂钩表另有、eng/03 未列——以规格为准，不冲突。
- 本票织网义务＝①「测试网钉」6 钉对应用例落网（本块 pin 行全量承载于本票）；② B3 行的 L1／L3 钉归 -b（本票只留指针）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」10 行逐行实现为 `tests/domains/test_v2_state.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–8、15、16）；
- 「测试网钉」6 钉对应用例在场且绿（pin-22／pin-23 为 P0 承重钉；pin-29 形状面）；
- 骨架与公开面按卡面签名齐备（八类形状，真源 `recon/I2a`），越界即判失败；
- `RunState` 字段集与 `synth/S5` 矩阵集合比较通过（`::field_set_matches_matrix`）；
- 边界闸 R4／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W1-01a 完成，产物 `appv2/runtimev2/state/`（骨架＋接口＋形状与状态语义＋受理载荷面），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
