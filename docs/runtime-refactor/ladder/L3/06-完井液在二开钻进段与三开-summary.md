# L3 · 06 · 完井液在二开钻进段与三开完井段的密度各是多少？与设计值差多少？

- 生成时刻：`2026-10-17T01:01:34`（`scripts/ladder_run.py`）
- 层级／序号：`L3` / `06`
- 题面：完井液在二开钻进段与三开完井段的密度各是多少？与设计值差多少？
- 端点：`http://127.0.0.1:8001`；身份：`X-Dev-User: laowang`
- run_id：`run-b5b6b056`
- verdict(final)：`completed`（run_id=run-b5b6b056，manifest_digest=0b107499358a8e14）
- 首段 HTTP：200／curl rc=0
- 续段（resume）：未发起

## 事件统计

| 事件 | 首段 | 续段 | 合计 |
| --- | --- | --- | --- |
| `blackbox` | 1 | 0 | 1 |
| `done` | 1 | 0 | 1 |
| `notice` | 1 | 0 | 1 |
| `session` | 1 | 0 | 1 |
| `step` | 8 | 0 | 8 |
| `text` | 2 | 0 | 2 |
| `verdict` | 1 | 0 | 1 |
| **合计** | 15 | 0 | 15 |

## 前缀延伸报告（KV 纪律验收线）

相邻调用前缀延伸 3/3 对 ✅（前链恒为后链前缀）

| # | caller | 前链长 | 本链长 | 公共前缀 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | `understand` | — | 2 | — | 起始调用 |
| 2 | `decision` | 2 | 4 | 2 | ✅ 前缀延伸 |
| 3 | `decision` | 4 | 6 | 4 | ✅ 前缀延伸 |
| 4 | `decision` | 6 | 8 | 6 | ✅ 前缀延伸 |

证据源：`logs/llm_calls/`（本次 glob 5 个 jsonl，排除 `*.baseline`；run 命中 4 条）

## 调用清单

| # | ts | caller | 链长 | prompt_tokens | cached | 耗时ms | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-10-17T01:01:27 | `understand` | 2 | 2697 | 0 | 1796 | None |
| 2 | 2026-10-17T01:01:29 | `decision` | 4 | 8342 | 0 | 2317 | None |
| 3 | 2026-10-17T01:01:32 | `decision` | 6 | 8635 | 0 | 2483 | None |
| 4 | 2026-10-17T01:01:34 | `decision` | 8 | 8869 | 0 | 2145 | None |

caller×次数：`decision`×3、`understand`×1

链长增长：2 → 4 → 6 → 8

## 拒因与 notice

被拒步记录：

- `id=3` 澄清 r1 被拒：ledger_notes 槽位对账未过：s1
- `id=5` 澄清 r2 被拒：ledger_notes 槽位对账未过：s1
- `id=7` 澄清 r3 被拒：ledger_notes 槽位对账未过：s1

notice 帧：

- `id=8` `budget_converged`：预算触界收敛：rounds 已用 3／上限 3；未完成项：未取得可交付材料（材料清单：无）

## ask 帧

（无 ask 帧）

## 归档文件

- `06-完井液在二开钻进段与三开.sse`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/06-完井液在二开钻进段与三开.sse`
- `06-完井液在二开钻进段与三开-last-context.json`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/06-完井液在二开钻进段与三开-last-context.json`
- `06-完井液在二开钻进段与三开-summary.md`：`/Users/divh/Downloads/petro-agent-platform/docs/runtime-refactor/ladder/L3/06-完井液在二开钻进段与三开-summary.md`
