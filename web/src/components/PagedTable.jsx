/**
 * PagedTable —— 业务数据集合表统一分页封装（组件形态，方案-阶段1交互优化-20261004
 * §2.1 定死；SHELL 审查发现 F2「统一分页组件尚不存在」的落位载体）。
 *
 * client 模式＝临时客户端分页，挂后续批 DEBT(阶段1-ui/UI-07)：服务端分页缺口
 * 全部去向 UI-07 提案票（tickets/phase1-ui/UI-07.md，Owner 拍板前不动合同册与
 * 后端）；全站 client 模式表格的债务只在本文件头登记一处，各页不散布标签。
 *
 * 形态锁定（偏离 props 全透传的两处取舍，方案 §2.1 定死）：
 * - locale.emptyText 强制收掉：外部 locale 其余键仍透传，但 emptyText 键一律换
 *   本件渲染的 <Empty>（空态话术只认 emptyText prop——强制每表显式想清空态话术）；
 * - pagination 不接受外部覆盖：分页条参数（showSizeChanger/showQuickJumper/
 *   hideOnSinglePage/showTotal/position/size）定死一处，保证全站统计恒显、形态齐一。
 * 失败态≠空态：error 只切空态描述，内联 Alert 由页面自挂（两件并存，不进封装）。
 *
 * UI-12（中间表格表内滚动，Owner 2026-10-05 巡检裁决）增 fill 模式：fill=true 时
 * 外层包 flex 列容器（flex:1 minHeight:0），ResizeObserver 实测容器高换 scroll.y
 * 表内滚——表头/分页条恒在视口内、页面级滚动消灭；消费方须搭「root→Card→body→
 * Tabs→pane」高度有界 flex 链（共享工具类 .fill-tabs 落 web/src/index.css）。
 */

import { useEffect, useRef, useState } from 'react'
import { Empty, Table } from 'antd'

/** pageSize 缺省 20——对齐后端 ReadOnlyRepository.paginate 的 page_size 默认（app/infra/db.py:395 实读）。 */
const DEFAULT_PAGE_SIZE = 20

/** 分页条形态定死（方案 §2.1）：统计恒显、无页大小切换、无快速跳转、右下、small。 */
const PAGINATION_FIXED = {
  showSizeChanger: false,
  showQuickJumper: false,
  hideOnSinglePage: false,
  showTotal: t => `共 ${t} 条`,
  position: ['bottomRight'],
  size: 'small'
}

/**
 * 全站业务集合表统一分页封装。
 *
 * @param {object} props
 * @param {any[]} [props.dataSource] 数据行：client 模式整表内存切片；server 模式原样透传当页数据
 * @param {any[]} props.columns antd Table columns（透传）
 * @param {string | ((row: any) => string)} [props.rowKey] antd Table rowKey（透传）
 * @param {boolean} [props.loading] antd Table loading（透传）
 * @param {string | any} props.emptyText 必填：空态话术（string | node）
 * @param {Error | null} [props.error] ApiError｜null——非空时空态描述换 errorEmptyText
 * @param {string | any} [props.errorEmptyText] error 非空时的空态描述，缺省「数据拉取失败」
 * @param {string | number} [props.resetKey] 变化时 client 模式页码归 1（显式筛条件联动）
 * @param {'client' | 'server'} [props.mode] 默认 'client'
 * @param {number} [props.page] server 模式当前页（受控）
 * @param {number} [props.pageSize] 页大小：client 缺省 20；server 模式必传（各册 pageSize 合同冻结，如 D1 流水=15）
 * @param {(page: number, pageSize: number) => void} [props.onPageChange] server 模式翻页上抛
 * @param {number} [props.total] server 模式总条数（分页条统计）
 * @param {boolean} [props.fill] 默认 false 零回归。fill=true＝表内滚动模式（UI-12）：
 *   外层包 flex 列容器（ref=wrapRef），useEffect 挂 ResizeObserver（环境无
 *   ResizeObserver——jsdom/兜底——自动跳过）实测容器高，scroll.y＝容器高−表头高
 *   −分页条高（渲染后 DOM .ant-table-thead/.ant-pagination offsetHeight 实测），
 *   观测回调随窗口/内容变化重算；首帧 thead/pagination 未实测前先不传 y，observer
 *   回调补挂。要求父链高度有界（root→Card→body→Tabs→pane flex 链），否则测得
 *   自然高、内滚不生效。scroll.x 照旧透传并与 y 合并（如 D1 流水 x:960＋fill.y）。
 * @param {object} [rest] expandable/onRow/rowClassName/scroll/size 等 antd Table props 全透传
 *   （locale.emptyText 与 pagination 两键收归本件——取舍见文件头；fill=true 时
 *   scroll 键由本件合并 y，其余键原样透传）
 * @returns {JSX.Element}
 */
export default function PagedTable(props) {
  const {
    dataSource = [], columns, rowKey, loading,
    emptyText, error = null, errorEmptyText = '数据拉取失败',
    resetKey, mode = 'client',
    page, pageSize, onPageChange, total,
    fill = false,
    ...rest
  } = props
  const { locale: restLocale, scroll: scrollX, ...passthrough } = rest

  // client 模式内部页码（server 模式页码全受控，不用内部态）
  const [clientPage, setClientPage] = useState(1)
  // resetKey 变化归页 1（显式筛控件联动）
  useEffect(() => { setClientPage(1) }, [resetKey])

  const size = pageSize ?? DEFAULT_PAGE_SIZE

  // 内置超界钳制（方案 §2.1 定死）：渲染时当前页超出总页数自动归 1——显式 resetKey
  // 覆盖不到的隐式筛变兜底（B5 图例隐去边、弹窗内数据切换等），不停在超界页出空表。
  // 渲染期受控归位（React 同组件 render-phase 更新，立即重渲不闪空表）。
  const count = dataSource.length
  const totalPages = Math.max(1, Math.ceil(count / size))
  if (mode === 'client' && clientPage > totalPages && clientPage !== 1) {
    setClientPage(1)
  }
  const currentPage = mode === 'client' ? Math.min(clientPage, totalPages) : page

  const slice = mode === 'client'
    ? dataSource.slice((currentPage - 1) * size, (currentPage - 1) * size + size)
    : dataSource

  // 空态渲染定死（方案 §2.1）：Empty 简单图＋emptyText；error 非空换 errorEmptyText
  const emptyNode = (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={error ? errorEmptyText : emptyText}
    />
  )

  const pagination = mode === 'server'
    ? {
        ...PAGINATION_FIXED,
        current: page,
        pageSize: size,
        total: total ?? 0,
        onChange: (p, ps) => onPageChange?.(p, ps)
      }
    : {
        ...PAGINATION_FIXED,
        current: currentPage,
        pageSize: size,
        total: count,
        onChange: p => setClientPage(p)
      }

  // ── fill 模式测高（UI-12 定死）：实测 wrapper 高 → scroll.y 内滚 ──
  // 主通道 ResizeObserver 随窗口/内容变化重算（Tabs 页签隐藏测高为 0 → 不传 y，
  // 切回再触发重算——无需 destroyInactiveTabPane）；兜底通道挂载即测＋双 rAF＋
  // resize 重测（部分嵌入式内核 RO 回调不送达——真机复验实测，见 effect 内注）。
  // 测得 ≤0（jsdom 零高/页签隐藏/视口过矮）不传 y，渲染物与 fill=false 同形，
  // 不做负值内滚。
  const wrapRef = useRef(null)
  const [y, setY] = useState()
  useEffect(() => {
    if (!fill) return undefined
    const measure = () => {
      const el = wrapRef.current
      if (!el) return
      const thead = el.querySelector('.ant-table-thead')
      const pager = el.querySelector('.ant-pagination')
      const next = el.clientHeight
        - (thead ? thead.offsetHeight : 0)
        - (pager ? pager.offsetHeight : 0)
      setY(next > 0 ? next : undefined)
    }
    // 主通道：ResizeObserver（标准环境随窗口/内容变化重算）。
    // 兜底通道（UI-12 真机复验发现）：部分嵌入式内核 RO 回调不送达（实测最小复现
    // 零回调）——挂载即测＋双 rAF 补测＋resize 事件重测，保证任何环境出初始 y；
    // measure 幂等（同值 setY 不引发额外渲染），channels 并存无副作用。
    let ro
    if (typeof ResizeObserver !== 'undefined') {
      ro = new ResizeObserver(measure)
      if (wrapRef.current) ro.observe(wrapRef.current)
    }
    measure()
    let raf1
    let raf2
    if (typeof requestAnimationFrame !== 'undefined') {
      raf1 = requestAnimationFrame(() => { raf2 = requestAnimationFrame(measure) })
    }
    window.addEventListener('resize', measure)
    return () => {
      if (ro) ro.disconnect()
      if (raf1) cancelAnimationFrame(raf1)
      if (raf2) cancelAnimationFrame(raf2)
      window.removeEventListener('resize', measure)
    }
  }, [fill])

  const table = (
    <Table
      {...passthrough}
      dataSource={slice}
      columns={columns}
      rowKey={rowKey}
      loading={loading}
      locale={{ ...restLocale, emptyText: emptyNode }}
      pagination={pagination}
      scroll={fill && y != null ? { ...scrollX, y } : scrollX}
    />
  )

  if (!fill) return table
  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }} ref={wrapRef}>
      {table}
    </div>
  )
}
