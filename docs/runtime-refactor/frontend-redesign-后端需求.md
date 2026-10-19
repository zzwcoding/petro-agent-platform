# 前端答案展示重设计 · 后端需求登记

> 2026-10-17 · 归属变更（Owner 拍板）：**未决后端条目全部挂账，归主窗 runtime 线解决**（登记真源＝`frontend-redesign-挂账清单.md` A1–A7，本文件为细节面）。
> 纪律：改动前后须过接口对账（见 `frontend-redesign-接口对账.md`）；前端按现状数据面降级设计，不因缺字段阻塞。

## P0 · 真机缺陷（2026-10-17 run-723b64c4 实机实证——问候「你好」零交付；挂账 A1/A2，归属主窗 runtime 线）

> 证据源：logs/llm_calls/20261017.jsonl:1986/1988/1990/1991、`GET /api/v2/chat/runs/run-723b64c4` step seq=2/13、curl 列表读口（answer:null）、appv2 源码 file:line 全链（挂账清单 A1/A2 互引）。

**缺陷 1A · 直答被闭世界误退＋退回文本错走 understanding 通道（understanding 层）**
- 现场：问候走 route=direct，文本自带示例枚举「抽油机时率」命中名录（`metric_roster`，`understanding/closure.py:70-87`）→ `_reject_direct`（`understanding/interpret.py:164-169`）退回 full。
- 退回文本升格 `Understanding(text=direct.text)`（`interpret.py:277`）并以 `kind='understanding'` 发帧（`interpret.py:320`）——**直答文本永远进不了答案面**，前端只能当旁白渲染。
- 自伤源：prompts 的直答示例本身列举名录指标名（自己命中自己）。
- 修复方向（任选/组合）：① closure 判据收窄为「含断言（数值/具体查询对象）才退回」；② 直答示例不列举具体名录名；③ 退回文本不用 understanding kind 发（发无 kind 正文帧进答案面）。

**缺陷 1B · 剥离误伤＋动作 JSON 回声链（answering 层）**
- 现场：作答相位模型回吐 `{"action":"finalize","answer":"你好！…"}`——因**澄清相位把前几轮动作 JSON 原话 append 进送模型对话链**（`clarification/core.py:175-183`），模型照抄回声。
- `strip_emission_fences` 按「整行裸 JSON」规则整行剥除（`answering/emission.py:93-98`，规则2/3 均咬中）——`answer` 字段里的正文一起删 → 空稿（step seq=13 failed「剥离后空稿」）→ 零 text 帧 → `state.answer=""` → 落库 `answer=NULL`（`orchestration/runtime.py:641`）。
- notice「已自动去掉，答案不受影响」（`answering/constants.py:121-123`）与实际相反——答案恰被剥没。
- 修复方向（组合）：① 剥离后空稿且原应答为 finalize 形时回退取 `answer` 字段；② 澄清相位不把动作 JSON 原话写进送模型链（只进过程档案）；③ 空稿收口文案改如实（不称「不受影响」）。

**运维事实（同次排查实证，挂账待办）**
- :8001 运行进程（PID 96998，15:28 起）载 BE-01 修复前代码 `fbe2e0b`——**重启即加载**（Owner 拍板暂缓，重启后内存历史行清空——进程用内存件，run 不落 PG）。
- **PG alembic 停在 0025**：0026/0027 未应用（`agent_v2_run` 无 supplements 列）——接线真件前必须 `alembic upgrade head`，否则列缺省/写入路径全断。

## P1 · 影响展示形态（有 workaround，有则更优）

> 2026-10-17 二次调研补强（刷新一致性专项）：**数据都已落库，缺的是 HTTP 读口，补读口＝暴露已有数据，非新增存储**。证据：`agent_v2_blackbox` 行含 20 白名单键（`observations`/`notices`/`answer`/`verdict`…，`appv2/runtimev2/persistence/models.py:58-87`）；`agent_v2_checkpoint` 含整个 RunState JSON（含 observations/notices，`persistence/checkpoint.py:57-59`）；`store.blackbox()` 读口已存在（`persistence/store.py:175-184`）只是无 API 挂。挂起态尚未写黑匣子（终态才写，`orchestration/runtime.py:470-486`），挂起还原走 `store.load().observations`。

1. **历史回读无 citations/materials 配对 + 无 notice 带 + 无 blackbox 统计行**（`appv2/api/chat.py:142-160,333-369`）
   - 现状：`GET /runs` 只有 `answer + supplements`；`GET /runs/{id}` 只有 `steps[].payload`（citations 只是序号数组、manifest 是整批材料数组，配不出 per-citation 的 source/source_id/trust/content）。刷新后看已完成对话时：正文✅、血缘/追加面文本✅（新 run）、**引用面板✅（2026-10-19 起由前端从 `supplements.citations`/`attribution` 回读——见下 workaround）**、notice 带❌、统计行❌。
   - 前端 workaround：**引用面已由前端自行回读补齐**（2026-10-19 打磨批⑨：`historyAdapter` 从 `supplements.citations`（`[n] 来源 · 出处编号（trust）`）与 `supplements.attribution`（`[n] 来源：观察正文`）两块文本投回 citations/materials——历史轮引用面板与正文 `[n]` 悬停卡与 live 同路）；notice 带仍如实隐藏、统计行只出核验计数（verify 步 payload 有）。**本条的剩余价值＝notice 带／blackbox 统计行 ＋ 单来源轮的逐条切片正文**（无 attribution 块时悬停卡正文走 E1 占位）。
   - 期望（本窗口后续施工——Owner 2026-10-17 拍板后端改动归本窗口；目标契约对账 D-4）：**读口区分旧行与无块新轮**——空列如实出 `[]`、`null` 仅旧行（`chat.py:218` 的 `[...] or None` 改为按列存在性判），或 `RunListItem` 加机读位。误标实证：真机 `eval/results/frames/EB3-NQ-C3.json`（completed／0 observation／无 supplement 帧的新 run）现状会被误标 legacy=true。施工排序：后端修复票（BE-01）须收在 FE-04 真接之前；前端 FE-02 按目标契约实现（null→legacy），不等待。挂起态取数注意黑匣子尚未写（见上）。
2. ~~无权威耗时字段~~ **已砍**（2026-10-17 Owner 拍板「耗时不需要」）：折叠条时长维持前端本地计时＋标注，后端不加 `duration_ms`。登记防复活。
3. **`citation.source_id` 无解析路径**（值形如 `f4`/`ensum-ec4b163075f1`）
   - 现状：Wekenora 式「点引标打开原文全文并定位高亮」做不了，只能定位到面板内切片卡。
   - 期望（Optional）：一个「source_id → 文档/切片详情」读口（哪怕只回切片原文+所在文档名），远期再谈位置锚点（source_locators 级）。
4. **running 期间无 blackbox 帧**（只在 run 终态发一次）——非缺口，前端统计行在收口前不渲染即可，登记防误报。

## 刷新一致性 · 已确认后端完备（前端欠账，勿报后端）

- **进行中刷新**：`POST /asks` 带 `resume_run_id` 重连＝全流帧逐字节重放（13 型全含，含 observation.payload.lineage）+ `follow` 尾随正在跑的 run（`api/bridge.py:89-181`）。浏览器断开不打断执行（detached task，`runtime.py:379-382`）。
- **无 `replay_truncated` 帧**：V2 永不发射（`specs/transport.md:103` 行为 13），那是 V1 遗产（`web/src/api/sse.js:31`）。重连失败＝开流前 HTTP 404（诚实拒），前端按「run 不可达/已过期」处理。
- **挂起刷新**：`pending_ask` 还原完备（`chat.py:350-353`）；resume 只出本腿新帧（cursor 语义，`chat.py:305-330`）。
- **前端欠账**：`web/src/api/chat.js:203-211` 的 `reconnectRun` 底座已备好，但 A1V2 页面未存 running run_id（sessionStorage 只存 rootId/followup，`A1V2.jsx:137,168-172`）、从未调用重连。重设计实施时必须接上：刷新后从 `GET /runs` 找 running run → 重连重放。

## P2 · 文案面（随 EB5/白话化批演进即可）

4. **notice 29 型 content 面混杂**：部分型仍是工序腔（`unsupported_claim`/`chain_switch_reentry` 等）。Owner 已拍板「等后端」——前端纯透传＋C 级默认收起，不硬编码白话摘要（设计稿 §6-3 已决）；全量白话化归主窗 EB5 批演进。
5. **supplement.lineage 块含工程腔**（`M-01 两步缝`/`actor=aqiang`/`D6 star_model`）：前端血缘卡先折叠兜底；长期希望补一版面向业务用户的白话五要素（或 payload 增补机读键）。

## P3 · 已确认非缺口（登记防误报）

- `supplement` 帧未消费＝**前端欠账**（reducer 无 case），后端通道完好。
- `observation.payload`（血缘五要素+limit）**已在帧里**，前端透传即可，无需后端动。
- tool 帧无入参/查询词：过程条白话标题可用 step.title 补齐，暂不强求。
- `runs` 列表重启后丢历史（跨进程注册表）＝后端自登记缺口，前端知悉即可。
