import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, App as AntApp } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import 'dayjs/locale/zh-cn'
import Shell from './shell/Shell.jsx'
import { antdTheme, applyCssVars } from './theme.js'
import './index.css'

// CSS 变量先于首帧渲染挂上——避免 body 底色与 antd 容器底色闪一帧割裂
applyCssVars()

ReactDOM.createRoot(document.getElementById('root')).render(
  <ConfigProvider locale={zhCN} theme={antdTheme}>
    <AntApp>
      <Shell />
    </AntApp>
  </ConfigProvider>
)
