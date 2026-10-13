# V2-79d · 对话层 compaction 摘要化（规则抽取版——零模型成本）

状态: **伪代码施工稿——随票实施** ｜ 来源: V2-79 方案 §6 切票第四票 ｜ 前置: V2-79a/b/c 已合入
总方案: `tickets/v2/V2-79-对话状态重构方案.md` §3.6（长对话治理——业界标配补齐）

## 0. 本票一句话

79a 的对话层预算截断（保首尾、弃中间——任意性丢弃）升级为 **compaction 摘要化**：
dialogue 视窗预算 4000 tokens（方案建议值，独立于任务书预算）；超限时旧轮对规则
摘要化（每轮问句原文＋答案首行——零模型成本），摘要以 system 消息置顶（前情摘要），
近期轮全量保留；**压缩只作用于模型视图**——checkpoint 原史零覆盖（Anthropic 警告
「过度压缩会丢关键上下文」→ 本版只压不删，原史全量在库可查）。

**偏差注记（终审呈 Owner）**：方案 §3.6 原文「摘要落 process_notes」——本票改为
编译期确定性现算（规则抽取零模型成本、随取随有、永不陈旧）；落库反而引入第二份
需要同步的摘要面。语义（原史不覆盖）与方案一致。

## 1. 施工伪代码

### 1.1 context.py —— compaction 单点（替换 _fit_history）

```python
DEFAULT_DIALOGUE_VIEW_TOKENS = 4000    # 方案 §3.6 建议值（独立于任务书预算）
_SUMMARY_HEAD_CAP = 120                # 摘要行单行上限（问原文/答首行）

def _compact_dialogue(turns, budget) -> tuple[list[turn], str | None]:
    """超预算旧轮→规则摘要；近期窗全量保留。返回（保留轮, 前情摘要｜None）。
    - 总量入预算 → (turns, None)（零压缩零漂移）；
    - 从尾部向前累积保留窗（至少 1 轮——最新轮恒在场，哪怕单轮超预算）；
    - 窗前旧轮逐轮摘要：user→「问：〈原文 ≤120〉」；assistant→「答：〈首行 ≤120〉」；
    - 摘要形＝「（前情摘要——旧轮原文已压缩，完整原史在会话档案可查）\n问：…\n答：…」。
    """
def _fit_history(...)   # 删除（compaction 取代纯截断）
```

### 1.2 compile 装配

```python
kept, summary = _compact_dialogue(run_state.dialogue, self.dialogue_view_tokens)
messages = [system(角色红线)]
if summary: messages.append({"role": "system", "content": summary})   # 前情摘要置顶
messages += kept + [current]
# Manifest.selected_reason：压缩时追加「对话层 compaction：N 轮→保留 K 轮＋前情
# 摘要（预算 4000）」——截断/压缩必披露纪律。
```

### 1.3 测试面（test_v2_multi_turn_context.py 改两钉＋新增）

1. 预算内钉：不变（字段名 max_context_tokens→dialogue_view_tokens）；
2. 超预算钉改 compaction 形：messages＝[system, 前情摘要(system), 近期轮…, 当前轮]；
   摘要含最早问句原文＋被压轮「问：/答：」行；reason 带 compaction 披露；
3. 新增：最新轮单轮超预算仍恒在场（kept 至少 1 轮——对话锚不丢）；
4. 新增：摘要行规则钉（问原文截 120／答取首行截 120）。

## 2. 边界红线

context.py 单文件＋tests；checkpoint 原史零覆盖；零模型调用（规则抽取）；零新依赖。

## 3. 验收

全量 pytest＋六闸绿。

## 完工记录（2026-10-13）

- context.py：`_compact_dialogue` 上岗（替换 _fit_history——纯截断退役）：超预算旧轮
  规则摘要化（user→问原文/assistant→答首行，`_head_line` 单行截 120），保留窗从尾部
  累积、最新轮恒在场（单巨轮独占预算＝原样放行零压缩）；`DEFAULT_DIALOGUE_VIEW_TOKENS
  =4000`（方案 §3.6 建议值）；摘要以 system 消息置顶（序列合法）；压缩披露进
  Manifest.selected_reason（轮数前后账＋预算值＋原史可查注记）；checkpoint 原史零覆盖。
- 偏差注记（票面 §0 已登记）：摘要编译期现算（不落 process_notes）——规则抽取零成本
  随取随有，落库引入陈旧面；语义（原史不覆盖）与方案一致，终审呈 Owner。
- 钉测：预算内钉（字段改名 dialogue_view_tokens）＋超预算 compaction 形钉（摘要置顶/
  披露/原史零覆盖/保留窗含最新轮）＋单巨轮零压缩钉＋摘要行规则钉＋_head_line 上限钉；
  全量 1741 过（基线 1738＋3 净增）六闸绿。
