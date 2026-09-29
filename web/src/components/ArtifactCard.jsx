/**
 * ArtifactCard —— 产物卡骨架（全局组件库首批，P0-06）。
 *
 * 合同形状来源：frontend-foundation.md §2.4 表「Artifact 产物卡 ← A1 端点 7/8
 * （kind/四步/current_step/预签名直链）」；A1-问一问.md 产物任务 DTO：
 *   { task_id, kind: 'ppt|img|audio', steps: 四步固定, current_step: 0 起索引,
 *     status: accepted|generating|stored|ready|failed, artifact?: {
 *       artifact_id, filename, download_url, url_policy, expires_at, trace } }
 * `ready` 才带 artifact（含 GET 预签名直链，小时级有效上限 7 天）。
 *
 * 本件为骨架：结构按合同 DTO 铺好，原型页暂不强制改用（P0-06 范围外），
 * A1 落地批（阶段 1）接真数据时按页面细节再加打磨。
 */

import { Alert, Card, Space, Steps, Tag, Typography } from 'antd'
import { DownloadOutlined, FileImageOutlined, FilePptOutlined, PlayCircleOutlined } from '@ant-design/icons'

/** 产物三 kind（PRD F10 三件套，合同冻结）。 */
const KIND_META = {
  ppt: { icon: <FilePptOutlined />, color: 'orange', label: 'PPT' },
  img: { icon: <FileImageOutlined />, color: 'blue', label: '图片' },
  audio: { icon: <PlayCircleOutlined />, color: 'purple', label: '语音' }
}

/** 任务状态 → 徽标（A1 五态；00 §5.1 同族）。 */
const STATUS_META = {
  accepted: { color: 'default', label: '已受理' },
  generating: { color: 'processing', label: '生成中' },
  stored: { color: 'processing', label: '已入库' },
  ready: { color: 'success', label: '可下载' },
  failed: { color: 'error', label: '失败' }
}

/**
 * 产物卡。
 * @param {{
 *   task: {task_id?: string, kind?: string, steps?: string[], current_step?: number,
 *          status?: string, artifact?: {artifact_id: string, filename: string,
 *          download_url: string, url_policy?: string, expires_at?: string, trace?: string}},
 *   reason?: string, failed 时的阶段定位＋人话原因（不发明错误码——B1 F32 红线同族）
 * }} props
 * @returns {JSX.Element}
 */
export default function ArtifactCard({ task, reason }) {
  const { kind = 'ppt', steps = [], current_step = 0, status = 'generating', artifact } = task || {}
  const meta = KIND_META[kind] || KIND_META.ppt
  const st = STATUS_META[status] || STATUS_META.generating

  return (
    <Card size="small" title={<Space>{meta.icon}<span>{artifact?.filename || `正在生成${meta.label}…`}</span><Tag color={meta.color}>{meta.label}</Tag><Tag color={st.color}>{st.label}</Tag></Space>}>
      {steps.length > 0 && (
        <Steps
          size="small"
          current={current_step}
          status={status === 'failed' ? 'error' : undefined}
          items={steps.map(label => ({ title: label }))}
        />
      )}
      {status === 'failed' && (
        <Alert style={{ marginTop: 12 }} type="error" showIcon
          message="产物生成失败" description={reason || '停在失败的步骤即可看到原因；可重试。'} />
      )}
      {status === 'ready' && artifact?.download_url && (
        <Space direction="vertical" size={2} style={{ marginTop: 12 }}>
          <Typography.Link href={artifact.download_url} target="_blank" rel="noreferrer">
            <DownloadOutlined /> 下载 {artifact.filename}
          </Typography.Link>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            直链{artifact.url_policy || '小时级有效（上限 7 天）'}{artifact.expires_at ? ` · 至 ${artifact.expires_at}` : ''}{artifact.trace ? ` · ${artifact.trace}` : ''}
          </Typography.Text>
        </Space>
      )}
    </Card>
  )
}
