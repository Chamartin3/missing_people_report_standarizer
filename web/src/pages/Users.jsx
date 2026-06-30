import { useEffect, useState } from 'react'
import { api } from '../api'
import { Loading, Badge, Modal } from '../components/ui'

const ROLES = [['curator', 'Curador'], ['admin', 'Administrador']]
const roleLabel = (r) => ROLES.find(([v]) => v === r)?.[1] || r

function NewUserForm({ onCreate, onCancel }) {
  const [v, setV] = useState({ email: '', password: '', display_name: '', role: 'curator' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true); setErr(null)
    try {
      const res = await onCreate(v)
      if (res?.error) setErr(res.error)
    } catch (e) {
      setErr(String(e.message))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="stack" style={{ gap: 10 }}>
      <label className="stack" style={{ gap: 2 }}><small>Correo</small>
        <input type="email" value={v.email} onChange={set('email')} required /></label>
      <label className="stack" style={{ gap: 2 }}><small>Nombre para mostrar</small>
        <input value={v.display_name} onChange={set('display_name')} placeholder="opcional" /></label>
      <label className="stack" style={{ gap: 2 }}><small>Contraseña (mín. 6)</small>
        <input type="password" value={v.password} onChange={set('password')} required minLength={6} /></label>
      <label className="stack" style={{ gap: 2 }}><small>Rol</small>
        <select value={v.role} onChange={set('role')}>
          {ROLES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
        </select></label>
      {err && <p className="banner error" style={{ margin: 0 }}>{err}</p>}
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button type="button" className="ghost" onClick={onCancel}>Cancelar</button>
        <button type="submit" className="primary" disabled={busy}>Crear cuenta</button>
      </div>
    </form>
  )
}

export default function Users() {
  const [users, setUsers] = useState(null)
  const [creating, setCreating] = useState(false)

  const load = () => api('/users').then((r) => setUsers(r.users))
  useEffect(() => { load() }, [])

  async function createUser(values) {
    const res = await api('/users', { method: 'POST', body: values })
    if (!res.error) { setCreating(false); load() }
    return res
  }
  async function patch(id, body) {
    const res = await api(`/users/${id}`, { method: 'PATCH', body })
    if (res?.error) alert(res.error)
    load()
  }
  function resetPassword(id) {
    const pwd = prompt('Nueva contraseña para esta cuenta (mín. 6 caracteres):')
    if (pwd == null) return
    if (pwd.length < 6) return alert('La contraseña debe tener al menos 6 caracteres.')
    patch(id, { new_password: pwd })
  }

  if (!users) return <Loading />

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Usuarios ({users.length})</h2>
        <button className="primary" onClick={() => setCreating(true)}>Nueva cuenta</button>
      </div>

      <table className="datatable">
        <thead>
          <tr><th style={{ width: 56 }}>ID</th><th>Correo</th><th>Nombre</th><th>Rol</th><th>Estado</th><th style={{ width: 280 }}>Acciones</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td><small>#{u.id}</small></td>
              <td>{u.email}</td>
              <td>{u.display_name}</td>
              <td><Badge>{roleLabel(u.role)}</Badge></td>
              <td>{u.is_active ? '✅ activo' : '🚫 inactivo'}</td>
              <td>
                <div className="row" style={{ gap: 6 }}>
                  <select value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}>
                    {ROLES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
                  </select>
                  <button onClick={() => patch(u.id, { is_active: !u.is_active })}>
                    {u.is_active ? 'Desactivar' : 'Activar'}
                  </button>
                  <button onClick={() => resetPassword(u.id)}>Resetear clave</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {creating && (
        <Modal onClose={() => setCreating(false)} className="form">
          <h2 style={{ margin: 0 }}>Nueva cuenta</h2>
          <NewUserForm onCreate={createUser} onCancel={() => setCreating(false)} />
        </Modal>
      )}
    </div>
  )
}
