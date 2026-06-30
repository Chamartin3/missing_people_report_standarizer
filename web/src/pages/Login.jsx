import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'

// Login only — there is no public signup. Accounts are created by an admin from
// the Usuarios page; the first admin comes from the startup seed.
export default function Login() {
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')

  async function submit(e) {
    e.preventDefault()
    setErr('')
    try {
      const res = await api('/auth/login', { method: 'POST', body: { email, password } })
      if (res.error) return setErr(res.error)
      setToken(res.token)
      nav('/dashboard')
    } catch (e) {
      setErr(String(e.message))
    }
  }

  return (
    <form onSubmit={submit} className="card stack" style={{ width: 320, margin: '80px auto' }}>
      <h1 style={{ textAlign: 'center', margin: '0 0 8px' }}>FaceFinder</h1>
      <input placeholder="correo" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="contraseña" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit" className="primary">Iniciar sesión</button>
      {err && <p className="banner error">{err}</p>}
    </form>
  )
}
