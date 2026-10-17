/**
 * mockLeft · 去夹具轮/去临时模块残留闸（specs/frontend-redesign.md「验收测试」表第 19 行）。
 *
 * 守什么（真流页转正后，页面临时面不再有夹具轮与临时 mock 模块）：
 * - landing/（含 redesign/ 与各测试文件）源码文本里**零**严禁字符串——临时 mock 轮的模块名与
 *   其导出名（本轮次的残留判据）；扫描面＝import.meta.glob 键集（在场文件），故文件路径也在判；
 * - 该模块文件本身已删（键集里不存在）；
 * - 真流页 A1V2R 的数据源只有本会话流与历史读口：引用 postAskV2（真提问）且不引用任何夹具轮。
 *
 * 本件的严禁字符串用**拼接字面量**写：本件自身也在被扫面内，直写会自命中判红。
 */
/** @vitest-environment node */
import { describe, expect, it } from 'vitest'

const SOURCES = import.meta.glob('../**/*.{js,jsx}', { query: '?raw', import: 'default', eager: true })

const BANNED = ['MOCK' + '_TURNS', 'mock' + 'Turns'] // 临时模块名与其导出名（新旧两种写法）
const BANNED_MODULE = ['mock' + 'Turns.js'] // 该模块文件名
const PAGE = './A1V2R.jsx' // glob 键形：本目录内＝'./X'，landing/ 顶层＝'../X'（vite 归一）

describe('mock/DEBT 清理（specs「验收测试」表第 19 行 no_mock_left）', () => {
  it('no_mock_left：landing/ 零夹具轮残留（含模块文件与文本引用）；真流页只走真提问与历史读口', () => {
    const files = Object.entries(SOURCES)
    expect(files.length).toBeGreaterThan(20) // 扫描面非空（glob 真跑起来——空面会让断言空转）
    expect(files.map(([path]) => path)).toContain(PAGE)

    const hits = []
    for (const [path, text] of files) {
      for (const s of [...BANNED, ...BANNED_MODULE]) {
        if (path.includes(s)) hits.push(`${path} :: 路径含 ${s}`)
        if (String(text).includes(s)) hits.push(`${path} :: 正文含 ${s}`)
      }
    }
    expect(hits).toEqual([])
    // 该模块文件本身已删（键集里不存在同名文件）
    expect(files.map(([path]) => path).some(p => BANNED_MODULE.some(s => p.endsWith(s)))).toBe(false)

    // 真流页：真提问接线在场 ＋ 不引夹具目录（页面临时面只喂真流/历史读口）
    const page = String(SOURCES[PAGE])
    expect(page).toContain('postAskV2')
    expect(page).not.toContain('__fixtures__')
  })
})
