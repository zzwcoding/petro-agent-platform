/**
 * 落地树 · D1 模型与线路（P0-06 冒烟骨架——本票只接 GET /api/gateway/models）。
 *
 * 页面完整落地（页头徽标/配置读写/spend 流水/演练工具栏全接线）是 P0-07；
 * 对照原型树：#/proto/D1。合同：D1-模型与线路.md 端点 1；响应 snake_case
 * （00 §14-R1）＝{ gateway: {status}, models: [{key,name,alias,role,access,note}] }。
 */

import { useEffect, useState } from 'react'
import { Alert, Card, Table, Tag, Typography } from 'antd'
import { ApiError, get } from '../api/client.js'
import { useAppStore } from '../store/app.js'

/** 网关运行态徽标（页头徽标；running|degraded|down——D1 端点 1）。 */
const GATEWAY_STATUS = {
  running: { color: 'success', label: '运行中' },
  degraded: { color: 'warning', label: '降级中' },
  down: { color: 'error', label: '不可用' }
}

const COLUMNS = [
  { title: '调用别名', dataIndex: 'alias', width: 180,
    render: (v, row) => <Typography.Text code>{v}</Typography.Text> },
  { title: '名称', dataIndex: 'name', width: 140 },
  { title: '角色', dataIndex: 'role', width: 100,
    render: v => <Tag color={v === 'main' ? 'blue' : 'default'}>{v === 'main' ? '主用' : v === 'backup' ? '备用' : v}</Tag> },
  { title: '接入', dataIndex: 'access' },
  { title: '说明', dataIndex: 'note', ellipsis: true }
]

/**
 * 落地 D1 冒烟页。
 * @returns {JSX.Element}
 */
export default function D1Landing() {
  const semanticVersion = useAppStore(s => s.semanticVersion)
  const [state, setState] = useState({ loading: true, gateway: null, models: [], error: null })

  useEffect(() => {
    let alive = true
    get('/gateway/models')
      .then(data => { if (alive) setState({ loading: false, gateway: data.gateway, models: data.models, error: null }) })
      .catch(err => { if (alive) setState({ loading: false, gateway: null, models: [], error: err }) })
    return () => { alive = false }
  }, [])

  const badge = GATEWAY_STATUS[state.gateway?.status]

  return (
    <div style={{ maxWidth: 1080 }}>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Typography.Title level={5} style={{ marginTop: 0 }}>
          模型与线路 · 落地树（真 API）
          {badge && <Tag style={{ marginLeft: 8 }} color={badge.color}>{badge.label}</Tag>}
          {semanticVersion && <Tag style={{ marginLeft: 4 }}>语义层 v{semanticVersion}</Tag>}
        </Typography.Title>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          P0-06 冒烟骨架：仅接 GET /api/gateway/models（api/client）；配置读写 / spend 流水 / 演练工具栏由
          P0-07 接线。对照原型树：#/proto/D1（数据为 mock）。
        </Typography.Text>
      </Card>

      {state.error && (
        <Alert style={{ marginBottom: 12 }} type="error" showIcon
          message="模型清单拉取失败"
          description={state.error instanceof ApiError
            ? `${state.error.message}${state.error.code ? `（code ${state.error.code}）` : ''}${state.error.traceId ? ` · trace ${state.error.traceId}` : ''}`
            : String(state.error)} />
      )}

      <Table
        rowKey="key"
        size="small"
        loading={state.loading}
        columns={COLUMNS}
        dataSource={state.models}
        pagination={false}
        locale={{ emptyText: state.error ? '——' : '加载中…' }}
      />
    </div>
  )
}
