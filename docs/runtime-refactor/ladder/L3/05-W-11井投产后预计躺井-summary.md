# L3 · 05 · W-11 井投产后预计躺井率是多少？

- 生成时刻：`2026-10-17T01:34:04`（`scripts/ladder_run.py`）
- 层级／序号：`L3` / `05`
- 题面：W-11 井投产后预计躺井率是多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-e1b6ff1e`
- verdict(final)：`completed`（run_id=run-e1b6ff1e，manifest_digest=fb9cb1d878c8d7ea）
- 首段：`05-W-11井投产后预计躺井.sse` 解析重建（20 帧）
- 续段（resume）：`05-W-11井投产后预计躺井-resume.sse` 解析重建（26 帧）
- 用户选择（自续段 `step` 帧回读）：W-11 属于渤中 34-5 油田，请按该油田查询
- 覆盖范围：首段 20 帧 ＋ 续段 26 帧（合计 46 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段 ✅ `done`

> 本摘要由 `--resummarize` 从归档 SSE 重建（不重跑题）：`05-W-11井投产后预计躺井-resume.sse`

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `ask` | 1 | 0 | 1 |
| `blackbox` | 0 | 1 | 1 |
| `done` | 1 | 1 | 2 |
| `notice` | 1 | 1 | 2 |
| `observation` | 2 | 2 | 4 |
| `session` | 1 | 1 | 2 |
| `step` | 10 | 16 | 26 |
| `text` | 1 | 1 | 2 |
| `tool` | 2 | 2 | 4 |
| `verdict` | 1 | 1 | 2 |
| **合计** | 20 | 26 | 46 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 8/8 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `decision` | 8 | 11 | 8 | ✅ 前缀延伸 |
| 6 | `decision` | 11 | 13 | 11 | ✅ 前缀延伸 |
| 7 | `decision` | 13 | 15 | 13 | ✅ 前缀延伸 |
| 8 | `decision` | 15 | 17 | 15 | ✅ 前缀延伸 |
| 9 | `decision` | 17 | 19 | 17 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；按 run_id 命中 9 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T23:43:58 | `understand` | 2 | 2675 | 0 | 1360 | None |
| 2 | 2026-10-16T23:44:00 | `decision` | 4 | 8293 | 0 | 1332 | None |
| 3 | 2026-10-16T23:44:02 | `decision` | 6 | 8356 | 0 | 1645 | None |
| 4 | 2026-10-16T23:44:05 | `decision` | 8 | 8415 | 0 | 2354 | None |
| 5 | 2026-10-16T23:45:01 | `decision` | 11 | 8617 | 0 | 1370 | None |
| 6 | 2026-10-16T23:45:03 | `decision` | 13 | 8680 | 0 | 1420 | None |
| 7 | 2026-10-16T23:45:05 | `decision` | 15 | 8737 | 0 | 1572 | None |
| 8 | 2026-10-16T23:45:06 | `decision` | 17 | 8975 | 0 | 1314 | None |
| 9 | 2026-10-16T23:45:08 | `decision` | 19 | 9187 | 0 | 1265 | None |

caller×次数：`decision`×8、`understand`×1

链长增长：2 → 4 → 6 → 8 → 11 → 13 → 15 → 17 → 19

## 拒因与 notice

被拒步记录：

- `id=32` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1
- `id=34` 澄清 r2 被拒：ledger_notes 槽位对账未过：s1
- `id=36` 澄清 r3 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=1` `unsupported_claim`：理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。
- `id=37` `budget_converged`：预算触界收敛：rounds 已用 3／上限 3；未完成项：已取得材料 5 条尚未收口（材料清单：no_hit、no_hit、no_hit、no_hit、no_hit）

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
- `05-W-11井投产后预计躺井-resume.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/05-W-11井投产后预计躺井-resume.sse`
