// F1 对外接口 · API 凭证页签 —— 接口契约 + mock 实现（PRD F61）
// 契约文档：specs/api/F1-对外接口.md（本批只覆盖「API 凭证」页签；F1 其余页签待产品化批）
// 约定：mock 只在这一层；后端就绪后函数体换 fetch，签名与返回形状不变。

// ── 契约来源：PRD F61（对外凭证与 API Key 管理）· F48 五层 · F49 内外同权 · m1 verify_token/require_permission ──
// 语义红线：scoped Key 未声明的能力一律默认拒绝（fail-closed）；明文仅签发/轮换时返回一次，服务端只存指纹；
// full-access 等效全能力，签发限治理角色；轮换后旧 Key 立即失效；停用为终态。

export const KEY_SCOPES = [
  { key: 'context', name: '能看', full: '背景注入', desc: '背景资料自动带入问答' },
  { key: 'query', name: '能查', full: '自主查询', desc: '只读查数（白名单表＋限量＋按人过滤）' },
  { key: 'compute', name: '能算', full: '专业计算', desc: '专业计算工具' },
  { key: 'write', name: '能动', full: '写操作', desc: '受控写入口（对外默认不授予）' },
  { key: 'governance', name: '守规矩', full: '治理约束', desc: '口径以语义账为准；改定义只能提建议' }
]

const sleep = ms => new Promise(r => setTimeout(r, ms))
const pad = n => String(n).padStart(2, '0')
const isoLocal = d =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
const minutesAgo = m => isoLocal(new Date(Date.now() - m * 60000))
const randHex = n => Array.from({ length: n }, () => '0123456789abcdef'[Math.floor(Math.random() * 16)]).join('')

// ── mock 服务端状态 ──
const state = {
  keys: [
    {
      id: 'ak-9f2c7a', name: '上级单位 · 数据报送', scopes: ['context', 'query'], fullAccess: false,
      createdAt: minutesAgo(60 * 24 * 32), lastUsedAt: minutesAgo(26), status: 'active', hint: 'pa-****9f2c'
    },
    {
      id: 'ak-3b81de', name: '值班告警推送机器人', scopes: ['query', 'write'], fullAccess: false,
      createdAt: minutesAgo(60 * 24 * 9), lastUsedAt: minutesAgo(3), status: 'active', hint: 'pa-****3b81'
    },
    {
      id: 'ak-77c015', name: '旧版报送（已轮换）', scopes: ['context', 'query'], fullAccess: false,
      createdAt: minutesAgo(60 * 24 * 95), lastUsedAt: minutesAgo(60 * 24 * 2), status: 'rotated', hint: 'pa-****77c0'
    }
  ]
}

const findKey = id => state.keys.find(k => k.id === id)

// GET /api/keys —— 凭证清单（创建时间倒序；只含脱敏 hint，永不回明文）
export async function listKeys() {
  await sleep(150)
  return { keys: [...state.keys].sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1)) }
}

// POST /api/keys —— 签发；返回体含 plaintext（明文仅此一次，服务端只存指纹）
export async function createKey({ name, scopes, fullAccess = false }) {
  await sleep(350)
  const trimmed = (name || '').trim()
  if (!trimmed) throw new Error('凭证名称必填')
  if (!fullAccess && (!Array.isArray(scopes) || scopes.length === 0)) {
    throw new Error('至少勾选一项能力（或选择 full-access）')
  }
  const id = `ak-${randHex(6)}`
  const record = {
    id, name: trimmed,
    scopes: fullAccess ? KEY_SCOPES.map(s => s.key) : [...scopes],
    fullAccess: !!fullAccess,
    createdAt: isoLocal(new Date()), lastUsedAt: null, status: 'active',
    hint: `pa-****${id.slice(3)}`
  }
  state.keys.unshift(record)
  return { key: { ...record }, plaintext: `pa-live-${randHex(24)}` }
}

// POST /api/keys/{id}/rotate —— 轮换；旧 Key 立即失效（status=rotated），新 Key 返回明文一次
export async function rotateKey(id) {
  await sleep(300)
  const old = findKey(id)
  if (!old) throw new Error('凭证不存在')
  if (old.status === 'revoked') throw new Error('已停用的凭证不能轮换（终态）')
  old.status = 'rotated'
  const record = {
    id: `ak-${randHex(6)}`, name: old.name.replace(/（已轮换）$/, ''),
    scopes: [...old.scopes], fullAccess: old.fullAccess,
    createdAt: isoLocal(new Date()), lastUsedAt: null, status: 'active',
    hint: `pa-****${randHex(4)}`
  }
  record.hint = `pa-****${record.id.slice(3)}`
  state.keys.unshift(record)
  return { key: { ...record }, rotatedFrom: old.id, plaintext: `pa-live-${randHex(24)}` }
}

// DELETE /api/keys/{id} —— 停用（终态；泄露/下线的处置动作，立即失效）
export async function revokeKey(id) {
  await sleep(250)
  const k = findKey(id)
  if (!k) throw new Error('凭证不存在')
  if (k.status !== 'active') throw new Error('仅启用中的凭证可停用')
  k.status = 'revoked'
  return { key: { ...k } }
}
