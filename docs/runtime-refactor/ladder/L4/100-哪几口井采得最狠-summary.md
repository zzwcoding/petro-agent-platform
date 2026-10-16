# L4 · 100 · 哪几口井采得最狠？

- 生成时刻：`2026-10-17T02:07:04`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `100`
- 题面：哪几口井采得最狠？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-d49614d0`
- verdict(final)：`completed`（run_id=run-d49614d0，manifest_digest=d35d2d042905a246）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- 覆盖范围：首段 84 帧（合计 84 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 11 | 0 | 11 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 51 | 0 | 51 |
| `session` | 1 | 0 | 1 |
| `step` | 10 | 0 | 10 |
| `text` | 5 | 0 | 5 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 84 | 0 | 84 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 3/3 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `answer` | 6 | 8 | 6 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；按 run_id 命中 4 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T02:06:57 | `understand` | 2 | 2667 | 0 | 1215 | None |
| 2 | 2026-10-17T02:06:59 | `decision` | 4 | 8376 | 0 | 1375 | None |
| 3 | 2026-10-17T02:07:00 | `decision` | 6 | 9324 | 0 | 1360 | None |
| 4 | 2026-10-17T02:07:04 | `answer` | 8 | 12550 | 0 | 2657 | None |

caller×次数：`decision`×2、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

notice 帧：

- `id=65` `unsupported_claim`：核验步改写无据断言 1 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `100-哪几口井采得最狠.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-哪几口井采得最狠.sse`
- `100-哪几口井采得最狠-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-哪几口井采得最狠-last-context.json`
- `100-哪几口井采得最狠-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-哪几口井采得最狠-summary.md`
