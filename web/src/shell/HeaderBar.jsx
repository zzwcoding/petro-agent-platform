import { Layout, Select, Typography } from 'antd'

export default function HeaderBar({ title, crumb, role, setRole }) {
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
      <Select
        value={role} onChange={setRole} style={{ width: 170 }}
        options={window.__roles.map(r => ({ value: r.key, label: r.label }))}
      />
    </Layout.Header>
  )
}
