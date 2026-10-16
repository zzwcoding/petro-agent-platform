# L3 · 07 · 完井液在二开钻进段与三开完井段的密度各是多少？与设计值差多少？

- 生成时刻：`2026-10-17T01:33:16`（`scripts/ladder_run.py`）
- 层级／序号：`L3` / `07`
- 题面：完井液在二开钻进段与三开完井段的密度各是多少？与设计值差多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-919ed881`
- verdict(final)：`completed`（run_id=run-919ed881，manifest_digest=c0831bdfcb4867a7）
- 首段：`07-完井液在二开钻进段与三开.sse` 解析重建（77 帧）
- 续段（resume）：未发起
- 覆盖范围：首段 77 帧（合计 77 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

> 本摘要由 `--resummarize` 从归档 SSE 重建（不重跑题）：`07-完井液在二开钻进段与三开.sse`

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 10 | 0 | 10 |
| `done` | 1 | 0 | 1 |
| `notice` | 3 | 0 | 3 |
| `observation` | 39 | 0 | 39 |
| `session` | 1 | 0 | 1 |
| `step` | 13 | 0 | 13 |
| `text` | 5 | 0 | 5 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 77 | 0 | 77 |

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
| 1 | 2026-10-17T01:14:05 | `understand` | 2 | 2697 | 0 | 2016 | None |
| 2 | 2026-10-17T01:14:08 | `decision` | 4 | 8443 | 0 | 2465 | None |
| 3 | 2026-10-17T01:14:10 | `decision` | 6 | 13805 | 0 | 2616 | None |
| 4 | 2026-10-17T01:14:19 | `answer` | 8 | 19359 | 0 | 6607 | None |

caller×次数：`decision`×2、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

notice 帧：

- `id=1` `unsupported_claim`：理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。
- `id=56` `material_truncated`：答案视野检索片段仅渲染 24/37 支（权威行集与台账卡已全量）——未渲染部分不作答（V2-61）。
- `id=59` `unsupported_claim`：核验步改写无据断言 3 行（INV-1——禁止无据断言进答案）

## ask 帧

（无 ask 帧）

## 归档文件

- `07-完井液在二开钻进段与三开.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/07-完井液在二开钻进段与三开.sse`
- `07-完井液在二开钻进段与三开-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/07-完井液在二开钻进段与三开-last-context.json`
- `07-完井液在二开钻进段与三开-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/07-完井液在二开钻进段与三开-summary.md`
