// ===== 直出组（faq / metric / context）：零生成链三场景 · 全过程树路径叙事 =====
import { NLi, NNode, Verdict, FlowHead, ExitNode, FrontDoor } from '../common.jsx'

// 三场景共用安检文案（角色/数据域事实照抄 A1Chat dataClean/rowlevel 设定：老王 · 数据域＝渤南）
const PLAIN3 = { '注入扫描': '未命中', '禁用词索引': '未命中', '身份与数据域': '用户老王 · 数据域＝渤南，在权限范围内' }

// ===== faq（产量完成率怎么算）：N18 预制问答 · 策展答案直出，全程零生成 =====
export function FaqFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N18→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={PLAIN3}>
        <NLi>✓ 问句归一化：已按七步规则处理（去空白→去 URL→小写→去首尾标点→繁转简→全角转半角→智能空格）</NLi>
        <NLi>○ 实体锚定：产量完成率为指标名、非实体；锚点集为空，原句以自由文本交给 FAQ 匹配器</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用 · 本轮唯一" on={stage >= 2}>
        <NLi>输入系统提示词＋装配段＋原句，输出结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高（≥0.8）· need_clarify＝false → 放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出已复核 ✓" on={stage >= 2}>
        <NLi>✓ chain 在 17 链注册表内　✓ slots 是文本标准问，无本体 ID 需核验</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至 FAQ 直出链（N18）；后续步骤由代码执行，无模型调用</NLi>
      </NNode>

      <NNode id="N18" name="预制问答" tag="标准问匹配与负例检查 · 代码执行" on={stage >= 3 && cur >= 0}>
        {cur >= 0 && <NLi>第 1 步（代码）：问句七步归一化（去空白→去 URL→小写→去首尾标点→繁转简→全角转半角→智能空格），生成匹配键</NLi>}
        {cur >= 1 && <NLi>第 2 步（代码）：标准问全等匹配，命中「产量完成率怎么算？」；相似问已合并至该条标准问</NLi>}
        {cur >= 2 && <NLi>第 3 步（代码）：负例检查通过 ✓——在册不予回答的问句（如油价预测）未命中，本句放行</NLi>}
        {cur >= 3 && <NLi>第 4 步（代码）：召回不足扩检未触发——本句第 1 轮即命中（上限 5 轮）</NLi>}
        {cur >= 4 && <NLi>→ 第 5 步（代码）：返回策展答案原文；本次未调用模型、无生成内容</NLi>}
      </NNode>

      <ExitNode on={answerOn} configLine="负例否决检查 ✓（油价预测类负例在册）· 扩检 ≤5 轮未触发（第 1 轮即中）✓ · FAQ 命中直出开关 开 ✓" />
    </div>
  )
}

// ===== metric（本月产量完成率）：N19 指标直出 · 固定模板填参，零模型出数 =====
export function MetricFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N19→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={PLAIN3}>
        <NLi>✓ 时间锚定：本月已解析为 [09-01, 09-27)，区间由代码计算</NLi>
        <NLi>○ 实体锚定：产量完成率为指标名、非实体；不进锚点集，交给指标卡匹配器</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用 · 本轮唯一" on={stage >= 2}>
        <NLi>输入系统提示词＋装配段＋原句，输出结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高（≥0.8）· need_clarify＝false → 放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出已复核 ✓" on={stage >= 2}>
        <NLi>✓ chain 在 17 链注册表内　✓ slots 的指标名对指标卡台账核验 ✓（产量完成率 v3 在册）</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至指标卡直出链（N19）；后续步骤由代码执行，无模型调用</NLi>
      </NNode>

      <NNode id="N19" name="指标直出" tag="命中指标卡填参 · 代码执行" on={stage >= 3 && cur >= 0}>
        {cur >= 0 && <NLi>第 1 步（代码）：命中指标卡「产量完成率 v3」，定义/公式/单位/粒度/Owner（开发室）五要素齐备；该卡已通过发布门禁（格式/引用/SQL 安全/金标回归）</NLi>}
        {cur >= 1 && <NLi>第 2 步（代码）：修饰词与维度消解完成：时间＝本月，范围＝默认全油田；本句无歧义，未弹澄清帧</NLi>}
        {cur >= 2 && <NLi>第 3 步（代码）：使用卡上登记的查询模板填参生成 SQL，未调用模型</NLi>}
        {cur >= 3 && <NLi>→ 第 4 步（执行前安全检查＋只读执行）：五道检查通过 ✓，返回 1 行汇总；答案标注口径版本 v3 与 Owner</NLi>}
      </NNode>

      <ExitNode on={answerOn} configLine="指标卡「产量完成率 v3」五要素齐备 ✓ · 查询模板发布前已过安检（格式/引用/SQL 安全/金标回归）✓ · 本次未调用模型，出数由模板直出 ✓" />
    </div>
  )
}

// ===== context（那口井有递减风险吗）：N20 上下文注入 · 指代确定性解析，不靠模型猜 =====
export function ContextFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N20→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={PLAIN3}>
        <NLi>○ 实体锚定：「那口井」为代词、句中无井号；锚点集为空，未生成实体 ID</NLi>
        <NLi>→ 页面背景（井档案页当前打开的井）已随会话提供，指代解析由链内第 1 步完成</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用 · 本轮唯一" on={stage >= 2}>
        <NLi>输入系统提示词＋装配段（候选清单为空）＋原句，输出结构化裁决：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高（≥0.8）· need_clarify＝false → 放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出已复核 ✓" on={stage >= 2}>
        <NLi>✓ chain 在 17 链注册表内　✓ slots 的 N-02 对本体实体核验 ✓</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至上下文注入链（N20）；后续步骤由代码执行，无模型调用</NLi>
      </NNode>

      <NNode id="N20" name="上下文注入" tag="指代解析与背景注入 · 代码执行" on={stage >= 3 && cur >= 0}>
        {cur >= 0 && <NLi>第 1 步（代码）：指代解析：结合会话历史与页面上下文，「那口井」解析为 N-02（井档案页当前打开的井）</NLi>}
        {cur >= 1 && <NLi>第 2 步（代码）：井档案与产量趋势已注入提示词作背景</NLi>}
        {cur >= 2 && <NLi>第 3 步（代码＋双重权限）：调用递减分析工具：选择工具，填参井号＝N-02，双重权限校验 ✓，沙箱执行</NLi>}
        {cur >= 3 && <NLi>→ 第 4 步（代码）：结论解读：递减率 4.2%/月属正常区间；仅返回结论与关键数值</NLi>}
      </NNode>

      <ExitNode on={answerOn} configLine="设备页背景注入开关 开 ✓ · 指代解析策略＝会话＋页面上下文 ✓ · 结论 4.2%/月 属正常递减区间 ✓" />
    </div>
  )
}

export const FLOWS = { 'faq': FaqFlow, 'metric': MetricFlow, 'context': ContextFlow }
