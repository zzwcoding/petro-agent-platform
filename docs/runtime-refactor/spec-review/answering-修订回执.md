- 日期：2026-10-15 ｜ 状态：**修订回执**
- 本次只改 specs/answering.md，其它文件未动。

## 一、逐条回执

| 修复单编号 | 已改／未改 | 改在哪（节名＋行号） | 备注（未改必写原因） |
|---|---|---|---|
| X-1（A-2） | 已改 | `## 行为约定` 第 10 条（`:80`） | 保留数字但补真源锚点：现状真源＝`docs/runtime-refactor/recon/L2b-作答装配与回声.md`（`_ANSWER_REQUIREMENTS`，现 **7 条**），并注「**V2 条数以 `prompts` 合同定稿为准**」——不再是无出处的裸数字（见 §三 X-1 取舍） |
| X-2（A-3） | 已改 | `## 框架与依赖红线` R7 行（`:64`） | 补「验收写法：模型调用点只出现在该出口 ＋ 调用行为测试绿」＋ 一条「无旁路」行为断言（写法照 `specs/understanding.md`／`specs/tool_matching.md` 同款） |
| X-3（A-4） | 已改 | `## 与闸的挂钩表`（`:124`：删 tools/R6 行、换 transport 行；`:129`：末行「接不上闸」原因改准） | (a) 删掉「只经 `tools` 公开面接触引擎｜边界闸 R6」行（本规格不涉 `tools`）；(b) 如实写明「`transport` 公开面当前无任何边界闸覆盖」并降维为**人审＋原因**（见 §三 X-3 取舍）；末行覆盖声明改为「能降维的部分（相位互不 import）已由边界闸 R1 覆盖」 |
| X-4（A-5） | 已改 | `## 不做什么` 第 3 行（`:17`） | 锚点补文件路径：评审 E-10 处置（`docs/runtime-refactor/spec-review/execution-评审.md` E-10） |
| X-5（A-6） | 已改 | `## 接口定义` 接口说明列（`:57`，新增一条） | 注明「大结果引用经 `seq → observation.ref`（`MaterialRef`）可达」，与 `specs/execution.md` 字段口径显式对齐（真源 `walk/裁决表.md` §14-B） |
| X-6（A-7） | 已改 | `## 框架与依赖红线`（`:64`／`:65`／`:67`） | 「禁手写替代」行补对应闸名（`tools/importlinter_v2.toml` **R7 契约**）＋ 验收写法「无旁路」行为断言；整节句式对齐样板（R5b 行补「（框架只许在 `orchestration`）」，`transport` 无闸一面交叉引挂钩表） |
| X-7（A-8） | 已改 | `## 不降级与静默禁令`（`:85`） | 事件类型（`text`／`citation`／`verdict`）补引真源：`（类型取自 `synth/S6-事件与帧目录.md`）` |
| X-8（A-9） | 已改 | `## 行为约定` 第 4 条（`:74`） | 改写为「本块只消费 `context` 的编译出口、只断言不实现」；「每次模型调用**必须有 Manifest 在场**（缺失＝判失败）」，并注「Manifest 的编译归 `context`」 |
| X-9（A-10） | 已改 | `## 行为约定` 第 7 条（`:77`） | 注明「**`verdict` 帧的批次落定由 `orchestration` 协调**，本块只保证自产部分（引用块／`citation` 帧）就位」 |

**计数：已改 9／未改 0。**

## 二、改动行数

- 新增 **1** 行（X-5 的接口说明列）；删除 **0** 行；修改 **10** 行（`:17`／`:64`／`:65`／`:67`／`:74`／`:77`／`:80`／`:85`／`:124`／`:129`）。
- 文件总行数 **128 → 129**；`状态: 草稿` 未动；十个 `##` 节标题逐字保留、顺序未变。

## 三、两道闸的实跑输出

- `uv run python tools/ref_resolvable.py check` → **绿**：`真源引用可解析闸绿：12 份规格的真源引用与边界规则编号均可解析。`（exit 0）
- `uv run python tools/check_specs.py` → **红**：`FAIL  modules.md: 模块 \`answering\` 依赖 \`text\`，后者未声明（拼写错误或漏卡）` ／ `spec gate: 1 失败 / 0 警告`（exit 1）

> **该红与本代理改动无关、且不在本代理可改范围**：唯一 FAIL 出自 `specs/modules.md`（阶段 2 改卡 A-1 的落点），非 `specs/answering.md`。已用基线（`HEAD` 版 `modules.md`）实测对照：`spec gate: PASS（0 警告）`——即该 FAIL 由阶段 2 改卡引入。详见 §四。

## 四、发现但修复单未覆盖的问题（只记录、不处理）

1. **`specs/modules.md` 阶段 2 改卡使 `spec gate` 变红（本次唯一红源，未改）**：`## answering`「### 依赖」行现为 `- 模块: `context`、`prompts`、`gateway_adapter`、`state`、`transport`（`text` 帧的增量发射，只经其公开面）`。`tools/check_specs.py` 的 `parse_modules` 用 `TICK.findall` 抓取该行**全部反引号 token**，把帧名 `` `text` `` 也当成模块名 → 判「依赖 `text`，未声明」。**建议**（交 L0／阶段 2 处理，非本步）：把括号里的帧名 `text` 去反引号（或改写措辞），使依赖行只含真模块名。本代理只读该文件，未动。
2. **R2 与 X-3 口径的字面张力（仅记录）**：`tools/importlinter_v2.toml` 的 R2 契约实际**禁止**业务相位 import `transport` 等公共层块的**深层子模块**（即「只经包根」），与 X-3 采用的「`transport` 公开面当前**无任何**边界闸覆盖」在字面上不完全一致——R2 管的是「深层子模块导入」，「不自行拼 wire 帧／不直连 SSE 通道」这一面确无闸。本步照修复单口径（无闸）落笔，未自行并入 R2。
3. **基线对照的暂存操作（net-zero，如实登记）**：为确认 §三 的红源归属，曾把 `specs/modules.md` 临时换回 `HEAD` 版跑一次闸后**立即原样还原**（`git diff --stat` 复原为同一处 `1 insertion(+), 1 deletion(-)`）。最终工作区除 `specs/answering.md` 外无净改动。

## 五、X-1／X-3 取舍（供复审核）

- **X-1：选「现状真源锚点 ＋ V2 待定」写法**（未采用「去掉裸数字」写法）。理由：修复单给了二选一，L2b（`_ANSWER_REQUIREMENTS`）是 V1 现状真源、确实记 7 条，**给出 `文件#节` 锚点后不再是「无出处的裸数字」**；同时明写「V2 条数以 `prompts` 合同定稿为准」，把 V2 的不确定性也标出。`specs/preconditions.md:70` 同款（「现为 `synth/S3` C-01 所记的 8 个判定位」）。
- **X-3：transport 行取「无边界闸 → 人审＋原因」写法**（未采用 AST 断言写法）。理由：修复单允许二选一；若写 AST 断言需绑一个测试标识（`tests/domains/test_v2_answering.py::…`），但该标识会**要求 `## 验收测试` 表新增一行**，而修复单未授权改验收测试表（照抄式纪律下不自行扩面，对照 `specs/execution.md` 的 `::no_direct_storage_symbols` 是「验收表＋挂钩表」双落）。故取「人审＋原因」，与 `spec-format.md` §五「剩下的才写人审＋原因」相容；原因如实写为「R1–R8 的 forbidden 面无 `transport` 公开面一面（R6 的 forbidden 面是引擎 knowledge/query/retrieval，与 `transport` 无涉）」。
