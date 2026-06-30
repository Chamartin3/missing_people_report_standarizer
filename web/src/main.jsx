import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import {
  createBrowserRouter,
  RouterProvider,
  NavLink,
  Outlet,
  Navigate,
  useNavigate,
} from 'react-router-dom'
import { api, token, setToken } from './api'
import './styles.css'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import People from './pages/People'
import Faces from './pages/Faces'
import Person from './pages/Person'
import Images from './pages/Images'
import Users from './pages/Users'
import Account from './pages/Account'

function Layout() {
  const nav = useNavigate()
  const [me, setMe] = useState(null)
  // Token can go stale (expired/revoked) — if /auth/me fails, force re-login.
  useEffect(() => {
    if (!token()) return
    api('/auth/me').then(setMe).catch(() => { setToken(null); nav('/login') })
  }, [])
  if (!token()) return <Navigate to="/login" replace />
  const logout = () => {
    setToken(null)
    nav('/login')
  }
  return (
    <div className="app">
      <nav className="nav">
        <NavLink to="/dashboard" style={{ fontWeight: 700, color: 'var(--accent)' }}>Estandarizador</NavLink>
        <NavLink to="/dashboard">Panel</NavLink>
        <NavLink to="/people">Personas</NavLink>
        <NavLink to="/faces">Rostros</NavLink>
        <NavLink to="/images">Imágenes</NavLink>
        {me?.role === 'admin' && <NavLink to="/users">Usuarios</NavLink>}
        <span style={{ marginLeft: 'auto' }} />
        <NavLink to="/account">{me ? me.display_name : 'Cuenta'}</NavLink>
        <button onClick={logout} className="ghost">Salir</button>
      </nav>
      <Outlet />
    </div>
  )
}

const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'people', element: <People /> },
      { path: 'faces', element: <Faces /> },
      { path: 'images', element: <Images /> },
      { path: 'person/:id', element: <Person /> },
      { path: 'users', element: <Users /> },
      { path: 'account', element: <Account /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
