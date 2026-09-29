// ===== 状态机回退组（思考过程 v2）：data-fix 改错重试 / fuse 停止重试转人工 =====
import { NLi, NNode, Verdict, FlowHead, ExitNode, FrontDoor } from '../common.jsx'

// ===== data-fix：上个月产量最高的三口井 · 六站＋一条改错重试回路（重试 1/3 即成功）=====
export function DataFixFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1–N7.6→N7.6a→N7.3–N7.5→N7.6→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中', '禁用词索引': '未命中', '身份与数据域': '用户老王（作业区工程师）· 数据域＝渤南，在权限范围内' }}>
        <NLi>○ 实体锚定：未命中——句中无区块/井号，落空信号已记录</NLi>
        <NLi>✓ 时间词解析：上个月 → [2026-08-01, 2026-09-01)</NLi>
        <NLi>○「排名 / 前 3」词表未命中 → 按自由文本处理，条数＝3 由意图裁决提供</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋本轮装配内容＋用户原句，输出结构化裁决结果（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高（≥0.8）· need_clarify＝false → 通过，继续执行；slots 已带「条数＝3」，生成 SQL 时按 LIMIT 3 处理</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 在 17 条执行链注册表内　✓ slots 已对本体 ID 核验通过</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 分派至问数执行链（问数执行器）· 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 意图＝查数据排名　✓ 指标＝日产油量　✓ 时间＝上个月 [2026-08-01, 2026-09-01) · 条数＝前 3 —— 复用第 1 次模型调用的解析结果，仅做缺参校验，未发起反问</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 全库 200 张表经检索裁剪为 5 张候选</NLi>
        <NLi>✓ 命中：日产计量表＋井档案表（Join 关系在白名单内）→ 锁定</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用 · 流式" on={stage >= 3 && cur >= 2}>
        <NLi>输入＝上下文缓存＋表结构＋查询条件，输出＝SQL 文本。本轮生成的 SQL 引用了不存在的列 oil_rate（真实列名为 oil_prod），该错误要到执行阶段才会报出</NLi>
      </NNode>

      <NNode id="N7.4" name="执行前安检" tag="执行前安全检查 · 五道检查 · 耗时 ~3ms" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 查询语句结构（只读白名单）　✓ 行级权限注入　✓ 新鲜度检查　✓ 数据来源登记　✓ 审计留痕 —— 本轮检查通过；列存在性将在执行阶段校验</NLi>
      </NNode>

      <NNode id="N7.5" name="查询执行" tag="只读执行 · 第 1 次" on={stage >= 3 && cur >= 4}>
        <NLi>✗ 数据库返回错误：Unknown column（列不存在）—— 由只读执行器实际执行</NLi>
      </NNode>

      <NNode id="N7.6" name="结果核验" tag="判失败 → 触发改错重试" on={stage >= 3 && cur >= 5}>
        <NLi>✗ 核对判定失败——报错不进入答案流，留在链内进入改错重试</NLi>
        <NLi>✓ 重试执行（第 2 次）后：行数 / 值域 / 口径核对通过</NLi>
      </NNode>

      <NNode id="N7.6a" name="反思改错" tag="报错回传 → 重新生成 · 重试计数 +1" on={stage >= 3 && cur >= 6}>
        <NLi>→ 重试输入＝报错原文＋可用表结构 → 重新提交 SQL 生成（重试计数 1/3，上限 3 次）</NLi>
        <NLi>→ 模型第 3 次调用（输入＝报错原文＋可用表结构，输出＝修正后 SQL）：ORDER BY oil_prod DESC —— 列名已依据报错修正</NLi>
      </NNode>

      <NNode id="N7.3–N7.5" name="复检 · 重执行" tag="改后 SQL 重过安检" on={stage >= 3 && cur >= 7}>
        <NLi>✓ 修正后 SQL 再次通过执行前安全检查 → 只读执行 → 返回 3 行</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="改错重试上限 3 次——本次第 1 次即成功，未走满 ✓ · LIMIT 3（未指定时补默认 50 · 超过 200 截到 200，只封顶不抬底）✓ · 批次 20260911-T3（承诺水位 T-1）✓" />
    </div>
  )
}

// ===== fuse：各区块综合含水率排名 · 三次改错重试均失败 → 停止重试转人工（3/3 用尽）=====
export function FuseFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1→N7.6a×3→N7.6b→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中', '禁用词索引': '未命中', '身份与数据域': '用户老王（作业区工程师）· 数据域＝渤南，在权限范围内' }}>
        <NLi>○ 实体锚定：未命中——「各区块」为泛指，未登记为实体</NLi>
        <NLi>○「综合含水率」词表未命中 → 按自由文本处理（该指标为跨库口径，未登记指标卡）</NLi>
        <NLi>○ 无锚点实体 → 邻域扩展未返回结果</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋本轮装配内容＋用户原句，输出结构化裁决结果（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>○ confidence＝中——按置信度分档继续执行并标注，未弹出澄清；need_clarify＝false → 进入执行链，改错重试上限不变</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 在 17 条执行链注册表内　✓ slots 已对本体 ID 核验通过</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 分派至问数执行链（问数执行器）· 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 意图＝排名　✓ 指标＝综合含水率（跨库口径）—— 复用第 1 次模型调用的解析结果，仅做缺参校验</NLi>
      </NNode>

      <NNode id="N7.6a" name="反思改错 · 第 1 轮" tag="白名单拒绝 → 重新生成（计数 1/3）" on={stage >= 3 && cur >= 1}>
        <NLi>→ 模型第 2 次调用（输入＝上下文缓存＋表结构＋查询条件，输出＝SQL）：引用了不存在的表 water_monthly，被白名单拒绝（relation water_monthly does not exist）</NLi>
        <NLi>→ 报错原文回传至 SQL 生成节点重新生成，重试计数 1/3</NLi>
      </NNode>

      <NNode id="N7.6a" name="反思改错 · 第 2 轮" tag="执行返回结果 · 结果核对拦截（计数 2/3）" on={stage >= 3 && cur >= 2}>
        <NLi>→ 模型第 3 次调用 → 执行前安全检查通过 → 执行返回结果——但区块数量对不上：粒度混用了月度表与日表</NLi>
        <NLi>→ 结果核对判定失败（安检已通过，执行成功后被结果核对拦截）→ 重新生成，计数 2/3</NLi>
      </NNode>

      <NNode id="N7.6a" name="反思改错 · 第 3 轮" tag="再次改写仍失败（计数 3/3）" on={stage >= 3 && cur >= 3}>
        <NLi>→ 模型第 4 次调用 → 仍失败：口径涉及注采平衡跨粒度 join，改错重试未能修正</NLi>
        <NLi>✗ 重试计数 3/3——改错重试上限已用完</NLi>
      </NNode>

      <NNode id="N7.6b" name="熔断转人工" tag="重试 3/3 用尽 · 停止重试，转人工处理" on={stage >= 3 && cur >= 4}>
        <NLi>→ 已生成工单 QA-1024 并流转至数据工程师；会话已暂停等待人工处理并留档，处理结果将回到本会话通知</NLi>
        <NLi>→ 回复附已尝试轨迹：三次尝试全程留痕（water_monthly 白名单拒绝 / 粒度混表核对失败 / 跨粒度 join 未改成功），停止重试事件留痕可查</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="改错重试上限 3/3 走满 → 停止重试 ✓ · 工单 QA-1024 已流转至数据工程师 ✓ · 停止重试事件留痕可查 ✓ · 本次未出数——三次尝试全程留痕，未硬编答案" />
    </div>
  )
}

export const FLOWS = { 'data-fix': DataFixFlow, 'fuse': FuseFlow }
