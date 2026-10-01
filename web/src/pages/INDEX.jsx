import { useEffect, useState } from 'react'
import { Card, List, Tag, Tooltip } from 'antd'
import {
  AlertOutlined, ApartmentOutlined, ApiOutlined, AuditOutlined, BarChartOutlined,
  BookOutlined, BulbOutlined, CheckSquareOutlined, CloudOutlined,
  DatabaseOutlined, FileDoneOutlined, FileSearchOutlined, FileTextOutlined,
  LockOutlined, MedicineBoxOutlined, MessageOutlined,
  ProfileOutlined, QuestionCircleOutlined, SafetyCertificateOutlined, SearchOutlined, ToolOutlined
} from '@ant-design/icons'
import { ROLES, menuForRole } from '../roles.js'

window.__traces = Object.assign(window.__traces || {}, {
  INDEX: '总导航 · F48 治理约束 · DESIGN.md §1 G0 行'
})

const helpIcon = content => (
  <Tooltip title={<div style={{ fontSize: 12, lineHeight: 1.8 }}>{content}</div>} placement="topLeft">
    <QuestionCircleOutlined style={{ marginLeft: 4, color: '#8a94a3', cursor: 'help' }} />
  </Tooltip>
)

// 当前角色从顶栏角色选择器读取（Shell 持有该状态；切换后本页随之重渲染）
const ROLE_KEY_BY_LABEL = Object.fromEntries(ROLES.map(r => [r.label, r.key]))
function readHeaderRole() {
  const els = document.querySelectorAll('.ant-layout-header .ant-select-selection-item')
  for (const el of els) {
    const key = ROLE_KEY_BY_LABEL[(el.textContent || '').trim()]
    if (key) return key
  }
  return 'aqiang'
}

// 平台家底：沿用本页原有四个统计
const STATS = [
  { label: '采油井', value: 86, icon: <ToolOutlined /> },
  { label: '注水井', value: 34, icon: <DatabaseOutlined /> },
  { label: '在库报告', value: 1247, icon: <FileSearchOutlined /> },
  { label: '本月待办', value: 3, icon: <AuditOutlined /> }
]

// 各入口一句话（取自各页页头既有说明）；roles＝该待办/入口对角色的可见规则（与 roles.js MENU 同口径）
const PAGES = {
  A1: { icon: <MessageOutlined />, color: '#1677ff', desc: '问报告 / 问数据 / 做汇报' },
  A2: { icon: <ProfileOutlined />, color: '#0b7a5c', desc: '一口井一页看全' },
  A3: { icon: <AuditOutlined />, color: '#d97706', desc: '低风险自动执行 · 高风险人工终审' },
  B1: { icon: <FileSearchOutlined />, color: '#7c4dff', desc: '入库 / 索引 / 出处' },
  B2: { icon: <FileTextOutlined />, color: '#7c4dff', desc: '切片浏览、标记与修正' },
  B3: { icon: <BulbOutlined />, color: '#7c4dff', desc: '常问问题直接秒回' },
  B4: { icon: <BookOutlined />, color: '#7c4dff', desc: '报告自动重写成中文百科页' },
  B5: { icon: <ApartmentOutlined />, color: '#7c4dff', desc: '对象关系图，原文有依据才建边' },
  C1: { icon: <BarChartOutlined />, color: '#0b7a5c', desc: '四本账：术语 / 指标 / 对象与关系 / 工作流' },
  C2: { icon: <FileDoneOutlined />, color: '#d97706', desc: '平台只提建议，合并由人批准' },
  C3: { icon: <SafetyCertificateOutlined />, color: '#d97706', desc: '五道检查，一道不过即停' },
  D1: { icon: <ApiOutlined />, color: '#1677ff', desc: '主用故障自动切备用，每次调用有账；花费聚合与预算阈值也在这' },
  D2: { icon: <SearchOutlined />, color: '#1677ff', desc: '检索与作答的规矩' },
  D3: { icon: <LockOutlined />, color: '#1677ff', desc: '四件全开才放行，没配权限＝没有入口' },
  D6: { icon: <DatabaseOutlined />, color: '#1677ff', desc: '原样进来 · 洗净 · 拼成问数大表' },
  E1: { icon: <CheckSquareOutlined />, color: '#d97706', desc: '考核题库 / 跑批评分 / 判分导出' },
  E2: { icon: <AlertOutlined />, color: '#d97706', desc: '质检任务 / 问题单' },
  E3: { icon: <MedicineBoxOutlined />, color: '#d97706', desc: '只出评分与建议，人不确认不改' },
  F1: { icon: <CloudOutlined />, color: '#8a94a3', desc: '外部系统接入：同一套安检 · 大结果只给凭证' }
}

// 业务区说明（收敛到分区标题旁 ?）
const AREA_HELP = {
  工作台: '日常处理业务的地方：向平台提问、查井档案、审批数据变动。开工先来这。',
  报告库: '报告从入库到使用的全链路：入库建索引、管切片、看百科页与关系图谱。找报告、核对切片质量时来这。',
  指标与术语: '管口径的账本：指标与术语台账、修订提案池、发布前安检。对口径有疑问、要改定义时来这。',
  设置中心: '平台自身的配置与运行：模型线路（含花费聚合与预算阈值、观测入口）、检索规矩、安全权限、数据接入。只对运维角色开放。',
  考核与质量: '定期体检三件事：考核平台答得准不准，质检数据干不干净，体检知识底子全不全。',
  平台: '给外部系统用的接口：外部 AI 和内部用户同一套安检，大结果只给凭证不给正文。'
}

// 待办：沿用本页原有三条；E2/C2 两条按 MENU 角色规则显示（与该页菜单可见性同口径）
const TODOS = [
  { tag: '问题单', color: 'orange', text: '质检问题单 3 项待认领（最新 #QT-20260915-01）', link: '#/E2', roles: ['xiaoli', 'aqiang', 'zhuren'] },
  { tag: '待审批', color: 'blue', text: '修改提案 2 条等待审批（含「递减增油」口径争议）', link: '#/C2', roles: ['aqiang', 'zhuren'] },
  { tag: '口径', color: 'red', text: '「有效产量」一词两译待确认默认口径', link: '#/C1' }
]

export default function Index() {
  const [role, setRole] = useState(readHeaderRole)

  // 每次渲染后核对顶栏角色（切换角色会触发本页重渲染，这里把最新角色同步进来）
  useEffect(() => {
    const k = readHeaderRole()
    setRole(prev => (prev === k ? prev : k))
  })

  const groups = menuForRole(role)
    .map(g => ({ ...g, items: g.items.filter(it => it.key !== 'INDEX') }))
    .filter(g => g.items.length > 0)
  const todos = TODOS.filter(t => !t.roles || t.roles.includes(role))

  return (
    <div>
      <Card
        title={<span>平台家底{helpIcon(<>登录后先看这里：一行家底数，下面按业务区放好各功能入口，待办提醒今天该处理的事。<br />没给你开的区不显示——不是被拒绝，是界面上没有入口。</>)}</span>}
        extra={<span style={{ color: '#8a94a3', fontSize: 12 }}>渤海油田分公司 · 3 作业区 · 120 口在产井</span>}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px 48px' }}>
          {STATS.map(s => (
            <div key={s.label} style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 16, color: '#8a94a3' }}>{s.icon}</span>
              <span style={{ fontSize: 24, fontWeight: 600, lineHeight: 1 }}>{s.value}</span>
              <span style={{ fontSize: 12, color: '#8a94a3' }}>{s.label}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card
        title={`待办（${todos.length}）`}
        style={{ marginTop: 16 }}
        extra={<span style={{ color: '#8a94a3', fontSize: 12 }}>点一条直达要处理的页面{helpIcon(<>列的是当前角色该处理的事，只显示你职责内的待办。</>)}</span>}
      >
        <List
          dataSource={todos}
          renderItem={t => (
            <List.Item style={{ padding: '8px 0' }}>
              <List.Item.Meta
                avatar={<Tag color={t.color}>{t.tag}</Tag>}
                title={<a href={t.link}>{t.text}</a>}
              />
            </List.Item>
          )}
        />
      </Card>

      {groups.map(g => (
        <Card
          key={g.group}
          style={{ marginTop: 16 }}
          title={<span>{g.group}（{g.items.length}）{helpIcon(AREA_HELP[g.group])}</span>}
        >
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 8 }}>
            {g.items.map(it => {
              const p = PAGES[it.key]
              if (!p) return null
              return (
                <a key={it.key} href={'#/' + it.key} className="home-entry">
                  <span style={{ fontSize: 18, color: p.color, lineHeight: 1.2 }}>{p.icon}</span>
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>{it.label}</span>
                    <span style={{ display: 'block', fontSize: 12, color: '#8a94a3', marginTop: 2 }}>{p.desc}</span>
                  </span>
                </a>
              )
            })}
          </div>
        </Card>
      ))}
    </div>
  )
}
