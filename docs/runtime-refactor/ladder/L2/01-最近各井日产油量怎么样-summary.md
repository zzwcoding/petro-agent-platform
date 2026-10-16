# L2 · 01 · 最近各井日产油量怎么样？

- 生成时刻：`2026-10-16T21:47:47`（`scripts/ladder_run.py`）
- 层级／序号：`L2` / `01`
- 题面：最近各井日产油量怎么样？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-aa203033`
- verdict(final)：`waiting_ask`（run_id=run-aa203033，manifest_digest=cf82e12bf9640e0b）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- **状态：待用户选择**（流内出现 `ask` 帧且未传 `--choice`，归档含首段为止）

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `ask` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `session` | 1 | 0 | 1 |
| `step` | 7 | 0 | 7 |
| `text` | 1 | 0 | 1 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 12 | 0 | 12 |

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
| 1 | 2026-10-16T21:47:41 | `understand` | 2 | 2665 | 0 | 1150 | None |
| 2 | 2026-10-16T21:47:43 | `decision` | 4 | 8219 | 0 | 1732 | None |
| 3 | 2026-10-16T21:47:45 | `decision` | 6 | 8537 | 0 | 1324 | None |
| 4 | 2026-10-16T21:47:47 | `decision` | 8 | 8868 | 0 | 1698 | None |

caller×次数：`decision`×3、`understand`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1
- `id=5` 澄清 r2 被拒：ledger_notes 槽位对账未过：s1

## ask 帧

- 帧位：`id=6`（首段 段）

```json
{
  "frame": {
    "kind": "clarify",
    "prompt": "「最近」未给出具体时间范围，请问按哪个时间窗取日产油量？",
    "options": [
      "近 7 天（2026-10-09 至 2026-10-16）",
      "近 30 天（2026-09-16 至 2026-10-16）",
      "上月（2026-09-01 至 2026-09-30）"
    ],
    "detail": {}
  },
  "run_id": "run-aa203033"
}
```

## 归档文件

- `01-最近各井日产油量怎么样.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/01-最近各井日产油量怎么样.sse`
- `01-最近各井日产油量怎么样-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/01-最近各井日产油量怎么样-last-context.json`
- `01-最近各井日产油量怎么样-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/01-最近各井日产油量怎么样-summary.md`
