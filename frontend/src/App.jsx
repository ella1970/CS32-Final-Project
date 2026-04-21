// src/App.jsx
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import AthleteDashboard from './pages/AthleteDashboard'
import ResearchPortal from './pages/ResearchPortal'
import SessionPage from './pages/SessionPage'
import SubjectPage from './pages/SubjectPage'
import NewSession from './pages/NewSession'
import './index.css'

function Nav() {
  return (
    <nav className="nav">
      <div className="nav-brand">
        <span className="nav-logo">◎</span>
        <span className="nav-title">SwimLoad</span>
      </div>
      <div className="nav-links">
        <NavLink to="/" end className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>
          Dashboard
        </NavLink>
        <NavLink to="/research" className={({isActive}) => isActive ? 'nav-link active' : 'nav-link'}>
          Research Portal
        </NavLink>
        <NavLink to="/session/new" className="nav-link nav-cta">
          + New Session
        </NavLink>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Nav />
        <main className="main">
          <Routes>
            <Route path="/"                    element={<AthleteDashboard />} />
            <Route path="/research"            element={<ResearchPortal />} />
            <Route path="/session/new"         element={<NewSession />} />
            <Route path="/session/:sessionId"  element={<SessionPage />} />
            <Route path="/subject/:subjectId"  element={<SubjectPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
