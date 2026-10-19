import { Layout, Menu, Tag, Typography } from 'antd'
import { LANDING_LIT, PROTO_EXCLUDED } from '../landing/registry.js'

/**
 * 「原型」角标（frontend-foundation §4：原型页常显带「原型」角标）。
 *
 * 角标原为 10px——实测全站 19 个/页、共 342 处 10px 文字，低于可读下限。
 * 现提到 12px（字号刻度内的最小档），角标的识别功能不变。
 */
function ProtoBadge() {
  return <Tag style={{ marginLeft: 6, fontSize: 12, lineHeight: '18px', padding: '0 5px' }}>原型</Tag>
}

/**
 * 侧边菜单（双树同列，P0-06）。
 *
 * 组织模式＝**原样**：每组先列已点亮的落地页（裸 key），再并列该组全部页面
 * 的原型页（`proto/<KEY>` ＋「原型」角标）。双树对照是 frontend-foundation §4
 * 的刻意设计（点菜单即切树比 mock 与真 API），**不因视觉改造而改组织**。
 *
 * 改造只动样式，不动组织：
 *   ① 原型项整体降一级视觉权重（`menu-proto` 类 → 三级文字色），
 *      落地项保持全亮——「一堵同权重的墙」靠**权重差**解决，而不是靠挪位置；
 *   ② 角标 10px → 12px（可读下限）；
 *   ③ 窄屏侧栏可折叠（`< lg` 自动收起，页头开关展开）——原先固定 216px 永不折叠，
 *      实测 18/18 页在 375px 横向溢出（单页 91 个元素越界）；
 *   ④ 颜色全部走令牌（`--pa-*`），不再散落手写 hex。
 */
export default function SideMenu({ role, tree, current, onNavigate, collapsed }) {
  const groups = window.__menuForRole(role)
  const selected = tree === 'proto' ? `proto/${current}` : current

  // 组织模式：逐组并列落地项与原型项（与改造前完全一致）
  const items = groups.map(g => {
    const lit = g.items.filter(it => LANDING_LIT.includes(it.key))
    const children = [
      ...lit.map(it => ({ key: it.key, label: it.label })),
      ...g.items.filter(it => !PROTO_EXCLUDED.includes(it.key)).map(it => ({
        key: `proto/${it.key}`,
        label: (
          <span className="menu-proto">
            {it.label}
            <ProtoBadge />
          </span>
        ),
      })),
    ]
    return { type: 'group', label: g.group, children }
  })

  return (
    <Layout.Sider
      width={216}
      collapsedWidth={0}
      collapsed={collapsed}
      theme="dark"
      style={{ height: '100vh', position: 'sticky', top: 0, overflowY: 'auto' }}
    >
      <div style={{ padding: '18px 16px 14px', borderBottom: '1px solid var(--pa-border)' }}>
        <Typography.Text strong style={{ color: 'var(--pa-sider-text)', fontSize: 16 }}>
          Petro-Agent
        </Typography.Text>
        <div style={{ fontSize: 12, color: 'var(--pa-sider-subtext)', marginTop: 2 }}>数据问答平台</div>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selected]}
        style={{ background: 'transparent', borderInlineEnd: 'none', padding: '8px' }}
        items={items}
        onClick={e => onNavigate(e.key)}
        inlineIndent={16}
      />
    </Layout.Sider>
  )
}
