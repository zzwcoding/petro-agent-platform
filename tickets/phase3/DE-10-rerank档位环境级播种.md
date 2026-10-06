# DE-10 rerank 档位环境级播种（运行面——换库不回退）

> 状态：⬜ 可开工 ｜ 依赖：—

任务: rerank 档位（fast/llm）存 DB 配置行；换新库（无配置行）时静默回落默认 fast——已实证两次
（Q8 云上全量误跑 fast；Q9 前重播种 #CFG-20261007-01）。本票给档位加环境级播种。交付物：
1. 语义定案（票内写明并测试钉死）——**env 仅播种，DB 行恒胜**：配置行不存在时，若环境变量
  `RERANK_TIER` 在位（合法值 llm/fast，非法值拒绝启动不静默）→ 以 env 值建行；行存在时 DB 胜
  （运行中变更单改行后重启不丢）；env 缺省→现状行为零变化。
2. 播种点：配置读取/装配路径（domain.py 种子值消费处——先读定位，缝票内定案），启动一次播种
  ＋日志一行（「RERANK_TIER 播种＝llm」/「DB 行在位跳过播种」）。
3. 部署件：deploy/cloud/compose.yml backend＋worker 增 `RERANK_TIER=llm`（注释注明语义）。
4. 三态测试：无行＋env→llm；无行＋无 env→fast（现状）；有行＋env→DB 胜。

先读:
- 059e8fc 提交说明「运行面备注：rerank 播种应环境级（换库即回默认已实证两次）」
- app/domains/chat/domain.py（rerank 档位种子默认值与读取路径——grep rerank 定位消费点）、
  app/main.py（启动装配缝）、app/domains/chat/chains.py（_rerank_evidence 档位分派）
- deploy/cloud/compose.yml（env 注入位置）；#CFG-20261006-01/#CFG-20261007-01 变更单先例

验收:
- [ ] 三态测试绿；非法 env 值拒绝启动（不静默回落）
- [ ] 既有 rerank 行为测试零跌（llm 档三段式/回退链不变）
- [ ] 全量闸全绿：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check`（回报附输出原文含通过数）

回报: 写 tickets/phase3/reports/DE-10.收尾.md。git 纪律：master 拉 `debt/rerank-env-seeding`；
只 add 本票文件；严禁 `git add -A`。
框架红线: 零新依赖；不改 llm 档三段式与回退语义；DB 配置行格式零变化。
边界红线: 只许触碰配置播种缝（chat 域/main 装配）＋deploy/cloud/compose.yml＋测试位。
〔来源：059e8fc 运行面备注；Q8/Q9 实证〕
