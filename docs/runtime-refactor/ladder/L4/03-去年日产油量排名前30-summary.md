# L4 · 03 · 去年日产油量排名前 30

- 生成时刻：`2026-10-16T23:47:18`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `03`
- 题面：去年日产油量排名前 30
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-1dbb3a7b`
- verdict(final)：`completed`（run_id=run-1dbb3a7b，manifest_digest=45d81ef6d323ec74）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 31 | 0 | 31 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 31 | 0 | 31 |
| `session` | 1 | 0 | 1 |
| `step` | 13 | 0 | 13 |
| `text` | 4 | 0 | 4 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 86 | 0 | 86 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 5/5 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `understand` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `decision` | 8 | 10 | 8 | ✅ 前缀延伸 |
| 6 | `answer` | 10 | 12 | 10 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 6 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T23:47:05 | `understand` | 2 | 2664 | 0 | 1168 | None |
| 2 | 2026-10-16T23:47:06 | `understand` | 4 | 2837 | 0 | 1149 | None |
| 3 | 2026-10-16T23:47:08 | `decision` | 6 | 8441 | 0 | 1692 | None |
| 4 | 2026-10-16T23:47:10 | `decision` | 8 | 8778 | 0 | 1667 | None |
| 5 | 2026-10-16T23:47:12 | `decision` | 10 | 14003 | 0 | 1895 | None |
| 6 | 2026-10-16T23:47:18 | `answer` | 12 | 16469 | 0 | 5221 | None |

caller×次数：`decision`×3、`understand`×2、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10 → 12

## 拒因与 notice

被拒步记录：

- `id=4` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=47` `unsupported_claim`：核验步改写无据断言 6 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `03-去年日产油量排名前30.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/03-去年日产油量排名前30.sse`
- `03-去年日产油量排名前30-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/03-去年日产油量排名前30-last-context.json`
- `03-去年日产油量排名前30-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/03-去年日产油量排名前30-summary.md`
