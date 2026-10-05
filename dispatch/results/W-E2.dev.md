# W-E2 接线票 回报 —— E2 质检台页面切真后端九端点

> 作业方式：git worktree `.scratch/wire-e2`（分支 `fix/wire-e2`，基线＝master 04f9606）隔离作业；
> 单提交 `74c8bd0`；验后 worktree 已清理（分支保留，FF 可合并——见偏差 4）。
> 合同真源：teach-petro-agent/specs/api/E2-数据质量台.md v0.5；差异清单真源：R-WIRE.md §1。
> 票面边界兑现：只动 `web/src/api/e2.js`、`web/src/pages/E2.jsx` 及对应测试（新建 2 个测试文件）；
> 显式路径 git add 四文件，未用 git add -A/.；主仓工作树（Owner 私产）零接触。

## 产物

- 提交：**74c8bd0**（分支 fix/wire-e2，父 04f9606，单提交；worktree 已 remove，分支在主仓可查）
  ```
  web/src/api/e2.js                    | 234 ++++++------------------  （改：mock→真接口）
  web/src/api/e2.test.js               | 136 ++++++++++++++++++         （新：10 例）
  web/src/pages/E2.jsx                 | 146 +++++++++++++-------        （改：映射/轮询/收口/空态）
  web/src/pages/__tests__/E2.test.jsx  | 279 ++++++++++++++++++          （新：11 例）
  4 files changed, 557 insertions(+), 238 deletions(-)
  ```
- 施工方案五条全落地：
  1. **api/e2.js mock→真接口**：mock 内存 store（RULES 种子/预置五单/固定报告/600ms 假进度/250ms sleep）
     全撤；九函数一一对应九端点，全走 api/client 统一出口（GET 用 get、POST 用 post、PATCH 走
     `request(path,{method:'PATCH',body:{enabled}})`——client 无 patch 便捷式）；issues 显式
     `page=1&pageSize=500`（V1 整表消费语义，防 server 缺省 20 静默截断；信封经 unwrapEnvelope
     归一化，lanes 兄弟键保留）；LANES 保留前端常量（与 domain.LANES 同值——R-WIRE E2-13「非必须」）。
  2. **R-WIRE 硬伤四处修正**：`report.quarantined_rows/rejected_batches`（E2-1）、报告弹窗「启用规则」
     改读 task 顶键 `rules`（E2-2）、`ai_note/close_note`（E2-3）、轮询真化 202→useTaskPolling 至
     done/failed、撤 mock 250ms 固定延时（E2-8）。
  3. **错误处理**：toast 收口三处 catch（启停回退/发起/流转）撤 `message.warning`——client 层单弹
     （人话 message＋trace_id 三段式）；409 重入/422 关闭守卫/501 复扫超时同收口（服务端有闸，页面只回退不重弹）。
  4. **空态渲染**：任务/水位页签空态文案（「空库即验收态」）＋首屏四拉取失败内联失败态≠空态＋重试按钮（E2-12）。
  5. **测试适配**：无既有 E2 测试（基线 12 文件 210 例不含 E2）——新建 api 10 例＋页面 11 例（不压制任何旧断言）。

### R-WIRE §1 差异清单逐条处置表

| # | R-WIRE 判定 | 处置 | 落点 |
|---|---|---|---|
| E2-1 | A（改名映射） | ✅ 已改 | 任务表「隔离/拒收」列＋报告弹窗读 `quarantined_rows/rejected_batches`（null 安全 `?? 0`/`'—'`） |
| E2-2 | A（键位上移） | ✅ 已改 | 报告弹窗「启用规则」行读 `reportTask.rules` 顶键；任务表「启用规则」列同步 |
| E2-3 | A（改名映射） | ✅ 已改 | 抽屉「诊断说明」←`ai_note`、「关闭原因」←`close_note`；表格复验列←`close_note` |
| E2-4 | 登记（无必须改动） | ✅ 处置＋加固 | 页面仍只读 items；api 层显式 `pageSize=500` 拉满防截断（合同 v0.5 整表语义），e2.test.js 断言信封归一化 page_size→pageSize |
| E2-5 | A（函数体换 fetch） | ✅ 已改 | 流转空体 `{}`；rescan 带 `{action:"rescan"}`；响应 `{id,lane,state,verify}` 回写行 |
| E2-6 | B（toast 收口） | ✅ 已改 | 三处 catch 撤手动弹；e2.test.js/E2.test.jsx 断言 client 层 notify 恰 1 次＋回退不重复弹 |
| E2-7 | B（行为差异＋文案核对） | ✅ 已改 | 13-20 启用 422 由乐观更新＋catch 回退承接；帮助文案撤 v0.4 前残留「去重保首条」，补「仅登记不实施（开关不可启用）」注记 |
| E2-8 | B（轮询通道＋步进条语义修） | ✅ 已改 | `useTaskPolling(taskId,{path:'/quality/tasks'})`（底座 1.5s＋容忍一次瞬时失败＋AbortController）；onProgress 以 running step 0/2/4 直映步进 current；done 收场任务入列＋自动开报告＋刷新问题单；failed 收场步进条 error 态＋内联 errText；「命中 3 条」硬文案撤 |
| E2-9 | 登记 | ✅ 兼容 | done 后全量 `listQualityIssues()` 刷新（单内容/数量随跑批实况）；aiNote「AI 归因草稿」随 mock 退役，ai_note 现为规则判据说明投影（v0.5 如实语义） |
| E2-10 | B（空态确认） | ✅ 已改 | 任务/水位页签 Empty 文案；空库形状（rules 20 行/tasks []/issues []/freshness []）curl 实测＋E2.test.jsx 空态用例（四空响应夹具）双证 |
| E2-11 | B（空值兜底） | ✅ 已改 | 抽屉 qrows 表 loc/note render `?? '—'`；owner/desc 同族兜底（owner 可空连带责任岗筛选项 roleOf 兜底） |
| E2-12 | B（错误态缺失） | ✅ 已改 | loadAll（useCallback）catch → loadError 内联 Empty：`数据加载失败——{errText}`（message＋code＋trace 三段）＋重试按钮；测试两例（失败态渲染／重试翻回数据） |
| E2-13 | A（可选） | ⭕ 保持常量 | LANES 前端常量与响应 lanes 同值（R-WIRE 自标「非必须」）；e2.test.js 断言 `res.lanes` 与常量 toEqual |

## 闸门实跑

### web 三连（worktree 内实跑，HEAD=74c8bd0 工作树同内容）

```
npx eslint .
  → ✖ 2 problems (0 errors, 2 warnings)
    （两条均存量：pages/D3.jsx:96 hooks exhaustive-deps / pages/INDEX.jsx:85 hooks——
      与 R-WIRE §闸门实跑基线完全一致，非本票文件，未新增任何 warning）

npx vitest run
  → Test Files  14 passed (14)
    Tests  231 passed (231)
    Duration  13.62s
    （基线 12 文件 210 例 → 14 文件 231 例：+e2.test.js 10 例＋E2.test.jsx 11 例，全过）

npx vite build
  → ✓ built in 4.03s
    （dist 零 *.test.* chunk——页面测试落 __tests__ 子目录规避 Shell.jsx:21 动态 import
      glob，主仓既有 dist 亦无 test chunk，build 产物形状不变）
```

### curl spot check（真后端 localhost:8000，X-Dev-User: aqiang；输出原文）

```
════ [1] GET /api/quality/rules（端点 1——形状：autoFix 冻结 camelCase＋enabled）════
{"items":[{"no":1,"kind":"重复","rule":"同一口井同一天每个班次只能有一条日产记录——A/B 班手抄重复行即命中","crit":"班次三元组（井,日,班次）唯一；重复/缺失行进问题单人工复核，不静默去重","enabled":true,"action":"告警","autoFix":false},...
total 20 | enabled 1-12: 12 | enabled 13-20: 0 | no13 action: ['—（总册）']        → HTTP 200

════ [3] GET /api/quality/tasks（端点 5——空库）════
{"items":[]}  → HTTP 200

════ [4] GET /api/quality/tasks/QT-20990101-99（端点 4 错误形）════
{"code":"quality_task_not_found","message":"质检任务不存在：QT-20990101-99"}  → HTTP 404

════ [5] GET /api/quality/issues?page=1&pageSize=500（端点 6——分页信封）════
{"lanes":["分发","认领","整改","复核","关闭"],"items":[],"page":1,"page_size":500,"total":0}  → HTTP 200

════ [6] GET /api/quality/issues?lane=0&rule_no=1（端点 6 筛参连通）════
{"lanes":[...],"items":[],"page":1,"page_size":20,"total":0}  → HTTP 200

════ [7] GET /api/quality/freshness（端点 8——空库如实空行）════
{"items":[]}  → HTTP 200

════ [8] GET /api/quality/quarantine?issue_id=d1（端点 9——三过滤之一）════
{"items":[]}  → HTTP 200

════ [9] PATCH /api/quality/rules/13 {enabled:true}（端点 2 档位守卫——服务前置零写）════
{"code":"quality_rule_registered_only","message":"仅登记规则未实施，不可启用（规则 13 属 13-20 仅登记档）——归属 M-05b 执行通道接通后放开"}  → HTTP 422

════ [10] PATCH /api/quality/rules/13 {enabled:false}（幂等无状态变化）════
{"no":13,"enabled":false}  → HTTP 200

════ [11] PATCH /api/quality/rules/1 {enabled:false}→{enabled:true}（启停回路，写后即复原）════
{"no":1,"enabled":false} HTTP 200 / {"no":1,"enabled":true} HTTP 200

════ [12] POST /api/quality/issues/d999/transitions {}（端点 7 错误形——服务前置零写）════
{"code":"quality_issue_not_found","message":"问题单不存在：d999"}  → HTTP 404

════ [13] 复核：rule13 enabled=False | rule1 enabled=True（状态零残留）════
```

八端点连通＋形状实测（1/2/4/5/6/7/8/9）；端点 3 有意不 POST——见偏差 1。

### 其他闸

```
债务短语 grep（debt_markers strict 面 8 短语族：挂后续批|挂账|未接线|留后续票|随其票|
随其端点票|接线预留|产品化批）× 4 改动文件 → 零命中（exit 1）。
uv 系 python 闸未复跑：本票零 Python 改动＋worktree 无 .venv——合并前执行台全量复跑兜底。
```

## 偏差

1. **端点 3（POST /api/quality/tasks）curl 有意不做**：受理会落持久 quality_task 行
   （running/step=0）＋B12 审计行；数据面 worker 不在场时任务恒 running 并 409 封锁后续受理，
   且会污染本票「空态即验收态」基线。按派工总指令①「POST/PATCH 类只做对测试无害的」判定为
   非无害，skip。受理形状（202 `{taskId}`）由 e2.test.js POST 用例＋页面轮询链路用例覆盖。
2. **页面测试落 `pages/__tests__/` 而非与页同目录**：Shell.jsx:21 `import(\`../pages/${key}.jsx\`)`
   动态 import glob 会把 pages/ 下每个 .jsx 逐文件切 chunk——首跑 build 实测多出 453KB 的
   E2.test 死 chunk（主仓既有 dist 无 test chunk，属回归）。移入子目录后单层 glob 不命中，
   复跑 build 确认 dist 零 test chunk。
3. **PATCH 类 spot check 落了 2 行 B12 审计留痕**（[10] rule13 幂等 false、[11] rule1 false→true
   回路；[9] 422 服务前置不落审计）。rule1 已复原 true、rule13 复核仍 false——业务状态零残留，
   仅审计表多 2 行可溯留痕。
4. **master 作业期间前移 c953f30**（阶段 3 方案落册，docs-only +304 行 md）：本分支基线仍
   04f9606（即其父），路径不相交，FF 合并无冲突。
5. **worktree 工程细节**：node_modules 以 APFS clone（cp -Rc，写时复制）入 worktree 跑三连，
   未动主仓 node_modules，随 worktree 清理一并删除；worktree 内 git 状态在提交前保持净。

## 疑点（待 L0 裁决，不动手）

1. **issues pageSize=500 拉满策略为本票自裁**：合同只说「V1 数据量小整表返回」，R-WIRE E2-4 判
   「无必须改动」。若 L0 认为问题单应走真分页 UI（C3/A1 同款）而非 api 层拉满，另立票调整。
2. **复扫按钮无 busy 态**：真复扫走数据面通道限时轮询（channel.py 最长 10s 阻塞 POST），期间按钮
   可重复点（服务端 409/复扫中状态有闸兜底）——R-WIRE §1.2 判「现有 catch 兜底可承接」，本票未加
   busy；如需交互打磨归 UI 系票。
3. **轮询 failed 双 toast**：useTaskPolling 连续两次拉取失败才置 failed，client 层每次失败各弹一次
   （合计 2 次）——底座既有行为（D1 同），页面未抑制；如要收口需动 client.js（本票边界外）。
4. **演示数据前置**（R-WIRE E2-10 环境注记）：执行台灌数据后的真数据复核待排期——本票验收态＝空库空态。
