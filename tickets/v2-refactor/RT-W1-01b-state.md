# RT-W1-01b · state——V2 运行状态与限额（-B：常量族与限额触界面／元／边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/state.md`（状态「已定稿」——前置满足）
Touches modules: `state`（本票只填 state 剩余行为簇：常量族／限额触界／元断言／边界·保留集；八类形状与公开面以 `RT-W1-01a-state.md` 为唯一真源）
波次: W1（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W1 行：全体地基——本波出口判据「字段读写矩阵逐字段在场；限额机制单点、数值只引预算表；R4 绿」）
施工队: A 队（eng/03 §五 W1 行 A 队＝state，分配理由原文：「关键路径求快；钉最密（S5 字段矩阵＋pin-22/23/24/26），网兜得住」）｜复审强度: 100%（eng/03 §五：A 队收波 100% 过独立复审；复审网在 L0 直派，复审代理报告直送主窗）
前置: ① 规格定稿（`specs/state.md` 已定稿——已满足）；② 波次前置：无（W1 为首波）；③ **`RT-W1-01a-state.md` 收票**（同包顺序施工、同包不并行——票间纪律）
阻塞: `RT-W1-01a-state.md`（-b 前置＝-a 收票）｜被阻塞: W2 各票波次前置＝「W1 state 收波」（须 -a＋-b 两票全收——persistence／transport 两包各 -a／-b 两票、gateway_adapter，票号以主窗 manifest 为准）；RT-W3-01a/b/c-bookkeeping 经 gateway_adapter 间接依赖 state 收波

## 任务

接 `RT-W1-01a-state.md` 落地的骨架，填 `appv2/runtimev2/state/` 的**剩余行为簇**：三族常量的闭世界与单点消费、限额键集与触界**判定**的纯性、触界注记与机读信号的同现，程序侧零判断零 IO 红线，以及边界集／保留集两行。

**本票＝state 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **19 行**，超 15 行上限 → 切 -A／-B；本票收**剩余 9 行**＝规格表第 9、10、11、12、13、14、17、18、19 行（常量族与限额触界面／元／边界·保留集）；前 10 行与**本块 6 条 pin 行**（pin-22／pin-23／pin-24／pin-26／pin-29／pin-30）全在 -a，本票零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。

**形状归属（切分注）**：八类形状签名与缺省面（真源 `recon/I2a`）由 -a 落地为本票唯一真源；本票只加常量族与触界行为、**不改形状**（改形状＝回 -a 或回设计仓）。常量族定义（`STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT`）与限额键集为本票面，仍单点落本块 `state/` 包内。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/state.md` 全文（十节版式，行为 9–13、16 与验收表第 9–14、17–19 行为本票面）；`specs/modules.md` `## state` 卡（签名以卡为准）；`docs/runtime-refactor/recon/I2a-状态常量与清单.md`（22 条常量真源）；`docs/runtime-refactor/recon/K-上下文事件指南预算.md`（R-K-72…R-K-76 限额数值真源）；`docs/runtime-refactor/eng/04-测试网设计.md` §三·§五（B3 行在本票「织网义务」节逐字转抄，施工期不必另开）。

框架红线: 无点名框架（`langgraph`／`langchain` 只许活在 `orchestration`）——对应闸 R5b 契约（specs/state.md「框架与依赖红线」首条）
边界红线: ① 不 import runtimev2 内任何其它块（R4，本块是最底层数据形状，防环）；② 模型出口零接触＝R7（不直引 `appv2.infra.llm_client`）＋R4（不引 `gateway_adapter`）**两闸合覆盖**；③ 不直引引擎（R6）；④ 外部依赖只许 `infra`（身份对象 `Actor` 类型——无专属闸，人审＋四闸降维）；⑤ `SseEvent` 只许以字符串前向引用指向 `transport`，不自建第二套帧形状；⑥ **禁手写替代**：常量族／限额键集单点落本块 `state/` 包内，不得在包外第二处自建集合、不得以裸状态字面量把守（行 10 `::no_second_source_of_constants` 即此红线的机检面）；不得改 -a 已定的八类形状另立第二套

## 票面对象（specs/state.md「验收测试」表逐行转抄——本票 9 行：规格表第 9、10、11、12、13、14、17、18、19 行）

〔来源：specs/state.md「验收测试」表 :135–:153（本票取自 :143–:148、:151–:153），逐行原文；`#` 列＝规格表行序（与 -a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 9 | 三族常量闭世界：越界取值抛错 | `tests/domains/test_v2_state.py::constant_families_closed_world` | specs/state.md:143 |
| 10 | 常量单点消费：无第二处自建集合、无裸状态字面量把守 | `tests/domains/test_v2_state.py::no_second_source_of_constants` | specs/state.md:144 |
| 11 | 限额参数键集闭世界、缺键取缺省（无散落字面量） | `tests/domains/test_v2_state.py::budget_keys_closed_world` | specs/state.md:145 |
| 12 | 触界判定确定、纯、不改入参 | `tests/domains/test_v2_state.py::check_limits_pure_and_deterministic` | specs/state.md:146 |
| 13 | 触界必带注记（恰三键）；未触界恒无注记 | `tests/domains/test_v2_state.py::converge_requires_notice` | specs/state.md:147 |
| 14 | `budget_hit` 与注记同现（触界不静默） | `tests/domains/test_v2_state.py::budget_hit_signal_present` | specs/state.md:148 |
| 17 | 本块零判断零 IO（AST 扫描） | `tests/domains/test_v2_state.py::no_judgement_or_io_in_state` | specs/state.md:151 |
| 18 | 【边界集】空状态／超限状态／v1 旧态／异参受理 → 各落对应分支 | `tests/domains/test_v2_state.py::boundary_empty_overlimit_legacy_variants` | specs/state.md:152 |
| 19 | 【保留集】常规状态读写与未触界路径行为不变 | `tests/domains/test_v2_state.py::retention_normal_state_unchanged` | specs/state.md:153 |

> 测试文件归属（spec :155 节尾原注照抄）：本票 9 行与 -a 的 10 行同落**同一个新建文件** `tests/domains/test_v2_state.py`；既有旧码测试本批不改。

## 测试网钉（本块 6 条 pin 行已在 `RT-W1-01a-state.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-22 ↔ 行 4、pin-23 ↔ 行 7、pin-24 ↔ 行 5、pin-26 ↔ 行 6、pin-29 ↔ 行 15、pin-30 ↔ 行 8——六条钉的机检用例全在 -a；本票 9 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -a 一处。

## 施工要点（specs/state.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/state.md:115 | 行为 9 三族常量闭世界 | `STEP_KINDS`／`RUN_STATUS_KINDS`／`INTENT` 只在本块定义、越界抛错、每族有真实消费点 |
| specs/state.md:116 | 行为 10 限额键集闭世界 | `Budget` 七键，数值与缺省只引 `recon/K` R-K-72…R-K-76（「回炉一次／同参重投」两项为行为机制、非 Budget 键） |
| specs/state.md:117 | 行为 11 触界判定确定、纯 | `check_limits` 同输入两次结果相等、不改入参、无 IO 无模型无随机 |
| specs/state.md:118 | 行为 12 触界必带如实注记 | `hit` 非空 ⇔ `notice` 恰三键 `type/gates/content`；未触界恒 `notice is None` |
| specs/state.md:119 | 行为 13 触界不静默 | `Convergence` 与 `budget_hit` 同现（红线＝`arch/P7a` A-P7a-37） |
| specs/state.md:122 | 行为 16 零判断零 IO | AST 扫描：无模型调用、无事件发射、无 DB／文件读写、无语义词表 |
| specs/state.md:152 | 行 18 边界集 | 空状态／超限状态／v1 旧态／异参受理四形各落对应分支 |
| specs/state.md:153 | 行 19 保留集 | 常规状态读写与未触界路径行为不变 |

结构锚：specs/state.md:31 接口定义（八类形状真源＝-a 已落地，本票只加行为、**不改形状**；`Budget` 键集与 `check_limits` 纯函数签名本票约束其行为面）；:124–:129 不降级与静默禁令（合法降级路径＝无；唯一允许的「降级」＝旧检查点读入）；卡注（2026-10-15，L0）：通知类型（`notice.type`）取值闭世界归 `transport`，本块只定义「触界注记必须恰三键」的形状——行 13 只判三键形状，不复述类型取值。

## 织网义务（eng/04-测试网设计.md §三 归本块行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单〕

> | B3 | H8 预算四限额边界（现只钉了 CLARIFY_ASK_CAP=6） | 每限额上限/触顶收敛行为钉（数值只引预算表） | 中 |

- 归块注（拆票 mapping，待主窗对账确认）：该行「限额上限」的**键集与数值面**＝本票 9 行（行 11 键集闭世界＋行 12 触界纯判定；specs/state.md 行为 10／11，数值真源 `recon/K` R-K-72…R-K-76）；「触顶收敛**落地**」半行归 `bookkeeping`（RT-W3-01a/b/c 行为 12 承接）——一行关涉两块，切分呈主窗。
- 转抄注（防两处漂移）：该 B3 行逐字转抄只在本票一处；`RT-W1-01a-state.md` 只留指针、不重复转抄。
- 本票织网义务＝① 上述 B3 行键集与数值半面的 L1／L3 钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；② 本票 9 行对应用例落网；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」9 行逐行实现为 `tests/domains/test_v2_state.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 9、10、11、12、13、14、17、18、19）；
- 三族常量闭世界（行 9）＋常量单点消费（行 10）＋限额键集闭世界（行 11）＋触界判定纯且确定（行 12）＋注记恰三键（行 13）＋`budget_hit` 同现（行 14）全绿；
- AST 红线断言 `::no_judgement_or_io_in_state` 绿（无模型调用／无事件发射／无 DB／文件读写／无语义词表）；
- 边界闸 R4／R5b／R6／R7 在 `lint-imports` 双配置下绿（V2 侧 18 KEPT 基线不红）；
- 形状单点：八类形状仍以 -a 落地的为唯一真源，本票不改形状（改形状＝回 -a 或回设计仓）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W1-01b 完成，产物 `appv2/runtimev2/state/`（剩余行为簇：常量族与限额触界面／元／边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
