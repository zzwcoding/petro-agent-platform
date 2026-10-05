# R-WIRE 接线预备对账 回报 —— E2/A2/B4 三页逐字段接线差异清单（阶段 2 收官·批 3/3）

> **证据非权威，待 L0 综合与 Owner 确认。** 本报告为只读盘点产物，全部行号实测于主仓
> HEAD＝`398ba20`（工作树净，含 5a6027e UI 系归档提交；三页最后触碰＝3c2d63a P2-05 快照同步）。
> 合同真源：teach-petro-agent/specs/api/E2-数据质量台.md v0.5 / A2-井档案.md v0.2 /
> B4-报告百科.md v0.4。**零改动红线兑现：主仓除本报告文件外零写入**（文末声明）。
> 树结构前提：三页现居原型树（#/proto/X，Shell.jsx:16-21 懒加载 pages/）——接线落地＝
> landing/ 新建 <KEY>.jsx＋registry.js LANDING_MODULES 注册（registry.js:12-20 先例），
> 下文「接线」均指落地树新建＋原型页随收官退役。

---

## 产物

本报告文件一件；零代码/零配置改动。

## 闸门实跑（web 三连，HEAD 398ba20）

```
npx eslint .        → ✖ 2 problems (0 errors, 2 warnings)
  （存量两条：pages/D3.jsx:96 hooks exhaustive-deps / pages/INDEX.jsx:85 hooks——
    P2-05 提交语已登记「既有 warning：D3/INDEX hooks 提示，非本批文件」，与现测一致）
npx vitest run      → Test Files 12 passed (12) · Tests 210 passed (210) · 13.99s
npx vite build      → ✓ built in 4.12s
```

结论：**master 5a6027e 基线三连全绿**（vitest 210 例 vs P2-05 时点 208 例——其后批次新增，
非三页影响）。

---

## 一、E2 质检台（pages/E2.jsx ＋ api/e2.js mock）× 真后端九端点（app/api/quality.py）

后端九端点已全量实装（master）：`/rules`(quality.py:73) · `/rules/{no}` PATCH(quality.py:103，
13-20 启用守卫 422 quality.py:118-126) · `/tasks` POST 202(quality.py:185) ·
`/tasks/{id}`(quality.py:213) · `/tasks`(quality.py:272) · `/issues`(quality.py:332，含
lane/rule_no/page/pageSize 查询参数 quality.py:336-339) · `/issues/{id}/transitions`
(quality.py:387，body `{action?}` quality.py:370-372) · `/freshness`(quality.py:445) ·
`/quarantine`(quality.py:479，batch_id/rule_no/issue_id 三过滤)。

### 1.1 逐字段差异清单

| # | 页面消费点 | mock 形状（e2.js） | 真接口形状（quality.py） | 判定 | 接线形态 |
|---|---|---|---|---|---|
| E2-1 | 任务表「隔离/拒收」列 E2.jsx:281；报告弹窗 E2.jsx:389 | `t.report.quarantinedRows` / `t.report.rejectedBatches`（camelCase，e2.js:41-42） | `quarantined_rows` / `rejected_batches`（TaskReportBody quality.py:160-161，snake_case） | **字段名不符——直连必渲染 undefined** | A（改名映射） |
| E2-2 | 报告弹窗「启用规则」行 E2.jsx:386 | `reportTask.report.rules`（mock 于 e2.js:165 把 rules 注入 report：`report: {...REPORT_0915, rules: run.rulesEnabled}`） | **TaskReportBody 无 rules 键**（quality.py:157-164 仅 range/scanned/quarantined_rows/rejected_batches/hits/verdict）；规则数在顶键 `task.rules`（TaskRecordBody quality.py:169） | **键位不符——弹窗该行渲染「undefined 条」**；改读顶键 | A（键位上移） |
| E2-3 | 抽屉「诊断说明」E2.jsx:422；「关闭原因」E2.jsx:424；复验列 E2.jsx:339 | `issueCard.aiNote` / `issueCard.closeNote`（camelCase，e2.js:56,100） | `ai_note` / `close_note`（IssueItemBody quality.py:319,321） | **字段名不符** | A（改名映射） |
| E2-4 | 问题单列表响应 E2.jsx:58 | `{lanes, items}` 无分页键（e2.js:183-186） | `{lanes, items, page, page_size, total}`（IssuesResponse quality.py:324-330；入参 page≥1＋pageSize alias quality.py:338-339） | 兼容——页面只读 `is.items`；client.unwrapEnvelope（client.js:156-171）会把 page/page_size 归一化。信封消费为可选项 | 登记（无必须改动） |
| E2-5 | 流转请求 E2.jsx:104-111 | `transitionQualityIssue(id, action)` 函数签名（e2.js:191），rescan 复扫/流转同函数 | POST body `{action?: "rescan"}`（quality.py:370-372）；流转请求体 `{}`；响应 `{id,lane,state,verify}` 两态同形（quality.py:374-379） | 形状对齐，函数体换 fetch 即可 | A |
| E2-6 | 错误提示路径 E2.jsx:74,97,109 | mock throw `Error('人话文案')`（e2.js:131 '规则不存在' / :140 '已有质检任务进行中' / :154 '质检任务不存在' / :194 '问题单不存在' / :196 '仅复核态可复扫' / :200 '已关闭——终态不可流转' / :202 '复验未全绿…'） | ApiError 族：`quality_rule_not_found` 404 / `quality_task_running` 409 / `quality_task_not_found` 404 / `quality_issue_not_found` 404 / `quality_issue_state` 409 / `quality_close_not_verified` 422 / `quality_param_invalid` 400 / `quality_task_channel_deferred` 501 / `quality_rule_registered_only` 422（errors.py:395-480＋quality.py:118-126）；错误包 `{code,message,detail,trace_id}`（errors.py:157-169） | client.request() 已先 antd message 弹错误包再抛 ApiError（client.js:208-214）——页面 catch 里再 `message.warning(e.message)` 会**双 toast**；且丢 code/trace_id 上下文（对比 errText 三段式 client.js:113-120） | B（toast 收口：catch 去手动弹或改 errText 展示） |
| E2-7 | 规则开关（13-20）E2.jsx:69-76 | mock 允许启用 13-20（e2.js:131-134 无守卫），且计入发起任务的规则数（e2.js:144） | **PATCH 置 13-20 enabled=true 拒 422**（quality.py:118-126 REGISTERED_ONLY_RULES＝range(13,21)；enabled=false 恒放行）——v0.5「仅登记不实施」 | 行为差异：乐观更新＋catch 回退逻辑（E2.jsx:71-74）可优雅承接（回退＋提示），但 13-20 开关在真接口下**永假**；页面规则库帮助文案 E2.jsx:141 仍写「去重保首条」旧白名单（v0.4 已撤——teach 快照残留，登记） | B（行为差异登记＋文案核对） |
| E2-8 | 发起→轮询 E2.jsx:85-95 | mock 同步受理＋600ms/步假进度（TASK_STEP_MS=600 e2.js:118；step 0→4 均匀步 e2.js:156）；页面自写 `for(;;)`＋250ms sleep | 真：202 受理落行 running/step=0 → **数据面 APScheduler worker 拾取执行**（任务表轮询通道，quality.py:141-150 注记）→ done step=2 → 服务端接续建单/挂单 step=4（service.py:385-406,414-461）；running 形 `{taskId,status,step}`、done 形 `{taskId,status,task}`（exclude_none，quality.py:213-217,262-269） | **轮询语义不同**：①步值域 0/2/4 非均匀 0-4，步进条 4 步文案（E2.jsx:187-192，硬编码「命中 3 条 → 开问题单」——真 hits 事先未知）需改判定式；②页面循环无瞬时失败容忍（一次网络抖动即 catch 整体退出）、无终止上限；底座 pollTaskUntilDone（client.js:281-305：1.5s 间隔＋容忍一次瞬时失败＋AbortController）即为此缝而建 | B（换 pollTaskUntilDone/useTaskPolling＋步进条语义修） |
| E2-9 | 重跑语义 | mock 清 `d` 前缀 lane0 后**追加固定三条 DYNAMIC_ISSUES**（e2.js:141,168-171） | 真：受理前撤「分发未认领」动态单（同判别式 d 前缀＋lane0，domain.py:129）；命中由数据面报告 hits 逐条 register_hit 建单/挂单（hit_identity 白名单投影 domain.py:135-160；owner＝DISTRIBUTION_OWNER domain.py:132）——单内容/数量随跑批实况 | 页面 `setIssues((await listQualityIssues()).items)` 刷新（E2.jsx:90）兼容。mock 的 aiNote=「AI 归因草稿」语义已废：真 `ai_note`＝规则判据说明投影（`规则 N 判据：<crit>`，service.py:179-183——v0.5 降级零 LLM），抽屉文案语义随之变化（登记） | 登记 |
| E2-10 | 首屏种子 | mock 预置五张单 p8/p5/p7/p4/p10（e2.js:81-102，覆盖五态演示）＋初始任务 QT-20260915-01（e2.js:80）＋水位三行（e2.js:71-75） | **0015 迁移只种 quality_rule 20 行**（migrations/versions/20261004_0015_quality_waterline.py:53-105，1-12 enabled=true、13-20 false；规则文本与 e2.js RULES 逐字一致——已核对）；quality_issue/quality_task/water_line **无种子** → 真接口首屏：任务页签空、问题单页签空；水位 items=[]（water_line 写权在数据面/入湖管道，缺层如实缺行 service.py:496-499）——页签「数据到哪天（0）」 | 空态承载需确认（Empty 文案已有多处）；演示/验收需数据面回写水位或登记空态预期 | B（空态确认） |
| E2-11 | 抽屉 qrows E2.jsx:336,426-433 | mock qrows.loc/note 恒有值 | 真 qrows＝隔离区回挂行，`note`＝payload["note"] 键约定（service.py:103-106,187）、`loc` 可 None——空值渲染兜底；隔离区端点 9（quality.py:479）mock 无对应函数、页面未直调——合同注记「页面当前以问题单详情抽屉内嵌呈现（按 issue_id 过滤）」由 qrows 已满足，端点 9 独立查询页留位 | 小改＋可选增强 | B（小：空值兜底） |
| E2-12 | 初始加载 E2.jsx:53-62 | `Promise.all` 四调用无 catch——真接口任一失败 loading 恒 true（骨架屏永挂） | — | 错误态缺失 | B |
| E2-13 | LANES 常量 E2.jsx:8 import 自 mock | 前端常量 | 响应携带 `lanes`（quality.py:347；domain.py:47 同值五态） | 可切换为响应源（非必须——两端同值） | A（可选） |

### 1.2「发起质检→轮询→三落地」真接口可用性判定

**条件可用**。受理面（端点 3：202＋409 重入闸 service.py:347-381）、轮询面（端点 4：running 直读＋
done step=2 服务端接续，接续/认领/建单/隔离行回挂同事务原子 service.py:414-461）、历史面（端点 5：
done 倒序 running 不进列表 service.py:408-412）均已接通；三落地（任务记录/隔离区落行/问题单建单）
在数据面 worker 跑批后由服务端接续完成。**风险两点**：①数据面 worker 拾取半边不在场时，任务恒
running step=0——页面现循环将无限轮询（接线时建议加「长时间无进展」提示或依赖 useTaskPolling
abort）；②复扫走同通道限时轮询，超时 10s（channel.py:57-58 DEFAULT_TIMEOUT_SECONDS=10.0）回
501 `quality_task_channel_deferred`——页面 flowCard catch 现有兜底可承接（配合 E2-6 toast 收口）。

### 1.3 mock 有而真接口没有（或反之）逐条汇总

- mock 有、真无：report.rules 键（E2-2）；quarantinedRows/rejectedBatches camelCase（E2-1）；
  aiNote/closeNote camelCase（E2-3）；13-20 可启用（E2-7）；固定三条动态单＋「AI 归因草稿」文案
  （E2-9）；五张预置单＋初始任务＋水位三行种子（E2-10）；600ms 均匀四步假进度（E2-8）。
- 真有、mock 无：issues 分页信封 page/page_size/total（E2-4）；lane/rule_no 服务端筛选参数；
  13-20 启用 422 守卫（E2-7）；409/422/404/501 错误码族与 trace_id（E2-6）；隔离区端点 9 与
  三过滤参数（页面可不变）；x-dev-user 身份头（client authHeaders client.js:62-64）。

---

## 二、A2 井档案（pages/A2.jsx 内嵌 WELLS 种子）× 真后端四端点（app/api/wells.py）

后端四端点已实装：`GET /api/wells`(wells.py:62，无 prefix 根端点) · `/{well_id}`(wells.py:100) ·
`/{well_id}/chain`(wells.py:202) · `/{well_id}/change-tickets`(wells.py:264)。页面当前**零 api
调用**（数据全内嵌＋`import { TICKETS } from '../data/changeTickets.jsx'` A2.jsx:7）——合同行为
规则 6⑤「页面数据从 A2.jsx 内嵌种子外移至服务端」即本票主体。

### 2.1 DTO 逐字段差异

| # | 页面消费 | 种子形状（A2.jsx） | 真接口形状 | 判定 | 接线形态 |
|---|---|---|---|---|---|
| A2-1 | 下拉选项 E2 对应 A2.jsx:13-18 | WELL_OPTIONS 常量 3＋1（禁用占位「（无查看权限的井不在此列表）」） | 端点 1 行 7 字段 `{well_id, well_name, well_kind, well_kind_code, block_name, current_status, remark}`＋total（wells.py:47-59）；服务端数据域过滤（无权井不出现）；排序 well_id 升序 | label 拼装是前端展示层职责（合同端点 1 注记：末段取状态**或**备注——N-06 用备注、N-02/N-11 用状态）；禁用占位条目为前端常量保留；`well_name: null` → 渲染「—」（种子 head.name='—' A2.jsx:48,75——真返回 null 需兜底） | A |
| A2-2 | 档案明细 Descriptions A2.jsx:237-247 | head 9 键 `{id,name,kind,spud,platform,block,status,ok,note}` | 端点 2 8 字段＋quality_notes＋foot_note（wells.py:86-97）：`well_id/well_name/well_kind+well_kind_code/first_prod_date/platform/block_name/current_status/remark` | 逐一映射：id←well_id、name←well_name、kind←`{well_kind}（{well_kind_code}）` 拼装（种子存拼装串「采油（EW）」A2.jsx:22；真两字段——合同端点 2「展示拼装」）、spud←first_prod_date、block←block_name、status←current_status、note←remark（span 2） | A |
| A2-3 | 状态 Tag 色 A2.jsx:245 | `ok` 布尔（种子自带） | **DTO 无 ok**（wells.py:86-97）——按 current_status 展示映射（合同：生产中绿/停产红；「检修/待弃置」二色未冻结——接线票定） | 布尔→映射函数 | B（小） |
| A2-4 | 红字质量备注 A2.jsx:248-250 | `quality: []`（数组） | `quality_notes: list[str]`（wells.py:96；仅 N-11 两条 domain.py:103-111——与种子 A2.jsx:77-78 **逐字一致**，已核对） | 同形无差 | 无 |
| A2-5 | 卡底注记 A2.jsx:251-253 | `infoFoot` | `foot_note`（wells.py:97；注水井派生冻结文案 domain.py:92-97＝种子 A2.jsx:50 逐字一致） | 改名；**DEV 工程注记分支撤除**（A2.jsx:106-108 `if (DEV) infoFoot='（m16…）'`——合同明示「mock 的 DEV 模式工程注记不入合同」） | A |
| A2-6 | chain.root | 种子三井均带 root（A2.jsx:26,52,82） | **合同不设该字段**（行为规则 6③「页面未渲染，合同不设」）——页面 grep 确认无消费 | 随种子退役 | 无（删数据） |
| A2-7 | 措施台账 A2.jsx:27-32,110-115 | `{key,date,type,content,result}` | 端点 3 measures 同形 `{key,date,type,content,result}`（wells.py:129-134）；真源＝raw.well_measures 表＋冻结演示文案按（井,日,类型）匹配（domain.py:155-165 与种子**逐字一致**；无匹配行 content/result=None service.py:93-108——空值兜底） | 同形；空值兜底 | A＋小 |
| A2-8 | 设备台账 A2.jsx:34-37,116-121 | `{key,type,status,ok,since,note}` | DeviceBody `{key,type,status,since,note}` **无 ok**（wells.py:137-142）；status∈三枚举（domain.py:41）；真源＝冻结演示快照（domain.py:187-218——中台 equip_status 无井关联列 DP-03 注记 store.py:16-18；三井快照与种子**逐字一致**，已核对）； DEVICE_COLS `color={r.ok?'green':'red'}` A2.jsx:118 → 按状态映射（运行中绿/停机检修红/随井停用红或灰——展示层定） | ok→映射函数；其余同形 | A＋B(小) |
| A2-9 | 检修台账 A2.jsx:38-39,122-127 | `{key,from,to,job,impact,batch}` | OverhaulBody `{key,date_start,date_end,job,impact,batch}`（wells.py:145-151）——**from/to→date_start/date_end 改名**；batch＝「批次 」+batch_id 服务端拼装（service.py:111-126）；真源＝raw.well_overhaul 表行（种子值是否在库取决于中台数据） | 改名映射（消费点 OVERHAUL_COLS A2.jsx:123＋buildEvents A2.jsx:140） | A |
| A2-10 | 状态变更行 A2.jsx:41,66-68,94-99＋buildEvents A2.jsx:136-145 | 种子独立 `statusEvents` 数组（warn 键）＋**前端合并排序**（buildEvents：措施按 date/检修按 to/状态变更按 date 倒序） | **服务端已合并**进 `events[]`（kind∈措施/检修/状态变更三值；状态变更行 outcome＝警示文案、无 warn 键；`date_end` 仅检修行携带——两响应体类型承载 wells.py:154-185；排序键＝措施作业日/检修完工日/状态变更发生日 domain.py:354-393） | **前端编排整体退役**（合同端点 3「合并与排序由服务端完成，前端零编排」）；EVENT_COLS 消费 r.from/r.to（A2.jsx:130）改 date/date_end；kind→Tag 色（default/orange/red）为展示映射保留前端常量 | B |
| A2-11 | 页签尾注 A2.jsx:42-43,69-70,100-101 | `measureEnum`/`deviceEnum` | `measure_foot`/`device_foot`（wells.py:193-194；N-06 措施变体/N-11 设备变体 domain.py:123-126 与种子**逐字一致**） | 改名 | A |
| A2-12 | 五页签计数 A2.jsx:199-213 | 页签 label 取数组长度；变动计数＝TICKETS.filter().length（A2.jsx:210） | 端点 3 `counts{events,measures,devices,overhauls,changes}`（wells.py:121-127,214-217）；`changes`＝端点 4 total 同源同值（**V1 恒 0** service.py:206,221-228） | 建议直接消费 counts | A |
| A2-13 | 尾注 tail A2.jsx:261-263 | 种子 `tail` | `tail`（wells.py:199,242；N-06 受效关系/N-11 追溯结论 domain.py:141-144 逐字一致；其余井 null） | 同形 | 无 |
| A2-14 | 变动页签 A2.jsx:157-186,210 | `TICKETS.filter(t => t.object.includes(wellId))` 字符串包含；status 机器码（pending/auto/rejected/withdrawn）经 CH_STATUS 映射（A2.jsx:157-162）；plane 由单号前缀推导 planeOf（A2.jsx:163）；proposer.replace('提出：','')（A2.jsx:171） | 端点 4 `{well_id, items:[{id,status,plane,short,proposer,time}], total}`（wells.py:249-262）——status/plane **直接返回展示值**（合同端点 4 注记「本页零加工渲染徽标」）；过滤按对象实体引用（装配批，非字符串匹配）；**V1 端点壳恒 items=[] total=0**（service.py:241-245「A3 主单未建——不 mock 假单」） | 差异五件：①过滤逻辑退役；②CH_STATUS 映射表退役（真 status 已是「待审批」等）；③planeOf 退役；④proposer 无「提出：」前缀（拼装简化）；⑤mock 演示 4/4/3 单 → 真恒空态「本井暂无变动单」——**演示效果显著回退属合同内如实态**（阶段 3 A3 施工回填） | B |
| A2-15 | 选中井切换 A2.jsx:220-224 | `setTimeout(400)` 假 Spin | 真＝并发拉端点 2/3/4＋Spin 遮罩（合同端点清单注记）；默认选中列表首口 | 交互逻辑替换 | B |
| A2-16 | 去问一问 A2.jsx:147-155,225-226,234 | goAsk 仅 `location.hash='/A1'`（不携带井） | 不立新端点；A1 `POST /api/chat/asks` 附 `page_context {page:'A2',object_type:'well',object_id}`——携带方式「结合实际前端框架定」（URL 参数/路由态/会话态） | **接线票需拍携带机制**（A2 是 page_context 第一个生产页）；不阻塞读面接线 | B（决策点） |
| A2-17 | 错误态 | 页面无任何错误处理 | 404 `well_not_found`（errors.py:377-384）/403 security_forbidden（预埋期 403 分支不可达——谓词恒真 domain.py:73-86）/401 | 404 提示/回退需补 | B |

### 2.2 内嵌种子 × 合同常量差异核对（票面指定项）

- **设备状态三枚举**（运行中/停机检修/随井停用）：种子 A2.jsx:35,36,60,61,85,86 与 domain.py:41
  **一致**；种子另带 `ok` 布尔（真 DTO 无——A2-3/8 映射化）。
- **措施效果列口径**（result＝演示粒度文案，不回推 incr_oil_annual）：种子九行与
  domain.py:155-165 `_MEASURE_DEMO_COPY` **逐字一致**（N-02 五行/N-06 四行；N-11 空数组一致）。
- 井状态四枚举/措施类型/设备类型枚举/EW-IW 码：种子与 domain.py:32-39 一致。
- **结论：内嵌种子与合同常量零冲突；全部差异在承载位置（页面内嵌 → 服务端）与字段名/键位。**

### 2.3 环境与数据前置（非页面缺陷，如实登记）

①raw.well_info/well_measures/well_overhaul＝中台源表轻声明（store.py:89-121，DDL 真源在数据面仓
DP-03）——开发库无行则端点 1 返回 `items:[] total=0`、下拉空；接线票需确认开发库中台表有设定书
§A 样本行（种子真源归数据面仓，主仓不造）。②`well_status_log` 平台补位表已建（0017 迁移）但
**写入通道悬置**（99 开放问题 2；store.py:269-287 只读不产行）——真接口下 N-06 一条/N-11 两条
状态变更警示行（种子 A2.jsx:66-68,94-99）**不出现**（events 缺行），属后端如实态非缺陷。

---

## 三、B4 报告百科（pages/B4.jsx 两页签版）× 真后端两端点（app/api/wiki.py）

后端两端点已实装（v0.4 纯读，版本族已撤）：`GET /pages`(wiki.py:55，lib/keyword 筛选) ·
`GET /pages/{pageId}`(wiki.py:123，恒当前版)。页面当前零 api 调用（PAGES/EVIDENCE/CLAIMS/
GLOSSARY/RELATED/正文快照/CUR_VER 全常量内嵌）。

### 3.1 逐字段差异清单

| # | 页面消费 | 页内形状（B4.jsx） | 真接口形状（wiki.py） | 判定 | 接线形态 |
|---|---|---|---|---|---|
| B4-1 | 目录行 B4.jsx:23-40,331-363 | PAGES 行 `{key,title,lib,src,slug,updated}` | 端点 1 行 `{id,title,lib,source_report:{id,doc},current_version,updated,status}`（wiki.py:40-52） | 映射：key←id（真值 wiki-n02-completion 等——slug 稳定性载体）；src←source_report.doc；slug 不在端点 1（只在端点 2 detail——目录页未用 slug ✔）；title/lib/updated 同名直用 | A |
| B4-2 | 目录「当前版」列 B4.jsx:346-348 | `v{CUR_VER[p.key]}`（常量 {w1:3,w2:1} B4.jsx:293） | `current_version`（重建计数语义同 v0.4——wiki.py:45,63-64） | 常量→字段；「当前版：vN」蓝 Tag 读页同（B4.jsx:414,423） | A |
| B4-3 | 目录「状态」列 B4.jsx:325-329,351-353 | `statusTagOf`：本地读 `CURRENT[key].includes('[[flag:')` 判定 | `status` 服务端按当前版正文 flag 有无判定直返（wiki.py:11-12,47——行为规则 5 服务端组装） | **本地判定退役**，两页签（目录列＋读页元数据条 B4.jsx:424）都改消费服务端 status | A |
| B4-4 | 目录筛选 B4.jsx:306-307,319-322,389-395 | 本地 filter（libF＋kw 对 title/src/lib） | 端点 1 query `lib`/`keyword`（wiki.py:59-61；keyword 冻结匹配题名/来源报告/所属库三字段——同页面现口径）；「筛选结果 X / Y 条」＝items.length＋total（total＝全量计数，count_pages 先于筛选 wiki.py:65-66） | 本地筛选退役→参数化请求（输入防抖可选） | B |
| B4-5 | 打开读页 B4.jsx:314-317 | `openPage(key)` 仅 setState 切页签（数据即常量） | GET /pages/{pageId} 拉全文快照（404 `wiki_not_found`——含开关关未生成，errors.py:270-276） | openPage 异步化＋detail state＋loading＋错误态 | B |
| B4-6 | 元数据条 B4.jsx:419-438 | 来源报告←page.src；生成来源←SOURCE_COLORS 常量（{自动重建:'default'} B4.jsx:296）；操作人←GEN_OPERATOR 常量（B4.jsx:298）；slug←page.slug | detail `{id,title,lib,slug,digest,source_report,current_version,updated,status,generation_source,operator,related_objects,content,claims,glossary_terms}`（wiki.py:105-120）——generation_source 值域单态「自动重建」（v0.4 ✔ 常量可退役）；operator 真 DTO 携带（自动重建恒「系统（入库管线）」）；digest 页面现无消费位（目录候选摘要用——登记不消费） | 字段映射＋常量退役 | A |
| B4-7 | 关联对象行 B4.jsx:232-241,428-437 | RELATED{label:'井 N-02', detail:'井名 …·关联注水井 N-06（受效关系）'}＋links 硬编码 `#/A2`·`#/B5`（B4.jsx:433） | `related_objects[]: {type,id,summary,links}`（wiki.py:98-102,147-148；summary＝合同逐字演示值；links=['#/A2','#/B5'] DTO 携带） | label「井 {id}」前端拼装（小）；detail←summary；links 改消费 DTO（B4.jsx:433 硬编码撤） | A＋小 |
| B4-8 | 正文渲染 B4.jsx:184-229,440 | W1_CURRENT/W2_CURRENT 页内快照（.replace 造 flag 版 B4.jsx:269-270） | `content`＝服务端生成时固化 markdown 全文（wiki.py:118,129-131），标记族 [[well:]]/[[route:]]/[[claim:]]/[[term:]]/[[flag:]] 同语法 | **Md/renderInline 解析器原样可用**（五族标记＋**bold 全覆盖）；种子常量与 replace 手法整体退役 | A |
| B4-9 | 证据弹层 B4.jsx:49-64,66-107 | CLAIMS（claim→ids）＋EVIDENCE 常量（f1-f4 {report,section,type,text}） | 真 claims[]: `{claim_id,text,evidence_chunk_ids}`（wiki.py:85-89,142）——**证据条目细节（report/section/type/text）不在 B4 端点 2**；合同 mock 更正清单⑨：证据条目改**展开时懒加载 B2 端点 1/2** | 懒加载改造：web 侧复用件已在——kb.js `listFragments`（:407-424，reportId 读法）＋`getFragmentContext`（:430-435）；claims[].text 真 DTO 有（弹层可补显论断句）；fail-closed 现实现已合规（B4.jsx:68-70 锚失效不渲染 ✔） | B |
| B4-10 | 台账挂接 chip B4.jsx:110-114,116-140 | GLOSSARY{kind:'指标口径'/'业务术语', ref:'指标台账 #5', def,status,statusColor,owner,extra,src} | `glossary_terms[]: {word,kind:'term'|'metric',ref_id,card:{…C1 端点 2/3 行同形}}`（wiki.py:91-95,143；票 93 服务端直取投影不建仓；「台账无账不挂」由服务端识别固化——前端 fallback 保留即可） | card→展示字段映射函数：kind metric→指标口径/term→业务术语；ref→`指标台账 #${ref_id}` 拼装；extra 组装（指标＝grain/unit、术语＝expires_display）；src←card.source；GlossChip 渲染器复用 | B |
| B4-11 | 版本族残留 | — | — | **零残留确认**：页签两枚 catalog/read（B4.jsx:372-375）✔；无版本历史页签/回滚按钮/确认弹窗/`?version=` ✔；CUR_VER 注释已是重建计数语义（B4.jsx:292-293）✔。唯一内部残留＝W1_SEED/W1_CURRENT 双常量＋.replace 造版工艺（B4.jsx:244-270）——mock 工艺随接线退役 | 无（登记确认） |

### 3.2 环境前置（如实登记）

wiki_page 表无种子（0004 基线/0016 补列均为结构迁移，INSERT=0）——真接口目录空，除非 B1 入库
管线 wiki 支路跑过生成。演示前提＝B1 侧生成真实页面或登记空态预期（合同：「制度文件库未出百科页
为演示缺省不洗白」同精神）。

---

## 四、web 三连与 UI 系提交基线（票面第 4 节）

- **基线**：HEAD 398ba20（工作树净；5a6027e＝UI-11 撤销票归档，仅 tickets/phase1-ui 文档）。三连
  实跑全绿（eslint 0 error＋2 存量 warning D3:96/INDEX:85；vitest 12 文件 210 例全过；vite build
  4.12s）——**对账三页在基线上无红灯**。
- **UI 系改动面与三页的冲突判定**：UI-08（41301f7/bb27fc3 真机填满）、UI-12（ceaecc6 PagedTable
  fill＋五页 flex 链）、UI-13（e8fc65d 标题上移壳层）、UI-15（5468b75 B2/B3 无头化）、UI-16
  （ec7daf5 A1 空态）**全部只落 landing/ 树＋shell/**（UI-13 stat 实证：landing/{B1,B2,B3,B5,D1}
  ＋shell/{HeaderBar,Shell}）——pages/E2.jsx、A2.jsx、B4.jsx 最后触碰＝3c2d63a（P2-05 快照同步），
  **UI 系零接触，无冲突面**。PagedTable（components/PagedTable.jsx）消费方＝landing 五页——三页
  现用页面级 Table（pagination=false 全表），接线落地树时是否收编 PagedTable 属 UI 惯例决策
  （B1 先例），非冲突项。
- **一项 UI 对齐登记（非阻塞）**：UI-13 交互惯例（页内大标题删除、标题上移壳层页头、? 迁卡头
  extra）对落地树生效——三页落地化时按此惯例调整 Card title 结构（E2.jsx:198-215/A2.jsx:230/
  B4.jsx:368-383 现形态为原型树形态）。

---

## 五、接线工作量判定（票面第 5 节——拆票输入）

| 页 | 形态 | 判定依据 | C（后端小改）清单 |
|---|---|---|---|
| **E2** | **B（偏 A）** | A 件：e2.js 函数体换 fetch＋四处字段名/键位映射（E2-1 quarantined_rows/rejected_batches、E2-2 report.rules→task.rules 顶键、E2-3 ai_note/close_note、E2-5 body {action?}、E2-13 lanes 可选切换）。B 件：轮询通道换 pollTaskUntilDone＋步进条语义修（E2-8）、错误 toast 收口/errText（E2-6）、13-20 守卫行为与帮助文案核对（E2-7）、空态与初始加载错误态（E2-10/12）、qrows 空值兜底（E2-11） | **无**——九端点已全量实装且形状与合同 v0.5 一致；report 无 rules 键属合同示例形状（页面侧改读顶键） |
| **A2** | **B** | 四端点全新接线（页面零 api 调用）＋新 api 模块；A 件：下拉/明细/三台账字段映射（A2-1/2/4/5/7/9/11/12/13）。B 件：buildEvents 退役改消费服务端 events（A2-10）、设备/状态色映射（A2-3/8）、变动页签切端点壳＋四件 mock 简化退役（A2-14）、切换并发拉＋Spin（A2-15）、page_context 携带机制拍板（A2-16）、404 错误态（A2-17） | **无**——端点 4 空列表是合同内 V1 如实态（不 mock 假单，A3 阶段 3 回填）；well_status_log 写通道悬置属 99 册开放问题 2（非本票）；环境前置＝中台表有样本行（数据面仓职责） |
| **B4** | **B** | 两端点全新接线＋新 api 模块；A 件：目录/元数据条/related_objects/content 字段映射（B4-1/2/6/7/8）。B 件：目录筛选参数化（B4-4）、读页异步化＋404 态（B4-5）、本地 status 判定退役（B4-3）、证据弹层懒加载 B2（B4-9——复用 kb.js listFragments/getFragmentContext）、glossary card 映射（B4-10） | **无**——两端点已实装 v0.4 形状；B2 页面消费 `#/B2?chunk=` locator 未落位属 B2 册出入对账 10 挂账（现「跳 B2 读面」可用，不阻塞）；环境前置＝wiki_page 有生成行（B1 管线职责） |

共性件（三页可共票或共约定）：①新 api 模块统一走 api/client（request/错误包/unwrapEnvelope/
authHeaders 已备）；②错误提示收口约定（client 已弹＋页面不重复弹，展示 code/trace 用 errText）；
③落地树注册（landing/<KEY>.jsx＋registry.js）＋UI-13 壳层标题惯例；④演示数据前置登记（中台表
样本行/water_line 回写/wiki_page 生成——三项均归数据面/B1 侧，接线票面应写明「空库空态即验收态」
或另立演示种子票）。

---

## 偏差

无。票面五节全覆盖：三页逐字段差异清单（每条带 file:line＋接线形态）、web 三连与 UI 系基线、
工作量三分类（A/B/C）。补充发现三项（票面未显式要求、接线票需知）：E2 帮助文案一处 v0.4 前残留
（E2.jsx:141「去重保首条」——teach 快照残留，随接线核对）、A2 状态变更行真接口下不出现
（well_status_log 写通道悬置——登记不修）、B4 digest 字段页面无消费位（登记不消费）。

## 零修复动作声明

本审计全程只读：未改任何源码/配置/合同；除本报告文件（dispatch/results/R-WIRE.md）外主仓零写入；
工作树在报告写就后仍应保持净（web 三连产物仅 node_modules/dist 内存态，未提交）。所有发现均为
登记性质，修复/接线动作归后续接线票（以第五节分类为拆票输入），裁决权在 L0/Owner。
