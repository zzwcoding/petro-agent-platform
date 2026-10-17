# V2-85 剥离空稿 notice 文案如实（A2③）

状态: done（2026-10-18 收票，验收全勾）
日期: 2026-10-18 ｜ 批次：挂账 A2 第③项 ｜ 施工：主窗亲自
依据: `docs/runtime-refactor/frontend-redesign-挂账清单.md` A2③（「notice 文案失实——答案恰被剥没」）＋后端需求 P0-1B 修复方向③

## 任务：

剥离管线把草稿剥成空稿时，`emission_strip` notice 不得再说「答案不受影响」——改成如实交代
「没剩下可交付的正文」。非空稿时保留原文案（此时确实不影响答案）。

## 先读：

- `appv2/runtimev2/answering/core.py`（`_draft` 剥离序：extract → strip → placeholders → blocks → dangling）
- `appv2/runtimev2/answering/constants.py`（`EMISSION_STRIP_CONTENT`）
- `tests/domains/test_v2_answering.py`（`::emission_strip_zero_leak`／`::test_empty_draft_not_pushed` 范式）
- `tests/domains/test_v2_eb4b_plain_wording.py`（上屏文案清单）

## 逐字稿（施工基准——照抄，偏离即停报 L0）

新增常量（`answering/constants.py`，紧邻 `EMISSION_STRIP_CONTENT`）：

> EMISSION_STRIP_EMPTY_CONTENT = "这次模型回复里混进了程序用的格式内容——已自动去掉；本轮没剩下可交付的正文。"

既有常量 `EMISSION_STRIP_CONTENT` 逐字不动（非空稿分支继续用）。

## 施工点（伪代码）

```python
# core.py::_draft
strip_hit = leaked or extracted is not None          # 原判据不动
...  # placeholders / block / dangling 剥除全走完
if strip_hit:                                        # 通知从「剥离后立刻发」挪到「终稿定形后发」
    content = EMISSION_STRIP_EMPTY_CONTENT if not draft_text.strip() else EMISSION_STRIP_CONTENT
    notice(state, type=NOTICE_EMISSION_STRIP, content=content)
```

- 剥除判据、notice 类型（`emission_strip`）、剥除管线顺序零改——只改**文案选择点**与**发点后移**。
- 中间无其它 notice 产生，后移不改通知相对序。

## 测试：

`tests/domains/test_v2_answering.py` 新增两例：
1. `::test_emission_strip_notice_honest_on_empty_draft`：应答为纯发射 JSON（剥后空稿）→
   notice 内容 == `EMISSION_STRIP_EMPTY_CONTENT`；零 text 帧、`state.draft==""`、缺口 missing。
2. `::test_emission_strip_notice_unchanged_when_draft_survives`：正文＋一条发射 JSON → 剥后仍非空 →
   notice 内容 == `EMISSION_STRIP_CONTENT`。
`tests/domains/test_v2_eb4b_plain_wording.py`：新常量入 `_USER_FACE_TEXTS` 清单（白话零行话）。

## 验收：以下 4 条全绿算收票（逐条机检）。

1. 上述两例全绿；`test_v2_eb4b_plain_wording.py` 全绿。
2. 既有 `::emission_strip_zero_leak`／`::test_empty_draft_not_pushed` 零回退。
3. 全量 `pytest -q` 全绿（0 failed）。
4. `tests/infra`／`answering` 相关测试零回退；ruff 全树过。

## 回报：

改动文件＋测试名＋全量数字。

框架红线: 无点名框架（只改文案选择与测试，不引依赖）。
边界红线: 只许动 `appv2/runtimev2/answering/core.py`、`appv2/runtimev2/answering/constants.py`、
`tests/domains/test_v2_answering.py`、`tests/domains/test_v2_eb4b_plain_wording.py`；不碰剥除判据
（`emission.py`）、transport notice 闭世界、V1 `appv2/runtime/`。

## 收票回写（2026-10-18）

- 施工：`core.py` notice 发点后移至终稿定形后、按 `draft_text.strip()` 分支文案；
  `constants.py` 新增 `EMISSION_STRIP_EMPTY_CONTENT`（原文案逐字不动）。
- 测试：`test_v2_answering.py::test_emission_strip_notice_honest_on_empty_draft`／
  `::test_emission_strip_notice_unchanged_when_draft_survives`；EB4b 上屏清单补录新常量。
- 全量 `pytest -q`：**2367 passed / 0 failed / 108 skipped**；ruff 全树过。
