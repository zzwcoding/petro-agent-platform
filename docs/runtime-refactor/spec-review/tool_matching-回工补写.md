- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次只改 `specs/tool_matching.md`，其它文件未动。行号均指改后文件（143 行）。

# tool_matching 规格回工补写（复审发现 #8）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/tool_matching.md:87` | 行为 4「不得为英文列名形（形态判定）」补**判定形**：值整体呈全小写字母开头、仅由 `[a-z0-9_]` 构成的 token 形；标注「**形状定义（本规格自立，待 Owner 过目）**，阶段 5 织网以此为准」；注记真源现状——`walk/11-匹配-工具阀.md` §一／§七仅记「禁英文列名」、未给判定形（§七 Q-A 裁的是工具描述三件套）；真源禁例 `oil_pressure`（`ontology/petro/skill-guides/eval-cases.md` AC-G11 两禁式之英文列名式） | 复审发现 #8（【中】英文列名形形状定义）；即 `spec-review/tool_matching-评审.md` F-06（改述为形态判定）的后续——形态判定无定义形则不可测 |
| `specs/tool_matching.md:109` | 验收行 `::metric_slot_not_english_column` 补判定形（全小写字母开头、仅 `[a-z0-9_]` 的 token 形——形状定义见行为 4），使断言可写：`oil_pressure` 呈形 → 判失败；`日产油量` 呈非该形 → 形状面通过 | 复审发现 #8（验收行原文 :109） |
| `specs/tool_matching.md:142` | 挂钩表补一行「`metric_slot` 英文列名形判定（形状定义见行为 4——本规格自立，待 Owner 过目）｜测试 `::metric_slot_not_english_column`｜待实现」 | 复审发现 #8 配套（硬要求逐条进挂钩表的版式纪律） |

## 上报项（升级 Owner）

1. **英文列名形形状定义无真源**：`walk/11-匹配-工具阀.md` §一仅记「禁英文列名」、§七 Q-A 裁的是工具描述三件套（要／保持／不做），`recon/K-上下文事件指南预算.md:394`（TOOLMATCH_CONTRACT）亦仅「metric_slot 必填非空禁英文列名」——**全证据面均无「何形算英文列名」的定义**。按复审预案，本规格已写为「形状定义（本规格自立，待 Owner 过目）」并升级上报：判定形暂取「值整体呈全小写字母开头、仅 `[a-z0-9_]` 构成的 token 形」（与真源禁例 `oil_pressure` 同形；`oil_output` 系复合注记禁式，归 guide 合同「禁英文列名/复合注记」的另一面）。**Owner 过目后**：若改判，须同步行为 4（:87）、验收行（:109）、挂钩行（:142）三处；若追认，建议回填 `walk/11` 作真源锚。

## 钉落点登记（无落点不硬挂）

- pin-24（相位合同一次性）在本块的回炉轮（拒因回喂）只是消费侧，本体归 state/context——**待 orchestration/context 规格**，不硬挂（与 preconditions 侧登记同源）。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。

---

# 补记（2026-10-15 二轮）：英文列名形判定形 Owner 拍板 B 案，三处同步落地

- **拍板**：上报项 1 经 Owner 定 **B 案**——大小写不敏感 ASCII 标识符形：值整体呈 `[A-Za-z][A-Za-z0-9_]*`（首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬，`oil_pressure` 与 `WELL_NAME` 都咬）。fail-closed 取向：咬错的代价是模型从台账重提议，漏咬的代价是脏指标进查询——宁可误拒重提议，不可漏放列名形。
- **本轮改动面**：`specs/tool_matching.md` 行 87／109／142 三处措辞（行数不变，仍 143 行；测试标识 `::metric_slot_not_english_column` 不变）＋ `docs/runtime-refactor/walk/11-匹配-工具阀.md` 末追加补注节（只追加不改正文）。
  - `specs/tool_matching.md:87`（行为 4）：判定形改为「值整体呈 ASCII 标识符形——首字符 `[A-Za-z]`、其余仅 `[A-Za-z0-9_]`，大小写都咬」；删「**形状定义（本规格自立，待 Owner 过目）**」临时标注，改注「**Owner 2026-10-15 拍板 B 案**（fail-closed：宁可误拒重提议，不可漏放列名形）」；禁例改 `oil_pressure`／`WELL_NAME`（前者保留 AC-G11 锚，后者为大写形补例）；walk/11 现状注记由「§一／§七仅记『禁英文列名』、未给判定形」改为判定形真源锚指其末「补注（2026-10-15 Owner 拍板）」节。
  - `specs/tool_matching.md:109`（验收行）：判定形措辞同步为 ASCII 标识符形（Owner 2026-10-15 拍板 B 案，判定形见行为 4）。
  - `specs/tool_matching.md:142`（挂钩表行）：删「本规格自立，待 Owner 过目」，改「判定形＝ASCII 标识符形，见行为 4——Owner 2026-10-15 拍板 B 案」。
- **真源回填**：`walk/11-匹配-工具阀.md` 末「补注（2026-10-15 Owner 拍板）」节载：「『禁英文列名』的判定形状拍板为 ASCII 标识符形 `[A-Za-z][A-Za-z0-9_]*`（大小写都咬；禁例 oil_pressure/WELL_NAME）；真源锚回本节。」——上报项 1 的「建议回填 walk/11 作真源锚」就此落实（改判同步三处＋回填真源并行完成）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/tool_matching.md`（143→144 行）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **修改点**（行号指改后文件）：
  1. 「触及的模块」依赖表（:36-37）：新增 `bookkeeping` 行（改动类型＝**新增依赖**；说明＝「模型调用发起面：经 bookkeeping.call_model（单点发起），本块不直引 gateway_adapter」）；同表 `gateway_adapter` 行说明由「模型调用唯一出口；本 spec 只消费」改为「模型出口（唯一出口仍归它）；本块不直引——经 bookkeeping.call_model 发起」。
  2. 「框架与依赖红线」（:78）：「模型调用唯一出口＝gateway_adapter」改为「**模型调用发起面＝`bookkeeping.call_model`（单点发起）；其内部唯一出口＝`gateway_adapter`**」，补「import 落点＝`appv2.runtimev2.bookkeeping` 包根——R2 禁深层子模块」；R7 括注改准为「禁直引 `appv2.infra.llm_client`——模型出口仍唯一归 `gateway_adapter`」＋「发起面收敛为规格层 doctrine，不设闸——主窗 2026-10-15 裁」。
  3. 「框架与依赖红线」禁手写替代条（:81）：R7 括注由「模型只经 `gateway_adapter`」改为「模型出口唯一归 `gateway_adapter`——发起经 `bookkeeping.call_model`」。
  4. 「依赖与风险」依赖行（:122）：补 `bookkeeping`（模型调用发起面——`call_model` 单点发起）；`gateway_adapter` 括注改为「经 `call_model` 的内部唯一出口，本块不直引」。
  5. 「与闸的挂钩表」（:138）：「模型调用只经 `gateway_adapter`」行改为「模型调用经 `bookkeeping.call_model` 发起（单点发起；其内部唯一出口 `gateway_adapter`）」；挂钩列注「出口面 R7；发起面为规格层 doctrine，不设闸」；现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R7「只经出口」＋R8 语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：逐条实读 `tools/importlinter_v2.toml`——R7（forbidden＝`appv2.infra.llm_client`；source 含 `appv2.runtimev2.bookkeeping`）与 R2（业务相位 forbidden 含 `appv2.runtimev2.bookkeeping.*` 深层子模块、不含包根）均与新 doctrine **无字面冲突**。实现期注意：相位 import 只许 `appv2.runtimev2.bookkeeping` 包根（R2 面）。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。
