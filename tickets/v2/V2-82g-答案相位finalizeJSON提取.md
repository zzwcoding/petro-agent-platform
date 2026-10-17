# V2-82g 答案相位 finalize-JSON 提取（空答案热修）

- 日期：2026-10-17 ｜ 性质：热修（线上"你好"空答案）＋同族隐患根治
- 现象（真机 run-9d1c5267）：问候题走 full 路由 → 澄清相位模型 3 次以 `{"action":"finalize","answer":"…"}` 试图交付、被"零实质观察禁定稿"拦 2 次后放行（直答收口）→ **答案相位模型沿袭同一 JSON 形**（llm_calls 实证：caller=answer 的返回内容就是 finalize JSON）→ `strip_emission_fences` 整枚剥除 → 空稿 → "不推空答案" → 前端"本次未产出答案正文"。
- 铁令合规：程序接管输入侧（提取既有 answer 字段），合同条例零新增。

## 施工点

`appv2/runtimev2/answering/core.py::_draft`（raw 取回后、`strip_emission_fences` 之前）插一步确定性提取：

```python
# 伪代码
parsed = try_parse_action_json(raw)   # 整应答恰为一个 JSON 对象（容忍 ```json 围栏——parsing 侧有现成件可参照）
if parsed and parsed.get("action") == "finalize" and isinstance(parsed.get("answer"), str) and parsed["answer"].strip():
    raw = parsed["answer"]            # 提取交付字段作为草稿原文
    notice("emission_recovered")      # 机读面留痕：程序从发射 JSON 提取了答案正文（additive 新 notice type 需进闭世界登记）
```

- 只认 `action=="finalize"`＋answer 非空串；其它 action（decompose/discover/ask）不提取（照旧剥除）。
- 提取后的文本走既有全部剥除管线（围栏/占位符/块/悬空引标），行为与正常草稿一致。
- notice type 取值：优先复用既有 `emission_strip` 同族（登记为准；若必须新值，走 transport notice 闭世界登记＋测试钉）。
- 提取属"恢复"非"放行"：`state.draft` 落提取后文本；`emission_strip` 类机检断言不翻方向。

## 测试

- 单测（answering 族）：答案相位返回整枚 finalize JSON（含围栏形）→ 草稿＝answer 字段文本、非空交付、notice 留痕；返回 decompose JSON → 照旧空稿不推；finalize 但 answer 空串 → 不提取照旧空稿。
- 回归：answering/相关文件全绿；全量 `pytest -q`（基线 2355 过；唯一已知红＝tests/tools/test_ref_resolvable.py::test_gate_green_on_current_repo，前端 specs 引用闸）。

## 非目标

- 不动理解路由（问候走 full 是模型侧不稳定，另册观察）。
- 不改"零实质观察禁定稿"闸语义。
- 不给答案合同加任何新条例。
