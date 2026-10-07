# FX-11 few-shot 例对齐本体声明方向（R4-B3-1 高项）

> 状态：⬜ 可开工 ｜ 依赖：B2/B3 合入 master
> 来源：审查 R4（reports/审查R4-B系-20261007.md）L0 裁决案①。**Owner 备选**：若业务需要 井—承载→平台/
> 井—隶属→油田 形状，拍板后改走案②（本体增 ASSOC），本票废止。

任务: few-shot 出厂例与严格闸声明终点组对齐（app/domains/derivatives/domain.py:486-487 区）：
1. 例 1「W-11井|承载|CEP-C平台」（井—承载→平台，声明＝平台→井）→ 改为声明方向演示：例句文字照
   语料原文（「W-11 井承载于 CEP-C 平台」类），三元组侧输出「CEP-C平台|承载|W-11井」——兼任别名
   规范名演示（与 B2 别名段对齐，两裁决一次收口）。
2. 例 2「W-11井|隶属|渤中34-5油田」（井—隶属→油田，声明＝区块→油田）→ 换一个**声明内形状**的
   语料实例（候选：配注/受效/作用于/下入/坐封 在 6 篇语料的实句——选一句最能演示「文本→声明方向
   归一」的，出处落回报）。
3. 全部 few-shot 例过闸自检断言（新增测试：出厂例三元组逐一喂 legal_triples 必须全过——防再漂）。
4. 红先绿后：现行例喂闸→红；改后→绿。

先读: tickets/phase3/reports/审查R4-B系-20261007.md B3-1 条＋裁决节；config/relation_types.json
（endpoint_groups）；app/domains/derivatives/domain.py few-shot 段与 gate 段；B2-01 收尾报告（别名段现状）

验收:
- [ ] 出厂例全过闸断言红先绿后；既有抽取测试零跌（桩适配除外——适配处逐条记回报）
- [ ] 全量闸：`uv run ruff check app tests migrations tools && uv run mypy app && uv run pytest -q && uv run lint-imports && uv run python tools/contract_coverage.py check && uv run python tools/debt_markers.py check` 全绿（回报附输出原文含通过数数字）＋`bash ontology/ci.sh`

回报: 写 tickets/phase3/reports/FX-11.收尾.md。git 纪律：master 拉 `gov/fx11-fewshot-align`，只 add
本票文件，严禁 git add -A。
框架红线: 零新依赖；闸实现零改动（只动 few-shot 常量与测试）；本体零改动（案②才动）。
边界红线: 只许触碰 app/domains/derivatives/domain.py few-shot 段与测试位。
〔来源：审查R4 L0 裁决节〕
