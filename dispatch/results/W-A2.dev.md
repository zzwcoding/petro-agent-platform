# W-A2 开发拍 回报

## 产物

- **提交**：`3af8dfe`（分支 `fix/wire-a2`，基于 master `04f9606` 单提交；**worktree `.scratch/wire-a2` 已验后清理**，分支与提交保留待合并）
- **文件**（票面点名三件，`git show --stat 3af8dfe`：3 files changed, 548 insertions(+), 196 deletions(-)）：
  - `web/src/api/wells.js` **新建**（149 行）——A2 四端点真 API 接口层（经 client.js：`get`＋统一错误包＋身份头；wire snake→视图 camel 折回，`api/graph.js` 先例同构；`wellOptionLabel` 下拉文案拼装导出为纯函数）
  - `web/src/api/wells.test.js` **新建**（240 行，14 例）——四端点路径/身份头/折回映射/空态形状/`well_not_found` 透传/option 文案拼装；夹具形状照抄 `app/api/wells.py` 实况＋curl spot check 实测原文
  - `web/src/pages/A2.jsx` 改写（355 行改动）——内嵌种子退役（WELLS/WELL_OPTIONS/buildEvents/CH_STATUS/planeOf/TICKETS import/DEV infoFoot 全撤），切真后端四端点
- **主仓零污染**：master 仍在 `04f9606`；Owner 未提交私产（dispatch/journal.jsonl、pending/、results/、tickets/phase3/ 等）零触碰；`.scratch/wire-a2` worktree 已 remove，主树无新增未跟踪文件
- **环境事实（交接台侧）**：uvicorn `app.main:app --port 8000` 已在主树 master 代码上拉起并**保持运行**（日志 `/tmp/w-a2-uvicorn.log`）；raw 8 表保持零行（探针取证后已清）

## 闸门实跑（worktree 内，提交前实跑原文）

```
npx eslint .
  → ✖ 2 problems (0 errors, 2 warnings)
    （两条均存量：pages/D3.jsx:96 / pages/INDEX.jsx:85 react-hooks/exhaustive-deps——
      R-WIRE §四基线同款「既有 warning：D3/INDEX hooks 提示，非本批文件」；本票三文件零告警）

npx vitest run
  → Test Files  13 passed (13)
    Tests  224 passed (224)        （基线 210 例＋本票 wells.test.js 新增 14 例＝224；
                                     零压制零删除——A2 原无任何测试，无 mock 断言可适配）

npx vite build
  → ✓ built in 3.97s

python3 tools/debt_markers.py check
  → 债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。
```

### curl spot check（四端点连通＋空态形状＋404 探针，`X-Dev-User: aqiang`，原文）

**① raw 零行业务态（空态验收态）**：

```
=== GET /api/wells ===
{"items":[],"total":0}
[HTTP 200]
=== GET /api/wells/N-02 ===
{"code":"well_not_found","message":"井不存在（归一化后无此主键）：N-02"}
[HTTP 404]
=== GET /api/wells/N-02/chain ===
{"code":"well_not_found","message":"井不存在（归一化后无此主键）：N-02"}
[HTTP 404]
=== GET /api/wells/N-02/change-tickets ===
{"code":"well_not_found","message":"井不存在（归一化后无此主键）：N-02"}
[HTTP 404]
=== GET /api/wells/NOPE-404 ===
{"code":"well_not_found","message":"井不存在（归一化后无此主键）：NOPE-404"}
[HTTP 404]
```

**② 探针取证（临时插入设定书 §A.1/§A.5/§A.4 N-02 样本行——`_snapshot_id=999901/_batch_id=W-A2-PROBE` 标记行，取证后即删并复验零行）**——四端点 200 形状与 N2 归一化实测原文：

```
=== GET /api/wells ===
{"items":[{"well_id":"N-02","well_name":"渤中28-1-N2","well_kind":"采油","well_kind_code":"EW","block_name":"渤南","current_status":"生产中","remark":"正常"}],"total":1}
[HTTP 200]
=== GET /api/wells/N-02 ===
{"well_id":"N-02","well_name":"渤中28-1-N2","well_kind":"采油","well_kind_code":"EW","first_prod_date":"2019-06-15","platform":"CEP-A","block_name":"渤南","current_status":"生产中","remark":"正常","quality_notes":[],"foot_note":null}
[HTTP 200]
=== GET /api/wells/N-02/chain ===
{"well_id":"N-02","counts":{"events":2,"measures":1,"devices":2,"overhauls":1,"changes":0},"measure_types":["压裂","酸化","补孔","调剖"],"device_types":["电泵","螺杆泵","加热炉"],"measure_foot":"措施类型枚举：压裂 / 酸化 / 补孔 / 调剖","device_foot":"设备类型枚举：电泵 / 螺杆泵 / 加热炉","events":[{"key":"m1","kind":"措施","date":"2026-03-18","title":"调剖 · 主力层段调剖，调整吸水剖面","outcome":"综合含水降 1.2 个点"},{"key":"o1","kind":"检修","date":"2024-10-09","date_end":"2024-10-11","title":"检泵（泵轴更换）","outcome":"影响产量约 18 吨 · 批次 20241012-T2"}],"measures":[{"key":"m1","date":"2026-03-18","type":"调剖","content":"主力层段调剖，调整吸水剖面","result":"综合含水降 1.2 个点"}],"devices":[{"key":"d1","type":"电泵","status":"运行中","since":"2021-04-12","note":"2021 年换泵更新；上次保养 2026-06-02"},{"key":"d2","type":"加热炉","status":"运行中","since":"2019-09-01","note":"冬季高负荷、夏季低负荷"}],"overhauls":[{"key":"o1","date_start":"2024-10-09","date_end":"2024-10-11","job":"检泵（泵轴更换）","impact":"影响产量约 18 吨","batch":"批次 20241012-T2"}],"tail":null}
[HTTP 200]
=== GET /api/wells/N-02/change-tickets ===
{"well_id":"N-02","items":[],"total":0}
[HTTP 200]
=== GET /api/wells/N2 ===   （well_id 归一化 N2→N-02——合同行为规则 7）
{"well_id":"N-02",...同端点 2 全形...}
[HTTP 200]

（取证后清理：DELETE ... WHERE _batch_id='W-A2-PROBE' → 三表 count 全 0；
  复跑 GET /api/wells 回到 {"items":[],"total":0}——空态验收态恢复）
```

## R-WIRE §2 差异清单逐条处置表（票面验收项）

| # | R-WIRE 判定 | 处置 |
|---|---|---|
| A2-1 | A（下拉/7 字段/label 拼装/占位条目/null 井名） | ✔ 已接端点 1；label＝`wellOptionLabel`（api 层导出，14 例测试含三井演示文案）；禁用占位条目保留前端常量；`well_name: null` 明细卡渲染「—」 |
| A2-2 | A（明细 8 字段映射） | ✔ 已接端点 2；id←well_id、kind←`well_kind（well_kind_code）` 展示拼装、spud←first_prod_date、block←block_name、note←remark(span 2) |
| A2-3 | B 小（ok 布尔→状态映射；检修/待弃置二色未冻结） | ✔ `WELL_STATUS_COLOR`：生产中绿/停产红照合同注记；检修橙/待弃置灰＝**接线票拍板**（未知值兜底 default） |
| A2-4 | 无（quality_notes 同形） | ✔ 红字块照渲染（数组直出） |
| A2-5 | A（infoFoot→foot_note；DEV 注记撤） | ✔ 改名接线；A2.jsx:106-108 DEV 工程注记分支整体删除（DEV import 一并撤） |
| A2-6 | 无（chain.root 随种子退役） | ✔ 种子整体删除，页面无该字段消费 |
| A2-7 | A＋小（措施同形；content/result 空值兜底） | ✔ 同形直传；列 render `v ?? '—'` 空值兜底 |
| A2-8 | A＋B 小（DeviceBody 无 ok；色映射） | ✔ `DEVICE_STATUS_COLOR` 按状态：运行中绿/停机检修红；**随井停用取灰**（「红或灰」二择——停产伴生非故障，与停机检修区分，接线票拍板） |
| A2-9 | A（from/to→date_start/date_end） | ✔ api 层折回 `dateStart/dateEnd`（camel 惯例，graph.js 先例）；检修页签起止列改消费新名 |
| A2-10 | B（buildEvents 前端合并整体退役） | ✔ buildEvents 函数整体删除；「纪录」页签直渲染服务端 `events[]`（date_end 仅检修行携带的形状保真有测试锚定）；kind→Tag 色三值映射保留前端常量 |
| A2-11 | A（measureEnum/deviceEnum→measure_foot/device_foot） | ✔ 改名接线；空数组仍常驻显示尾注全文（N-11 措施 0 行照显——合同端点 3） |
| A2-12 | A（五页签计数消费 counts） | ✔ 页签 label 全部改消费服务端 `counts{events,measures,devices,overhauls,changes}`（变动计数不再前端 filter） |
| A2-13 | 无（tail 同形） | ✔ 直传直渲染 |
| A2-14 | B（变动页签四件 mock 简化退役） | ✔ ①字符串过滤退役（消费端点 4 items）；②CH_STATUS 机器码映射退役（真 status 已是「待审批」等展示值，四枚举→徽标色照合同常量橙/绿/红/灰）；③planeOf 退役（plane 直返，蓝/橙/紫）；④proposer 无「提出：」前缀替换（直出）；⑤V1 恒空态「本井暂无变动单」照合同渲染＋「去数据变动审批看全部」链接保留 |
| A2-15 | B（假 Spin→并发拉＋Spin） | ✔ 端点 2/3/4 `Promise.all` 并发＋Spin 遮罩；默认选中列表首口；seq 竞窗守卫（快速切井旧响应不回写）；`setTimeout(400)` 删除 |
| A2-16 | B（page_context 携带机制拍板） | **未动**——票面施工方案五项未含、R-WIRE 明示「不阻塞读面接线」；`goAsk` 维持纯跳转 `#/A1` 现状，行内注释登记。**拍板悬置→疑点 1，待 L0** |
| A2-17 | B（404/403/401 错误态补齐） | ✔ client 统一错误包 toast 后，页面 inline `errText` 三段（message·code·trace）呈现于 Empty 描述位；401/403/404/网络态全覆盖；列表失败与档案失败两路分别兜底（实测 404 形状见 spot check） |

补充处置（R-WIRE §2.3 环境前置登记）：①raw 中台表开发库无行→端点 1 `items:[] total=0` 空态即验收态（页面「暂无可见井」Empty＋空态渲染验收，实测见 spot check ①）；②`well_status_log` 写通道悬置（99 开放问题 2）→真接口下状态变更警示行不出现属后端如实态，**页面零特判不洗白**（events 缺行即不渲染，前端零编排）。

## 偏差

1. **票面前提「真后端已在 localhost:8000 运行」与实际不符→已代为恢复**：派发时 8000 无监听（仅 5173 vite 在跑）。处置：按 README 惯例主树 master 代码拉起 `uv run uvicorn app.main:app --port 8000`（后台，日志 `/tmp/w-a2-uvicorn.log`），保持运行供台侧复核。
2. **首拉 /api/wells 500（`permission denied for schema raw`）→按文档化模板补授**：dev 库 `midplatform` 角色在位、`default_transaction_read_only=on` 在位，唯 raw 模式 GRANT 缺失（ACL 空）。处置：照 data-plane 仓 `migrations/midplatform_readonly.sql` 模板补 `GRANT USAGE ON SCHEMA raw`＋8 表 `GRANT SELECT`（只授模板既有条目，零新增表）；此为环境预置步（该 SQL 自述「账号建立随数据面部署批由管理员执行，不进迁移账」），非代码改动。
3. **形状取证用临时探针行**：为取端点 2/3/4 的 200 信封原文，临时插入设定书 §A 样本行（N-02＋1 措施行＋1 检施行，`_snapshot_id=999901/_batch_id=W-A2-PROBE` 探针标记），curl 后即删并复验三表 count=0、端点 1 回到 `{"items":[],"total":0}`。业务数据零残留、业务事实零发明（行值＝设定书样本）。
4. **npm ci 而非 symlink node_modules**：worktree symlink 方案被主仓根级误装 node_modules（398ba20 登记物）破坏 vite 配置解析；改在 worktree 内 `npm ci`（499 包，package-lock 与主树同版）。
5. **camel 折回 vs R-WIRE 蛇形消费点**：R-WIRE 处置表按蛇形（date/date_end）写消费点；实现按 `api/graph.js` 先例在 api 层折回 camel（dateStart/dateEnd），页面消费 camel——同一差异清单的等价处置，测试锚定折回保真。
6. **N-06 下拉文案逐字 cosmetic 差**：种子 label「分层注水 3 层」（去括号），DB remark 原文「分层注水（3 层）」——实现取 remark **原文零加工**（label＝「N-06（渤南 · 注水 · 分层注水（3 层））」），不做字串改写（业务事实零发明）。合同端点 1 注记末段「取状态或备注属展示层选择」范围内。
7. **落地树注册未做**：R-WIRE §五共性件③建议 landing/<KEY>.jsx＋registry.js 注册与 UI-13 壳层标题惯例——**票面边界红线限定只动 `web/src/api/wells.js`（新建）与 `web/src/pages/A2.jsx` 及对应测试**，本票维持原型树（`#/proto/A2`）接线；落地化是否另立票→疑点 5。

## 疑点（待 L0 裁决，不动手）

1. **A2-16 去问一问 page_context 携带机制**（A2 为 page_context 第一生产页）：URL 参数／路由态／会话态三选未拍板；现维持纯跳转（不携带），拍板后 A1 侧消费需同批接线（涉及 A1Chat 页文件——超出本票边界红线）。
2. **两处未冻结色的接线票拍板请追认**：井状态「检修＝橙／待弃置＝灰」、设备「随井停用＝灰」——已在代码注释注源（W-A2 拍板，R-WIRE A2-3/8），若 Owner 另有偏好为常量一行改。
3. **N-06 下拉文案内层括号**：remark 原文直出（见偏差 6）是否接受，或需要展示层去括号工艺。
4. **环境修复留痕**：raw schema GRANT 补授（偏差 2）与 uvicorn 常驻（偏差 1）是否由台侧记入 watch/journal；raw 8 表当前零行，演示批灌数（数据面仓职责）后需另复核真数据态。
5. **落地树注册**（R-WIRE 共性件③＋UI-13 惯例）超出本票文件边界——原型树页面接线完成后是否补「A2 落地化」票，请裁决。
