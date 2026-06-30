import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'
import { Loading, Badge } from '../components/ui'

const roleLabel = (r) => (r === 'admin' ? 'Administrador' : 'Curador')

export default function Account() {
  const nav = useNavigate()
  const [me, setMe] = useState(null)
  const [profile, setProfile] = useState({ display_name: '', email: '' })
  const [pmsg, setPmsg] = useState(null) // profile save feedback
  const [pwd, setPwd] = useState({ current_password: '', new_password: '' })
  const [pwdMsg, setPwdMsg] = useState(null)

  useEffect(() => {
    api('/auth/me').then((u) => {
      setMe(u)
      setProfile({ display_name: u.display_name, email: u.email })
    })
  }, [])

  async function saveProfile(e) {
    e.preventDefault()
    setPmsg('saving')
    try {
      const res = await api('/auth/me', { method: 'PATCH', body: profile })
      setPmsg(res.error || 'saved')
      if (!res.error) setMe(res)
    } catch (err) {
      setPmsg(String(err.message))
    }
  }

  async function changePassword(e) {
    e.preventDefault()
    setPwdMsg('saving')
    try {
      const res = await api('/auth/password', { method: 'POST', body: pwd })
      setPwdMsg(res.error || 'saved')
      if (!res.error) setPwd({ current_password: '', new_password: '' })
    } catch (err) {
      setPwdMsg(String(err.message))
    }
  }

  function logout() {
    setToken(null)
    nav('/login')
  }

  if (!me) return <Loading />

  return (
    <div className="stack" style={{ maxWidth: 480, gap: 24 }}>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>Mi cuenta</h2>
        <Badge>{roleLabel(me.role)}</Badge>
      </div>

      <form onSubmit={saveProfile} className="card stack" style={{ gap: 10 }}>
        <strong>Perfil</strong>
        <label className="stack" style={{ gap: 2 }}><small>Nombre para mostrar</small>
          <input value={profile.display_name}
            onChange={(e) => setProfile({ ...profile, display_name: e.target.value })} /></label>
        <label className="stack" style={{ gap: 2 }}><small>Correo</small>
          <input type="email" value={profile.email}
            onChange={(e) => setProfile({ ...profile, email: e.target.value })} /></label>
        <div className="row">
          <button type="submit" className="primary" disabled={pmsg === 'saving'}>Guardar</button>
          {pmsg === 'saved' && <span className="badge">Guardado ✔</span>}
        </div>
        {pmsg && pmsg !== 'saving' && pmsg !== 'saved' && <p className="banner error" style={{ margin: 0 }}>{pmsg}</p>}
      </form>

      <form onSubmit={changePassword} className="card stack" style={{ gap: 10 }}>
        <strong>Cambiar contraseña</strong>
        <label className="stack" style={{ gap: 2 }}><small>Contraseña actual</small>
          <input type="password" value={pwd.current_password} required
            onChange={(e) => setPwd({ ...pwd, current_password: e.target.value })} /></label>
        <label className="stack" style={{ gap: 2 }}><small>Nueva contraseña (mín. 6)</small>
          <input type="password" value={pwd.new_password} required minLength={6}
            onChange={(e) => setPwd({ ...pwd, new_password: e.target.value })} /></label>
        <div className="row">
          <button type="submit" className="primary" disabled={pwdMsg === 'saving'}>Actualizar contraseña</button>
          {pwdMsg === 'saved' && <span className="badge">Actualizada ✔</span>}
        </div>
        {pwdMsg && pwdMsg !== 'saving' && pwdMsg !== 'saved' && <p className="banner error" style={{ margin: 0 }}>{pwdMsg}</p>}
      </form>

      <div><button className="ghost" onClick={logout}>Cerrar sesión</button></div>
    </div>
  )
}
