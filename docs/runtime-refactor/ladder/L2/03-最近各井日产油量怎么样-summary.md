# L2 · 03 · 最近各井日产油量怎么样？

- 生成时刻：`2026-10-16T21:49:48`（`scripts/ladder_run.py`）
- 层级／序号：`L2` / `03`
- 题面：最近各井日产油量怎么样？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-52db7a6c`
- verdict(final)：`failed`（run_id=run-52db7a6c，manifest_digest=c4292fdcae3e97d4）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `notice` | 32 | 0 | 32 |
| `session` | 1 | 0 | 1 |
| `step` | 69 | 0 | 69 |
| `text` | 1 | 0 | 1 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 106 | 0 | 106 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 34/34 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `decision` | 8 | 10 | 8 | ✅ 前缀延伸 |
| 6 | `decision` | 10 | 11 | 10 | ✅ 前缀延伸 |
| 7 | `decision` | 11 | 12 | 11 | ✅ 前缀延伸 |
| 8 | `decision` | 12 | 13 | 12 | ✅ 前缀延伸 |
| 9 | `decision` | 13 | 14 | 13 | ✅ 前缀延伸 |
| 10 | `decision` | 14 | 15 | 14 | ✅ 前缀延伸 |
| 11 | `decision` | 15 | 16 | 15 | ✅ 前缀延伸 |
| 12 | `decision` | 16 | 17 | 16 | ✅ 前缀延伸 |
| 13 | `decision` | 17 | 18 | 17 | ✅ 前缀延伸 |
| 14 | `decision` | 18 | 19 | 18 | ✅ 前缀延伸 |
| 15 | `decision` | 19 | 20 | 19 | ✅ 前缀延伸 |
| 16 | `decision` | 20 | 21 | 20 | ✅ 前缀延伸 |
| 17 | `decision` | 21 | 22 | 21 | ✅ 前缀延伸 |
| 18 | `decision` | 22 | 23 | 22 | ✅ 前缀延伸 |
| 19 | `decision` | 23 | 24 | 23 | ✅ 前缀延伸 |
| 20 | `decision` | 24 | 25 | 24 | ✅ 前缀延伸 |
| 21 | `decision` | 25 | 26 | 25 | ✅ 前缀延伸 |
| 22 | `decision` | 26 | 27 | 26 | ✅ 前缀延伸 |
| 23 | `decision` | 27 | 28 | 27 | ✅ 前缀延伸 |
| 24 | `decision` | 28 | 29 | 28 | ✅ 前缀延伸 |
| 25 | `decision` | 29 | 30 | 29 | ✅ 前缀延伸 |
| 26 | `decision` | 30 | 31 | 30 | ✅ 前缀延伸 |
| 27 | `decision` | 31 | 32 | 31 | ✅ 前缀延伸 |
| 28 | `decision` | 32 | 33 | 32 | ✅ 前缀延伸 |
| 29 | `decision` | 33 | 34 | 33 | ✅ 前缀延伸 |
| 30 | `decision` | 34 | 35 | 34 | ✅ 前缀延伸 |
| 31 | `decision` | 35 | 36 | 35 | ✅ 前缀延伸 |
| 32 | `decision` | 36 | 37 | 36 | ✅ 前缀延伸 |
| 33 | `decision` | 37 | 38 | 37 | ✅ 前缀延伸 |
| 34 | `decision` | 38 | 39 | 38 | ✅ 前缀延伸 |
| 35 | `decision` | 39 | 40 | 39 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 4 个 jsonl，排除 `*.baseline`；run 命中 35 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T21:48:42 | `understand` | 2 | 2665 | 0 | 1356 | None |
| 2 | 2026-10-16T21:48:44 | `decision` | 4 | 8221 | 0 | 1501 | None |
| 3 | 2026-10-16T21:48:45 | `decision` | 6 | 8574 | 0 | 1413 | None |
| 4 | 2026-10-16T21:48:47 | `decision` | 8 | 8975 | 0 | 1187 | None |
| 5 | 2026-10-16T21:48:49 | `decision` | 10 | 14056 | 0 | 2153 | None |
| 6 | 2026-10-16T21:48:51 | `decision` | 11 | 14118 | 0 | 1334 | None |
| 7 | 2026-10-16T21:48:52 | `decision` | 12 | 14139 | 0 | 1369 | None |
| 8 | 2026-10-16T21:48:54 | `decision` | 13 | 14167 | 0 | 1376 | None |
| 9 | 2026-10-16T21:48:55 | `decision` | 14 | 14223 | 0 | 1535 | None |
| 10 | 2026-10-16T21:48:57 | `decision` | 15 | 14280 | 0 | 1348 | None |
| 11 | 2026-10-16T21:48:58 | `decision` | 16 | 14337 | 0 | 1251 | None |
| 12 | 2026-10-16T21:49:01 | `decision` | 17 | 14394 | 0 | 2122 | None |
| 13 | 2026-10-16T21:49:03 | `decision` | 18 | 14628 | 0 | 2176 | None |
| 14 | 2026-10-16T21:49:05 | `decision` | 19 | 14909 | 0 | 1345 | None |
| 15 | 2026-10-16T21:49:08 | `decision` | 20 | 14966 | 0 | 3664 | None |
| 16 | 2026-10-16T21:49:12 | `decision` | 21 | 15527 | 0 | 3208 | None |
| 17 | 2026-10-16T21:49:13 | `decision` | 22 | 16006 | 0 | 1419 | None |
| 18 | 2026-10-16T21:49:15 | `decision` | 23 | 16063 | 0 | 1245 | None |
| 19 | 2026-10-16T21:49:16 | `decision` | 24 | 16120 | 0 | 1345 | None |
| 20 | 2026-10-16T21:49:18 | `decision` | 25 | 16153 | 0 | 1179 | None |
| 21 | 2026-10-16T21:49:19 | `decision` | 26 | 16209 | 0 | 1258 | None |
| 22 | 2026-10-16T21:49:21 | `decision` | 27 | 16266 | 0 | 1593 | None |
| 23 | 2026-10-16T21:49:23 | `decision` | 28 | 16323 | 0 | 1524 | None |
| 24 | 2026-10-16T21:49:30 | `decision` | 29 | 16380 | 0 | 6728 | None |
| 25 | 2026-10-16T21:49:31 | `decision` | 30 | 16437 | 0 | 1735 | None |
| 26 | 2026-10-16T21:49:33 | `decision` | 31 | 16494 | 0 | 1373 | None |
| 27 | 2026-10-16T21:49:35 | `decision` | 32 | 16551 | 0 | 1282 | None |
| 28 | 2026-10-16T21:49:36 | `decision` | 33 | 16608 | 0 | 1311 | None |
| 29 | 2026-10-16T21:49:39 | `decision` | 34 | 16665 | 0 | 2565 | None |
| 30 | 2026-10-16T21:49:40 | `decision` | 35 | 17059 | 0 | 1386 | None |
| 31 | 2026-10-16T21:49:42 | `decision` | 36 | 17116 | 0 | 1340 | None |
| 32 | 2026-10-16T21:49:43 | `decision` | 37 | 17195 | 0 | 1321 | None |
| 33 | 2026-10-16T21:49:45 | `decision` | 38 | 17252 | 0 | 1362 | None |
| 34 | 2026-10-16T21:49:47 | `decision` | 39 | 17309 | 0 | 1454 | None |
| 35 | 2026-10-16T21:49:48 | `decision` | 40 | 17366 | 0 | 1296 | None |

caller×次数：`decision`×34、`understand`×1

链长增长：2 → 4 → 6 → 8 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28 → 29 → 30 → 31 → 32 → 33 → 34 → 35 → 36 → 37 → 38 → 39 → 40

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1
- `id=5` 澄清 r2 被拒：ledger_notes 槽位对账未过：s1
- `id=10` 工具匹配被拒（必填缺）
- `id=13` 工具匹配被拒（缺配）
- `id=16` 工具匹配被拒（缺配）
- `id=19` 工具匹配被拒（必填缺）
- `id=22` 工具匹配被拒（必填缺）
- `id=25` 工具匹配被拒（必填缺）
- `id=28` 工具匹配被拒（必填缺）
- `id=31` 工具匹配被拒（缺配）
- `id=34` 工具匹配被拒（缺配）
- `id=37` 工具匹配被拒（必填缺）
- `id=40` 工具匹配被拒（必填缺）
- `id=43` 工具匹配被拒（缺配）
- `id=46` 工具匹配被拒（必填缺）
- `id=49` 工具匹配被拒（必填缺）
- `id=52` 工具匹配被拒（缺配）
- `id=55` 工具匹配被拒（必填缺）
- `id=58` 工具匹配被拒（必填缺）
- `id=61` 工具匹配被拒（必填缺）
- `id=64` 工具匹配被拒（必填缺）
- `id=67` 工具匹配被拒（必填缺）
- `id=70` 工具匹配被拒（必填缺）
- `id=73` 工具匹配被拒（必填缺）
- `id=76` 工具匹配被拒（必填缺）
- `id=79` 工具匹配被拒（必填缺）
- `id=82` 工具匹配被拒（缺配）
- `id=85` 工具匹配被拒（必填缺）
- `id=88` 工具匹配被拒（缺配）
- `id=91` 工具匹配被拒（必填缺）
- `id=94` 工具匹配被拒（必填缺）
- `id=97` 工具匹配被拒（必填缺）
- `id=100` 工具匹配被拒（必填缺）

notice 帧：

- `id=8` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=11` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=14` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=17` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=20` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=23` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=26` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=29` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=32` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=35` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=38` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=41` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=44` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=47` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=50` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=53` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=56` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=59` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=62` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=65` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=68` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=71` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=74` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=77` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=80` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=83` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=86` `decision_rejected`：工具匹配发射被拒（缺配）：缺 matches（非空数组——组内每个子问题恰一条）——修正后重新输出 JSON。
- `id=89` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=92` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=95` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=98` `decision_rejected`：工具匹配发射被拒（必填缺）：matches s1 缺 mention_mode（「提及 vs 执行」结论——须给 executed／mentioned_only）——修正后重新输出 JSON。
- `id=101` `run_failed`：run 执行失败：Recursion limit of 35 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.
For troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT

## ask 帧

（无 ask 帧）

## 归档文件

- `03-最近各井日产油量怎么样.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/03-最近各井日产油量怎么样.sse`
- `03-最近各井日产油量怎么样-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/03-最近各井日产油量怎么样-last-context.json`
- `03-最近各井日产油量怎么样-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/03-最近各井日产油量怎么样-summary.md`
