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
