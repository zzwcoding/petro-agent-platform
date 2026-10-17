# H 批开票：system 承载位（角色分家＋链首背景块）

> 状态：已研究、待施工（Owner 批后派子代理）。原则：**既有合同文本一字不改，只动承载位**；唯一新增文本＝背景块（逐字稿在 §5）。

## 1. 改的理由（证据链）

| 证据 | 内容 |
|---|---|
| 角色实测 | 233 条链消息＝user 154／assistant 79／**system 0**（audit-143）——规章与材料同角色平级 |
| 指令层级实证 | system＞user（arXiv:2404.13208，调研 3a 已收）——合同在 user 位天然矮一级 |
| 照抄病 | 291 次答案调用 221 次照抄尾段注记——"命令/资料同口袋"是结构根因之一 |
| Owner 新令 | 提示词里没有任何"本系统作用/原理/机制/目的"的背景交代 |
| 铁律 | 只换承载位不换文本（A-P6b-24/34 先例） |

## 2. 已核实的四个关键事实（施工依据）

1. **写入口已支持任意角色**：`bookkeeping/ports.py:110 append_message(state, *, role: str, content)`——role 是自由字符串，单点写口，无需改造。
2. **供应商形态**：`config/models.yaml`＝`provider: anthropic`（litellm 走 Anthropic 兼容口，模型 MiniMax-M3）。**litellm 对 anthropic 把 messages 中所有 system 消息合并为顶层 system 参数**。
3. **装配点**（user 包现在在哪拼）：
   - 读题：`understanding/interpret.py:236`（append user payload）
   - 澄清：`clarification/core.py:281-284`（package＋increment 两条 user）
   - 匹配：`tool_matching/matching.py`（_append_round_instruction 同形）
   - 作答：`answering/core.py`（assemble_answer_prompt 后 append user）
4. **链首插入点**：understand 入口（`orchestration` 起 run 后第一次 append 前）。

## 3. 设计决策：调用级临时 system（方案 C），不选 A/B

| 方案 | 做法 | 不选/选的理由 |
|---|---|---|
| A 仅链首一条 system（只放背景） | 背景入 system，合同留 user | 只能满足"背景交代"，命令/资料混装没解决——**不够** |
| B 每环节一条 system **骑进链里** | 持久化 system 消息随链追加 | litellm/anthropic 会把全链 system **合并**→ 每个环节调用都看见全部环节规章（串味：作答时看见"写答案"也看见澄清动作契约，可能诱发越相动作）——**不选** |
| **C 调用级临时 system（入票）** | system **不写进链**；每次调模型时请求形＝`[system(背景+本环节规章)] + state.messages`；链本体仍只含 user/assistant | ① 角色真分离（system=规章、user=材料）② 无串味（每环节只带自己的规章）③ 不依赖"中插 system 被逐条尊重"的供应商行为 ④ 链不变→落库/回放/簿记零扰动 |

**KV 缓存代价（明示接受）**：请求首条是环节规章 system→跨环节首调用前缀不同、缓存重算一次；**环节内多轮（澄清常 2-8 轮）system 相同→缓存照吃**。每 run 多付 3-4 次前缀重算（链长 2-19 条），可忽略。

## 4. 伪代码（施工照此）

```python
# ① prompts/constants.py 新增（唯一新文本，逐字稿见 §5）
SYSTEM_BACKGROUND = (
    "【系统背景】你是\"问一问\"——油田生产数据问答助手。你的作用：帮业务人员用一句话"
    "查到平台里的生产数据和报告结论，省去他们自己翻系统。你的原理：你不直接连库乱查——"
    "每个问题经过读题→澄清→选链→检索/查数→起草→核验六道工序，每步都有专门程序和规则"
    "约束，你只做规定环节的事。你的目的：每条答案有据，不确定就说不确定，宁可说没查到也"
    "不编。平台数据分两类：数据库实时汇总（权威）、报告库各篇报告（人写口径，性质不同）。"
)

# ② prompts/ 每环节新增"规章取件"函数（文本全部引用既有常量，零新写）
def clarify_system_contract() -> str:      # 相位①合同＋§A 指南＋台账常驻＋样例（现 user 包的规章段）
    return CLARIFY_HEADER + GUIDE_SECTION + LEDGER_BLOCK + SAMPLES   # 段落组合照 EB2 装配序
def match_system_contract() -> str:        # 相位②合同＋台账常驻
    return TOOLMATCH_HEADER + LEDGER_BLOCK
def answer_system_contract() -> str:       # 三件套＋白话表＋SUMMARY＋ANSWER_REQUIREMENTS
    return ANSWER_PREAMBLE + JARGON_PLAIN_GLOSSARY + SUMMARY_CONTRACT + ANSWER_REQUIREMENTS
def understand_system_contract() -> str:   # 读题合同＋环境装配
    return READ_CONTRACT + ENV_ASSEMBLY

# ③ 各相位 core.py：原 append 的 user 包拆两路（伪代码——现装配函数返回的"规章段"改从
#    system 走，"动态段"仍进 user；实现=装配函数拆返回 or 新包装函数，二选一，以改动最小为准）
# before（clarification/core.py:281）:
append_message(state, role="user", content=package)      # package = 规章+台账+动态条 一整包
# after:
system_text = SYSTEM_BACKGROUND + clarify_system_contract()
pass_system_contract(call_context, system_text)          # 见 ④：只随本次请求走，不入链
append_message(state, role="user", content=dynamic_only) # 只剩动态条＋拒因回喂＋问题组

# ④ bookkeeping.call_model（或 gateway_adapter 调用面——择一实现点）：
#    state 上新增"本次请求 system"槽（易变量面，不进 messages、不进持久化）：
def call_model(state, caller, messages):
    req = list(messages)
    if state.pending_system_contract:                     # 有则置首、用完即清
        req = [{"role": "system", "content": state.pending_system_contract}] + req
        state.pending_system_contract = None
    return completer.complete(req, caller=caller, run_id=state.run_id)

# ⑤ 链首背景持久化（替代方案：背景也走临时 system——每环节重复 ~200 字。
#    若实测更简，可背景也走 ④ 的 pending_system 前缀；本票默认背景持久化一次入链首）：
#    understand 入口第一次 append 前：
append_message(state, role="system", content=SYSTEM_BACKGROUND)   # 每 run 恰一次
#    （litellm 合并后＝背景恒在 system 位；环节规章经 ④ 每环节叠加一次，调用结束即散）
```

**before/after 消息序（一个 run 的片段）**：
```
before: [u读题包][a][u澄清包(规章+台账+动态)][a][u澄清增量][a]…[u作答包(规章+材料+注记)][a]
after:  [s背景][u题][a] …调用澄清时请求=[s背景+s相位①规章]+链… [u动态][a]… 调用作答时请求=[s背景+s作答规章]+链…[u材料+注记][a]
```

## 5. 逐字稿（唯一新文本，照抄）

```
【系统背景】你是"问一问"——油田生产数据问答助手。你的作用：帮业务人员用一句话查到平台里的生产数据和报告结论，省去他们自己翻系统。你的原理：你不直接连库乱查——每个问题经过读题→澄清→选链→检索/查数→起草→核验六道工序，每步都有专门程序和规则约束，你只做规定环节的事。你的目的：每条答案有据，不确定就说不确定，宁可说没查到也不编。平台数据分两类：数据库实时汇总（权威）、报告库各篇报告（人写口径，性质不同）。
```

## 6. 测试与验证清单

1. 单测：①每环节请求首条＝system 且含本环节规章头（【相位①/【答案要求 等）＋背景 ②user 包不再含规章头 ③背景持久化恰一次、字节稳定 ④pending_system 用完即清（防泄漏到下一环节）⑤链 messages 里 role 只含 user/assistant/system(背景一条)。
2. 门禁：tests/domains＋tests/runtimev2＋ruff＋mypy＋lint-imports 双配置＋check_specs；主窗全量 pytest。
3. **真机探针（本票必含）**：ladder 跑 2 题（数-明1＋一题问答），抽 llm_calls 请求 messages[0].role=="system" 且模型行为无越相动作（无 finalize 出现在澄清轮等）；核对 **环节内第二轮缓存命中**（cached_tokens>0 或上游等价信号——若无信号则记"缓存不可测"不造假）。

## 7. 风险与回退

| 风险 | 应对 |
|---|---|
| litellm 合并行为与假设不符 | 真机探针先行；异常则回退方案 A（仅背景入 system，合同留 user）——回退只动 ④ |
| 环节规章离开"每轮可见"位置后模型失锚 | 探针题对比 before/after 判分；若明显退化，规章段可拆"system 放红线＋user 留样例行"混合位（备选，先不实现） |
| 测试大改 | 受影响断言＝段序/角色/messages 长度三类，grep 清单逐改 |
| KV 跨环节重算 | §3 已明示接受；探针确认环节内缓存保留即可 |
