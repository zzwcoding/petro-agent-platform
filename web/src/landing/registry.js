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
  D1: () => import('./D1.jsx')
}

/** 已点亮（已有落地页）的页面 key，按 frontend-foundation §5 阶段顺序增长。 */
export const LANDING_LIT = Object.keys(LANDING_MODULES)

/** 落地页懒加载器（key ∈ LANDING_LIT 保证命中；Shell 侧包 React.lazy）。 */
export function loadLandingPage(key) {
  return LANDING_MODULES[key]()
}

/** 落地树默认页（空 hash 时落第一个已点亮页）。 */
export const DEFAULT_LANDING_KEY = LANDING_LIT[0]
