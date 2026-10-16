# L2 · 05 · 最近各井日产油量怎么样？

- 生成时刻：`2026-10-17T01:51:00`（`scripts/ladder_run.py`）
- 层级／序号：`L2` / `05`
- 题面：最近各井日产油量怎么样？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-eb52402b`
- verdict(final)：`completed`（run_id=run-eb52402b，manifest_digest=7e100b8ad1cde280）
- 首段：`05-最近各井日产油量怎么样.sse` 解析重建（13 帧）
- 续段（resume）：`05-最近各井日产油量怎么样-resume.sse` 解析重建（23 帧）
- 用户选择（自续段 `step` 帧回读）：近 30 天
- 覆盖范围：首段 13 帧 ＋ 续段 23 帧（合计 36 帧；本摘要按完整 run 统计）
- 流收尾：首段 ✅ `done`；续段 ✅ `done`

> 本摘要由 `--resummarize` 从归档 SSE 重建（不重跑题）：`05-最近各井日产油量怎么样-resume.sse`

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `ask` | 1 | 0 | 1 |
| `blackbox` | 0 | 1 | 1 |
| `citation` | 0 | 1 | 1 |
| `done` | 1 | 1 | 2 |
| `notice` | 1 | 2 | 3 |
| `observation` | 0 | 1 | 1 |
| `session` | 1 | 1 | 2 |
| `step` | 7 | 11 | 18 |
| `text` | 1 | 2 | 3 |
| `tool` | 0 | 1 | 1 |
| `verdict` | 1 | 2 | 3 |
| **合计** | 13 | 23 | 36 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 6/6 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |
| 5 | `decision` | 8 | 11 | 8 | ✅ 前缀延伸 |
| 6 | `decision` | 11 | 12 | 11 | ✅ 前缀延伸 |
| 7 | `answer` | 12 | 14 | 12 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；按 run_id 命中 7 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-16T22:33:27 | `understand` | 2 | 2665 | 0 | 1278 | None |
| 2 | 2026-10-16T22:33:29 | `decision` | 4 | 8240 | 0 | 1772 | None |
| 3 | 2026-10-16T22:33:30 | `decision` | 6 | 8611 | 0 | 1676 | None |
| 4 | 2026-10-16T22:33:32 | `decision` | 8 | 13773 | 0 | 1584 | None |
| 5 | 2026-10-16T22:33:55 | `decision` | 11 | 13887 | 0 | 1781 | None |
| 6 | 2026-10-16T22:33:57 | `decision` | 12 | 13968 | 0 | 1382 | None |
| 7 | 2026-10-16T22:34:00 | `answer` | 14 | 14848 | 0 | 2602 | None |

caller×次数：`decision`×5、`understand`×1、`answer`×1

链长增长：2 → 4 → 6 → 8 → 11 → 12 → 14

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=8` `decision_note`：前置条件机：子问题 s1 等用户（caliber_clarify）——子问题 s1 的时间范围未能确定（模型发射载荷窗槽双 null＝不能确定）——请先选定时间范围（模糊时间词不解析、不默认）
- `id=15` `decision_note`：前置条件机：子问题 s1 放行（注记 1 条）——窗上沿 2026-10-16 晚于汇总层水位 2026-08-31——引擎新鲜度闸将拦停/改绑并注记（照实判定）
- `id=25` `unsupported_claim`：核验步改写无据断言 1 行（INV-1——禁止无据断言进答案）

## ask 帧

- 帧位：`id=7`（首段）

```json
{
  "frame": {
    "kind": "clarify",
    "prompt": "子问题 s1 的时间范围未能确定（模型发射载荷窗槽双 null＝不能确定）——请先选定时间范围（模糊时间词不解析、不默认）",
    "options": [
      "近 3 天",
      "近 30 天",
      "本月至今"
    ],
    "detail": {}
  },
  "run_id": "run-eb52402b"
}
```

## 归档文件

- `05-最近各井日产油量怎么样.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/05-最近各井日产油量怎么样.sse`
- `05-最近各井日产油量怎么样-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/05-最近各井日产油量怎么样-last-context.json`
- `05-最近各井日产油量怎么样-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/05-最近各井日产油量怎么样-summary.md`
- `05-最近各井日产油量怎么样-resume.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L2/05-最近各井日产油量怎么样-resume.sse`
