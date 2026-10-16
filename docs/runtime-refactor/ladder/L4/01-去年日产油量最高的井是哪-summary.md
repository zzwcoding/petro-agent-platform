# L4 · 01 · 去年日产油量最高的井是哪口？

- 生成时刻：`2026-10-16T23:46:05`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `01`
- 题面：去年日产油量最高的井是哪口？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-4afff90a`
- verdict(final)：`completed`（run_id=run-4afff90a，manifest_digest=99c952edce44a348）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 10 | 0 | 10 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 51 | 0 | 51 |
| `session` | 1 | 0 | 1 |
| `step` | 12 | 0 | 12 |
| `text` | 3 | 0 | 3 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 83 | 0 | 83 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 4/4 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `answer` | 8 | 10 | 8 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 5 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T23:45:57 | `understand` | 2 | 2667 | 0 | 1161 | None |
| 2 | 2026-10-16T23:45:58 | `decision` | 4 | 8290 | 0 | 1606 | None |
| 3 | 2026-10-16T23:46:00 | `decision` | 6 | 8653 | 0 | 1609 | None |
| 4 | 2026-10-16T23:46:02 | `decision` | 8 | 13888 | 0 | 1573 | None |
| 5 | 2026-10-16T23:46:05 | `answer` | 10 | 17118 | 0 | 2163 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=65` `unsupported_claim`：核验步改写无据断言 1 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `01-去年日产油量最高的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/01-去年日产油量最高的井是哪.sse`
- `01-去年日产油量最高的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/01-去年日产油量最高的井是哪-last-context.json`
- `01-去年日产油量最高的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/01-去年日产油量最高的井是哪-summary.md`
