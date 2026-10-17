import { Fragment } from 'react'
import { Layout, Menu, Tag, Typography } from 'antd'
import { LANDING_LIT, PROTO_EXCLUDED, REDESIGN_LIT } from '../landing/registry.js'

/** 「原型」角标（frontend-foundation §4：原型页常显带「原型」角标）。 */
function ProtoBadge() {
  return <Tag style={{ marginLeft: 6, fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>原型</Tag>
}

/**
 * 侧边菜单（双树同列，P0-06）：
 * 每组先列已点亮的落地页（裸 key），再并列原型页（proto/<KEY> ＋角标）。
 * 落地页按阶段点亮（LANDING_LIT）；原型页常显——点一下即对比 mock 与真 API。
 * REDESIGN_LIT（重设计 mock 静态页，临时路由）与落地页同列展示——同属落地树键位。
 */
export default function SideMenu({ role, tree, current, onNavigate }) {
  const groups = window.__menuForRole(role)
  const items = groups.map(g => {
    const lit = g.items.filter(it => LANDING_LIT.includes(it.key) || REDESIGN_LIT.includes(it.key))
    const children = [
      ...lit.map(it => ({ key: it.key, label: it.label })),
      ...g.items.filter(it => !PROTO_EXCLUDED.includes(it.key)).map(it => ({
        key: `proto/${it.key}`,
        label: <Fragment>{it.label}<ProtoBadge /></Fragment>
      }))
    ]
    return { type: 'group', label: g.group, children }
  })
  const selected = tree === 'proto' ? `proto/${current}` : current
  return (
    <Layout.Sider width={216} theme="dark"
      style={{ height: '100vh', position: 'sticky', top: 0, overflowY: 'auto' }}>
      <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid rgba(255,255,255,.12)' }}>
        <Typography.Text strong style={{ color: '#fff', fontSize: 16 }}>Petro-Agent</Typography.Text>
        <div style={{ fontSize: 11, color: '#8fa8c8' }}>数据问答平台</div>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selected]}
        style={{ background: 'transparent', borderInlineEnd: 'none', padding: '8px' }}
        items={items}
        onClick={e => onNavigate(e.key)}
      />
    </Layout.Sider>
  )
}
