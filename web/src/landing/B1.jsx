/**
 * 落地树 · B1 报告库（P1-03 全页真 API——P1-02a/P1-02b 后端 15 端点消费）。
 *
 * 合同：teach-petro-agent/specs/api/B1-报告库.md v0.3（端点 1–15）。视觉与
 * 交互形态对照原型树 #/proto/B1（prototype 终稿快照 web/src/pages/B1.jsx，
 * P1-00a 同步）——数据是真、形是原型；页面静态演示资产（切段三法对照原文与
 * 三面板）照抄原型（合同「三切法对照演示＝前端静态资产不入合同」）。
 *
 * 接线差异（相对原型页，登记票面）：
 * - 数据源 = api/kb.js（client 真 HTTP；后端 R1 snake_case 在接口层折回
 *   camel，页面列定义与原型同形；无任何 mock 种子）；
 * - 上传 = 直传两拍真流：受理（端点 5，lib_id 缺省走路由建议）→ 建议库弹窗
 *   （LLM 建议卡 理由+置信度+模板推荐——可确认/改选/直指定）→ 客户端 PUT
 *   字节直达对象存储（putObjectDirect——平台不经手）→ confirm（端点 6，
 *   带确认 lib_id）→ 任务开跑；
 * - 五步进度 = useTaskPolling 轮询端点 8（节点/note 服务端组装，前端零拼装
 *   业务文案）；失败/卡住按 stop_at/reason 人话渲染（不发明错误码）；
 * - 台账「入库中」标 = 端点 1 status 直出（v0.2 裁决）；详情/片段/版本＝
 *   端点 2；修正 = 端点 4（乐观锁 409 兜底提示——「别人已改过这段」）；
 * - 库停用/启用 = 端点 13 可选 status（连同配置全量整存整取）；
 * - 看切片行内跳转落落地树 #/B2（P1-04 点亮——P1-03 疑点 2 收口）；看百科仍落
 *   原型树 #/proto/B4（B4 落地票接线时改指）。
 */

import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Checkbox, Descriptions, Drawer, Empty, Input, message, Modal, Select,
  Space, Spin, Steps, Switch, Table, Tabs, Tag, Tooltip
} from 'antd'
import {
  BookOutlined, DownloadOutlined, FileTextOutlined, FormOutlined, HistoryOutlined,
  PauseCircleOutlined, PlayCircleOutlined, PlusOutlined,
  RedoOutlined, SettingOutlined, UploadOutlined
} from '@ant-design/icons'
import { ApiError, errText } from '../api/client.js'
import {
  BIZ_TEMPLATES, TASK_SOURCES, mapTaskSnapshot, confirmUpload, createLibrary, useKbTaskPolling,
  getAdditions, getDownloadUrl, getLibraryConfig, getReportDetail, getReports, getTask,
  initUpload, listLibraries, listLibraryActivities, listTasks, putObjectDirect,
  reviseFragment, retryTask, saveLibraryConfig
} from '../api/kb.js'
// UI-00 共享件（方案-阶段1交互优化 §3.3）——helpIcon/dim/errText 唯一定义点
// （UI-02 T11 页内同构副本删除；fieldLabel 仅 B1 一处消费，留 B1 不抽）。
import { helpIcon, dim } from '../components/helpIcon.jsx'
import PagedTable from '../components/PagedTable.jsx'

const fieldLabel = { fontSize: 12, color: '#8a94a3', marginBottom: 4 }

const POLL_MS = 800 // 轮询节奏由服务端真实进度决定（00 §5.2——页面节奏不入合同）

// 模板说明（建库弹窗——合同端点 15 四枚举说明文案，前端静态展示资产）
const TEMPLATE_HINTS = {
  completion: '四开关全开（含关系图谱——井与井的受效、措施关联就靠它），切段智能、索引期加法两项都做；带出默认配置，建后可调。',
  monthly: '语义/关键词/百科开、图谱关（月报按井月计量为主，省抽取费），切段智能、索引期加法两项都做；带出默认配置，建后可调。',
  dynamic: '语义/关键词/百科开、图谱关（动态分析以指标与曲线为主，图谱需要时再开），切段智能、索引期加法两项都做；带出默认配置，建后可调。',
  blank: '不带业务预设，按平台默认档建库（语义/关键词/百科开、图谱关）；带出默认配置，建后可调。'
}

// 四个索引开关（配置弹窗——说明与关闭后果文案照抄原型，合同常量展示资产）
const SWITCHES = [
  {
    key: 'semantic', name: '语义索引',
    note: '换种说法也能搜到——语义搜索的底子。',
    off: '关掉后：只剩关键词精确命中，问法一换就可能搜不到。'
  },
  {
    key: 'keyword', name: '关键词索引',
    note: '按字面精确搜：井号、编号一搜一个准。',
    off: '关掉后：换个说法的问句仍能靠语义索引命中，但精确编号（如 N-02）搜不到。'
  },
  {
    key: 'wiki', name: '百科页',
    note: '入库后顺手生成中文百科页——如 200 页英文完井报告 → 一页中文。',
    off: <span>关掉后：不生成中文百科页，英文原版只能整本翻；需要时去<a href="#/proto/B4">「报告百科」页</a>人工翻。</span>
  },
  {
    key: 'graph', name: '关系图谱',
    note: '逐段抽"谁—什么关系→谁"，费用较高；没有关系的库（如制度文件库）建议关。',
    off: '（图谱已关）本次入库不做关系抽取，省下费用；"哪些井受过 N-06 注水影响"这类问题将答不了。想开 → 点上方开关。'
  }
]

// 切段三法对照（前端静态演示资产——对照原文照抄原型，事实注源设定书 §A.1）
const RAW_TEXT = '3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW），2019-06-15 投产。3.2 完井段：详见射孔与防砂参数表。'

function chunkPanel(mode) {
  return (
    <div>
      <div className="code-block">{RAW_TEXT}</div>
      <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.9 }}>
        {mode === 'smart' && (<>
          <div><Tag color="blue">小段 1</Tag>3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤南区块 CEP-A 平台，井别采油（EW）。</div>
          <div><Tag color="blue">小段 2</Tag>……井别采油（EW），2019-06-15 投产。3.2 完井段：详见射孔与防砂参数表。</div>
        </>)}
        {mode === 'fixed' && (<>
          <div><Tag color="blue">小段 1</Tag>3. N-02 井完井情况。3.1 基本数据：N-02 井（渤中28-1-N2）位于渤</div>
          <div><Tag color="blue">小段 2</Tag>南区块 CEP-A 平台，井别采油（EW），2019-06-15 投产。3.2 完井段：详见……</div>
        </>)}
        {mode === 'mixed' && (<>
          <div><Tag color="blue">小段</Tag>（进索引，负责被找到）</div>
          <div style={{ marginLeft: 8 }}>① N-02 井（渤中28-1-N2）2019-06-15 投产。</div>
          <div style={{ marginLeft: 8 }}>② 井别采油（EW），位于 CEP-A 平台。</div>
          <div style={{ marginTop: 6 }}><Tag color="purple">大段</Tag>（只入库、不进索引，负责被读懂）</div>
          <div style={{ marginLeft: 8 }}>3. N-02 井完井情况。3.1 基本数据：……（整段全文）。</div>
        </>)}
      </div>
    </div>
  )
}

/** 错误包 → 内联展示行走共享 errText（client.js 导出，UI-02 T11——渲染物不变）。 */

const mark = on => (on ? '✓' : '✗')

const SW_LABELS = { semantic: '语义', keyword: '关键词', wiki: '百科页', graph: '关系图谱' }

/** 开关快照 → 四 Tag 列（最近一次入库所用——端点 11 两态分离展示）。 */
function switchTags(switches) {
  if (!switches) return <span style={dim}>—（尚未入库）</span>
  return (
    <Space size={4} wrap>
      {Object.keys(SW_LABELS).map(k => (
        <Tag key={k} color={switches[k] ? 'green' : 'default'} style={{ marginInlineEnd: 0 }}>
          {`${SW_LABELS[k]} ${mark(switches[k])}`}
        </Tag>
      ))}
    </Space>
  )
}

const TASK_STATE = {
  running: <Tag color="orange">处理中</Tag>,
  done: <Tag color="green">已完成</Tag>,
  failed: <Tag color="red">失败</Tag>,
  stuck: <Tag>疑似卡住</Tag>
}

/**
 * 任务轮询监听件（挂载即轮询端点 8——运行中任务的展开区进度靠它点亮；
 * 终态收场回调页面刷新台账/任务/库三面＋产物读取）。
 */
function TaskMonitor({ taskId, attempt, onProgress, onSettled }) {
  const { status, data, error } = useKbTaskPolling(taskId, {
    intervalMs: POLL_MS,
    onProgress: snap => onProgress(taskId, mapTaskSnapshot(snap))
  })
  const settledRef = useRef(false)
  useEffect(() => {
    if ((status === 'done' || status === 'failed') && !settledRef.current) {
      settledRef.current = true
      onSettled(taskId, status, data, error)
    }
  }, [status]) // eslint-disable-line react-hooks/exhaustive-deps
  // attempt 变化（重试/重跑）→ 重置收场标记重新监听
  useEffect(() => { settledRef.current = false }, [attempt])
  return null
}

/**
 * 落地 B1 报告库页（三页签：报告台账 / 入库任务 / 库管理——15 端点全接线）。
 * @returns {JSX.Element}
 */
export default function B1Landing() {
  const [tab, setTab] = useState('ledger')

  // ── 三个读面（端点 1/7/11——失败态内联常驻，失败态≠空态）──
  // libs/actRows 存归一化信封对象（kb.js listLibraries/listLibraryActivities 已带
  // total——UI-02 T2：页签/行内计数一律读信封 total，不读 items.length）
  const [libs, setLibs] = useState({ items: [], total: 0 })
  const [libsLoading, setLibsLoading] = useState(true)
  const [libsError, setLibsError] = useState(null)
  const [reports, setReports] = useState({ items: [], total: 0 })
  const [reportsLoading, setReportsLoading] = useState(true)
  const [reportsError, setReportsError] = useState(null)
  const [tasks, setTasks] = useState({ items: [], total: 0 })
  const [tasksLoading, setTasksLoading] = useState(true)
  const [tasksError, setTasksError] = useState(null)

  // 筛选（服务端筛参——00 §4.5）
  const [ledgerLib, setLedgerLib] = useState('all')
  const [ledgerKw, setLedgerKw] = useState('')
  const [sourceF, setSourceF] = useState('all')
  const [graphF, setGraphF] = useState('all')
  const [libKw, setLibKw] = useState('')

  const [expandedKeys, setExpandedKeys] = useState([]) // 受控展开行（新任务受理成功后主动展开）
  // 轮询快照（taskId → mapTaskSnapshot 形；attempt 计数驱动重试后重挂监听）
  const [snaps, setSnaps] = useState({})
  const [attempts, setAttempts] = useState({})
  const [additions, setAdditions] = useState({}) // taskId → 端点 9 产物

  // 上传流（两拍＋建议库弹窗）
  const fileRef = useRef(null)
  const [upFile, setUpFile] = useState(null)
  const [upOpen, setUpOpen] = useState(false)
  const [upReceipt, setUpReceipt] = useState(null) // 端点 5 受理回执（initUpload camel 形）
  const [upInitError, setUpInitError] = useState(null)
  const [upTarget, setUpTarget] = useState(null) // libId 或 '__new__'
  const [newLibName, setNewLibName] = useState('')
  const [newLibTpl, setNewLibTpl] = useState('blank')
  const [upBusy, setUpBusy] = useState(false)
  const [upError, setUpError] = useState(null)

  // 报告详情抽屉（台账行双击→端点 2）＋片段修正弹窗（端点 4）
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [fixFrag, setFixFrag] = useState(null) // {frag}
  const [fixText, setFixText] = useState('')
  const [fixBusy, setFixBusy] = useState(false)
  const [fixError, setFixError] = useState(null)

  // 库管理：新建库弹窗 / 库配置弹窗 / 活动流抽屉
  const [nlOpen, setNlOpen] = useState(false)
  const [nlName, setNlName] = useState('')
  const [nlTpl, setNlTpl] = useState('completion')
  const [nlBusy, setNlBusy] = useState(false)
  const [nlError, setNlError] = useState(null)
  const [cfgLib, setCfgLib] = useState(null) // lib 行（配置弹窗）
  const [cfgForm, setCfgForm] = useState(null) // 表单编辑值
  const [cfgSaved, setCfgSaved] = useState(null) // 保存回执 hint
  const [cfgBusy, setCfgBusy] = useState(false)
  const [cfgError, setCfgError] = useState(null)
  const [actLib, setActLib] = useState(null)
  const [actRows, setActRows] = useState({ items: [], total: 0 })
  const [actLoading, setActLoading] = useState(false)
  const [actError, setActError] = useState(null) // UI-02 T3：活动流失败态与空态分立

  const activeLibs = libs.items.filter(l => l.status === 'active')

  function refreshLists() {
    loadReports(); loadTasks(); loadLibs()
  }

  const loadLibs = () => {
    setLibsLoading(true)
    listLibraries({ graph: graphF, keyword: libKw })
      .then(d => { setLibs(d); setLibsError(null); setLibsLoading(false) }) // 信封整存（items＋total——T2）
      .catch(err => { setLibsError(err); setLibsLoading(false) })
  }
  const loadReports = () => {
    setReportsLoading(true)
    getReports({ lib: ledgerLib, keyword: ledgerKw })
      .then(d => { setReports(d); setReportsError(null); setReportsLoading(false) })
      .catch(err => { setReportsError(err); setReportsLoading(false) })
  }
  const loadTasks = () => {
    setTasksLoading(true)
    listTasks({ source: sourceF })
      .then(d => { setTasks(d); setTasksError(null); setTasksLoading(false) })
      .catch(err => { setTasksError(err); setTasksLoading(false) })
  }

  useEffect(() => { loadLibs() }, [graphF, libKw]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { loadReports() }, [ledgerLib, ledgerKw]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { loadTasks() }, [sourceF]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── 轮询收场（TaskMonitor 回调）：刷新三面＋done 读产物（端点 9） ──
  function onTaskProgress(taskId, snap) {
    setSnaps(s => ({ ...s, [taskId]: snap }))
  }
  function onTaskSettled(taskId, status, data, error) {
    if (data) setSnaps(s => ({ ...s, [taskId]: mapTaskSnapshot(data) }))
    refreshLists()
    if (status === 'done') {
      getAdditions(taskId)
        .then(d => setAdditions(a => ({ ...a, [taskId]: d })))
        .catch(() => {}) // 产物读取失败不打扰收场（展开区空态兜底）
    }
    if (status === 'failed' && error) {
      setSnaps(s => ({ ...s, [taskId]: { ...(s[taskId] || {}), pollError: errText(error) } }))
    }
  }

  // ── 重试/重跑（端点 10：failed/stuck/done 可重试；来源转「重跑定型」） ──
  async function doRetry(taskId) {
    try {
      const snap = await retryTask(taskId)
      setSnaps(s => ({ ...s, [taskId]: snap }))
      setAttempts(a => ({ ...a, [taskId]: (a[taskId] || 0) + 1 })) // 重挂监听（新 run 重轮询）
      loadTasks()
      message.info('已重新开跑——按该库当前配置重新定型，进度见展开区。')
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        message.warning('任务处理中，不能重复重试（网关 409）。')
      }
      // 其余错误 client 已统一 message
    }
  }

  // ── 上传流：选文件 → 受理（路由建议）→ 建议库弹窗 → 直传 → confirm ──
  function pickFile() {
    setUpInitError(null)
    fileRef.current?.click()
  }
  async function onFileChosen(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setUpFile(file)
    setUpError(null)
    setUpBusy(true)
    try {
      const receipt = await initUpload({ filename: file.name, size: file.size }) // 不带 lib_id＝走路由建议
      setUpReceipt(receipt)
      setUpTarget(receipt.routing?.mode === 'existing' && receipt.routing.libId
        ? receipt.routing.libId
        : (receipt.routing?.mode === 'new' ? '__new__' : null))
      setNewLibName(receipt.routing?.topic || file.name.replace(/\.[A-Za-z0-9]+$/, ''))
      setNewLibTpl(receipt.routing?.template || 'blank')
      setUpOpen(true)
    } catch (err) {
      setUpInitError(err) // client 已 message；受理失败内联常驻（重新选文件重试）
    } finally {
      setUpBusy(false)
    }
  }
  async function doConfirmUpload() {
    if (!upReceipt || !upFile) return
    if (!upTarget) { message.warning('请先选择目标库（或确认建议）。'); return }
    setUpBusy(true)
    setUpError(null)
    try {
      let libId = upTarget
      if (upTarget === '__new__') {
        const name = newLibName.trim()
        if (!name) { message.warning('请输入新库名。'); setUpBusy(false); return }
        const created = await createLibrary({ libName: name, bizTemplate: newLibTpl })
        libId = created.libId
        loadLibs()
      }
      await putObjectDirect(upReceipt.putUrl, upFile) // 直传第二拍前置：字节直达对象存储（平台不经手）
      const done = await confirmUpload(upReceipt.uploadId, { libId }) // confirm 定型（路由确认通道）
      setUpOpen(false)
      setUpReceipt(null)
      setUpFile(null)
      refreshLists()
      setTab('tasks')
      setExpandedKeys(k => [done.taskId, ...k]) // 新任务行主动展开——五步进度立即可见
      message.success(`已受理入库：《${done.doc.replace(/^《|》$/g, '')}》五步管线开跑——进度见「入库任务」展开区。`)
    } catch (err) {
      setUpError(err) // 直传/confirm 失败内联常驻（409 落桶核实失败→重新走受理）
    } finally {
      setUpBusy(false)
    }
  }

  // ── 报告详情（端点 2）＋下载直链（端点 3）＋片段修正（端点 4） ──
  async function openDetail(report) {
    setDetailLoading(true)
    try {
      const d = await getReportDetail(report.id)
      setDetail(d)
    } catch {
      // 其余错误 client 已统一 message（UI-02 T8：页面层不再叠弹第二次）
    } finally {
      setDetailLoading(false)
    }
  }
  async function doDownload(report) {
    try {
      const d = await getDownloadUrl(report.id)
      message.success(`已生成下载直链——链接${d.ttl}有效（至 ${d.expiresAt}）。`)
      window.open(d.downloadUrl, '_blank', 'noopener')
    } catch {
      // 其余错误 client 已统一 message（UI-02 T8）
    }
  }
  function openFix(frag) {
    setFixError(null)
    setFixText(frag.text)
    setFixFrag(frag)
  }
  async function doRevise() {
    if (!fixFrag || !detail) return
    setFixBusy(true)
    setFixError(null)
    try {
      const r = await reviseFragment(detail.id, fixFrag.id, { baseVersion: fixFrag.version, text: fixText })
      message.success(r.rebuild.hint || '已保存——索引重建已折算入库任务。')
      setFixFrag(null)
      loadTasks() // 「片段修正」任务进任务页签
      const d = await getReportDetail(detail.id) // 版本/百科回显（重铸后 wiki 版本随刷新可见）
      setDetail(d)
      loadReports()
    } catch (err) {
      setFixError(err) // 409 乐观锁冲突 → 内联兜底提示（别人已改过这段）
    } finally {
      setFixBusy(false)
    }
  }

  // ── 库管理：新建库（端点 15）/ 停用启用（端点 13 status）/ 配置（端点 12/13） ──
  async function doCreateLib() {
    setNlBusy(true)
    setNlError(null)
    try {
      const r = await createLibrary({ libName: nlName, bizTemplate: nlTpl })
      message.success('已建库——默认配置已生成，可在「库配置」中调整。')
      setNlOpen(false)
      setNlName('')
      setNlTpl('completion')
      loadLibs()
      if (actLib === r.libId) loadActivities(r.libId)
    } catch (err) {
      setNlError(err) // 409 重名 → 内联提示「库名与现有库重复」
    } finally {
      setNlBusy(false)
    }
  }
  async function toggleLib(lib) {
    const to = lib.status === 'active' ? 'disabled' : 'active'
    try {
      const cfg = await getLibraryConfig(lib.id) // 停用/启用走端点 13——配置全量整存整取＋status
      const r = await saveLibraryConfig(lib.id, {
        switches: cfg.switches, mode: cfg.mode,
        addSummary: cfg.addSummary, addQuestions: cfg.addQuestions, status: to
      })
      message.success(r.hint || (to === 'disabled'
        ? `已停用「${lib.name}」——不再接收新入库，已有内容保留可查。`
        : `已启用「${lib.name}」——恢复接收新入库。`))
      loadLibs()
      loadActivities(lib.id)
    } catch {
      // 其余错误 client 已统一 message（UI-02 T8：停用/启用失败单弹足够）
    }
  }
  async function openCfg(lib) {
    setCfgSaved(null)
    setCfgError(null)
    setCfgForm(null)
    setCfgLib(lib)
    try {
      const cfg = await getLibraryConfig(lib.id)
      setCfgForm({ switches: cfg.switches, mode: cfg.mode, addSummary: cfg.addSummary, addQuestions: cfg.addQuestions })
    } catch (err) {
      setCfgError(err)
    }
  }
  async function doSaveCfg() {
    if (!cfgLib || !cfgForm) return
    setCfgBusy(true)
    setCfgError(null)
    try {
      const r = await saveLibraryConfig(cfgLib.id, { ...cfgForm })
      setCfgSaved(r)
      loadLibs()
      loadActivities(cfgLib.id)
    } catch (err) {
      setCfgError(err)
    } finally {
      setCfgBusy(false)
    }
  }
  // 活动流（端点 14）——UI-02 T3：失败态分立（actError 置错＋抽屉内联 Alert 常驻，
  // 对齐同页三读面惯例；不再静默吞错伪装空态）；T2：信封整存计数读 total。
  function loadActivities(libId) {
    setActLoading(true)
    setActError(null)
    listLibraryActivities(libId)
      .then(d => { setActRows(d); setActError(null); setActLoading(false) })
      .catch(err => { setActError(err); setActLoading(false) })
  }
  function openActivities(lib) {
    setActLib(lib)
    setActRows({ items: [], total: 0 })
    loadActivities(lib.id)
  }

  // ── 列定义 ──
  const ledgerColumns = [
    {
      title: (<span>报告{helpIcon(<>处理中的报告进台账：行内标「入库中」，入库完成后转为已入库、标自动消失。</>)}</span>),
      dataIndex: 'doc',
      render: (v, r) => (
        <Space size={6}>
          <b>{v}</b>
          {r.status === '入库中' && <Tag color="orange" style={{ marginInlineEnd: 0 }}>入库中</Tag>}
        </Space>
      )
    },
    { title: '所属库', dataIndex: 'lib', width: 116 },
    {
      title: (<span>出处片段{helpIcon(<>切片管理中该报告的片段数——小段负责被找到，大段负责被读懂。未建检索切片的报告如实标"—"。</>)}</span>),
      dataIndex: 'refs', width: 92,
      render: v => (v ? `${v} 段` : <span style={dim}>—</span>)
    },
    {
      title: (<span>中文百科{helpIcon(<>入库时勾选"百科页"开关的报告，处理完自动生成中文结构化百科页（当前版本号随重建递增）。未生成的标"—"。</>)}</span>),
      dataIndex: 'wiki', width: 92,
      render: v => (v ? v : <span style={dim}>—</span>)
    },
    {
      title: '操作', width: 128, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="下载原件——报告原件直链下载，链接小时级有效">
            <Button size="small" icon={<DownloadOutlined />}
              onClick={e => { e.stopPropagation(); doDownload(r) }} />
          </Tooltip>
          {r.refs != null && (
            <Tooltip title="看切片——去切片管理页按报告浏览切出的片段">
              <Button size="small" icon={<FileTextOutlined />}
                onClick={e => { e.stopPropagation(); location.hash = '/B2' }} />
            </Tooltip>
          )}
          {r.wiki != null && (
            <Tooltip title="看百科——去报告百科页看中文结构化页">
              <Button size="small" icon={<BookOutlined />}
                onClick={e => { e.stopPropagation(); location.hash = '/proto/B4' }} />
            </Tooltip>
          )}
        </Space>
      )
    }
  ]

  const taskColumns = [
    {
      title: '报告', dataIndex: 'doc',
      render: (v, t) => <b>{v}{t.state === 'stuck' && <span style={{ ...dim, fontWeight: 'normal', marginLeft: 8 }}>已 20 多分钟没有进展</span>}</b>
    },
    { title: '目标库', dataIndex: 'libName', width: 116 },
    {
      title: (<span>来源{helpIcon(<>任务来源：上传入库＝直传上传；片段修正＝片段修正保存后触发的索引重建；重跑定型＝对既有任务重试/重跑。</>)}</span>),
      dataIndex: 'source', width: 100
    },
    { title: '状态', width: 96, render: (_, t) => TASK_STATE[t.state] || t.state },
    {
      title: '操作', width: 64, align: 'center',
      render: (_, t) => (
        // 禁用控件外包一层 <span> 再挂 Tooltip（UI-02 T4——方案 §3.3 定死，先例 B5.jsx:461-465）：
        // 任务运行中 Button disabled 悬停事件不达 button，span 保 Tooltip 可见
        <Tooltip title="重试/重跑入库管线">
          <span>
            <Button size="small" icon={<RedoOutlined />} disabled={t.state === 'running'}
              onClick={e => { e.stopPropagation(); doRetry(t.id) }} />
          </span>
        </Tooltip>
      )
    }
  ]

  const libColumns = [
    {
      title: '库', dataIndex: 'name', width: 140,
      render: (v, l) => (
        <Space size={6}>
          <b>{v}</b>
          {l.status === 'disabled' && <Tag color="default" style={{ marginInlineEnd: 0 }}>已停用</Tag>}
        </Space>
      )
    },
    { title: '最近入库', dataIndex: 'lastIngestion', render: v => (v?.doc || <span style={dim}>—</span>) },
    {
      title: (<span>索引开关{helpIcon(<>该库最近一次入库所用的四个索引开关：语义 / 关键词 / 百科页 / 关系图谱。下次入库用哪几个，在行尾"配置"里按库调整，保存后下次入库生效。</>)}</span>),
      dataIndex: 'lastIngestion', width: 320,
      render: v => switchTags(v?.switches)
    },
    {
      title: '操作', width: 128, align: 'center',
      render: (_, l) => (
        <Space size={4}>
          <Tooltip title="库配置（索引开关 / 切段方式 / 索引期加法）">
            <Button size="small" icon={<SettingOutlined />}
              onClick={e => { e.stopPropagation(); openCfg(l) }} />
          </Tooltip>
          <Tooltip title={l.status === 'disabled'
            ? '启用——恢复接收新入库'
            : '停用——该库不再接收新入库，已有内容保留可查'}>
            <Button size="small" icon={l.status === 'disabled' ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
              onClick={e => { e.stopPropagation(); toggleLib(l) }} />
          </Tooltip>
          <Tooltip title="活动——这个库的操作留痕">
            <Button size="small" icon={<HistoryOutlined />}
              onClick={e => { e.stopPropagation(); openActivities(l) }} />
          </Tooltip>
        </Space>
      )
    }
  ]

  // ── 任务展开区：Steps（节点/note 服务端组装）＋失败/卡住人话＋产物两卡 ──
  function expandedTask(t) {
    const snap = snaps[t.id]
    const nodes = snap?.nodes
    const add = additions[t.id]
    const retryBtn = (
      <Button size="small" icon={<RedoOutlined />} style={{ marginLeft: 8 }}
        disabled={t.state === 'running'} onClick={e => { e.stopPropagation(); doRetry(t.id) }}>重试</Button>
    )
    return (
      <div style={{ padding: '4px 2px' }}>
        {t.state === 'failed' && (
          <Alert style={{ marginBottom: 12 }} type="error" showIcon
            message={<span>停在「{snap?.stopAt || t.stopAt || '—'}」阶段：{snap?.reason || t.reason || '—'}——可重试；仍失败请报修。{retryBtn}</span>} />
        )}
        {t.state === 'stuck' && (
          <Alert style={{ marginBottom: 12 }} type="warning" showIcon
            message={<span>已 20 多分钟没有进展：已没有任务在推进——可停止后重试。{retryBtn}</span>} />
        )}
        {snap?.pollError && (
          <Alert style={{ marginBottom: 12 }} type="error" showIcon
            message="任务进度轮询失败" description={snap.pollError} />
        )}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>处理进度</span>
            {helpIcon(<>五步依次点亮：解析 → 切段 → 向量化 → 建索引 → 索引期加法。重跑按该库当前配置重新定型；关掉的索引支路直接跳过、不跑不花钱。</>)}
            <Button size="small" icon={<RedoOutlined />} style={{ marginLeft: 'auto' }}
              disabled={t.state === 'running'}
              onClick={e => { e.stopPropagation(); doRetry(t.id) }}>重跑入库管线</Button>
          </div>
          {nodes ? (
            <>
              <Steps size="small" current={snap.currentStep}
                status={t.state === 'done' ? 'finish' : t.state === 'failed' ? 'error' : 'process'}
                items={nodes.map(n => ({
                  title: n.label,
                  status: n.state,
                  description: n.note ? <span style={{ fontSize: 12, color: '#8a94a3' }}>{n.note}</span> : undefined
                }))} />
              <Table
                style={{ marginTop: 14 }} size="small" pagination={false} rowKey="key"
                columns={[
                  { title: '步骤', dataIndex: 'label', width: 180 },
                  { title: '说明', dataIndex: 'note', render: v => v || <span style={dim}>—</span> }
                ]}
                dataSource={nodes.filter(n => n.note)}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="管线启动后，每亮一步这里多一行说明。" /> }}
              />
            </>
          ) : (
            <div style={dim}>{t.state === 'running' ? '管线启动中……' : '展开查看五步进度。'}</div>
          )}
        </div>
        {t.state === 'done' && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 600, fontSize: 13 }}>索引期加法产物</span>
              {helpIcon(<>处理完自动多做两件事：全文档摘要 ×1；每 20 段生成一批"可能被问的问题"。是否生成在该库配置里勾选，保存后下次入库生效。</>)}
            </div>
            {add ? (<>
              {add.summary ? (
                <Card size="small" style={{ marginBottom: 8 }}
                  title={<span><Tag color="green">摘要块</Tag>{add.summary.title || '全文档摘要（自动生成）'}</span>}>
                  <span style={{ fontSize: 13 }}>{add.summary.text}</span>
                </Card>
              ) : (
                <div style={{ ...dim, marginBottom: 8 }}>本次入库未开启「自动生成全文档摘要」（按入库快照跳过）。</div>
              )}
              {add.questions ? (
                <Card size="small"
                  title={<span><Tag color="orange">问题块</Tag>{add.questions.title || '这份报告可能被问的问题（自动生成）'}</span>}>
                  <ol style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 2 }}>
                    {(add.questions.items || []).map((q, i) => <li key={i}>{q}</li>)}
                  </ol>
                </Card>
              ) : (
                <div style={dim}>本次入库未开启「可能被问的问题」生成（按入库快照跳过）。</div>
              )}
            </>) : (
              <div style={dim}>产物读取中……</div>
            )}
          </div>
        )}
      </div>
    )
  }

  const helpTop = helpIcon(
    <>在库报告的总账与入库管理：上传后平台自动切段、建索引，处理到哪步亮哪步；每个库可单独配四个索引开关和切段方式；处理完自动产出全文档摘要和"可能被问的 10 个问题"。</>
  )

  const fixVersionTable = fixFrag ? (
    <Table style={{ marginTop: 8 }} size="small" pagination={false} rowKey="v"
      columns={[
        { title: '版本', dataIndex: 'v', width: 110, render: (v, r) => (r.v === fixFrag.version ? `v${v}（当前）` : `v${v}`) },
        { title: '来源', dataIndex: 'note', width: 90 },
        { title: '内容', dataIndex: 'text', render: t => <span style={{ fontSize: 12 }}>{t}</span> }
      ]}
      dataSource={fixFrag.versions || []} />
  ) : null

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Card
        // UI-12：root→Card→body→Tabs→pane flex 链——Card 高度有界（flex 1 1 auto＋minHeight:0），
        // body flex 列 overflow:hidden，三页签 PagedTable fill 内滚、表头/分页条恒在、页面级滚动消灭
        // UI-13：页标题上移壳层页头——helpTop 迁卡头 extra（页面帮助悬停不丢）
        style={{ flex: '1 1 auto', minHeight: 0, display: 'flex', flexDirection: 'column' }}
        styles={{ body: { flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' } }}
        extra={helpTop}
        title={
          <Tabs
            className="fill-tabs" // UI-12：页签 nav 收紧＋链式高度（本 Tabs 仅作卡头页签，content 规则不参与）
            activeKey={tab} size="small" onChange={setTab}
            items={[
              { key: 'ledger', label: (
                // UI-02 T6：台账卡底步骤类指引收进页签 ?（同内容；§3.1-3 操作步骤类）
                <span>报告台账（{reports.total}）{helpIcon(<>新报告入库 → 切「入库任务」上传；索引与百科等产物的生成规则按库配置，见「库管理」。</>)}</span>
              ) },
              { key: 'tasks', label: `入库任务（${tasks.total}）` },
              { key: 'libs', label: `库管理（${libs.total}）` } // UI-02 T2：读信封 total
            ]}
          />
        }
      >
        {tab === 'ledger' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Select size="small" style={{ width: 150 }} value={ledgerLib}
                  onChange={v => setLedgerLib(v)}
                  options={[{ value: 'all', label: '所属库：全部' },
                    ...libs.items.map(l => ({ value: l.name, label: l.name }))]} />
                <Input size="small" allowClear style={{ width: 240 }} value={ledgerKw}
                  onChange={e => setLedgerKw(e.target.value)} placeholder="搜报告名 / 所属库…" />
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>双击行看详情</span>
            </div>
            {reportsError && (
              <Alert style={{ marginBottom: 12 }} type="error" showIcon
                message="报告台账拉取失败——下表不是最新数据" description={errText(reportsError)} />
            )}
            {/* UI-02 T1：接 PagedTable client 模式（pageSize 20、统计恒显）；resetKey 绑筛状态
                （方案 §2.2 总表）——筛选缩短数据后自动回页 1，不停在超界页出空表；
                UI-12：fill 表内滚（台账长表页签内滚、页面不滚） */}
            <PagedTable
              fill
              size="small" loading={reportsLoading} columns={ledgerColumns}
              dataSource={reports.items} rowKey="id"
              onRow={r => ({ onDoubleClick: () => openDetail(r), style: { cursor: 'pointer' } })}
              emptyText="还没有报告入库：切「入库任务」页签上传。"
              error={reportsError} errorEmptyText="台账拉取失败"
              resetKey={`${ledgerLib}|${ledgerKw}`}
            />
          </>
        )}

        {tab === 'tasks' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Button type="primary" size="small" icon={<UploadOutlined />}
                  loading={upBusy} onClick={pickFile}>上传报告（直传）</Button>
                {helpIcon(<>报告从客户端直接传进文件库，不绕平台服务；解析、切段、建索引由平台在入库时自动完成。上传受理后按 LLM 路由建议确认目标库（可改选/直指定），确认后开跑。</>)}
                <input ref={fileRef} type="file" style={{ display: 'none' }} onChange={onFileChosen} />
                <Select size="small" style={{ width: 130 }} value={sourceF}
                  onChange={v => setSourceF(v)}
                  options={[{ value: 'all', label: '来源：全部' }, ...TASK_SOURCES.map(v => ({ value: v, label: v }))]} />
              </Space>
              {/* UI-02 T10：卡头「任务 N 条」计数行已删——页签「入库任务（N）」＋分页条统计防第三处冗余 */}
            </div>
            {tasksError && (
              <Alert style={{ marginBottom: 12 }} type="error" showIcon
                message="任务列表拉取失败——下表不是最新数据" description={errText(tasksError)} />
            )}
            {upInitError && (
              <Alert style={{ marginBottom: 12 }} type="error" showIcon
                message="上传受理失败——请重新选择文件再试" description={errText(upInitError)} />
            )}
            {/* UI-02 T1：接 PagedTable——expandable 整包透传（新任务受理后主动展开逻辑不动），
                resetKey 绑来源筛；UI-12：fill 表内滚；
                UI-14 巡检违例 (b) 修复（先登记后改）：tasksError 失败态经 error prop 切
                失败空态——不再混入「还没有入库任务」业务引导文案（对齐同页 ledger/libs/
                activity 三表 error/errorEmptyText 惯例；上方内联 Alert 另挂，两件并存） */}
            <PagedTable
              fill
              size="small" loading={tasksLoading} columns={taskColumns}
              dataSource={tasks.items} rowKey="id"
              emptyText="还没有入库任务：点上方「上传报告（直传）」发起一次入库。"
              error={tasksError} errorEmptyText="任务列表拉取失败"
              resetKey={sourceF}
              expandable={{
                expandRowByClick: true,
                expandedRowKeys: expandedKeys,
                onExpandedRowsChange: keys => setExpandedKeys(keys),
                expandedRowRender: expandedTask,
                rowExpandable: () => true,
                onExpand: (expanded, t) => {
                  // 非运行中任务展开时拉一次轮询形状（端点 8）——失败/卡住/已完成
                  // 的五步节点与说明由服务端组装，列表（端点 7）不带节点
                  if (expanded && !snaps[t.id]) {
                    getTask(t.id).then(s => setSnaps(x => ({ ...x, [t.id]: s }))).catch(() => {})
                  }
                }
              }}
            />
            {/* 运行中任务轮询监听（挂载即轮询端点 8；终态收场刷新三面） */}
            {tasks.items.filter(t => t.state === 'running' || t.state === 'stuck').map(t => (
              <TaskMonitor key={`${t.id}:${attempts[t.id] || 0}`} taskId={t.id}
                attempt={attempts[t.id] || 0}
                onProgress={onTaskProgress} onSettled={onTaskSettled} />
            ))}
          </>
        )}

        {tab === 'libs' && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <Space wrap size={8}>
                <Button size="small" icon={<PlusOutlined />}
                  onClick={() => { setNlName(''); setNlTpl('completion'); setNlError(null); setNlOpen(true) }}>新建库</Button>
                {helpIcon(<>按业务类型模板建库：模板带出一份默认配置（四个索引开关、切段方式、索引期加法），建后可在行尾"配置"里按库调整；建库与停用/启用都会记入库活动流。</>)}
                <Select size="small" style={{ width: 136 }} value={graphF}
                  onChange={v => setGraphF(v)}
                  options={[{ value: 'all', label: '图谱开关：全部' }, { value: 'on', label: '图谱已开' }, { value: 'off', label: '图谱已关' }]} />
                <Input size="small" allowClear style={{ width: 220 }} value={libKw}
                  onChange={e => setLibKw(e.target.value)} placeholder="搜库名 / 最近入库…" />
              </Space>
              <span style={{ color: '#8a94a3', fontSize: 12 }}>{`筛选结果 ${libs.total} 条`}</span> {/* UI-02 T2：读信封 total */}
            </div>
            {libsError && (
              <Alert style={{ marginBottom: 12 }} type="error" showIcon
                message="库列表拉取失败——下表不是最新数据" description={errText(libsError)} />
            )}
            {/* UI-02 T1：接 PagedTable，resetKey 绑图谱筛＋库名关键字（方案 §2.2 总表）；UI-12：fill 表内滚 */}
            <PagedTable
              fill
              size="small" loading={libsLoading} columns={libColumns}
              dataSource={libs.items} rowKey="id"
              emptyText="还没有库：点「新建库」创建。"
              error={libsError} errorEmptyText="库列表拉取失败"
              resetKey={`${graphF}|${libKw}`}
            />
          </>
        )}
      </Card>

      {/* 上传建议库弹窗（受理回执→LLM 建议卡可确认/改选/直指定→直传→confirm） */}
      <Modal title="上传报告（直传）" open={upOpen} onCancel={() => { setUpOpen(false); setUpReceipt(null) }}
        footer={null} width={560} maskClosable={false}>
        <div style={{ marginBottom: 10 }}>
          <span style={{ fontSize: 13 }}>已选择：<b>{upFile?.name}</b></span>
          {upFile && <span style={dim}>（{Math.max(1, Math.round(upFile.size / 1024))} KB）</span>}
        </div>
        {upReceipt?.dupWarning && (
          <Alert style={{ marginBottom: 10 }} type="warning" showIcon message={upReceipt.dupWarning} />
        )}
        {upReceipt?.routing && (
          <Card size="small" style={{ marginBottom: 10 }} title="入库路由建议（LLM 只建议 · 由你确认）">
            {upReceipt.routing.mode === 'existing' && (
              <div style={{ fontSize: 13 }}>
                建议归入现有库「<b>{upReceipt.routing.libName}</b>」
                {upReceipt.routing.reason && <div style={{ ...dim, marginTop: 4 }}>理由：{upReceipt.routing.reason}</div>}
                {upReceipt.routing.confidence != null && <div style={dim}>置信度：{Math.round(upReceipt.routing.confidence * 100)}%</div>}
              </div>
            )}
            {upReceipt.routing.mode === 'new' && (
              <div style={{ fontSize: 13 }}>
                建议新建库——模板推荐：「{BIZ_TEMPLATES.find(t => t.value === upReceipt.routing.template)?.label || upReceipt.routing.template}」
                {upReceipt.routing.reason && <div style={{ ...dim, marginTop: 4 }}>理由：{upReceipt.routing.reason}</div>}
                {upReceipt.routing.confidence != null && <div style={dim}>置信度：{Math.round(upReceipt.routing.confidence * 100)}%</div>}
              </div>
            )}
            {!upReceipt.routing.mode && (
              <div style={{ fontSize: 13 }}>
                话题分析不可用——请手动指定目标库。
                {upReceipt.routing.reason && <div style={{ ...dim, marginTop: 4 }}>{upReceipt.routing.reason}</div>}
              </div>
            )}
          </Card>
        )}
        <div style={fieldLabel}>目标库（可改选 / 直指定；停用库不接收新入库）</div>
        <Select style={{ width: '100%' }} placeholder="选择目标库" value={upTarget}
          onChange={v => setUpTarget(v)}
          options={[
            ...activeLibs.map(l => ({ value: l.id, label: l.name })),
            ...(upReceipt?.routing?.mode === 'new'
              ? [{ value: '__new__', label: '新建库（按建议模板）' }]
              : [])
          ]} />
        {upTarget === '__new__' && (
          <>
            <div style={{ ...fieldLabel, marginTop: 10 }}>新库名</div>
            <Input value={newLibName} onChange={e => setNewLibName(e.target.value)} maxLength={40} placeholder="如：措施效果库" />
            <div style={{ ...fieldLabel, marginTop: 10 }}>业务类型模板</div>
            <Select style={{ width: '100%' }} value={newLibTpl} onChange={v => setNewLibTpl(v)}
              options={BIZ_TEMPLATES.map(t => ({ value: t.value, label: t.label }))} />
            <Alert style={{ marginTop: 8 }} type="info" showIcon message={TEMPLATE_HINTS[newLibTpl]} />
          </>
        )}
        {upError && (
          <Alert style={{ marginTop: 10 }} type="error" showIcon
            message="入库确认失败——对象未落桶或凭证已用时请重新上传" description={errText(upError)} />
        )}
        {/* UI-02 T7：弹窗底部机制说明已删——与「上传报告（直传）」按钮旁 helpIcon 同义重复 */}
        <Button type="primary" style={{ marginTop: 12 }} loading={upBusy} onClick={doConfirmUpload}>确认入库</Button>
      </Modal>

      {/* 报告详情抽屉（台账行双击——端点 2：片段预览含版本）；UI-02 T5：开窗加载期渲染 Spin，不再空白 */}
      <Drawer title={detail ? '报告详情' : '报告详情'} placement="right" width={560}
        open={!!detail || detailLoading} onClose={() => setDetail(null)}>
        {detailLoading ? <Spin /> : (
          detail && (
          <>
            <Descriptions size="small" column={1} colon labelStyle={{ width: 110, color: '#8a94a3' }}>
              <Descriptions.Item label="报告名">{detail.doc}</Descriptions.Item>
              <Descriptions.Item label="所属库">{detail.lib}</Descriptions.Item>
              <Descriptions.Item label="井号 / 月份">{detail.subject || '—'}</Descriptions.Item>
              <Descriptions.Item label="出处片段">{detail.refs != null ? `${detail.refs} 段` : '—'}</Descriptions.Item>
              <Descriptions.Item label="中文百科">{detail.wiki || '—'}</Descriptions.Item>
              <Descriptions.Item label="入库状态">{detail.status}</Descriptions.Item>
            </Descriptions>
            <div style={{ marginTop: 16, fontWeight: 600, fontSize: 13 }}>
              片段预览
              {helpIcon(<>原文片段（与「切片管理」页同源）；发现解析错字可点"修正"——保存后重建索引，别人已改过时会提示刷新后再改。</>)}
            </div>
            {detail.fragments.map(f => {
              const revised = f.versions.length > 1
              return (
                <div key={f.id} style={{ border: '1px solid rgba(128,128,128,0.25)', borderRadius: 6, padding: '8px 12px', marginTop: 8 }}>
                  <div style={{ ...dim, marginBottom: 4 }}>
                    {f.path}{f.type ? ` · ${f.type}` : ''}{revised ? ` · 已修正（v${f.version}）` : ''}
                  </div>
                  <div style={{ fontSize: 13 }}>{f.text}</div>
                  <div style={{ marginTop: 6 }}>
                    <Button size="small" icon={<FormOutlined />} onClick={() => openFix(f)}>修正</Button>
                  </div>
                </div>
              )
            })}
            {!detail.fragments.length && (
              <div style={{ ...dim, marginTop: 8 }}>该报告的片段暂未收录，入库处理后可预览。</div>
            )}
          </>
          )
        )}
      </Drawer>

      {/* 片段人工修正（端点 4：乐观锁——409 冲突内联兜底提示） */}
      <Modal title={fixFrag ? '修正片段' : ''} open={!!fixFrag} onCancel={() => setFixFrag(null)} footer={null} width={560}>
        {fixFrag && (
          <>
            <div style={dim}>{fixFrag.path}</div>
            <Input.TextArea style={{ marginTop: 8 }} rows={4} value={fixText} onChange={e => setFixText(e.target.value)} />
            <div style={{ ...dim, marginTop: 8 }}>保存后重建检索索引；若别人已改过这段，保存时会提示你刷新后再改。</div>
            {fixError && (
              <Alert style={{ marginTop: 8 }} type={fixError instanceof ApiError && fixError.status === 409 ? 'warning' : 'error'}
                showIcon
                message={fixError instanceof ApiError && fixError.status === 409
                  ? '这段已被别人修改过（版本冲突）——请关闭后重新打开详情，刷新后再改。'
                  : '修正保存失败'}
                description={errText(fixError)} />
            )}
            <Button type="primary" style={{ marginTop: 10 }} loading={fixBusy} onClick={doRevise}>保存修正</Button>
            <div style={{ marginTop: 16, fontWeight: 600, fontSize: 13 }}>版本记录（第一期只回看，不回写）</div>
            {fixVersionTable}
          </>
        )}
      </Modal>

      {/* 新建库弹窗（端点 15：库名＋业务模板四枚举带默认配置） */}
      <Modal title="新建库" open={nlOpen} onCancel={() => setNlOpen(false)} footer={null} width={520}>
        <div style={fieldLabel}>库名</div>
        <Input style={{ marginTop: 2 }} placeholder="如：措施效果库" value={nlName}
          onChange={e => setNlName(e.target.value)} maxLength={40} />
        <div style={{ ...fieldLabel, marginTop: 14 }}>
          业务类型模板
          {helpIcon(<>模板决定初始配置档：四个索引开关的预设、切段方式、索引期加法——只是起点，建后在行尾"配置"里按库调整。</>)}
        </div>
        <Select style={{ width: '100%' }} value={nlTpl} onChange={setNlTpl}
          options={BIZ_TEMPLATES.map(t => ({ value: t.value, label: t.label }))} />
        <Alert style={{ marginTop: 10 }} type="info" showIcon message={TEMPLATE_HINTS[nlTpl]} />
        {nlError && (
          <Alert style={{ marginTop: 10 }}
            type={nlError instanceof ApiError && nlError.status === 409 ? 'warning' : 'error'} showIcon
            message={nlError instanceof ApiError && nlError.status === 409
              ? '库名与现有库重复，请换一个名称。'
              : '建库失败'}
            description={errText(nlError)} />
        )}
        {/* UI-02 T7：弹窗底部停用/启用指引已删——与库列表行「停用/启用」Tooltip 重复 */}
        <Button type="primary" style={{ marginTop: 14 }} loading={nlBusy} onClick={doCreateLib}>确认建库</Button>
      </Modal>

      {/* 库活动流抽屉（端点 14——F62 只读）；UI-02 T3：失败态内联 Alert 常驻（对齐同页
          三读面惯例），表格 error 切错误空态——失败态与空态分叉渲染 */}
      <Drawer title={actLib ? `活动 · ${actLib.name}` : ''} placement="right" width={560}
        open={!!actLib} onClose={() => setActLib(null)}>
        {actError && (
          <Alert style={{ marginBottom: 12 }} type="error" showIcon
            message="活动记录拉取失败——下表不是最新数据" description={errText(actError)} />
        )}
        {/* UI-02 T1/T9：接 PagedTable；rowKey 复合（活动行仅分钟精度四字段无 id，
            同分钟两行 time 单键碰撞——合同 B1:342-348 行形状）；resetKey 绑库切换 */}
        <PagedTable
          size="small" loading={actLoading}
          rowKey={r => `${r.time}|${r.action}|${r.target}`}
          columns={[
            { title: '时间', dataIndex: 'time', width: 140 },
            { title: '操作人', dataIndex: 'who', width: 130 },
            { title: '动作', dataIndex: 'action', width: 100 },
            { title: '对象', dataIndex: 'target' }
          ]}
          dataSource={actRows.items}
          emptyText="这个库还没有活动记录"
          error={actError} errorEmptyText="活动记录拉取失败"
          resetKey={actLib?.id ?? ''}
        />
        <div style={{ ...dim, marginTop: 10 }}>只记录，不改任何数据。</div>
      </Drawer>

      {/* 库配置弹窗（端点 12 读 / 端点 13 存——下次入库定型不热切换） */}
      <Modal
        title={<span>库配置 · {cfgLib ? cfgLib.name : ''}{helpIcon(<>四个索引开关、切段方式、索引期加法都按库单独配置；保存后在下次入库时生效，正在处理的报告不受影响。</>)}</span>}
        open={cfgLib != null} onCancel={() => setCfgLib(null)} footer={null} width={680}
      >
        {cfgError && (
          <Alert type="error" showIcon message="库配置加载失败——暂不可编辑" description={errText(cfgError)} />
        )}
        {/* UI-02 T5：开窗加载期（cfgForm 未到且无 cfgError）渲染 Spin，不再空白 */}
        {cfgLib && !cfgForm && !cfgError && <Spin />}
        {cfgLib && cfgForm && (() => {
          const setForm = patch => { setCfgForm(f => ({ ...f, ...patch })); setCfgSaved(null) }
          return (
            <>
              <div style={fieldLabel}>入库索引开关（按库配置）</div>
              {SWITCHES.map(s => (
                <div key={s.key} style={{ marginBottom: 12 }}>
                  <Space align="start">
                    <Switch size="small" checked={cfgForm.switches[s.key]}
                      onChange={v => setForm({ switches: { ...cfgForm.switches, [s.key]: v } })} />
                    <b>{s.name}</b>
                    {helpIcon(s.note)}
                  </Space>
                  {!cfgForm.switches[s.key] && (
                    <Alert style={{ marginTop: 6 }} type="warning" showIcon message={s.off} />
                  )}
                </div>
              ))}

              <div style={{ ...fieldLabel, marginTop: 4 }}>
                切段方式（三选一）
                {helpIcon(<>同一段报告原文，三种切法切出来不一样：智能切段一段 256–1024 字、相邻段重叠 10–20%；固定大小每段等长；大小段配合＝小段进索引被找到、大段入库被读懂。</>)}
              </div>
              <Tabs
                size="small" activeKey={cfgForm.mode} onChange={k => setForm({ mode: k })}
                items={[
                  { key: 'smart', label: '智能切段（256–1024 字）', children: chunkPanel('smart') },
                  { key: 'fixed', label: '固定大小', children: chunkPanel('fixed') },
                  { key: 'mixed', label: '大小段配合', children: chunkPanel('mixed') }
                ]}
              />

              <div style={{ ...fieldLabel, marginTop: 4 }}>
                索引期加法（处理完自动多做两件事）
                {helpIcon(<>全文档摘要 ×1；每 20 段自动生成一批"可能被问的问题"。处理完随"索引期加法"一步一起产出，见「入库任务」展开区。</>)}
              </div>
              <Checkbox checked={cfgForm.addSummary}
                onChange={e => setForm({ addSummary: e.target.checked })}>自动生成全文档摘要 ×1</Checkbox>
              <div style={{ marginTop: 6 }}>
                <Checkbox checked={cfgForm.addQuestions}
                  onChange={e => setForm({ addQuestions: e.target.checked })}>每 20 段自动生成"可能被问的问题"一批</Checkbox>
              </div>

              <Space style={{ marginTop: 16 }}>
                <Button type="primary" size="small" loading={cfgBusy} onClick={doSaveCfg}>保存本库配置</Button>
                {cfgSaved && <span style={{ fontSize: 12, color: '#8a94a3' }}>{cfgSaved.hint}</span>}
              </Space>
            </>
          )
        })()}
      </Modal>
    </div>
  )
}
