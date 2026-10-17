# 前端答案展示重设计 · 新窗口交接文案（Owner 2026-10-17 定）

> 用法：把下面整段贴进新窗口的第一条消息。新窗口只做**前端**，后端已就绪。

---

你在 petro-agent-platform 仓（`/Users/divh/Downloads/petro-agent-platform`）执行**前端答案展示重设计**。你是施工窗口，后端已定型不动（守纪律：不许动 `appv2/`、`tests/`、后端任何文件；发现后端缺陷→记录报告，不代修）。

## 背景（三句话）

这是油田业务用户的检索问答系统（agent 平台）。后端刚完成"答案面瘦身"：用户看到的**答案正文=纯模型回复**（Markdown），程序生成的结构化数据（引用、血缘/查询口径、分源、截断披露、过程）全部走**结构化帧/接口**，不再混在正文里。前端任务=把这些数据**以友好方式展示**。

## 你的四步任务

### 1. 调研后端接口能给出什么数据（先调研后设计）
- SSE 流帧类型闭世界（13 值）：`session/step/text/tool/observation/ask/verdict/citation/notice/blackbox/supplement/done/error`；逐帧载荷定义在 `appv2/runtimev2/transport/frames.py`＋常量 `transport/constants.py`（NOTICE_TYPES 29 值、SUPPLEMENT_BLOCKS 四值 split/attribution/citations/lineage）。
- 关键帧：①`citation` `{index,source,source_id,trust}`；②`observation` `{index,source,content,trust}`（含血缘五要素/证据片段）；③`supplement`（新）`{block,text}`＝程序追加面（分源列明/跨源归属/引用清单/血缘卡全文）；④`notice` `{type,gates,content}` 29 型（refused/material_truncated/window_note/budget_converged…）；⑤`blackbox` run 元数据；⑥`verdict`（核验计数+final）。
- 轮询/历史：`GET /api/v2/chat/runs`（回读字段含 answer/citations/supplements/…）；`POST /api/v2/chat/asks`（SSE）；`POST /api/v2/chat/runs/{id}/resume`（澄清续答）。端点真源 `appv2/api/chat.py`。
- 真机帧样本：`eval/results/frames/EB3G2-L04-01.json` 等（`eval/results/frames/` 下 EB3*/EB3G*），`docs/runtime-refactor/ladder/` 各级 `.sse`。
- 产出：调研清单（数据面→展示意图映射表）。

### 2. 确定展示哪些数据、怎么展示（设计方案先出稿）
必须覆盖的展示位（现状在 `web/src/landing/A1V2.jsx`）：
- 答案正文（已有 `AnswerView.jsx`：marked lexer→React、正文 `[n]` 引标点击→引用抽屉高亮——保留可用）
- **引用抽屉**：citation↔observation 配对（现状已有，增强：点正文引标定位、无对应条目不虚构）
- **新增：血缘/查询口径卡**（supplement 的 lineage 块 + observation 血缘）——"这数哪来的、怎么算的、更新到哪天"，用户可展开
- **新增：程序追加面展示**（supplement 的 split/attribution/citations 块——多来源对照、引用清单）——放次要位置（折叠/侧栏），不抢正文
- **notice 带**：29 型分级（Alert/折叠/灰字）现状在 `A1V2.jsx NoticeRow`，按新增 supplement 帧适配
- **过程面板**（step/tool 右栏现状）＋ **blackbox**（现状归约器收了但没渲染位——补 run 元数据小字）
- 历史轮次（runs 回读）：无 citation/materials 数据的旧轮如何降级展示
产出：设计稿（每展示位：数据来自哪个帧/字段、UI 形态、空态处理），Owner 过目后动工。

### 3. 统一修改
按设计稿实现；antd 组件优先；不新建样式体系；不动 V1 面（`A1.jsx`）。

### 4. 验证
`web/` 下 `npm run test`＋`npm run build`＋`npm run lint` 全绿；新展示位各补至少一条 vitest；用 `eval/results/frames/` 真机帧做一轮 E2E 人工核对（答案+抽屉+血缘卡+追加面）。

## 现状速查
- `web/src/landing/a1v2Reducer.js`（帧归约）、`A1V2.jsx`（渲染）、`AnswerView.jsx`（Markdown+引标锚点，2026-10-17 EB2 新增）、`api/chatV2.js`（SSE）。
- 已装 `marked`（lexer-only 用法）。依赖仅 antd/react/zustand/dayjs。
- 教学轨原型真源在 teach 仓（本仓 web/ 是快照）——若设计要动信息架构，先与 Owner 对一遍是否需要同步 teach 原型。

## 纪律
每票一提交；发现后端数据缺口（该有字段没有）→ 记报告给主窗口，不伪造不硬编；术语展示用白话（注解锚：`docs/runtime-refactor/research/最佳实践-3a-白话化与受众适配.md` 第三节）。
