import { Button, Layout, Select } from 'antd'
import { MenuOutlined } from '@ant-design/icons'

/**
 * 壳层页头。
 *
 * 改造要点：
 * ① 页面标题落 <h1>——改造前全站 18 个页面的 h1 数量为 0（页标题只是个
 *    <span style={{fontSize:16}}>）。语义层级缺失，屏幕阅读器与
 *    「按语义选元素再按层级定样式」（refactoring-ui §2.6）都无从谈起。
 * ② 元信息行的 13px → 12px（13px 不在字号刻度 12/14/16/18/20/24 上）。
 * ③ 颜色改走令牌（--pa-*），不再散落手写 hex。
 * ④ 折叠态下的侧栏开关——配合 Sider 的断点折叠，375px 窄屏才有出路。
 */
export default function HeaderBar({ title, tag, crumb, role, setRole, collapsed, onToggle }) {
  return (
    <Layout.Header style={{
      background: 'transparent', padding: '0 20px', height: 52, lineHeight: '52px',
      borderBottom: '1px solid var(--pa-border)', display: 'flex', alignItems: 'center', gap: 14
    }}>
      {/* UI-13：页面标题上移壳层页头——标题＋树角标＋树名一行（标题/元信息两 span 并排，间距 12） */}
      {collapsed && (
        <Button
          type="text"
          aria-label="展开导航"
          icon={<MenuOutlined />}
          onClick={onToggle}
          style={{ color: 'var(--pa-text-secondary)', paddingInline: 4 }}
        />
      )}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, minWidth: 0 }}>
        <h1 style={{
          fontSize: 16, fontWeight: 600, margin: 0, lineHeight: '52px',
          color: 'var(--pa-text-primary)', whiteSpace: 'nowrap',
        }}>{title}</h1>
        <span className="header-crumb" style={{
          fontSize: 12, color: 'var(--pa-text-tertiary)',
          display: 'inline-flex', alignItems: 'center', gap: 10, whiteSpace: 'nowrap',
        }}>{tag}{crumb}</span>
      </div>
      <div style={{ flex: 1 }} />
      <Select
        value={role} onChange={setRole} style={{ width: 170 }}
        options={window.__roles.map(r => ({ value: r.key, label: r.label }))}
      />
    </Layout.Header>
  )
}
