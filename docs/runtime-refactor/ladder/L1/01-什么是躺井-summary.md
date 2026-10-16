# L1 · 01 · 什么是躺井？

- 生成时刻：`2026-10-16T21:47:21`（`scripts/ladder_run.py`）
- 层级／序号：`L1` / `01`
- 题面：什么是躺井？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-9d749759`
- verdict(final)：`completed`（run_id=run-9d749759，manifest_digest=671fe66b93c96d25）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `observation` | 1 | 0 | 1 |
| `session` | 1 | 0 | 1 |
| `step` | 10 | 0 | 10 |
| `text` | 2 | 0 | 2 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 20 | 0 | 20 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 3/3 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `answer` | 6 | 8 | 6 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 4 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T21:47:14 | `understand` | 2 | 2657 | 0 | 2077 | None |
| 2 | 2026-10-16T21:47:17 | `decision` | 4 | 8204 | 0 | 1881 | None |
| 3 | 2026-10-16T21:47:19 | `decision` | 6 | 8261 | 0 | 1645 | None |
| 4 | 2026-10-16T21:47:21 | `answer` | 8 | 8995 | 0 | 1985 | None |

caller×次数：`decision`×2、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

（无）

## ask 帧

（无 ask 帧）

## 归档文件

- `01-什么是躺井.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L1/01-什么是躺井.sse`
- `01-什么是躺井-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L1/01-什么是躺井-last-context.json`
- `01-什么是躺井-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L1/01-什么是躺井-summary.md`
