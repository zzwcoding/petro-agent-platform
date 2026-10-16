# L2 · 04 · 最近各井日产油量怎么样？

- 生成时刻：`2026-10-16T21:49:52`（`scripts/ladder_run.py`）
- 层级／序号：`L2` / `04`
- 题面：最近各井日产油量怎么样？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-72926401`
- verdict(final)：`failed`（run_id=run-72926401，manifest_digest=a5c78cdf51d1b16d）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `session` | 1 | 0 | 1 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 5 | 0 | 5 |

## 前缀延伸报告（KV 纪律验收线）

调用链不足两条，无法判定前缀延伸

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 1 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T21:49:52 | `understand` | 2 | 2665 | 0 | 1240 | None |

caller×次数：`understand`×1

链长增长：2

## 拒因与 notice

notice 帧：

- `id=0` `run_failed`：run 执行失败：读题应答不合 schema（非合法 JSON／缺必填字段／字段类型不符／route 越界闭世界 {"full","direct"}）——不猜、不取默认、不降级（原始应答片段：{"route":"full","text":"理解：问最近各井的日产油量怎么样。\n指标候选：日产油量"}）

## ask 帧

（无 ask 帧）

## 归档文件

- `04-最近各井日产油量怎么样.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/04-最近各井日产油量怎么样.sse`
- `04-最近各井日产油量怎么样-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/04-最近各井日产油量怎么样-last-context.json`
- `04-最近各井日产油量怎么样-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/04-最近各井日产油量怎么样-summary.md`
