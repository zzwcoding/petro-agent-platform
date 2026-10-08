# V2-15 · teach 原型 V2 问一问页（任务 3——落点裁决：teach 仓真源）

状态: done（2026-10-09，P-019 验收通过·teach 仓待 Owner 合入拍板）
Touches modules: （teach-petro-agent/prototype/app——非本仓；AGENTS.md 硬纪律 0：页面真源）
阻塞: 无（与 V2-14 可并行）｜被阻塞: V2-16 web 对接

## 落点裁决（L0，票面生效）

任务 3 原型**落 teach-petro-agent 仓**（teach-petro-agent/prototype/app）——硬纪律 0：
页面讨论与改版只动 teach 原型真源，本仓 web/src 待阶段同步。执行子代理跨仓绝对路径作业。

## 任务

复制 V1 问一问原型页，改 V2 版：**思考过程与决策树逐一对话重新核对当前实现逻辑并展示**——
即 loop 六步（understand/plan/tool/observe/verify/answer）逐步可见，
每步展示"模型此刻看到了什么（Manifest 摘要）/调了什么工具/观察结果/核验结论"。
开工前必须核对真源：appv2/api/wire.py 事件枚举＋appv2/runtime step 类型＋
tests/api/test_v2_asks.py 帧实例（禁止凭想象画 V1 旧瀑布）。

## 验收: 以下逐条——

- V2 页以真实 wire 事件为准：六类 step＋ask 帧交互（澄清三选一/审批）＋verdict subtype
- 决策树逐节点有真实实现出处注记（file:line 或 spec 节）
- V1 页原样保留（V2 页新路由并列）
- 样张数据：用 P-009 冒烟两题的真实帧形态（六步恰序）做页面 fixtures

回报: results/P-015.dev.md（teach 仓 commit SHA＋逐节点实现出处对照表）。
