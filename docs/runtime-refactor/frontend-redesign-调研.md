# 前端答案展示重设计 · 调研（第一步产物）

> 2026-10-17 · 前端独立施工窗口 · 调研方式：三路线并行子代理（后端帧闭世界 / 前端现状 / Tencent WeKnora 源码），主窗汇总。
> 配套文档：设计稿 `frontend-redesign-设计.md`、后端需求 `frontend-redesign-后端需求.md`、窗口文案 `frontend-redesign-窗口文案.md`。

## 0. 一句话结论

后端「答案面瘦身」后，**正文通道已干净**（text 帧=纯模型回复 Markdown），**结构化通道已通但前端没接**：`supplement` 帧（分源/归属/引用清单/血缘四块）被 reducer 静默丢弃，`observation.payload`（结构化血缘五要素）被丢弃，`verdict`/`blackbox` 入了 state 无渲染位。历史回读只有 `answer + supplements`（无 citations/materials）。**前端展示的数据面是够的**，缺的不是数据而是归约与展示位；Wekenora 式「点引标打开原文全文定位高亮」**短期做不了**（无切片→原文位置锚点接口），hover 预览切片**可以做**（内容已在内存）。

## 1. 后端帧闭世界（13 值逐字段）

真源：`appv2/runtimev2/transport/frames.py:43-156`、`transport/constants.py:19-168`。信封恒三行 `id/event/data`；`id` = 全流单调游标（wire 三帧 session/done/error 不占号位）。

| 帧 | 关键字段 | 前端现状 | 说明 |
|---|---|---|---|
| `session` | `run_id`, `resume` | 已消费 | 开流首帧 |
| `step` | `seq`(int 步号), `step`(六相位), `title` | 已消费（右栏） | 无 status 键；live 态字段名 `station` 与历史态 `step` 不一致 |
| `text` | `content`, `kind?`(`"understanding"`=理解旁白，缺省=正文) | 已消费 | 正文唯一来源 |
| `tool` | `tool`, `status`(`ok/failed/ask`), `seq`, `message?` | 部分消费 | **reducer 丢弃 `seq`**；无入参/查询词/结果数/耗时 |
| `observation` | `index`, `source`, `content`, `trust`, **`payload?`** | 部分消费 | content 可能极长；**`payload.lineage`（血缘五要素键值对）+ `payload.limit{hit,rows}` 被丢弃** |
| `ask` | `frame{kind,prompt,options,detail}`, `run_id` | 已消费 | clarify / external_table_approval 两型 |
| `verdict` | verify 形 `{supported,rewritten,split,cited[],attribution}`；final 形 `{status,run_id,manifest_digest}` | **入 state 未渲染** | `cited[]`=被核验支撑的引标号集，可做引标可信度标注 |
| `citation` | `index`, `source`, `source_id`, `trust` | 已消费 | 与 observation 按 `index` 配对 |
| `notice` | `type`(29 值), `gates`, `content` | 已消费（单薄） | 见 §3 |
| `blackbox` | `run_id`,`question`,`status`,`error`,`stored`,`bytes`,`counts{messages,dialogue,process_notes,observations,steps}` | **入 state 未渲染** | 恰一帧/run；挂起腿不发 |
| **`supplement`** | **`block`(`split/attribution/citations/lineage`), `text`** | **零消费（静默丢弃）** | 发射于收口，citation 之后、verdict(final) 之前 |
| `done` / `error` | `run_id` / `{code,message}` | 已消费 | done 后仍可能有 ask（挂起判据=askFrame 在场） |

### supplement 四块 `text` 实样（真机）

- 载荷是 `{"block": ..., "text": "前导\n\n+ 块头行 + 逐行条目"}` 的**原始 markdown 串**，渲染前需 `strip()`。
- **`citations`**（152 次/全样本）：`引用：\n[1] 《A-W11井完井工程报告》 · f17（report）`——与 citation 帧同源，机读快照已有，文本块可视为兜底。
- **`attribution`**（139）：块头+`[n] {source}：{content}` 逐源归属行。
- **`split`**（19）：多来源不一致分列，**单条可极长**（整段报告原文 700+ 字，含全角空格表格）→ 必须限高/折叠。
- **`lineage`**（8）：无块头，直接五要素段：`① 口径 / ② 来源表 / ③ 过滤条件（含 └（权限注入）） / ④ 数据截至批次 / ⑤ 收口注记`；含工程腔（`M-01 两步缝`、`D6 star_model`、`actor=aqiang`）→ 面向业务用户需白话注解或折叠兜底。
- ⚠️ 块头字面随 EB4b 白话化**已演进过一次**，前端**只按 `block` 值分派，禁止硬匹配块头文本**。

### 真机时间线顺序（EB4-A-正1.json，按信封 id）

```
session → text(understanding) → notice → step×6 → tool(seq7) → observation×16
→ step(seq7) → text×6(正文) → step×2 → notice → verdict(verify) → step(verify)
→ citation×3 → supplement(citations) → step → verdict(final) → blackbox → done
```

要点：① 材料一次性到齐（答案前）→「引用了 N 篇」可早出；② tool(seq7) 先于其承载 step(seq7) 到达 → **排序按信封 id，归组才用 data.seq**。

## 2. 历史/轮询接口（实际实现，非任务书描述）

真源 `appv2/api/chat.py`：

- `GET /api/v2/chat/runs` → `[{run_id, question, status, answer|null, followup_of, created_at, updated_at, supplements|null}]`。**没有 citations、没有 materials**（任务书描述过时）。`supplements` 是 2026-10-17 新列，**全部历史 run 为 null**。
- `GET /api/v2/chat/runs/{id}` → `{status, steps[{seq,step,status,title,manifest,payload}], manifest_digest, pending_ask?}`。步级 `status/manifest/payload` 前端全丢。
- `POST /api/v2/chat/asks` / `runs/{id}/resume`：SSE，resume 只出本腿新帧。
- 旧轮（10-17 前）`answer` 内嵌旧式「引用：…」块文本；新轮 answer 纯净。前端要同时面对两种形态。
- 列表行集来自本进程 SSE 注册表，重启后历史不进列表（后端自登记缺口）。

## 3. notice 29 型分级建议

`gates` 实测恒空（不能当分级判据），分级只能按 `type`。content 面混杂：部分白话可见、部分内部工序腔（含英文参数/票据号）。

| 级 | type 值 | 展示 |
|---|---|---|
| A 醒目 | `refused` `run_failed` `freshness_block` `unbound_degrade` `schema_not_allowed` `material_truncated` `emission_strip` `blackbox_write_failed` `audit_write_failed` | 彩色 Alert |
| B 灰字/折叠 | `rebind` `window_note` `no_hit` `approval_recorded` `ban_exempt` `clarify_capped` `budget_converged` `window_miss_reentry` | 折叠条/灰条 |
| C 回喂面收起 | `decision_rejected` `same_param_replay` `emission_quote_repair` `decision_note` `chain_switch_reentry` `subtask_failed` `subtask_refused` `tool_unavailable` `unsupported_claim` `contradiction_split` `attribution_split` | 默认收起（工序腔），点开才见 |
| 兜底 | 未知 type | 通用灰条，**不静默丢弃**（闭世界会增补） |

> `unsupported_claim`/`contradiction_split`/`attribution_split` 虽归 C，但提示「核验删改/分列」的事实在答案可信度上有用户价值——建议给一句白话摘要（可由前端按 type 映射模板生成，见设计稿），原文收起。

## 4. 前端现状关键事实

- 布局：左 250px 对话列表 / 中 flex 对话流 / 右 330px 思考过程（决策树 Modal）。antd v5 暗色，无独立样式体系（内联 style + `index.css` 40 行）。
- reducer state：`{kind,question,runId,steps,tools,materials,notices,citations,understanding,answerText,verdicts,blackbox,askFrame,runStatus,closed}`。
- 引用抽屉：citation↔observation 按 index 配对已实现；无配对出「（材料未在回合内渲染）」如实占位；**历史轮不传 onCite，`[n]` 是死文本**。
- 加载态：只有发送按钮 loading + 空卡一颗 Spin，**无任何阶段叙述**。
- 测试基线 341 条全绿：landing 237（A1V2 21 / a1v2Reducer 17 / AnswerView 12）等。
- `trust` 四值原样显示英文，需白话映射：`authoritative→权威台账` `ledger→台账` `report→报告` `notice→系统注记`（`trust=notice` 的 citation 指向程序声明不是文档，抽屉不能按文档渲染）。

## 5. 数据面 → 展示意图映射表（第一步核心产出）

| 数据（帧/字段） | 展示什么 | 放哪 | 空态/降级 |
|---|---|---|---|
| `text`(正文) | 纯模型回复 Markdown | 中栏答案卡（AnswerView 保留） | completed 且无正文 → 显式占位「本次未产出答案正文」，不空卡 |
| `text`(understanding) | 「我理解为：…」 | 答案上方灰折叠条（思考素材） | 无 → 不渲染 |
| `step`+`tool` | 过程阶段叙述 | **答案上方过程折叠条**（Wekenora 同形）：折叠一行摘要，展开树状时间线 | 无 → 整行不渲染 |
| 材料数/引用数（observation/citation 计数） | 「检索完成 · 引用了 N 篇文档」 | 同上折叠条摘要 | N=0 → 退「N 步 · M 次工具」 |
| `citation`↔`observation` | 引用抽屉（增强：trust 白话徽标、分组、点击定位高亮） | 右 Drawer | 无配对不虚构（已有）；无引用 → 「本回合无引用」 |
| 引标 `[n]` hover | 切片内容预览 popover（**零请求**，内存直查 materials） | 正文内 antd Popover | 无对应材料 → 不弹 |
| `observation.payload.lineage` + `supplement(lineage)` | **血缘/查询口径卡**：「这数哪来的、怎么算的、更新到哪天」 | 答案卡下方独立折叠卡（或抽屉内） | 两者都无 → 不渲染（数据题才出） |
| `supplement(attribution/split/citations)` | **程序追加面**：多来源对照/分列/引用清单 | 次要位：折叠区，不抢正文 | 无 → 不渲染 |
| `notice{type,content}` | 三级分级带（§3） | 答案上方 | 无 → 不渲染 |
| `verdict(verify)` | 核验计数小徽标（有据 N 条·改写 M 条·分列 K 条） | 统计行 | 无 → 不渲染 |
| `verdict(final)`+`blackbox` | run 元数据小字「run-xxx · N 步 · N 材料 · 40 KB」（时长只能本地计时并标注） | 轮次卡底部 | 挂起腿无 blackbox → 不渲染 |
| 历史轮（GET /runs） | answer + supplements 可渲染；引用不可交互 | 同上新组件降级 | supplements=null → 「本轮为旧版记录，无引用/口径明细」；answer 内嵌旧块则原样渲染 |

## 6. 关键纪律（施工时遵守）

1. 时间线排序按**信封 id**（到达顺序），归组用 `data.seq`。
2. supplement 只按 `block` 值分派，**禁硬匹配块头文本**。
3. 未知 notice type / 未知帧一律通用兜底渲染，不静默丢弃。
4. 全部空态静默降级，不报错、不伪造。
5. 不动 `appv2/`、不动 V1 `A1.jsx`、不新建样式体系、antd 优先。
6. 沿用 lexer-only 免注入纪律（AnswerView 已立），引标交互用 React 事件冒泡委托。
