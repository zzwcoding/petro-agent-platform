import { Layout, Select } from 'antd'

export default function HeaderBar({ title, tag, crumb, role, setRole }) {
  return (
    <Layout.Header style={{
      background: 'transparent', padding: '0 20px', height: 52, lineHeight: '52px',
      borderBottom: '1px solid #303030', display: 'flex', alignItems: 'center', gap: 14
    }}>
      {/* UI-13：页面标题上移壳层页头——标题＋树角标＋树名一行（标题/元信息两 span 并排，间距 12） */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 16, fontWeight: 600 }}>{title}</span>
        <span style={{ fontSize: 13, color: '#8a94a3', display: 'inline-flex', alignItems: 'center', gap: 10 }}>{tag}{crumb}</span>
      </div>
      <div style={{ flex: 1 }} />
      <Select
        value={role} onChange={setRole} style={{ width: 170 }}
        options={window.__roles.map(r => ({ value: r.key, label: r.label }))}
      />
    </Layout.Header>
  )
}
