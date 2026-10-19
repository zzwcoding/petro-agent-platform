/**
 * theme.js —— 前端设计令牌唯一真源（DESIGN.md 配套）
 *
 * 为什么有这一层（refactoring-ui §1.5「每个值都来自系统」）：
 * 改造前全站 1421 处内联 style={{}}、526 个手写 hex、约 60 个去重色值。
 * 根因不是「忘了加变量」，而是——源码作者写的是 antd **亮色主题**的色值
 * （#52c41a 绿 / #faad14 琥珀 / #ff4d4f 红 / #4a9dff 蓝），而 antd 的
 * darkAlgorithm 会把每个语义色**重新派生一遍**：
 *     种子 #4a9dff  →  渲染 #4288dc   （色差 1.31:1，肉眼可见）
 *     源码 #52c41a  →  渲染 #49aa19
 *     源码 #faad14  →  渲染 #d89614
 *     源码 #ff4d4f  →  渲染 #dc4446
 * 于是每个语义色都分裂成「源码值」和「渲染值」两个，分属两套系统。
 *
 * 解法不在于逐个改 526 处源码，而在于**在算法层把整套令牌钉死**，
 * 让 antd 的渲染值 === 项目源码里已经写了 287 次的那套值。
 * 一处改动，全站收敛；且此后改令牌即改全站。
 *
 * 落地位置：antd ConfigProvider（components 走 antd 自己的 token 契约）
 * ＋ CSS 变量（供 index.css / 非 antd 的原生样式消费）。
 */

import { theme } from 'antd'

/** 语义色板（primitive）—— 与 design-tokens.json 同源，改这里也要改 JSON。 */
export const palette = {
  // 中性：GitHub-dark 家族（项目既有：#0d1117 body / #161b22 卡片 / #30363d 描边）
  surface: {
    page: '#0d1117',      // 页面底
    card: '#161b22',      // 卡片 / 容器底
    raised: '#212830',    // 浮层 / 弹层底
    border: '#30363d',    // 分隔线 / 描边
    borderStrong: '#212830',
  },
  // 文字三级 + 禁用级（§2.2.a：三级文字；每级都过了 WCAG 4.5:1）
  text: {
    primary:   'rgba(255, 255, 255, 0.85)',  // 12.61:1 on card
    secondary: 'rgba(255, 255, 255, 0.65)',  //  7.71:1 on card
    tertiary:  '#8a94a3',                    //  5.64:1 on card（项目既成值，287 处）
    quaternary:'rgba(255, 255, 255, 0.25)',  //  2.25:1 —— 仅限禁用态（WCAG 豁免）
  },
  // 品牌与语义
  brand: {
    primary: '#4a9dff',   // on card 6.23:1
    onPrimary: '#0d1117', // on primary 6.81:1 —— 翻转对比（§5.6.1）
    success: '#52c41a',   // 7.64:1
    warning: '#faad14',   // 9.10:1
    danger:  '#ff4d4f',   // 5.29:1
    info:    '#4a9dff',
  },
  // 侧栏品牌蓝（唯一不来自 antd 的表面：品牌识别需要）
  sider: {
    bg:        '#0b2e59',
    text:      '#ffffff',   // 13.55:1
    subText:   '#8fa8c8',   //  5.55:1 —— 带蓝相的浅色，不是灰（§5.7 禁灰压彩底）
    groupTitle:'#8aa2c0',   //  5.17:1 —— 分组标题；须明显暗于菜单项 8.27:1（层级保留）
    itemHover: 'rgba(255, 255, 255, 0.08)',
  },
  // ── 数据可视化分类色（与 UI 色相分离的独立一套） ──────────────────────
  // 用途：关系图谱（G6）按节点类型着色——井/区块/平台/油田/措施 + 未知类型轮转。
  // 为什么不并入 UI 令牌：① 这一套的职责是**互相区分**，若都映射到
  //   --pa-primary/--pa-success/… ，图上不同类型会撞成同一色，图谱失去可读性；
  // ② G6 的 fill/stroke/labelFill 走图形属性（SVG 属性或 canvas），
  //   **CSS 变量在 canvas 里不解析**，故此套必须是字面 hex。
  // 所以它是「系统里的一个值」但用字面量承载——进令牌文件、闸机看守，但不经 CSS 变量。
  viz: {
    typeHex: { 井: '#3b8dff', 区块: '#52c41a', 平台: '#9254de', 油田: '#faad14', 措施: '#fa8c16' },
    palette: ['#3b8dff', '#52c41a', '#9254de', '#faad14', '#fa8c16', '#4aa3ff', '#e8a23d', '#57a75f', '#a78bde', '#eb2f96'],
    unknown: '#8a94a3',     // 未知类型兜底
    highlight: '#4a9dff',   // 悬停高亮
    active: '#7ab3ff',      // 选中
    // ── 以下四个是「喂给 G6 图形属性」的颜色 ──────────────────────────
    // G6 的 fill/stroke/labelFill/background 走 SVG 属性与 canvas，
    // **CSS 变量在图形属性里不解析**——实测踩坑：把画布底/节点文字改成
    // var(--pa-*) 后，画布变纯黑、节点主文字整段消失、边标签不显。
    // 故凡进 G6 配置的颜色一律取本块的**字面 hex**；
    // DOM 侧（tooltip 浮层、图例色点、行内样式）仍走 CSS 变量。
    canvasBg:    '#161b22',  // 画布底
    nodeText:    '#e6edf3',  // 节点主文字（iconText 的填充）
    edgeLabel:   '#8a94a3',  // 边标签文字
    edgeLabelBg: '#161b22',  // 边标签底
  },
}

/**
 * 钉死暗色算法派生的结果。
 *
 * 注意签名：cssinjs 的 derivatives.reduce 是 `r(seed, prev)`，
 * 第二个参数才是上一步的结果——写成 `(t) => ({...t})` 会把 seed 当 prev，
 * 派生链直接断掉（colorBorder 等全变 undefined）。
 *
 * @param {object} seed  antd 种子令牌
 * @param {object} prev  上一个 derivative 的输出
 */
function pinDarkPalette(seed, prev) {
  return {
    ...prev,
    // —— 品牌 / 语义色：消除「源码值 vs 渲染值」分裂 ——
    colorPrimary: palette.brand.primary,
    colorInfo: palette.brand.info,
    colorLink: palette.brand.primary,
    colorSuccess: palette.brand.success,
    colorWarning: palette.brand.warning,
    colorError: palette.brand.danger,
    // —— 文字 ——
    colorTextTertiary: palette.text.tertiary,
    // —— 表面：消除「页面底 #0d1117 vs 卡片底 #141414」的割裂 ——
    colorBgContainer: palette.surface.card,
    colorBgLayout: palette.surface.page,
    colorBgElevated: palette.surface.raised,
    colorBorder: palette.surface.border,
    colorBorderSecondary: palette.surface.borderStrong,
  }
}

/** 间距刻度（§3.2.2：4 基准）—— 改造前有 13 档 padding、10 档 gap、15 档 margin。 */
export const spacing = [0, 4, 8, 12, 16, 24, 32, 48, 64]

/** 字号刻度（§4.1.1d：12 14 16 18 20 24）—— 改造前有 8 档，含 10/11/13。 */
export const fontSizes = [12, 14, 16, 18, 20, 24]

/**
 * ConfigProvider 主题对象（main.jsx 消费）。
 * 令牌走 antd 自己的契约——不另起一套 CSS 体系（既有系统永远优先）。
 */
export const antdTheme = {
  algorithm: [theme.darkAlgorithm, pinDarkPalette],
  token: {
    colorPrimary: palette.brand.primary,
    // 主按钮字色：走 token prop 而非 algorithm——alias.js 会在派生后
    // 用 colorWhite 重算 colorTextLightSolid，把 algorithm 里的钉死覆盖掉。
    colorTextLightSolid: palette.brand.onPrimary,
    colorWhite: palette.brand.onPrimary,
    borderRadius: 6,
    fontSize: 14,
    controlHeight: 32,
    wireframe: false,
  },
  components: {
    Layout: {
      siderBg: palette.sider.bg,
      triggerBg: palette.sider.bg,
      headerBg: 'transparent',
      bodyBg: palette.surface.page,
    },
    Menu: {
      darkItemBg: 'transparent',
      darkSubMenuItemBg: 'transparent',
      // 选中态＝主色底 + 深色字（与主按钮同一套语言）。
      // 注：半透明白叠在品牌蓝侧栏上会「洗灰」选中项，颜色信号丢失——已修。
      darkItemSelectedBg: palette.brand.primary,
      darkItemSelectedColor: palette.brand.onPrimary,
      darkItemHoverBg: palette.sider.itemHover,
      darkItemColor: 'rgba(255, 255, 255, 0.75)',
      // 分组标题（工作台/报告库/…）：antd 默认取 colorTextLightSolid——本项目把
      // colorTextLightSolid 翻成深色（主按钮字色），暗色菜单的分组标题会跟着变深，
      // 叠在品牌蓝侧栏上对比度只有 1.28:1（几乎不可见）。故显式给定：
      // 与侧栏同色相的浅蓝灰 #8aa2c0 = 5.17:1，且明显暗于菜单项 8.27:1（层级保留）。
      darkGroupTitleColor: palette.sider.groupTitle,
      itemBorderRadius: 6,
    },
    Table: {
      headerBg: palette.surface.raised,
      headerColor: palette.text.secondary,
      rowHoverBg: 'rgba(255, 255, 255, 0.04)',
      borderColor: palette.surface.border,
    },
    Card: {
      colorBgContainer: palette.surface.card,
    },
    Tabs: {
      inkBarColor: palette.brand.primary,
      itemSelectedColor: palette.brand.primary,
      itemHoverColor: palette.brand.primary,
    },
    Tag: {
      defaultBg: 'rgba(255, 255, 255, 0.08)',
      defaultColor: palette.text.secondary,
    },
  },
}

/**
 * CSS 自定义属性——供 index.css 与非 antd 的原生样式消费，
 * 保证「CSS 里的底色」与「antd 组件的底色」同源（改造前 body 是 #0d1117
 * 而 antd 卡片是 #141414，肉眼可见的接缝）。
 */
export const cssVars = {
  '--pa-surface-page': palette.surface.page,
  '--pa-surface-card': palette.surface.card,
  '--pa-surface-raised': palette.surface.raised,
  '--pa-border': palette.surface.border,
  '--pa-text-primary': palette.text.primary,
  '--pa-text-secondary': palette.text.secondary,
  '--pa-text-tertiary': palette.text.tertiary,
  '--pa-text-quaternary': palette.text.quaternary,
  '--pa-primary': palette.brand.primary,
  '--pa-success': palette.brand.success,
  '--pa-warning': palette.brand.warning,
  '--pa-danger': palette.brand.danger,
  '--pa-on-primary': palette.brand.onPrimary,
  '--pa-sider-bg': palette.sider.bg,
  '--pa-sider-text': palette.sider.text,
  '--pa-sider-subtext': palette.sider.subText,
  '--pa-radius': '6px',
  '--pa-radius-sm': '4px',
  '--pa-radius-lg': '8px',
}

/** 把 CSS 变量挂到 :root（main.jsx 调用一次）。 */
export function applyCssVars(root = document.documentElement) {
  for (const [k, v] of Object.entries(cssVars)) root.style.setProperty(k, v)
}
