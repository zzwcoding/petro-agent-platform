# L4 · 100 · 上月检泵周期最长的井是哪口？

- 生成时刻：`2026-10-17T15:34:38`（`scripts/ladder_run.py`）
- 层级／序号：`L4` / `100`
- 题面：上月检泵周期最长的井是哪口？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-12aee7ec`
- verdict(final)：`completed`（run_id=run-12aee7ec，manifest_digest=3c12f7651438f59c）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起
- 覆盖范围：首段 50 帧（合计 50 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `citation` | 3 | 0 | 3 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `observation` | 18 | 0 | 18 |
| `session` | 1 | 0 | 1 |
| `step` | 13 | 0 | 13 |
| `supplement` | 2 | 0 | 2 |
| `text` | 6 | 0 | 6 |
| `tool` | 2 | 0 | 2 |
| `verdict` | 2 | 0 | 2 |
| **合计** | 50 | 0 | 50 |

## 前缀延伸报告（KV 纪律验收线）

⚠️ 存在非前缀延伸（4 对中含断裂——KV 纪律验收线不达标）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 4 | — | 起始调用 |
| 2 | `decision` | 4 | 6 | 0 | ⚠️ 非前缀延伸（KV 失效） |
| 3 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 4 | `decision` | 8 | 10 | 0 | ⚠️ 非前缀延伸（KV 失效） |
| 5 | `answer` | 10 | 12 | 0 | ⚠️ 非前缀延伸（KV 失效） |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；按 run_id 命中 5 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T15:34:26 | `understand` | 4 | 2789 | 0 | 1883 | None |
| 2 | 2026-10-17T15:34:29 | `decision` | 6 | 7370 | 0 | 2852 | None |
| 3 | 2026-10-17T15:34:31 | `decision` | 8 | 7428 | 0 | 1664 | None |
| 4 | 2026-10-17T15:34:33 | `decision` | 10 | 7312 | 0 | 1673 | None |
| 5 | 2026-10-17T15:34:38 | `answer` | 12 | 11889 | 0 | 3834 | None |

caller×次数：`decision`×3、`understand`×1、`answer`×1

链长增长：4 → 6 → 8 → 10 → 12

## 拒因与 notice

notice 帧：

- `id=37` `unsupported_claim`：核验步删去无据断言 3 行（EB3 D3：真无据断言删句、不贴前缀——禁止无据断言进答案；留痕＝rewrites 逐行原句 ＋ 本计数）

## ask 帧

（无 ask 帧）

## 归档文件

- `100-上月检泵周期最长的井是哪.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-上月检泵周期最长的井是哪.sse`
- `100-上月检泵周期最长的井是哪-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-上月检泵周期最长的井是哪-last-context.json`
- `100-上月检泵周期最长的井是哪-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L4/100-上月检泵周期最长的井是哪-summary.md`
