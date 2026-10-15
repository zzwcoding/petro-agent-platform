# persistence 规格回工补写（2026-10-15，复审⑥）

- 依据：独立复审⑥对 `specs/persistence.md` 的 findings（主窗已逐条裁方向）。
- 范围：只改 `specs/persistence.md`（本文件是修改点台账）；**卡级问题只上报不改卡**（`specs/modules.md` 在另一窗口施工中）。不 git commit。
- 闸验证：`uv run python tools/check_specs.py`＝**PASS（0 警告）**；`uv run python tools/ref_resolvable.py check`＝**绿（20 份规格可解析）**。（首跑曾红一处：行为 9 里裸写 `` `eval/results` `` 被真源闸当路径解析失败——已把目录名移出反引号、真源只留文件路径 `eval/results/Q15-对账报告.md`，复跑绿。）

## 修改点清单

| # | 落点 | 改前 → 改后 | 对应 finding |
|---|---|---|---|
| 1 | `specs/persistence.md:141`（行为 5 审计四要素改组） | 原**五组**（主体／范围／意图与授权／执行事实／结果与证据）→ 按主裁改回裁决原文**四项＝主体／意图／事实／结果**（Owner 裁决 `walk/16` §七 Q-C「审计按四要素补齐字段」，枚举同 `walk/裁决表.md` §16-C）：`scope` 并入**主体**项（主体的范围细化，不另立要素）、`authorization` 并入**意图**项（授权依据，不另立要素）、`facts`＝事实、`evidence`＝结果；「缺组判失败」→「缺项判失败」；断言保持「缺 `scope` 或 `evidence` → 抛错」（字段不删、只改要素归组） | finding「四要素按主裁改回」 |
| 2 | `specs/persistence.md:169`（验收行同步） | 「审计四要素**缺组**判失败」→「审计四要素**缺项**判失败」；测试标识 `::audit_four_elements_required` 不变 | finding 1 配套 |
| 3 | `specs/persistence.md:116`（闭世界二补真源锚） | `StepRecord.status`＝`ok`｜`failed`｜`refused` 原无真源 → 补「（真源＝`specs/bookkeeping.md` 已定口径——`status` 是显式关键词参，闭世界三值、缺省 `ok`、由调用方如实给）」 | finding「status 三值补真源锚」 |
| 4 | `specs/persistence.md:145`（行为 9 逐题账数据源补指） | 「逐题账集合与落盘记录等值可对账」无数据源 → 补「对账数据源＝逐题 `ledger_run_ids` 集合与跑批 jsonl（eval/results 下各题记录）的 `run_id` **集合等值**（真源 `eval/results/Q15-对账报告.md`（:207——逐题 `ledger_run_ids` 与 jsonl `run_id` 集合等值））」 | finding「行为 9 数据源补指」 |
| 5 | `specs/persistence.md:149`（行为 13 长度受控补判据） | 「长度受控」原无判据 → 补真源值：审计 `facts` 摘要 ≤120 字符（R-J-06 `SUMMARY_LIMIT=120`）；黑匣子单行摘要 ≤96 字符、换行替换后按字符数计（R-J-60）；分面截断 title 30／60、digest 80、source 40（R-J-62） | finding「行为 13 补判据」 |
| 6 | `specs/persistence.md:80`（CheckpointRow 补投影映射注记） | 类注释补「列名映射：ns↔checkpoint_ns、kind↔type、metadata↔metadata_json——投影改名不换列，真源 recon/J 表事实」（对照 `recon/J` `AgentV2Checkpoint` 实列：thread_id/checkpoint_ns/checkpoint_id/parent_checkpoint_id/type/checkpoint/metadata_json） | finding「投影改名补映射注记」 |
| 7 | `specs/persistence.md`（StepRecord 补 `created_at` 列） | 投影原缺 `created_at`（现状表 `AgentV2Step` 实有该列，recon/J L58-71 `created_at default=now`）→ 补列 `created_at: datetime  # 该记录末次落盘时间（现状列如实投影——recon/J AgentV2Step；语义定死＝末次落盘，首写时间不可回溯——见风险 4）`；风险 4 尾补「本批已按此对策在 `StepRecord` 投影补 `created_at` 列（见接口定义）」 | finding「created_at 列缺，二选一」 |
| 8 | `specs/persistence.md`（行为 9／挂钩表不动面确认） | `run_id` 全盖章、`ledger_run_ids` 对账与钉 `pin-28` 落盘面行既有登记一致，未重复建钉 | —（自查） |

## 二选一说明（finding 7：补列 vs 改风险 4 措辞）

**选「补列」。理由**：① 现状表实有该列（recon/J `AgentV2Step`：`created_at default=now`）——`StepRecord` 自称「agent_v2_step 行的投影」，缺列＝读回面丢现状事实；② 风险 4 的对策原文已把列语义定死为「该记录末次落盘时间」，但该对策悬空在一条未声明的列上——补列使对策落地，规格自洽；③ 写侧无涟漪：`specs/bookkeeping.md` 行为 3 的「`record_step` 产出 StepRecord 的**七个字段**」指装配**入参面**（run_id/seq/step/status/title/manifest/payload），`created_at` 由落盘层／DB default 填、不经 `record_step` 装配，两者不冲突——但「七个字段」的枚举在 StepRecord 增列后字面变旧，**登记为 bookkeeping 侧连带**（见下上报项 2），本批不越界改。

## 上报项（只报不改）

1. **卡级：审计四要素的「四分组」表述不对齐——落点实测在 `## persistence` 卡，非 bookkeeping 卡**。任务面描述为「bookkeeping 卡四分组表述不对齐」；经 grep 实测：`specs/modules.md:488`（**`## persistence` 卡**测试计划行）写「审计四要素（**主体与范围／意图与授权／执行事实／结果与证据**）」——四组斜杠对的枚举取自 `walk/16:34/:57` 的 handbook 采纳面措辞，与主裁认定的裁决原文四项「主体/意图/事实/结果」（`walk/16:68`／`walk/裁决表.md` §16-C）**表面枚举不一**（实质可通：前者把 scope 并主体、authorization 并意图，与本次行为 5 的归组一致）；而 `## bookkeeping` 卡（`specs/modules.md:321-355`）**无任何审计四分组表述**（其测试计划行＝写口/序号/触界三件，grep「审计|四要素|主体」零命中）。请主窗裁定：persistence 卡 :488 的枚举是否随主裁统一为「主体/意图/事实/结果」，或双措辞并存并注「同物异排」。**本批未改卡**。
2. **bookkeeping 侧连带（登记级）**：`specs/bookkeeping.md:95`（行为 3）「`record_step` 产出 StepRecord 的七个字段」——StepRecord 本批补 `created_at` 后投影为八字段；该句的「七个字段」指 record_step 装配入参面、与 `created_at`（落盘层填）不冲突，但字面建议 bookkeeping 批次顺手注一句「`created_at` 非装配入参、由落盘层填」防后人误读。本批不越界改。
3. **行为 5 的断言面维持两点**：四要素归组改变不改变断言（缺 `scope`／`evidence` 抛错）与 `AuditRecord` 字段集——`scope`／`authorization` 字段保留（各为主体／意图项的细化字段），未删字段、未自造第五要素。
