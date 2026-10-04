import { Suspense, lazy, createElement, useEffect, useState } from 'react'
import { Layout, Skeleton, Tag } from 'antd'
import { ROLES, PAGE_NAMES, menuForRole } from '../roles.js'
import SideMenu from './SideMenu.jsx'
import HeaderBar from './HeaderBar.jsx'
import TraceBar, { DEV } from './TraceBar.jsx'
import A1Chat, { A1_TRACE } from '../pages/A1Chat.jsx'
import Stub from '../pages/Stub.jsx'
import NotLit from '../landing/NotLit.jsx'
import { DEFAULT_LANDING_KEY, LANDING_LIT, loadLandingPage } from '../landing/registry.js'
import { useAppStore, switchRole } from '../store/app.js'

window.__roles = ROLES
window.__menuForRole = menuForRole

// 懒加载页面（P1–P5 施工产出 src/pages/<KEY>.jsx；各页文件副作用注册溯源）：
// —— 双树共存（frontend-foundation §4）后归原型树（#/proto/X），组件原样复用零搬迁。
const LAZY = {}
for (const key of ['A2','A3','B1','B2','B3','B4','B5','C1','C2','C3',
  'D1','D2','D3','D6','E1','E2','E3','F1','INDEX']) {
  LAZY[key] = lazy(() => import(`../pages/${key}.jsx`))
}

// 落地树懒加载页（landing/<KEY>.jsx，按 LANDING_LIT 点亮；真 API 走 api/client）：
const LANDING_LAZY = {}
for (const key of LANDING_LIT) {
  LANDING_LAZY[key] = lazy(() => loadLandingPage(key))
}

/**
 * 解析 hash → 双树导航态（P0-06 双树共存：落地 #/X · 原型 #/proto/X）。
 * 空 hash ＝ 落地树默认页（第一个已点亮页）。
 * hash 内 query 剥离（P1-11 收口——NotLit locator 桥退役）：`#/B2?chunk=x`
 * 的 query 挪到真 location.search（replaceState 无刷新），页面直读
 * location.search 消费（B2 ?chunk=）；路由 pageKey 恒裸键。
 * @returns {{tree: 'landing' | 'proto', page: string}}
 */
export function parseHash() {
  const raw = (location.hash || '').replace(/^#\/?/, '')
  const qAt = raw.indexOf('?')
  const path = qAt >= 0 ? raw.slice(0, qAt) : raw
  if (qAt >= 0) peelQueryIntoSearch(raw.slice(qAt + 1), path)
  if (raw.startsWith('proto/')) return { tree: 'proto', page: path.slice(6) || 'A1' }
  return { tree: 'landing', page: path || DEFAULT_LANDING_KEY }
}

/** hash query → location.search（replaceState 无刷新；失败静默——query 留 hash 不碍路由）。 */
function peelQueryIntoSearch(query, path) {
  try {
    history.replaceState(null, '', `?${query}#/${path}`)
  } catch { /* jsdom/隐私模式静默 */ }
}

export default function Shell() {
  // 角色槽收进 zustand（store/app.js 槽①，接 roles.js 唯一真源）
  const role = useAppStore(s => s.role)
  const [nav, setNav] = useState(parseHash)

  useEffect(() => {
    const onHash = () => setNav(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // 菜单 key：落地页＝裸 key（#/D1），原型页＝'proto/<KEY>'（#/proto/D1）
  const navigate = key => { location.hash = '/' + key }
  const { tree, page } = nav
  const isProto = tree === 'proto'
  const title = page === 'A1' ? '问一问'
    : (PAGE_NAMES[page] || menuForRole(role).flatMap(g => g.items).find(i => i.key === page)?.label || page)
  const crumb = isProto ? '原型树 · mock 数据' : '落地树 · 真 API'
  const treeTag = <Tag color={isProto ? 'default' : 'green'} style={{ marginLeft: 8 }}>{isProto ? '原型' : '落地'}</Tag>
  const traceText = isProto ? (page === 'A1' ? A1_TRACE : (window.__traces?.[page] || '')) : ''
  // Content 48px 底垫与 TraceBar 渲染同源（UI-00）——判据同 TraceBar.jsx:5
  // `if (!DEV || !text) return null`：只在「DEV 且 traceText 非空」时给垫。
  // dev 模式落地树 traceText 恒空，不再白垫 48px。
  const hasTracePad = Boolean(DEV && traceText)

  const ProtoPage = page === 'A1' ? A1Chat : LAZY[page]

  return (
    <Layout style={{ height: '100vh' }}>
      <SideMenu role={role} tree={tree} current={page} onNavigate={navigate} />
      <Layout style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        {/* 角色切换走 store.switchRole 双写（先 X-Dev-User 桩后角色槽）——
            只写槽会让请求头带旧身份、页头与数据权限脱钩（P0-06 审查 P2 修复） */}
        <HeaderBar title={<span>{title}{treeTag}</span>}
          crumb={crumb}
          role={role} setRole={switchRole} />
        <Layout.Content style={{ padding: hasTracePad ? '16px 20px 48px' : '16px 20px', flex: 1, overflow: 'auto' }}>
          {isProto ? (page === 'A1' ? <A1Chat role={role} /> : ProtoPage ? (
            <Suspense fallback={<Skeleton active />}>
              <ProtoPage />
            </Suspense>
          ) : <Stub pageKey={page} />) : LANDING_LAZY[page] ? (
            <Suspense fallback={<Skeleton active />}>
              {createElement(LANDING_LAZY[page])}
            </Suspense>
          ) : <NotLit pageKey={page} />}
        </Layout.Content>
      </Layout>
      <TraceBar text={traceText} />
    </Layout>
  )
}
