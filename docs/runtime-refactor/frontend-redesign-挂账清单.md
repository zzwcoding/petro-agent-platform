# 前端答案展示重设计 · 挂账清单（未决项全登记）

> 2026-10-17 收官挂账 · Owner 指示「没有解决的问题都挂账，将在别的窗口解决」。
> 纪律：记票是暂存不是销账——归属窗口收项时逐条回写终态。本清单＝唯一真源，后端条目细节在 `frontend-redesign-后端需求.md`，条目间以编号互引。

## A · 后端/runtime（归属：主窗 runtime 线）

| # | 挂账 | 证据/细节 | 期望终态 |
|---|---|---|---|
| A1 | **直答闭世界误退＋退回文本错走 understanding 通道**（P0-1A） | 后端需求文档 P0；run-723b64c4 实证（step seq=2 direct_rejected）；涉 `understanding/closure.py:70-87`（判据收窄：含断言才退）、`interpret.py:277,320`（退回文本不发 understanding kind）、prompts 直答示例自伤 | 问候/示例枚举类直答正常出正文 |
| A2 | **剥离误伤空稿＋动作 JSON 回声链＋notice 文案失实**（P0-1B） | 后端需求文档 P0；step seq=13「剥离后空稿」实证；涉 `clarification/core.py:175-183`（动作 JSON 不写进送模型链）、`answering/emission.py:93-98`（finalize 形回退取 answer 字段）、`answering/constants.py:121-123`（文案改如实） | 回吐 finalize 形不再零交付 |
| A3 | **:8001 进程重启加载 BE-01**（Owner 择机） | 运行进程载 `fbe2e0b`（BE-01 修复前）；重启后内存历史行清空（见 A4） | 重启＋验证新 run 不再误标 legacy |
| A4 | **PG alembic upgrade head（0026/0027）＋真件接线** | PG 实查 alembic_version=0025、`agent_v2_run` 无 supplements 列；进程现挂内存件（`app.py:394`），run 不落库、重启即丢历史 | 升级 migration＋接线真件（主窗装配线既有登记项，BE-01 收尾报告挂账过） |
| A5 | **历史读口补 citations/materials/notices/blackbox**（P1-1） | 后端需求文档 P1-1；数据已落库（黑匣子 20 键/检查点全量），补读口＝暴露已有存储；前端组件零改动自动满血。**2026-10-19 前端已先行回读投影**（打磨批⑨：`historyAdapter` 从 `supplements.citations`／`attribution` 两块文本投回 citations/materials——历史轮引用面板与正文 `[n]` 悬停卡已复活）；本条收窄为**notice 带／blackbox 统计行**＋**单来源轮切片正文**（无 attribution 块时卡正文仍走「材料未在回合内渲染」占位） | 历史轮 notice 带/统计行复活（引用面已复活） |
| A6 | **`citation.source_id`→原文定位读口**（P1-3，Wekenora 式点引标开全文） | 后端需求文档 P1-3；需检索/摄取面位置锚点落库＋api 读口，工程量大，另票 | 远期能力 |
| A7 | **notice 白话化全量＋lineage 白话五要素**（P2-4/5） | 主窗 EB5 白话化批在跑，自然演进；前端已按「纯透传」消费，无前端动作 | 随 EB5 批收口 |

## B · 前端本线遗留（归属标注逐条）

| # | 挂账 | 状态/证据 | 归属 |
|---|---|---|---|
| B1 | **真机帧走查 Owner 目验** | `frontend-redesign-验证记录.md` 第 1 节核对清单已备，「待 Owner 目验」 | Owner |
| B2 | **vitest 偶发 `Errors 1 error`**（用例全 passed、退出码 0，5 次复跑未复现） | 验证记录第 5/9 节登记 | 本线观察清单（复现再修） |
| B3 | **历史文档与现行 UI 不一致**：设计稿/调研/接口对账/验证记录仍提及已删的「按来源列出」中栏位、SupplementBlocks 组件、「已到最早」按钮、旧灰字条款（规格条款已同步，过程文档未动） | 992b217 打磨批后产生；留痕或同步二选一 | Owner 拍板（默认留痕=历史记录不改） |
| B4 | **左栏行标识口径**：现取「链内 created_at 最早轮」（旧页 buildThreads 口径）；加载更多后链根入窗会发生两行合并（测试已钉）；若改「followup 字面根」一行可换（`groupRunsIntoChains` rootId 取值） | cb91d4b 披露 | Owner 产品判断 |
| B5 | **打磨批遗留两处微调**：④单条引标/单次检索也出统一统计行措辞（「1 条 · 1 处来源」）；⑥B 级并入「系统注记」标签——Owner 目验后如需分标可回调 | 992b217 披露 | Owner 目验 |

## 进展回写（2026-10-18 接手窗口）

> 归属窗口收项回写；终态以本条为准，细节见票面与提交流水。

| # | 终态 | 证据 |
|---|---|---|
| A1 | ✅ **收**（V2-83，commit `b85126b`） | 直答子句禁令＋closure 收窄为数值形；真机「你好」5 连跑 **0 次误退、5/5 非空交付**（run-86f66df3／run-28073804／run-296ef376／run-46bc6d99 直答；run-27c48bce 模型自判 full 非误退）；指标名/表名单独出现保留直答（含真机问候原句测试钉） |
| A2 | 🟡 **部分收** | ①finalize 提取＝82g（`a7ca048`）；②空正文不静默＝V2-84（`45297a8`：主模型 500 切备 petro-lite 的空 content 不再当成功）；③剥离空稿 notice 文案如实＝V2-85；④回声链（澄清/动作 JSON 原话入送模型链）**未动**——涉及追加链与 KV 前缀设计，待 Owner 拍板另票 |
| A3 | ✅ **收**（2026-10-18） | :8001 已重启载 V2-83/84 新码（PID 19156 起，日志 `logs/v2-8001.log`）；重启前历史仅测试数据 |
| A4 | 🟡 **部分收** | `alembic upgrade head` 已到 **0027**（`agent_v2_run.supplements` 列实查在场）；**真件接线未做**——`persistence.Tables` 为同步协议、`RunStore` 同步面，现有 PG 面是异步行（`infra.db` 异步引擎），需设计票（同步适配器/异步化二选一，且守 B3 单出口） |
| A5 | ⏳ 未动 | 依赖 A4 真件（无落库则历史读口无数据可补） |
| A6／A7 | ⏳ 未动 | 原文照旧 |


## 已销账（防重复登记）

- BE-01 读口空列语义（eafcda4，收）｜悬浮窗混乱/右栏重复/流水线噪音/加载按钮/噪音提示（992b217，收）｜新会话/滚底/链分组/行话/框框（a31fa1f+cb91d4b，收）｜check_specs web/src 守门洞（6106c0d，收）。
