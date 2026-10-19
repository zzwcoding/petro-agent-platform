# web/ —— 前端（React18 + antd5 + Vite）

由 `teach-petro-agent/prototype/app` fork 改造而来（ADR-0007），底座五件按
`teach-petro-agent/specs/frontend-foundation.md` 落地（P0-06）。

## 双树共存（frontend-foundation §4）

- 落地树（真 API，全部走 `src/api/client.js`）：`#/D1 …`——按阶段点亮（`src/landing/registry.js`）；
- 原型树（mock，数据自包含，fork 快照零搬迁）：`#/proto/A1 …`——菜单常显带「原型」角标；
- 同一 shell 同一菜单，点菜单即切树对比；全部阶段验收后原型树整体删除。

**侧栏组织模式＝原样**（落地项与原型项同组并列）：双树对照是刻意设计，不因视觉改造而改组织。
视觉改造只动样式——原型项整体降一级文字色（`menu-proto`）、角标 10px→12px、窄屏侧栏可折叠、
颜色走令牌。

## 底座五件落位

| 件 | 路径 | 说明 |
|---|---|---|
| 请求层 | `src/api/client.js` | fetch 封装（不引 axios）：API_BASE 默认 `/api`（dev 走 vite proxy → FastAPI :8000）、X-Dev-User 身份桩头（默认 aqiang，localStorage `petro.dev-user` 可改）、统一错误包解包（00 册 §3 → antd message＋抛 ApiError）、分页信封解包（00 册 §4）、`useTaskPolling`（00 册 §5，11 处任务先例同构） |
| SSE 客户端 | `src/api/sse.js` | 原生 EventSource 封装：帧分发、`done/error/replay_truncated` 三帧语义、Last-Event-ID 续传接线说明（P0-06 骨架＋单测桩，不接 A1） |
| 全局态 | `src/store/app.js` | zustand 三槽：当前角色（接 roles.js）/ 语义版本徽标（占位）/ 会话列表缓存（A1 预留） |
| 组件库 | `src/components/` | 首批：四态徽标 StateBadge（过/拦下/不涉及/未跑，C3 合同）、产物卡骨架 ArtifactCard（A1 端点 7/8 DTO） |
| 工程形态 | `vite.config.js` / `eslint.config.js` | 去 singlefile 正常 dev/build＋`/api` proxy；eslint（含 react-hooks）进 CI（`.github/workflows/ci.yml` frontend job） |

## 命令

```bash
npm install     # 安装依赖
npm run dev     # vite dev :5173（/api 代理到 :8000，需后端先起）
npm run lint    # eslint
npm test        # vitest（api/client + api/sse）
npm run build   # 产物出 dist/（不进 git）
```

fork 与底座施工见 tickets/phase0/README.md 的 P0-06 节。
