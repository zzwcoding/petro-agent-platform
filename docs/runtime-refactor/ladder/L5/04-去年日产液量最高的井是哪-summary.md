# L5 · 04 · 去年日产液量最高的井是哪口、合计多少方？另外完井报告里 W-11 井 12mm 油嘴的折算日产油是多少？

- 生成时刻：`2026-10-17T01:15:31`（`scripts/ladder_run.py`）
- 层级／序号：`L5` / `04`
- 题面：去年日产液量最高的井是哪口、合计多少方？另外完井报告里 W-11 井 12mm 油嘴的折算日产油是多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-7cfa7e87`
- verdict(final)：`completed`（run_id=run-7cfa7e87，manifest_digest=34c1175bcfd226f6）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 5 | 0 | 5 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 76 | 0 | 76 |
| `session` | 1 | 0 | 1 |
| `step` | 12 | 0 | 12 |
| `text` | 5 | 0 | 5 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 106 | 0 | 106 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 3/3 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `answer` | 6 | 8 | 6 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；run 命中 4 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T01:15:19 | `understand` | 2 | 2721 | 0 | 2017 | None |
| 2 | 2026-10-17T01:15:22 | `decision` | 4 | 8508 | 0 | 2684 | None |
| 3 | 2026-10-17T01:15:25 | `decision` | 6 | 13890 | 0 | 2722 | None |
| 4 | 2026-10-17T01:15:31 | `answer` | 8 | 22436 | 0 | 4227 | None |

caller×次数：`decision`×2、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

notice 帧：

- `id=93` `unsupported_claim`：核验步改写无据断言 1 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `04-去年日产液量最高的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/04-去年日产液量最高的井是哪.sse`
- `04-去年日产液量最高的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/04-去年日产液量最高的井是哪-last-context.json`
- `04-去年日产液量最高的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L5/04-去年日产液量最高的井是哪-summary.md`
