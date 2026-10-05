# W-AUX 开发拍 回报

> 作业方式：git worktree `.scratch/w-aux`（分支 `fix/w-aux-query-narrate`，基线＝master 最新 `5fef5f4`）隔离作业；
> 单提交 `ce38179`（六文件，+430/−42）；闸门全绿实跑后 worktree 已 remove（分支与提交保留待合并）。
> 主树零污染：显式路径 `git add` 六文件（chat 域 service/chains/domain＋三测试文件），未用 `git add -A/.`；
> Owner 私产（eval/、tickets/、web/src、node_modules、dispatch/ 作业前既有件）零触碰。
> 作业期间 master 前移两次（`5fef5f4` eval 题库、`adc3849` DEP-01 收口）——与本次六文件零交集，FF 合并无冲突。

## 产物

- **提交**：`ce38179`（分支 `fix/w-aux-query-narrate`，父 `5fef5f4`，单提交；worktree 已 remove）

| 票面工序 | 文件 | 说明 |
|---|---|---|
| ③ 降级接续 | `app/domains/chat/chains.py` | 出不了数三路（N7.1 无注册声明／N7.4a 全窗未出数／N7.6 零行）不再以拒答收场——新增 `_continue_with_retrieval` 同模块函数级复用 `retrieval_chain`（零新缝）：token/citation 缓冲随终局分派，接续链真出检索答案（kind=text 且引用非空）按原序放行；接续链兜底收场 → 双重如实拒答（丢弃缓冲流，回落问数链原拒答话术）；三路原拒答文本逐字保留作双重拒答收场话术 |
| ③ 降级接续 | `app/domains/chat/domain.py` | `ChainContext.data_fallback_note`（None 缺省＝直接进检索链行为不变）＋`DATA_CHAIN_FALLBACK_NOTE`/`DATA_CHAIN_FALLBACK_NOTICE` 常量（票面规定标注原文单源） |
| ③ 降级接续 | `app/domains/chat/chains.py` | `retrieval_chain` 收束处在流式切片前消费 `data_fallback_note` 前置进正文（`RESCORED_ANSWER_TAG` 同款改法）——token 流与答案帧同文，零新增帧键 |
| ① 判型恢复 | `app/domains/chat/service.py` | `INTENT_VERDICT_SYSTEM_PROMPT` 分型路由取代 P1F-01「自然语言问法一律选检索问答链」过渡约束（票面注记：经 Owner 2026-10-05 批准，六站链已接线非空壳）——数据型（命中指标声明＋取值诉求：多少/最高/最低/排名/对比族）→ 状态机六站链；措施/原因/定义/机理报告叙述型 → 检索问答链；复合题 → 检索兜底；纯定义问法（什么是 X）→ 仍检索链（P1F-02「命中只是材料信号」精化为「命中＋取值诉求合判」）；@ 显式锚定兜底与「指标卡直出链/口径消歧链仅受理 @ 锚定」条款原样保留；N5b 未注册链覆写回退零改动 |
| ④ 测试 | `tests/domains/chat/test_chat_query_fallback_continue.py` | 新增 285 行：(a) 提示词分型路由断言＋确定性兜底面回归（LLM 不可用时数据型→六站、纯定义→检索）；(c) 三路接续成功（标注前置＋引用照常＋token 与答案同文）×双重拒答（0 行/无声明/新鲜度三话术原样恢复）；(d) 帧序合同（节点键全景树在册集、状态推进单向、六站帧＋N17/S/GEN 帧混排、token→citation→answer→done、answer 恰一次、tool_call 0 行留痕） |
| ④ 测试 | `tests/domains/chat/test_chat_query_chain.py` | 两测试随票面行为变更更新（非回归，见偏差 2）：`test_unregistered_metric_degrades_honestly`→`test_unregistered_metric_degrades_then_continues`（不生成 SQL/零执行/不冒充审定口径立场断言全保留＋接续标注断言）；`test_freshness_full_miss_refuses`→`test_freshness_full_miss_continues_to_retrieval`（闸仍零调用拦停＋接续标注断言） |
| ④ 测试 | `tests/domains/chat/test_chat_n5_shell_fallback.py` | `test_intent_prompt_carries_constraint` 随分型路由更新（新增「分型路由/状态机六站链/取值诉求」断言，新增「一律选已撤」负断言；@ 锚定与仅受理条款断言保留） |

- **TDD 红先实证**：新测试文件首跑 `4 failed, 5 passed`（判型提示词/0 行接续/无声明接续/帧序混排四红，红因全为「接续不存在/旧约束在」）；实现后 chat 域 `243 passed`、全量 `885 passed`。

### 帧形状合规证明（验收 3——对照 A1 册，破形状即停线）

1. **①③零破形状**：①只改裁决提示词文案（verdict 帧字段集不动）；③全部帧取自既有 19 类（node 键均在全景树在册键集内、`node_line` 后置于 finish 有 `_config_check_line` 既有先例、answer 恒最后、done 收尾）——新增的是 `ChainContext` 域内字段与 `notice`/既有帧内的标注文本，无新帧类型、无 answer 载贷新键。
2. **②停线判定（票面条款触发）**——对照 `/Users/divh/Downloads/teach-petro-agent/specs/api/A1-问一问.md`：
   - answer DTO 六种 kind 为合同值（L148「answer DTO（六种 kind，合同值…）」）；`table` kind payload 冻结为 `{title?, note?, columns[], rows[], source_note?, chart_suggestion?, citations?, tool_call?, lineage?}`（L153），**无 `narrative`/`caption` 槽位**；
   - 现存可选字段的合同语义各自绑死：`note`＝「命中指标卡等前置说明（Alert info）」、`source_note`＝「数据来源…」、`chart_suggestion`＝「图表建议行」——解读段挂任何一处均属字段语义挪用（AGENTS.md 硬纪律 1：字段语义与合同不一致＝缺陷，改合同回设计仓改）；
   - 变更记录全表（L300–309）核对：additive 登记仅 verdict `source`（2026-10-02）、clarify `subtype=rewrite`（2026-10-04）、locator `fragment_id`（2026-09-29）、verdict `intent_source`（2026-10-05 T-01）——**answer 帧无任何 additive 槽位登记**；
   - 行为规则 2（L267）：「帧类型集不可改：19 类事件帧与载荷形状是本合同核心冻结物」。
   - **结论：票面「无 → 停线回报（不破帧合同）」条件命中**——辅助检索召回、`gateway.complete`（caller=chat.query.narrate）叙述生成、解读段挂帧整体未实现（避免无消费面的死代码与无意义计费）；除此之外三件全交付。

## 闸门实跑（worktree 内 HEAD=ce38179 同内容工作树，提交后实跑原文）

```
$ uv run pytest -q
........................................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
........................................................................ [ 29%]
...............ssss..................................................... [ 37%]
......................................................................ss [ 44%]
ssssssss........................................................ss...... [ 52%]
.................ss..........................................ssss....... [ 59%]
............................................sssssss..................... [ 66%]
........................................................................ [ 74%]
..............ssssss...........................ssssssss................. [ 81%]
..........ssssss....sss..............ssssssssssssss..................... [ 89%]
......................sssssssssss.........................ss............ [ 96%]
.................ssss...........                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /Users/divh/Downloads/petro-agent-platform/.scratch/w-aux/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient  # noqa

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
885 passed, 83 skipped, 1 warning in 30.54s

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

- caller 计费留痕：接续链全部模型调用照既有 caller 归因（`chat.retrieval.answer`/`chat.retrieval.rerank`/`chat.query.rewrite`/`chat.retrieval.fallback`），零新 caller——`chat.query.narrate` 因②停线未落（见偏差 1）；既有 caller 断言族回归绿。

## 偏差

1. **票面工序②「问数链辅助检索＋叙述生成」未实现——按票面停线条款停线**：现象→A1 册 answer kind=table 无 narrative/caption 合规槽位且变更记录无 answer 帧 additive 登记（证据见上文合规证明节）；原因→帧合同冻结物无承载位，`note` 等既有字段语义绑死他用途；处置→停线回报不破帧合同（票面原文条款），召回/生成/挂帧整体不落、验收 (b) 测试未建，待 L0 裁决出路后随合同对齐批重派。
2. **既有两测试随行为变更更新（票面授权的行为变化，非测试衰减）**：降级解释链与新鲜度全窗未出数两路原「直接拒答收场」按票面③改为「接续检索＋双重无果才拒答」——两测试断言更新后原立场断言（零执行/不生成 SQL/不冒充审定口径/拦停不出空数）全保留；另有 `test_intent_prompt_carries_constraint` 随①提示词更新（P1F-01 过渡约束撤除经票面注记 Owner 批准）。
3. **既有 PG 集成测试零改动兼容**：`tests/domains/semantics/test_sem_seed_0019_pg.py` 红例（0019 种子落库前 N7.1 降级）断言「未命中注册指标声明」——接续改造后该话术经「双重拒答回落原话」仍然成立（本环境 TEST_DATABASE_URL 未配置随 83 skipped，逻辑推演＋sqlite 同构路径已测）。

## 疑点（待 L0 裁决，不动手）

1. **②停线后的出路三选一（裁决后可随 A1 合同对齐批重派本票②）**：
   a. 教学仓 A1 册走 additive 登记为 answer kind=table 增解读段槽位（如 `narrative`，或扩宽 `note` 语义并在变更记录背书）——本仓随后接线，帧形状合同先行；
   b. Owner 明示批准以 `note` 字段承载解读段（须 A1 册变更记录补语义扩宽登记，否则违反硬纪律 1）；
   c. 解读段降级为 `notice` 帧并列呈现（零帧形状改动，但 notice 合同语义是「非终局提示」，承载生成内容属语义挪用——需 Owner 点头）。
2. **N7.5 执行缝未装配路径不在票面列举三路内**（现仍是「查询执行通道未装配——本次不出数」运维告警收场）：是否也接续检索，待 L0 定（本拍维持原状——该路径是基础设施缺陷信号，接续检索可能掩盖故障）。
3. **接续成功判据＝答案 kind=text 且引用非空**：D2 fallback_strategy=free 时接续链「检索无果的自由回答」（无引用、带「未依据报告库」标）按双重无果处理回落问数链拒答——宁可拒答不用非检索内容充数；若 Owner 希望自由回答也算接续成功，需明确改判据。
4. **接续路可能触发检索链改写澄清**（P1F-06 低分带第二道——clarify 额度在时弹 rewrite 帧 interrupt 挂起）：既有链内行为，帧协议合法；问数题落到澄清交互是否符合预期，请 L0 相机裁量（本拍不额外设闸）。

---

## 修复拍处置（W-AUX.fix——2026-10-05，出路 C 已实现）

- **出路 C → 已实现**：辅助检索＋叙述生成落地，解读段以 notice 旁注帧呈现——提交 `20d16ce`（分支 `fix/w-aux-query-narrate`，父 `ce38179`，rev-list=2）；帧位次＝血缘帧 → citation → notice(解读段) → answer → done（answer 恒最后，零新帧型、answer 载荷零新增键）。全文见 `results/W-AUX.fix.md`。
- **四条预裁决记录**：
  1. **接续范围**：降级接续仅限三路出不了数路径（N7.1/N7.4a/N7.6 零行）——N7.5 执行缝未装配路径维持如实现状（「查询执行通道未装配」运维告警收场，不接续检索——防掩盖基础设施故障）——登记，**归属：M-06 后续打磨批**。
  2. **free 兜底无引用回答＝双重无果处理** → 判据确认（`_continue_with_retrieval` 接续成功判据维持「kind=text 且引用非空」——free 无引用回答回落问数链原拒答话术，不用非检索内容充数）。
  3. **接续路沿用检索链既有行为（含 P1F-06 低分带改写澄清触发）** → 确认为预期交互，登记（不额外设闸）。
  4. **A1 册「解读槽位」正式化** → 登记，**归属：阶段 3 合同对齐批**（本拍以 notice 旁注帧为过渡呈现形态，零合同变更；阶段 3 对齐时若 A1 册为 answer kind=table 走 additive 解读槽位登记，再迁移）。
