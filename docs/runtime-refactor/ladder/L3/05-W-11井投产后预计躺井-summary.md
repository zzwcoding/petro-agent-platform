# L3 · 05 · W-11 井投产后预计躺井率是多少？

- 生成时刻：`2026-10-16T23:44:05`（`scripts/ladder_run.py`）
- 层级／序号：`L3` / `05`
- 题面：W-11 井投产后预计躺井率是多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-e1b6ff1e`
- verdict(final)：`waiting_ask`（run_id=run-e1b6ff1e，manifest_digest=de6ea3af312256b1）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- **状态：待用户选择**（流内出现 `ask` 帧且未传 `--choice`，归档含首段为止）

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `ask` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 2 | 0 | 2 |
| `session` | 1 | 0 | 1 |
| `step` | 10 | 0 | 10 |
| `text` | 1 | 0 | 1 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 20 | 0 | 20 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 3/3 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 4 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T23:43:58 | `understand` | 2 | 2675 | 0 | 1360 | None |
| 2 | 2026-10-16T23:44:00 | `decision` | 4 | 8293 | 0 | 1332 | None |
| 3 | 2026-10-16T23:44:02 | `decision` | 6 | 8356 | 0 | 1645 | None |
| 4 | 2026-10-16T23:44:05 | `decision` | 8 | 8415 | 0 | 2354 | None |

caller×次数：`decision`×3、`understand`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

notice 帧：

- `id=1` `unsupported_claim`：理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。

## ask 帧

- 帧位：`id=14`（首段）

```json
{
  "frame": {
    "kind": "clarify",
    "prompt": "W-11 井在系统井主数据中未命中。需要您确认或补充：",
    "options": [
      "W-11 实际是另一口井号（如 W-11H、W-11S、W-011 等），我确认后重查",
      "W-11 属于哪个油田/区块，我提供后系统按该区块查询",
      "W-11 是新井尚未投产，躺井率为投产方案/设计文档里的预测值——请告知报告名（如《XX 油田开发方案》）",
      "W-11 不在本系统数据范围内，撤回此问"
    ],
    "detail": {}
  },
  "run_id": "run-e1b6ff1e"
}
```

## 归档文件

- `05-W-11井投产后预计躺井.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/05-W-11井投产后预计躺井.sse`
- `05-W-11井投产后预计躺井-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/05-W-11井投产后预计躺井-last-context.json`
- `05-W-11井投产后预计躺井-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/05-W-11井投产后预计躺井-summary.md`
