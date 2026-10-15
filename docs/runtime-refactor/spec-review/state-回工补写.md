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
