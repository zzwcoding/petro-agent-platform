import { Button, Input, Layout, Select, Tooltip, Typography } from 'antd'
import { QuestionCircleOutlined, SearchOutlined } from '@ant-design/icons'

export default function HeaderBar({ title, crumb, role, setRole, onGuide }) {
  return (
    <Layout.Header style={{
      background: 'transparent', padding: '0 20px', height: 52, lineHeight: '52px',
      borderBottom: '1px solid #303030', display: 'flex', alignItems: 'center', gap: 14
    }}>
      <Typography.Title level={4} style={{ margin: 0, fontSize: 16 }}>
        {title}
        <span style={{ fontSize: 12, color: '#8a94a3', fontWeight: 400, marginLeft: 10 }}>{crumb}</span>
      </Typography.Title>
      <div style={{ flex: 1 }} />
      <Input
        prefix={<SearchOutlined />} placeholder="搜井号 / 报告 / 指标…"
        style={{ width: 200, background: 'rgba(255,255,255,0.08)' }}
      />
      <Select
        value={role} onChange={setRole} style={{ width: 170 }}
        options={window.__roles.map(r => ({ value: r.key, label: r.label }))}
      />
      <Tooltip title="演示导览：本页的点击顺序与看点">
        <Button icon={<QuestionCircleOutlined />} onClick={onGuide}>导览</Button>
      </Tooltip>
    </Layout.Header>
  )
}
