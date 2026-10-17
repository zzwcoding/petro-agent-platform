/**
 * 落地树注册表（双树共存，P0-06——frontend-foundation.md §4/§5）。
 *
 * 双树结构：落地树（真 API，#/X，全部走 api/client）× 原型树（mock，
 * #/proto/X，数据自包含）。菜单同列：落地页按阶段点亮（本表 LANDING_LIT）；
 * 原型页常显带「原型」角标。收官＝全部阶段验收后原型树整体删除。
 *
 * 新页落地流程：landing/ 下建 <KEY>.jsx → LANDING_LIT 加入该 KEY → 菜单
 * 自动点亮。阶段落位见 frontend-foundation §5（阶段 0＝D1；A1 属阶段 1）。
 */

/** 落地页模块表（显式注册——Vite 动态导入不支持自目录变量导入）。 */
const LANDING_MODULES = {
  A1: () => import('./A1.jsx'),
  A1V2: () => import('./A1V2.jsx'),
  D1: () => import('./D1.jsx'),
  B1: () => import('./B1.jsx'),
  B2: () => import('./B2.jsx'),
  B5: () => import('./B5.jsx'),
  B3: () => import('./B3.jsx'),
  A2: () => import('./A2.jsx'),
  B4: () => import('./B4.jsx'),
  E2: () => import('./E2.jsx')
}

/** 已点亮（已有落地页）的页面 key，按 frontend-foundation §5 阶段顺序增长。 */
export const LANDING_LIT = Object.keys(LANDING_MODULES)

/** 原型树排除集（不出「原型」菜单条目）：A1V2＝问一问V2 新建改造页——
 *  没有 mock 原型对应物，原型树复用落地组件只会产生同名假条目。
 *  A1V2R＝问一问V2 重设计 mock 静态页（临时路由，见下 REDESIGN_MODULES）——
 *  本身就是 mock 页，落地树已有「(mock)」菜单项，原型树不再出同页副本。 */
export const PROTO_EXCLUDED = ['A1V2', 'A1V2R']

/**
 * 重设计 mock 静态页注册表（临时路由——DEBT(Owner)：只服务设计稿 §5 第 1 步
 * 「mock 静态页对版面」，去向 docs/runtime-refactor/frontend-redesign-设计.md；
 * 第 2 步接归约器后由 Owner 裁决删除或替换现状页）。
 *
 * 与 LANDING_MODULES 分开登记：这些页是「对版面的静态假数据页」，不属落地阶段点亮链
 * （LANDING_LIT＝十键阶段表，由 landing/dual-tree-smoke.test.jsx 钉死），但复用同一套
 * 懒加载/菜单/页头标题机制（Shell.jsx 把本表并进 LANDING_LAZY）。
 */
const REDESIGN_MODULES = {
  A1V2R: () => import('./redesign/A1V2R.jsx')
}

/** 重设计 mock 页键（Shell 懒加载 + SideMenu 菜单点亮用）。 */
export const REDESIGN_LIT = Object.keys(REDESIGN_MODULES)

/** 重设计 mock 页懒加载器（key ∈ REDESIGN_LIT 保证命中）。 */
export function loadRedesignPage(key) {
  return REDESIGN_MODULES[key]()
}


/** 落地页懒加载器（key ∈ LANDING_LIT 保证命中；Shell 侧包 React.lazy）。 */
export function loadLandingPage(key) {
  return LANDING_MODULES[key]()
}

/**
 * 落地树默认页（空 hash 落此页）。
 * P1-09 裁定：切 A1——问一问是全员可见的统一入口（roles.js 工作台首位、
 * 所有问句唯一主端点 POST /api/chat/asks 的消费面），落地树点亮它之后空
 * hash 首屏应为工作台主入口，而非阶段序首个点亮页 D1。
 */
export const DEFAULT_LANDING_KEY = 'A1'
