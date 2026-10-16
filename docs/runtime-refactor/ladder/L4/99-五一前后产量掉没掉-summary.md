# L4 · 99 · 五一前后产量掉没掉？

- 生成时刻：`2026-10-16T23:47:55`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `99`
- 题面：五一前后产量掉没掉？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-d6e48a06`
- verdict(final)：`completed`（run_id=run-d6e48a06，manifest_digest=64f7023e547a6a3d）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 2 | 0 | 2 |
| `done` | 1 | 0 | 1 |
| `observation` | 2 | 0 | 2 |
| `session` | 1 | 0 | 1 |
| `step` | 14 | 0 | 14 |
| `text` | 3 | 0 | 3 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 27 | 0 | 27 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 5/5 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `decision` | 8 | 10 | 8 | ✅ 前缀延伸 |
| 6 | `answer` | 10 | 12 | 10 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 6 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T23:47:39 | `understand` | 2 | 2663 | 0 | 6453 | None |
| 2 | 2026-10-16T23:47:42 | `decision` | 4 | 8258 | 0 | 2507 | None |
| 3 | 2026-10-16T23:47:44 | `decision` | 6 | 8615 | 0 | 2606 | None |
| 4 | 2026-10-16T23:47:47 | `decision` | 8 | 8969 | 0 | 2258 | None |
| 5 | 2026-10-16T23:47:49 | `decision` | 10 | 14157 | 0 | 2402 | None |
| 6 | 2026-10-16T23:47:54 | `answer` | 12 | 15361 | 0 | 4156 | None |

caller×次数：`decision`×4、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10 → 12

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1
- `id=5` 澄清 r2 被拒：ledger_notes 槽位对账未过：s1

## ask 帧

（无 ask 帧）

## 归档文件

- `99-五一前后产量掉没掉.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/99-五一前后产量掉没掉.sse`
- `99-五一前后产量掉没掉-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/99-五一前后产量掉没掉-last-context.json`
- `99-五一前后产量掉没掉-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/99-五一前后产量掉没掉-summary.md`
