# W-AUX 审查拍 回报（T1 关票前独立审查）

> 作业方式：全程只读。审查对象＝`fix/w-aux-query-narrate` 顶端 `20d16ce`（父 `ce38179`，rev-list=2）合并态；主树在 master 未切分支未动文件（Owner 私产零触碰）。源码按 `git archive` 解包 `/tmp/waux-review` 隔离副本审读＋复跑；变异探针在第二隔离副本 `/tmp/waux-mut`（探后复原复绿）。帧合同判据＝teach 真源 `/Users/divh/Downloads/teach-petro-agent/specs/api/A1-问一问.md`（只读）。

## 产物

零代码产物（审查拍——只产本发现清单）。审查基线 SHA：

- 开发拍：`ce38179efac5f51efee3257aa0117fa442a2d1c8`
- 修复拍：`20d16cee3a7ff8cc4aaf62a240bb368f673d5f88`（分支顶端，审查以顶端合并态为准）

## 结论逐项（专查四节＋通用两节）

### 专查① 判型提示词（vs P1F-01 失败模式）——通过，附 1 建议

1. **「自然语言一律检索」已撤，误派空壳链有双层护栏**：撤除在场（`app/domains/chat/service.py:77-89`，负断言 `tests/domains/chat/test_chat_query_fallback_continue.py:109`＋`tests/domains/chat/test_chat_n5_shell_fallback.py:135`）。护栏一＝提示词保留「指标卡直出链/口径消歧链仅受理 @ 显式锚定」（service.py:87-88）；护栏二＝N5b 接线核验覆写回退原样在位（`service.py:1433-1451`——未注册链就地覆写「检索问答链」，ask/resume-clarify/resume-approval 三调用点 service.py:384-395/737-741/870-874 共用单源实现），LLM 即使误派 13 条未接线壳链也在分派前被覆写，N5b 帧 note 留痕＋B12 审计行不缺。复核结论：N5b 兜底完好。
2. **纯定义问法判据边界清晰**：「纯定义问法（什么是 X）即使命中台账也选检索问答链」与取值诉求词面枚举（多少/最高/最低/排名/对比）在提示词中直接可判（service.py:81-85）；确定性兜底面回归测试双例在位（LLM 不可用时数据型→六站、纯定义→检索，`test_chat_query_fallback_continue.py:117-138`）。LLM 面判型质量本身无法机判（固有限制）——见疑点 3。
3. **「命中＋取值诉求合判」与 P1F-02 旧纪律措辞审读——相容，措辞差即票面授权的行为变更本体**：新表述保留「台账命中只是装配材料信号」前半句（P1F-02 材料信号语义未丢），路由条件为合取（命中∧取值诉求），命中单独不派链——不是复活「台账命中选链」。与旧文「不构成选链依据」的差异只在一个「唯一」字（service.py:84-85「不构成选链唯一依据」）：严格读旧纪律下「命中作合取必要条件」也是新行为，但这正是 Owner 2026-10-05 批准撤 P1F-01 过渡约束所授权的分型路由本身，非暗渡。实证面缺口见疑点 3（eval 回归未跑）。

### 专查② 辅助检索数值保护——通过

1. **变异断言非空洞（真伪独立复核）**：`tests/domains/chat/test_chat_query_aux_narrate.py:219-238`——99999 确实进生成窗（桩片段 snippet）且断言其出现在旁注 notice（:231，证明变异路径真走到），再断言 answer 帧与 lineage 帧全文无 99999（:234-237）＋表格行与桩数据逐行全等（:238）。探针 A/B 注入验证断言有牙（见「变异验证独立复跑摘要」）。
2. **cN 引用 fail-closed**：伪造别名剥除＋warning 留痕（`app/domains/chat/chains.py:1482-1496`——未知 ref 剥除；fragment_id 在场时锚校验 `anchor_loader`→None 或 report 归属不匹配即剥）；`IndexHitFace.fragment_id` 为必填 str（`app/domains/chat/domain.py:339`）→ 辅助片段锚校验恒可达，无「fragment_id 缺失绕过锚检」漏洞；UNANCHORED_CITATION_NOTE 单源（domain.py:828）。探针 B 证实剥除断言有牙。
3. **提示词三约束逐条在位**：`chains.py:139-155` NARRATE_SYSTEM_PROMPT——①数值一律以表格为准（片段数值不采）②句末 [cN] 标注格式③不得虚构；user 模板（:147-154）三约束复述。直测 `test_chat_query_aux_narrate.py:138-143`。残余风险（解读文本自身不采片段数值仅提示词约束、无机判）＝fix 回报疑点 2 已登记归 M-06，不另立发现。

### 专查③ 降级接续帧序——通过，附 2 低级别发现

1. **三路接续混排对照 A1 帧合同合法**：帧序＝六站帧（N7.1…N7.6）→ info notice（已接续标注，`chains.py:1513`）→ 检索链帧（N17/S0…S7/GEN）→ token→citation→answer→done；全部帧取自 19 类在册集，node 键经全景树在册集断言（`test_chat_query_fallback_continue.py:246-285`）。token/citation 缓冲机制保证双重无果时零半截流外泄（`chains.py:1515-1539`，双重拒答测试三话术原样恢复）；接续链弹 P1F-06 改写澄清时 `_run_chain` 哨兵拦截即 return（`app/domains/chat/service.py:1483-1493`）——不会出现 clarify 与 answer 双终局帧（预裁决 3 的机制基础核实成立）。
2. **answer 恒最后**：三收场（直出表卡/接续成功/接续双重拒答）均 answer→done 收尾，answer 恰一次断言在位；血缘帧仅在出数路发出、0 行接续路无血缘帧（测试断言 :282）。
3. **标注如实性**：`DATA_CHAIN_FALLBACK_NOTE/NOTICE`（`app/domains/chat/domain.py:1229-1233`）「数据库口径未能出数…非权威数值」——N7.4a/N7.6 两路与事实相符；N7.1 路严格说库未查（未命中注册声明），「数据库口径未能出数」措辞宽于事实，但同帧 alert 精确说明「未命中注册指标声明——不冒充审定口径出数」，合并读如实——记发现 4（信息级）。

### 专查④ 合同帧形状——通过

1. **零新帧型**：旁注新增帧全为既有 citation/notice/node_line；与 A1 册 19 类帧集（L113-135）逐一对照无越集。notice 载荷恰 `{level, text}`（chains.py:189-190＝A1 帧 16）；citation 帧恰四键 `{ref, kind, label, locator}`（domain.py:1008-1015＝A1 帧 11）；节点键 N7.6/N17/S/GEN 全在全景树在册集（测试自持拷贝断言）。
2. **answer 载荷零新增键逐项复核**：answer kind=table 实发键集 {kind, columns, rows, source_note, citations, lineage} ⊆ A1 L153 冻结集 {title?, note?, columns[], rows[], source_note?, chart_suggestion?, citations?, tool_call?, lineage?}；`TABLE_ANSWER_KEYS`（`test_chat_query_aux_narrate.py:39-42`）与合同逐键同名，`set(answer.keys()) <= TABLE_ANSWER_KEYS`＋narrative/caption 负断言在位（:212-213）。解读段未挂 answer 任何既有键（note/source_note/chart_suggestion 语义绑死 A1 原义，未被挪用——裁决 C 的旁注帧方案恰避免了挪用）。
3. **notice 承载 LLM 生成内容的语义（登记级判定）**：A1 帧 16 合同语义＝「非终局提示：中置信标注、@ 锚定行、断线横幅话术」——承载 LLM 解读段属语义扩宽，A1 册变更记录（L297-309）**尚无对应注记**。判定：属「有主挂账」而非隐瞒违规——裁决 C 在票面/dev 回报停线判定 c 项「需 Owner 点头」→ 修复拍按出路 C 实现，四层登记在案（票面预裁决 4、dev 回报末节、fix 回报疑点 1、commit message），归属阶段 3 合同对齐批。风险敞口：阶段 3 落册前处于「实现已行、合同未记」状态，web 快照同步批（硬纪律 0 阶段初同步）需知悉此语义。不构成现行缺陷，阶段 3 补登时建议不止「解读槽位」一项（见发现 5）。

### 通用⑤ 修复增量（20d16ce）——通过

2 文件 +456/−5 逐块核过：`_aux_retrieval_fragments`（chains.py:1430-1449）确系复用 `deps.index_searcher_dual` 注入缝（S4 同缝 chains.py:285、低分带同款 :690——零新缝属实；merge 策略随 cfg.merge 与 `_relaxed_rescore` 同款）；`_narrate_table`（:1452-1497）经 `_complete`→`gateway.complete` 单点出口（chains.py:888-900，B6 面零旁路）；帧位次施工与回报一致（血缘帧 :1361 → aux 行 :1389 → citation :1396-1397 → warning :1398-1401 → notice :1402 → answer :1421-1427）。

### 通用⑥ 边界与回归——通过

1. **chat 域零越界**：两 commit 合计 7 文件全在 `app/domains/chat/`（3）＋`tests/domains/chat/`（4），master…分支 diff 同集合，无域外文件。
2. **caller 计费留痕**：CALLER_NARRATE="chat.query.narrate" 经 `_complete` 传 `caller=` 进 completer（chains.py:895）；断言在位（`test_chat_query_aux_narrate.py:162-173`——narrate 在场且全量 caller ⊆ {chat.intent.verdict, chat.query.narrate}）；接续路全部模型调用照既有 caller（retrieval/rerank/rewrite/fallback），零新 caller。零片段主路零模型调用断言在位（:130）。
3. **主树零写入声明**：审查全程主仓工作树零写入（未切分支/未 stash/未改文件）；pytest、两闸、lint、mypy、变异探针全部在 /tmp 隔离副本执行。

## 发现清单（每条带 file:line＋影响评级＋建议处置）

| # | 位置 | 发现 | 评级 | 建议处置 |
|---|---|---|---|---|
| 1 | `tests/domains/chat/test_chat_query_aux_narrate.py:314-315`＋`tests/domains/chat/test_chat_query_fallback_continue.py:257-258` | 帧序合同测试的「节点键全景树在册」断言只覆盖 node 帧键（`node_walk` 仅投影 FRAME_NODE，conftest.py:287-293），不覆盖 node_line 帧的 key——**独立变异探针 C（辅助检索行挂发明键 N7.9）11 例中 0 例拦截**。被审代码实际用 N7.6 在册键（chains.py:1390）无现行违规，但测试 docstring「旁注施工不发明新键」的保障面对 node_line 存在盲区 | 低（看守面缺口，非合同违规） | 两文件键集断言扩及 node_line 帧 key（events_by_name(events)["node_line"] 的 key 同样 ⊆ PANORAMA_KEYS）；或 L0 知悉断言覆盖面后挂账 M-06 |
| 2 | `app/domains/chat/chains.py:1488-1495` | `_narrate_table` fail-closed 的「失锚」半边无直测：新测试只覆盖未知别名（[c9]，test_chat_query_aux_narrate.py:240-255）；anchor_loader 返回 None（片段已删）与 report 归属不匹配两分支在 narrate 路无专测。GEN 同形逻辑有全测（test_chat_chains_unit.py:549-595），narrate 系复制未随测 | 低 | 随 M-06 补两例（锚不存在/归属他报告→剥除＋留痕），或确认 GEN 全测的同形复制可信后不补 |
| 3 | `app/domains/chat/chains.py:1386-1394` | 辅助检索发起先于生成可用性判断：先跑双路检索再进 `_narrate_table`（completer 未装配/生成失败时检索白跑）；且 N7.6 aux 行（「旁注解读材料」）在生成前发出，生成不可用时该行语义超前（召回真实发生但解读未产出，用户见行无果） | 低（资源＋行文准确性，非合同面） | completer 判空先行（`deps.completer is None` 时跳过 aux 块）或 aux 行文条件化；随 M-06 打磨批裁量 |
| 4 | `app/domains/chat/domain.py:1229` | N7.1 接续路答案前置标注「数据库口径未能出数」措辞宽于该路事实（未命中注册声明、库未执行查询）；同帧 alert 已精确说明，合并读如实 | 信息 | 阶段 3 合同对齐批文案微调可选（如「数据库口径未能出数（未命中可出数声明/闸拦停/零行）」）；不强制 |
| 5 | teach `A1-问一问.md:132`（帧 16）＋变更记录 L297-309 | notice 承载 LLM 解读段＝语义扩宽，A1 册侧尚无注记；同批未入册的还有：辅助检索 node_line 新文案（chains.py:1389-1393）、降级接续标注/接续 notice/双重拒答文案族（domain.py:1229-1233）、旁注 cN 不随 citation_format 改写（fix 偏差 2）。本仓四层登记齐全（票面预裁决 4＋dev/fix 回报＋commit），非隐瞒 | 信息（登记级判定＝有主挂账） | 阶段 3 合同对齐批补登时按本清单一次带全（不止「解读槽位」一项）；届时前端快照同步批需同步 notice 旁注渲染语义 |
| 6 | `app/domains/chat/chains.py:1440-1445` | cfg.merge=concat 时 `concat_merge` 按 fragment_id 不去重（domain.py:871-875，rrf_merge 才去重）——4 支辅助窗口可能被同片段双腿占位（最多折半）；系沿 S4/低分带同款合并策略的**既有链行为继承**，非本票引入，但小窗口放大了影响 | 低（继承性） | 记 M-06：concat 合并去重属检索链既有面统一问题，不随本票单独改（保持「同款」承诺） |

## 变异验证独立复跑摘要

全部探针在 `/tmp/waux-mut` 隔离副本（源码同 `20d16ce` 合并态），探后复原、复原后全量例复绿（11 passed）：

| 探针 | 注入变异 | 结果 |
|---|---|---|
| A | 解读段挂上表卡（`table = dict(table, note=narration)`——模拟「解读进 answer 载荷」缺陷类） | **拦截**：`test_mutation_fake_fragment_values_never_touch_table_or_lineage` 失败于 :234（99999 进 answer JSON）——变异断言有牙 |
| B | fail-closed 剥除失效（未知别名/失锚分支只计数不 `strip_ref`） | **拦截**：`test_hallucinated_ref_stripped_fail_closed` 失败（[c9] 残留 notice 文本）——fail-closed 断言有牙 |
| C | 辅助检索 node_line 挂发明键 N7.9（帧序合同变异） | **未拦截**（11 例全过）——即发现 1：键集在册断言不覆盖 node_line 帧 |

另：变异断言的「变异路径在场」半边独立核实——桩片段携 99999 确实进生成窗且出现在旁注 notice（test :231 断言），排除「假数值根本没进系统、断言空转」的假阳性形态。

## 独立复跑数字（附报）

| 项 | 结果 | 对照 |
|---|---|---|
| 全量 pytest 基线态（/tmp 副本，主仓 venv，无 TEST_DATABASE_URL） | **896 passed, 83 skipped**, 1 warning in 24.84s | ＝fix 回报数字，基线不跌（885+83→+11=修复拍新测试，skip 持平） |
| 全量 pytest PG 态（TEST_DATABASE_URL=postgresql+asyncpg://petro:petro@localhost:5433/petro，PG16@5433 实跑） | **954 passed, 4 skipped, 1 failed, 20 errors** | 1 failed＋20 errors 全在 `tests/infra/test_db_midplatform_pg.py`＋`tests/domains/wells/test_wells_contract_pg.py`；**master 快照同环境复跑同款 1 failed＋20 errors**——环境前置（midplatform 三账号未按 DEP-01 runbook 建号/未种子），与被审两 commit 零因果（chat 域零交集） |
| chat 域＋sem 0019 种子 PG 态单证 | **264 passed**（含 test_chat_query_store_pg.py＋test_sem_seed_0019_pg.py——dev 回报偏差 3 的 0019 降级话术经双重拒答回落实证绿） | —— |
| ruff check app tests migrations tools | All checks passed! | ＝回报 |
| mypy app | Success: no issues found in 76 source files | ＝回报 |
| lint-imports | Contracts: 5 kept, 0 broken. | ＝回报 |
| tools/contract_coverage.py check | 合同覆盖率闸绿：169 条合同端点双向对账通过 | ＝回报 |
| tools/debt_markers.py check | 债务标记闸绿：33 条盘点 | ＝回报 |

## 偏差

无（审查对象、基线数字与 dev/fix 两回报全部对上；PG 态失败经 master 对照定性为环境前置，非被审变更引入——不构成回报与 git 事实不符）。

## 疑点（待 L0 裁决，不动手）

1. 发现 1（node_line 键集断言盲区）修不修：修补属测试加强（非生产行为变更），可随 M-06 或由 L0 拍板随本票关票前顺手处理——现测试 docstring 声称的保障强于实际断言面，二者取一（补断言或弱化表述）。
2. 发现 2（narrate fail-closed 失锚半边无直测）与发现 3（检索先行/aux 行文超前）是否随 M-06 后续打磨批挂账。
3. 判型恢复（P1F-01 撤除）的实证面：eval 题册问数组（v2 17 题）未随本票跑——提示词行为变化建议 L0 安排一次 eval 回归（重点＝P1F-01 当年的「台账命中误派」负例语料在分型路由下是否仍守），作为关票后的观察项或阶段 3 前置。
4. 发现 5 的 A1 册补登范围（解读槽位＋notice 旁注用法＋接续标注文案族＋旁注 cN 呈现语义）——建议 L0 在阶段 3 合同对齐批拆票时把本清单发现 5 四项一并入票面清单，防漏。

## 零修复动作声明

零修复动作已执行：本审查全程未改任何仓内文件、未提交、未合并、未切分支；主仓工作树写入为零，全部审读/复跑/变异探针在 /tmp 隔离副本完成（探针副本探后复原复绿）。本回报为唯一产物。
