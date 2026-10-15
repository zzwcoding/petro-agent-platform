# modules 卡回工补写

- 日期：2026-10-15 ｜ 状态：**回工补写**（`## parsing` 卡指纹器材 L0 补录；本件为首建）
- 本次只改 `specs/modules.md`（597→603 行）`## parsing` 卡「公开接口」节＋本记录。未 git commit（主窗统一提交）。

## 流水 31 裁决落笔（卡级 L0 P-01＝指纹器材四件补录）——2026-10-15

- **依据**：`parsing-评审.md` P-01（**L0，卡级**）——指纹器材四件＝卡缺公开成员（S-2 类）；「指纹器材公开化（去下划线）」＝窗 B 评审定案项（`specs/parsing.md` 差异点⑦）。主窗派卡补录，卡补录即 L0 清零动作。
- **修改点**（`specs/modules.md` `## parsing` 卡「公开接口」节，:391-394）：补指纹器材四件，签名照 `specs/parsing.md` 接口定义节④**逐字**——`payload_fingerprint(payload) -> str`／`discover_fingerprint(tool_name, args) -> str`／`emission_fingerprints(plan, retrieval_need) -> tuple[str, ...]`／`is_same_param_replay(fingerprints, executed) -> bool`，各带该节原注（R-A1-24／R-A1-25／R-A1-26／R-A1-27-28）；节内注「L0 补录 2026-10-15——签名照 specs/parsing.md 接口定义节④逐字，「指纹器材公开化（去下划线）」＝窗 B 评审定案项」。
- **未随批改面（登记交主窗）**：P-01 处置的其余卡面补录项不在本批票面——V2 定案公开成员（`parse_tool_match`／`ClarifyEmission`／`Subtask` 等）、`parse_question_group` 返回形勘正（`-> ClarifyEmission | str`）、「族名单以 parsing 规格接口定义为准（闭世界）」注记——仍按 P-01 处置表登记待派。
- **验证**：三闸绿（同批实跑：spec gate PASS（0 警告）／ref_resolvable 绿（21 份规格）／lint-imports **18 kept, 0 broken**）。均 exit 0。
