# RT-W1-01 · state——V2 运行状态与限额

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/state.md`（状态「已定稿」——前置满足）
Touches modules: `state`（本票只建 state 本体；规格「触及的模块」表另声明 bookkeeping／orchestration 两消费侧，归各自票承接）
波次: W1（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W1 行：全体地基——本波出口判据「字段读写矩阵逐字段在场；限额机制单点、数值只引预算表；R4 绿」）
施工队: A 队（eng/03 §五 W1 行 A 队＝state，分配理由原文：「关键路径求快；钉最密（S5 字段矩阵＋pin-22/23/24/26），网兜得住」）｜复审强度: 100%（eng/03 §五：A 队收波 100% 过独立复审；复审网在 L0 直派，复审代理报告直送主窗）
前置: ① 规格定稿（`specs/state.md` 已定稿——已满足）；② 波次前置：无（W1 为首波）
阻塞: 无（W1 首票）｜被阻塞: RT-W2-01-persistence／RT-W2-02-transport／RT-W2-03-gateway_adapter（三票波次前置＝「W1 state 收波」）；RT-W3-01-bookkeeping 经 gateway_adapter 间接依赖本票

## 任务

按 `specs/state.md` 新建 `appv2/runtimev2/state/`：运行状态字段形状、模型调用 Manifest、受理与回执载荷、闭世界常量族、限额参数表与触界**判定**——**纯数据形状＋纯计算，零行为分支、零模型调用、零落盘、零业务语义判断**；写函数零供给（共享写口归 bookkeeping，见其规格）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: `specs/state.md` 全文（十节版式）；`specs/modules.md` `## state` 卡（签名以卡为准）；`docs/runtime-refactor/synth/S5-RunState字段矩阵.md`（字段集真源）；`docs/runtime-refactor/recon/K-上下文事件指南预算.md`（R-K-72…R-K-76 限额数值真源）；`docs/runtime-refactor/recon/I2a-状态常量与清单.md`（22 条常量真源）；`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二／§五；`docs/runtime-refactor/eng/04-测试网设计.md` §三／§五；AGENTS.md 硬纪律 6b（逐字稿纪律）

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（specs/state.md「框架与依赖红线」首条）
边界红线: ① 不 import runtimev2 内任何其它块（R4，本块是最底层数据形状，防环）；② 模型出口零接触＝R7（不直引 `appv2.infra.llm_client`）＋R4（不引 `gateway_adapter`）**两闸合覆盖**；③ 不直引引擎（R6）；④ 外部依赖只许 `infra`（身份对象 `Actor` 类型——无专属闸，人审＋四闸降维）；⑤ `SseEvent` 只许以字符串前向引用指向 `transport`，不自建第二套帧形状

## 票面对象（specs/state.md「验收测试」表逐行转抄，19 行）

〔来源：specs/state.md「验收测试」表 :135–:153，逐行原文〕

| # | 验收标准（原文） | 对应测试（原文标识） |
|---|---|---|
| 1 | 字段集与 `synth/S5` 矩阵一致（集合比较） | `tests/domains/test_v2_state.py::field_set_matches_matrix` |
| 2 | 不可变载荷全 `frozen+slots`、`RunState` 可变 | `tests/domains/test_v2_state.py::mutability_split` |
| 3 | 全字段 JSON 可投影（跨进程恢复无损前提） | `tests/domains/test_v2_state.py::state_json_projectable` |
| 4 | `messages` 只追加：相邻调用互为前缀延伸 | `tests/domains/test_v2_state.py::messages_append_only_prefix` |
| 5 | 相位合同一次性：回炉轮不重发、标记幂等 | `tests/domains/test_v2_state.py::contracts_appended_idempotent` |
| 6 | 对话层纯度：`dialogue` 条目 `origin` 全部落在来源闭世界内（不混层） | `tests/domains/test_v2_state.py::dialogue_layer_purity` |
| 7 | 追问播种＝前轮终链整链承接（跨 run 前缀延伸） | `tests/domains/test_v2_state.py::followup_seeds_full_chain` |
| 8 | 旧检查点如实读入（不抛错、对话通道空显、`schema_version` 如实） | `tests/domains/test_v2_state.py::legacy_checkpoint_read_honest` |
| 9 | 三族常量闭世界：越界取值抛错 | `tests/domains/test_v2_state.py::constant_families_closed_world` |
| 10 | 常量单点消费：无第二处自建集合、无裸状态字面量把守 | `tests/domains/test_v2_state.py::no_second_source_of_constants` |
| 11 | 限额参数键集闭世界、缺键取缺省（无散落字面量） | `tests/domains/test_v2_state.py::budget_keys_closed_world` |
| 12 | 触界判定确定、纯、不改入参 | `tests/domains/test_v2_state.py::check_limits_pure_and_deterministic` |
| 13 | 触界必带注记（恰三键）；未触界恒无注记 | `tests/domains/test_v2_state.py::converge_requires_notice` |
| 14 | `budget_hit` 与注记同现（触界不静默） | `tests/domains/test_v2_state.py::budget_hit_signal_present` |
| 15 | 受理三形态互斥、`AskChoice` 两枚举闭世界 | `tests/domains/test_v2_state.py::ask_payload_shape_closed_world` |
| 16 | `Manifest.as_dict` 全键恒出＋列表拷贝语义 | `tests/domains/test_v2_state.py::manifest_all_keys_and_copy` |
| 17 | 本块零判断零 IO（AST 扫描） | `tests/domains/test_v2_state.py::no_judgement_or_io_in_state` |
| 18 | 【边界集】空状态／超限状态／v1 旧态／异参受理 → 各落对应分支 | `tests/domains/test_v2_state.py::boundary_empty_overlimit_legacy_variants` |
| 19 | 【保留集】常规状态读写与未触界路径行为不变 | `tests/domains/test_v2_state.py::retention_normal_state_unchanged` |

> 测试文件归属（spec :155 节尾原注照抄）：本块验收测试绑**新建** `tests/domains/test_v2_state.py`（`state` 是阶段 2 新划的公共层块 `appv2/runtimev2/state/`，与现状 `appv2/runtime/state.py` 所在的旧码测试形状不同）；既有旧码测试本批不改。

## 测试网钉（specs/state.md「与闸的挂钩表」pin 行逐行转抄，6 钉）

〔来源：specs/state.md「与闸的挂钩表」:186–:191，逐行原文〕

1. **pin-22（P0）**｜`RunState.messages` 只追加不改写（本块的**字段契约面**）｜测试 `::messages_append_only_prefix`｜现状：待织网（阶段 5）；循环行为面同钉挂 `specs/agent-loop.md`
2. **pin-23（P0）**｜追问播种＝前轮终链整链承接（**状态字段面**）｜测试 `::followup_seeds_full_chain`｜现状：待织网（阶段 5）；播种动作面同钉挂 `specs/agent-loop.md`
3. **pin-24**｜相位合同一次性（`contracts_appended`）｜测试 `::contracts_appended_idempotent`｜现状：待织网（阶段 5）
4. **pin-26**｜对话层纯度（`dialogue`／`process_notes` 不混层）｜测试 `::dialogue_layer_purity`｜现状：待织网（阶段 5）；渲染面同钉挂 `specs/understanding.md`
5. **pin-30（P2）**｜旧 run **状态字段读入**如实（`schema_version` 如实、`dialogue` 无业务写）——注：**钉文原两面＝compaction／黑匣子回放**（`eng/04a` pin-30 原文），本规格仅承接**状态字段读入面**（延伸挂法）；**回放面**挂 `specs/persistence.md`（行为 12，分工互认）；**compaction 半面**归 `context`（`synth/S1` H6／V2-79d）——该规格尚未定稿，**待 `context` 规格（窗 B 编写）定稿时登记**｜测试 `::legacy_checkpoint_read_honest`｜现状：待织网（阶段 5）
6. **pin-29（P0）**｜`AskChoice` 的 `kind` 判别字段（**形状面**）｜**闭环面挂 `specs/agent-loop.md`**；本块测试 `::ask_payload_shape_closed_world`｜现状：待织网（阶段 5）

钉的字段面分工（spec :198 原注照抄，防双头）：`pin-09`（`Manifest.material_truncated` 的**字段面**←本块；材料截断披露行为面←`specs/answering.md`）｜`pin-15`（连续反问上限的**参数键面**←本块；到顶截断与挂起不计轮行为面←`specs/clarification.md`）｜`pin-28`（`run_id` 的**字段面**←本块；全盖章与计费对账面←`specs/agent-loop.md`）——三钉由**他块挂行为面**、本块只承载**字段／参数键面**，故不重复挂行为测。

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
| specs/state.md:115 | 行为 9 三族常量闭世界 | `STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT` 只在本块定义、越界抛错、每族有真实消费点 |
| specs/state.md:116 | 行为 10 限额键集闭世界 | `Budget` 七键，数值与缺省只引 `recon/K` R-K-72…R-K-76（「回炉一次／同参重投」两项为行为机制、非 Budget 键） |
| specs/state.md:117 | 行为 11 触界判定确定、纯 | `check_limits` 同输入两次结果相等、不改入参、无 IO 无模型无随机 |
| specs/state.md:118 | 行为 12 触界必带如实注记 | `hit` 非空 ⇔ `notice` 恰三键 `type/gates/content`；未触界恒 `notice is None` |
| specs/state.md:119 | 行为 13 触界不静默 | `Convergence` 与 `budget_hit` 同现（红线＝`arch/P7a` A-P7a-37） |
| specs/state.md:120 | 行为 14 受理三形态互斥（钉 pin-29 形状面） | `resume_run_id` 与 `followup_run_id` 同在场抛错；`AskChoice.kind`／`decision` 越界抛错 |
| specs/state.md:121 | 行为 15 Manifest 全键恒出 | `as_dict()` 全键＋列表值返回拷贝（改返回值不改原对象） |
| specs/state.md:122 | 行为 16 零判断零 IO | AST 扫描：无模型调用、无事件发射、无 DB／文件读写、无语义词表 |

结构锚：specs/state.md:31 接口定义（八类形状签名与缺省面，真源 `recon/I2a`）；:96–103 框架与依赖红线（R4/R5b/R6/R7 挂闸与人审降维面）；:124–129 不降级与静默禁令（合法降级路径＝无；唯一允许的「降级」＝旧检查点读入）。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单〕

> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |

- 归块注（拆票 mapping，待主窗对账确认）：该行「限额上限」的键集与数值面＝本块 `Budget`／`check_limits`（specs/state.md 行为 10／11，数值真源 `recon/K` R-K-72…R-K-76）；「触顶收敛**落地**」半行归 `bookkeeping`（RT-W3-01 行为 12 承接）——一行关涉两块，切分呈主窗。
- 钉级核对：eng/03 §二 W1 行所列「pin-22/23/24/26」与上表 6 钉中 4 钉吻合；pin-29／pin-30 为规格挂钩表另有、eng/03 未列——以规格为准，不冲突。
- L2 新规格钉不入门（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）——本票验收测试即 L2 钉源。

验收: 以下判据逐条全绿为过——
- 「票面对象」19 行逐行实现为 `tests/domains/test_v2_state.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行）；
- 「测试网钉」6 钉对应用例在场且绿（pin-22／pin-23 为 P0 承重钉）；
- `RunState` 字段集与 `synth/S5` 矩阵集合比较通过（`::field_set_matches_matrix`）；
- 边界闸 R4／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W1-01 完成，产物 `appv2/runtimev2/state/`，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
