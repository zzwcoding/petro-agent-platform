# L0 · 01 · asdkfjqwqe

- 生成时刻：`2026-10-16T21:58:08`（`scripts/ladder_run.py`）
- 层级／序号：`L0` / `01`
- 题面：asdkfjqwqe
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-0c241f75`
- verdict(final)：`completed`（run_id=run-0c241f75，manifest_digest=a4df397e7ee007df）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `session` | 1 | 0 | 1 |
| `step` | 2 | 0 | 2 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 6 | 0 | 6 |

## 前缀延伸报告（KV 纪律验收线）

调用链不足两条，无法判定前缀延伸

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 1 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T21:58:07 | `understand` | 2 | 2660 | 0 | 3890 | None |

caller×次数：`understand`×1

链长增长：2

## 拒因与 notice

（无）

## ask 帧

（无 ask 帧）

## 归档文件

- `01-asdkfjqwqe.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L0/01-asdkfjqwqe.sse`
- `01-asdkfjqwqe-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L0/01-asdkfjqwqe-last-context.json`
- `01-asdkfjqwqe-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L0/01-asdkfjqwqe-summary.md`
