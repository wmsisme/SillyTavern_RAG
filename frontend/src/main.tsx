import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App as AntdApp, ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import { installErrorReporting } from './services/errorReporter'
import './index.css'

// 在任何渲染之前装好错误上报：这样连 React 挂载阶段崩的错误也能被捕获
installErrorReporting()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* ConfigProvider：antd 内置文案（分页「条/页」、确认框按钮等）走中文 */}
    {/* AntdApp：提供 message/modal 的上下文，供各页面用 App.useApp() */}
    <ConfigProvider locale={zhCN}>
      <AntdApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
