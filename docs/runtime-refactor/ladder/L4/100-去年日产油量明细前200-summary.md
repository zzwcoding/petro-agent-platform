# L4 · 100 · 去年日产油量明细前 200 行

- 生成时刻：`2026-10-17T02:07:32`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `100`
- 题面：去年日产油量明细前 200 行
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-561d5d00`
- verdict(final)：`completed`（run_id=run-561d5d00，manifest_digest=dc83d52d4919a278）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- 覆盖范围：首段 426 帧（合计 426 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 200 | 0 | 200 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 201 | 0 | 201 |
| `session` | 1 | 0 | 1 |
| `step` | 12 | 0 | 12 |
| `text` | 6 | 0 | 6 |
| `tool` | 1 | 0 | 1 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 426 | 0 | 426 |

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
| 1 | 2026-10-17T02:07:06 | `understand` | 2 | 2668 | 0 | 1890 | None |
| 2 | 2026-10-17T02:07:08 | `decision` | 4 | 8358 | 0 | 1768 | None |
| 3 | 2026-10-17T02:07:10 | `decision` | 6 | 8739 | 0 | 1568 | None |
| 4 | 2026-10-17T02:07:12 | `decision` | 8 | 9666 | 0 | 1899 | None |
| 5 | 2026-10-17T02:07:32 | `answer` | 10 | 20275 | 0 | 19188 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 10

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=218` `unsupported_claim`：核验步改写无据断言 7 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `100-去年日产油量明细前200.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量明细前200.sse`
- `100-去年日产油量明细前200-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量明细前200-last-context.json`
- `100-去年日产油量明细前200-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-去年日产油量明细前200-summary.md`
