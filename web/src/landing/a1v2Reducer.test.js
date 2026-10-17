/**
 * a1v2Reducer ＋ api/chatV2 钉测（问一问V2 对接基座）。
 *
 * 真事件序列素材（逐字转录，零编造）：
 * - eval/results/V2-场景对照-20261013/runs-复测-70b72b/ 三个 jsonl 的 leg=="frame"
 *   行转 {id, event, data}：
 *   ambig.jsonl：run-f39e6707 无挂起直接收口形（37 帧，实测 n_asks=0——无 ask 帧）；
 *   reject.jsonl：run-b951ecc7 澄清挂起形（ask(kind=clarify) 后照发 done；续推腿
 *   收口 notice 实测 type=budget_converged gates=[max_rounds]）；
 *   extable.jsonl：run-46425185 审批挂起形（ask(kind=external_table_approval，
 *   detail.approval_id=precond-s2)→续推腿 approval_recorded）。
 * - eval/results/frames/（FE-01 扩面素材，jq 抽取）：
 *   EB4-A-正1.json 信封 id≤25 前缀（run-b8e6d07c「W-11 井生产套管的尺寸与下深」——
 *   真机到达序 tool(seq7) 先于承载 step(seq7)，中间夹 observation×16）；
 *   EB4-数-明2.json supplement 三块（id=120 lineage／121 attribution／122 citations）
 *   与 payload 观察（id=59——lineage 五要素＋limit{hit,rows}）；
 *   EB4-A-正3.json id=110 split 块（EB4-数-明2 实测仅 3 块——同批 EB4-A 补齐第四块）；
 *   EB2-D-诱9.json 引擎异常腿（run-4c83211c：id=100 notice run_failed → id=102 done
 *   真实收口——取代合同构造形）。
 *
 * 素材实测与票面描述出入，钉测一律以真实帧为准：
 * ① ambig 无 ask 帧（澄清挂起形实测在 reject 序列第一腿）；② clarify 选项实测
 * 3 条（非 2 条）；③ reject 收口 notice 实测为 budget_converged（素材中无
 * clarify_capped）；④ EB4-数-明2 supplement 实测 3 块（票面写「4 类块帧序列」），
 * split 取 EB4-A-正3 id=110 补齐，四块全部真机转录。挂起腿收束语义（ask 后照发
 * done→closed='done' 且 runStatus 保持 'waiting_ask'）由 reject/extable 两序列共同钉死。
 *
 * chatV2 层：vi.mock streamChat 捕获入参（路径/载荷形状）；getRunV2 走
 * vi.stubGlobal('fetch') 非 2xx→ApiError（同 api/chat.test.js 惯例）。
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client.js'
import { streamChat } from '../api/chat.js'
import { getRunV2, postAskV2, postResumeV2, resumeBodyFromAskFrame } from '../api/chatV2.js'
import { newTurnV2, phaseOf, reduceV2Frame, reduceV2Frames } from './a1v2Reducer.js'

vi.mock('../api/chat.js', () => ({ streamChat: vi.fn() }))

// ── 真实帧逐字转录（runs-复测-70b72b 三 jsonl 的 leg=="frame" 行） ──

/** ambig.jsonl 第一腿（run-f39e6707——「有效产量是多少」，无挂起直接收口）。 */
const AMBIG_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-f39e6707', resume: false } },
  { id: '1', event: 'step', data: { step: 'decision', seq: 1, title: '问有效产量是多少。' } },
  { id: '2', event: 'text', data: { content: '问有效产量是多少。' } },
  {
    id: '19',
    event: 'notice',
    data: {
      type: 'window_note',
      gates: [],
      content: '召回 37 支/送窗 11 支；已召回未送窗 26 支；矛盾来源同窗并立（各留代表支）：'
        + '《C-渤中34-5油田三季度注水调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》、'
        + '《A-W11井完井工程报告》、《渤中34-8油田一季度注采调整与生产运行分析》；缺位来源（预算未及）：'
        + '《渤中34-8油田躺井治理与检泵作业月报-202701》、《Y-21井完井工程报告》；'
        + '节级摘要展开节内切片 +5 支（摘要命中→节内补席）'
    }
  },
  { id: '36', event: 'done', data: { run_id: 'run-f39e6707' } }
]

/** reject.jsonl 第一腿（run-b951ecc7——「帮我预测明年油价」，澄清挂起形）。 */
const REJECT_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-b951ecc7', resume: false } },
  { id: '1', event: 'step', data: { step: 'decision', seq: 1, title: '预测明年油价。' } },
  { id: '2', event: 'text', data: { content: '预测明年油价。' } },
  {
    id: '4',
    event: 'ask',
    data: {
      frame: {
        kind: 'clarify',
        prompt: '您的「明年油价预测」不在本系统数据范围——本系统覆盖油田生产台账与报告（产量、注水、井况等），并不接入油价市场预测模型。请确认范围：',
        options: [
          '退出本题——本系统不预测油价',
          '改问油田生产指标（例如明年产量完成率预测／明年递减率走势等）',
          '改问报告事实（例如本月油价相关条款／完井报告中是否提及油价影响）'
        ],
        detail: null
      },
      run_id: 'run-b951ecc7'
    }
  },
  { id: '6', event: 'done', data: { run_id: 'run-b951ecc7' } }
]

/** reject.jsonl 第二腿（续推——body 实录 {kind:'clarify',choice:'退出本题——本系统不预测油价'}）。 */
const REJECT_RESUME_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-b951ecc7', resume: true } },
  {
    id: '6',
    event: 'notice',
    data: {
      type: 'budget_converged',
      gates: ['max_rounds'],
      content: '预算触界收敛（max_rounds）——未完成项：工具（discover/execute）未执行或未取得观察；'
        + '观察（observe）未入栈；核验（verify）/阐述（answer）未执行。未取得可交付观察材料——如实回报，不编造。'
    }
  },
  { id: '11', event: 'done', data: { run_id: 'run-b951ecc7' } }
]

/** extable.jsonl 第一腿 ask 帧的 frame 载荷（逐字——审批挂起形真样本）。 */
const EXTABLE_ASK_FRAME = {
  kind: 'external_table_approval',
  prompt: '子问题 s2 的取数计划引用外部表 erp_well_register——是否批准越集查询？',
  options: ['批准', '驳回'],
  detail: {
    approval_id: 'precond-s2',
    tables: ['erp_well_register'],
    reason: '外表越集审批（前置条件机判定——放行态落 ToolContext）',
    impact: '批准后该表进放行名单（ToolContext），不重排计划',
    declared_tables: ['erp_well_register'],
    detected_tables: ['erp_well_register'],
    miss_declared: []
  }
}

/** extable.jsonl 第一腿（run-46425185——外表越集审批挂起形）。 */
const EXTABLE_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-46425185', resume: false } },
  { id: '5', event: 'step', data: { step: 'decision', seq: 4, title: '前置条件机：s1=pass｜s2=blocked_ask｜s3=pass' } },
  { id: '65', event: 'ask', data: { frame: EXTABLE_ASK_FRAME, run_id: 'run-46425185' } },
  { id: '67', event: 'done', data: { run_id: 'run-46425185' } }
]

/** extable.jsonl 第二腿（续推——body 实录 {kind:'approval',decision:'approve',approval_id:'precond-s2'}）。 */
const EXTABLE_RESUME_FRAMES = [
  { id: '0', event: 'session', data: { run_id: 'run-46425185', resume: true } },
  {
    id: '1',
    event: 'notice',
    data: { type: 'approval_recorded', gates: [], content: '审批单号 precond-s2 已留痕（resume 留痕，可回溯）。' }
  },
  { id: '34', event: 'done', data: { run_id: 'run-46425185' } }
]

// ── FE-01 真机帧转录（eval/results/frames/，jq 抽取——行序＝信封到达序） ──

/** EB4-A-正1.json 信封 id≤25 前缀（run-b8e6d07c——27 帧：session(-1)→text(understanding)
 *  →notice→step×6→tool(seq7)→observation×16→step(seq7)。id=-1 为字符串号，余为数字号）。 */
const EB4_A_PREFIX_FRAMES = [
  {"id": "-1", "event": "session", "data": {"run_id": "run-b8e6d07c", "resume": false}},
  {"id": 0, "event": "text", "data": {"content": "理解：问 W-11 井生产套管的尺寸与下深。", "kind": "understanding"}},
  {"id": 1, "event": "notice", "data": {"type": "unsupported_claim", "gates": [], "content": "理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。"}},
  {"id": 2, "event": "step", "data": {"step": "decision", "seq": 1, "title": "模型调用：understand"}},
  {"id": 3, "event": "step", "data": {"step": "decision", "seq": 2, "title": "理解候选违约：名录外 1 个"}},
  {"id": 4, "event": "step", "data": {"step": "decision", "seq": 3, "title": "模型调用：decision"}},
  {"id": 5, "event": "step", "data": {"step": "decision", "seq": 4, "title": "澄清 r1：分解 1 子问题"}},
  {"id": 6, "event": "step", "data": {"step": "decision", "seq": 5, "title": "模型调用：decision"}},
  {"id": 7, "event": "step", "data": {"step": "decision", "seq": 6, "title": "前置条件机：s1=allow"}},
  {"id": 8, "event": "tool", "data": {"tool": "doc_retrieve", "status": "ok", "seq": 7, "message": null}},
  {"id": 9, "event": "observation", "data": {"index": 1, "source": "《A-W11井完井工程报告》", "content": "1.2 井身结构（实钻）　　层次　　　　套管尺寸　　下深（米）　　　水泥返高\n　　隔水管　　　30″　　　　0 ～ 118.5　　　泥面\n　　表层套管　　20″　　　　322.4　　　　　 泥面\n　　技术套管　　13-3/8″　　1258.6　　　　　 地面\n　　生产套管　　9-5/8″　　 2462.0　　　　　 地面生产套管钢级 N80、壁厚 10.03 毫米，固井质量测井评价合格段占比 96.8%，油层顶界 2380 米以上 200 米内无明显窜槽。人工井底 2532.6 米。", "trust": "report"}},
  {"id": 10, "event": "observation", "data": {"index": 2, "source": "《A-W11井完井工程报告》", "content": "第十章 邻井完井情况对照━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━　　井号　　完井方式　　　射孔段厚(米)　孔密(孔/米)　初期日产油(m³/d)　投产地层\n　　W-07　　套管射孔＋筛管　22.0　　　　 13　　　　　 291　　　　　　　 2023-05\n　　W-09　　套管射孔　　　　31.5　　　　 16　　　　　 402　　　　　　　 2024-11\n　　W-11　　筛管适度防砂　　28.0　　　　 16　　　　　 386　　　　　　　 2026-07对照说明：W-09 井未下防砂筛管（地层评价结论当时偏乐观），生产两年余未见出砂，是本井敢于采用筛管适度防砂（而非砾石充填）的重要参照；W-07 井历史上曾发生筛管堵塞（2024 年 3 月，堵塞段集中于上段），处理方式为酸洗解堵，未影响筛管继续使用。W-07 井目前日产油已递减至 96 m³/d，含水 71.4%，处于双高阶段。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━附录A 主要入井物资与用量━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━　　物资　　　　　　　　规格　　　　　　　数量\n　　精密冲缝筛管　　　　7″·150μm　　　　 41.0 米（三段跨装）\n　　油管　　　　　　　　4-1/2″·N80　　　 2486.5 米\n　　射孔枪　　　　　　　SYD-102　　　　　 3 支（合计弹 448 发）\n　　永久封隔器　　　　　7″·液压坐封　　　 1 套\n　　井下安全阀　　　　　SCSSV·液控　　　　1 套（液控管线 291.0 米）\n　　滑套　　　　　　　　7″·开关式　　　　 1 套　　扶正套　　　　　　　φ148　　　　　　 36 只　　完井液　　　　　　　过滤海水 KCl 体系 320 立方米（含损耗）注：液控管线到 SCSSV 悬挂点长度 291.0 米（285.3 米阀深＋地面余量），与第五章安全阀深 285.3 米为两个不同口径数值，引用时注意区分。（本报告为评测用拟造数据，井号、数值均非真实生产数据。）", "trust": "report"}},
  {"id": 11, "event": "observation", "data": {"index": 3, "source": "《A-W11井完井工程报告》", "content": "〔节级摘要｜《A-W11井完井工程报告》·章节 01 第一章 井基本情况｜覆盖 4 支切片〕W-11井位于渤中34-5油田三号构造高部位、CEP-C平台西侧8号井槽，为常规定向生产井，设计井深2530米（垂深2360米），完钻井深2541米，垂深2368米。目的层为东营组二段（Ed2），油层中深2399米，孔隙度24.3%，渗透率486 mD。四层套管结构：30″隔水管、20″表层套管（322.4米）、13-3/8″技术套管（1258.6米）、9-5/8″N80生产套管（2462.0米，壁厚10.03毫米，固井合格段96.8%），人工井底2532.6米。与A版设计差异：完井液密度由1.10 g/cm³下调至1.05 g/cm³，其余一致。", "trust": "report"}},
  {"id": 12, "event": "observation", "data": {"index": 4, "source": "《A-W11井完井工程报告》", "content": "W-11井位于渤中34-5油田三号构造高部位,为常规定向生产井,完钻井深2541米,目的层为东营组二段,采用9-5/8\"生产套管固井合格段占比96.8%。完井段密度由设计1.10 g/cm³依据邻井压力复核下调至1.05 g/cm³,采用过滤海水+KCl体系完井液。射孔采用TCP加压延时起爆,分三段共28.0米、448发,发射率100%;防砂选用7\"精密冲缝筛管150微米精度适度防砂,未充填砾石。施工中第三射孔段漏失115立方米经堵漏浆处理后恢复,筛管下入2410米遇阻经顶驱循环旋转通过。12mm油嘴求产折算日产油386 m³/d,采油指数208.6,表皮系数预计-2.0~-1.0,完井质量综合94.2分,建议按12mm油嘴投产。", "trust": "report"}},
  {"id": 13, "event": "observation", "data": {"index": 5, "source": "《A-W11井完井工程报告》", "content": "第九章 结论与建议━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━（1）W-11 井完井施工按 B 版方案完成，射孔、防砂、管柱三项主作业质量评价优良；（2）完井段密度按实钻压力复核由设计 1.10 下调至 1.05 g/cm³，实践证明近平衡微正压设计有效（漏失可控、产能正常）；（3）建议生产前 3 个月每月取样化验含砂量，验证 150 微米防砂精度适应性；（4）建议 W-111 观察井压力数据每旬回传一次，用于标定本井生产压差与地层能量；（5）后续如需分层措施，可开启 1520.8 米滑套配合下入插入密封。附：主要工期统计——搬迁安装 2.0 天、射孔 1.5 天、防砂完井 4.5 天、诱喷求产 2.0 天、合计 10.0 天（计划 9.5 天，超期 0.5 天，原因为插曲一漏失处理）。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 14, "event": "observation", "data": {"index": 6, "source": "《Y-21井完井工程报告》", "content": "〔节级摘要｜《Y-21井完井工程报告》·章节 01 第一章 井基本情况｜覆盖 4 支切片〕Y-21井位于渤中34-8油田一号构造东高点CEP-D平台12号井槽，为常规定向生产井，完钻井深2996米（垂深2772.5米）。目的层为沙河街组Es2主力油层（中深2826米），平均孔隙度21.6%、渗透率320mD。井身结构为四层套管（30″/20″/13-3/8″/9-5/8″）+7″尾管，固井质量合格率97.2%。完井段密度由A版1.05下调至1.02g/cm³，射孔负压由2.5上调至3.0MPa。", "trust": "report"}},
  {"id": 15, "event": "observation", "data": {"index": 7, "source": "《C-渤中34-5油田三季度注水调整与生产运行分析》", "content": "五、递减与能量分析━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━三季度自然递减率 4.6%，同比下降 0.9 个百分点；综合递减率 6.1%，同比上升 0.2 个百分点——自然递减改善主要来自 W-33 酸化增油与含水回落，综合递减上升反映措施总量偏少（季度仅 1 井次）。递减增油口径提示：自然递减率与综合递减率之间的差值部分即为措施贡献量，台账中\"递减增油\"指标存在口径争议注记（待联席裁决），本报告暂按\"措施后产量与递减基线之差\"的作业区口径统计，不直接与台账对比。注采比长期低于 1.0 的能量后果：地层压力由年初 21.9 MPa 降至当前 21.4 MPa（参照 W-111 观察井实测），压力保持率 97.7%。若四季度月注采比不能稳定在 1.0 附近，预计年末地层压力降至 21.1 MPa 以下，将触及 96% 保持率的开发红线。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 16, "event": "observation", "data": {"index": 8, "source": "《A-W11井完井工程报告》", "content": "第一章 井基本情况━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 17, "event": "observation", "data": {"index": 9, "source": "《A-W11井完井工程报告》", "content": "1.1 井位与井别W-11 井位于渤中 34-5 油田三号构造高部位，CEP-C 生产平台西侧井槽 8 号位。本井为生产井，井型为常规定向井，设计井深 2530 米（垂深 2360 米），完钻井深 2541 米，垂深 2368 米。目的层为东营组二段（Ed2）主力油层，油层中深 2399 米，属常规中高渗砂岩油藏，平均孔隙度 24.3%，平均渗透率 486 mD。同平台 W-111 井为观察井，不承担生产任务，主要用于油藏压力监测与注水推进观察，其压力计于 2026 年 6 月 30 日完成下放，基线压力 21.4 MPa。本报告涉及的地面流程与 W-111 井共用测试分离器，但井下作业互相独立。", "trust": "report"}},
  {"id": 18, "event": "observation", "data": {"index": 10, "source": "《A-W11井完井工程报告》", "content": "1.3 与 A 版设计的差异说明A 版设计文件中完井液完井段密度设计值为 1.10 g/cm³；现场依据邻井 W-09 井实钻压力复核，将完井段密度下调至 1.05 g/cm³（详见第三章），其余井身结构、射孔井段与 A 版一致。本报告所有数据除特别注明外均为现场实际执行值。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 19, "event": "observation", "data": {"index": 11, "source": "《Y-21井完井工程报告》", "content": "第一章 井基本情况━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 20, "event": "observation", "data": {"index": 12, "source": "《Y-21井完井工程报告》", "content": "1.1 井位与井别Y-21 井位于渤中 34-8 油田一号构造东高点，CEP-D 生产平台东侧井槽 12 号位。本井为生产井，常规定向井，设计井深 2980 米（垂深 2760 米），完钻井深 2996 米，垂深 2772.5 米。目的层为沙河街组二段（Es2）主力油层，油层中深 2826 米、顶界 2748 米，属中渗疏松细砂岩油藏，平均孔隙度 21.6%，平均渗透率 320 mD，层内渗透率变异系数 0.38。同平台 Y-19、Y-23 井为本井邻井，均生产 Es2 层系。本报告数据除注明外均为现场实际执行值。", "trust": "report"}},
  {"id": 21, "event": "observation", "data": {"index": 13, "source": "《Y-21井完井工程报告》", "content": "1.2 井身结构（实钻）　　层次　　　　套管尺寸　　下深（米）　　　水泥返高\n　　隔水管　　　30″　　　　0 ～ 126.0　　　泥面\n　　表层套管　　20″　　　　348.2　　　　　 泥面\n　　技术套管　　13-3/8″　　1425.8　　　　　 地面\n　　生产套管　　9-5/8″　　 2680.4　　　　　 地面\n　　尾管　　　　7″　　　　 2680.4 ～ 2975.0　返至悬挂器顶生产套管钢级 N80、壁厚 10.03 毫米，固井质量测井合格段占比 97.2%，油层顶界以上 200 米内无明显窜槽。7″ 尾管钢级 N80、壁厚 9.19 毫米，悬挂器坐挂于 9-5/8″ 生产套管内 2665.2 米，尾管固井碰压 12.5 MPa。钻井人工井底 2968.8 米，完井丝堵底界 2951.6 米。", "trust": "report"}},
  {"id": 22, "event": "observation", "data": {"index": 14, "source": "《Y-21井完井工程报告》", "content": "1.3 与 A 版设计的差异说明A 版设计完井段密度 1.05 g/cm³；现场依据四开实测地层压力复核下调至 1.02 g/cm³（见第二章），射孔负压相应由 2.5 MPa 上调至 3.0 MPa，其余与 A 版一致。━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", "trust": "report"}},
  {"id": 23, "event": "observation", "data": {"index": 15, "source": "检索供给窗声明（截断显式）", "content": "共检索到 56 条材料，14 条用进了答案；另有 42 条已找到但未用进答案（受送入答案的数量限制）；以下材料来源说法不一，各保留了代表条目：《A-W11井完井工程报告》、《Y-21井完井工程报告》、《C-渤中34-5油田三季度注水调整与生产运行分析》；以下来源因数量限制未纳入：《渤中34-8油田一季度注采调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》；以下条目因直接命中提问关键词获得保留：《C-渤中34-5油田三季度注水调整与生产运行分析》；命中的章节摘要已展开为节内材料（+7 条）", "trust": "notice"}},
  {"id": 24, "event": "observation", "data": {"index": 16, "source": "检索供给窗声明（缺位名单）", "content": "检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《B-渤中34-5油田躺井治理与检泵作业月报-202608》", "trust": "report"}},
  {"id": 25, "event": "step", "data": {"step": "execute", "seq": 7, "title": "doc_retrieve：ok（子问题 s1）"}},
]

/** EB4-数-明2.json supplement 三块（id=120/121/122 逐字——lineage 无边界空白（trim 原样），
 *  attribution/citations 带前导 \n\n（strip 证据））。 */
const EB4_SHU2_LINEAGE_FRAME = {"id": 120, "event": "supplement", "data": {"block": "lineage", "text": "① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注\n② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）\n③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)\n　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）\n④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）\n⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"}}

const EB4_SHU2_ATTRIBUTION_FRAME = {"id": 121, "event": "supplement", "data": {"block": "attribution", "text": "\n\n按来源分别列出（每条结论都标出它来自哪个来源）：\n[1] agg.fct_daily_metering：井号=N-01；区块=渤南；日期=2026-01-01；日产液量（方）=36.97\n[2] agg.fct_daily_metering：井号=N-02；区块=渤南；日期=2026-01-01；日产液量（方）=48.72\n[3] agg.fct_daily_metering：井号=N-03；区块=渤南；日期=2026-01-01；日产液量（方）=45.67\n[4] agg.fct_daily_metering：井号=N-04；区块=渤南；日期=2026-01-01；日产液量（方）=38.92\n[5] agg.fct_daily_metering：井号=N-05；区块=渤南；日期=2026-01-01；日产液量（方）=69.97\n[6] agg.fct_daily_metering：井号=N-06；区块=渤南；日期=2026-01-01；日产液量（方）=67.86\n[7] agg.fct_daily_metering：井号=N-07；区块=渤南；日期=2026-01-01；日产液量（方）=43.97\n[8] agg.fct_daily_metering：井号=N-08；区块=渤南；日期=2026-01-01；日产液量（方）=33.68\n[9] agg.fct_daily_metering：井号=N-09；区块=渤南；日期=2026-01-01；日产液量（方）=26.79\n[10] agg.fct_daily_metering：井号=N-10；区块=渤南；日期=2026-01-01；日产液量（方）=47.65\n[11] agg.fct_daily_metering：井号=N-11；区块=渤南；日期=2026-01-01；日产液量（方）=67.92\n[12] agg.fct_daily_metering：井号=N-12；区块=渤南；日期=2026-01-01；日产液量（方）=53.76\n[13] agg.fct_daily_metering：井号=N-13；区块=渤南；日期=2026-01-01；日产液量（方）=41.16\n[14] agg.fct_daily_metering：井号=N-14；区块=渤南；日期=2026-01-01；日产液量（方）=38.54\n[15] agg.fct_daily_metering：井号=N-15；区块=渤南；日期=2026-01-01；日产液量（方）=84.89\n[16] agg.fct_daily_metering：井号=N-16；区块=渤南；日期=2026-01-01；日产液量（方）=28.76\n[17] agg.fct_daily_metering：井号=N-17；区块=渤南；日期=2026-01-01；日产液量（方）=24.57\n[18] agg.fct_daily_metering：井号=N-18；区块=渤南；日期=2026-01-01；日产液量（方）=48.48\n[19] agg.fct_daily_metering：井号=N-19；区块=渤南；日期=2026-01-01；日产液量（方）=45.29\n[20] agg.fct_daily_metering：井号=N-20；区块=渤南；日期=2026-01-01；日产液量（方）=66.12\n[21] agg.fct_daily_metering：井号=N-21；区块=渤南；日期=2026-01-01；日产液量（方）=45.57\n[22] agg.fct_daily_metering：井号=N-22；区块=渤南；日期=2026-01-01；日产液量（方）=29.49\n[23] agg.fct_daily_metering：井号=N-23；区块=渤南；日期=2026-01-01；日产液量（方）=70.82\n[24] agg.fct_daily_metering：井号=N-24；区块=渤南；日期=2026-01-01；日产液量（方）=44.06\n[25] agg.fct_daily_metering：井号=N-25；区块=渤南；日期=2026-01-01；日产液量（方）=49.45\n[26] agg.fct_daily_metering：井号=N-26；区块=渤南；日期=2026-01-01；日产液量（方）=39.78\n[27] agg.fct_daily_metering：井号=N-27；区块=渤南；日期=2026-01-01；日产液量（方）=31.64\n[28] agg.fct_daily_metering：井号=X-01；区块=渤西；日期=2026-01-01；日产液量（方）=39.48\n[29] agg.fct_daily_metering：井号=X-02；区块=渤西；日期=2026-01-01；日产液量（方）=28.99\n[30] agg.fct_daily_metering：井号=X-03；区块=渤西；日期=2026-01-01；日产液量（方）=53.89\n[31] agg.fct_daily_metering：井号=X-04；区块=渤西；日期=2026-01-01；日产液量（方）=51.78\n[32] agg.fct_daily_metering：井号=X-05；区块=渤西；日期=2026-01-01；日产液量（方）=66.88\n[33] agg.fct_daily_metering：井号=X-06；区块=渤西；日期=2026-01-01；日产液量（方）=37.20\n[34] agg.fct_daily_metering：井号=X-07；区块=渤西；日期=2026-01-01；日产液量（方）=58.12\n[35] agg.fct_daily_metering：井号=X-08；区块=渤西；日期=2026-01-01；日产液量（方）=56.44\n[36] agg.fct_daily_metering：井号=X-09；区块=渤西；日期=2026-01-01；日产液量（方）=21.25\n[37] agg.fct_daily_metering：井号=X-10；区块=渤西；日期=2026-01-01；日产液量（方）=44.70\n[38] agg.fct_daily_metering：井号=X-11；区块=渤西；日期=2026-01-01；日产液量（方）=45.26\n[39] agg.fct_daily_metering：井号=X-12；区块=渤西；日期=2026-01-01；日产液量（方）=44.17\n[40] agg.fct_daily_metering：井号=X-13；区块=渤西；日期=2026-01-01；日产液量（方）=58.83\n[41] agg.fct_daily_metering：井号=X-14；区块=渤西；日期=2026-01-01；日产液量（方）=25.20\n[42] agg.fct_daily_metering：井号=X-15；区块=渤西；日期=2026-01-01；日产液量（方）=29.23\n[43] agg.fct_daily_metering：井号=X-16；区块=渤西；日期=2026-01-01；日产液量（方）=32.25\n[44] agg.fct_daily_metering：井号=X-17；区块=渤西；日期=2026-01-01；日产液量（方）=23.47\n[45] agg.fct_daily_metering：井号=X-18；区块=渤西；日期=2026-01-01；日产液量（方）=46.89\n[46] agg.fct_daily_metering：井号=X-19；区块=渤西；日期=2026-01-01；日产液量（方）=27.03\n[47] agg.fct_daily_metering：井号=X-20；区块=渤西；日期=2026-01-01；日产液量（方）=29.23\n[48] agg.fct_daily_metering：井号=X-21；区块=渤西；日期=2026-01-01；日产液量（方）=32.18\n[49] agg.fct_daily_metering：井号=X-22；区块=渤西；日期=2026-01-01；日产液量（方）=68.51\n[50] agg.fct_daily_metering：井号=X-23；区块=渤西；日期=2026-01-01；日产液量（方）=52.67\n[51] agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date：① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注\n② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）\n③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)\n　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）\n④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）\n⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"}}

const EB4_SHU2_CITATIONS_FRAME = {"id": 122, "event": "supplement", "data": {"block": "citations", "text": "\n\n引用：\n[1] agg.fct_daily_metering · N-01@2026-01-01（authoritative）\n[2] agg.fct_daily_metering · N-02@2026-01-01（authoritative）\n[3] agg.fct_daily_metering · N-03@2026-01-01（authoritative）\n[4] agg.fct_daily_metering · N-04@2026-01-01（authoritative）\n[5] agg.fct_daily_metering · N-05@2026-01-01（authoritative）\n[6] agg.fct_daily_metering · N-06@2026-01-01（authoritative）\n[7] agg.fct_daily_metering · N-07@2026-01-01（authoritative）\n[8] agg.fct_daily_metering · N-08@2026-01-01（authoritative）\n[9] agg.fct_daily_metering · N-09@2026-01-01（authoritative）\n[10] agg.fct_daily_metering · N-10@2026-01-01（authoritative）\n[11] agg.fct_daily_metering · N-11@2026-01-01（authoritative）\n[12] agg.fct_daily_metering · N-12@2026-01-01（authoritative）\n[13] agg.fct_daily_metering · N-13@2026-01-01（authoritative）\n[14] agg.fct_daily_metering · N-14@2026-01-01（authoritative）\n[15] agg.fct_daily_metering · N-15@2026-01-01（authoritative）\n[16] agg.fct_daily_metering · N-16@2026-01-01（authoritative）\n[17] agg.fct_daily_metering · N-17@2026-01-01（authoritative）\n[18] agg.fct_daily_metering · N-18@2026-01-01（authoritative）\n[19] agg.fct_daily_metering · N-19@2026-01-01（authoritative）\n[20] agg.fct_daily_metering · N-20@2026-01-01（authoritative）\n[21] agg.fct_daily_metering · N-21@2026-01-01（authoritative）\n[22] agg.fct_daily_metering · N-22@2026-01-01（authoritative）\n[23] agg.fct_daily_metering · N-23@2026-01-01（authoritative）\n[24] agg.fct_daily_metering · N-24@2026-01-01（authoritative）\n[25] agg.fct_daily_metering · N-25@2026-01-01（authoritative）\n[26] agg.fct_daily_metering · N-26@2026-01-01（authoritative）\n[27] agg.fct_daily_metering · N-27@2026-01-01（authoritative）\n[28] agg.fct_daily_metering · X-01@2026-01-01（authoritative）\n[29] agg.fct_daily_metering · X-02@2026-01-01（authoritative）\n[30] agg.fct_daily_metering · X-03@2026-01-01（authoritative）\n[31] agg.fct_daily_metering · X-04@2026-01-01（authoritative）\n[32] agg.fct_daily_metering · X-05@2026-01-01（authoritative）\n[33] agg.fct_daily_metering · X-06@2026-01-01（authoritative）\n[34] agg.fct_daily_metering · X-07@2026-01-01（authoritative）\n[35] agg.fct_daily_metering · X-08@2026-01-01（authoritative）\n[36] agg.fct_daily_metering · X-09@2026-01-01（authoritative）\n[37] agg.fct_daily_metering · X-10@2026-01-01（authoritative）\n[38] agg.fct_daily_metering · X-11@2026-01-01（authoritative）\n[39] agg.fct_daily_metering · X-12@2026-01-01（authoritative）\n[40] agg.fct_daily_metering · X-13@2026-01-01（authoritative）\n[41] agg.fct_daily_metering · X-14@2026-01-01（authoritative）\n[42] agg.fct_daily_metering · X-15@2026-01-01（authoritative）\n[43] agg.fct_daily_metering · X-16@2026-01-01（authoritative）\n[44] agg.fct_daily_metering · X-17@2026-01-01（authoritative）\n[45] agg.fct_daily_metering · X-18@2026-01-01（authoritative）\n[46] agg.fct_daily_metering · X-19@2026-01-01（authoritative）\n[47] agg.fct_daily_metering · X-20@2026-01-01（authoritative）\n[48] agg.fct_daily_metering · X-21@2026-01-01（authoritative）\n[49] agg.fct_daily_metering · X-22@2026-01-01（authoritative）\n[50] agg.fct_daily_metering · X-23@2026-01-01（authoritative）\n[51] agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date · lineage（authoritative）"}}

/** EB4-A-正3.json id=110 split 块（EB4-数-明2 无 split——同批 EB4-A 补齐第四块；前导 \n\n）。 */
const EB4_A3_SPLIT_FRAME = {"id": 110, "event": "supplement", "data": {"block": "split", "text": "\n\n互不一致——各来源说法如下，按来源分别列出：\n[22] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》\n[43] 检索供给窗声明（缺位名单） · window_miss：检索窗注记：缺位来源（预算未及）：《渤中34-8油田一季度注采调整与生产运行分析》、《渤中34-8油田躺井治理与检泵作业月报-202701》"}}

/** EB4-数-明2.json id=59 observation（结构化血缘 payload——lineage 五要素＋limit{hit,rows}）。 */
const EB4_SHU2_PAYLOAD_OBSERVATION_FRAME = {"id": 59, "event": "observation", "data": {"index": 51, "source": "agg.fct_daily_metering ⋈ agg.dim_well ⋈ agg.dim_date", "content": "① 口径 日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注\n② 来源表 agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）\n③ 过滤条件 时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)\n　└（权限注入） 数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）\n④ 数据截至批次 批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）\n⑤ 收口注记 LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底", "trust": "authoritative", "payload": {"lineage": {"① 口径": "日产液量（方）（单位：方）——指标台账注册声明：日产计量的日产液量——源 oil_production_daily.liquid_output（R5·A.2）；agg 读模型绑定列 agg.fct_daily_metering.liquid_output（99 §2.12），口径随答案标注", "② 来源表": "agg.fct_daily_metering（agg 星型读模型 · 即汇总层「日产计量表」——99 册 §2.12/D6 star_model，机器名＝A1 解释链②冻结）⋈ agg.dim_well（井维度·按井号）⋈ agg.dim_date（日期维度·按日期）", "③ 过滤条件": "时间＝2026-01-01～2026-08-30 [2026-01-01, 2026-08-31)", "　└（权限注入）": "数据域＝全量——行级注入经 M-01 两步缝拼入 WHERE，不靠模型自觉（预埋期谓词恒空＝恒真；真分权只换谓词生产实现，注入点形状冻结）（actor＝aqiang · 落点 agg.fct_daily_metering——谓词随执行并语句）", "④ 数据截至批次": "批次 b-a1a61db9f458 · 汇总层水位 2026-08-31（承诺 T-1 · 落后 37 天 · 超期）", "⑤ 收口注记": "LIMIT 50——强制限量纪律：没写补默认 50、超 200 截到 200，只封顶不抬底"}, "limit": {"hit": true, "rows": 50}}}}

/** EB2-D-诱9.json 引擎异常腿真转录（run-4c83211c：session→…→id=100 notice run_failed
 *  →id=102 done——桥面流干净收束、done 无 ask 帧；中间帧与本腿判据无关，按腿裁取）。 */
const RUN_FAILED_LEG_FRAMES = [
  {"id": "-1", "event": "session", "data": {"run_id": "run-4c83211c", "resume": false}},
  {"id": 100, "event": "notice", "data": {"type": "run_failed", "gates": [], "content": "run 执行失败：Recursion limit of 35 reached without hitting a stop condition. You can increase the limit by setting the `recursion_limit` config key.\nFor troubleshooting, visit: https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT"}},
  {"id": 102, "event": "done", "data": {"run_id": "run-4c83211c"}},
]

// ── 归约器钉测 ──

describe('ambig 真序列（run-f39e6707 无挂起直接收口形）', () => {
  it('runId 非空、done 判完局（无 askFrame→completed）、answerText 非空、notices 类型实测 window_note', () => {
    const fresh = newTurnV2('ask', '有效产量是多少')
    const turn = reduceV2Frames(fresh, AMBIG_FRAMES)
    expect(turn.runId).toBe('run-f39e6707')
    expect(turn.closed).toBe('done')
    expect(turn.askFrame).toBeNull()
    expect(turn.runStatus).toBe('completed') // 无挂起：done 即完局
    expect(turn.answerText).toBe('问有效产量是多少。') // text 帧拼贴（非空）
    expect(turn.notices.map(n => n.type)).toEqual(['window_note']) // 实测仅 window_note
    expect(turn.notices[0].content).toContain('召回 37 支/送窗 11 支')
    // 首个 step 帧原位入列（station＝step 字段）
    expect(turn.steps[0]).toEqual({ seq: 1, station: 'decision', title: '问有效产量是多少。' })
  })

  it('纯函数：归约不改入参回合（reduceV2Frames/reduceV2Frame 均出新对象）', () => {
    const fresh = newTurnV2('ask', '有效产量是多少')
    reduceV2Frames(fresh, AMBIG_FRAMES)
    expect(fresh).toEqual(newTurnV2('ask', '有效产量是多少'))
    const t2 = newTurnV2('ask', '有效产量是多少')
    reduceV2Frame(t2, AMBIG_FRAMES[0])
    expect(t2.runId).toBe('')
  })
})

describe('reject 真序列（run-b951ecc7 澄清挂起形——ask 后照发 done）', () => {
  it('askFrame.kind=clarify 且 options 实测 3 条；done 后 runStatus 保持 waiting_ask（挂起腿收束语义）', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '帮我预测明年油价'), REJECT_FRAMES)
    expect(turn.runId).toBe('run-b951ecc7')
    expect(turn.askFrame).not.toBeNull()
    expect(turn.askFrame.kind).toBe('clarify')
    expect(turn.askFrame.options).toHaveLength(3) // 实测 3 条（票面写 2 条，以真帧为准）
    expect(turn.askFrame.options[0]).toBe('退出本题——本系统不预测油价')
    expect(turn.askFrame.detail).toBeNull()
    expect(turn.closed).toBe('done') // 本腿流正常收束
    expect(turn.runStatus).toBe('waiting_ask') // 不以 done 判完局——ask 帧在场即仍等人工
    expect(turn.answerText).toBe('预测明年油价。')
  })

  it('续推腿（session.resume=true）收口 notice 实测 budget_converged gates=[max_rounds]；无 ask→done 判完局', () => {
    const turn = reduceV2Frames(newTurnV2('resume', '帮我预测明年油价'), REJECT_RESUME_FRAMES)
    expect(turn.resumed).toBe(true)
    expect(turn.notices.map(n => n.type)).toEqual(['budget_converged']) // 实测（票面写 clarify_capped，素材中无）
    expect(turn.notices[0].gates).toEqual(['max_rounds'])
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('completed')
  })
})

describe('extable 真序列（run-46425185 审批挂起形——挂起腿＋续推腿）', () => {
  it('挂起腿：askFrame.kind=external_table_approval、detail.approval_id=precond-s2、done 后仍 waiting_ask', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下'), EXTABLE_FRAMES)
    expect(turn.runId).toBe('run-46425185')
    expect(turn.askFrame.kind).toBe('external_table_approval')
    expect(turn.askFrame.detail.approval_id).toBe('precond-s2')
    expect(turn.askFrame.options).toEqual(['批准', '驳回'])
    expect(turn.steps).toHaveLength(1) // 序列仅一个 step 帧（seq=4）
    expect(turn.steps[0].title).toContain('s2=blocked_ask')
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('waiting_ask')
  })

  it('续推腿：resumed=true、approval_recorded 留痕 notice 在场、done 判完局', () => {
    const turn = reduceV2Frames(newTurnV2('resume', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下'), EXTABLE_RESUME_FRAMES)
    expect(turn.resumed).toBe(true)
    expect(turn.notices.map(n => n.type)).toEqual(['approval_recorded'])
    expect(turn.notices[0].content).toContain('precond-s2 已留痕')
    expect(turn.closed).toBe('done')
    expect(turn.runStatus).toBe('completed')
  })
})

describe('materials/citations 同 index 原位去重（upsert 合同——同 index 二发覆盖首帧）', () => {
  // 素材内无真实同 index 二发（各腿 index 均唯一）；两帧字段值均取自真实帧
  // （observation/extable leg2 id=7；citation/ambig id=27·id=28），二发为构造更新帧。
  it('materials：同 index 两帧→数组长 1 且后帧字段覆盖', () => {
    let turn = newTurnV2('resume', '渤海油田各区块的产量，和 erp 井位台账里的坐标对一下')
    turn = reduceV2Frame(turn, {
      id: '7',
      event: 'observation',
      data: {
        index: 53,
        source: '汇总层水位读面',
        content: '新鲜度闸拦停：汇总层数据水位＝2026-08-31（落后 42 天 · 超期）——查询窗「2026-09-13～2026-10-12」'
          + '尚无已出数数据，不返回空数冒充。催办：源表催办走「考核与质量 → 问题单」。',
        trust: 'notice'
      }
    })
    turn = reduceV2Frame(turn, {
      id: '8',
      event: 'observation',
      data: { index: 53, source: '汇总层水位读面', content: '新鲜度闸解除：水位已覆盖查询窗。', trust: 'report' }
    })
    expect(turn.materials).toHaveLength(1) // 同 index 不追加
    expect(turn.materials[0].index).toBe(53) // 原位保留
    expect(turn.materials[0].content).toBe('新鲜度闸解除：水位已覆盖查询窗。') // 后帧 content 覆盖
    expect(turn.materials[0].trust).toBe('report') // 后帧 trust 覆盖
  })

  it('citations：同 index 两帧→数组长 1 且后帧 source_id 覆盖', () => {
    let turn = newTurnV2('ask', '有效产量是多少')
    turn = reduceV2Frame(turn, {
      id: '27',
      event: 'citation',
      data: { index: 1, source: '《C-渤中34-5油田三季度注水调整与生产运行分析》', source_id: 'f51', trust: 'report' }
    })
    turn = reduceV2Frame(turn, {
      id: '28',
      event: 'citation',
      data: { index: 1, source: '《C-渤中34-5油田三季度注水调整与生产运行分析》', source_id: 'ensum-d4687e6c9b68', trust: 'report' }
    })
    expect(turn.citations).toHaveLength(1)
    expect(turn.citations[0].index).toBe(1)
    expect(turn.citations[0].source_id).toBe('ensum-d4687e6c9b68') // 后帧覆盖
    expect(turn.citations[0].source).toBe('《C-渤中34-5油田三季度注水调整与生产运行分析》')
  })
})

describe('未知事件与保留收场（12 事件闭世界容错）', () => {
  it('未知事件（heartbeat）→忽略＋计数不炸流（G6——原「词表外静默忽略」契约由 FE-01/G6 取代：新增 ignoredCount 机读信号）', () => {
    const turn = reduceV2Frame(newTurnV2('ask', '有效产量是多少'), { id: '99', event: 'heartbeat', data: {} })
    expect(turn.ignoredCount).toBe(1) // 忽略+计数（G6）
    expect(turn.closed).toBeNull()
    expect(turn.runStatus).toBe('running')
    expect({ ...turn, ignoredCount: 0 }).toEqual(newTurnV2('ask', '有效产量是多少')) // 其余字段不变
  })

  it('V2-77 理解旁白分流：text 帧 kind=understanding→进 understanding 字段不混入 answerText；无 kind＝答案正文照旧', () => {
    let turn = newTurnV2('ask', '有效产量是多少')
    turn = reduceV2Frame(turn, { id: '1', event: 'text', data: { content: '用户在问候寒暄。', kind: 'understanding' } })
    turn = reduceV2Frame(turn, { id: '2', event: 'text', data: { content: '您好！请问想查什么油田数据？' } })
    expect(turn.understanding).toBe('用户在问候寒暄。') // 旁白独立成字段——灰条渲染源
    expect(turn.answerText).toBe('您好！请问想查什么油田数据？') // 答案面不再被旁白污染
    // 多段旁白拼接；kind 缺省帧恒进答案（老流兼容）。
    turn = reduceV2Frame(turn, { id: '3', event: 'text', data: { content: '（续）', kind: 'understanding' } })
    expect(turn.understanding).toBe('用户在问候寒暄。（续）')
    turn = reduceV2Frame(turn, { id: '4', event: 'text', data: { content: '。' } })
    expect(turn.answerText).toBe('您好！请问想查什么油田数据？。')
  })

  it('error 帧→closed=error 且 runStatus=failed（errorFrame 载荷落位——FE-01 对账 D-2）', () => {
    const turn = reduceV2Frame(newTurnV2('ask', '有效产量是多少'), {
      id: '9', event: 'error', data: { code: 'chat_stream_failed', message: '流内异常' }
    })
    expect(turn.closed).toBe('error')
    expect(turn.runStatus).toBe('failed')
    expect(turn.errorFrame).toEqual({ code: 'chat_stream_failed', message: '流内异常' })
  })
})

describe('引擎异常腿（run_failed notice 随行、流尾照发 done——收束语义三分之三）', () => {
  // 帧形按合同构造（eval 素材三 jsonl 无此腿真实转录）：executor.py:380-385 except 分支
  // 发 notice{type:'run_failed',gates:[],content:'run 执行失败：…'}，bridge.py:149-156
  // stream.error 为空（bus finally 干净 close）→ done 帧照发——done 无 ask 帧不再判完局
  //（FE-01 后真帧转录见 RUN_FAILED_LEG_FRAMES——EB2-D-诱9，本构造形留作回归钉）
  it('done 无 ask 帧但 run_failed notice 在场 → runStatus failed（不判完局）、closed 仍 done', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '有效产量是多少'), [
      { id: '0', event: 'session', data: { run_id: 'run-engfail', resume: false } },
      { id: '1', event: 'notice', data: { type: 'run_failed', gates: [], content: 'run 执行失败：引擎异常' } },
      { id: '2', event: 'done', data: { run_id: 'run-engfail' } }
    ])
    expect(turn.closed).toBe('done') // 流干净收束（桥面照发 done）
    expect(turn.runStatus).toBe('failed') // run 已落库 failed——不判完局（锚推进闸同判据）
    expect(turn.notices.map(n => n.type)).toEqual(['run_failed'])
  })

  it('正常收口腿无 run_failed notice → 既有语义不回归（completed）', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '有效产量是多少'), AMBIG_FRAMES)
    expect(turn.runStatus).toBe('completed')
  })
})

// ── FE-01 归约扩面（specs/frontend-redesign.md「验收测试」表 1–6 行——票面对象逐行对应） ──

describe('FE-01 supplement 四槽（G1——按 block 分派存 strip 后原文，未知 block 忽略+计数）', () => {
  it('supplement_four_slots：EB4-数-明2 三块＋EB4-A-正3 split → 四槽各为 strip 后原文；掺 bogus block → ignoredCount=1 且四槽不变', () => {
    const turn = reduceV2Frames(newTurnV2('ask', '今年各井按天列出的日产液量'), [
      EB4_SHU2_LINEAGE_FRAME,
      EB4_SHU2_ATTRIBUTION_FRAME,
      EB4_SHU2_CITATIONS_FRAME,
      EB4_A3_SPLIT_FRAME,
      // 边界帧（票面边界集「未知 block 帧在场」——票面草稿钦定 {block:'bogus'}）
      { id: '999', event: 'supplement', data: { block: 'bogus', text: '不应入槽的未知块' } }
    ])
    expect(Object.keys(turn.supplements).sort()).toEqual(['attribution', 'citations', 'lineage', 'split'])
    // strip 后原文：lineage 无边界空白——trim 原样；其余三块仅去前导 \n（slice 精确锚——
    // 前导空白去除、内文逐字保留）
    expect(turn.supplements.lineage).toBe(EB4_SHU2_LINEAGE_FRAME.data.text)
    expect(turn.supplements.attribution).toBe(EB4_SHU2_ATTRIBUTION_FRAME.data.text.slice(2))
    expect(turn.supplements.citations).toBe(EB4_SHU2_CITATIONS_FRAME.data.text.slice(2))
    expect(turn.supplements.split).toBe(EB4_A3_SPLIT_FRAME.data.text.slice(2))
    // 转录保真锚（源帧 text 字长：601/4177/3129/203——jq 实测）
    expect(turn.supplements.lineage).toHaveLength(601)
    expect(turn.supplements.attribution).toHaveLength(4175)
    expect(turn.supplements.citations).toHaveLength(3127)
    expect(turn.supplements.split).toHaveLength(201)
    expect(turn.ignoredCount).toBe(1) // 未知 block——忽略+计数，不炸流
    expect('bogus' in turn.supplements).toBe(false) // 四槽不变——未知块不落槽
  })
})

describe('FE-01 observation payload 透传（G2）', () => {
  it('observation_payload_pass_through：带 payload 帧 → materials[0].payload.lineage 五键在场、limit={hit,rows}；无 payload 帧 → payload undefined', () => {
    const turn = reduceV2Frame(newTurnV2('ask', '今年各井按天列出的日产液量'), EB4_SHU2_PAYLOAD_OBSERVATION_FRAME)
    expect(turn.materials).toHaveLength(1)
    const m = turn.materials[0]
    expect(m.index).toBe(51)
    expect(m.trust).toBe('authoritative')
    expect(Object.keys(m.payload.lineage)).toEqual([
      '① 口径', '② 来源表', '③ 过滤条件', '　└（权限注入）', '④ 数据截至批次', '⑤ 收口注记'
    ]) // 血缘五要素（①–⑤）＋└ 权限注入子键——真机键序
    expect(m.payload.limit).toEqual({ hit: true, rows: 50 })
    // 无 payload 帧（EB4-A-正1 id=9 真帧）→ payload: undefined（G2）
    const bare = reduceV2Frame(newTurnV2('ask', 'W-11 井生产套管的尺寸与下深'), EB4_A_PREFIX_FRAMES.find(f => f.event === 'observation'))
    expect(bare.materials[0].index).toBe(1)
    expect(bare.materials[0].payload).toBeUndefined()
  })
})

describe('FE-01 tool seq 保留（G3——与 step.seq 同轴）', () => {
  it('tool_seq_kept：EB4-A-正1 id=8 tool 帧 → tools[0].seq===7（既有 tools 形状字段不变＋seq）', () => {
    const toolFrame = EB4_A_PREFIX_FRAMES.find(f => f.event === 'tool')
    const turn = reduceV2Frame(newTurnV2('ask', 'W-11 井生产套管的尺寸与下深'), toolFrame)
    expect(turn.tools).toHaveLength(1)
    expect(turn.tools[0].seq).toBe(7)
    expect(turn.tools[0]).toEqual({ tool: 'doc_retrieve', status: 'ok', message: '', seq: 7 }) // 全形状钉死（message null→'' 归一）
  })
})

describe('FE-01 events 到达序（G4——信封 id 序追加，不补排序）', () => {
  it('events_arrival_order：EB4-A-正1 id≤25 前缀真机序 → events 快照钉死：understanding→notice→step1..6→tool(seq7)→materials(count 逐帧+1 至 16)→step(seq7)——「tool 先于承载 step」原样保留', () => {
    const turn = reduceV2Frames(newTurnV2('ask', 'W-11 井生产套管的尺寸与下深'), EB4_A_PREFIX_FRAMES)
    expect(turn.events).toEqual([
      { type: 'understanding', text: '理解：问 W-11 井生产套管的尺寸与下深。' },
      { type: 'notice', notice: { type: 'unsupported_claim', gates: [], content: '理解步指标候选出现名录外名字（无）——判违约，如实上报，不静默丢弃。' } },
      { type: 'step', seq: 1, phase: 'decision', title: '模型调用：understand' },
      { type: 'step', seq: 2, phase: 'decision', title: '理解候选违约：名录外 1 个' },
      { type: 'step', seq: 3, phase: 'decision', title: '模型调用：decision' },
      { type: 'step', seq: 4, phase: 'decision', title: '澄清 r1：分解 1 子问题' },
      { type: 'step', seq: 5, phase: 'decision', title: '模型调用：decision' },
      { type: 'step', seq: 6, phase: 'decision', title: '前置条件机：s1=allow' },
      { type: 'tool', seq: 7, tool: 'doc_retrieve', status: 'ok', message: '' },
      { type: 'materials', count: 16 }, // 16 帧 observation 聚合单行——count 逐帧+1 至 16
      { type: 'step', seq: 7, phase: 'execute', title: 'doc_retrieve：ok（子问题 s1）' }
    ])
    // 「tool(seq7) 先于承载 step(seq7)」真机序原样保留（不补排序——G4）
    const toolAt = turn.events.findIndex(e => e.type === 'tool')
    const step7At = turn.events.findIndex(e => e.type === 'step' && e.seq === 7)
    expect(toolAt).toBe(8)
    expect(step7At).toBe(10)
    expect(toolAt).toBeLessThan(step7At)
    // materials 聚合恒单行（不逐帧开行）
    expect(turn.events.filter(e => e.type === 'materials')).toHaveLength(1)
    expect(phaseOf(turn)).toBe('running') // 前缀无正文未收口——phase 渲染期派生（不入 state）
  })
})

describe('FE-01 runStatus 三分（G5——done 不作完局判据）', () => {
  it('run_status_three_way：done+askFrame→waiting_ask；done+run_failed notice→failed；done 干净→completed（三分各一）', () => {
    // ① done＋askFrame 在场（reject.jsonl 第一腿真帧）→ waiting_ask
    const waiting = reduceV2Frames(newTurnV2('ask', '帮我预测明年油价'), REJECT_FRAMES)
    expect(waiting.closed).toBe('done')
    expect(waiting.askFrame).not.toBeNull()
    expect(waiting.runStatus).toBe('waiting_ask')
    expect(phaseOf(waiting)).toBe('done') // closed 置位即收口；续答由 askFrame 在场驱动
    // ② done＋run_failed notice 在场（EB2-D-诱9 run-4c83211c 收口腿真帧）→ failed
    const failed = reduceV2Frames(
      newTurnV2('ask', '按台账口径，8 月 5 口检泵井的检泵周期最长的是哪口井、多少天？最短的比它短多少天？这 5 口井的检泵作业费合计多少万元？'),
      RUN_FAILED_LEG_FRAMES
    )
    expect(failed.closed).toBe('done') // 桥面流干净收束（照发 done）
    expect(failed.askFrame).toBeNull()
    expect(failed.notices.map(n => n.type)).toEqual(['run_failed'])
    expect(failed.runStatus).toBe('failed') // run 已落库 failed——不判完局
    // ③ done 干净（ambig.jsonl 真帧）→ completed
    const completed = reduceV2Frames(newTurnV2('ask', '有效产量是多少'), AMBIG_FRAMES)
    expect(completed.closed).toBe('done')
    expect(completed.runStatus).toBe('completed')
  })
})

describe('FE-01 未知帧计数（G6——机读信号在场，不炸流）', () => {
  it('unknown_event_counted：mystery 帧 → ignoredCount=1、其余字段与输入 turn 深等', () => {
    const before = newTurnV2('ask', '有效产量是多少')
    const turn = reduceV2Frame(before, { id: '99', event: 'mystery', data: {} })
    expect(turn.ignoredCount).toBe(1)
    expect({ ...turn, ignoredCount: 0 }).toEqual(before) // 其余字段与输入 turn 深等
  })
})

describe('FE-01 phaseOf 派生（票面伪代码第 3 节——phase 不入 state，渲染期纯函数）', () => {
  it('running（在跑无正文）／answering（首字已到）／done（收口——done/error 皆收口）', () => {
    expect(phaseOf(newTurnV2('ask', '有效产量是多少'))).toBe('running')
    // 首字已到未收口：AMBIG 真帧去尾 done（真机前缀）——answerText 在场＝流水线让位
    const mid = reduceV2Frames(newTurnV2('ask', '有效产量是多少'), AMBIG_FRAMES.slice(0, -1))
    expect(mid.answerText).toBe('问有效产量是多少。')
    expect(mid.closed).toBeNull()
    expect(phaseOf(mid)).toBe('answering')
    const fin = reduceV2Frames(newTurnV2('ask', '有效产量是多少'), AMBIG_FRAMES)
    expect(phaseOf(fin)).toBe('done')
    const err = reduceV2Frame(newTurnV2('ask', '有效产量是多少'), { id: '9', event: 'error', data: { code: 'chat_stream_failed', message: '流内异常' } })
    expect(phaseOf(err)).toBe('done') // error 收口同相位
  })
})

// ── api/chatV2 层（streamChat 打桩捕获入参；fetch 打桩读口） ──

describe('api/chatV2 三端点形状', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    streamChat.mockClear()
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('postAskV2 三形态：question｜resume_run_id｜followup_run_id 互斥键名上送', async () => {
    await postAskV2({ question: '有效产量是多少' })
    expect(streamChat.mock.calls[0][0].path).toBe('/v2/chat/asks')
    expect(streamChat.mock.calls[0][0].body).toEqual({ question: '有效产量是多少' })

    await postAskV2({ question: '有效产量是多少', resumeRunId: 'run-f39e6707' })
    expect(streamChat.mock.calls[1][0].body).toEqual({
      question: '有效产量是多少', resume_run_id: 'run-f39e6707'
    })

    await postAskV2({ question: '有效产量是多少', followupRunId: 'run-46425185' })
    expect(streamChat.mock.calls[2][0].body).toEqual({
      question: '有效产量是多少', followup_run_id: 'run-46425185'
    })
  })

  it('postResumeV2：body.kind 缺失抛 TypeError 且不出网；clarify/approval 两形打 /v2/chat/runs/{id}/resume', async () => {
    expect(() => postResumeV2('r1', {})).toThrow(TypeError)
    expect(() => postResumeV2('r1')).toThrow(TypeError)
    expect(streamChat).not.toHaveBeenCalled()

    await postResumeV2('run-b951ecc7', { kind: 'clarify', choice: '退出本题——本系统不预测油价' })
    expect(streamChat.mock.calls[0][0].path).toBe('/v2/chat/runs/run-b951ecc7/resume')
    expect(streamChat.mock.calls[0][0].body).toEqual({ kind: 'clarify', choice: '退出本题——本系统不预测油价' })

    await postResumeV2('run-46425185', { kind: 'approval', decision: 'approve', approvalId: 'precond-s2' })
    expect(streamChat.mock.calls[1][0].path).toBe('/v2/chat/runs/run-46425185/resume')
    expect(streamChat.mock.calls[1][0].body).toEqual({
      kind: 'approval', decision: 'approve', approval_id: 'precond-s2'
    })
  })

  it('resumeBodyFromAskFrame 双向：审批帧 approve/reject＋澄清帧 choice（输出=客户端驼峰形，链式直连 postResumeV2）', () => {
    // V2-69 基座接缝勘误（子代理上报、已修）：统一客户端层驼峰形——approvalId 由
    // postResumeV2 上线时映射 approval_id，链式调用不再静默丢审批单号。
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '批准')).toEqual({
      kind: 'approval', decision: 'approve', approvalId: 'precond-s2'
    })
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '驳回')).toEqual({
      kind: 'approval', decision: 'reject', approvalId: 'precond-s2'
    })
    // 澄清帧（reject 真帧）——真机 open 腿2 实录 body {kind:'clarify',choice:'退出本题——本系统不预测油价'}
    const clarifyFrame = REJECT_FRAMES[3].data.frame
    expect(resumeBodyFromAskFrame(clarifyFrame, '退出本题——本系统不预测油价')).toEqual({
      kind: 'clarify', choice: '退出本题——本系统不预测油价'
    })
    // 链式钉：helper 输出直连 postResumeV2——wire 侧 approval_id 不丢（mock streamChat 捕获）。
    expect(resumeBodyFromAskFrame(EXTABLE_ASK_FRAME, '批准')).toMatchObject({
      kind: 'approval', decision: 'approve', approvalId: 'precond-s2'
    })
  })

  it('getRunV2：GET /api/v2/chat/runs/{id}；404 抛 ApiError 且 status 正确；200 直读状态面', async () => {
    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ code: 'chat_run_not_found', message: '运行不存在或已过期：run-404' }),
      { status: 404, headers: { 'Content-Type': 'application/json' } }
    ))
    const err = await getRunV2('run-404').catch(e => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(404)
    expect(err.code).toBe('chat_run_not_found')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v2/chat/runs/run-404')
    expect(fetchMock.mock.calls[0][1].method).toBeUndefined() // GET 缺省

    fetchMock.mockResolvedValueOnce(new Response(
      JSON.stringify({ status: 'running', steps: [], manifest_digest: 'sha256:abc' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ))
    expect(await getRunV2('run-46425185')).toEqual({ status: 'running', steps: [], manifest_digest: 'sha256:abc' })
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v2/chat/runs/run-46425185')
  })
})
