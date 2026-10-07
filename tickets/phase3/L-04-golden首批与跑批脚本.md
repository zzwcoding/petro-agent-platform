# L-04 golden 首批与跑批脚本（Owner 审过才算数；回归闸以脚本形态先在位）

> 状态：🔨 **交付齐——待 Owner 签认 golden**（四件交付与全量闸六件套绿在案，
> 收尾报告＝tickets/phase3/reports/L-04.收尾.md；**未签认本票不得关票**——拍板 5。
> 依赖：L-01（Draft/validator 在位——意图机器判要对着 validator 同源
> 口径判）；可与 L-02/L-03 并行。开工定案：分支＝`l-plan/L-04-golden`（独立工作树
> /Users/divh/Downloads/petro-wt/l04），自 `l-plan/L-01-shadow` 端点 de30a27 续开——
> L-01 未合入 master，按票面「开工时定案」取工作树检出分支名（与票面 runner 后缀
> 差异在此登记）。

任务: 实现阶段 3 方案 v2.1 应用线 L-04——golden 首批＋轻量跑批脚本。拍板 5 在案：**轻量
评测不可省**，golden 清单＋跑批脚本随票滚动建、不以 assessment 机器为前置，闸 B 起为生效
硬闸——没有回归闸，后面每个新指标都是裸奔。TDD 先红后绿（意图比对纯函数先写测试见红→
实现转绿；eval 侧脚本本体照 rerun.py 惯例不进 tests/，但比对纯函数必须进 tests/）。三件
交付物：
1. golden 首批（票内定案落点：`eval/results/golden/plan-golden-v1.json`；票内定案规模：
   首批 24 题，≥20 为下限，增减由 Owner 审核位裁量）。每题字段：qid／题目原句／期望意图
   （五源槽位：metric_slot/window.start/window.end+label/limit_requested/ranking/
   direction）／期望路径（快路｜慢路触发｜不触发）／标准答案要点（数值＋口径——人审用）／
   覆盖标签。覆盖矩阵（票内定案，24 题分配）：
   - 三指标×快路（6）：日产油量/日产液量/油压各 2（排名型＋明细型各一——快路信号齐直进）；
   - 慢路触发（6）：词面缺件/确定性解析缺件问法（含「哪几口井采得最狠」——不命中
     DATA_QUESTION_RE 词面亦无默认窗的代表例）；
   - 默认窗（2）：无显式时间词——默认窗＋标注路径；
   - 触发边界（4）：纯检索/释义问法不触发（非数据问句）＋词面边缘判例；
   - 红例族（6）：完成率/递减率降级解释链、外表审批问法（erp_well_register/井位台账）、
     LIMIT 收口（「前 500」→截 200）、反例不编数（0 行/无注册指标如实拒答）。
   标准答案要点的数值**来自实查 agg 表**（golden 对库），不许编数——业务事实零发明；
   数值随库变化属预期，人审按「口径＋量级」判。Owner 审核位：golden 清单整表 Owner 审过
   才算数（拍板 5），签认记本票回报。
2. 轻量跑批脚本（票内定案落点：`eval/results/tools/plan_rerun.py`；形态参照
   eval/results/tools/rerun.py——HTTP 流式提问、SSE 帧全量存档 eval/results/frames/
   {tag}-{qid}.json、判分辅助表；题间间隔、RERUN_BASE 环境变量同款）。增量＝意图机器判：
   意图比对纯函数（进 tests/，TDD）从帧提取实际槽位与 golden 期望逐字段等值比对（字段集
   与 L-01 比对算子执行语义字段集同源：metric_slot/window.start/window.end/limit_effective
   /ranking/direction）。实际槽位提取口径（票内定案）：N7.1 finish 节点行解析为主
   （「指标＝{slot}（台账「{name}」）· 时间＝{label} · 条数＝{n}」），verdict slots 佐证，
   影子日志 draft 三态为慢路题佐证；解析失败＝该题落「人审列」不进机器判绿红。
   脚本退出码＝机器判结果（全绿 0、有红 1）——答案数值部分只进判分辅助表（人审件），
   **不进退出码**（票内定案：闸看机器判、人审看辅助表，两不相混）。
3. 回归闸在位＋少样本对接：脚本以退出码形态成为闸 B 生效硬闸的载体（拍板 5）；golden
   文件同时是 L-02 提示词构建器的少样本源——对接验证一项：构建器吃 golden 前 3 条（票内
   定案 K=3）产出合法 messages（若 L-02 未合入，本项落本票测试替身上验证接口形状，
   对接实测记回报）。

先读:
- tickets/phase3/方案-LLM问数演进-20261005.md §3 机制 14（golden 双用＋评测回归闸）、§4
  治理线「轻量评测不可省」、§5 拆票表第 5 行、§2.3 D3（比对算子字段集）
- tickets/phase3/拍板记录-20261005.md 第 5 条（轻量评测不可省——本票真源）＋挂点更新
  （移交清单①）
- tickets/phase3/L-01-问数入口精解析-影子观测件.md（比对算子字段集/三态——机器判同源口径）
- eval/results/tools/rerun.py（脚本形态/纪律真源：题干原句不改写、每题一遍零重试、
  SSE 帧存档、判分辅助表、RERUN_BASE）
- eval/results/tools/suites_q3.py（题册形态参照——qid/组别/题干三元组惯例）
- app/domains/chat/chains.py:1331-1387（N7.1 现状——【注意】方案册引 1037-1110 为旧行号，
  现位已漂移；finish 节点行文本＝意图提取口径的消费面）
- app/domains/chat/domain.py:1107-1132（QueryPlan 五源槽位/QUERY_DEFAULT_LIMIT 50/
  QUERY_LIMIT_CAP 200——期望值字段的合同口径）

验收:
- [ ] golden 首批 24 题落 eval/results/golden/plan-golden-v1.json：覆盖矩阵五族各在案
  （每族题数与票面分配一致）；数值答案要点全部实查在案（附查询口径注记）；Owner 审核
  签认记录进回报（「Owner 审过才算数」——未签认本票不得关票）
  —— 子件齐：golden 落盘 ✓／五族 6·6·2·4·6 ✓／数值 2026-10-07 实查 agg 注记 ✓／
  签认记录进回报（**签认位留空待 Owner**）；**本框待 Owner 签认后勾选关票**
- [x] 意图比对纯函数 TDD 先红后绿：逐字段等值/字段缺失/期望缺件三路测试在案
  （tests/tools/test_plan_golden_judge.py 28 例；红态＝模块缺席 FileNotFoundError 实录）
- [x] 跑批脚本可跑通：对本地起服实跑 golden 全量一次（帧存档＋判分辅助表＋退出码在案）；
  机器判红题清单在回报列明（红题本身不挡本票——本票交付的是闸，红题诊断归 L-05 前整改
  或 Owner 裁决，如实记录）
  —— 实跑两轮在案：L04G（跨零点→锚机制把 day 级窗题落人审，退出码 0）＋L04G2（重锚
  同日：绿 16／红 0／人审 8＝慢路题预期态，退出码 0）；**机器判红题清单＝空**
- [x] 少样本对接验证在案：golden 前 3 条→构建器 messages 合法（替身或实测，方式如实记）
  —— 替身路径（l-plan/L-02-shadow-wiring 停在 L-01 端点、构建器未落码）：build_fewshot_messages
  按方案 §2.1 契约产 messages＋TestFewshotStub 3 例进测试闸；L-02 合入后替换即对接
- [x] `uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）

回报: 写 tickets/phase3/reports/L-04.收尾.md——产物清单（golden/脚本/测试文件＋commit
SHA）/闸门实跑输出原文/实跑结果（绿红分布/红题清单）/Owner 签认记录/偏差逐条（现象→
原因→处置）/疑点列 L0 不动手。git 纪律：`l-plan/L-04-golden-runner` 自
`l-plan/L-01-shadow` 续开（与 L-02/L-03 并行线；若 L-01 分支已合入 master 则自 master
拉，开工时定案记录）；只 add 本票明确改动文件，提交前 git status 核对暂存区仅含本票
文件，严禁 git add -A/git add .；不 push 不合入（合入随闸 A 后 L-05 批）。

框架红线: 零新依赖；golden 题干与期望意图零业务发明（数值实查、口径查 C1 台账注册声明，
查不到→停工问 Owner）；LLM 调用面只许经 gateway.complete（本票跑批走 HTTP 端点，不经
本票新开调用面）；不改 19 类事件帧、17 链枚举、血缘五要素键序；SQL 唯一出口＝装配器
（本票只读 agg，不触装配面）。

边界红线: 只许触碰 eval/results/golden/（新）、eval/results/tools/plan_rerun.py（新）、
eval/results/frames/（跑批存档）、tests/（意图比对纯函数）；不动 app/、web/、migrations/、
pyproject.toml；若对接 L-02 构建器需读其接口，只读不改。

〔来源：方案-LLM问数演进-20261005 §2.3(D3)/3(机制14)/4(轻量评测不可省)/5(第5行)；
拍板记录-20261005 第 5 条＋挂点更新；票册总表-统一开票-20261007 乙节〕
