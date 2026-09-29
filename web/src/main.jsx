import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntApp, theme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import 'dayjs/locale/zh-cn'
import Shell from './shell/Shell.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.darkAlgorithm,
      token: { colorPrimary: '#4a9dff', borderRadius: 6, fontSize: 14 },
      components: { Layout: { siderBg: '#0b2e59', triggerBg: '#0b2e59', headerBg: '#141414' } }
    }}
  >
    <AntApp>
      <Shell />
    </AntApp>
  </ConfigProvider>
)
