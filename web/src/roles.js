// 角色 × 菜单可见性（F48：不是被拒答，而是世界里没有）
export const ROLES = [
  { key: 'laowang', label: '老王 · 油藏工程师' },
  { key: 'xiaoli', label: '小李 · 地质/质检' },
  { key: 'zhuren', label: '主任 · 汇报人' },
  { key: 'aqiang', label: '阿强 · 平台运维' },
  { key: 'shixi', label: '实习生 · 作业区' }
]

// 组/页面对角色的可见规则：roles 字段缺省=全员可见
export const MENU = [
  { group: '工作台', items: [
    { key: 'A1', label: '问一问V1' },
    { key: 'A1V2', label: '问一问V2' },
    // 重设计 mock 静态页（临时路由 #/A1V2R——与现状页并排对比，不覆盖现状页）。
    // DEBT(Owner)：去向 docs/runtime-refactor/frontend-redesign-设计.md §5 第 1 步。
    { key: 'A1V2R', label: '问一问V2·新版(mock)' },
    { key: 'A2', label: '井档案' },
    { key: 'A3', label: '数据变动审批', roles: ['aqiang', 'zhuren'] }
  ]},
  { group: '报告库', items: [
    { key: 'B1', label: '报告库' },
    { key: 'B2', label: '切片管理' },
    { key: 'B3', label: '常见问题' },
    { key: 'B4', label: '报告百科' },
    { key: 'B5', label: '关系图谱' }
  ]},
  { group: '指标与术语', items: [
    { key: 'C1', label: '指标与业务术语' },
    { key: 'C2', label: '语义修订提案池', roles: ['aqiang', 'zhuren'] },
    { key: 'C3', label: '发布流水线', roles: ['aqiang'] }
  ]},
  { group: '设置中心', items: [
    { key: 'D1', label: '模型与线路' },
    { key: 'D2', label: '搜索与回答' },
    { key: 'D3', label: '安全与权限' }
  ], roles: ['aqiang']},
  { group: '考核与质量', items: [
    { key: 'E1', label: '答题考核' },
    { key: 'E2', label: '数据质量台' },
    { key: 'E3', label: '知识体检' }
  ], roles: ['xiaoli', 'aqiang', 'zhuren']},
  { group: '平台', items: [
    { key: 'F1', label: '对外接口', roles: ['aqiang'] },
    { key: 'INDEX', label: '平台总览' }
  ]}
]

export function menuForRole(role) {
  return MENU
    .filter(g => !g.roles || g.roles.includes(role))
    .map(g => ({ ...g, items: g.items.filter(it => !it.roles || it.roles.includes(role)) }))
    .filter(g => g.items.length > 0)
}

export const PAGE_NAMES = Object.fromEntries(
  MENU.flatMap(g => g.items.map(it => [it.key, it.label]))
)
