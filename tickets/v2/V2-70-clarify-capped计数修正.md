# V2-70 · clarify_capped 连续计数修正（resume 回收轮不计连续）

状态: 待施工 ｜ 优先级: P1 ｜ 来源: 场景对照报告瑕疵②（reject 题实锤）

## 背景与根因

场景对照 reject 题（预测油价）：仅 1 次 ask＋1 次 resume（用户答「取消」）即触发
`clarify_capped`（「连续 ask ≥2」）——回收轮被计入连续ask 计数，截断话术提前于真实
连环反问。根因：`graph.py` clarify 相位 `consecutive_asks` 簿记在 resume 后未按语义重置
（spec：挂起等人工不计轮，回收是同一轮内延续非新一轮 ask）。

## 改动面

`_make_clarify`（graph.py）：resume 回收入口处将本轮回收视作对上一 ask 的应答——
连续计数语义修正为「**新的**连续 ask 才累加」：resume 携 choice 回场后首次再 ask 时
计数从 1 起算（现行为疑似直接 ≥2）。具体簿记位以代码取证为准（施工首日取
`consecutive_asks` 全部读写点列表附票面收尾报告）。

## 验收（场景覆盖：reject）

- `test_v2_four_phase.py` 增钉：ask→resume→再 ask＝第二次 ask 正常挂起（不出
  clarify_capped）；ask→resume→ask→resume→ask（第三次）→clarify_capped 截断；
- reject 题形态重放：1 问 1 答不出现 clarify_capped notice；
- 既有连环澄清截断钉测（P-024b 疑点2 面）保持绿。

## 边界红线

- clarify_capped 截断后的直答行为本身不动（材料如实交付语义零变化）；只改计数语义。

## 依赖与分工

无前置。与 V2-72（检索深度）同在 clarify 相位但不同簿记面，可并行。

## 施工发现（2026-10-13——施工中止，待 Owner 裁决）

取证结论：现行语义「run 生命期内 ask 发射计数、**任何路径不清零**」是先前有据拍板
（graph.py 决策节点 ask 分支注释——P-024b 疑点2；run-69517e02 实测：澄清回收/执行后
若清零，「恢复→执行→再澄清」环永不封口，挂起等人工不计轮预算）。本票原方案
「resume 回收重置计数」会重开该环，**不能机械施工**。候选案（呈 Owner）：
a) 维持现状——reject 题 1 问 1 答即截断视为设计内（截断后如实直答，无害）；
b) 上限 2→3（与轮预算对齐，防环面不变）；
c) streak 语义＋新防环面（同参 ask 指纹去重——成本最高）。

