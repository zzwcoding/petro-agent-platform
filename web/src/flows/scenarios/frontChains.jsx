// ===== 前门业务链组（exfil / action / graph）：树路径叙事 v2 =====
// exfil＝N11 外发拦截 · action＝N12 受控写入 · graph＝N13 关系追溯——三者都是「前门 + 专属链 + 出口」结构
// 数字照抄 A1Chat.jsx 的 SCENARIOS / META 与业务执行全景树 N11–N13，未新造数字；文案已改写为产品界面腔
import { NLi, NNode, Verdict, FlowHead, ExitNode, FrontDoor } from '../common.jsx'

// ===== exfil：把产量数据发到我的邮箱（外发拦截链 N11）=====
export function ExfilFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N11→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中——「发到邮箱」为正常中文表述', '禁用词索引': '未命中', '身份与数据域': '令牌验签通过 · 数据域在权限范围内' }}>
        <NLi>○ 实体锚定：「产量数据」「邮箱」「我的」均查无登记 → 未锚定到已登记实体</NLi>
        <NLi>○ 带出邻域：未锚定到实体，邻域查询跳过</NLi>
        <NLi>→ 未涉及具体井对象，按整句意图裁决</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>已将系统提示词、装配内容与原句送入模型，输出结构化裁决：识别为数据外发意图：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · need_clarify＝false → 已放行</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="复核模型输出" on={stage >= 2}>
        <NLi>✓ chain 在 17 条链清单内　✓ slots 为意图级参数（不含实体 ID）→ 核验通过</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至外发拦截链 · 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N11" name="外发拦截 · 通道检查" tag="代码闸 · 查白名单" on={stage >= 3 && cur >= 0}>
        <NLi>已判定为数据外发意图 · 白名单核对：邮箱通道不在白名单内 → 拒绝</NLi>
      </NNode>

      <NNode id="N11.2" name="三者不同会话判定" tag="红线判定 · 代码执行" on={stage >= 3 && cur >= 1}>
        <NLi>红线判定：私有数据、不可信内容、外发通道三项叠加 → 判定拒绝</NLi>
      </NNode>

      <NNode id="N11.3" name="拦截＋留痕" tag="代码闸 · 拦截并留痕" on={stage >= 3 && cur >= 2}>
        <NLi>已拦截：数据未离开生产域，外发未执行、未排队、未重试；拦截事件已记入审计日志</NLi>
      </NNode>

      <NNode id="N11.4" name="正路指引" tag="组装进答案" on={stage >= 3 && cur >= 3}>
        <NLi>已组装正路指引：如有业务需要，可提交外发白名单申请，经管理员审批后开通一次性通道</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="外发通道白名单＝默认全关 ✓（白名单中不含邮箱通道）· 外发申请人工审批流——本次未触发" />
    </div>
  )
}

// ===== action：把 N-02 配注下调到 30（受控写入 Action 合同链 N12）=====
export function ActionFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N12→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中——「下调配注」为正常业务表述', '禁用词索引': '未命中', '身份与数据域': '一线工程师 · 令牌验签通过，数据域在权限范围内' }}>
        <NLi>✓ 实体锚定：N-02 → well_n02（井）　·　「配注 30 方/天」非登记实体，作为参数由意图识别提取</NLi>
        <NLi>✓ 带出邻域：N-06（注水受效关系）＋渤南作业区（隶属关系）——供影响测算使用</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>已将系统提示词、装配内容与原句送入模型，输出结构化裁决：识别为写操作并分派至对应执行链：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 → 已放行；执行仍需人工批准</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="复核模型输出" on={stage >= 2}>
        <NLi>✓ chain 在 17 条链清单内　✓ slots 中 N-02（well_n02）与本体表一致；「配注 30 方/天」为参数值，由合同核验校验</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至 Action 合同链 · 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N12" name="受控写入 · 合同四要素核验" tag="代码闸 · 查合同登记" on={stage >= 3 && cur >= 0}>
        <NLi>四要素核验：参数＝配注 30 · 规则＝在日配注区间内 · 前置＝N-02 在产 · 副作用＝邻井受效变化——四项全部满足</NLi>
      </NNode>

      <NNode id="N12.2" name="影响测算" tag="只读查询 · 未执行写入" on={stage >= 3 && cur >= 1}>
        <NLi>影响测算完成：N-06 注水量重分配，N-02 日产油预估 −2.1t/天；测算结果随审批单展示，供批准前参考</NLi>
      </NNode>

      <NNode id="N12.3" name="提交人工审批" tag="已暂停，等待人工处理" on={stage >= 3 && cur >= 2}>
        <NLi>高风险写操作已暂停，等待人工批准</NLi>
        <NLi>→ 批准后继续执行 · 驳回理由记入审计日志</NLi>
      </NNode>

      <NNode id="N12.4" name="写变更记录区" tag="append-only · 原表不动" on={stage >= 3 && cur >= 3}>
        <NLi>已写入独立变更记录区：生产原表未改动，全程审计留痕</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="Action 合同四要素齐 ✓ · 变更审批流已暂停，等待人工处理（王主任审批中）· 变动单 N-02 配注 50 → 30 方/天 · 影响测算 −2.1t/天（只读）" />
    </div>
  )
}

// ===== graph：N-02 的受效井是哪口（图谱问答链 N13）=====
export function GraphFlow({ stage, secDone, secFail, matched, cur, answerOn, chosen, onChoose, meta, sc }) {
  const r = meta.router
  return (
    <div>
      <FlowHead path="N0→N1→N3→N4→N5→N5b→N6→N13→N8–N10" />

      <FrontDoor stage={stage} secDone={secDone} secFail={secFail} matched={matched} meta={meta} r={r}
        plain3={{ '注入扫描': '未命中——关系查询属正常业务问题', '禁用词索引': '未命中', '身份与数据域': '一线工程师 · 令牌验签通过，数据域在权限范围内' }}>
        <NLi>✓ 实体锚定：N-02 → well_n02（井）　·　「受效井」非登记词，作为自由文本由意图识别提取关系词</NLi>
        <NLi>✓ 带出邻域：N-06（注水受效关系）＋渤南作业区（隶属关系）——供关系查询作为证据</NLi>
      </FrontDoor>

      <NNode id="N5" name="意图裁决" tag="模型第 1 次调用" on={stage >= 2}>
        <NLi>已将系统提示词、装配内容与原句送入模型，输出结构化裁决：slots 提取「实体＋关系」：</NLi>
        <Verdict r={r} />
        <NLi>✓ confidence＝高 · need_clarify＝false → 已放行；关系词已归一（受效井 → 注水受效）</NLi>
      </NNode>

      <NNode id="N5b" name="裁决核验" tag="复核模型输出" on={stage >= 2}>
        <NLi>✓ chain 在 17 条链清单内　✓ 实体 N-02 与本体表一致　✓ 关系「注水受效」在本体关系白名单内 → 核验通过</NLi>
      </NNode>

      <NNode id="N6" name="链路分派" tag="查映射表派链" on={stage >= 2}>
        <NLi>→ 已分派至图谱问答链 · 后续步骤由代码执行</NLi>
      </NNode>

      <NNode id="N13" name="关系追溯 · 实体解析" tag="复用意图识别结果 · 未调用模型" on={stage >= 3 && cur >= 0}>
        <NLi>实体解析完成：N-02 → 井实体</NLi>
      </NNode>

      <NNode id="N13.2" name="关系查询" tag="关系类型入库时已校验" on={stage >= 3 && cur >= 1}>
        <NLi>按「注水受效」关系查询，命中已登记关系类型</NLi>
        <NLi>○ 受效关系带劈分系数，已校验每个源节点出边系数合计＝1</NLi>
      </NNode>

      <NNode id="N13.3" name="沿链追溯" tag="逐级返回节点/边 ID" on={stage >= 3 && cur >= 2}>
        <NLi>查询路径：N-06（注水井）→ 注水受效 → N-02；N-02 —隶属→ 渤南作业区，逐级返回节点与关系 ID</NLi>
      </NNode>

      <NNode id="N13.4" name="组装结论＋图谱出处" tag="出处＝节点/边 ID" on={stage >= 3 && cur >= 3}>
        <NLi>结论已附实体 N-02 / 边 e-102，可在关系图谱页点开核对完整链路</NLi>
      </NNode>

      <ExitNode on={answerOn} configLine="图谱入库与实体关系抽取 ✓（关系类型入库时校验）· 检索档位与拒答阈值按默认设置（本问未触发拒答）· 出处＝实体 N-02 / 边 e-102 可回链" />
    </div>
  )
}

export const FLOWS = { exfil: ExfilFlow, action: ActionFlow, graph: GraphFlow }
