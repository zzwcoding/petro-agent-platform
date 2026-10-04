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
 */

import { useEffect, useState } from 'react'
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
 * @param {object} [rest] expandable/onRow/rowClassName/scroll/size 等 antd Table props 全透传
 *   （locale.emptyText 与 pagination 两键收归本件——取舍见文件头）
 * @returns {JSX.Element}
 */
export default function PagedTable(props) {
  const {
    dataSource = [], columns, rowKey, loading,
    emptyText, error = null, errorEmptyText = '数据拉取失败',
    resetKey, mode = 'client',
    page, pageSize, onPageChange, total,
    ...rest
  } = props
  const { locale: restLocale, ...passthrough } = rest

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

  return (
    <Table
      {...passthrough}
      dataSource={slice}
      columns={columns}
      rowKey={rowKey}
      loading={loading}
      locale={{ ...restLocale, emptyText: emptyNode }}
      pagination={pagination}
    />
  )
}
