import { useState } from 'react'
import Dashboard from './pages/Dashboard'
import Employees from './pages/Employees'
import './styles/access.css'

export default function App() {
  const [page, setPage] = useState('dashboard')
  return (
    <>
      <nav className="access-nav" aria-label="Navigation principale">
        <span className="access-nav__brand">SENTINEL-X</span>
        <button type="button" aria-current={page === 'dashboard' ? 'page' : undefined} onClick={() => setPage('dashboard')}>Supervision</button>
        <button type="button" aria-current={page === 'employees' ? 'page' : undefined} onClick={() => setPage('employees')}>Employés & badges</button>
      </nav>
      {page === 'dashboard' ? <Dashboard /> : <Employees />}
    </>
  )
}
