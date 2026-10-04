import { Layout, Select } from 'antd'

export default function HeaderBar({ tag, crumb, role, setRole }) {
  return (
    <Layout.Header style={{
      background: 'transparent', padding: '0 20px', height: 52, lineHeight: '52px',
      borderBottom: '1px solid #303030', display: 'flex', alignItems: 'center', gap: 14
    }}>
      <span style={{ fontSize: 13, color: '#8a94a3', display: 'inline-flex', alignItems: 'center', gap: 10 }}>{tag}{crumb}</span>
      <div style={{ flex: 1 }} />
      <Select
        value={role} onChange={setRole} style={{ width: 170 }}
        options={window.__roles.map(r => ({ value: r.key, label: r.label }))}
      />
    </Layout.Header>
  )
}
