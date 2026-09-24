import { Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import HomePage from './pages/HomePage'
import CardsPage from './pages/CardsPage'
import CardEditPage from './pages/CardEditPage'
import WorldBooksPage from './pages/WorldBooksPage'
import WorldBookEditPage from './pages/WorldBookEditPage'
import ToolboxPage from './pages/ToolboxPage'
import ToolDetailPage from './pages/ToolDetailPage'

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
      </Route>
    </Routes>
  )
}

export default App
