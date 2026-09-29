// ===== 树路径叙事共享件（思考过程 v2 规范——全场景统一格式）=====
// 节点格式：NNode(id,name,tag) 标题 + NLi/NCode 内容行（✓/○/→ 前缀）
// 术语纪律：发起对话/意图识别/工作流/17 链清单内选择；禁偏门词（闭世界/听懂问题/剧本/一跳闭包/直连线…）
export const SEC_CHECKS = ['注入扫描', '禁用词索引', '身份与数据域']
export const MATCHERS = ['FAQ 索引', '指标卡台账', '术语台账', '工具清单', '分析工作流', '报告索引']
export const CHAIN17 = '统一安检链 / 状态机六站链 / 指标卡直出链 / FAQ直出链 / 工具执行链 / 工作流执行链 / 检索问答链 / 图谱问答链 / 汇报生成链 / 大结果落盘链 / Action合同链 / 外发拦截链 / 澄清反问链 / 口径消歧链 / 新鲜度闸链 / 行级权限链 / 上下文注入链'

export function NLi({ children }) {
  return <div style={{ fontSize: 12, color: '#c9d1d9', marginTop: 3, lineHeight: 1.7 }}>{children}</div>
}

export function NNode({ id, name, tag, on, children }) {
  if (!on) return null
  return (
    <div style={{ marginBottom: 12 }} onClick={e => e.stopPropagation()}>
      <div style={{ fontSize: 12 }}>
        <b style={{ color: '#79b8ff' }}>{id} {name}</b>
        {tag && <span style={{ color: '#8a94a3' }}> · {tag}</span>}
      </div>
      <div style={{ paddingLeft: 12, marginTop: 3, borderLeft: '2px solid rgba(121,184,255,0.25)' }}>{children}</div>
    </div>
  )
}

export function NCode({ children }) {
  return <div className="code-block" style={{ marginTop: 4 }}>{children}</div>
}

// 统一安检三道检查（secDone/secFail 驱动逐条翻）
export function SecChecks({ done, fail, plain }) {
  return (
    <div style={{ marginTop: 3 }}>
      {SEC_CHECKS.map((c, i) => {
        const reached = done > i
        const failed = fail === i
        return (
          <div key={c} style={{ fontSize: 12, marginTop: 2, color: failed ? '#ff7875' : reached ? '#c9d1d9' : '#555' }}>
            {failed ? '✗' : reached ? '✓' : '·'} {c}：{reached || failed ? plain[c] : '检查中…'}
            {failed ? ' —— 拦截，链路终止' : ''}
          </div>
        )
      })}
    </div>
  )
}

// 六路候选逐条翻（matched 驱动）
export function MatchList({ matched, meta, prefix = '六路候选' }) {
  return MATCHERS.map(m => {
    const flipped = matched.includes(m)
    const hit = (meta.hits || []).find(h => h.m === m)
    return (
      <div key={m} style={{ fontSize: 12, marginTop: 2, color: !flipped ? '#555' : hit ? '#79b8ff' : '#c9d1d9' }}>
        {!flipped ? '·' : hit ? '★' : '○'} {prefix} · {m}：{!flipped ? '…' : hit ? '命中' : '未命中'}
      </div>
    )
  })
}

// 模型裁决 JSON（回归断言依赖 "chain" 字段照抄 meta.router.chain）
export function Verdict({ r }) {
  const lines = ['{']
  lines.push(`  "chain": ${r.chain ? '"' + r.chain + '"' : 'null'},`)
  if (r.slots) lines.push(`  "slots": "${r.slots}",`)
  lines.push(`  "confidence": "${r.conf || '——'}",`)
  lines.push(`  "need_clarify": ${r.clarify ? 'true' : 'false'}${r.clarify ? ',' : ''}`)
  if (r.clarify) lines.push(`  "clarify_frame": "${r.clarify}"`)
  lines.push('}')
  return <NCode>{lines.join('\n')}</NCode>
}

// 路径头
export function FlowHead({ path }) {
  return (
    <div style={{ fontSize: 12, color: '#8a94a3', marginBottom: 10, lineHeight: 1.7 }}>
      <b style={{ color: '#c9d1d9' }}>处理过程</b> · {path}
    </div>
  )
}

// 出口三件套（N8 组装 → N9 推送 → N10 记账）＋配置核对行
export function ExitNode({ on, configLine }) {
  return (
    <NNode id="N8–10" name="出口" tag="组装 → 推送 → 记录" on={on}>
      <NLi>整理答案（含数据来源与出处）→ 流式推送到对话 → 完成记录（审计与日志留痕，可回查）</NLi>
      {configLine && <NLi>配置核对：{configLine}</NLi>}
    </NNode>
  )
}

// 前门公共节点：N0 发起对话 / N1 统一安检 / N3 轻装配 / N4 装配块 / N5 意图裁决 / N5b 裁决核验 / N6 链路分派
// plain3 = 三道安检的直白结果文案；asmExtra = 装配块附加行
export function FrontDoor({ stage, secDone, secFail, matched, meta, r, plain3, anchorLine, children }) {
  const asm = [
    '# —— 系统提示词 · 本轮装配（来自本体/语义层闭包）——',
    `实体/槽位：${r.slots || '∅（未锚定到显式实体）'}`,
    '术语层：未涉及',
    meta.hits && meta.hits.length
      ? `候选清单：${meta.hits.map(h => h.m + (h.c === 'low' ? '(疑似提及)' : '')).join('、')}`
      : '候选清单：∅ 全空——模型按通用知识理解问句，路由仍限 17 条链内选择',
    `可用执行链（仅这 17 条，超出即无效）：${CHAIN17}`,
  ]
  return (
    <div>
      <NNode id="N0" name="发起对话" tag="建 SSE 会话" on={stage >= 0}>
        <NLi>已建立会话通道，后续事件写入缓冲区；断线后按事件编号续传，已收到的内容不丢失。</NLi>
      </NNode>
      <NNode id="N1" name="统一安检" tag="三道检查，全过才放行" on={stage >= 0}>
        <SecChecks done={secDone} fail={secFail} plain={plain3} />
      </NNode>
      <NNode id="N3" name="轻装配" tag="代码预处理 · 毫秒级 · 不调模型" on={stage >= 1}>
        {children}
        <MatchList matched={matched} meta={meta} />
      </NNode>
      <NNode id="N4" name="装配块" tag="只整理，不替模型决定" on={stage >= 1 && matched.length >= MATCHERS.length}>
        {anchorLine}
        <NLi>识别结果与候选清单，整理进本次会话的上下文：</NLi>
        <NCode>{asm.join('\n')}</NCode>
      </NNode>
    </div>
  )
}
