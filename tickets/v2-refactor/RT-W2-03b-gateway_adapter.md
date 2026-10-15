# RT-W2-03b · gateway_adapter——V2 网关桥（-B：替身面＋元面＋边界·保留集）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/gateway_adapter.md`（状态「已定稿」——前置满足）
Touches modules: `gateway_adapter`（本票只填 gateway_adapter 的替身面与元／边界·保留行，形状以 -03a 落地的为唯一真源；规格「触及的模块」表另声明 bookkeeping／infra 两关联侧，归各自票承接）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「模型出口唯一＋替身可注入」半句；同 row 强调原文：「**gateway_adapter 的测试替身（fake）是后续所有相位测试的地基，必须最先可用**」）
施工队: B 队（eng/03 §五 终表 W2 行 B 队列＝「gateway_adapter」，分配理由整行原文「出口/计费/替身＝慢漏型缺陷，必须稳」；已按 eng/03 §五 终表对齐；提交前缀＝[B]——eng/03 §五 扣件①）｜复审强度: 100%（主窗裁：B 队施工≠免复审——本票维持 100% 过独立复审，复审网在 L0 直派；eng/03 §五 B 队标准为抽 50%，本票按主窗裁提高）
前置: ① 规格定稿（`specs/gateway_adapter.md` 已定稿——已满足）；② **`RT-W2-03a-gateway_adapter.md` 收票**（同包顺序施工、同包不并行——骨架、签名面与「`ModelReply` 暂寄居 `fake.py`」结构锚以 -03a 为唯一真源）；③ 波次前置：**W1 state 收波**（经 -03a 传递，已满足；注：eng/03 §一依赖图 gateway_adapter → infra，不依赖 state——波次归属按 eng/03 §二 W2 行不变，呈对账留痕）
阻塞: `RT-W2-03a-gateway_adapter.md`（-03b 前置＝-03a 收票）｜被阻塞: `RT-W3-01a-bookkeeping.md`（依赖图 bookkeeping → gateway_adapter——子票 RT-W3-01a/b/c，票号以主窗 manifest 为准）；W4 全部相位（替身是后续所有相位测试的地基）

## 任务

接 `RT-W2-03a-gateway_adapter.md` 落地的骨架与签名面，填 `appv2/runtimev2/gateway_adapter/` 的**替身面与元／边界·保留行**：替身与生产桥**同面**（同一签名＋同一回执形状）、替身**不静默兜底**（未剧本化且无 `default`→当场抛错）、替身**观测面只读**（注入剧本不被改写、留痕为调用时刻快照），外加本块零判断的元面断言与【边界集】／【保留集】两行。替身面沿用既有织网地基件（见「织网义务」）。

**本票＝gateway_adapter 的 -B 票**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **16 行**，超 15 行上限 → 切 -A／-B 两票。本票收 **剩余 6 行**＝规格表第 11–16 行（替身同面／替身不静默兜底／替身观测面只读／本块零判断元面／【边界集】／【保留集】）；前 10 行与**本块 3 条 pin 行**（pin-25／pin-27／pin-28）全在 -03a，本票**零 pin 行**、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移）。两票同包**顺序施工**（同包不并行）：本票只填行为、**不改 -03a 落地的形状**（`ModelReply` 十字段／`complete` 签名／冻结时钟四分支／`ScriptedCompleter` 签名——改形状＝回 -03a 或回设计仓）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （5 份）`specs/gateway_adapter.md` 全文（十节版式）；`specs/modules.md` `## gateway_adapter` 卡（签名以卡为准）；`appv2/runtimev2/gateway_adapter/fake.py`（既有替身真源——`ScriptedCompleter`／`ModelReply` 暂寄居处）；`tests/runtimev2/test_gateway_adapter_fake.py`（替身自证件，14 测——行 11–13 的看守件）；`docs/runtime-refactor/eng/04-测试网设计.md` §五（织网地基件口径与挂账行）。eng/04 §三 B7b 行已在 `RT-W2-03a-gateway_adapter.md` 同节逐字转抄，施工期不必另开。

**小票制自检（流水 48）**：票面对象 6 行 ≤ 15 ✓；先读 5 份 ≤ 6 ✓；聚焦一个行为簇＝替身面（同面／不静默兜底／观测面只读）＋元与边界·保留收口 ✓ → 本票不派生。

框架红线: 无点名框架（本块不引入任何框架）——对应闸 R5b 契约
边界红线: ① 模型供应商唯一出口＝`infra`（`llm_client`／`gateway.complete`；B6）——本块是全工程**唯一允许**直引该出口的 runtimev2 块，对应闸 R7 契约（其 `source` 不含本块——例外面）＋ V2 B6 契约（`tools/importlinter_v2.toml`：`litellm` 唯一接触点＝`appv2.infra.llm_client`）；② 不直引引擎（R6）；③ 不引包内其它块（本块只依赖 `infra`——无专属闸→人审＋AST 断言「本块 import 只出现 infra」登记待补）；④ 禁手写替代（不自建 HTTP 客户端／供应商 SDK 直连——V2 B6 契约＋AST 断言「不出现 httpx／requests／裸 SDK」登记待补）

## 票面对象（specs/gateway_adapter.md「验收测试」表逐行转抄——本票 6 行：规格表第 11–16 行）

〔来源：specs/gateway_adapter.md「验收测试」表 :115–:120，逐行原文；`#` 列＝规格表行序（与 -03a 同一行序，不重编）〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 11 | 替身与生产桥同面（签名＋回执形状） | `tests/runtimev2/test_gateway_adapter_fake.py::TestCardFace::test_complete_signature_matches_card` | specs/gateway_adapter.md:115 |
| 12 | 替身不静默兜底（无 default 抛错；有 default 照回且留痕） | `tests/runtimev2/test_gateway_adapter_fake.py::TestDefaultFallback::test_unscripted_without_default_fails_fast` | specs/gateway_adapter.md:116 |
| 13 | 替身观测面只读（注入剧本不被改写、留痕为调用时刻快照） | `tests/runtimev2/test_gateway_adapter_fake.py::TestObservationFaces::test_script_injection_readonly` | specs/gateway_adapter.md:117 |
| 14 | 本块零判断（AST 扫描） | `tests/domains/test_v2_gateway_adapter.py::no_judgement_in_gateway_adapter` | specs/gateway_adapter.md:118 |
| 15 | 【边界集】空 messages／超长 messages／限流失败／非法时钟值 → 各落对应分支 | `tests/domains/test_v2_gateway_adapter.py::boundary_empty_huge_ratelimit_clock` | specs/gateway_adapter.md:119 |
| 16 | 【保留集】常规成功调用的回执字段与归因行为不变 | `tests/domains/test_v2_gateway_adapter.py::retention_normal_call_unchanged` | specs/gateway_adapter.md:120 |

> 测试文件归属（票注，非规格引文）：本票行 11–13 绑**既有**织网地基件 `tests/runtimev2/test_gateway_adapter_fake.py`（该件已按新接口面回写并**全绿（该件 14 测；`tests/runtimev2/` 目录合计 45 测全绿）**，由替身随规格同步维护）；行 14–16 绑**新建** `tests/domains/test_v2_gateway_adapter.py`（与 -03a 同一文件——spec :122 节尾原注已在 `RT-W2-03a-gateway_adapter.md` 同节照抄，本票不重复转抄，防两处漂移）。

## 测试网钉（本块 3 条 pin 行已在 `RT-W2-03a-gateway_adapter.md` 同节全量逐字转抄——本票零 pin 行，不重复转抄）

- 核对关系（防两处漂移）：pin-25 ↔ 行 3、pin-27 ↔ 行 9、pin-28 ↔ 行 5——三条钉的逐字转抄与机检用例全在 -03a；本票 6 行不承载任何 pin 行。
- 分票理由（逐字稿纪律）：同一 pin 行在两票重复转抄＝两处真源必漂移，故本块 pin 行只落 -03a 一处（先例 `RT-W4-05b-execution.md` 分票理由原文）。

## 施工要点（specs/gateway_adapter.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/gateway_adapter.md:90 | 行为 11 替身与生产桥同面 | `ScriptedCompleter.complete` 与生产桥同形签名（替身 `run_id` 可缺省）与同一回执形状；离线零触网；观测面只读留痕 |
| specs/gateway_adapter.md:91 | 行为 12 替身不静默兜底 | 未剧本化 caller 且未设 `default`→当场抛错；设了 `default` 照回且调用照样留痕 |
| specs/gateway_adapter.md:92 | 行为 13 本块零判断 | 不读词表、不判语义、不做业务分支（只有「可重试／不可重试」结构分派；AST 扫描） |
| specs/gateway_adapter.md:119 | 行 15 边界集 | 空 `messages`／超长 `messages`／限流失败／非法时钟值四形各落对应分支（分支本体在 -03a 的行 2／6／8／9） |
| specs/gateway_adapter.md:120 | 行 16 保留集 | 常规成功调用的回执字段与归因行为不变（-03a 落地的同面签名与回执形状不得因本票回退） |

结构锚：specs/gateway_adapter.md:32 接口定义（`ModelReply` 十字段／`complete`／冻结时钟常量／`ScriptedCompleter` 签名——**形状真源＝-03a 已落地的**，本票只加行为、不改形状）；:70–76 框架与依赖红线（R7 例外面＋V2 B6 契约）；:94–99 不降级与静默禁令（合法降级路径＝无；失败必须留痕；估算必标注；冻结时钟不得静默回落真实钟——替身面同样不得静默兜底，行为 12）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §五 织网地基件承接＋§三 B7b 指针）

〔来源：eng/04-测试网设计.md §五 织网工序 step 1 原文＋§三 B7b 行（B7b 逐字转抄落 `RT-W2-03a-gateway_adapter.md`）〕

- **沿用既有替身**（拆票 mapping 注）：eng/04 §五 step 1 原文照抄——「**钉地基**（对应 W2）：`gateway_adapter` 测试替身（ScriptedCompleter 等价物）＋ leg 格式回放 harness——没有这两件，后面全是沙上建塔。**✅ 已落成（2026-10-15，子代理施工＋主窗复验）**：`runtimev2/gateway_adapter/fake.py`（45 测中替身自证 15）＋ `tests/runtimev2/`（leg_replay 19 测／frozen_clock 8 测）；45 测全绿、18 契约 KEPT、ruff 净。挂账：替身接口按卡面同步实现、待 gateway_adapter 规格定稿回写（docstring 已登记）」——替身与替身自证件已建，本票沿用既有替身并按规格回写差异（规格「与闸的挂钩表」现状列原注：「已实测全绿（该件 14 测；目录合计 45 测）」）。
- 实测核对（2026-10-15 本包起草时）：`pytest --collect-only`——`tests/runtimev2/` 目录合计 45 测、`test_gateway_adapter_fake.py` 计 14 测；规格「14 测」与实测一致，eng/04 §五旁注「替身自证 15」差 1（呈主窗勘误）。
- B7b 存量改写（按新规格行为 6 织可重试断言）的逐字转抄与改写义务落 `RT-W2-03a-gateway_adapter.md` 同节（指针，防两处真源漂移）——本票不动其断言、不重复转抄。
- L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。
- 本票织网义务＝① 既有替身自证件不因本票回退（`pytest tests/runtimev2` 合计 45 测全绿——2026-10-15 实测基线）；② 本票 6 行对应用例落网（行 11–13 由既有件看守，行 14–16 随 -03a 的新建件落网）；③ L2 新规格钉随施工 TDD 生长。

验收: 以下判据逐条全绿为过——
- 「票面对象」6 行逐行在场并全绿：11–13 行由既有件 `tests/runtimev2/test_gateway_adapter_fake.py` 看守（沿用既有替身，测试标识与规格列逐字一致）；14–16 行实现为 `tests/domains/test_v2_gateway_adapter.py` 用例（`#` 保留规格表行序 11–16，含【边界集】／【保留集】两行）；
- 「测试网钉」零 pin 行——本票只写归属指针，不重复转抄（3 行全在 -03a）；
- 既有替身自证件不因本票回退（`pytest tests/runtimev2` 合计 45 测全绿——2026-10-15 实测基线）；
- 形状单点：`ModelReply`／`complete`／冻结时钟常量／`ScriptedCompleter` 签名仍以 -03a 落地的为唯一真源，本票不改形状（改形状＝回 -03a 或回设计仓）；
- 边界闸 R5b／R6／R7＋V2 B6 契约在 `lint-imports` 双配置下绿（V1 6 KEPT／V2 18 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-03b 完成，产物 `appv2/runtimev2/gateway_adapter/`（替身面＋元面＋边界·保留集），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
