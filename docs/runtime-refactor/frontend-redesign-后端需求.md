# 前端答案展示重设计 · 后端需求登记

> 2026-10-17 · 归属变更（Owner 拍板）：**后端改动后续在本窗口自改**（不再走主窗收取）；P1-1 读口与 P1-3 定位面由本窗口后续开票施工。
> 纪律：改动前后须过接口对账（见 `docs/runtime-refactor/frontend-redesign-接口对账.md`）；前端一律按现状数据面降级设计，不因缺字段阻塞。

## P1 · 影响展示形态（有 workaround，有则更优）

> 2026-10-17 二次调研补强（刷新一致性专项）：**数据都已落库，缺的是 HTTP 读口，补读口＝暴露已有数据，非新增存储**。证据：`agent_v2_blackbox` 行含 20 白名单键（`observations`/`notices`/`answer`/`verdict`…，`appv2/runtimev2/persistence/models.py:58-87`）；`agent_v2_checkpoint` 含整个 RunState JSON（含 observations/notices，`persistence/checkpoint.py:57-59`）；`store.blackbox()` 读口已存在（`persistence/store.py:175-184`）只是无 API 挂。挂起态尚未写黑匣子（终态才写，`orchestration/runtime.py:470-486`），挂起还原走 `store.load().observations`。

1. **历史回读无 citations/materials 配对 + 无 notice 带 + 无 blackbox 统计行**（`appv2/api/chat.py:142-160,333-369`）
   - 现状：`GET /runs` 只有 `answer + supplements`；`GET /runs/{id}` 只有 `steps[].payload`（citations 只是序号数组、manifest 是整批材料数组，配不出 per-citation 的 source/source_id/trust/content）。刷新后看已完成对话时：正文✅、血缘/追加面文本✅（新 run）、**引用面板❌、notice 带❌、统计行❌**。
   - 前端 workaround：历史轮引用面板与 notice 带如实隐藏 + 灰字「历史记录无引用/提示明细」，统计行只出核验计数（verify 步 payload 有）。
   - 期望（Optional，按成本从低到高）：①新增 `GET /runs/{id}/blackbox`（直挂 `store.blackbox()`）；或 ②`RunView` 增加 `observations[]`（从 `store.load()` 投影）——任选其一即能让历史轮引用面板/notice 带复活。挂起态取数注意黑匣子尚未写（见上）。
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
