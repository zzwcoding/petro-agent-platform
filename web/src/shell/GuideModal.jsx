import { Modal, Typography } from 'antd'

export default function GuideModal({ open, onClose, steps }) {
  return (
    <Modal title="演示导览 · 本页看点与点击顺序" open={open} onCancel={onClose} footer={null} width={560}>
      <Typography.Paragraph type="secondary" style={{ fontSize: 13 }}>
        按下面的顺序点，每步告诉你看什么。
      </Typography.Paragraph>
      <ol style={{ lineHeight: 2, paddingLeft: 20 }}>
        {steps.map((s, i) => <li key={i} style={{ marginBottom: 4 }}>{s}</li>)}
      </ol>
    </Modal>
  )
}
