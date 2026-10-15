- 日期：2026-10-15 ｜ 状态：**回工补写**（独立复审打回项落实施工）
- 本次改 `specs/preconditions.md` ＋ 真源侧两处（`docs/adr/0005-子任务图与前置条件机.md` 修订注记、`docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md` 仅 M4 一行）。行号均指改后文件（preconditions 141 行）。

# preconditions 规格回工补写（复审发现 #4/#5）

| 修改点 | 改了什么 | 依据 |
|---|---|---|
| `specs/preconditions.md:138` | 挂钩表补登记 **pin-14**（模糊时间词＋plan 非空 → 确定性改判走 clarify 三选一反问帧）——落点＝判定序第 2 位闸1b，消费 `tool_matching` 时间窗结论 → `ask` 反问 | 复审发现 #4（【P1】挂钩表补登记）；钉面 `eng/04a` pin-14（真源 `arch/P4a2-票堆V2-51至55.md:21-22`） |
| `specs/preconditions.md:139` | 挂钩表补登记 **pin-16**（软失败域闸：data/semantic 成功返回但域错 → 换链回炉恰 1 次为界）——落点＝行为 7 换链回炉一次为界 | 复审发现 #4；钉面 `eng/04a` pin-16（真源 `arch/P4a2-票堆V2-51至55.md:20`） |
| `specs/preconditions.md:140` | 挂钩表补登记 **pin-17**（前置条件机**三态**语义一字不动：放行／拒答／等用户，注记并入放行；判定固定序命中即停；零 LLM 面；扩口未批不得直答终局）——落点＝行为 2／3／5＋判定序明文表＋零 LLM 红线；真源 `walk/裁决表.md` §12-B/C | 复审发现 #4；钉面 `eng/04a` pin-17（已按裁决 §12-B 记三态） |
| `specs/preconditions.md:53` | 「三态与真源『四态』的差异」条：§12-A 更正为 **§12-B**（§12-A 是语义上移裁决且注「不动 ADR-0005」，三态裁决在 §12-B——原引用系修订回执 P-6 落笔时的编号误差）；「ADR／S1 同步修订」标注**已兑现**（2026-10-15），指向 ADR 修订注记与 S1 M4 行 | 复审发现 #5（【中】ADR-0005／S1 四态同步）；即 `spec-review/preconditions-评审.md` F-10 的兑现补完（修订回执 P-6 只落了声明句，ADR/S1 本体未动） |
| `docs/adr/0005-子任务图与前置条件机.md:36-38` | 末尾新增「修订注记（2026-10-15）」一节：随裁决 `walk/裁决表.md` §12-B 改**三态**（放行／拒答／等用户，注记并入放行）；决策段「判四态」原文**保留加注不改**；现行口径以 `specs/preconditions.md` 三态闭世界为准 | 复审发现 #5 处置之一（ADR-0005 加修订注记，原文保留加注） |
| `docs/runtime-refactor/synth/S1-重写单元与证据交叉矩阵.md:27` | M4 行「零 LLM 逐子问题四态闸（放行/挂起/拒答/注记）」改「零 LLM 逐子问题**三态闸（放行／拒答／等用户；2026-10-15 随裁决 §12-B，注记并入放行）**」——**仅此一行，S1 其余未动** | 复审发现 #5 处置之二（S1 的 M4 行同步） |

## 钉落点登记（无落点不硬挂）

- **pin-24（相位合同一次性：contracts_appended 回炉轮不重发）**：属 state/context 记账面（真源 `recon/I2b-RunState全字段.md:40`），本块只有回炉轮的消费侧——**待 orchestration/context 规格**，不硬挂本块挂钩表。

## 验证

- `uv run python tools/check_specs.py` → **PASS（0 警告）**；`uv run python tools/ref_resolvable.py check` → **绿**。未 git commit。
