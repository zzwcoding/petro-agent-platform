/**
 * V2 决策树结构自检（pages/DecisionTreeV2）——树/路径/场景三方一致性：
 * - 每条场景路径引用的节点 key 必须真实存在于树上（高亮集合闭世界）；
 * - 每个场景 key 必须有 PATHS 条目（byKey[n.sc] 弹窗 tag 不悬空）；
 * - 树上每个带 sc 的叶节点，其场景 key 必须在册（routeOf/TREE_BY_KEY 闭世界）；
 * - routeOf 词面真值抽测：kw 常量取自 appv2/tools/precondition.py 真词面。
 * 另附渲染冒烟（active 命中/highlight pathSet 不抛错）。
 */

/** @vitest-environment jsdom */
import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import DecisionTreeV2, { V2_PATHS, V2_ROOT, V2_SCENARIOS } from './DecisionTreeV2.jsx'

if (!window.matchMedia) {
  window.matchMedia = query => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn()
  })
}

function walkKeys(node, acc = new Set()) {
  acc.add(node.key)
  for (const c of node.children || []) walkKeys(c, acc)
  return acc
}
function walkScLeaves(node, acc = []) {
  if (node.sc) acc.push({ key: node.key, sc: node.sc })
  for (const c of node.children || []) walkScLeaves(c, acc)
  return acc
}

const NODE_KEYS = walkKeys(V2_ROOT)

describe('V2 决策树 · 结构一致性', () => {
  it('每条场景路径引用的节点都在树上（路径闭世界）', () => {
    for (const [sc, path] of Object.entries(V2_PATHS)) {
      for (const k of path) {
        expect(NODE_KEYS.has(k), `场景 ${sc} 引用了树上不存在的节点 ${k}`).toBe(true)
      }
    }
  })

  it('每个带 sc 的叶节点其场景都在册（场景表闭世界）', () => {
    const scKeys = new Set(V2_SCENARIOS.map(s => s.key))
    for (const leaf of walkScLeaves(V2_ROOT)) {
      expect(scKeys.has(leaf.sc), `节点 ${leaf.key} 的 sc=${leaf.sc} 不在 V2_SCENARIOS`).toBe(true)
    }
  })

  it('每个场景 key 都有 PATHS 条目且根 T0 不必显式列入（组件自动并入）', () => {
    for (const s of V2_SCENARIOS) {
      expect(Array.isArray(V2_PATHS[s.key]) && V2_PATHS[s.key].length > 0,
        `场景 ${s.key} 缺 PATHS 条目`).toBe(true)
    }
  })

  it('节点/场景规模锚（防误删）：38 节点 · 19 场景（V2-80 词面阀/直答/四场景入图）', () => {
    expect(NODE_KEYS.size).toBe(38)
    expect(V2_SCENARIOS.length).toBe(19)
  })

  it('kw 词面真值抽测（词源＝precondition.py 真常量）', () => {
    const routeOf = text => {
      const t = (text || '').toLowerCase()
      let best = null, bestPri = Infinity
      for (const s of V2_SCENARIOS) {
        if (!s.kw.some(k => t.includes(k.toLowerCase()))) continue
        if (s.pri < bestPri) { best = s; bestPri = s.pri }
      }
      return best ? best.key : null
    }
    expect(routeOf('「产量完成率」以前叫什么名字')).toBe('ban-exempt')
    expect(routeOf('最近的产量情况怎么样')).toBe('engine-ask')
    expect(routeOf('各区块产量和 ERP 台账对一下')).toBe('extable')
    expect(routeOf('本月产量是否达标')).toBe('caliber')
    expect(routeOf('渤南区块本月产油量')).toBe('data-clean')
  })
})

describe('V2 决策树 · 渲染冒烟', () => {
  it('active 命中/未命中两态渲染不抛错，主干节点在文档中', () => {
    const byKey = Object.fromEntries(V2_SCENARIOS.map(s => [s.key, s]))
    const { unmount } = render(<DecisionTreeV2 byKey={byKey} active="data-clean" />)
    expect(document.querySelectorAll('foreignObject').length).toBe(38)
    unmount()
    const { unmount: unmount2 } = render(<DecisionTreeV2 byKey={byKey} active={null} />)
    expect(document.querySelectorAll('foreignObject').length).toBe(38)
    unmount2()
  })
})
