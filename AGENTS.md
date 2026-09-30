# AGENTS.md —— petro-agent-platform 仓协作说明

## 这个仓是什么

Petro-Agent 主平台的**真实实现仓**（后端+前端），与 teach-petro-agent（设计/教学双轨仓）、petro-ontology（本体资产仓）、tpa-data-plane（数据面仓）鼎立。本仓只放实现代码，**合同/架构/ADR 真源在 teach-petro-agent，禁止把合同正文复制进本仓**（引用路径即可）。

## 硬纪律

0. **嵌套独立仓**：`ontology/` 与 `data-plane/` 是平台文件夹内的**独立 git 仓**（各归各文件夹，2026-09-30 改判，submodule 注册已退除）——①各自提交互不牵连，平台仓 .gitignore 排除之；②平台仓不记录其版本（gitlink 已退，单人开发各走最新）；③改子仓纪律仍守各自 AGENTS.md（本体=all-agent 纪律，数据面=其 ADR 链）。
1. **合同驱动**：每个端点实现前先引用合同册（`teach-petro-agent/specs/api/<页>.md` 端点号）；字段名/语义/错误码与合同不一致＝缺陷，改合同回设计仓改，不在本仓私改语义。
2. **四层 + B1–B16**：层间依赖单向向下；边界规则进 import-linter，CI 红即不过。新增 import 前先看 pyproject 的 import-linter contracts。
3. **统一出口**：DB 只经 `infra.db`（B3）、LLM 只经 `gateway.complete`（B6）、审计唯一写口 `security.audit`（B12）、时间一律 `infra.clock`（B14）。
4. **身份桩**：开发期 `X-Dev-User` 头即身份；不许在代码里硬编码用户；OAuth2.0 替换只动 `security.resolve_actor` 实现。
5. **每票一提交**：tickets/ 一票一分支一提交，验收（票面对象全勾）过才合。
6. **子代理一律全新**：派子代理只许新开无历史记录实例，提示词自带完整上下文。
7. **业务事实零发明**：业务语义疑问查 teach-petro-agent/docs/business-setting.md 与合同册，查不到就问 Owner，不许编造。

## 与教学仓的关系

teach-petro-agent 的"不建 app/ scripts/"纪律**不约束本仓**（那是教学轨纪律——ADR-0005）；本仓也不要改教学轨任何文件。
