# L5 · 02 · 去年日产液量最高的井是哪口、合计多少方？另外完井报告里 W-11 井 12mm 油嘴的折算日产油是多少？

- 生成时刻：`2026-10-16T23:50:26`（`scripts/ladder_run.py`）
- 层级／序号：`L5` / `02`
- 题面：去年日产液量最高的井是哪口、合计多少方？另外完井报告里 W-11 井 12mm 油嘴的折算日产油是多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-b7f405d0`
- verdict(final)：`completed`（run_id=run-b7f405d0，manifest_digest=0d42c21d3deeb1b4）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 12 | 0 | 12 |
| `done` | 1 | 0 | 1 |
| `notice` | 2 | 0 | 2 |
| `observation` | 27 | 0 | 27 |
| `session` | 1 | 0 | 1 |
| `step` | 14 | 0 | 14 |
| `text` | 9 | 0 | 9 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 71 | 0 | 71 |

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
| 1 | 2026-10-16T23:50:00 | `understand` | 2 | 2721 | 0 | 2071 | None |
| 2 | 2026-10-16T23:50:03 | `decision` | 4 | 8416 | 0 | 3065 | None |
| 3 | 2026-10-16T23:50:07 | `decision` | 6 | 8926 | 0 | 3167 | None |
| 4 | 2026-10-16T23:50:13 | `decision` | 8 | 14303 | 0 | 5837 | None |
| 5 | 2026-10-16T23:50:26 | `answer` | 10 | 21659 | 0 | 11311 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1、s2

notice 帧：

- `id=50` `unsupported_claim`：核验步改写无据断言 6 行（INV-1——禁止无据断言进答案）
- `id=51` `attribution_split`：跨源归属审（V2-50）：答案被引检索片段 [5]、[18]、[26] 的引标源与题眼锚（W-11）不一致——答案面分源列明（跨源引用按出处如实区分）

## ask 帧

（无 ask 帧）

## 归档文件

- `02-去年日产液量最高的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/02-去年日产液量最高的井是哪.sse`
- `02-去年日产液量最高的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/02-去年日产液量最高的井是哪-last-context.json`
- `02-去年日产液量最高的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/02-去年日产液量最高的井是哪-summary.md`
