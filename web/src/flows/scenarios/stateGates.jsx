// ===== 状态机分支闸组（思考过程 v2）：extable 外表审批 / bigresult 大结果落盘 / freshness 新鲜度闸 / rowlevel 行级权限 =====
// 树口径：learning-records/2026-09-27-业务执行全景树.md（N7.4a/N7.4b/N7.4c/N7.5a 四个分支闸节点）
import { Button, Space } from 'antd'
import { NLi, NNode, NCode, Verdict, FlowHead, ExitNode, FrontDoor } from '../common.jsx'

// ===== extable：各区块产量和 ERP 井位台账对一下 · N7.4c 外表审批（暂停等待人工处理 + 批准/驳回双分支）=====
export function ExtableFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta }) {
  const r = meta.router
  const rejected = (chosen || '').startsWith('驳回')
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1→N7.2→N7.3→N7.4c→N7.5→N7.6→N8–N10（驳回支：N7.4c 终局）" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{
          '注入扫描': '未命中',
          '禁用词索引': '未命中',
          '身份与数据域': '用户＝作业区工程师 · 数据域＝渤南，在权限范围内',
        }}>
        <NLi>✓ 实体锚定：渤海油田 → 油田实体（本体登记）</NLi>
        <NLi>○ 实体锚定：erp 井位台账 → 实体册查无，未锚定</NLi>
        <NLi>✓ 带出邻域：渤海油田的一跳邻居 渤南／渤中／渤西 区块进装配块</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋装配段＋原句 → 输出＝结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · chain 已选定；need_clarify＝true：本轮已暂停，等待人工处理</NLi>
        {stage === 2 && meta.pause && !answerOn && (
          <Space direction="vertical" size={4} style={{ marginTop: 6 }}>
            {(meta.choices || []).map(c => (
              <Button key={c.v} size="small" type={c.primary ? 'primary' : 'default'}
                onClick={() => onChoose && onChoose(c.v)}>{c.label || c.v}</Button>
            ))}
          </Space>
        )}
        {answerOn && meta.pause && (
          <NLi>→ 已选：{chosen || '批准 · 续跑（人工）'} → 移交执行链</NLi>
        )}
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 已在系统支持的 17 条链清单内　✓ slots 的渤海油田与本体登记一致</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已派发状态机六站链（问数执行器）· 链内第 4 站的表引用比对将暂停，等待人工处理</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 意图＝跨源核对（区块产量 vs 井位坐标）　✓ 范围＝渤海油田各区块 · 复用意图识别阶段的解析结果，仅做缺参校验，未额外调用模型</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 命中：日产计量表＋井档案表——白名单内、Join 合法</NLi>
        <NLi>○ ERP 井位台账不在本轮选表命中集</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用 · 流式" on={stage >= 3 && cur >= 2}>
        <NLi>模型已将 ERP 井位台账写入查询——该表存在，但不在本轮选表命中集内，由下一站表引用比对处理：</NLi>
        <NCode>{`SELECT … FROM 日产计量表 … JOIN erp_well_register ON …`}</NCode>
      </NNode>

      <NNode id="N7.4c" name="外表审批" tag="暂停 · 等待人工处理" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 执行前安全检查·表引用比对：SQL 引用选表命中集之外的外表 erp_well_register → 已触发人工审批</NLi>
        <NLi>○ 流程已暂停，审批卡写明「表引用超出选表集合: erp_well_register」</NLi>
      </NNode>

      <NNode id="N7.5" name="查询执行" tag="批准支 · 只读续跑" on={stage >= 3 && cur >= 5 && !rejected}>
        <NLi>✓ 批准后流程从中断点恢复：只读账号执行（生产库未动）→ 产量与坐标并排出数</NLi>
      </NNode>

      <NNode id="N7.6" name="结果核验" tag="批准支 · 行数/口径" on={stage >= 3 && cur >= 5 && !rejected}>
        <NLi>✓ 结果核对通过——各区块产量与 ERP 井位台账坐标并排出数（演示样本三区块）</NLi>
      </NNode>

      <NNode id="N7.4c" name="驳回终局" tag="权限拒绝 · 零重试" on={answerOn && rejected}>
        <NLi>✗ 不予执行，且不自动改写 SQL 重试</NLi>
        <NLi>→ 处理方式：请数据 Owner 先将 erp_well_register 登记进可用表白名单（安全与权限设置），再重新提问</NLi>
      </NNode>

      <ExitNode on={answerOn}
        configLine="表引用比对 ✓ 触发（erp_well_register 越集）· 审批留痕单号 APP-0915-06 ✓ · 只读执行，生产库未动 ✓" />
    </div>
  )
}

// ===== bigresult：全部在产井一年的日产量明细 · N7.5a 大结果落盘 =====
export function BigresultFlow({ stage, secDone, secFail, matched, cur, answerOn, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1→N7.2→N7.3→N7.4→N7.5a→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{
          '注入扫描': '未命中',
          '禁用词索引': '未命中',
          '身份与数据域': '验签通过 · 数据域在权限范围内',
        }}>
        <NLi>✓ 时间锚定：「这一年」→ 时间词函数命中，输出为范围估算</NLi>
        <NLi>○ 实体锚定："全部在产井／明细"实体册查无，未锚定 → 空锚点、原句留作自由文本</NLi>
        <NLi>○ 带出邻域：无锚点实体 → 无邻居带入</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋装配段＋原句 → 输出＝结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · need_clarify＝false → 已放行，进入大结果落盘链</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 已在系统支持的 17 条链清单内　✓ slots 的范围口径与问句一致</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已派发大结果落盘链：复用状态机六站前四站，执行站结果不走常规回传、走大结果分流</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="三要素＋行数量级估算" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 范围估算：86 口井 × 365 天 ≈ 3.1 万行 · 复用意图识别阶段的解析结果，未额外调用模型</NLi>
        <NLi>→ 已按行数量级判定走大结果分流执行</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 已锁定日产计量表（白名单内）</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用" on={stage >= 3 && cur >= 1}>
        <NLi>已生成全年全井明细查询（复用状态机站 3）；SQL 照常通过执行前安全检查</NLi>
      </NNode>

      <NNode id="N7.4" name="执行前安检" tag="五道检查 · 沙箱执行" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 执行前安全检查五道检查通过 → 沙箱执行：只读断言 · 资源限额 · 超时中止 → 返回 31,390 行结果集</NLi>
      </NNode>

      <NNode id="N7.5a" name="大结果落盘" tag="结果不进上下文" on={stage >= 3 && cur >= 2}>
        <NLi>✓ 行数 31,390 超过阈值 → 结果不进入对话上下文：结果集已写入 MinIO 生成文件 → 写元数据 → 签发预签名 URL</NLi>
        <NLi>→ 31,390 行均未进入对话上下文</NLi>
      </NNode>

      <NNode id="N8" name="组装取货凭证" tag="返回预览与下载凭证" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 仅返回 5 行预览＋统计摘要＋下载凭证四字段，全量数据凭凭证下载：</NLi>
        <NCode>{`artifact_id：art-9f2c7
下载 URL：/files/art-9f2c7?token=…（GET 预签名 · 小时级有效，上限 7 天）
总行数：31,390
过期时间 expires_at：2026-09-29T04:30:00Z（签发 2026-09-22 ＋ 7 天 · 演示值）`}</NCode>
      </NNode>

      <ExitNode on={answerOn}
        configLine="大结果行数阈值 ✓ 触发（31,390 行落盘）· 预览 5 行 ✓ · 下载直链小时级有效、上限 7 天 ✓" />
    </div>
  )
}

// ===== freshness：昨天的产量是多少 · N7.4a 新鲜度闸（超窗拦停 → 最近可用日）=====
export function FreshnessFlow({ stage, secDone, secFail, matched, cur, answerOn, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1→N7.2→N7.3→N7.4a→N7.5→N7.6→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{
          '注入扫描': '未命中',
          '禁用词索引': '未命中（"昨天"非禁用词）',
          '身份与数据域': '用户＝作业区工程师 · 数据域＝渤南，在权限范围内',
        }}>
        <NLi>✓ 时间锚定：昨天 → 时间词函数算窗 2026-09-24（单日）</NLi>
        <NLi>○ 实体锚定：产量 → 实体册查无，未锚定</NLi>
        <NLi>○ 带出邻域：锚点是时间窗不是实体 → 无邻居带入</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋装配段＋原句 → 输出＝结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · need_clarify＝false → 已放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 已在系统支持的 17 条链清单内　✓ slots 时间窗核验一致</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已派发状态机六站链（问数执行器）· 新鲜度检查位于执行前安全检查的新鲜度段</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 时间＝昨天（2026-09-24）· 指标＝产油量（已补全）· 范围走数据域默认（渤南）——缺参校验通过，未额外调用模型</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 已锁定日产计量表（白名单内）</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用 · 流式" on={stage >= 3 && cur >= 1}>
        <NLi>已按问句日期生成查询：</NLi>
        <NCode>{`SELECT … FROM fct_daily_metering WHERE prod_date='2026-09-24' …`}</NCode>
      </NNode>

      <NNode id="N7.4a" name="新鲜度闸" tag="出数前比对批次水位" on={stage >= 3 && cur >= 2}>
        <NLi>✓ 比对：SQL 时间窗 2026-09-24 vs 批次水位——日产计量表水位＝2026-09-22（ETL 每日 04:00 刷新，延迟约 2 天）</NLi>
        <NLi>✗ 数据水位 09-22 早于问句日期 09-24 → 已拦停，不返回该日期结果</NLi>
      </NNode>

      <NNode id="N7.5" name="查询执行" tag="改绑最近可用日" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 已改按最近可用日 9 月 22 日只读执行 → 渤南产油 1,3xx 吨（已标注数据延迟）</NLi>
      </NNode>

      <NNode id="N7.6" name="结果核验" tag="行数 / 值域 / 口径" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 核对通过，答案已附催办入口：源表催办走"考核与质量 → 问题单"流程</NLi>
      </NNode>

      <ExitNode on={answerOn}
        configLine="数据水位 2026-09-22 ✓（超窗拦停 · 已标注延迟约 2 天）· 最近可用日 9-22 出数（渤南 1,3xx 吨）✓ · 催办入口已附 ✓" />
    </div>
  )
}

// ===== rowlevel：全油田所有井的产量 · N7.4b 行级权限（WHERE 自动注入）=====
export function RowlevelFlow({ stage, secDone, secFail, matched, cur, answerOn, meta }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N7.1→N7.2→N7.3→N7.4b→N7.5→N7.6→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{
          '注入扫描': '未命中',
          '禁用词索引': '未命中',
          '身份与数据域': '用户＝作业区工程师 · 数据域＝渤南',
        }}>
        <NLi>○ 实体锚定：「全油田／所有井／产量」实体册查无，未锚定</NLi>
        <NLi>○ 带出邻域：锚点为空 → 无邻居带入，"全油田"以自由文本进装配块</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>输入＝系统提示词＋装配段＋原句 → 输出＝结构化裁决（chain / slots / confidence / need_clarify）：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · need_clarify＝false → 已放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="模型输出需复核" on={stage >= 2}>
        <NLi>✓ chain 已在系统支持的 17 条链清单内　✓ slots 的渤南对应本体表 block_bonan</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已派发状态机六站链（问数执行器）· 行权限检查位于执行前安全检查的行权限段</NLi>
      </NNode>

      <NNode id="N7" name="状态机六站链 · 意图识别" tag="校验三要素" on={stage >= 3 && cur >= 0}>
        <NLi>✓ 范围＝全油田（86 口井）· 指标＝产油量 · 无显式时间走默认窗——未额外调用模型</NLi>
      </NNode>

      <NNode id="N7.2" name="语义检索" tag="选表" on={stage >= 3 && cur >= 1}>
        <NLi>✓ 已锁定日产计量表（白名单内）</NLi>
      </NNode>

      <NNode id="N7.3" name="SQL 生成" tag="模型第 2 次调用 · 流式" on={stage >= 3 && cur >= 1}>
        <NLi>模型按"全油田"语义生成查询，WHERE 条件不含区块限制；实际可见范围由下一站权限检查收窄</NLi>
      </NNode>

      <NNode id="N7.4b" name="行级权限" tag="权限层自动改写" on={stage >= 3 && cur >= 2}>
        <NLi>✓ 数据域判定：角色＝作业区工程师 → 查策略表得数据域＝渤南——其他域不可见</NLi>
        <NLi>✓ 权限自动注入：由权限层并入 WHERE 条件 AND block_name IN ('渤南')；改写已记录进数据来源明细「（权限注入）」独立一行</NLi>
      </NNode>

      <NNode id="N7.5" name="查询执行" tag="只读执行" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 只读账号执行：无权区块的行不进入结果集 → 返回渤南 12 口井</NLi>
      </NNode>

      <NNode id="N7.6" name="结果核验" tag="行数 / 值域 / 口径" on={stage >= 3 && cur >= 3}>
        <NLi>✓ 行数／值域核对通过——其他区块数据未被返回（非脱敏处理）；跨区查看需申请数据域授权</NLi>
      </NNode>

      <ExitNode on={answerOn}
        configLine="数据域＝渤南 ✓（WHERE 自动注入 · 无模型参与）· 返回渤南 12 口井 ✓ · 越权行查不出来 ✓" />
    </div>
  )
}

export const FLOWS = {
  'extable': ExtableFlow,
  'bigresult': BigresultFlow,
  'freshness': FreshnessFlow,
  'rowlevel': RowlevelFlow,
}
