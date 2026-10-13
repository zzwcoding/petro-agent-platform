# V2-79b · 播种新形（checkpoint 级全量传承）＋旧 v1 checkpoint 读兼容抽取（golden 钉测）

状态: **伪代码施工稿——随票实施** ｜ 来源: V2-79 方案 §6 切票第二票 ｜ 前置: V2-79a 已合入（d1300ea 后）
总方案: `tickets/v2/V2-79-对话状态重构方案.md` §3.5（播种新形）＋§4.2（旧 run 读兼容）

## 0. 本票一句话

把 79a 的播种最小形（runs 行问＋答两轮）升级为 **checkpoint 级全量传承**：前轮
`dialogue` 通道直读（含澄清/审批回收轮——完整会话线程进追问）；前轮无 `dialogue`
（v1 旧 checkpoint）走**读兼容抽取纯函数**（fail-closed：只保留可分类轮），golden
钉测锁真实库样形。只读不改写——旧 checkpoint 零写回。

## 1. 现场与规则（79a 后状态）

- `executor._seed_dialogue`（79a 最小形）：runs 行 `prior.question`＋`prior.answer`
  两轮，不读 checkpoint；
- v2 checkpoint 的 `dialogue` 通道：受理落 user 原话 → 澄清/审批回收插 user 轮 →
  收口单点落 assistant 终稿（completed 时末轮恒 assistant）；
- v1 旧 checkpoint（库里 1740 个）：只有 `history` 混装通道（任务书/决策 JSON/
  台账/伪标注全在），无 `dialogue` 键——aget_state 后 `values.get("dialogue")` 为空。

## 2. 施工伪代码

### 2.1 executor.py —— v1 抽取纯函数（模块级，零 I/O）

```python
def extract_dialogue_from_legacy_history(
    values: dict[str, Any], *, question: str, answer: str
) -> list[dict[str, str]]:
    """旧 v1 checkpoint（history 混装史）→对话层抽取（V2-79b 读兼容——只读不改写）。

    fail-closed：只保留可分类轮——
    - 首轮 user＝前轮 question 权威字段（任务书轮整体跳过——题干嵌任务书尾部，
      不做尾部剥离再抽取：多份任务书同形，question 字段已权威）；
    - 「用户补充：X」回收轮 → user 轮 X（去系统前缀——对话纯度红线）；
    - 「外表引用审批决定：V（审批单号 …）」回收轮 → user 轮 V（批准/驳回）；
    - 台账轮（「{tool} 参数：{…} → 结果…」形）跳过；assistant 轮全部跳过
      （模型过程原话不进对话层——终稿以 runs.answer 权威字段落）；其余不可
      分类轮（决策/澄清指令等）fail-closed 跳过。
    输出＝[user question, *回收轮(自然化), assistant answer]（answer 空则省）。
    """
```

### 2.2 executor.py —— _seed_dialogue 升级

```python
async def _seed_dialogue(self, followup_of) -> list[dict[str, str]]:
    if not followup_of: return []
    prior = await self._store.get_run(followup_of)
    # 守卫照旧（404/409 面零变化）
    graph = build_graph(self._deps(EventBus(), run_id=followup_of),
                        checkpointer=self._saver, four_phase=self._four_phase)
    snapshot = await graph.aget_state({"configurable": {"thread_id": followup_of}})
    values = snapshot.values or {}
    dialogue = [自然化(v2 投影) for t in values.get("dialogue") or []]
    if dialogue:
        # v2 对话层直读——checkpoint 级全量传承（问/答/澄清回收/审批回收全在）
        if dialogue[-1]["role"] != "assistant" and prior.answer:
            dialogue.append({"role": "assistant", "content": prior.answer})  # 防御位
        return dialogue
    # v1 旧 checkpoint（无 dialogue 键/无 checkpoint）→读兼容抽取（golden 钉测守）
    return extract_dialogue_from_legacy_history(
        values, question=str(prior.question or ""), answer=str(prior.answer or ""))
```

### 2.3 测试面（test_v2_multi_turn_context.py 追加）

1. **golden①问候形**（真实库 run-4435a7ce 样形逐字）：history＝[任务书(我能问什么),
   「直接回答：您好…」, 播种轮您好…, 任务书(我刚刚问了什么), 「直接回答：…未发送」]
   → 抽取＝[user 我能问什么, assistant answer]（任务书/原话/伪标注全不进）；
2. **golden②澄清回收形**：history 含「用户补充：N-01 井」→ 抽取含 user「N-01 井」；
3. **golden③审批回收形**：「外表引用审批决定：批准（审批单号 eng-x）」→ user「批准」；
4. **golden④fail-closed**：决策指令轮/台账轮/assistant 原话轮全部不进抽取面；
5. **传承 e2e（v2 直读）**：run A 澄清挂起→resume→completed（dialogue＝[问, 补充, 答]
   三轮）→追问 run B 的 understand 上下文含三轮（checkpoint 级——非 runs 行两轮）；
6. **降级 e2e（无 checkpoint）**：store.create_run＋finish_run(completed) 造 run 行
   无 checkpoint → _seed_dialogue 走 v1 抽取支＝[问, 答]；
7. 79a 既有钉（播种纯度/闸拒终稿跨轮）回归零改动——预计全绿。

## 3. 边界红线

executor.py＋tests 对应位；前轮 checkpoint 只读不改写；零新依赖零迁移；
process_notes 跨轮摘要（方案「≤300 字可选段」）归 V2-79c——本票不做。

## 4. 验收

全量 pytest＋六闸绿；golden 4 例＋e2e 2 例新增全绿；79a 钉测回归零回退。

## 完工记录（2026-10-13）

- executor.py：`extract_dialogue_from_legacy_history` 纯函数上岗（fail-closed 四规则——
  任务书轮/台账轮跳过、「用户补充：」去前缀、审批轮取批准/驳回、assistant 全跳过＋
  runs.answer 权威落）；`_seed_dialogue` 升级 checkpoint 级全量传承（v2 dialogue 直读
  ＋防御位补终稿轮；无 dialogue 键走 v1 抽取支）；前轮 checkpoint 零写回。
- 钉测 6 新枚（golden①4435a7ce 问候样形逐字/golden②澄清回收/golden③审批回收/
  golden④fail-closed/传承 e2e——澄清挂起→resume→completed 三轮 dialogue 全量进追问
  understand 上下文/降级 e2e——run 行在库无 checkpoint 走抽取支）；79a 既有钉零改动全绿。
- 六闸绿：pytest 1736 过（基线 1730＋6 净增）／ruff／mypy 149 文件／lint-imports／
  合同覆盖率 173 条／债务标记。
- 边界注记：过程摘要跨轮（方案「≤300 字可选段」）随 V2-79c——本票未做（票面红线）。
