# V2-80g · KV 缓存友好的当前轮重排（变量后置——稳定前缀最大化）

状态: **伪代码施工稿——待 Owner 过目后实施** ｜ 来源: V2-80 方案 §9（KV 缓存调研——Owner 2026-10-14「只按最佳实践规划」）｜ 前置: V2-80a/d/e 已合入；cached_tokens 留痕已上线（验证面）

## 0. 本票一句话

当前轮 1 万字里，每轮变化的回喂行/「本 run 已做」段/failed 行插在指令中段——把后面约 1 万字的稳定骨架与常驻台账块的缓存全部连坐失效。本票把**全部每轮变量后置到当前轮最末**（compile 新增 `tail` 参数），使跨轮可命中前缀从「骨架头」延伸到「材料段尾」。**零语义变化**：变量内容原样搬家（含稳定段头「【本轮动态（每轮变化——置于末尾以保持前缀稳定）】」），模型读取位置从「中段」变「末尾」（官方实测问题放末尾反而提升质量）。

## 1. 现场事实（2026-10-14 核对）

- compile 内部既有序：`指令 → 常驻块 → 材料段`——常驻块已前于材料段 ✓（无需动）；
- 每轮变量的实际位置（churn 源）：回喂行（decision_error/user_hint，4 处）、「本 run 已做」过程段（V2-79c，3 处，逐轮增长是大头）、failed 回炉行（clarify）——**全部插在指令中段、常驻块之前**；
- 已知不修（记录）：`{discover_used}` 在 CLARIFY_CONTRACT 锁定逐字稿内（V2-53 附 A「不得增删字」＋两枚钉）——它只在 discover 发生时变，低频；动它需重锁逐字稿，不划算。

## 2. 施工伪代码

### 2.1 context.py —— compile 加 tail 参数（变量行统一后置点）

```python
def compile(self, run_state, *, step, instruction, with_material=True,
            extra_sources=None, tail: str = "") -> CompiledContext:
    ...
    current = instruction          # 骨架（稳定）
    # 常驻块（稳定大块）→ 材料段（追加式）——既有序不动
    ...
    if tail:
        current += ("\n\n【本轮动态（每轮变化——置于末尾以保持前缀稳定）】\n" + tail)
    # 消息列表＝[system]＋对话层＋[骨架…常驻…材料…本轮动态]
```

### 2.2 四节点变量行搬家（内容逐字保留，只挪位置）

| 节点 | 原位置（instruction 中段） | 新位置（tail） |
|---|---|---|
| decision（legacy） | 「上次决策被拒…」「用户已补充…」＋「本 run 已做」段 | tail＝回喂行＋已做段 |
| clarify | 「上次发射被拒…」「用户已补充…」＋「本 run 已做」段＋failed 回炉行 | tail＝回喂行＋已做段＋failed 行 |
| toolmatch | 「上次发射被拒…」＋「本 run 已做」段 | tail＝回喂行＋已做段 |
| answer | （本票不动——单次调用为主） | — |

语义钉自检：p039（hint 进汇总面）／过程段在册钉／回喂钉——全部位置无关（断言的是「在场」不是「第几段」），预计零改动。


## 2.3 全链路过程（按裁决图 V2 · 38 节点——每个上下文装配节点标尾巴内容）

裁决图已核对修正至现链路（web/src/pages/DecisionTreeV2.jsx——T2n 词面阀/T2b 直答两节点补入、
三处漂移修正，页面测试 13/13 过）。下表为 T0→T9 全链路：**每个会装配上下文的节点，标注
V2-80g 实施后往上下文尾巴添加的内容**；无 LLM 调用的节点不装配上下文（标——）。

| 裁决图节点 | LLM 调用 | 当前轮组装（按序） | 上下文尾巴（【本轮动态】段内容） |
|---|---|---|---|
| T0/T0x/T0y/T0z | —（T0y 播种＝对话层） | — | — |
| T1 入口阀 | — | — | — |
| T2n 词面安全阀 | —（零模型，命中即直答收口） | — | — |
| T2a 禁用词闸 | —（零模型） | — | — |
| **T2 理解** | understand | 任务书（场景→输出→样例→环境【本系统块】→红线→题干）——整轮稳定 | **无**（任务书无每轮变量） |
| T2b 无关业务直答 | —（两步收口） | — | — |
| **T3 澄清**（每轮） | decision | 锚行＋相位合同＋分解样例＋§A 指南＋finalize 边界 → 常驻台账块 | 【本轮动态】＝①上次发射被拒行 ②用户已补充行 ③本 run 已做段 ④failed 回炉行 |
| T3a 钻取 | —（工具） | — | — |
| T3b 观察入栈 | — | — | — |
| T3d 反问挂起→回收 | （回收写对话层＋user_hint） | — | —（下轮 T3 的 tail 携带） |
| T3e 截断 | —（直答） | — | — |
| **T4 工具匹配** | decision | 锚行＋匹配合同＋§A 指南＋问题组 JSON → 常驻台账块 | 【本轮动态】＝①上次发射被拒行 ②本 run 已做段 |
| T5 前置条件机 | —（零模型） | — | — |
| T5b 审批挂起→回收 | （回收写对话层） | — | — |
| **T6 批量执行** | —（工具） | — | — |
| T6a 引擎反问→回收 | （同澄清回收） | — | — |
| T6b 失败回炉 | —（回 T3，tail 随轮更新） | — | — |
| **T7 汇总作答** | answer | 答案轮三件套＋汇总合同＋子问题清单（拒因人话）＋作答指令 → 材料段 | **无**（清单随结果定稿即稳定；单次调用） |
| T8 核验 | —（零模型） | — | — |
| T9 收尾 | — | — | — |

### 2.3.1 compile 签名（唯一机制改动）

```python
# context.py ContextBuilder.compile —— 新增 tail 参数（缺省空串＝零变化）
def compile(self, run_state, *, step, instruction,
            with_material=True, extra_sources=None, tail: str = ""):
    ...
    current = instruction                    # 骨架（稳定）
    # 常驻块（稳定大块——既有序不动）
    # 材料段（追加式——观察按稳定序）
    if tail:
        current += ("\n\n【本轮动态（每轮变化——置于末尾以保持前缀稳定）】\n" + tail)
    # 消息列表＝[system]＋对话层＋[骨架…常驻…材料…本轮动态]
```

### 2.3.2 四装配位接线（before/after 伪代码）

```python
# ① clarify_node（改动最大——四件变量全部出骨架进 tail）
# before：
#   instruction = anchor + 相位合同{discover_used} + 样例 + §A + 边界句
#   if decision_error: instruction += "\n上次发射被拒：…修正后重新输出 JSON。"
#   if segment: instruction += "\n\n" + 本run已做段
#   if user_hint: instruction += "\n用户已补充：…"
#   # failed 回炉行在 instruction 组装区
#   context = compile(state, step=…, instruction=instruction, extra_sources=常驻)
# after：
+   instruction = anchor + 相位合同{discover_used} + 样例 + §A + 边界句     # 骨架（稳定）
    …（failed 行计算保留）
+   tail_parts = []
+   if decision_error: tail_parts.append(f"上次发射被拒：{decision_error}——修正后重新输出 JSON。")
+   if failed: tail_parts.append(失败回炉行…)                              # 逐条原样
+   if segment: tail_parts.append(本run已做段)                             # V2-79c 段
+   if user_hint: tail_parts.append(f"用户已补充：{user_hint}——请把它落进本轮分解。")
+   tail = "\n".join(tail_parts)
    context = compile(state, step=…, instruction=instruction,
                      extra_sources=常驻, tail=tail)

# ② toolmatch_node：同构——decision_error 行＋本run已做段 → tail
# ③ decision_node（legacy 决策环）：回喂行（decision_error／user_hint）＋本run已做段 → tail
#    （guide 稳定段留骨架；compile with_material=True 材料段在 tail 之前）
# ④ understand_node / answer_node：零改动（tail 缺省空串）
```

### 2.3.3 已知限（逐字稿锁定面）

- CLARIFY_CONTRACT 的 `{discover_used}` 计数在锁定逐字稿内（V2-53 附 A）——每轮变化点保留在
  骨架合同内（低频：仅 discover 发生时数值变），不动；
- 材料段渲染按信任级稳定序——新增高信任观察会插入既有材料之前（前缀从该点失效）：
  材料语义优先于缓存，接受并记录。

---

## 3. 理由（调研映射——Appendix B）

- OpenAI："Put stable developer instructions and shared reference material first."，每轮变化内容 "place those at the end rather than the beginning"；
- Kimi："保持同一会话中固定内容的顺序和文本完全一致，不要在前缀中插入时间戳、随机 ID 或其他动态字段。"；
- Anthropic：长文数据在前、问题在后可提质量（+30% 实测）——变量后置与质量同向；
- vLLM/方舟：前缀逐 token 精确匹配——中段一字变，后文全重算。

## 4. 测试与验证

- compile tail 钉（有 tail 追加末尾段＋稳定段头在册；无 tail 零变化）；
- 四节点变量内容搬家钉（内容在 messages[-1] 末尾段、不在骨架区）；
- 全量 pytest（位置无关钉预计零改动）＋六闸；
- **验证协议**：重排前后各跑一轮多轮对话（澄清循环场景最佳），对比留痕 `cached_tokens`——重排后第 2 轮起命中应大幅上升（前提：prompt 超模型门槛或模型支持——见方案 §9.2 缺口，命中为零不代表重排错误）。

## 5. 边界红线

变量内容逐字搬家零删改；锁定逐字稿（CLARIFY_CONTRACT 含 {discover_used}、V2-61 行集段、V2-53 附 A）零触碰；材料排序（信任级稳定序）不动；零新依赖零迁移。

## 6. 验收

六闸绿＋新钉绿＋真机多轮对比 cached_tokens 有命中提升（或如实记录模型不支持）；每票一提交。
