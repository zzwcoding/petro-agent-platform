# 前端答案展示重设计 · 前后端接口闭世界双向对账

> 2026-10-17 · 对账子代理（全新实例）· 对账对象：规格 `specs/frontend-redesign.md`「接口定义」节 TurnShape × 后端供给面（`appv2/runtimev2/transport`＋`appv2/api/chat.py`＋发射方）× 前端消费面（`web/src/api/*`＋`web/src/landing/*`）。
> 纪律：只读调研＋只写本文件；未改任何 spec／票／代码。真机帧证据一律用 jq／python 抽取（未整读大文件）。
> 本报告是后续**后端读口施工**（Owner 2026-10-17 拍板由本窗口自改）的前置件。

## 1. 总结论

| 向 | 对账单元 | 通过 | 差异／待处置 | 登记不消费（合法） |
|---|---|---|---|---|
| A 前端消费面 × 后端供给面（TurnShape 逐字段） | 34 字段 | 24 | 7 | 3（客户端派生，无供给需求） |
| B 后端供给面 × 前端消费面（13 帧型） | 13 帧 | 11 | 1（verdict final 形无专位） | 1（supplement——前端欠账，FE-01 已票） |
| B 端点逐字段（4 端点） | 29 字段 | 23 | 0 | 6（updated_at／RunView.status／steps[].status／steps[].manifest／manifest_digest／steps[].payload〔登记为 T3 消费面〕） |
| C 语义一致性抽查（七项） | 7 项 | 6 | 1（C5 重连底座路径） | — |
| D 合同册登记 | 现状 4 条端点＋新增读口要求 | 现状绿 | — | — |

**差异清单 10 条（§6）：未清零**——其中须**改前端** 7 条（D-2／D-3／D-5／D-6 尚未落在任何票内，须补票面或并入 FE 票；D-7／D-8／D-9 已由 FE-01 承载）、须**回改票面／底座** 1 条（D-1）、须**改后端**（本窗口后续施工）1 条（D-4）、**登记不消费／无消费方** 1 条（D-10）。无一条是「后端供给缺数据」——供给面在真机帧里逐条在场（唯一例外是历史回读的引用／notice 面，已登记 `frontend-redesign-后端需求.md` P1-1）。

机器闸现状（本报告实跑）：
- `python3 tools/contract_coverage.py check` → **绿**：`合同覆盖率闸绿：V1 173 条 ＋ V2 4 条端点双向对账通过。`
- 真机帧证据集：`eval/results/frames/` 2423 个文件；本报告做了全量扫描（帧型分布／块值分布／citation-observation 配对／notice 取值／tool 状态分布）＋关键文件逐帧 jq 抽取。

## 2. A 向逐字段表（TurnShape → 供给源 → 结论）

规格真源：`specs/frontend-redesign.md:34-60`（TurnShape 字段逐字）。「前端消费点」列给**当前已落地**代码；FE-01/02 规划的落点另注。

| # | TurnShape 字段 | 后端供给源（file:line） | 前端消费点（file:line） | 结论 |
|---|---|---|---|---|
| 1 | `kind` | 无（客户端定） | `web/src/landing/a1v2Reducer.js:22-25`（ask/resume/replay 入参） | 客户端派生，无供给需求 |
| 2 | `question` | 无（用户输入） | `web/src/landing/A1V2.jsx:327`；history 侧 `appv2/api/chat.py:155` | 客户端派生（history 行走读口 `question`）✓ |
| 3 | `runId` | `session` 帧 `run_id`：`appv2/api/chat.py:272,298,326` | `a1v2Reducer.js:56-58`；`A1V2.jsx:238-240` | ✓ 逐字一致 |
| 4 | `resumed` | `session` 帧 `resume`：同上 | `a1v2Reducer.js:58`；`A1V2.jsx:432` | ✓ |
| 5 | `phase` | 无（客户端派生：`specs/frontend-redesign.md:39-40`） | `redesign/ExecutionPipeline.jsx:113`、`redesign/events.js:170` | 客户端派生 |
| 6 | `steps[].seq` | `step` 帧 `seq`：`orchestration/graph.py:177-184` | `a1v2Reducer.js:60-66` | ✓ |
| 7 | `steps[].station` | `step` 帧 `step`（六值闭世界 `runtimev2/state/constants.py:13-22`） | `a1v2Reducer.js:62`（station←data.step） | ✓（含 history 分支，见 C3） |
| 8 | `steps[].title` | `step` 帧 `title` | `a1v2Reducer.js:64` | ✓ |
| 9 | `tools[].tool` | `tool` 帧 `tool`：`execution/core.py:1211-1219` | `a1v2Reducer.js:67-72` | ✓ |
| 10 | `tools[].status` | `tool` 帧 `status` ∈ `ok/failed/ask`：`execution/core.py:193-195` | `a1v2Reducer.js:70`；`ExecutionPipeline.jsx:36` | ✓（真机 2203 tool 帧：ok 1947／failed 213／ask 43，无越界值） |
| 11 | `tools[].seq` | `tool` 帧 `seq`：`execution/core.py:1216` | **现状丢弃**（`a1v2Reducer.js:67-72` 只取 tool/status/message） | **差异 D-7**（FE-01 G3 已票） |
| 12 | `tools[].message` | `tool` 帧 `message`（可为 `null`——真机 `EB4-数-明2.json` tool 帧 `message: null`） | `a1v2Reducer.js:71`（`?? ''` 兜底） | ✓（null→空串，空态纪律合规） |
| 13 | `materials[].index` | `observation` 帧 `index`（＝`observation.seq`）：`execution/core.py:1228-1238` | `a1v2Reducer.js:74-80`（按 index 原位 upsert） | ✓；与 citation.index 同轴（全量扫描 855 个带整型 index 的文件，**0 条 citation 无配对 observation**） |
| 14 | `materials[].source` | `observation` 帧 `source` | 同上 | ✓ |
| 15 | `materials[].trust` | `observation` 帧 `trust`（四值：`context/materials.py:28-30,56`） | 同上；白话映射 `redesign/cites.js:19-25` | ✓（见 C2） |
| 16 | `materials[].content` | `observation` 帧 `content` | 同上；`CiteHoverCard.jsx:38`、`CitationPanel.jsx:107` | ✓ |
| 17 | `materials[].payload` | `observation` 帧 `payload`（**条件在场**：`locator.payload` 为映射才挂键）：`execution/core.py:1228-1237` | **现状丢弃**（`a1v2Reducer.js:74-80` 未取 payload） | **差异 D-8**（FE-01 G2 已票） |
| 18 | `materials[].payload.lineage` | `locator.payload.lineage`（键名单点 `appv2/tools/schema.py:70`） | `redesign/LineageCard.jsx:70-73`（消费，但入参来自顶层键——**差异 D-5**） | 供给在场 ✓／接线口径差异 |
| 19 | `materials[].payload.limit{hit,rows}` | `locator.payload.limit`（`appv2/tools/schema.py:71-73`） | `LineageCard.jsx:105-109`（同上入参问题） | 供给在场 ✓（真机 `{hit:true,rows:50}`）／接线口径差异 D-5 |
| 20 | `notices[].type` | `notice` 帧 `type`（29 值闭世界 `transport/constants.py:70-103`） | `a1v2Reducer.js:90-95`；分级 `redesign/events.js:54-79` | ✓（`approval_gate_pending` 落未知兜底——见 D-10） |
| 21 | `notices[].gates` | `notice` 帧 `gates`（真机实测恒 `[]`） | `a1v2Reducer.js:93` | ✓ |
| 22 | `notices[].content` | `notice` 帧 `content` | `redesign/NoticeBand.jsx:41-68` | ✓ |
| 23 | `citations[]{index,source,source_id,trust}` | `citation` 帧四键：`answering/core.py:607-614`（发射点 `:379`） | `a1v2Reducer.js:82-88`；面板 `CitationPanel.jsx:80-97` | ✓ |
| 24 | `understanding` | `text` 帧 `kind:'understanding'`：`understanding/interpret.py:291` | `a1v2Reducer.js:104-105` | ✓ |
| 25 | `answerText` | 其余 `text` 帧 `content`（起草段＋直答旁路补发 `orchestration/graph.py:528-549`） | `a1v2Reducer.js:107`；`AnswerView.jsx` | ✓ |
| 26 | `events` | 帧到达序（客户端保序：`api/chat.js:49-71,131-147`） | `ExecutionPipeline.jsx:51-102`（消费 `ev.phase／ev.count／ev.notice／ev.verdict／ev.cite`） | **差异 D-3**（元素形状未定义；FE-01 定帧名形、FE-02 让组件直吃） |
| 27 | `verdicts`（verify 形） | `verdict` 帧（verify）：`verification/core.py:582-589` | `a1v2Reducer.js:110-112`；`RunMetaLine.jsx:27-33` | ✓ |
| 28 | `verdictFinal`（final 形） | `verdict` 帧（final）：`orchestration/runtime.py:458-465` | **无字段落地**（reducer 不分子型，全进 `verdicts`） | **差异 D-6** |
| 29 | `blackbox` | `blackbox` 帧：`orchestration/runtime.py:485` | `a1v2Reducer.js:113-114`；`RunMetaLine.jsx:36-40` | ✓ |
| 30 | `askFrame` | `ask` 帧 `frame{kind,prompt,options,detail}`：`orchestration/graph.py:246` | `a1v2Reducer.js:97-99`；挂起卡 `A1V2.jsx:448-466` | ✓（`kind` 二值 `transport/constants.py:113`） |
| 31 | `runStatus` | 客户端派生（G5；值域真源 `runtimev2/state/constants.py:25-31`） | `a1v2Reducer.js:99,121-123,127` | ✓（见 C1） |
| 32 | `closed` | 派生自 done/error/transport（`api/chat.js:140-157`＋`api/sse.js:90-105`） | `a1v2Reducer.js:117,126` | ✓（**但 error 帧载荷无位**——差异 D-2） |
| 33 | `supplements{4 槽}` | `supplement` 帧 `{block,text}`：`orchestration/graph.py:212-221`（块值闭世界 `transport/constants.py:49-60`） | **零消费**（`a1v2Reducer.js:55-131` 无 `supplement` case） | **差异 D-9**（FE-01 G1 已票；后端需求 P3 已登记为前端欠账） |
| 34 | `legacy` | `RunListItem.supplements` 为 `null`：`appv2/api/chat.py:160,218` | `A1V2R.jsx:104-108`（灰字） | **差异 D-4**（判据与后端列语义不对齐） |

### A 向读口源字段（history 形）

| 字段 | 供给（file:line） | 消费（file:line） | 结论 |
|---|---|---|---|
| `RunListItem.run_id/question/status/answer/followup_of/created_at` | `chat.py:153-159` | `A1V2.jsx:109-135`（buildThreads）、`:526`（answer）、`ThreadList.jsx:55-113` | ✓ |
| `RunListItem.supplements` | `chat.py:160,218` | FE-02 historyAdapter（H2/H4）；现状仅 mock | ✓ 供给；判据问题见 D-4 |
| `RunListItem.updated_at` | `chat.py:159` | **无消费方** | D-10 登记 |
| `RunView.steps[]{seq,step,title}` | `chat.py:117-126,357-367` | `A1V2.jsx:638-642`；FE-02 H2 | ✓ |
| `RunView.steps[]{status,manifest,payload}` | 同上 | 现状无消费；`payload` 为设计 §7 的 T3 登记消费面（`frontend-redesign-设计.md:132`） | D-10 登记 |
| `RunView.status`／`manifest_digest` | `chat.py:136-139,354-368` | **无消费方**（列表侧用 `RunListItem.status`） | D-10 登记 |
| `RunView.pending_ask` | `chat.py:139,351-355` | `A1V2.jsx:276,304-307`；FE-03 R4 | ✓ |

## 3. B 向逐帧／逐端点消费矩阵

### 3.1 十三帧闭世界（`transport/constants.py:19-42`＝`EVENT_KINDS` 10 ＋ `WIRE_FRAMES` 3）

| 帧 | 发射点（file:line） | 前端消费路径（file:line） | 消费结论 |
|---|---|---|---|
| `session` | `api/chat.py:272,298,326`（桥 `bridge.py:163-164`） | `api/chat.js:139-140`→`a1v2Reducer.js:56-58`；页面锚 `A1V2.jsx:238-240` | 全消费 |
| `step` | `orchestration/graph.py:171-184` | `a1v2Reducer.js:60-66`→`ExecutionPipeline.jsx:60-66`／`A1V2.jsx:653-657` | 全消费 |
| `tool` | `execution/core.py:1211-1219` | `a1v2Reducer.js:67-72`→`ExecutionPipeline.jsx:67-77`／`A1V2.jsx:658-662` | 消费（`seq` 待 FE-01 补，D-7） |
| `observation` | `execution/core.py:1228-1238` | `a1v2Reducer.js:74-80`→`CitationPanel.jsx:52`／`ExecutionPipeline.jsx:78-84` | 消费（`payload` 待 FE-01 补，D-8） |
| `ask` | `orchestration/graph.py:246`（`_suspend` `:237-248`） | `a1v2Reducer.js:97-99`→`A1V2.jsx:448-466`／`renderSuspendCard:483-513` | 全消费 |
| `verdict`（verify） | `verification/core.py:582-589` | `a1v2Reducer.js:110-112`→`RunMetaLine.jsx:27-33`／`events.js:157-158` | 全消费 |
| `verdict`（final） | `orchestration/runtime.py:458-465` | 仅被并入 `verdicts`（无 subtype 判据），页面不取 | **部分消费**（D-6） |
| `citation` | `answering/core.py:379`（载荷 `:607-614`） | `a1v2Reducer.js:82-88`→`CitationPanel`／`CiteHoverCard`／`ExecutionPipeline.jsx:94-99` | 全消费 |
| `notice` | `verification/core.py:597`、`orchestration/graph.py:199-208`、`runtime.py:477-484` | `a1v2Reducer.js:90-95`→`NoticeBand.jsx:41-68,73-` | 全消费（未知 type 走兜底，E3） |
| `blackbox` | `orchestration/runtime.py:485` | `a1v2Reducer.js:113-114`→`RunMetaLine.jsx:36-40` | 全消费 |
| `supplement` | `orchestration/graph.py:212-221` | **无路径**（reducer 无 case，默认分支静默忽略） | **登记不消费**（D-9；理由：前端欠账，非后端缺数据——后端需求 `:34` 已登记） |
| `text` | `answering` 起草段／`understanding/interpret.py:291`／`graph.py:528-549` | `a1v2Reducer.js:101-108`→`AnswerView.jsx` | 全消费 |
| `done` | `bridge.py:175` | `api/chat.js:142`（onDone）＋`a1v2Reducer.js:116-124`（closed='done'＋runStatus 三分） | 全消费（`data.run_id` 无消费方——D-10） |
| `error` | `bridge.py:168-173`（`code='chat_stream_failed'` `errors.py:40`／话术 `bridge.py:51`） | `api/chat.js:143`（onError）＋`a1v2Reducer.js:125-128`（closed='error'） | 消费；**载荷无显示位**（D-2） |

> 前端残留：`REPLAY_TRUNCATED` 保留帧（`web/src/api/sse.js:31`、`api/chat.js:140-144`）在 V2 闭世界**不存在**（`EVENT_KINDS ∪ WIRE_FRAMES` 十三值中无此名）——**死分支**，无害；已由 `frontend-redesign-后端需求.md:23` 登记「V2 永不发射」。

### 3.2 端点逐字段（响应／入参字段 → 消费方）

| 端点 | 字段 | 消费方（file:line） | 结论 |
|---|---|---|---|
| `POST /api/v2/chat/asks`（入参） | `question` | `chatV2.js:25` | ✓ |
| | `resume_run_id` | `chatV2.js:26` | ✓（重连路径底座问题见 D-1） |
| | `followup_run_id` | `chatV2.js:27`；`A1V2.jsx:336` | ✓ |
| | `Last-Event-ID` 头 | `api/chat.js:103` | ✓ |
| （响应） | `session{run_id,resume}` | `a1v2Reducer.js:56-58` | ✓ |
| `POST /runs/{id}/resume`（入参） | `kind`／`choice`／`decision`／`approval_id` | `chatV2.js:43-50`；装配 `chatV2.js:60-69` | ✓（逐字见 C5） |
| `GET /runs` | `run_id` | `A1V2.jsx:110-122`；`ThreadList.jsx:60-113` | ✓ |
| | `question` | `A1V2.jsx:131`；`ThreadList.jsx:61` | ✓ |
| | `status` | `ThreadList.jsx:28,112`；`A1V2.jsx:88-96,573` | ✓ |
| | `answer` | `A1V2.jsx:526`；FE-02 H2 | ✓ |
| | `followup_of` | `A1V2.jsx:116-118` | ✓ |
| | `created_at` | `A1V2.jsx:101`；`ThreadList.jsx:112` | ✓ |
| | `updated_at` | **无** | D-10 登记 |
| | `supplements` | FE-02（H2/H4）；现状 mock | ✓ 供给 |
| | `limit` 夹取 1..100 | `ThreadList.jsx:49,56,63-66`；`chatV2.js:85-86` | ✓（C6） |
| `GET /runs/{id}` | `status` | **无**（列表行 status 代用） | D-10 登记 |
| | `steps[].seq/step/title` | `A1V2.jsx:638-642`；FE-02 H2 | ✓ |
| | `steps[].status/manifest/payload` | 现状无；`payload` 为 T3 登记面（设计 `:132`） | D-10 登记 |
| | `manifest_digest` | **无** | D-10 登记 |
| | `pending_ask` | `A1V2.jsx:276,304-307` | ✓ |

## 4. C 向七项语义核对逐项结论

**C1 runStatus 四值：逐字一致 ✓**
后端 `appv2/runtimev2/state/constants.py:25-31`＝`running/waiting_ask/completed/failed`（闭世界 `RUN_STATUS_KINDS`，写入口径由 persistence 状态机把守）。前端归约产出同一四值：`a1v2Reducer.js:38`（初值 running）、`:99`（ask→waiting_ask）、`:121-123`（done 三分：waiting_ask/failed/completed）、`:127`（error→failed）。词表两处同键集：`ThreadList.jsx:28`、`A1V2.jsx:88-90`。

**C2 trust 四值：逐字一致 ✓**
后端 `authoritative/ledger/report/notice`：`context/materials.py:28-30`（前三值）＋`:56`（`"notice"→"notice"`，notice 名义入表、材料段排除）。前端 `redesign/cites.js:19-25`（TRUST_TEXT 四键，未知值原样回显）；消费点 `CiteHoverCard.jsx:22,28`、`CitationPanel.jsx:80-87`。真机 `trust='notice'` 现身（如 `EB3-数-降1.json` 的「检索供给窗声明」citation）。

**C3 step 帧 live 态 `station` vs 历史态 `step`：两分支都对得上 ✓**
- live：`step` 帧键集 `{step,seq,title}`（`orchestration/graph.py:177-184`，真机逐帧验证）→ reducer `station ← data.step`（`a1v2Reducer.js:62`）；六相位值 `state/constants.py:13-22`，前端白话表 `events.js:30-37` 六键同名。
- history：`RunView.steps[].step` 直出 `state.steps[].step`（`chat.py:121,360`）→ FE-02 H2「station←step、title 原样」；现页右栏直接渲染 `s.step`（`A1V2.jsx:641`）。
- 形状不对称（非缺陷，登记）：live 帧**无** `status` 键，history `StepView` **有** `status/manifest/payload`（`chat.py:118-126`）；TurnShape 只声明三键，多出的键归一后被丢（D-10）。

**C4 supplement 四值：逐字一致 ✓（现状零消费）**
后端闭世界 `transport/constants.py:49-60`＝`split/attribution/citations/lineage`；构造期越界即抛（`frames.py:89-105`）。真机全量扫描 supplement 帧 399 条：块值分布 `citations 190／attribution 168／split 25／lineage 16`——**无越界第五值**。前端**无第二份块型字面**（`web/src` 内无硬编码 block 名单），mock 四槽键 `mockTurns.js:1223-1296` 与闭世界同名；分派实现待 FE-01 G1。

**C5 resume 语义：逐字一致 ✓，但重连底座路径不一致 ✗（D-1）**

| 参数 | 前端（file:line） | 后端（file:line） | 结论 |
|---|---|---|---|
| `resume_run_id` | `api/chatV2.js:26` | `api/chat.py:104`（`AskBody`） | ✓ 同名同义 |
| `Last-Event-ID` | `api/chat.js:103`（值＝最后收到帧的 `id`，`:138`） | `api/chat.py:230`（`Header(alias="Last-Event-ID")`）＋`parse_last_event_id:58-82`（`cursor=id+1`；负游标 400） | ✓（排他起点语义一致） |
| `kind` | `chatV2.js:43-50`（`clarify`｜`approval` 二值，`:43` 守卫） | `chat.py:111`（`Literal["clarify","approval"]`）→ 映射 `chat.py:54-55,169-186`（`approval`→`external_table_approval`） | ✓ |
| `choice` | `chatV2.js:48` | `chat.py:112,170-177`（clarify 必填，空＝400） | ✓ |
| `decision` | `chatV2.js:49`（`approve`｜`reject`） | `chat.py:113,178-183` | ✓ |
| `approval_id` | `chatV2.js:50`（驼峰 `approvalId` → 上线映射 snake，`:57-59` 注记） | `chat.py:114,185` | ✓ |
| 装配器 | `resumeBodyFromAskFrame`（`chatV2.js:60-69`）：`external_table_approval`→`kind:'approval'`＋decision，`detail.approval_id` 取单号 | 真机 `detail.approval_id="precond-s1"`（`V2-53-数-察2.json`） | ✓ |

**✗ 不一致项（唯一）**：FE-03 票面把重连底座指到 `web/src/api/chat.js:203-211` 的 `reconnectRun`，该函数打的是 **`/chat/asks`**（`chat.js:205`）＋`API_BASE='/api'`（`client.js:28`）＋ vite 代理 `/api → :8000`（`web/vite.config.js:20-22`）＝**V1 端点**；而 V2 重连真源是 `POST /api/v2/chat/asks`（`chat.py:260-276`），代理 `/api/v2 → :8001`（`vite.config.js:16-19`），正确底座＝`chatV2.postAskV2({resumeRunId}, handlers, {lastEventId})`（`chatV2.js:21-32`，`opts` 可透 `lastEventId`）。V1 侧 `replay_preflight` 读 `chat_run/chat_message`（`app/domains/chat/service.py:1159-1169`），V2 run 不在该表 → **V2 run 走 V1 重连恒 404**（详见 D-1）。

**C6 `GET /runs` limit 夹取与前端默认值：一致 ✓**
后端 `wanted = max(1, min(limit, 100))`（`chat.py:208`，越界**静默夹取不 400**——只读面宽容，docstring `:195`）。前端：`listRunsV2(limit=20)` 缺省 20（`chatV2.js:85`）、V2 现页调用 `listRunsV2(20)`（`A1V2.jsx:194`）、ThreadList `pageStep=20／maxRows=100`（`ThreadList.jsx:49`）＋`atEarliest = limit >= maxRows`（`:56`）＋`loadMore` 不越上限（`:63-66`）＋到顶出「已到最早」（`:88`）。规格 L1（`specs/frontend-redesign.md:105`）与两端同形。

**C7 错误契约：对得上 ✓（error 帧话术无显示位——D-2）**
- SSE 内异常：`{code:'chat_stream_failed', message:'本次回答中断——请重新提问'}`（帧载荷定形恰二键 `frames.py:77-86`；装配 `bridge.py:51,168-173`；真机旧批次同形 `{"code":"chat_stream_failed","message":"流内异常——请重新提问"}` 9 例）→ 前端 `chat.js:143 onError(f.data)` ＋ `sse.js:95-97` 同语义 ＋ reducer `:125-128` → 页面 errMsg（`A1V2.jsx:255-258`）。
- HTTP 404：run 不存在（`chat.py:263-267,344-349`；映射 `errors.py:88-93`＋persistence 侧同族兜底 `:102-109`，码 `chat_run_not_found`）→ `streamChat` 非 2xx 抛 `ApiError(status)`（`chat.js:117-121`）；`getRunV2/listRunsV2` 同（`chatV2.js:76-81,89-93`）。**R3 灰条依赖的正是「开流前 404 抛出而非 onTransportError」**——本层语义成立（`streamChat` 对非 2xx 走 throw，对读流中断才走 onTransportError `:149-157`）。
- HTTP 409：resume 非挂起（`errors.py:95-100`＋persistence 侧 `:111-118`）／`resume_run_id` 与 `followup_run_id` 同在场（`chat.py:244-259`，含 `detail.conflict`）→ ApiError(409) 可判。

## 5. D 向合同册登记现状与新增读口的登记要求

**现状（本报告实跑证据）**
- V2 端点清单＝`config/runtimev2_endpoints.json:5-34`：4 条（E1 `GET /api/v2/chat/runs`／E2 `POST /api/v2/chat/asks`／E3 `POST /api/v2/chat/runs/{}/resume`／E4 `GET /api/v2/chat/runs/{}`），每条带 owner 注记。
- 闸扫描实读＝4 条，与清单**逐条对齐**：`parse_implemented(appv2/api)` → `[('GET','/api/v2/chat/runs'), ('GET','/api/v2/chat/runs/{}'), ('POST','/api/v2/chat/asks'), ('POST','/api/v2/chat/runs/{}/resume')]`（静态扫面 `tools/contract_coverage.py:70-80`＋`V2_API_DIR:35`）。
- 闸判定：`reconcile` 双向（实现有/清单无＝红 `:104-105`；清单有/实现无且空 owner＝红 `:106-111`）`tools/contract_coverage.py:96-112`；CLI `check()` 同源（`:115-126`）；pytest 看守 `tests/tools/test_contract_coverage.py`；CI 挂 `.github/workflows/ci.yml:28`。本报告实跑：**绿**（V1 173 ＋ V2 4）。
- 注意一：**V2 清单是手写冻结基线，`export` 只重生成 V1 清单**（`tools/contract_coverage.py:26-30`「V2 无仓外合同册真源」＋`export()` 只写 `MANIFEST_PATH`，`:129-150`，写盘点 `:146`）→ V2 新增端点**必须手改** `config/runtimev2_endpoints.json`，不能指望重跑 export。
- 注意二：闸的扫描面只认 `APIRouter(prefix=...)` ＋ `@router.<method>("...")`（`:74-75` 两条正则，遍历 `appv2/api/*.py`）——经 `app.add_api_route`／`app.get` 旁路新增的路由**扫不到**（不触发红灯，但也不被登记看守）。

**若后续新增读口（如 `GET /runs/{id}/blackbox`），登记要求**
1. 路由实现：`appv2/api/chat.py` 内 `@router.get("/runs/{run_id}/blackbox")`（router 前缀 `/api/v2/chat`，`chat.py:50`）→ 归一为 `/api/v2/chat/runs/{}/blackbox`。
2. **必须同批在 `config/runtimev2_endpoints.json` 增一行**（`book:"V2"`／`no` 顺延（现最大 E4→`E5`）／`method:"GET"`／`path:"/api/v2/chat/runs/{}/blackbox"`／`owner` 写票号或挂账行）。否则闸红「实现有/清单无」（`:104-105`）。该路径与 E4 `/api/v2/chat/runs/{}` 归一后不同串，不冲突。
3. 若改走**扩 `RunView`**（增 `observations[]` 等）而非新端点：**无新路由＝闸不涉及**（端点闸只对端点存在性敏感，DTO 形状漂移明文归测试面——`tools/contract_coverage.py:14-15` 注）；但仍须在 `frontend-redesign-后端需求.md` P1-1 处更新登记（前端适配据此）。
4. 合同册侧义务：V2 面无 teach 仓合同册真源（同上 `:26-30`），**不产生「合同册复述」义务**；AGENTS.md 硬纪律 1 的 teach 合同册引用只约束 V1 面。故 V2 读口新增＝「清单登记＋owner 注记」两件。
5. 若同时**新增前端消费面**（如 history 轮 notice 带），须同步改 `specs/frontend-redesign.md` 的 H2／E4 行（现文写「恒为空」——`specs/frontend-redesign.md:86,95`）；属改 spec，不在本报告范围。

## 6. 差异清单（10 条：描述＋影响＋建议处置）

| # | 差异 | 影响 | 建议处置 |
|---|---|---|---|
| **D-1** | **重连底座打 V1 端点**：FE-03 票面（`tickets/frontend/FE-03-重连线.md:13,21,41`）指定 `web/src/api/chat.js:203-211` 的 `reconnectRun`，其 path 为 `/chat/asks`（`chat.js:205`）＋`API_BASE='/api'`（`client.js:28`）→ vite 代理到 **:8000（V1）**（`web/vite.config.js:20-22`）；V2 重连须 `POST /api/v2/chat/asks`（`chat.py:260-276`，代理 `/api/v2 → :8001` `vite.config.js:16-19`） | V1 `replay_preflight` 读 `chat_run/chat_message`（`app/domains/chat/service.py:1159-1169`），V2 run 不在其中 → **重连恒 404** → R2「全帧重放归一＋尾随新帧」永不成立，R3 灰条「本轮已结束或不可达」被误常显（把可重连的 run 判成不可达）；FE-03 的用户故事整条落空 | **改前端／回改票面**：FE-03 改用 `postAskV2({resumeRunId}, handlers, {lastEventId})`（`chatV2.js:21-32`，`opts.lastEventId` 可透）；`chat.js::reconnectRun` 归 V1 专用，票面「任务/先读/施工要点」三处引用同步改（**开工前先改票面，勿照旧施工**） |
| **D-2** | **SSE `error` 帧 `{code,message}` 在 TurnShape 无安放位**：`closed` 只有 `done/error/transport/null`（`specs/frontend-redesign.md:56`）；reducer `case 'error'` 只置 `closed/runStatus`（`a1v2Reducer.js:125-128`），`message` 丢弃；现页靠侧路 `errMsg`（`A1V2.jsx:255-258`） | 流内异常／服务端稳定话术（`bridge.py:51`）在新页**无法上屏**；E 组空态纪律未覆盖 error 文案位；与 R3 前端自造灰条文案可能双标 | **改前端＋spec 补键**：TurnShape 增 `error: {code,message}\|null`（或组件 props 增 onError 直呈），`specs/frontend-redesign.md` 接口定义节补该键；无后端改动 |
| **D-3** | **`events` 元素形状未定义**：spec 只写 `{ type: string, ... }[]`（`specs/frontend-redesign.md:50`）；FE-01 定为「帧到达序追加的 typed 事件」（帧名形），而 `ExecutionPipeline.jsx:63,81,86,90,97` 消费 `ev.phase／ev.count／ev.notice／ev.verdict／ev.cite`，`events.js:116-161` 现产的正是**派生显示型**（`materials/verify/citation` 三型非帧名，`materials` 更是计数聚合） | FE-02 退役 `deriveEvents` 后组件直吃 `turn.events`：step 行丢 `phase`（`phaseText(undefined)`）、verify／citation／materials 行全落 `ev-unknown` JSON 兜底（`ExecutionPipeline.jsx:100-101`）——流水线肉眼可读性崩 | **改前端＋spec 补键**：FE-01 与 FE-02 之间定死元素形状（帧名形＋归一层派生键，或显示型＋映射单点），并回写 spec「接口定义」节；无后端改动 |
| **D-4** | **H4 `legacy` 判据与后端空列语义不对齐**：读口把空列折成 `null`（`chat.py:218` 的 `[...] or None`）；`RunRecord.supplements` 缺省空列表（`persistence/models.py:133`）、旧行／非列表读成 `[]`（`persistence/store.py:277-282`）；空文本块零入列（`answering/core.py:210-220`） | **新轮误标旧版**：真机 `eval/results/frames/EB3-NQ-C3.json` 是一个 completed、0 observation、无 supplement 帧的**新** run——其列 `[]` → 读口 `null` → H4 `legacy=true` → 渲染「本轮为旧版记录，无引用/口径明细」并触发 E4 隐藏位（在有数据可显的轮上假降级） | **改后端（本窗口后续施工）**：读口区分「旧行」与「无块新轮」——如空列如实出 `[]`（前端改判 `null` 才 legacy），或 `RunListItem` 增机读位（`legacy`／`supplements_version`／`has_supplements`）；前端按新判据改；登记点：`frontend-redesign-后端需求.md` P1-1 追加一条 |
| **D-5** | **TurnShape 无顶层 `lineage/limit`，而展示件吃顶层键**：spec 把血缘放在 `materials[].payload.{lineage,limit}`（`specs/frontend-redesign.md:44`）；`A1V2R.jsx:100,154` 传 `turn.lineage/turn.limit`（mock 顶层造键 `mockTurns.js:1298-1309`），`LineageCard.jsx:70`／`CitationPanel.jsx:39` 同吃顶层 | 接真流时若无人从 `materials[].payload` 取值，血缘卡恒空 → 走 E2「不渲染」，把「有数据」当「非数据题」（静默降级成信息损失） | **改前端**：FE-05／A1V2R 增加从 `materials[].payload` 的选择（或 TurnShape 明示派生字段来源）；spec 接口定义节可补一句「payload 唯一源，展示层自行取首支在场者」；无后端改动 |
| **D-6** | **`verdictFinal` 无落地**：spec 声明 `verdictFinal: object\|null`（`specs/frontend-redesign.md:52`）；reducer 把**全部** verdict 帧推入 `verdicts`（`a1v2Reducer.js:110-112`），不判 `subtype`（注入点 `frames.py:141-146`）；FE-01 票面「TurnShape 字段全集」列举未点名 `verdictFinal` | final 形载荷（`{status,run_id,manifest_digest}`，`runtime.py:458-465`）无消费位；`RunMetaLine` 取 `verdicts[0]` 恰为 verify 是**靠帧序**而非显式判据（帧序若变则徽标错读 final 形） | **改前端**：FE-01 补 `verdictFinal`（或 spec 删该键），`RunMetaLine` 改按 `subtype==='verify'` 取；无后端改动 |
| **D-7** | `tool` 帧 `seq` 现状被丢（`a1v2Reducer.js:67-72`），供给在场（`execution/core.py:1216`；真机 `{"tool":"data_query","status":"ok","seq":8,"message":null}`） | 流水线「工具挂到同 seq 步下」的归组与事件挂步失去轴 | **已登记需求**：FE-01 G3（`tickets/frontend/FE-01-归约层扩面.md` 任务 3）——按票施工即清零 |
| **D-8** | `observation.payload` 现状被丢（`a1v2Reducer.js:74-80`），供给在场且条件挂键（`execution/core.py:1228-1237`；真机 43193 条 observation 中 49 条带 payload） | 血缘卡首选源（结构化五要素）与 `limit.hit` 截断披露全丢，只剩 `supplement(lineage)` 文本兜底 | **已登记需求**：FE-01 G2——按票施工即清零（后端需求 `:35` 已明示「已在帧里，无需后端动」） |
| **D-9** | `supplement` 帧零消费（reducer 无 case） | 分源／归属／引用清单／血缘四块文本在 live 轮全丢（`AnswerView` 正文也不含这些块——`answering/core.py:369-378` 正文只留模型稿） | **已登记需求**：FE-01 G1（票面任务 1）；后端需求 P3 记为「前端欠账」（`frontend-redesign-后端需求.md:34`）——后端零改动 |
| **D-10** | **供给有／消费无（登记不消费，非缺陷）**：`RunListItem.updated_at`（`chat.py:159`）、`RunView.status`（`:137`）、`RunView.manifest_digest`（`:368`）、`RunView.steps[].status/manifest`（`:121-126`）、`steps[].payload`（登记为 T3 半血形态消费面，设计 `:132`）、`done` 帧 `data.run_id`（`bridge.py:175`）、`notice.approval_gate_pending`（29 值之一未入前端 A/B/C 表 → 落未知兜底，符合 E3 `NoticeBand.jsx:60-66`） | 无功能影响；风险是「登记位被当缺口误报」或「T3 半血形态漏实现」 | **登记**：本清单即登记面；FE-05 的 T3 走查清单建议点名 `steps[].payload` 还原工具名／状态一件；`approval_gate_pending` 若需专门文案，归后端 EB5 白话批 |

### 附：本报告对既有表述的更正

- `docs/runtime-refactor/frontend-redesign-调研.md:17` 写「step 无 status 键」——**只在 live 帧成立**；`RunView.steps[]` 有 `status`（`chat.py:120`）。
- 同文 `:52` 写「supplements 全部历史 run 为 null」——**读口语义成立，但不区分「旧行」与「新轮无块」**（D-4 根因）。
- 其余引用件（`frontend-redesign-设计.md`／`frontend-redesign-窗口文案.md`）与本次对账无冲突，无更正。
