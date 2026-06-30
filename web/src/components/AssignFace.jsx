import { useState } from 'react'
import { api } from '../api'
import { Modal } from './ui'
import PersonForm from './PersonForm'

// Human-readable label that also carries the id.
export const personLabel = (p) =>
  `${p.display_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || `Persona`} · #${p.id}`

// Accent/case-insensitive fold so "maria sarahi" matches "MARÍA SARAHÍ".
// ponytail: native <datalist> can't do accent-folding, so we filter ourselves.
const norm = (s) => (s || '').normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase()

// One face → one person. Accent-insensitive autocomplete to pick an existing
// person, or create / fully edit a person inline without leaving the row.
export default function AssignFace({ faceId, candidates = [], persons = [], onAssigned, onPersonsChanged }) {
  const [busy, setBusy] = useState(false)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(null) // null | 'new' | person object
  const [assigned, setAssigned] = useState(null) // person once assigned

  const matches = query.trim()
    ? persons.filter((p) => norm(personLabel(p)).includes(norm(query))).slice(0, 8)
    : persons.slice(0, 8)

  // 'probable' is the only legal step from a freshly-suggested face.
  async function assign(person) {
    setBusy(true)
    setError(null)
    try {
      await api(`/faces/${faceId}/assign`, { method: 'POST', body: { person_id: person.id, level: 'probable' } })
      setAssigned(person)
      setQuery(personLabel(person))
      onAssigned?.(faceId, person.id)
    } catch (e) {
      setError(String(e.message))
    } finally {
      setBusy(false)
    }
  }

  async function savePerson(values) {
    if (editing === 'new') {
      const { person } = await api('/persons', { method: 'POST', body: values })
      setEditing(null)
      onPersonsChanged?.()
      await assign(person)
    } else {
      const { person } = await api(`/persons/${editing.id}`, { method: 'PATCH', body: values })
      setEditing(null)
      if (assigned?.id === person.id) setAssigned(person)
      onPersonsChanged?.()
    }
  }

  const named = candidates.filter((c) => c.person_id != null)
  const cleanName = (p) => personLabel(p).replace(/ · #\d+$/, '')

  return (
    <>
      <div className="grow stack" style={{ gap: 6, minWidth: 0 }}>
        <div className="row" style={{ flexWrap: 'nowrap', position: 'relative' }}>
          <input
            placeholder="Buscar y asignar persona…"
            value={query}
            disabled={busy}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
            onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
            style={{ flex: 1, minWidth: 0 }}
          />
          <button type="button" disabled={busy} onClick={() => setEditing('new')}>+ Nueva</button>
          {assigned && <button type="button" disabled={busy} onClick={() => setEditing(assigned)}>Editar</button>}
          {open && matches.length > 0 && (
            <ul style={{
              position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20, margin: '2px 0 0',
              padding: 0, listStyle: 'none', maxHeight: 220, overflowY: 'auto',
              background: 'var(--bg, #fff)', border: '1px solid var(--border)', borderRadius: 6,
              boxShadow: '0 4px 12px rgba(0,0,0,.12)',
            }}>
              {matches.map((p) => (
                <li key={p.id}>
                  <button type="button" disabled={busy}
                    onMouseDown={() => { setQuery(personLabel(p)); setOpen(false); assign(p) }}
                    style={{ display: 'block', width: '100%', textAlign: 'left', border: 0, background: 'none', padding: '6px 10px', cursor: 'pointer' }}>
                    {personLabel(p).replace(/ · #\d+$/, '')}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {named.length > 0 && !assigned && (
          <div className="row" style={{ gap: 6, fontSize: 12 }}>
            <small>Similares:</small>
            {named.map((c) => {
              const p = persons.find((x) => x.id === c.person_id)
              if (!p) return null
              return (
                <button key={c.person_id} type="button" disabled={busy} onClick={() => assign(p)}>
                  {cleanName(p)} ({Math.round(c.similarity * 100)}%)
                </button>
              )
            })}
          </div>
        )}

        {error && <small className="banner error" style={{ margin: 0 }}>{error}</small>}
      </div>

      {assigned ? (
        <span className="badge" style={{ background: '#dcfce7', color: '#166534', flexShrink: 0 }}>
          ✔ {cleanName(assigned)}
        </span>
      ) : (
        <span className="badge" style={{ flexShrink: 0 }}>sin asignar</span>
      )}

      {editing && (
        <Modal onClose={() => setEditing(null)} className="form">
          <h2 style={{ margin: 0 }}>{editing === 'new' ? 'Nueva persona' : 'Editar persona'}</h2>
          <PersonForm
            initial={editing === 'new' ? {} : editing}
            submitLabel={editing === 'new' ? 'Crear y asignar' : 'Guardar'}
            onSubmit={savePerson}
            onCancel={() => setEditing(null)}
          />
        </Modal>
      )}
    </>
  )
}
