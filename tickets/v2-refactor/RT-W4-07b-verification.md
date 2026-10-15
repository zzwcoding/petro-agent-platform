# RT-W4-07b · verification——V2 核验（-B：红线与健壮性簇＋边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/verification.md`（状态「已定稿」——前置满足）
Touches modules: `verification`（本票只填 verification 的红线与健壮性行为簇；规格「触及的模块」表另声明 state／transport 两关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 100%（eng/03 §五 流水 48 规则——本块在 §五 表 W4 行质量关键侧，该列分配理由整行原文「零 LLM 精度件＋P0 钉最重的交付面给 B」（该行 B 列三块＝`preconditions`／`answering`／`verification`）；§五 头注原文「**2026-10-16 更新：双队制废止**——改为单窗＋子代理 ≤3 并发、小票制，流水 48；下表 A/B 分配**降级为「复审强度规则」保留**：B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证」——故本票复审强度＝100%，复审网在 L0 直派、报告直送主窗）
前置: ① 规格定稿（`specs/verification.md` 已定稿——已满足）；② **`RT-W4-07a-verification.md` 收票**（同包顺序施工、同包不并行——eng/03 §二 W4 纪律）；③ W3 全收波（经 -07a 传递，已满足）
阻塞: `RT-W4-07a-verification.md`（-07b 前置＝-07a 收票）｜被阻塞: W5 `orchestration`

## 任务

接 `RT-W4-07a-verification.md` 落地的骨架，填 `appv2/runtimev2/verification/` 的**红线与健壮性簇**：确定性（同输入两次运行 `Verdict` 五个计数与 `ok` 完全一致）、两处闭世界的越界判失败、核验器抛错的 fail-closed（不静默放行）、零 LLM（AST＋import 双证）与零词表／正则语义判断两条 AST 红线，以及【边界集】／【保留集】两行。

**本票＝verification 的 -B 票**。拆分理由（承 -A 票「拆分理由」节，同一条——小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **18 行**，超 15 行上限 → 切 -A／-B。**-A**＝骨架＋接口＋核心核验簇＋交付记账面（逐行核验／数值复述／无据改写＋notice／矛盾分列／归属审／`Verdict` 齐备／判据加严两行／零数值断言／机读信号在场／行集对账）＋**本块全部织网钉**（pin-01／pin-02／pin-10／pin-11／pin-12／pin-03 六行）；**-B**＝本票 7 行＝规格表第 10–14、17、18 行（确定性／`RewriteRecord.reason` 闭世界／核验器抛错 fail-closed／零 LLM AST＋import 双证／零词表正则 AST／【边界集】／【保留集】）——本票 7 行 ≤15、必读 6 份 ≤6，聚焦「确定性与红线守门」这一行为簇；两票同包**顺序施工**（-B 前置＝-A 收票），不并行：本票不另立第二套形状，`Verdict`／`RewriteRecord`／`Gap` 仍以 -07a 落地的为唯一真源。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/verification.md` 全文（十节版式）；`specs/modules.md` `## verification` 卡（签名以卡为准）＋`## 边界规则`（R1／R2／R5b／R7／R8）；`tools/importlinter_v2.toml`（R2／R5b／R7／R8 四契约字面——本票两条 AST 红线的闸侧对账依据）；`tests/domains/test_v2_four_phase.py`（AST 机检先例，规格「框架与依赖红线」原文所指 `:446`——零 LLM 与零语义两条断言的写法先例）；`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（核验规则与归属审真源——行为 7 边界记号化／全角归一的判据与承载豁免 R-A2-11，【边界集】／【保留集】两行判据）；`specs/state.md`（状态形状面与闭世界常量族——`RewriteRecord` 越界判失败的形状真源）。eng/04 §三 关联行已在本票「织网义务」节与 -07a 同节逐字转抄，施工期不必另开。

框架红线: **无点名框架**（本模块不引入任何框架、**不调模型**）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）＋ **零 LLM 铁律**（R7／R8，见边界红线①）
边界红线: ① **零 LLM 铁律**：本块**不调模型、不存在模型调用发起面**——不引 `appv2.runtimev2.gateway_adapter`（**R8** :119–:123，source 覆盖 `preconditions`／`verification`／`execution`）＋不直引 `appv2.infra.llm_client`（R7 :113–:117，本块天然满足）；**验收写法＝AST 机检（先例 `tests/domains/test_v2_four_phase.py:446`）＋「无旁路」断言**（规格「框架与依赖红线」原文）；② 不得直接 import `langgraph`／`langchain`——R5b（:100–:105）；③ 只经 `transport` 公开面发帧——「只经包根」半面由 R2 覆盖（:73–:78）；另一半「不自行拼 wire 帧／不直连 SSE 通道」**无专属闸→人审**（规格「与闸的挂钩表」:133 行原文），本票不得降维自设闸（降维需新增验收行，本批未授权）；④ 七个业务相位互不 import——R1（:66–:71）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ **程序不判语义**：无词表／正则语义判定（AST 断言 `::no_lexicon_or_regex_in_verification`，豁免面＝形态处理／集合成员判定）；⑦ **禁手写替代**：不得自建模型客户端、不得自建帧通路（对应闸 R8／R2）；⑧ **形状单点**：三形状仍以 -07a 落地的为唯一真源，本票不改形状（改形状＝回 -07a 或回设计仓）；本票不实现核验主链（逐行判定／数值复述／改写／分列／归属审／行集对账归 -07a）

## 票面对象（specs/verification.md「验收测试」表逐行转抄——本票 7 行：规格表第 10–14、17、18 行）

〔来源：specs/verification.md「验收测试」表 :93–:110（本票取自 :102–:106、:109–:110），逐行原文；`#` 列＝规格表行序（与 -07a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 10 | 不确定性：同输入两次运行 verdict 完全一致 | `tests/domains/test_v2_verification.py::deterministic_repeatable` | specs/verification.md:102 |
| 11 | `RewriteRecord.reason` 越界取值 → 判失败 | `tests/domains/test_v2_verification.py::rewrite_reason_closed_world` | specs/verification.md:103 |
| 12 | 核验器抛错 → fail-closed 取 `ok=False`（不静默放行） | `tests/domains/test_v2_verification.py::verifier_error_fail_closed` | specs/verification.md:104 |
| 13 | 本模块零 LLM（AST＋import 双证） | `tests/domains/test_v2_verification.py::no_model_call_in_verification` | specs/verification.md:105 |
| 14 | 程序侧无词表／正则语义判断（AST 扫描；豁免面＝形态处理／集合成员判定） | `tests/domains/test_v2_verification.py::no_lexicon_or_regex_in_verification` | specs/verification.md:106 |
| 17 | 【边界集】单句答案／零材料答案／双源矛盾／全角数字 → 各自落到对应分支 | `tests/domains/test_v2_verification.py::boundary_single_zero_material_conflict_fullwidth` | specs/verification.md:109 |
| 18 | 【保留集】无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变 | `tests/domains/test_v2_verification.py::retention_clean_answer_unchanged` | specs/verification.md:110 |

> 测试文件归属（票注，非规格引文）：本票 7 行与 -07a 的 11 行同落**同一个新建文件** `tests/domains/test_v2_verification.py`（规格 :112 节尾原注已在 -07a 同节照抄）；既有 `tests/domains/test_v2_agent_verify.py` 本批不改。
> 行序缺口说明（票注）：本票行序跳过第 1–9、15、16 行（归 -07a）——`#` 列两票共用规格表行序，便于 manifest 逐行对账。
> 跨行衔接注（票注）：【边界集】行（17）与【保留集】行（18）是**跨两票行为的聚合行**——其四形／两态判据的行为实现分别在 -07a（零材料答案／双源矛盾／全角数字／单句答案的逐行判定与改写）与本票（fail-closed 与闭世界守门）；保留集行的「`ok=True` 行为不变」与规格行为 9（`Verdict.ok=False` 才回炉）配对，本票只落其断言、不改 -07a 的主链口径。
> 规格侧缺口登记（四项：信号落地写口〔**已消化（流水 50）**，见 `RT-W4-07a-verification.md` 票注①〕／行为 11「补如实注记」载体／风险 5 增量引标跨块待办／「不自行拼 wire 帧」人审面）见 `RT-W4-07a-verification.md`「票面对象」节票注——本票不重复登记（防两处漂移）。

## 测试网钉（本块 6 条 pin 行已在 `RT-W4-07a-verification.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

〔来源：specs/verification.md「与闸的挂钩表」:137–:142——表内 pin 行 6 行（pin-01／pin-02／pin-10／pin-11／pin-12／pin-03）的落点行为全在核心核验簇与交付记账面（-07a 行 2／3／5／9／16），已随 `RT-W4-07a-verification.md`「测试网钉」节逐字转抄并落地〕

- 核对关系（防两处漂移）：pin-01 ↔ -07a 行 5、pin-02 ↔ -07a 行 2／3、pin-10 ↔ -07a 行 9、pin-11 ↔ -07a 行 3、pin-12 ↔ -07a 行 16、pin-03 ＝本块无独立落点（只登记备查）——六条钉的机检用例全在 -07a；本票 7 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -07a 一处（照 `RT-W4-01b-understanding.md`／`RT-W4-02b-clarification.md`／`RT-W4-05b-execution.md` 同款纪律）。
- 规格「与闸的挂钩表」其余行（spec gate 两行、R8／R5b／R2 三条边界闸、零语义与判据加严两条 `测试 ::...` 行、质量度量织网行、末行人审）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄。

## 施工要点（specs/verification.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/verification.md:57 | 接口定义 确定性 | 同一输入两次运行，`Verdict` 的五个计数与 `ok` **完全一致**（零随机、零模型）——行 10 |
| specs/verification.md:54 | 接口定义 闭世界（一） | `RewriteRecord.reason` 闭世界（`no_material`｜`conflict`）；**越界值判失败**——行 11 |
| specs/verification.md:58 | 接口定义 错误契约 | 核验器自身抛错 → **不判 `Verdict.ok=True`**（fail-closed），转 `Verdict.ok=False` ＋缺口，由 `orchestration` 承接——行 12 |
| specs/verification.md:79 | 行为 9 `Verdict.ok=False` 才回炉 | 只要仍存在无据断言残留 → `ok=False`（供 `orchestration` 决定回炉）；`Verdict.ok=True` 时**不得再改写**——与保留集行（`ok=True` 行为不变）成对 |
| specs/verification.md:64 | 框架与依赖红线 零 LLM 面（R8） | 本块零 LLM 面（R8），**不存在模型调用发起面**——验收写法＝AST 机检（先例 `tests/domains/test_v2_four_phase.py:446`）＋「无旁路」断言——行 13 |
| specs/verification.md:67 | 框架与依赖红线 禁手写替代 | 不得自建模型客户端、不得自建帧通路（R8／R2）；**「自建帧通路」一面**的另一半「不自行拼 wire 帧」无专属闸 → 人审，登记待补（原文已在 -07a 票注④） |
| specs/verification.md:85 | 不降级与静默禁令 合法降级路径 | **合法降级路径：无**（本模块不降级；核验器不可用时按 fail-closed 取 `ok=False`）——本票 7 行不得引入任何静默放行分支 |
| specs/verification.md:106 | 行 14 零语义判断 | AST 扫描本模块：无语义词表／正则（豁免面＝形态处理／集合成员判定） |
| specs/verification.md:109 | 行 17 边界集 | 单句答案／零材料答案／双源矛盾／全角数字四形各落对应分支 |
| specs/verification.md:110 | 行 18 保留集 | 无矛盾、有支撑的普通答案：各字段取值与 `ok=True` 行为不变 |

结构锚：specs/verification.md:32–:51 接口定义（**形状真源＝-07a 已落地的三形状**，本票只加行为、不改形状；`Gap` 闭世界 `refused`｜`missing`｜`unverified` 复用 `answering` 口径）；:61–:67 框架与依赖红线（零 LLM 面 R8／R5b／R2＋禁手写替代；「不自行拼 wire 帧」半面无专属闸→人审，见 :133 行）；:83–:87 不降级与静默禁令（**合法降级路径＝无**；改写／分列／归属失败必产机读信号：`verdict`／`notice` 事件〔类型取自 `synth/S6-事件与帧目录.md`〕＋ step payload 各字段；改写**不得静默**——红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」）；:89–:110 验收测试表（`#` 行序与 -07a 共用）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 关联行——唯一关联行已在 -07a 同节逐字转抄）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行；唯一关联行 B5 已随 `RT-W4-07a-verification.md`「织网义务」节原文照抄）〕

- 归块注（呈主窗对账）：eng/04 §三 表内**无一行明写「对应 runtimev2 `verification`」**（该表内唯一明写行为块名者是 B1→`bookkeeping`）。全块唯一关联行＝ B5「帧协议级时序（step/text/ask/verdict/done/error 序与 data 形）｜从 `eval/results/frames/` 真帧流转离线 golden 回放钉｜中」，该行已在 `RT-W4-07a-verification.md`「织网义务」节**原文照抄**，本票不重复转抄（同一行两处转抄＝两处真源必漂移，逐字稿纪律）。
- 本票在该行的义务面（关系注，非新钉）：B5 的 `verdict` 帧有 `verify`（核验裁决）与 `final`（收口）两形（形状真源 `synth/S6-事件与帧目录.md` §二）——`verify` 形的**裁决落定后果**（`ok=False` 触发回炉、`ok=True` 不再改写，行为 9）由本票行 10／12／18 承载；批次落定本身归 `orchestration`（规格行为 10）。钉法真源＝`eval/results/frames/` 真帧流转离线 golden 回放钉。
- 关联行（已他归）：B1（公共位与结果归一，明写归 `bookkeeping`）——本块只经 step payload 消费其记账面，不另立钉；B3（限额上限／触顶收敛）数值面归 `state`，非本块行。
- 本票织网义务＝① B5 关联行的 L3 回放钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；② 本票 7 行对应用例落网（含【边界集】／【保留集】两行）；③ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」7 行逐行实现为 `tests/domains/test_v2_verification.py` 用例并全绿，测试标识与规格列逐字一致（含【边界集】／【保留集】两行；`#` 保留规格表行序 10–14、17、18）；
- 两条 AST 红线断言绿：`::no_model_call_in_verification`（零 LLM AST＋import 双证）＋`::no_lexicon_or_regex_in_verification`（语义词表／正则零出现，豁免面按规格原文）；
- 闭世界越界即判失败（行 11）＋核验器抛错 fail-closed 取 `ok=False`（行 12，不静默放行）＋确定性（行 10，同输入两次运行结论一致）；
- 边界闸 R1／R2／R5b／R6／R7／R8 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 形状单点：`Verdict`／`RewriteRecord`／`Gap` 三形状仍以 -07a 落地的为唯一真源，本票不改形状（改形状＝回 -07a 或回设计仓）；
- 规格侧缺口登记（四项）见 `RT-W4-07a-verification.md` 票注——本票不重复登记（防两处漂移）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-07b 完成，产物 `appv2/runtimev2/verification/`（红线与健壮性簇＋边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
