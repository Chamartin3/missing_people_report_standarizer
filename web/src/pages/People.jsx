import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { Loading, Empty, Badge, Modal } from '../components/ui'
import PersonForm, { statusLabel } from '../components/PersonForm'

const fullName = (p) =>
  p.display_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || `Persona #${p.id}`

// Sortable / filterable columns. `get` returns the cell's comparable value.
const COLUMNS = [
  { key: 'id', label: 'ID', get: (p) => p.id, width: 64 },
  { key: 'name', label: 'Nombre', get: fullName },
  { key: 'cedula', label: 'Cédula', get: (p) => p.cedula || '' },
  { key: 'current_location', label: 'Ubicación actual', get: (p) => p.current_location || '' },
  { key: 'last_seen', label: 'Visto por última vez', get: (p) => p.last_seen || '' },
  { key: 'status', label: 'Estatus', get: (p) => statusLabel(p.status) },
  { key: 'is_minor', label: 'Menor', get: (p) => (p.is_minor ? 'Sí' : ''), width: 70 },
]

export default function People() {
  const [persons, setPersons] = useState(null)
  const [sort, setSort] = useState({ key: 'id', dir: 'asc' })
  const [filters, setFilters] = useState({}) // column key -> substring
  const [creating, setCreating] = useState(false)

  const load = () => api('/persons').then((r) => setPersons(r.persons))
  useEffect(() => { load() }, [])

  function toggleSort(key) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))
  }

  async function createPerson(values) {
    await api('/persons', { method: 'POST', body: values })
    setCreating(false)
    load()
  }

  const rows = useMemo(() => {
    let r = persons || []
    for (const col of COLUMNS) {
      const needle = (filters[col.key] || '').trim().toLowerCase()
      if (needle) r = r.filter((p) => String(col.get(p)).toLowerCase().includes(needle))
    }
    const col = COLUMNS.find((c) => c.key === sort.key)
    r = [...r].sort((a, b) => {
      const av = col.get(a), bv = col.get(b)
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv), 'es', { numeric: true })
      return sort.dir === 'asc' ? cmp : -cmp
    })
    return r
  }, [persons, filters, sort])

  if (!persons) return <Loading />

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Personas ({rows.length})</h2>
        <button className="primary" onClick={() => setCreating(true)}>Nueva persona</button>
      </div>

      {!persons.length ? (
        <Empty>Aún no hay personas. Crea una o asígnale un rostro.</Empty>
      ) : (
        <table className="datatable">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th key={c.key} style={{ width: c.width, cursor: 'pointer' }} onClick={() => toggleSort(c.key)}>
                  {c.label}{sort.key === c.key ? (sort.dir === 'asc' ? ' ▲' : ' ▼') : ''}
                </th>
              ))}
            </tr>
            <tr>
              {COLUMNS.map((c) => (
                <th key={c.key} style={{ padding: 4 }}>
                  <input
                    placeholder="filtrar…"
                    value={filters[c.key] || ''}
                    onChange={(e) => setFilters((f) => ({ ...f, [c.key]: e.target.value }))}
                    style={{ width: '100%', fontSize: 12 }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td><small>#{p.id}</small></td>
                <td><Link to={`/person/${p.id}`}>{fullName(p)}</Link></td>
                <td>{p.cedula || <small>—</small>}</td>
                <td>{p.current_location || <small>—</small>}</td>
                <td>{p.last_seen || <small>—</small>}</td>
                <td><Badge>{statusLabel(p.status)}</Badge></td>
                <td>{p.is_minor && <Badge>menor</Badge>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {rows.length === 0 && persons.length > 0 && <Empty>Ningún resultado para el filtro.</Empty>}

      {creating && (
        <Modal onClose={() => setCreating(false)} className="form">
          <h2 style={{ margin: 0 }}>Nueva persona</h2>
          <PersonForm submitLabel="Crear" onSubmit={createPerson} onCancel={() => setCreating(false)} />
        </Modal>
      )}
    </div>
  )
}
