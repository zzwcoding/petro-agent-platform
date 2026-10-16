# L4 · 02 · 今年各井的日产液量按天列出来

- 生成时刻：`2026-10-16T23:47:04`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `02`
- 题面：今年各井的日产液量按天列出来
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-f866c567`
- verdict(final)：`completed`（run_id=run-f866c567，manifest_digest=84209f78ffdc773b）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 52 | 0 | 52 |
| `done` | 1 | 0 | 1 |
| `notice` | 2 | 0 | 2 |
| `observation` | 52 | 0 | 52 |
| `session` | 1 | 0 | 1 |
| `step` | 12 | 0 | 12 |
| `text` | 8 | 0 | 8 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 132 | 0 | 132 |

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
| 1 | 2026-10-16T23:46:42 | `understand` | 2 | 2672 | 0 | 1600 | None |
| 2 | 2026-10-16T23:46:45 | `decision` | 4 | 8297 | 0 | 2134 | None |
| 3 | 2026-10-16T23:46:47 | `decision` | 6 | 8600 | 0 | 1963 | None |
| 4 | 2026-10-16T23:46:49 | `decision` | 8 | 13801 | 0 | 2089 | None |
| 5 | 2026-10-16T23:47:03 | `answer` | 10 | 17396 | 0 | 13765 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=7` `decision_note`：前置条件机：子问题 s1 放行（注记 1 条）——窗上沿 2026-10-16 晚于汇总层水位 2026-08-31——引擎新鲜度闸将拦停/改绑并注记（照实判定）
- `id=72` `unsupported_claim`：核验步改写无据断言 3 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `02-今年各井的日产液量按天列.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/02-今年各井的日产液量按天列.sse`
- `02-今年各井的日产液量按天列-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/02-今年各井的日产液量按天列-last-context.json`
- `02-今年各井的日产液量按天列-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/02-今年各井的日产液量按天列-summary.md`
