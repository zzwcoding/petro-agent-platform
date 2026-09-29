# AGENTS.md · petro-ontology 仓库协作说明

> 任何 agent/新窗口进入本仓，先读本文件恢复上下文。

## 这个仓库是什么

**Petro-Agent 平台的本体真源仓**（all-agent 式：Git+YAML 唯一真源、进仓过语义闸、提案走 proposal_check、MR 由人完成）。

- **上游蓝本**：`~/Downloads/All-agent`（企业语义中台，skill+脚本形态）。本仓 fork 其 schema/tools/bohai 域，**验证 all-agent 本体工程在真实平台工程中的可行性**（验证判据见主仓 `docs/adr/0004`）。
- **下游消费方**：`~/Downloads/teach-petro-agent`（Petro-Agent 主平台）。其 semantics 模块同步器 `sync_from_ontology_repo()` 消费本仓合入事件，把 YAML 投影为台账 DB 行。**台账行禁手改，改本体只在这里。**
- 建造依据：`teach-petro-agent/docs/adr/0004-本体真源回归与all-agent衔接.md` + `docs/roadmap.md` 轨道 0。

## 目录地图

| 路径 | 是什么 |
|---|---|
| `schema/` | 八模型 schema + 模型注册表 + 依赖白名单（fork 自 All-agent，schemaVersion 1.0.0 契约——同步器钉住此版本） |
| `tools/` | 语义闸 schema_check（L1–L4）+ 提案闸 proposal_check + 图派生物 graph_index + 语义服务 semantic_service_core + 新域接入 onboard_check + 出厂集 fixture_run |
| `fixtures/` | 出厂集（pattern-library：AC1–7 断言与非法变体——"约定不落闸等于没有"） |
| `bohai/` | 渤海域本体 fork（对齐底稿，注源 R5=主仓设定书 v3；原仓 All-agent/ontology/bohai 不动） |
| `alignment/` | **bohai ↔ 平台七域对齐矩阵**（轨道 0 首任务产出，主仓 C1 合同+页面种子为 B 侧真源） |
| `petro/` | 平台七域模型（对齐→fork+增补→语义闸全绿后的成品；同步器拉取目标） |

## 工程体系声明

- 本仓走 **all-agent 工程纪律**（sdd-flow2 资产纪律），**跳过其中教学性环节**（朗读关/教学文/lessons 逐行讲解类）——工程闸（语义闸/出厂集/提案闸）全保留，教学产物一律不产。
- 主平台与数据面代码工程走 sdd-flow，见各自仓。

## 改动纪律

1. **模型文件进仓必过语义闸**：`python3 tools/schema_check.py petro` 全绿才可合入（L1–L4 任一红即拒）。
2. **逐元素注源**：每个元素注「设定书 §x / 合同册锚 / 裁决记录 PROP-*」；设定书没有的一律不建（不发明业务事实）。
3. **变更走提案**：内容变更先 `proposal_check` 过确定性预检，Owner 裁决后进仓；平台侧变更意向经主平台 C2 提案池→自动 MR 回流本仓（阶段 3 接线）。
4. **schema 契约**：schemaVersion 1.0.0 被主平台同步器钉住；schema 升级须与主仓联合变更（先改这里登记 CHANGELOG，再改同步器）。
5. **每项工作一提交**，提交信息写清对齐/增补/裁决依据。

## 新窗口入口

1. 读本文件 → `alignment/bohai-to-platform.md`（对齐矩阵，了解七域缺口）→ 主仓 `docs/adr/0004`
2. 报告"当前在轨道 0 第几步、产物 X 已有/缺失"，给出下一步，停下等拍板
