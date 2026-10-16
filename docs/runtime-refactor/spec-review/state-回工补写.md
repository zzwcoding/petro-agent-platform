# state 规格回工补写（2026-10-15，复审⑥）

- 依据：独立复审⑥对 `specs/state.md` 的 findings（文字级修正批，主窗已逐条裁方向）。
- 范围：只改 `specs/state.md`（本文件是修改点台账）；不碰其他文件。不 git commit。
- 闸验证：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（20 份规格可解析）**。

## 修改点清单

| # | 落点 | 改前 → 改后 | 对应 finding |
|---|---|---|---|
| 1 | `specs/state.md:38-51`（接口定义 Manifest 块） | 原「骨架逐字真源 recon/I2a」且字段全裸声明（无缺省值）→ **补七合同字段缺省面**：四个列表字段 `field(default_factory=list)`、`selected_reason ""`、`token_count 0`、`transform "filter→rank→budget→cite"`，三机检字段（material_total/material_rendered/material_truncated）同批补 `0／0／False`；注释改「骨架字段逐字真源 recon/I2a；缺省值面同源＝R-I2a-05 码面实测」；`as_dict` 行补「`Manifest()` 无参可构造（七合同字段＋三机检字段全带缺省——真源 recon/I2a R-I2a-05）」 | finding「骨架逐字」改实 |
| 2 | `specs/state.md:116`（行为 10 双指收敛） | 原「R-K-72…R-K-78 逐键承载七项 ＋ §06-A 承载循环上限五项」→ 改「**`Budget` 键集唯 `recon/K` R-K-72…R-K-76 逐键承载七项**；`walk/裁决表.md` §06-A 五项中「回炉一次／同参重投即拦」两项为**行为机制、非 Budget 键**，其余三项数值与 R-K 同源」 | finding「:116 双指引用面收敛」 |
| 3 | `specs/state.md:21`（不做什么 row 7 连带对齐） | 「R-K-72…R-K-78 逐键」→「R-K-72…R-K-76 逐键承载七键」，并补「其中『回炉一次／同参重投』为行为机制、非 Budget 键」 | finding 2 的连带面（同一双指表述，避免行内两说） |
| 4 | `specs/state.md:159`（依赖行连带对齐） | 「数值真源＝`recon/K` R-K-72…R-K-78（逐键）＋ §06-A（循环上限五项）」→「R-K-72…R-K-76（逐键承载七键）＋ §06-A（循环上限五项——『回炉一次／同参重投』两项为行为机制、非 Budget 键，见行为 10）」 | finding 2 的连带面 |
| 5 | `specs/state.md:128`（不降级节互引改指针式） | 原「断言：v1 fixture 读入后 `schema_version` 为读入态、**对话通道空显（行为 8）**」→ 改「`schema_version` 为读入态（行为 8）；**「对话通道空显」归 `specs/persistence.md` 行为 12**（分工互认——本块不另写该断言，见行为 8 的分工注）」——与行为 8 的分工注、persistence 行为 12 三处一致 | finding「:128 互引失准」 |
| 6 | `specs/state.md:190`（挂钩表 pin-30 行补延伸挂法注记） | 补「注：**钉文原两面＝compaction／黑匣子回放**（`eng/04a` pin-30 原文），本规格仅承接**状态字段读入面**（延伸挂法）」；回放面挂 persistence 行为 12（分工互认）、compaction 半面待 context 规格的既有表述保留 | finding「pin-30 延伸挂法补注」 |
| 7 | `specs/state.md:112`（行为 6 补写口指针） | 「任务书、相位指令…只入 `process_notes`」句后补「**`dialogue` 的写口承担＝`bookkeeping`（对话层追加唯一入口 `append_dialogue`）**——本块只定条目形状与来源闭世界、不提供写函数」——与 bookkeeping 卡 `append_dialogue` 唯一入口、本规格风险 2「写口归 bookkeeping 单点」同口径 | finding「行为 6 写口指针」 |

## 二选一说明（finding 1）

**选「补缺省面」（a 案），不选「改措辞」。理由**：缺省值面在真源里**已有实载**——`recon/I2a` R-I2a-05 明文「Manifest 无参可构造：七合同字段全带缺省（列表 default_factory=list；selected_reason ""；token_count 0；transform "filter→rank→budget→cite"）」，字段表并载三机检字段缺省（0／0／False）——补进规格**零发明**，且使 `Manifest()` 可构造这一公开事实（消费侧要无参建实例）在规格内自足；规格体例一致（`AskRequest`／`AskChoice` 本就带缺省值声明，Manifest 补后同款）。若选改措辞（「缺省面本规格补充」）则补的还是同一批值、少一句可构造保证，不取。

## 连带与说明

1. R-K-72…78 → R-K-72…76 的依据（亲读 `recon/K:458-464`）：R-K-72 轮数、R-K-73 轮内发现＋执行、R-K-74 段时长＋单工具超时、R-K-75 全 run 发现、R-K-76 连续 ask——七键恰在 72…76；R-K-77＝防环语义、R-K-78＝「合同值不因测试改动」注释纪律，均**非 Budget 键**。原文「72…78 逐键」按数差恰好凑 7，属巧合性误写。
2. §06-A 五项（发现≤10／大循环≤3轮／回炉一次／连续澄清≤6／同参重投即拦）中，「回炉一次」「同参重投即拦」是回炉与重投的**行为机制**（承接在 `specs/agent-loop.md`／`specs/clarification.md` 行为面），不进 `Budget` 键集；其余三项与 R-K-75／R-K-72／R-K-76 同源。行为 10 是主落点，:21／:159 两处同款双指为同一 finding 的连带面、已对齐，防「行内两说」。
3. pin-30 的延伸挂法注只补挂法声明，未改分工实质（回放面＝persistence 行为 12、compaction 半面待 context 规格均维持原文）。

## W3 前规格微修正批：`check_limits` 签名注（2026-10-16，流水 52-A）

- 依据：`docs/runtime-refactor/00-决议与方法.md` 流水 52「**裁定 A＝限额三键判定面采「注入制」**」＋流水 53「裁定 A **规格面落地**：`state.md` `check_limits` 签名补注注入参」。
- 范围：只改 `specs/state.md`（接口定义新增 :90 签名注 bullet＋行为 11 :118 补句）＋本记录；**实现与测试未动**；未 git commit。

### 改动

| 落点 | 改后 |
|---|---|
| `specs/state.md:90`（接口定义节新增 bullet「**`check_limits` 签名注（2026-10-16 裁·流水 52-A）**」） | 「补注注入制签名——`check_limits(state, *, elapsed_seconds: float | None = None, consecutive_asks: int | None = None) -> Convergence | None`——注入制（流水 52-A）：None＝该项不判定；`tool_timeout` 为单次调用时限归执行侧实时面、不经本判定。」 |
| `specs/state.md:118`（行为 11） | 句尾补：「**签名与用量面**：判定采**注入制**（`elapsed_seconds`／`consecutive_asks` 可选，None＝该项不判定；`tool_timeout` 为单次调用时限、归执行侧实时面）——签名逐字见接口定义注（2026-10-16 裁·流水 52-A）。」 |

- **注落点判定（对派单「行为 10／接口定义」的落法说明）**：`check_limits` 的**判定行为**是行为 11（行为 10 是 `Budget` 键集闭世界、无 `check_limits` 面），故注落「接口定义 :87-90」＋「行为 11」，未在行为 10 落重复副本（一物一处）。:88 的原接口签名行本身**未改**——派单是「补注签名」，形状行的改写权不在本批。
- **未动项**：`appv2/runtimev2/state/limits.py`（:104）、`tests/domains/test_v2_state.py`、`specs/modules.md` 卡面，均未动。

### 上报项（L0：注文与「现实现／现测试」两处不齐，请主窗裁）

1. **实现没有注入参**：现实现＝`def check_limits(state: RunState) -> Convergence`（`appv2/runtimev2/state/limits.py:104`），**不接受** `elapsed_seconds`／`consecutive_asks`；其 docstring 自述「余下三键（`seconds`／`tool_timeout`／`ask_cap`）的用量面不在 `RunState` 形状内…故不作判定（登记待裁）」（:16-19）。即「实现已兼容此形」只成立于**行为语义**（三键今日不判＝None 注入时的行为），**不成立于签名**（今日传注入参会 TypeError）。
2. **`-> Convergence | None` 与现实现／现规格不符**：实现恒回 `Convergence`（未触界回 `Convergence(hit=(), notice=None)`）；行为 12／13 的断言模型（`hit`／`notice` 同现、未触界恒 `notice is None`）也无 None 分支。派单注文逐字含 `| None`，本批**照抄未改**（逐字稿纪律：偏离即停报）；是否改为 `-> Convergence`、或反向把 None 分支补进行为 12，请主窗裁。
3. **W1 测试已钉「三键不判定」**：`tests/domains/test_v2_state.py:1009-1011` 钉「`seconds`／`tool_timeout`／`ask_cap` 用量面不在 `RunState` 形状内——上限归零也不生假命中」，与本注「None＝该项不判定」相容；若后续给实现加注入参，该处「登记待裁」注须同批更新。
4. **卡面**：`specs/modules.md` `## state` 卡公开接口若载 `check_limits` 签名，须随本注同批（阶段 7 接口对账批或本批后续）——本批未动 `modules.md`。

### 闸与验证（本批实跑）

```
$ uv run python tools/check_specs.py          → spec gate: PASS（0 警告）            exit 0
$ uv run python tools/ref_resolvable.py check → 真源引用可解析闸绿：22 份规格可解析   exit 0
$ uv run python -m pytest tests/domains/test_v2_state.py tests/domains/test_v2_transport.py -q
                                              38 passed in 1.67s                    exit 0
$ uv run python -m pytest -q（全量，排除 3 个 real smoke 文件）
                                              1910 passed, 105 skipped in 77.78s    exit 0
$ uv run lint-imports ／ uv run lint-imports --config tools/importlinter_v2.toml
                                              6 kept,0 broken ／ 18 kept,0 broken   exit 0
$ uv run mypy app appv2                       → Success（195 source files）         exit 0
```

### 微修正批二期收尾（2026-10-16，流水 52-A）：注入参落地

- **审计一句**：上节「上报项」1／2／3 三条已按主窗裁定（签名面取裁定 A、返回形以现实现为准）一次收齐——`appv2/runtimev2/state/limits.py:106` 补注入面签名 `check_limits(state, *, elapsed_seconds: float | None = None, consecutive_asks: int | None = None) -> Convergence`（**只接形状**，注入值的判定逻辑随 W5 票落地；两参缺省时行为与落地前**逐字节等价**、四键判定不变）；`specs/state.md:90` 注的返回形由 `-> Convergence | None` 改 `-> Convergence`（恒回 `Convergence`，未触界回 `Convergence(hit=(), notice=None)`，无 `None` 分支）；`tests/domains/test_v2_state.py:1009` 的「（登记待裁）」注改「（注入形已备（流水 52-A），缺省调用三键不判定）」。
- 未动项：`specs/state.md:88` 接口签名行本身、行为 11 注（指针式引用 :90，不重复副本）、`specs/modules.md` 卡面。
- 闸：`pytest tests/domains/test_v2_state.py -q`＝19 passed；`tools/check_specs.py`＝PASS（0 警告）；`mypy appv2/runtimev2/state/`＝Success（4 source files）；未 git commit。
