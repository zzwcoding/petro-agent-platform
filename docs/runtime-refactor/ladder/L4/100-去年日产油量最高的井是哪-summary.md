# L4 · 100 · 去年日产油量最高的井是哪口？

- 生成时刻：`2026-10-17T03:06:16`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `100`
- 题面：去年日产油量最高的井是哪口？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-4ac83fe0`
- verdict(final)：`completed`（run_id=run-4ac83fe0，manifest_digest=dd1761da6f5f3fe7）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- 覆盖范围：首段 79 帧（合计 79 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 6 | 0 | 6 |
| `done` | 1 | 0 | 1 |
| `observation` | 51 | 0 | 51 |
| `session` | 1 | 0 | 1 |
| `step` | 12 | 0 | 12 |
| `text` | 4 | 0 | 4 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 79 | 0 | 79 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 4/4 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `answer` | 8 | 10 | 8 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；按 run_id 命中 5 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T03:06:09 | `understand` | 2 | 2667 | 0 | 1160 | None |
| 2 | 2026-10-17T03:06:11 | `decision` | 4 | 8350 | 0 | 1392 | None |
| 3 | 2026-10-17T03:06:12 | `decision` | 6 | 8698 | 0 | 1134 | None |
| 4 | 2026-10-17T03:06:13 | `decision` | 8 | 9611 | 0 | 1430 | None |
| 5 | 2026-10-17T03:06:16 | `answer` | 10 | 12675 | 0 | 1912 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

## ask 帧

（无 ask 帧）

## 归档文件

- `100-去年日产油量最高的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量最高的井是哪.sse`
- `100-去年日产油量最高的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量最高的井是哪-last-context.json`
- `100-去年日产油量最高的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量最高的井是哪-summary.md`
