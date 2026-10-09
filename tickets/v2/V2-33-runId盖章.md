# V2-33 · 服务侧 run_id 盖章（spend 账本归属链补环）

状态: open
Touches modules: `infra`
阻塞: 无｜被阻塞: 无（暗债不挡路但越拖越脏）

## 任务

P-025 实测：gateway spend 账本 run_id 列 0/3095 行有值——`GatewayService.complete/_settle`
记账时不落 run_id（调用面有 request/run 语境可传）。补环：调用面（GraphRunExecutor 经
completer 协议）携 run_id → _settle 写账；账本既有列零迁移。工具侧时间窗归集退役为
兜底（留双跑一段防回归）。

## 验收: 以下逐条——

- RUNTIME_SMOKE 后账本新行 run_id 逐笔非空（与 jsonl run_id 全等）
- rerun --spend 归集改用 run_id 直查（时间窗法保留为 fallback 注记）
- 既有测试零回退

回报: results/P-027.dev.md。
