# W-AUX 修复拍 回报

> 作业方式：票面「主树当前在该分支上」与事实不符——主树在 master 且 `dispatch/journal.jsonl` 有未提交改动、master 与 fix 分支在该文件上有分歧（直接切分支必触 Owner 未提交内容），故照本仓 dev 拍/DEP-01 先例以 git worktree `.scratch/w-aux-fix` 挂 `fix/w-aux-query-narrate` 隔离作业：追加 commit 不 rebase，提交后 worktree 已 remove（分支与提交保留）。
> 主树零污染：未切分支、未 stash、`git add` 仅显式两文件（`app/domains/chat/chains.py`＋新测试文件），未用 `git add -A/.`；
> Owner 私产与并行未提交改动零触碰（作业期间 master 前移 adc3849→3d68193——并行窗 eval/journal 落盘，与本拍两文件零交集；5fef5f4 仍为 master 祖先，后续 FF 合并无冲突面）。

## 产物

- **提交**：`20d16ce`（分支 `fix/w-aux-query-narrate`，父 `ce38179`；`git rev-list --count master..fix/w-aux-query-narrate`＝2 ✓）

| 票面工序 | 文件 | 说明 |
|---|---|---|
| ① 辅助检索 | `app/domains/chat/chains.py` | 新增 `_aux_retrieval_fragments`：N7.5 只读执行行数>0 后，用原问句复用检索链双路召回缝（`deps.index_searcher_dual`——S4 同一注入缝，零新缝；合并策略随 `cfg.merge`，`_relaxed_rescore` 同款）取辅助片段，小窗口 `AUX_TOP_K=4`；引用别名自 `AUX_REF_START=3` 起（表卡数据证据 c1/c2 已占——同 run 全局不撞号）；报告库空 → 空清单＝纯表格自然降级零报错零帧 |
| ② 叙述生成 | `app/domains/chat/chains.py` | 新增 `_narrate_table`：辅助片段＋表格数据进 gateway.complete 单点（`CALLER_NARRATE="chat.query.narrate"`——chat.query.rewrite 计费留痕惯例），`NARRATE_SYSTEM_PROMPT` 三约束：**数值一律以表格为准（片段数值不采）／引用标注 cN／不得虚构**；生成不可用（completer 未装配/调用失败/空输出——照 rewrite 惯例）返回 None＝纯表格降级；引用 fail-closed 照检索链 GEN 收口同款（`parse_refs`→`anchor_loader` 锚校验→`strip_ref`——伪造/失锚引用拦截剥除＋`UNANCHORED_CITATION_NOTE` warning 留痕，绝不带病出帧） |
| ③ 旁注帧呈现 | `app/domains/chat/chains.py` | 解读段以既有 notice 机制输出（裁决 C——P2-03 状态标注先例，零合同变更）：**帧位次＝血缘帧 → citation 帧（被引片段 cN 出处展开）→〔warning 拦截留痕（仅 fail-closed 触发时）〕→ notice(level=info，解读段全文) → answer(kind=table 原样)**；answer 恒最后、零新帧型、answer 载荷零新增键；旁注不走 token 流（不冒充正文流）；辅助检索出 node_line 一行留痕（N7.6 键，「辅助检索：报告库双路召回 N 支片段……」） |
| ④ L0 预裁决四条 | `dispatch/results/W-AUX.dev.md` 末节「修复拍处置」＋commit message | ①接续范围限三路出不了数路径——N7.5 执行缝未装配路径维持如实现状（运维告警收场，不接续防掩盖基础设施故障），登记归 M-06 后续打磨批；②free 兜底无引用回答＝双重无果处理，判据确认（接续成功判据维持 kind=text 且引用非空）；③接续路沿用检索链既有行为（含 P1F-06 改写澄清触发），确认为预期交互，登记；④A1 册「解读槽位」正式化，登记归阶段 3 合同对齐批 |
| ④ 测试 | `tests/domains/chat/test_chat_query_aux_narrate.py`（新增 287 行 11 例） | 四族：辅助检索（双路召回缝恰一次/片段窗恰 4 支/别名 c3 起 c1·c2 不占/报告库空纯表格零报错零模型调用）；叙述生成（提示词三约束逐项/权威表格行值＋片段原文同窗/caller 计费留痕且无其他新 caller）；旁注帧（帧位次 lineage→citation→notice→answer→done/citation 帧冻结四键形状/answer 载荷冻结键集⊆A1 表卡 DTO 无 narrative·caption/**变异断言：片段携 99999 假数值进旁注但表格行与血缘卡逐字原样**/fail-closed 剥 [c9]＋拦截留痕）；降级与帧序合同（空输出软失败/调用硬异常 → 纯表格零报错/节点键全景树在册·状态推进单向·notice level 枚举内·answer 恰一次 done 收尾） |

- **TDD 红先实证**：常量先行落地（CALLER_NARRATE/NARRATE_SYSTEM_PROMPT——命名先行的红）后首跑 `7 failed, 4 passed`：辅助检索红＝`test_rows_found_reuses_dual_recall_small_window`（红因 index_dual=0≠1——辅助检索未接线）；旁注帧红＝`TestNarrateNoticeFrame` 三例（红因 notice/citation 帧缺失）＋帧序合同例；生成窗与计费留痕两例随红；4 绿为降级护栏组（实现前纯表路径本就无旁注——回归守卫）。实现后 11 例全绿。
- **帧序合法性对照 A1 册**（票面验收 2）：19 类帧集不动（新增帧全为既有类型）；node_line 键 N7.6 在全景树在册集（断言在位）；notice 载荷 `{level, text}` 冻结形状；citation 帧四键 `{ref, kind, label, locator}` 冻结形状；answer 恒最后且载荷键集 ⊆ A1 表卡 DTO 冻结集（`TABLE_ANSWER_KEYS` 断言在位——无解读槽位新键）；done 收尾、零异常帧。**位置与帧序施工说明（票面工序③要求回报）**：旁注帧置于血缘帧之后、answer 帧之前——与外表批准支既有 notice→answer 先例及 P1F-08「notice 在 token/answer 流前并列呈现」同构；被引片段的 cN 先以 citation 帧展开再出旁注帧（前端引用注册先行，cN 可解析）。

## 闸门实跑（worktree 内 HEAD=20d16ce 提交后实跑原文）

```
$ uv run pytest -q
........................................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
........................................................................ [ 29%]
..........................ssss.......................................... [ 36%]
........................................................................ [ 44%]
.........ssssssssss..................................................... [ 51%]
...ss.......................ss.......................................... [ 58%]
ssss...................................................sssssss.......... [ 66%]
........................................................................ [ 73%]
.........................ssssss...........................ssssssss...... [ 80%]
.....................ssssss....sss..............ssssssssssssss.......... [ 88%]
.................................sssssssssss.........................ss. [ 95%]
............................ssss...........                              [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /Users/divh/Downloads/petro-agent-platform/.scratch/w-aux-fix/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
896 passed, 83 skipped, 1 warning in 22.08s

$ uv run ruff check app tests migrations tools
All checks passed!

$ uv run mypy app
Success: no issues found in 76 source files

$ uv run lint-imports
Contracts: 5 kept, 0 broken.
（B16 层间单向/B16 infra 禁咬上层/B1 框架接触面/B9 kb→derivatives/B6 litellm 单点 全 KEPT）

$ uv run python tools/contract_coverage.py check
合同覆盖率闸绿：169 条合同端点双向对账通过。

$ uv run python tools/debt_markers.py check
债务标记闸绿：web 源码债务短语全部携可解析 DEBT 标签（盘点 33 条见 report）。
```

- 全量数字：**896 passed, 83 skipped**（票面基线 885+83 不跌——恰 +11＝本拍新测试，skip 持平）。
- caller 计费留痕：`chat.query.narrate` 断言在位（`test_caller_billing_trace`——completions 记录含 CALLER_NARRATE 且全量 caller ⊆ {chat.intent.verdict, chat.query.narrate}）；零片段主路回归断言零模型调用（`test_report_library_empty_pure_table_zero_error`）。

## 偏差

1. **作业方式偏差（非票面工序偏差）**：票面前提「主树当前在该分支上」不成立——主树在 master，且 `dispatch/journal.jsonl` 有未提交改动、master 与 fix 分支在该文件上有分歧，主树直接切分支必触碰 Owner 未提交内容。处置：照本仓 dev 拍/DEP-01 先例 worktree 隔离作业（`.scratch/w-aux-fix`），追加 commit 不 rebase（rev-list=2 达成），提交后 worktree 已 remove；主树未切分支未 stash，Owner 私产与并行未提交改动零触碰。
2. **旁注帧内 cN 引用不随 cfg.citation_format=page 改写**：D2「引用格式切换」只切答案正文呈现（`rewrite_citations` 仅用于检索/图谱链答案正文），旁注帧文本按票面验收明文保留 [cN] 编号（「notice 帧含 cN 引用」）；cN 的公开出处由先行 citation 帧承载——非编号语义挪用，fail-closed 校验照旧。
3. **extable 批准支不出旁注**：票面工序①锚定「N7.5 只读执行后」的旁注解读落在标准表卡答案支（kind=table）；extable 批准支（answer kind=extable）保持原样——其已携审批留痕脚注与独立 notice，本拍不扩面（如需覆盖 extable 支待 L0 补裁决）。

## 疑点（待 L0 裁决，不动手）

1. notice 帧合同语义（A1 册帧 16「非终局提示」）承载生成内容＝裁决 C 已明知的语义扩宽（dev 拍停线判定 c 项「需 Owner 点头」已由出路 C 选择满足）——建议阶段 3 合同对齐批在 A1 册变更记录补一行注记（notice 旁注解读用法），与「解读槽位正式化」登记同批处理。
2. 变异断言只证明呈现位次的物理隔离（片段假数值进得了旁注、进不了表格/血缘卡）；「解读文本自身不采片段数值」目前是提示词约束（模型面），无确定性机判——若要机判需数值抽取比对闸，归属建议随 M-06 后续打磨批裁量。
