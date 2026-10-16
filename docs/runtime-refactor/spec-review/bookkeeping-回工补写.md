- 日期：2026-10-15 ｜ 状态：**回工补写**（复审⑦ V6/F1＋V4/F2＋F3 修法；本件为首建——此前本规格无回工补写记录）
- 本次只改 `specs/bookkeeping.md`（183→189 行）＋本记录，其它文件未动（`specs/state.md` **一字未动**、`specs/modules.md` 未动——卡级欠账见「上报项」）；未 git commit（主窗统一提交）。

## V1 修法记录（复审⑦：V6/F1 接口补 `set_intent` ＋ V4/F2 补 `append_contract` ＋ F3 悬空验收标识入表）——2026-10-15

### 1.（V6/F1）接口定义节补 `set_intent`——已补

- 「接口定义」共享写口代码块（`specs/bookkeeping.md:65`）新增 `def set_intent(state, intent: str) -> None: ...`（注释：「next_intent 唯一写口（闭世界越界即拒；路由决策仍在 orchestration——行为 6）」），签名与 `specs/modules.md:335` 卡面**逐字同形**。此前行为 6（`next_intent` 的唯一写口＝本块 `set_intent`，BZ-1/BZ-2 处置产物）与验收行 `::set_intent_single_port_closed_world` 已引用该函数，接口块漏列——本批补齐，卡面 12 成员对齐。

### 2.（V4/F2）补合同标记写函数 `append_contract`——已补（三处：接口＋行为＋验收）

- **接口**（:66）：新增 `def append_contract(state, phase: str) -> None: ...`（注释：「contracts_appended 唯一写口（幂等；越界相位抛错——钉 pin-24 写入面，行为 8）」）。签名按本块既有「state 首参」体例落（派单文本写作 `append_contract(phase) -> None`，与同单 `set_intent(intent)` 同为省略 state 的简写——照 `set_intent(state, intent)` 卡面同款展开，特此注明）。
- **接口 bullet**（:79）：`phase` ∈ **合同追加相位闭世界**（`decision`｜`clarify`｜`toolmatch`——合同文本追加面的相位标记集）；现状锚＝`appv2/runtime/graph.py` 三处 `contracts_appended` 标记写入，写手面真源＝`synth/S5-RunState字段矩阵.md` `contracts_appended` 行（写手 M1／M2／M3）；越界相位抛错（fail-closed，同本块错误契约）；幂等（已标记再标记＝无操作）；**`contracts_appended` 字段语义真源＝`specs/state.md` 行为 5**（本规格不复制其语义，本块只认领唯一写入面——主窗裁「谁写口谁拥有」）。闭世界取值集以现状标记集锚定，未自造业务相位名；重写期若标记改名，属该实现批同批改。
- **行为约定**（行为 8，:103）：由「`contracts_appended` 标记过的相位不再重复追加合同文本——`append_message` 的调用方据此幂等」改写为「**唯一写函数＝本块 `append_contract(state, phase)`**——相位经它标记；已标记再标记＝幂等无操作；越界相位抛错」，断言补「`contracts_appended` 的写操作只出现在本块该函数（并入行为 1 的写口单点断言集）」。
- **验收测试表**（:134 新增行）：绑 `tests/domains/test_v2_bookkeeping.py::append_contract_sole_write_idempotent_closed_world`（标识体例照既有行）。
- **挂钩表 pin-24 行**（:182）：由「相位合同一次性（写入面）｜钉 pin-24（P1）；测试 ::contract_once」更新为「相位合同一次性（**写入面落点＝`append_contract`**——`contracts_appended` 唯一写函数，越界相位抛错）｜钉 pin-24（P1）；测试 ::contract_once ＋ ::append_contract_sole_write_idempotent_closed_world」——钉 pin-24 的写入面落点即本函数。
- **风险节债务清账**（风险 11，:167 新增）：登记「`contracts_appended` 写入悬空」（复审⑦ V4：字段语义在 `specs/state.md` 行为 5、`specs/prompts.md` 侧称「追加记账归 state 行为 5」——写函数无人认领，写入面悬空）→ 标 **已清（本批）**：写入面归本块 `append_contract`；检测＝`::append_contract_sole_write_idempotent_closed_world`。**`specs/state.md` 未动**（其行为 5 字段语义面原样成立）。

### 3.（F3）红线引用的 `::no_direct_state_write_in_phases` 入验收表——已补（二选一取「入表」）

- 「验收测试表」（:127 新增行，紧随 `::single_write_port` 行）：「相位侧不得绕过写口直改状态字段（红线「禁手写替代」的相位侧半面——与 `::single_write_port` 同断言集的相位侧扫描）｜`tests/domains/test_v2_bookkeeping.py::no_direct_state_write_in_phases`」。
- **取舍理由（照要求记录）**：红线「禁手写替代：不得绕过写口直改状态字段（相位侧同禁）」早已把该测试标为本块的验收写法（对应闸：无专属闸→人审＋测试 `::no_direct_state_write_in_phases`），但验收表 20 行里没有它——悬空验收标识。该测试与 `::single_write_port` 是同一断言集的两个扫描方向（本块内写点单点 ↔ 相位侧禁直写），由本块验收件承载最贴（写口的唯一性本来就是本块主张）；故取「入表」而非改红线措辞。挂钩表「共享写口单点、相位禁直写」行（:180）同步补挂该标识。

### 上报项（非本批擅改，报主窗）

1. **卡级欠账**：`specs/modules.md` `## bookkeeping` 卡公开接口（12 成员）**缺 `append_contract`**——本批只在规格侧落函数，卡面公开接口与规格接口定义现差一件；按本仓先例（卡级修正＝窗 A 亲改＋记流水），留主窗落卡。
2. **`specs/prompts.md` 两处与 V4 处置字面不一致**（该文件窗 B 在改，本批未动）：`:19`「合同消息的追加记账与重发判定（contracts_appended）｜state（行为 5 已定稿）＋**追加执行归 orchestration**」与 `:163`「**追加记账归 `specs/state.md` 行为 5**（已定稿，测试 `contracts_appended_idempotent`）」——按 V4「谁写口谁拥有」，追加的**写面**归 `bookkeeping.append_contract`（orchestration／相位经写口调用），state 行为 5 只是字段语义面、无写函数。建议窗 B 随在途修订把两处对齐为「追加经 `bookkeeping.append_contract` 写口」，避免「两头都不认」复发。
3. **闸层核对结论（非冲突）**：`tools/importlinter_v2.toml` R2（相位禁引 `bookkeeping.*` 深层子模块、包根放行）与 R7（source 含 bookkeeping、forbidden 只 `appv2.infra.llm_client`）与本次补函数无字面冲突，未改 toml。

### 验证

```
$ uv run python tools/check_specs.py
spec gate: PASS（0 警告）                                  # exit 0

$ uv run python tools/ref_resolvable.py check
真源引用可解析闸绿：20 份规格的真源引用与边界规则编号均可解析。   # exit 0
```

（本批改后实跑均 exit 0；`::append_contract_sole_write_idempotent_closed_world`／`::no_direct_state_write_in_phases` 为阶段 5 承诺标识，spec 状态＝已定稿，闸不要求测试在场。）

## W3 前规格微修正批：`gates` 闭世界补注（2026-10-16，流水 52-B）

- 依据：`docs/runtime-refactor/00-决议与方法.md` 流水 52「**裁定 B＝`converge` 注记 `gates` 闭世界以七限额键名为准**」——本规格行为 11「`gates` ⊆ 轮数／时长两项」系**旧两限额世界措辞**，与 `LimitHit.limit` 七键闭世界（新单源）冲突。
- 范围：只改 `specs/bookkeeping.md`（:78／:106 两处）＋本记录；其它文件未动；未 git commit（主窗统一收口）。

### 改动（两处同一口径，不留第二说法）

| 落点 | 改前 → 改后 |
|---|---|
| `specs/bookkeeping.md:78`（接口定义·「写口入参形状」bullet） | 「`gates` 取值闭世界＝轮数／时长两项（取值真源＝`recon/B1-公共位与结果归一.md` R-B1-04…；限额数值真源＝`walk/裁决表.md` §06-A 与 `recon/K` R-K-72…R-K-78）」→「`gates` 取值闭世界＝`LimitHit.limit` 七限额键名（**2026-10-16 裁·流水 52-B**；原「轮数／时长两项」为旧两限额世界措辞，见行为 11 注；取值真源＝R-B1-04…）」，三条真源引用逐字未动 |
| `specs/bookkeeping.md:106`（行为 11） | 「`gates` ⊆ 轮数／时长两项」句后补注：「**2026-10-16 裁（流水 52-B）**：闭世界以 `LimitHit.limit` 七限额键名为准（旧两限额世界措辞更新）；converge 注记 `gates` 取命中键名」 |

- :78 取「改写＋指针」而非只补注：该行是**接口层面**的唯一闭世界声明，留旧措辞即成「接口说两项、行为说七键」的同规格两说。:78 不复制七键清单（形状真源＝`specs/state.md` 接口定义 `LimitHit.limit` 的 `Literal` 七值），只改指称——一物一处。
- R-B1-04 引文（「gates 取值闭世界＝max_rounds／total_seconds」）**保留未删**：那是旧世界取证原文，`recon/B1` 是取证件、不改写；本批以注记更正规格侧口径。

### 闸与验证（本批实跑）

```
$ uv run python tools/check_specs.py          → spec gate: PASS（0 警告）            exit 0
$ uv run python tools/ref_resolvable.py check → 真源引用可解析闸绿：22 份规格可解析   exit 0
$ uv run python -m pytest -q（全量，排除 3 个 real smoke 文件）
                                              1910 passed, 105 skipped in 77.78s   exit 0
$ uv run lint-imports ／ uv run lint-imports --config tools/importlinter_v2.toml
                                              6 kept,0 broken ／ 18 kept,0 broken  exit 0
```

（本批为文本层注记：`appv2/runtimev2/bookkeeping/` 未动、importlinter 两配置未改。行为 11 的验收标识 `::notice_three_keys_closed_world` 属 W3 承诺面，本批未补齐。）

### 上报项（非本批擅改，报主窗）

1. **W3 票面逐字稿待随本批同步（高）**：`tickets/v2-refactor/RT-W3-01c-bookkeeping.md:52` 的施工基准逐字稿仍照抄旧句「`gates` ⊆ 轮数／时长两项」（指 `specs/bookkeeping.md:106`）。W3 开工前该行须同步为补注后口径（`LimitHit.limit` 七键），否则子代理按票面逐字稿实现**旧两限额世界**（AGENTS 6b：票面即交接）。
2. **键集真源落点**：`appv2/runtimev2/state/limits.py` 的 `LIMIT_KINDS`＝`get_args(LimitKind)`（与 `Budget` 字段名同集、同源派生）——W3 落地时 `gates` 的越界判据直接引该单点即可，无须另立第二张键表（与本注「以 `LimitHit.limit` 为准」一致）。
