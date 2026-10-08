# 双窗口直驱调度协议（PROTOCOL 模板——sdd-flow 版 v1.0）

> 本文件是 petro-agent-platform 的双窗口协议本体，L0 主控（Kimi 窗口）与执行调度台（ZCode 窗口）的第一阅读物；冲突时以本协议为准。
> 来源：sdd-flow skill references/dispatch-template/PROTOCOL.md——由 L0 在启用双窗口模式时复制到 /Users/divh/Downloads/petro-agent-platform/dispatch/PROTOCOL.md 并替换尖括号占位。

## 一、角色表

| 角色 | 承担者 | 干什么 | 绝不干 |
|---|---|---|---|
| L0 主控 | 本仓库目录下最新的 kimi 会话 | 拆票/写 pending/ 派工单、读 results/ 回报、验收、收尾裁决（修复/挂账归属/不采纳）、拍板请求写 decisions/open/、文档对齐裁决 | 派子代理、写实现代码 |
| 执行调度台 | ZCode 窗口 | 执法检查（含 tools/ticket_shape_check.py 必跑）→ 原样派发全新子代理 → 核实回报 → 拨 enabled 开关 → `kimi -S -p` 向 L0 报到 → 执行合并 → 回访 | 写实现、加工派工单一字、规划、拍板、用 Cron |
| 执行子代理 | ZCode Agent 工具全新实例 | 读派工单原样执行（TDD：测试先行；对齐拍：文档核对只产差异清单），自写回报文件 | 复用实例；审查拍直接改代码 |
| Owner | 人 | 点火两窗口、decisions/ 拍板、`rm dispatch/enabled` 急停 | —— |

## 二、目录即状态（会话记忆不进执法链）

```
dispatch/
├── PROTOCOL.md   # 本文件
├── enabled       # 总开关：存在=可执行；rm=急停（执行台当前子代理跑完即停）
├── pending/      # L0 召唤：P-x.md（开发/审查/修复/对齐四种拍，点号命名强制）
├── results/      # 子代理自写回报：P-x.<拍>.md（附闸门输出原文）
├── done/ rejected/          # 归档 / 执法驳回
├── decisions/open|closed/   # 拍板请求 / Owner 裁决
└── journal.jsonl # 单向留痕（只追加不删改）
```

## 三、一张票的完整生命周期（同步调用链＝循环，零定时器）

1. L0 拆票 → `pending/P-x.md`（shape 闸：L0 自校＋执行台复跑，红了退回重拆）。
2. 开发拍：执行台 `rm enabled` → 派全新子代理（提示词只说："读 /Users/divh/Downloads/petro-agent-platform/dispatch/pending/P-x.md 并原样执行其中全部指令，绝对路径作业；完成后按本协议「回报格式」写 results/P-x.dev.md，测试字段附 `uv run pytest -q` 实际输出原文"）。
3. 子代理：TDD（红→绿）→ 建分支提交 → 自写回报。
4. 执行台：核实回报存在且非空 → `touch enabled` → 调 L0 报到："报到:P-x 开发拍回报已写入 results/，请验收并下发下一步"。
5. 审查拍（触发三线见 sdd-flow ticket-gates.md 闸三）：同流程派发，**只产发现清单不修码**。
6. L0 裁决清单：修复项写成 `pending/P-x.fix.md`（只带被裁决条目）；挂账行必须「归属：X」。
7. 修复拍/对齐拍：同流程；对齐拍只产差异清单（改文档归 L0，改码转修复拍）。
8. L0 收尾裁决（close 闸自校）→ 合并指令；执行台执行合并 → **复跑 `uv run ruff check app appv2 tests migrations tools && uv run mypy app appv2 && uv run pytest -q && uv run lint-imports && uv run lint-imports --config tools/importlinter_v2.toml && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check`（退出码说话）** → 回访 L0："裁决已执行完毕（SHA/测试/队列状态），请拆下一张或明示停止值守"——回访是必经步，不许省略。
9. L0 拆下一张，或明示"停止值守"；执行台确认 enabled 在位 → 向 Owner 交总结报告。

## 四、执法点（不靠模型自觉）

| 纪律 | 机制 |
|---|---|
| 开发/审查/修复/对齐强制分拍 | pending/ 命名与拍型后缀；开发票混入对齐内容→rejected/ |
| 派工单形状 | `python3 /Users/divh/Downloads/petro-agent-platform/tools/ticket_shape_check.py <票>` 派发前必跑 |
| commit 带红 | 子代理 commit 前必跑快扫 `uv run ruff check app tests migrations tools && uv run python tools/debt_markers.py check && uv run python tools/contract_coverage.py check` 并附输出到回报「闸门实跑」节；执行台验收时核对快扫输出存在——Owner 拍板（2026-10-03）：不装 pre-commit 钩子，合并前全量复跑已覆盖主干污染风险，快扫靠本执法点 |
| 关票形状 | `python3 /Users/divh/Downloads/petro-agent-platform/tools/ticket_close_check.py <票> <收尾报告>` 关票前必跑 |
| TDD 真绿 | 回报附 `uv run pytest -q` 原文；执行台复跑 `uv run ruff check app appv2 tests migrations tools && uv run mypy app appv2 && uv run pytest -q && uv run lint-imports && uv run lint-imports --config tools/importlinter_v2.toml && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 核验 |
| 决策权归 L0 | 执行台只驳回不代改；续停由回访条款保证由 L0 决定 |
| 留痕 | 每动作追加 journal.jsonl 单行：`{"ts":"<ISO8601>","from":"desk|L0|subagent","to":"...","event":"report|reply|dispatch|verdict|other","text":"<≤600字>"}` |

## 五、回报格式（results/P-x.<拍>.md）

```
# P-x <拍名> 回报
## 产物
<提交 SHA 清单 / 文件清单>
## 闸门实跑
<`uv run pytest -q` 与 `uv run ruff check app appv2 tests migrations tools && uv run mypy app appv2 && uv run pytest -q && uv run lint-imports && uv run lint-imports --config tools/importlinter_v2.toml && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 输出原文摘要——含通过数数字，"全绿"两字不合格>
## 偏差
<有/无；有则逐条：现象→原因→处置（修复/挂账归属/不采纳理由）>
## 疑点（待 L0 裁决，不动手）
<逐条列出>
```

## 六、异常处理

派工单缺失 / L0 无响应（两次调用均失败）/ 闸门复跑不过 / 子代理回报与 git 事实对不上——**执行台停下如实报 Owner，不自行发明补救**。同一只读查询连续不得超过 2 次（防验证-行动死循环）。
