import { Routes, Route, useNavigate } from 'react-router-dom'
import { Button, Result } from 'antd'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'
import CardsPage from './pages/CardsPage'
import CardEditPage from './pages/CardEditPage'
import WorldBooksPage from './pages/WorldBooksPage'
import WorldBookEditPage from './pages/WorldBookEditPage'
import ToolboxPage from './pages/ToolboxPage'
import ToolDetailPage from './pages/ToolDetailPage'

// 原先没有兜底路由：访问未知地址会渲染一个只有顶栏的空壳，看不出哪里错了
function NotFound() {
  const navigate = useNavigate()
  return (
    <Result
      status="404"
      title="页面不存在"
      subTitle="你访问的地址没有对应页面"
      extra={<Button type="primary" onClick={() => navigate('/')}>回首页</Button>}
    />
  )
}

function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/cards" element={<CardsPage />} />
        <Route path="/cards/:id" element={<CardEditPage />} />
        <Route path="/cards/new" element={<CardEditPage />} />
        <Route path="/worldbooks" element={<WorldBooksPage />} />
        <Route path="/worldbooks/:id" element={<WorldBookEditPage />} />
        <Route path="/worldbooks/new" element={<WorldBookEditPage />} />
        <Route path="/toolbox" element={<ToolboxPage />} />
        <Route path="/toolbox/:toolId" element={<ToolDetailPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

export default App
