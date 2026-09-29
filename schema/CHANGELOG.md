# ontology/schema CHANGELOG

schema 三件（`schema.md` 人读 + `model-registry.json` / `model-deps.json` 机读）的版本演进账。
版本号记在两份机读表顶层 `version`（语义化三段，两表必须同步）；本文件记**为什么变、迁移注意什么**。
演进路由：元模型错 → 框架版本演进（CHANGELOG + 版本号 + 迁移票伴随实现票，CONTEXT.md 信号路由表）。

## 1.3.0 · 2026-09-29 · M3 指标口径登记字段（对齐矩阵裁决 e/g；轨道 0 fork 批前置）

**变更点**

- M3 规则模型新增**可选指标口径字段组**（schema.md §6）：`mark`（★/☆ 展示标记）/ `grain`（统计粒度）/ `unit`（计量单位）/ `modifiers`（修饰词列表）/ `calibers`（口径支列表）/ `defaultCaliber`（默认口径标识）/ `ambiguous`（歧义标记）/ `dispute`（口径争议注记）——C1 指标口径卡八项的结构化登记位（alignment/bohai-to-platform.md §3b 结构级，裁决项 e 案 2 限口径内容字段）。粒度/单位/修饰词/口径支/争议注记是指标口径的本体内容（判据②零手养要求仓内有真源），非运行期派生。
- **`slot_name` 不落仓**：slots 剥法（剥首 ★/☆ → 剥尾括注 → 剥尾 η/T、β 保留）由服务端单点执行（票 93 禁止下游自留拷贝），slot_name 一律由 name+mark 派生——域文件存储该派生值即违裁决 e。
- `defaultCaliber` 本次只定义不填值（C1 仅指标 #2 登记 default_caliber，种子现值待素材），其余七字段在 petro/ M3 迁移批按真源原文填值。
- 依据：主仓 `docs/adr/0004-本体真源回归与all-agent衔接.md` + 对齐矩阵 §4 裁决项 e/g（Owner 2026-09-29 全部「按建议倾向执行」）。

**版本演进说明**

- 两份机读表顶层 `version` 由 `"1.2.0"` → **`"1.3.0"`**（model-deps.json 本次仅版本同步，无内容变更）。
- **schema 契约版本**（域 manifest `schemaVersion`，主平台同步器钉住面）`1.0.0` → **`1.1.0`**：受控小版本——只加可选字段的向后兼容演进（裁决项 g 案 2 范围收紧）。petro 域 manifest 即以 1.1.0 声明；**主仓同步器钉版升级（1.0.0→1.1.0）为联合变更待办**（先仓后同步器，本仓 AGENTS.md 纪律 4）。

**迁移注记：存量域零改动兼容**

- 八项全部可选：必填闸 `requiredElementFields` 未动、`lockedFields` 未动、依赖白名单未动——bohai 存量 96 元素与全部出厂集不受影响，「元素级存在即放行」保证老文件零改动过闸。
- 凡涉必填结构/换义锁定字段的演进一律不做（裁决项 g 前提原文）；裁决项 d（工作流账号绑定两态）与 f（join_key/白名单机器键）按裁决走同步器投影层与 M1 ASSOC.referenceField 承载，**不动 schema**。

## 1.2.0 · 2026-09-19 · 票 13：机读必填字段闸 + AC6 反向豁免

**变更点**

- `model-registry.json` 每模型新增 **`requiredElementFields`**（前缀→必填字段键列表）：八模型逐元素结构性必填下沉机读表，schema.md 退为目录页。口径 = 身份（id/name/具名 ID 键、schema.md ✓ 的 alias）+ 类型判别（aggregateType/associationType/behaviorType/ruleType/actorType/targetType/flowType/objectType/screenType）+ 检查锚点（M7.behaviorRef、PERM.targetRef、M6.roleRefs/activities、M2.ownerEntity/appliedRules/requiredPermissions、M6.businessObjectRefs、M5 roles/inheritsFrom/permissions）+ 载荷容器（AGG.attributes、DICT.types、M7.sourceObjects、MU.elements/actions）。逐模型推导表与两域（bohai/valid-domain）100% 呈现率证据见 `lessons/13-机读必填字段闸.md`。
- `tools/schema_check.py` 新增 **L1 required-field** 元素级闸（缺必填字段/空壳文件；文件名错挂的文件跳过本闸让位 filename-mismatch）与 **L4 missing-model-file** AC6 反向闸（profile 启用却缺文件且 manifest `omittedModels` 无带理由豁免 → 红；豁免条目缺 reason = 无效；引用未注册模型 = L1）。
- **manifest 结构变更**：新增可选清单 `omittedModels: [{model, reason}]`。仓内全部域（bohai、四套出厂集域副本、既有负变体）已按新标准升级登记豁免，红因保持唯一；bohai 的 MU 豁免理由引 docs/walkthrough/step2-mr-adjudication.md（R5 无界面素材证据）。
- 出厂集 `fixtures/schema_check/` 增必填闸套件：`req-ac4-reserved-fields` 预留字段正例（REQ-AC4）+ `req-ac1/2/3a/3b` 必填负变体（REQ-AC1/2/3）+ `req-ac5/6` AC6 反向无/有豁免对（REQ-AC5/6），断言标签加 REQ- 前缀防撞（手法沿票 10/11）。cons-ac1 的 M7 参照补 sourceObjects（新必填集入集字段，升级样本不破其一致性对红因唯一性）。
- `tools/check_citations.py` 新增引用清单比对检具（配套单测；接线 fixtures/semantic-service CIT-01–05，审查一 P2「正文↔清单逐条比对」落闸）。

**版本演进说明**

- 两份机读表顶层 `version` 由 `"1.1.0"` → **`"1.2.0"`**（model-deps.json 本次仅版本同步，无内容变更）。

**迁移注记：旧域兼容面**

- 域 manifest 不写 `omittedModels` 也能过闸，前提是 profile 组合内每个启用的模型都有文件——**凡有有意缺文件的域必须补豁免条目**（bohai 的 MU 即先例），否则 AC6 反向红。
- 新增模型或给既有模型扩 `requiredElementFields` 时，跑全量语义闸（`python3 tools/schema_check.py ontology` + 全部出厂集）核对合法域零新增红灯，呈现率不足的字段先进缺口清单（lessons/13）。
- 域 manifest 的 `schemaVersion` 不强制联动本版本号（现状闸不校验联动），各域按需自行演进。

## 1.1.0 · 2026-09-19 · 票 10：术语模型 GLS（元模型演进）

**变更点**

- 新增第 8 个模型类型 **GLOSSARY（GLS）**：文件 `glossary-model.yaml`（照 `mu-ui-model.yaml` 非数字先例）、ID 前缀 `GLS-`（`GLS-{域}-{Seq}`）、camp=business-core、consumers=[runtime, build]。OMF v6/v9 均无此模型，属本仓自定义扩展——术语（概念定义/别名/解释）与 M1 DICT（值域字典）不是一回事。
- **profile 组合**：GLS 入 v9-full 与 headless，**不入 v9-core**（四模型最小核保持原样，术语属增强件；"未启用"因此有可测负变体 GLS-AC2）。
- `model-deps.json`：idPrefixes 增 `GLS-→GLS`；refKeys 增 `relatedObjectRefs`；edges 增 `GLS.relatedObjectRefs→[M1]`（GLS 依赖白名单只此一条，单向；GLS→GLS 不设边，见 schema.md §11）。
- `tools/schema_check.py` 新增 **L1 filename-mismatch** 检查：模型文件名必须等于注册表该模型 `yamlFile`（真源=机读表，非脚本硬编码）。对既有七模型是"一模型一 YAML、固定文件名"约定（schema.md §1）的闸上强化；对 GLS 承载票 10 AC4（model_type 写错如 OBJECT / GLS 文件名错挂 → 红）。
- 出厂集 `fixtures/schema_check/` 增 GLS 套件：`gls-valid` 正变体 + `gls-ac2-core-profile` / `gls-ac3-dangling-ref` / `gls-ac4-filename-mismatch` 三负变体，断言 GLS-AC1–4。

**版本演进说明**

- 两份机读表顶层 `version` 由整数 `1`（票 03 初版未落语义化号）演进为 **`"1.1.0"`**，本票起立约：版本号语义化三段、两表同步、每次演进必配本文件条目。

**迁移注记：旧域零改动兼容**

- 无 `glossary-model.yaml` 的域**不校验 GLS**（缺在场不校验是既定行为，AC6 同款语义）——现有域（`ontology/bohai/`、fixture `valid-domain` 等）零改动仍全绿。
- v9-core 域出现 GLS 文件 = L4 红（GLS-AC2）；GLS 文件 model_type 写错或文件名错挂 = L1 红（GLS-AC4）；术语 relatedObjectRefs 悬空 = L2 红（GLS-AC3）。
- 域 manifest 的 `schemaVersion` 不强制联动本版本号（现状闸不校验联动），各域按需自行演进。
