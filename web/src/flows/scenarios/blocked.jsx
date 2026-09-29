// ===== 拦截与澄清组（injection / ban / ambig / askback）：全过程树路径叙事 =====
// injection/ban：D1 拦截终局零模型（不走 FrontDoor，自写 N0+N1+终局节点）
// ambig/askback：N5a 澄清帧两实例（A 一词两译按钮式 / B 缺参反问文本式）
import { NLi, NNode, SecChecks, Verdict, FlowHead, ExitNode, FrontDoor } from '../common.jsx'
import { Button, Space } from 'antd'

// —— injection：忽略指令注入 · 统一安检第 1 检查命中，拦截终局零模型 ——
export function InjectionFlow({ stage, secDone, secFail }) {
  return (
    <div>
      <FlowHead path="N0→N1（注入扫描 ✗）→N2a 终局" />

      <NNode id="N0" name="发起对话" tag="建立会话通道" on={stage >= 0}>
        <NLi>已建立会话通道，每个事件写入缓冲区；断线后可按事件编号续传。拦截答复也从这条通道返回。</NLi>
      </NNode>

      <NNode id="N1" name="统一安检" tag="三道检查 · 未调用模型" on={stage >= 0}>
        <SecChecks done={secDone} fail={secFail} plain={{
          '注入扫描': '命中「忽略之前所有指令」特征；该特征已收录进安全测试用例库',
          '禁用词索引': '未执行（命中即拦截，后续检查不再执行）',
          '身份与数据域': '未执行（命中即拦截，后续检查不再执行）',
        }} />
      </NNode>

      <NNode id="N2a" name="注入拦截" tag="已拦截 · 未调用模型 · 未返回数据" on={secFail === 0}>
        <NLi>✓ 注入特征扫描：消息与已知注入特征库比对，命中即拦截</NLi>
        <NLi>✓ 指令分层判定：用户消息与数据内容均不作为系统指令，不能覆盖系统层规则</NLi>
        <NLi>→ 已拦截并剥离：消息中内嵌的指令未执行、注入内容已剥除；合法部分（查询表结构）可按权限继续使用查询工具</NLi>
        <NLi>✓ 拦截事件已写入审计（谁 / 何时 / 哪句 / 结论）；该特征已加入安全测试用例库</NLi>
        <NLi>✗ 已终止：模型第 1 次调用未发生，轻装配 / 意图裁决等后续节点均未执行；本次拦截已留痕</NLi>
        <NLi>配置核对：注入特征规则与安全测试用例 ✓ · 拦截事件留痕查看 ✓</NLi>
      </NNode>
    </div>
  )
}

// —— ban：老完成率 · 禁用词索引 0 号位命中，替代帧终局零模型 ——
export function BanFlow({ stage, secDone, secFail }) {
  return (
    <div>
      <FlowHead path="N0→N1（禁用词索引 ✗）→N2b 终局" />

      <NNode id="N0" name="发起对话" tag="建立会话通道" on={stage >= 0}>
        <NLi>已建立会话通道，每个事件写入缓冲区；断线后可按事件编号续传。替代帧也从这条通道返回。</NLi>
      </NNode>

      <NNode id="N1" name="统一安检" tag="三道检查 · 未调用模型" on={stage >= 0}>
        <SecChecks done={secDone} fail={secFail} plain={{
          '注入扫描': '未命中',
          '禁用词索引': '命中「老完成率」＝2024 年已废弃口径（登记在禁用词表）；文本归一化后全等比对命中',
          '身份与数据域': '未执行（命中即拦截，后续检查不再执行）',
        }} />
      </NNode>

      <NNode id="N2b" name="禁用词替代" tag="已拦截 · 未替换口径 · 未返回数据" on={secFail === 1}>
        <NLi>✓ 禁用词索引：文本先归一化（去空格 / 全半角），再与禁用词表全等比对；该检查先于解析与模型执行</NLi>
        <NLi>✓ 已组装替代帧：说明命中的规则，并提示改用「产量完成率」（Σ实际÷Σ计划，Owner：开发室）</NLi>
        <NLi>✓ 已终止：未执行检索、未生成应答、未进入意图裁决；事件已写入审计</NLi>
        <NLi>✗ 已终止：未替换口径、未返回数据；候选匹配与模型第 1 次调用均未发生（在更早的检查环节已拦截）</NLi>
        <NLi>配置核对：禁用词 / 黑话 / 一词两译台账命中 ✓ · 术语变更审批流（替代词登记走审批）✓</NLi>
      </NNode>
    </div>
  )
}

// —— ambig：有效产量 · 一词两译澄清帧（N5a-A，按钮式，pause 挂起等点选）——
export function AmbigFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5a-A→回 N5 重判→N5b→N6→模板直出（同 N19）→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中', '禁用词索引': '未命中（「有效产量」是一词两译登记词，非禁用词）', '身份与数据域': '用户老王 · 数据域＝渤南，在权限范围内' }}>
        <NLi>○ 实体锚定：「有效产量」为指标词而非实体，实体索引查无该词；无时间词、无井号</NLi>
        <NLi>✓ 术语台账命中：「有效产量」登记为一词两译词，含 A/B 两种口径，默认口径 B</NLi>
        <NLi>○ 带出邻域：无实体锚点，无可带邻域；候选仅术语台账一条</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>模型第 1 次调用：输入为系统提示词（已注入术语台账一词两译片段）＋装配段＋原句，输出为结构化裁决：</NLi>
        <Verdict r={r} />
        <NLi>✓ need_clarify＝true（一词两译未消歧）→ 已暂停派链，先弹出澄清帧，由用户选择口径</NLi>
      </NNode>

      <NNode id="N5a" name="澄清帧 · 口径两译" tag="已暂停，等待人工处理" on={stage >= 2}>
        <NLi>✓ 已取出台账中「有效产量」两种口径的定义：A 开井日历折算（分子含关井日折产）；B 剔除检修（分子剔检泵期）——两种结果相差约 3%</NLi>
        {stage >= 3 && cur >= 1 && <NLi>○ 已弹出澄清帧，列出两种口径差异供选择；未选择时按默认口径 B 出数并标注</NLi>}
        {stage >= 3 && cur >= 2 && <NLi>✓ 口径锁定：选定口径已写入会话状态，取数 / 出数全程携带版本标注；应答已带回意图裁决重新判定</NLi>}
        {stage === 2 && meta.pause && !answerOn && (
          <Space direction="vertical" size={4} style={{ marginTop: 6 }}>
            {(meta.choices || []).map(c => (
              <Button key={c.v} size="small" type={c.primary ? 'primary' : 'default'} onClick={() => onChoose(c.v)}>{c.label || c.v}</Button>
            ))}
          </Space>
        )}
        {answerOn && <NLi>→ 已选：{chosen || '默认口径 B（剔除检修）'} → 已移交执行链</NLi>}
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="重判后复核" on={stage >= 3}>
        <NLi>✓ 重判通过（带用户选择参数）：chain 在 17 链注册表内　✓ 默认口径 B 与术语条目登记一致</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 3}>
        <NLi>→ 已分派至指标卡直出段（口径消歧后移交）；后续路由由代码执行，不再调用模型</NLi>
      </NNode>

      <NNode id="N19" name="模板直出" tag="取数未调用模型" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 已按锁定口径在指标卡登记的查询模板中填参直出 → 执行前安全检查通过 ✓ → 执行完成 → 已标注口径版本 v2</NLi>
        <NLi>○ 模型调用计数：意图裁决 2 次（初判＋重判）；取数 0 次</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="默认口径＝B 剔除检修（登记在术语条目上）✓ · 口径版本 v2 标注 ✓ · 渤南 8 月有效产量 12,4xx 吨（另一译约高 3%）✓" />
    </div>
  )
}

// —— askback：N-02 最近怎么样 · 缺参反问帧（N5a-B，文本式反问，A1Chat 本场景无 pause）——
export function AskbackFlow({ stage, secDone, secFail, matched, cur, answerOn, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5a-B→N5b→N6→（应答后移交状态机续跑，本页未演示）→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中', '禁用词索引': '未命中', '身份与数据域': '用户老王 · 数据域＝渤南，在权限范围内' }}>
        <NLi>✓ 实体锚定：N-02 → 井实体（识别为井号格式，归一标准形后在实体索引中命中）</NLi>
        <NLi>○ 时间锚定：「最近」为模糊时间词，无法确定时间窗 → 时间窗＝∅（已记为缺参）</NLi>
        <NLi>✓ 带出邻域：隶属渤南作业区 · CEP-A 平台 · 注水受效 N-06（背景信息进入装配块，因缺参反问未用于出数）</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>模型第 1 次调用：输入为系统提示词＋装配段＋原句，输出为结构化裁决：</NLi>
        <Verdict r={r} />
        <NLi>✓ need_clarify＝true（时间窗缺参）→ 已转澄清反问链，等待用户补充时间范围（confidence 栏为「——」）</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="重判后核验" on={stage >= 2}>
        <NLi>✓ chain 在 17 链注册表内　✓ 井号 ID 与本体表一致　✓ 时间窗＝∅ 判为缺参</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至澄清反问链；用户应答后移交状态机续跑，后续路由由代码执行，不再调用模型</NLi>
      </NNode>

      <NNode id="N5a" name="澄清帧 · 缺参反问" tag="已暂停，等待用户应答" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 条件逐项核验（复用意图裁决解析结果，未新增调用）：井号＝N-02 ✓；时间窗 ✗</NLi>
        {cur >= 1 && <NLi>✓ 反问帧由代码按缺参策略组装：① 近 3 天 ② 近 30 天 ③ 本月至今</NLi>}
        {cur >= 2 && <NLi>○ 已暂停，等待用户应答；应答后回意图裁决补充时间窗重新判定，再移交状态机续跑（续跑段本页未演示）</NLi>}
      </NNode>

      <ExitNode on={answerOn} configLine="缺参反问策略：时间窗必填 ✓ · 候选枚举 ①近 3 天 ②近 30 天 ③本月至今 ✓ · 缺参时必反问 ✓" />
    </div>
  )
}

export const FLOWS = { injection: InjectionFlow, ban: BanFlow, ambig: AmbigFlow, askback: AskbackFlow }
