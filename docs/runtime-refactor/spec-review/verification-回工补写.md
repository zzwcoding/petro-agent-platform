- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次只改 `specs/verification.md`，其它文件未动（真源侧另见 preconditions-回工补写.md 的 ADR-0005／S1 记录）。行号均指改后文件（142 行）。

# verification 规格回工补写（复审发现 #1/#2/#3）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/verification.md:39-40` | 接口 `Verdict` 在 `cited` 与 `attribution` 之间补 `delivered_rows: int`（答案交付行数）／`obs_rows: int`（在窗数据行数）两字段 | 复审发现 #1（【P1】pin-12 接口字段）；真源 `docs/runtime-refactor/arch/P7a-交接包与挂账清单.md:99`（A-P7a-38 对账机检字段）；`eng/04a` pin-12 |
| `specs/verification.md:75` | 行为 6「各字段齐备」清单补「行集对账 `delivered_rows`／`obs_rows`」——缺键＝判失败覆盖新字段 | 复审发现 #1 配套（保证可写成 pytest 断言：缺任一新键判失败） |
| `specs/verification.md:80` | 新增行为 11「行集对账（记账面、非拦截阀门）」：确定性对账在窗数据行数 vs 答案交付行数，两字段随 step payload 落账；差额>0 且答案面无行集声明 → 补如实注记；不改写、不重试、不拦截 | 复审发现 #1；真源 A-P7a-38「记账面非拦截阀门——差额>0 且答案无声明→补如实注记；不改写数值断言、不重试不拦截」 |
| `specs/verification.md:85` | 「不降级与静默禁令」机读信号 step payload 字段清单补 `delivered_rows`／`obs_rows` | 复审发现 #1 配套（payload 与 Verdict 字段镜像一致） |
| `specs/verification.md:107` | 验收测试新增一行：行集对账字段入 Verdict 与 step payload、差额>0 无声明补如实注记（不改写、不拦截）→ `tests/domains/test_v2_verification.py::row_reconciliation_bookkeeping` | 复审发现 #1（测试名修订步自拟，阶段 5 织网实现） |
| `specs/verification.md:136-140` | 「与闸的挂钩表」补登记五根钉：pin-01（落点＝行为 5 归属审→`attribution=False`）、pin-02（落点＝行为 2 数值须复述＋行为 3 无据改写）、pin-10（落点＝行为 8 零数值断言不恒过＋`Verdict.cited`）、pin-12（落点＝接口两字段＋行为 11）、pin-03（注明本块无独立落点，见下） | 复审发现 #2（【P1】挂钩表补登记）；登记形式照 `eng/04` §六（`pin-NN` 标识）与 `preconditions`/`tool_matching` 挂钩表 pin-31 行先例 |
| `specs/verification.md:71` | 行为 2 承载豁免措辞由「表格行／血缘卡／fragment」改为真源字面 **`agg_row`（表格行）／`lineage`（血缘卡）／`fragment`**（括注保留中文义） | 复审发现 #3（【P2】用词对齐）；真源 `docs/runtime-refactor/recon/A2-核验规则与归属审.md:105`（R-A2-11「carrier 豁免（agg_row/lineage/fragment）」）——真源引用是字面匹配 |

## 补充任务追加（2026-10-15 主窗核定 pin-11 归本块）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/verification.md:139` | 挂钩表在 pin-10 与 pin-12 之间补登记 **pin-11**（INV-1 前缀规则：「未找到（材料未披露）：」只挂无据行，行内有引标/观察对齐即放行，理想残余=0）——落点＝行为 3 无据改写（前缀只随 `RewriteRecord.reason="no_material"` 落，有据行不粘前缀）；真源 `eval/results/Q16-对账报告.md` §五 第 3 条（:59）＋ `tickets/v2/V2-54-核验辖域治理.md` 修法三层。格式照既有钉行（`pin-NN` 标识＋落点＋待织网（阶段 5）） | 主窗核定补充任务（体例同 pin-03 的「prompts 7 条③引用链承接」注记先例）；钉面 `eng/04a` pin-11（P1） |

**承接行确认**：INV-1 前缀规则的承接行是既有**行为 3「无据 → 改写」**（改后 :72）——「没有支撑的句子改写成『未找到／材料未披露』」即前缀的落点；「只挂无据行」的反向面（有据行不粘前缀）由行为 1 逐行判定＋行为 8「仍须有可解析引标支撑」共同保证，行为约定**未新增条目**。真源核对：V2-54 票面修法三层（空壳辖域整行重判／窗内对齐放行／真无据照旧盖章——行为零变化面）即 pin-11 的「行内有引标/观察对齐即放行」；Q16:59「INV-1 前缀误挂 6 题 15 行复现（不计档仅登记）」即「理想残余=0」要清零的病灶面。本规格行为约定与该口径一致、无冲突。

**连带行号变化**：挂钩表由 6 行（:136-141）变 7 行（:136-142）——:139 pin-11、:140 pin-12、:141 pin-03、:142 人审行；:139 之前各修改点行号不变。

## 钉落点登记（无落点不硬挂）

1. **pin-03（跨油田分源列明油田归属）**：本块无独立落点——verify 侧只有行为 5 归属审的触发面（真源 `arch/P4a1-票堆V2-46至50.md` A-P4a1-22/23：不一致→改写或分源列明、机读 `attribution_split`）；答案交付面的分源列明属 prompts 合同——按复审指定挂「**prompts 7 条③引用链承接**」，已在挂钩表 pin-03 行内注明（prompts 规格落盘后承接，登记备查不落本块验收）。
2. **verdict(final) 帧归属**：不属本块（行为 10 已声明「批次落定由 `orchestration` 协调；本块只保证自产部分就位」）——**待 orchestration 规格**，不硬挂。

## 备查未动点（只记录、不处理）

- `specs/verification.md:111` 测试文件归属注中的「表格·血缘卡·fragment」是描述**既有** `tests/domains/test_v2_agent_verify.py` 的现状行为（措辞承 `specs/agent-loop.md:108`），非真源引用行，不属发现 #3 作用面——留待 `agent-loop.md` 侧同步时一并（先例：verification-评审观察 2）。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（13 份规格）**。未 git commit。


---

## V1 发起面回改（主窗裁 doctrine）——2026-10-15

- **依据**：复审⑦处置（`docs/runtime-refactor/00-决议与方法.md` 流水 27 第①裁）——相位调模型一律经 `bookkeeping.call_model`（其内部唯一出口 `appv2.runtimev2.gateway_adapter`）。本次只改 `specs/verification.md`（142 行不变）＋本记录，其它文件未动；未 git commit（主窗统一提交）。
- **本块定性**：`verification` 属**零 LLM 面**（R8 契约 source 覆盖 `preconditions`／`verification`／`execution` 三块）——**不调模型、不存在发起面**。按主窗裁注「零 LLM 不调模型，不加 bookkeeping 依赖」，本次**不新增 bookkeeping 依赖行**，只改措辞声明：
  1. 「框架与依赖红线」零 LLM 条（:63）：补「本块零 LLM 面（R8），**不存在模型调用发起面**——不调模型，模型调用发起面（`bookkeeping.call_model`）不在本块作用面」；R8/R7 分层辨明与验收写法不变。
  2. 「与闸的挂钩表」零 LLM 行（:129）：硬要求列由「零 LLM 面（不调模型）」改为「零 LLM 面（不调模型、不存在发起面）」；挂钩与现状列不变。
- **不加闸（裁定照录）**：importlinter 边界闸**不随本批加**——R8 零 LLM 面语义不变，doctrine 是规格层不是闸层（主窗 2026-10-15 裁）。
- **契约字面核对（未改 toml）**：R8（forbidden＝`appv2.runtimev2.gateway_adapter`，source 含本块）与新 doctrine 无字面冲突；R7 对本块「天然满足」的表述不受影响。
- **验证**：`uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿（20 份规格）**。均 exit 0（批次一改后实跑）。
