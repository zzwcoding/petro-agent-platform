# RT-W4-07a · verification——V2 核验（-A：骨架＋接口＋核心核验簇＋交付记账面）

状态: **草案（待主窗 manifest 对账后派工）** ｜ 所属规格: `specs/verification.md`（状态「已定稿」——前置满足）
Touches modules: `verification`（本票只建 verification 本体与核心核验簇；规格「触及的模块」表另声明 state／transport 两关联侧，归各自票承接）
波次: W4 —— `docs/runtime-refactor/eng/03-施工顺序与切换计划.md` §二 W4 行三列原文：块列「七个业务相位（understanding → clarification → tool_matching → preconditions → execution → answering → verification）」；理由列「互零依赖，**建议按业务链序施工**（便于走查 narrative 与测试网逐块加厚），不禁止并行」；出口判据列「每相位配属规格十节版式定稿＋新规格钉绿＋触及该相位的特征钉绿」
复审强度: 100%（eng/03 §五 流水 48 规则——本块在 §五 表 W4 行质量关键侧，该列分配理由整行原文「零 LLM 精度件＋P0 钉最重的交付面给 B」（该行 B 列三块＝`preconditions`／`answering`／`verification`）；§五 头注原文「**2026-10-16 更新：双队制废止**——改为单窗＋子代理 ≤3 并发、小票制，流水 48；下表 A/B 分配**降级为「复审强度规则」保留**：B 列六块＝质量关键块施工后 100% 复审，A 列抽 50%，交界归消费者验证」——故本票复审强度＝100%，复审网在 L0 直派、报告直送主窗）
前置: ① 规格定稿（`specs/verification.md` 已定稿——已满足）；② 波次前置：**W3 全收波**（eng/03 §一依赖图原文「verification → state」；本块另经 `transport` 公开面发 `verdict`／`notice` 帧——transport 归 W2，W3 全收即本块开工条件）；③ W4 硬前置＝本块触及的特征钉已钉好（eng/03 §四原文：「W4 每相位开工的硬前置＝该相位触及的特征钉已钉好」）
阻塞: W3 全收波（bookkeeping／context／gate 三票，票号以主窗 manifest 为准）｜被阻塞: `RT-W4-07b-verification.md`（同包顺序施工——-07b 前置＝-07a 收票）、W5 `orchestration`

## 任务

按 `specs/verification.md` 新建 `appv2/runtimev2/verification/`（现为 `__init__.py` 占位骨架）：答案交付前**逐句核对有没有材料撑着**——**纯程序、零模型**（防编造的机器底线）；没支撑的话**改写掉**，两来源对不上就**分开列**（`specs/verification.md`「目标」节原文）。

**本票＝verification 的 -A 票（骨架＋接口＋核心核验簇＋交付记账面＋本块全部 pin 行）**。拆分理由（小票制判据「票面对象 ≤15 验收行、先读清单 ≤6 份文件、聚焦一个行为簇」）：规格「验收测试」表共 **18 行**（`:93–:110`），超 15 行上限 → 切 -A／-B 两票。本票收 **11 行**＝规格表第 1–9、15、16 行（逐行核验／数值复述／无据改写＋notice／矛盾分列／归属审／`Verdict` 齐备／判据加严两行／零数值断言／机读信号在场／行集对账记账面）＋ **本块 6 条 pin 行全量**（pin-01／pin-02／pin-10／pin-11／pin-12／pin-03，逐字转抄见「测试网钉」节）；剩余 **7 行**＝规格表第 10–14、17、18 行（确定性／`RewriteRecord.reason` 闭世界／核验器抛错 fail-closed／零 LLM AST＋import 双证／零词表正则 AST／【边界集】／【保留集】）归 `RT-W4-07b-verification.md`（红线与健壮性簇＋边界·保留集）。两票同包**顺序施工**（同包不并行）：本票出骨架、公开面（三形状，含 `Verdict` 的行集对账两字段）与逐行核验主链，-07b 只填红线与健壮性行为簇、不另立第二套形状。

> 逐字稿载体（AGENTS.md 6b）：本票「票面对象」「测试网钉」「织网义务」三节的每一行均为所引规格／eng 文档表行**原文照抄**（无改写、无增删、无换述）；施工子代理对逐字稿只许照抄，偏离即停报 L0，不自行裁量。

先读: （6 份）`specs/verification.md` 全文（十节版式）；`specs/modules.md` `## verification` 卡（签名以卡为准——`verify(state) -> Verdict`）；`specs/answering.md`（`Gap` 口径三档闭世界＝本块复用物的真源；`verdict` 帧「批次落定归 `orchestration`」协调条款＝行为 10 的对面）；`specs/state.md`（`Verdict`／改写行／引用的状态形状面——本块只消费）；`specs/transport.md`（`verdict`／`notice` 帧发射面——只经其公开面）；`docs/runtime-refactor/recon/A2-核验规则与归属审.md`（核验规则与归属审真源——行为 2 的承载豁免字面 `agg_row`／`lineage`／`fragment` 见 R-A2-11、判据加严见 D-A2-10）。eng/04 §三 关联行与 eng/04a 六条钉已在本票「织网义务」「测试网钉」两节逐字转抄，施工期不必另开。

框架红线: **无点名框架**（本模块不引入任何框架、**不调模型**）——对应闸 R5b 契约（`tools/importlinter_v2.toml` :100–:105）
边界红线: ① **零 LLM 面**：本块**不调模型、不存在模型调用发起面**——不引 `appv2.runtimev2.gateway_adapter`（**R8** :119–:123，source 覆盖 `preconditions`／`verification`／`execution`）＋不直引 `appv2.infra.llm_client`（R7 :113–:117，本块天然满足）；② 不得直接 import `langgraph`／`langchain`——R5b（:100–:105）；③ 只经 `transport` 公开面发帧——「只经包根」半面由 R2 覆盖（:73–:78）；另一半「不自行拼 wire 帧」**无专属闸→人审**（规格「与闸的挂钩表」:133 行），本票不得降维自设闸（降维需新增验收行，本批未授权）；④ 七个业务相位互不 import——R1（:66–:71）；⑤ 不引旧 `appv2.runtime`——R5（:94–:98）；⑥ 不直引引擎——R6（:107–:111，本块天然满足）；⑦ **禁手写替代**：不得自建模型客户端、不得自建帧通路（对应闸 R8／R2）；⑧ 本票不实现 -07b 的红线面（两条 AST 断言）与【边界集】／【保留集】，也不改两票共用的三形状

## 票面对象（specs/verification.md「验收测试」表逐行转抄——本票 11 行：规格表第 1–9、15、16 行）

〔来源：specs/verification.md「验收测试」表 :93–:110（本票取自 :93–:101、:107–:108），逐行原文；`#` 列＝规格表行序，-07b 续用同一行序不重编〕

| # | 验收标准（原文） | 对应测试（原文标识） | 规格源行 |
|---|---|---|---|
| 1 | 逐行核验（多句答案逐句判定，非整段判） | `tests/domains/test_v2_verification.py::per_line_check` | specs/verification.md:93 |
| 2 | 数值未在断言里复述 → 判无据并改写 | `tests/domains/test_v2_verification.py::cited_value_must_be_restated` | specs/verification.md:94 |
| 3 | 无据句改写成「未找到」＋ notice 在场 | `tests/domains/test_v2_verification.py::unsupported_rewritten_with_notice` | specs/verification.md:95 |
| 4 | 矛盾来源分列、各带出处、不调和 | `tests/domains/test_v2_verification.py::conflict_split_not_merged` | specs/verification.md:96 |
| 5 | 归属对不上 → `attribution=False` ＋ 缺口 | `tests/domains/test_v2_verification.py::attribution_mismatch` | specs/verification.md:97 |
| 6 | `Verdict` 各字段齐备；缺字段判失败 | `tests/domains/test_v2_verification.py::verdict_all_keys` | specs/verification.md:98 |
| 7 | 边界记号化：`52` 不命中 `1520` | `tests/domains/test_v2_verification.py::token_boundary_no_substring_false_positive` | specs/verification.md:99 |
| 8 | 全角／半角标点先归一后切分 | `tests/domains/test_v2_verification.py::fullwidth_normalized_before_split` | specs/verification.md:100 |
| 9 | 零数值断言不自动判过 | `tests/domains/test_v2_verification.py::no_number_assertion_not_auto_pass` | specs/verification.md:101 |
| 15 | 机读信号在场（verdict／notice ＋ step payload） | `tests/domains/test_v2_verification.py::verification_signal_present` | specs/verification.md:107 |
| 16 | 行集对账：`delivered_rows`／`obs_rows` 入 `Verdict` 与 step payload；差额>0 且答案面无行集声明 → 补如实注记（不改写、不拦截） | `tests/domains/test_v2_verification.py::row_reconciliation_bookkeeping` | specs/verification.md:108 |

> 测试文件归属（规格 :112 节尾原注照抄，非本票改写）：「**测试文件归属（与既有 `tests/domains/test_v2_agent_verify.py` 的关系）**：本块验收测试绑**新建**的 `tests/domains/test_v2_verification.py`——`verification` 是 V2 十七块的新模块（`appv2/runtimev2/verification/`，公开接口 `verify(...) -> Verdict`），与既有 `test_v2_agent_verify.py`（现状 agent-loop 核验步：`verify_draft` 直测／表格·血缘卡·fragment 承载豁免现状行为）所测形状不同；故本块落新文件，既有文件继续覆盖现状核验步、本批不改。」
> 规格侧缺口登记（票注，呈主窗对账；只登记事实、**不自行增设验收行**——增设＝改规格，回设计仓）：
> ① **信号落地写口**——**已消化（流水 50）**：写口面＝`bookkeeping` 唯一写口，触及表 `specs/verification.md:28` 已列该写口行；行为 3（改写并发 `notice`）、行为 11（`delivered_rows`／`obs_rows`「随 step payload 落账」）与「不降级与静默禁令」（step payload 各字段）的信号落到 step payload，写入承接方＝该写口、相位禁直写（`RT-W3-01a/b/c-bookkeeping.md` 边界红线⑤）。
> ② **行为 11「补如实注记」的载体形状与写口**（走 `notice` 帧？走 step payload 键？规格未给形状）——登记事实。
> ③ **跨块待办（本块无验收行）**：风险 5「核验对增量引标」（承接真流式）＝规格自身已登记的跨块待办，随 `answering` 真流式协同定稿（真源 `walk/裁决表.md` §14-A）——本票不承接、不自设断言。
> ④ **「不自行拼 wire 帧」半面无专属闸**＝规格「与闸的挂钩表」:132 行原文已有的人审登记（另一半由 R2 覆盖），按原样引用、不降级自设闸。

## 测试网钉（specs/verification.md「与闸的挂钩表」pin 行逐行转抄——全块 6 行，全在本票）

〔来源：specs/verification.md「与闸的挂钩表」:137–:142，逐行原文；列名同规格「本规格的硬要求｜挂钩｜现状」〕

| 本规格的硬要求（原文） | 挂钩（原文） | 现状（原文） |
|---|---|---|
| 题眼锚定归属审（答案引用的报告≠题干点名报告即失败） | 钉 **`pin-01`**（落点＝行为 5 归属审 → `attribution=False` ＋缺口留痕） | 待织网（阶段 5） |
| 答案面禁现无据差值／无据口径框架（「252 天」型：全文零出现的数值不得充当答案） | 钉 **`pin-02`**（落点＝行为 2 数值须复述 ＋ 行为 3 无据改写） | 待织网（阶段 5） |
| citation 落账（引标对应窗内切片；不得 `cited=[]` 且数字在场） | 钉 **`pin-10`**（落点＝行为 8 零数值断言不恒过 ＋ `Verdict.cited`） | 待织网（阶段 5） |
| INV-1 前缀规则（「未找到（材料未披露）：」只挂无据行，行内有引标/观察对齐即放行，理想残余=0） | 钉 **`pin-11`**（落点＝行为 3 无据改写——前缀只随 `RewriteRecord.reason="no_material"` 落，有据行不粘前缀；真源 `eval/results/Q16-对账报告.md` §五 第 3 条（:59）＋ `tickets/v2/V2-54-核验辖域治理.md` 修法三层） | 待织网（阶段 5） |
| verify 对账机读字段（delivered_rows／obs_rows）入 step payload | 钉 **`pin-12`**（落点＝接口 `Verdict` 两字段 ＋ 行为 11 行集对账；真源 `arch/P7a-交接包与挂账清单.md` A-P7a-38） | 待织网（阶段 5） |
| 跨油田题交付分源列明油田归属（C-正6 形禁现） | 钉 **`pin-03`**（本块无独立落点——verify 侧仅行为 5 归属审触发面；答案交付面的分源列明属 prompts 合同「7 条③引用链承接」，prompts 规格落盘后承接，登记备查不落本块验收） | 待织网（阶段 5） |

- 分工注（票注，防双头）：pin-01 落点＝本票行 5；pin-02 落点＝行 2／行 3；pin-10 落点＝行 9（＋接口 `Verdict.cited`）；pin-11 落点＝行 3；pin-12 落点＝接口 `Verdict` 两字段 ＋ 行 16；pin-03 按规格本行自注「本块无独立落点……登记备查不落本块验收」**只登记不硬挂**（原文见上表末行）。**6 条 pin 行的机检用例全部落本票**——分布 6／0 是行为簇落点的产物（钉的落点行为全在核心核验簇与交付记账面）；`RT-W4-07b-verification.md` 零 pin 行、不重复转抄（同一 pin 行两处转抄＝两处真源必漂移，逐字稿纪律）。
- 归块佐证（票注）：① `docs/runtime-refactor/eng/04a-应钉行为清单.md:19`（pin-10 行）归属注记原文「**归属注记（主窗 2026-10-15 裁）**：行为落点＝verification（答案面判定），persistence 仅落盘对账面无独立钉（复审⑥核正，原映射「persistence←pin-10」作废）」——pin-10 落本块为现有裁决照抄；② pin-11 归本块亦经主窗核定（`docs/runtime-refactor/spec-review/verification-回工补写.md`「补充任务追加」节，真源照抄不改）。
- 规格「与闸的挂钩表」其余行（spec gate 两行、R8／R5b／R2 三条边界闸、零语义与判据加严两条 `测试 ::...` 行、末行人审）非 pin 行，按各自「挂钩」列由上述闸与用例承接，本票不转抄；**质量度量（精确率／召回率）行**（:136，织网义务行）照抄处＝本票「织网义务」节。

## 施工要点（specs/verification.md「行为约定」节骨架——file:line 锚＋一句话）

| 锚 | 条目 | 一句话 |
|---|---|---|
| specs/verification.md:71 | 行为 1 逐行断言级核验 | 先把答案剥掉结构性残留（JSON／引标记号）再**逐行**判定——**不是整段判** |
| specs/verification.md:72 | 行为 2 数值须复述＋承载豁免（钉 pin-02） | 被引观察里的数值须在断言文本里复述才算有支撑；**但 `agg_row`（表格行）／`lineage`（血缘卡）／`fragment` 承载形式下豁免「全数值复述」**——任一数值重叠即支撑、零重叠照改（carrier 字面真源＝`recon/A2` R-A2-11） |
| specs/verification.md:73 | 行为 3 无据 → 改写（钉 pin-02／pin-11 落点） | 无支撑句改写成「未找到／材料未披露」（`RewriteRecord.reason="no_material"`）并**发 `notice`**；INV-1 前缀只随该 reason 落、有据行不粘前缀 |
| specs/verification.md:74 | 行为 4 矛盾 → 分列 | 两源数对不上→**分开列、各带出处**（`reason="conflict"`）、不强调和、不取其一 |
| specs/verification.md:75 | 行为 5 归属审（钉 pin-01 落点） | 引用的材料与问句点名的对象对不上号→`attribution=False`，并把该情形写进缺口 |
| specs/verification.md:76 | 行为 6 给出核对结果卡 | `Verdict` **各字段齐备**（五计数 supported／rewritten／split／cited／attribution ＋ `ok`／`gaps` ＋ 行集对账 `delivered_rows`／`obs_rows`）——**缺键＝判失败** |
| specs/verification.md:77 | 行为 7 判据加严（治已知假阳／假阴） | 数值比对先做**边界记号化**（`52` 不得命中 `1520`）；**全角与半角标点先归一**再切分 |
| specs/verification.md:78 | 行为 8 零数值断言不恒过（钉 pin-10 落点） | 断言里没有任何数值时**不得自动判过**——仍须有可解析引标支撑，否则计入无据 |
| specs/verification.md:80 | 行为 10 `verdict` 帧批次落定 | 批次落定由 `orchestration` 协调；本块只保证自产部分（`Verdict`／`notice`）就位（承接＝`specs/agent-loop.md` 行为 11／`specs/answering.md` 行为 7——两处「只保证自产部分」说法与规格一致） |
| specs/verification.md:81 | 行为 11 行集对账（钉 pin-12 落点） | 在窗数据行数 vs 答案交付行数确定性对账，两字段**随 step payload 落账**；差额>0 且答案面无行集声明 → **补如实注记**；**不改写数值断言、不重试、不拦截**（真源 A-P7a-38） |

结构锚：specs/verification.md:32–:51 接口定义（`verify`／`Verdict` 九键／`RewriteRecord`（`reason` 闭世界 `no_material`｜`conflict`）／`Gap`（复用 `answering` 口径，字段＝`kind`／`subtask_id`／`reason`，核验侧产 `kind="unverified"`）；**错误契约**＝核验器自身抛错**不判 `Verdict.ok=True`**（fail-closed）——该行的验收用例属 -07b 行 12，本票只落地形状与 fail-closed 语义的形状面）；:61–:67 框架与依赖红线（零 LLM 面 R8／R5b／R2＋禁手写替代；「不自行拼 wire 帧」半面无专属闸→人审，见 :133 行）；:83–:87 不降级与静默禁令（**合法降级路径＝无**；改写／分列／归属失败必产机读信号：`verdict`／`notice` 事件〔类型取自 `synth/S6-事件与帧目录.md`〕＋ step payload 的 `supported`／`rewritten`／`split`／`cited`／`delivered_rows`／`obs_rows`；改写**不得静默**——红线原文 `arch/P7a-交接包与挂账清单.md`（A-P7a-37）「不许静默」）；:89–:110 验收测试表（`#` 行序与 -07b 共用）。规格「与闸的挂钩表」末行（**人审**）＝「不做什么」的纯范围排除无形状／存在性／退出码判据，不由本票自设闸。

## 织网义务（eng/04-测试网设计.md §三 关联行＋本规格挂钩表的织网义务行）

〔来源：eng/04-测试网设计.md §三 盲区补钉清单（本块无明写归块行，下列为逐字转抄的关联行）〕

> | B5 | 帧协议级时序（step/text/ask/verdict/done/error 序与 data 形） | 从 `eval/results/frames/` 真帧流转离线 golden 回放钉 | 中 |

〔来源：specs/verification.md「与闸的挂钩表」:136，逐行原文〕

> | 质量度量（精确率／召回率） | **测试网**（人工标注对照，非运行时闸） | 待织网（阶段 5） |

- 归块注（呈主窗对账）：eng/04 §三 表内**无一行明写「对应 runtimev2 `verification`」**（该表内唯一明写行为块名者是 B1→`bookkeeping`）。上引 B5 是**关联行**——其帧序里的 `verdict` 帧有 `verify`（核验裁决）与 `final`（收口）两形（形状真源 `synth/S6-事件与帧目录.md` §二），`verify` 形＝本块自产裁决帧、批次落定归 `orchestration`（规格行为 10）；钉法真源＝`eval/results/frames/` 真帧流转离线 golden 回放钉。
- 本块最大空白的织网面（规格挂钩表 :135 行原文照抄如上）：规格「依赖与风险」风险 1 原文——「**召回／误杀从未与人工标注度量过**（本块最大空白，Owner 裁决 Q-B「要补」）→ 对策：**用人工标注样本算核验的精确率／召回率**（拦错的 vs 放过的），**进测试网**（不是本块实现的运行时能力）；检测手段＝测试网的人工标注对照」——属**测试网义务、非本块运行时能力**。
- 关联行（已他归）：B1（公共位与结果归一：`_step_record`／`_next_seq`／`_converge` 等 16 个全节点共用符号）明写归 `bookkeeping`（`RT-W3-01a/b/c-bookkeeping.md` 承接）——本块只经 step payload 消费其记账面，不另立钉；B3（限额上限／触顶收敛）数值面归 `state`，非本块行。
- 本票织网义务＝① B5 关联行的 L3 回放钉（织网工序第 3 步「盲区补钉」，与 W1–W4 施工可并行——eng/04 头注）；② 质量度量的人工标注对照集（非运行时闸，落测试网）；③「测试网钉」6 行对应用例落网（pin-01／pin-02 为 P0 承重钉）；④ L2 新规格钉随本票施工 TDD 生长（eng/04 §五原文：「L2 新规格钉不入门——它随各块施工按 TDD 生长，是网的使用者不是织网判据」）。

验收: 以下判据逐条全绿为过——
- 「票面对象」11 行逐行实现为 `tests/domains/test_v2_verification.py` 用例并全绿，测试标识与规格列逐字一致（`#` 保留规格表行序 1–9、15、16；本票 11 行与 -07b 的 7 行同落同一新建文件）；
- 「测试网钉」6 行对应用例在场且绿（pin-01／pin-02 为 P0 承重钉——`eng/04a` 头注 P0 十三条含 pin-01／pin-02／pin-03／pin-10；pin-12 落点面＝行 16）；
- 骨架与公开面按卡面签名（`verify(state) -> Verdict`）＋三形状齐（规格 :32–:51：`Verdict` 九键／`RewriteRecord`／`Gap` 复用 `answering` 口径），两处闭世界（`RewriteRecord.reason`／`Gap.kind`）越界即判失败；
- 零模型：本块不引 `appv2.runtimev2.gateway_adapter`（R8）——本票验收面只核 import 契约，AST 双证用例（行 13／14）归 -07b；
- 边界闸 R1／R2／R5b／R6／R7／R8 在 `lint-imports` 双配置下绿（V2 侧 18 契约 KEPT 基线不红）；
- 「任务」节票注所列规格侧缺口登记**四项**已呈主窗（第①项＝信号落地写口**已消化（流水 50）**——写口面＝`bookkeeping` 唯一写口，触及表 `specs/verification.md:28` 已列；②③④ 未裁前相关行按规格原文落形状、不发明写口）；
- 回报附 pytest 全量输出与 lint-imports 输出原文。

回报: 完成后回主窗——「RT-W4-07a 完成，产物 `appv2/runtimev2/verification/`（骨架＋接口＋核心核验簇＋交付记账面），偏差: 有/无（有则逐条列），测试: pytest 摘要＋lint-imports 摘要」。对逐字稿任何一行偏离即停码停报 L0，不落实现。
