// ===== data-clean（树主干 N0→N10）：渤南区块本月产油量 · 全过程树路径叙事 =====
import { NLi, NNode, NCode, Verdict, FlowHead, ExitNode, FrontDoor } from './common.jsx'

export function DataCleanFlow({ stage, secDone, secFail, matched, cur, answerOn, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中', '禁用词索引': '未命中', '身份与数据域': '用户老王 · 数据域＝渤南，在权限范围内' }}>
        <NLi>✓ 已识别实体：渤南 → 区块 block_bonan　·　本月 → [09-01, 09-27)</NLi>
        <NLi>○ 已识别实体：产油量 → 未登记于指标台账，未完成映射</NLi>
        <NLi>✓ 已扩展候选范围：渤南周边 12 口井、CEP-A/B 平台加入候选集</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>模型输出结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高（≥0.8）· need_clarify＝false，裁决通过</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="复核模型输出" on={stage >= 2}>
        <NLi>✓ chain 在 17 条链注册表内　✓ slots 的 block_bonan 与登记的区块清单一致</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="按路由表分派" on={stage >= 2}>
        <NLi>→ 已分派到状态机六站链（问数执行器）· 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 时间　✓ 范围　✓ 指标 —— 三要素齐全，无需反问</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>○ 名称查询“产油量”：未登记，转入检索</NLi>
        <NLi>✓ 向量索引＋关键词索引双路检索：命中 fct_daily_metering（白名单内）→ 已锁定</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用 · 流式" on={stage >= 3 && cur >= 2}>
        <NLi>首字 420ms；SQL 生成完成：</NLi>
        <NCode>{`SELECT block_name, SUM(oil_output) FROM fct_daily_metering
WHERE block='渤南' AND prod_date>='2026-09-01' GROUP BY 1`}</NCode>
      </NNode>

      <NNode id="N7.4" name="执行前安检" tag="五道检查 · 代码 ~3ms" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 语法　✓ 只读　✓ 白名单　✓ 行权限　✓ 新鲜度（批次水位 T-3 在承诺窗口内，答案标注“数据截至 T-3”）</NLi>
      </NNode>

      <NNode id="N7.5" name="查询执行" tag="只读执行" on={stage >= 3 && cur >= 4}>
        <NLi>只读账号执行，返回 26 行（＜限量 50，未截断）</NLi>
      </NNode>

      <NNode id="N7.6" name="结果核验" tag="行数 / 值域 / 口径" on={stage >= 3 && cur >= 5}>
        <NLi>✓ 行数　✓ 值域　✓ 口径 —— 一次通过，未触发改错重试</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="查询限量 50/200 ✓ · 单次花费阈值 0.05 未触发（本问 ¥0.0042）✓ · 数据水位 T-3 ✓" />
    </div>
  )
}
