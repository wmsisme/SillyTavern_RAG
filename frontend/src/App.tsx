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
import LoginPage from './pages/LoginPage'
import AdminPage from './pages/AdminPage'
import RequireLogin from './components/RequireLogin'
import { AuthProvider } from './services/auth'

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
    <AuthProvider>
      <Routes>
        {/* 登录页不套主框架：未登录时不该看见侧边栏与页面骨架 */}
        <Route path="/login" element={<LoginPage />} />
        <Route element={<MainLayout />}>
          {/* 知识库搜索与工具箱对匿名开放 —— 这是路人不注册也能用的部分 */}
          <Route path="/" element={<HomePage />} />
          <Route path="/toolbox" element={<ToolboxPage />} />
          <Route path="/toolbox/:toolId" element={<ToolDetailPage />} />
          {/* 角色卡 / 世界书是私有数据：没登录就明说，而不是让接口回一串 401 */}
          <Route path="/cards" element={<RequireLogin><CardsPage /></RequireLogin>} />
          <Route path="/cards/:id" element={<RequireLogin><CardEditPage /></RequireLogin>} />
          <Route path="/cards/new" element={<RequireLogin><CardEditPage /></RequireLogin>} />
          <Route path="/worldbooks" element={<RequireLogin><WorldBooksPage /></RequireLogin>} />
          <Route path="/worldbooks/:id" element={<RequireLogin><WorldBookEditPage /></RequireLogin>} />
          <Route path="/worldbooks/new" element={<RequireLogin><WorldBookEditPage /></RequireLogin>} />
          {/* 后台管理：页内还会再判一次 is_admin（双保险），后端那几个接口本来也只放给管理员 */}
          <Route path="/admin" element={<RequireLogin><AdminPage /></RequireLogin>} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}

export default App
