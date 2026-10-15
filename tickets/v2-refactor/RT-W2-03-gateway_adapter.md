# RT-W2-03 · gateway_adapter——V2 网关桥

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/gateway_adapter.md`（状态「已定稿」——前置满足）
Touches modules: `gateway_adapter`（本票只建 gateway_adapter 本体；规格「触及的模块」表另声明 bookkeeping／infra 两关联侧，归各自票承接）
波次: W2（`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W2 行：纯件层，只依赖 state/infra——本波出口判据「解析异常分支不静默；帧/游标单调；只追加可重放；模型出口唯一＋替身可注入」，本块承担「模型出口唯一＋替身可注入」半句；同 row 强调原文：「**gateway_adapter 的测试替身（fake）是后续所有相位测试的地基，必须最先可用**」）
施工队: B 队（eng/03 §五 终表 W2 行 B 队列＝「gateway_adapter」，分配理由整行原文「出口/计费/替身＝慢漏型缺陷，必须稳」；已按 eng/03 §五 终表对齐；提交前缀＝[B]——eng/03 §五 扣件①）｜复审强度: 100%（主窗裁：B 队施工≠免复审——本票维持 100% 过独立复审，复审网在 L0 直派；eng/03 §五 B 队标准为抽 50%，本票按主窗裁提高）
前置: ① 规格定稿（`specs/gateway_adapter.md` 已定稿——已满足）；② 波次前置：**W1 state 收波**（本包统一波次前置；注：eng/03 §一依赖图 gateway_adapter → infra，不依赖 state——波次归属按 eng/03 §二 W2 行不变，呈对账留痕）
阻塞: W1 state 收波（RT-W1-01，波次闸）｜被阻塞: RT-W3-01-bookkeeping（依赖图 bookkeeping → gateway_adapter）；W4 全部相位（替身是后续所有相位测试的地基）

## 任务

按 `specs/gateway_adapter.md` 新建 `appv2/runtimev2/gateway_adapter/`：模型调用的**唯一出口桥**——一次调用的入参面、回执面、限流重试与退避、测试替身、评测冻结时钟。**供应商与路由细节不出本块**，运行时各相位只能从这里出去。替身面沿用既有织网地基件（见「织网义务」）。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: `specs/gateway_adapter.md` 全文（十节版式）；`specs/modules.md` `## gateway_adapter` 卡（签名以卡为准）；`docs/runtime-refactor/recon/L3-网关与支撑小件.md`（Completer／calllog／eval_clock 段真源）；`appv2/infra/llm_client.py` 与 `appv2/tools/registry.py`（现状判据锚——「切备」与「重试」分层）；`appv2/runtime/llm.py`:47-49（重试 env 现状锚）；`appv2/runtimev2/gateway_adapter/fake.py` 与 `tests/runtimev2/test_gateway_adapter_fake.py`（既有替身与自证件）；`docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二／§五；`docs/runtime-refactor/eng/04-测试网设计.md` §三／§五；AGENTS.md 硬纪律 6b（逐字稿纪律）

框架红线: 无点名框架（本块不引入任何框架）——对应闸 R5b 契约
边界红线: ① 模型供应商唯一出口＝`infra`（`llm_client`／`gateway.complete`；B6）——本块是全工程**唯一允许**直引该出口的 runtimev2 块，对应闸 R7 契约（其 `source` 不含本块——例外面）＋ V2 B6 契约（`tools/importlinter_v2.toml`：`litellm` 唯一接触点＝`appv2.infra.llm_client`）；② 不直引引擎（R6）；③ 不引包内其它块（本块只依赖 `infra`——无专属闸→人审＋AST 断言「本块 import 只出现 infra」登记待补）；④ 禁手写替代（不自建 HTTP 客户端／供应商 SDK 直连——V2 B6 契约＋AST 断言「不出现 httpx／requests／裸 SDK」登记待补）

## 票面对象（specs/gateway_adapter.md「验收测试」表逐行转抄，16 行）

〔来源：specs/gateway_adapter.md「验收测试」表 :105–:120，逐行原文〕

| # | 验收标准（原文） | 对应测试（原文标识） |
|---|---|---|
| 1 | 唯一出口：模型调用点只在本块与 `bookkeeping.call_model` | `tests/domains/test_v2_gateway_adapter.py::single_model_egress` |
| 2 | 入参面固定三件、无自由 `params`（未知键报错） | `tests/domains/test_v2_gateway_adapter.py::params_face_fixed` |
| 3 | 回执十键恒在场；`cached_tokens` 未上报＝0（`pin-25`） | `tests/domains/test_v2_gateway_adapter.py::reply_all_keys_and_cached_zero` |
| 4 | `complete` 是协程 | `tests/domains/test_v2_gateway_adapter.py::complete_is_async` |
| 5 | 归因面逐调用保留（`caller`／`run_id` 可分组） | `tests/domains/test_v2_gateway_adapter.py::attribution_per_call` |
| 6 | 非限流失败一次即抛（不误伤）；限流失败重试到上限 | `tests/domains/test_v2_gateway_adapter.py::retry_only_on_retryable` |
| 7 | 分类判据不在本块另立 | `tests/domains/test_v2_gateway_adapter.py::no_second_classification_source` |
| 8 | 重试耗尽 fail-closed：原异常上抛＋失败留痕 | `tests/domains/test_v2_gateway_adapter.py::exhausted_fail_closed` |
| 9 | 冻结时钟四分支（缺省／`real`／ISO／非法）＋生产不读 env | `tests/domains/test_v2_gateway_adapter.py::frozen_clock_four_branches` |
| 10 | 用量实测与估算可区分（`usage_estimated`） | `tests/domains/test_v2_gateway_adapter.py::usage_estimated_flagged` |
| 11 | 替身与生产桥同面（签名＋回执形状） | `tests/runtimev2/test_gateway_adapter_fake.py::TestCardFace::test_complete_signature_matches_card` |
| 12 | 替身不静默兜底（无 default 抛错；有 default 照回且留痕） | `tests/runtimev2/test_gateway_adapter_fake.py::TestDefaultFallback::test_unscripted_without_default_fails_fast` |
| 13 | 替身观测面只读（注入剧本不被改写、留痕为调用时刻快照） | `tests/runtimev2/test_gateway_adapter_fake.py::TestObservationFaces::test_script_injection_readonly` |
| 14 | 本块零判断（AST 扫描） | `tests/domains/test_v2_gateway_adapter.py::no_judgement_in_gateway_adapter` |
| 15 | 【边界集】空 messages／超长 messages／限流失败／非法时钟值 → 各落对应分支 | `tests/domains/test_v2_gateway_adapter.py::boundary_empty_huge_ratelimit_clock` |
| 16 | 【保留集】常规成功调用的回执字段与归因行为不变 | `tests/domains/test_v2_gateway_adapter.py::retention_normal_call_unchanged` |

> 测试文件归属（spec :122 节尾原注照抄）：生产桥与时钟的验收测试绑**新建** `tests/domains/test_v2_gateway_adapter.py`（阶段 5 落地时建）；**替身面**（卡片面／兜底／观测面）已由织网地基件 `tests/runtimev2/test_gateway_adapter_fake.py` 实测看守——本批已按新接口面回写并**全绿（该件 14 测；`tests/runtimev2/` 目录合计 45 测全绿）**（该件由替身随规格同步维护）。

## 测试网钉（specs/gateway_adapter.md「与闸的挂钩表」pin 行逐行转抄，3 钉）

〔来源：specs/gateway_adapter.md「与闸的挂钩表」:150–:152，逐行原文〕

1. **pin-25（P1）**｜`cached_tokens` 未上报＝0（**回执面**）；「透传 calllog JSONL」的**落痕面**归 `infra`（`specs/infra.md` 侧）——**登记待补**，本块不冒充覆盖｜测试 `::reply_all_keys_and_cached_zero`｜现状：待织网（阶段 5）
2. **pin-27（P0，时钟面）**｜冻结时钟：缺省冻结日＋`real` 须显式（时钟面；「帧 `frozen_date`」半面不属本块）｜测试 `::frozen_clock_four_branches`｜现状：待织网（阶段 5）
3. **pin-28（P1，调用盖章面）**｜每次调用 `run_id` 盖章、计费可对账——**落盘面挂 `specs/persistence.md`、全盖章面挂 `specs/agent-loop.md`**｜测试 `::attribution_per_call`｜现状：待织网（阶段 5）

## 施工要点（specs/gateway_adapter.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/gateway_adapter.md:80 | 行为 1 唯一出口＋桥接单点 | 运行时所有模型调用经本块 `complete`；发起方＝`bookkeeping.call_model`（向节点只回 `content`，用量与归因面交 bookkeeping 记账进 Manifest） |
| specs/gateway_adapter.md:81 | 行为 2 入参面固定三件 | `messages`／`caller`／`run_id` 三件（+`self`）；无自由 `params`，传未知键报错 |
| specs/gateway_adapter.md:82 | 行为 3 回执面恒全键 | `ModelReply` 十字段恒在场；失败尝试 `error` 非 None、`content` 空串；`cached_tokens` 未上报＝0（钉 pin-25） |
| specs/gateway_adapter.md:83 | 行为 4 `async` 是硬要求 | `complete` 是协程；不得在事件循环内同步阻塞（`inspect.iscoroutinefunction`） |
| specs/gateway_adapter.md:84 | 行为 5 归因面逐调用保留 | `caller`（三桶族）与 `run_id` 逐调用交出口，不合并不覆盖；替身 `calls`／`counts()`／`messages_of()` 同口径 |
| specs/gateway_adapter.md:85 | 行为 6 重试只对可重试类 | 限流／超时／网络错／5xx 按配置重试退避（env 现状锚 `appv2/runtime/llm.py`:47-49；正式数值阶段 5 随真机定）；4xx 业务性拒绝不重试 |
| specs/gateway_adapter.md:86 | 行为 7 可重试性判据闭世界＋与「切备」分层 | 四类 `rate_limited`／`timeout`／`upstream_unavailable`／`rejected`——前两类可重试、后两类不重试；「切备」判据在 `infra`、「再试一次」判据在本块，两件事不许并成一句；类别映射单点函数只在本块出现一次 |
| specs/gateway_adapter.md:87 | 行为 8 重试耗尽 fail-closed | 耗尽或不可重试类→原异常上抛（失败尝试也留痕：最后回执 `error` 非 None）；收口归 `orchestration` |
| specs/gateway_adapter.md:88 | 行为 9 评测冻结时钟 | 未设/空串→缺省冻结日；`real`→当日真实日期（读 `infra.clock`，必须显式）；ISO→该日；非法→抛错；生产装配路径不读该环境变量（钉 pin-27 时钟面） |
| specs/gateway_adapter.md:89 | 行为 10 用时与用量如实 | `duration_ms`／token 实测；估算必须显式标注（`usage_estimated` 机读信号，不得恒定值） |
| specs/gateway_adapter.md:90 | 行为 11 替身与生产桥同面 | `ScriptedCompleter.complete` 与生产桥同形签名（替身 `run_id` 可缺省）与同一回执形状；离线零触网；观测面只读留痕 |
| specs/gateway_adapter.md:91 | 行为 12 替身不静默兜底 | 未剧本化 caller 且未设 `default`→当场抛错；设了 `default` 照回且调用照样留痕 |
| specs/gateway_adapter.md:92 | 行为 13 本块零判断 | 不读词表、不判语义、不做业务分支（只有「可重试／不可重试」结构分派；AST 扫描） |

结构锚：specs/gateway_adapter.md:32 接口定义（`ModelReply` 十字段——块级单一定义暂寄居 `fake.py`、阶段 5 迁至非替身模块禁双定义；`complete`／`EVAL_FROZEN_DATE_DEFAULT`／`EVAL_FROZEN_DATE_REAL`／`frozen_date`／`ScriptedCompleter` 签名）；:70–76 框架与依赖红线（R7 例外面＋V2 B6 契约＋两条人审降维面）；:94–99 不降级与静默禁令（合法降级路径＝无；失败必须留痕；估算必标注；冻结时钟不得静默回落真实钟）。

## 织网义务（eng/04-测试网设计.md §三 归本块行＋既有替身承接）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单〕

> | B7b | `tests/domains/test_v2_llm_429_retry.py:126-135` 旧钉断言网络错「一次即抛」——与新 gateway_adapter 规格行为 6「网络错可重试」**语义相抵**（复审⑦ V5） | 织网②改写：按新规格织可重试断言；重试次数/退避默认值以现状 env 面（`appv2/runtime/llm.py:47-49`）为现状锚、正式数值阶段 5 随真机定 | 高 |

- **沿用既有替身**（拆票 mapping 注）：eng/04 §五 step 1 原文照抄——「**钉地基**（对应 W2）：`gateway_adapter` 测试替身（ScriptedCompleter 等价物）＋ leg 格式回放 harness——没有这两件，后面全是沙上建塔。**✅ 已落成（2026-10-15，子代理施工＋主窗复验）**：`runtimev2/gateway_adapter/fake.py`（45 测中替身自证 15）＋ `tests/runtimev2/`（leg_replay 19 测／frozen_clock 8 测）；45 测全绿、18 契约 KEPT、ruff 净。挂账：替身接口按卡面同步实现、待 gateway_adapter 规格定稿回写（docstring 已登记）」——替身与替身自证件已建，本票沿用既有替身并按规格回写差异（规格「与闸的挂钩表」现状列原注：「已实测全绿（该件 14 测；目录合计 45 测）」）。
- 实测核对（2026-10-15 本包起草时）：`pytest --collect-only`——`tests/runtimev2/` 目录合计 45 测、`test_gateway_adapter_fake.py` 计 14 测；规格「14 测」与实测一致，eng/04 §五旁注「替身自证 15」差 1（呈主窗勘误）。
- B7b 改写义务落点：织网②存量改写（改写型义务，非新写盲区钉）——按新规格行为 6 织可重试断言。
- L2 新规格钉随本票施工 TDD 生长（eng/04 §五：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」16 行逐行在场并全绿：1–10／14–16 行实现为**新建** `tests/domains/test_v2_gateway_adapter.py` 用例；11–13 行由既有件 `tests/runtimev2/test_gateway_adapter_fake.py` 看守（沿用既有替身，测试标识与规格列逐字一致）；
- 「测试网钉」3 钉对应用例在场且绿（pin-27 为 P0 承重钉）；
- 既有替身自证件不因本票回退（`pytest tests/runtimev2` 合计 45 测全绿——2026-10-15 实测基线）；
- 边界闸 R5b／R6／R7＋V2 B6 契约在 `lint-imports` 双配置下绿（V1 6 KEPT／V2 18 KEPT 基线不红）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W2-03 完成，产物 `appv2/runtimev2/gateway_adapter/`，偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
