# 前端答案展示重设计 · 后端需求登记

> 2026-10-17 · 前端独立施工窗口登记，主窗口（runtime 重写线）定期收取。
> 纪律：只登记不代修；前端一律按现状数据面降级设计，不因缺字段阻塞。

## P1 · 影响展示形态（有 workaround，有则更优）

1. **历史回读无 citations/materials**（`GET /api/v2/chat/runs`，`appv2/api/chat.py:142-160`）
   - 现状：只有 `answer + supplements`。历史轮无法重建引用抽屉/引标交互。
   - 前端 workaround：历史轮仅渲染正文 + supplements，灰字标注「无引用明细」。
   - 期望（ Optional）：回读行带 `citations[]` 与 `materials[]`（或至少 citations），让历史轮引用可交互。
2. **无权威耗时字段**（blackbox/verdict/step 均无时间戳）
   - 现状：Kimi/WeKnora 式「思考 1m45s」只能前端本地计时，重连/续推段会漏。
   - 期望（Optional）：blackbox 帧或 verdict(final) 加 `duration_ms`（服务端计时）。
3. **`citation.source_id` 无解析路径**（值形如 `f4`/`ensum-ec4b163075f1`）
   - 现状：Wekenora 式「点引标打开原文全文并定位高亮」做不了，只能定位到抽屉内切片卡。
   - 期望（Optional）：一个「source_id → 文档/切片详情」读口（哪怕只回切片原文+所在文档名），远期再谈位置锚点（source_locators 级）。

## P2 · 文案面（随 EB5/白话化批演进即可）

4. **notice 29 型 content 面混杂**：部分型仍是工序腔（`unsupported_claim`/`chain_switch_reentry` 等）。前端计划按 type 做白话摘要模板 + 原文收起；若后端白话化全量覆盖，前端可退化为纯透传。需 Owner 裁决「前端硬编码映射表 vs 等后端覆盖」（见设计稿 §6-3）。
5. **supplement.lineage 块含工程腔**（`M-01 两步缝`/`actor=aqiang`/`D6 star_model`）：前端血缘卡先折叠兜底；长期希望补一版面向业务用户的白话五要素（或 payload 增补机读键）。

## P3 · 已确认非缺口（登记防误报）

- `supplement` 帧未消费＝**前端欠账**（reducer 无 case），后端通道完好。
- `observation.payload`（血缘五要素+limit）**已在帧里**，前端透传即可，无需后端动。
- tool 帧无入参/查询词：过程条白话标题可用 step.title 补齐，暂不强求。
- `runs` 列表重启后丢历史（跨进程注册表）＝后端自登记缺口，前端知悉即可。
