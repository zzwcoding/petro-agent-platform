# DE-15 branch_status 键级合并（E2-list——进度写防覆盖）

> 状态：⬜ 可开工 ｜ 依赖：DE-06（建议序——同载荷面增量票先此后彼，非硬阻塞）

任务: 任务分支状态（branch_status）为整块读-改-写：wiki 支路写 done 与 graph 支路写逐 chunk
进度交错时，基于旧载荷的整块写会盖掉对方键——只影响进度展示（轻），但盖错「done」会卡任务卡
状态。本票把写面改键级合并。交付物：
1. 写入语义改造：按分支键合并写（只覆盖本支路键，他支路键原样保留）——实现形态二选一票内
  定案：a) store 层 per-key 更新（JSON 键级 UPDATE）；b) 单写者串行化（每 task 一把写锁）。
  选型标准写进回报（成本/复杂度/锁面）。
2. 交错测试：两协程交错写（wiki done ∥ graph 进度 N 次）→ 终态两键均保留且值正确（现行实现
  先写一个必失败的红测试钉住缺陷，再实现转绿——TDD）。
3. 既有 branches 消费方零破坏（G-02 载荷键序不变；DE-06 新增键同受保护）。

先读:
- tickets/phase3/挂账清单-20261006.md §E2（「彻底修需 per-task 串行化或键级合并」两案原文）
- app/domains/kb/store.py＋service.py（branch_status 读写点）、app/main.py（装配）
- tickets/phase3/DE-06-切块自检告警进任务卡.md（同载荷面增量票——先此后彼避免冲突，本票后开）

验收:
- [ ] 交错红转绿测试在案（现行缺陷先钉红）
- [ ] G-02 既有测试零跌；与 DE-06 载荷键共存断言
- [ ] 全量闸全绿：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check`（回报附输出原文含通过数）；若涉渲染位另跑 web 侧 `npx vitest run`

回报: 写 tickets/phase3/reports/DE-15.收尾.md（含选型标准）。git 纪律：master 拉
`debt/e2-branch-key-merge`；只 add 本票文件；严禁 `git add -A`。
框架红线: 零新依赖；不动 SSE 帧枚举。
边界红线: 只许触碰 app/domains/kb/ store/service 写入段＋测试位。
〔来源：挂账清单-20261006 §E2〕
