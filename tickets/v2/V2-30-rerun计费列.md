# V2-30 · rerun 计费列＋gold 基线行（Q12 欠账清偿）

状态: 实现中（2026-10-09，P-025 已派发）
Touches modules: （eval 工具链——eval/results/tools/）
阻塞: 无｜被阻塞: 无

## 任务

1. rerun.py 采集 spend：跑批后按 run_id 从网关 spend 账本（PG gateway_spend_record）
   归集计费（jsonl 增 spend 字段或独立计费摘要文件）——Q12 挂账 5 清偿
2. gold README 增 V2 首个全量基线行（Q12-V2：✅10/⚠️39/❌48/742s/0.207 元）＋
   "Q13 为 ReAct 重构后首个复测基线"注记——Q12 挂账 4（L0 已拍板）

## 验收: 以下逐条——

- 干跑 2 题计费归集实证（与 spend 账本逐笔对得上）
- README 基线行落字＋防拟合协议不动

回报: results/P-025.dev.md。
