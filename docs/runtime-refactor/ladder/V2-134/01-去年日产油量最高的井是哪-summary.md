# V2-134 · 01 · 去年日产油量最高的井是哪口、合计多少？

- 生成时刻：`2026-10-19T12:12:55`（`scripts/ladder_run.py`）
- 层级／序号：`V2-134` / `01`
- 题面：去年日产油量最高的井是哪口、合计多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-39cd99dd`
- verdict(final)：`completed`（run_id=run-39cd99dd，manifest_digest=ad0cb857c1852b47）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- 覆盖范围：首段 82 帧（合计 82 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 2 | 0 | 2 |
| `done` | 1 | 0 | 1 |
| `observation` | 53 | 0 | 53 |
| `session` | 1 | 0 | 1 |
| `step` | 14 | 0 | 14 |
| `supplement` | 3 | 0 | 3 |
| `text` | 3 | 0 | 3 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 82 | 0 | 82 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 4/4 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 3 | — | 起始调用 |
| 2 | `decision` | 3 | 5 | 3 | ✅ 前缀延伸 |
| 3 | `decision` | 5 | 7 | 5 | ✅ 前缀延伸 |
| 4 | `decision` | 7 | 9 | 7 | ✅ 前缀延伸 |
| 5 | `answer` | 9 | 11 | 9 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 7 个 jsonl，排除 `*.baseline`；按 run_id 命中 5 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-19T12:12:42 | `understand` | 3 | 2471 | 0 | 2116 | None |
| 2 | 2026-10-19T12:12:45 | `decision` | 5 | 8340 | 0 | 2461 | None |
| 3 | 2026-10-19T12:12:47 | `decision` | 7 | 8991 | 0 | 2493 | None |
| 4 | 2026-10-19T12:12:50 | `decision` | 9 | 10071 | 0 | 2385 | None |
| 5 | 2026-10-19T12:12:55 | `answer` | 11 | 14621 | 0 | 3586 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：3 → 5 → 7 → 9 → 11

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1、s2

## ask 帧

（无 ask 帧）

## 归档文件

- `01-去年日产油量最高的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/V2-134/01-去年日产油量最高的井是哪.sse`
- `01-去年日产油量最高的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/V2-134/01-去年日产油量最高的井是哪-last-context.json`
- `01-去年日产油量最高的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/V2-134/01-去年日产油量最高的井是哪-summary.md`
