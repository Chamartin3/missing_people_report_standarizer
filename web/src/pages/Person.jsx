import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, API } from '../api'
import { Loading, Empty, Badge, Modal } from '../components/ui'
import PersonForm, { statusLabel } from '../components/PersonForm'

const fullName = (p) =>
  p.display_name || [p.first_name, p.last_name].filter(Boolean).join(' ') || `Persona #${p.id}`

// Labelled person fields, shown only when they have a value.
const DETAILS = [
  ['cedula', 'Cédula de identidad'],
  ['expected_location', 'Ubicación esperada'],
  ['current_location', 'Ubicación actual'],
  ['last_seen', 'Visto por última vez'],
]

export default function Person() {
  const { id } = useParams()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [report, setReport] = useState({ kind: 'note', location: '', notes: '' })
  const [comment, setComment] = useState('')
  const [editing, setEditing] = useState(false)

  function load() {
    api(`/persons/${id}`).then(setData)
  }
  useEffect(load, [id])

  if (!data) return <Loading />
  if (data.error) return <Empty>{data.error}</Empty>
  const { person, faces, reports, comments } = data
  const imageIds = [...new Set(faces.map((f) => f.image_id))]

  async function addReport(e) {
    e.preventDefault()
    await api(`/persons/${id}/reports`, { method: 'POST', body: report })
    setReport({ kind: 'note', location: '', notes: '' })
    load()
  }
  async function addComment(e) {
    e.preventDefault()
    await api(`/persons/${id}/comments`, { method: 'POST', body: { body: comment } })
    setComment('')
    load()
  }
  async function saveEdit(values) {
    await api(`/persons/${id}`, { method: 'PATCH', body: values })
    setEditing(false)
    load()
  }
  async function archive() {
    if (!confirm('¿Archivar esta persona?')) return
    await api(`/persons/${id}/archive`, { method: 'POST' })
    nav('/people')
  }

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>
          {fullName(person)} <Badge>{statusLabel(person.status)}</Badge>
          {person.is_minor && <Badge> menor</Badge>}
        </h2>
        <div className="row">
          <button onClick={() => setEditing(true)}>Editar</button>
          <button onClick={archive} className="ghost">Archivar</button>
        </div>
      </div>

      {person.is_minor && (
        <p className="banner warn" style={{ marginTop: 12 }}>
          ⚠️ <strong>Menor de edad — persona de especial cuidado.</strong> La ubicación solo debe
          compartirse con sus representantes legales.
        </p>
      )}

      <dl className="details">
        {DETAILS.map(([key, label]) =>
          person[key] ? (
            <div key={key} className="row" style={{ gap: 8 }}>
              <dt style={{ color: 'var(--muted, #888)', minWidth: 160 }}>{label}</dt>
              <dd style={{ margin: 0 }}>{person[key]}</dd>
            </div>
          ) : null,
        )}
        {person.notas && (
          <div className="stack" style={{ gap: 2, marginTop: 4 }}>
            <dt style={{ color: 'var(--muted, #888)' }}>Notas</dt>
            <dd style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{person.notas}</dd>
          </div>
        )}
      </dl>

      <h3>Rostros ({faces.length})</h3>
      {faces.length === 0 ? (
        <Empty>Esta persona aún no tiene rostros asignados.</Empty>
      ) : (
        <div className="row">
          {faces.map((f) => (
            <figure key={f.id} className="face" style={{ margin: 0 }}>
              <img src={`${API}/faces/${f.id}/crop`} alt={`rostro ${f.id}`} />
              <figcaption>{f.confirmation}</figcaption>
            </figure>
          ))}
        </div>
      )}

      <h3>Imágenes de origen ({imageIds.length})</h3>
      <div className="row">
        {imageIds.map((iid) => (
          <a key={iid} href={`${API}/images/${iid}/file`} target="_blank" rel="noreferrer" title={`imagen #${iid}`}>
            <img src={`${API}/images/${iid}/file`} alt={`imagen ${iid}`}
              style={{ width: 120, height: 120, objectFit: 'cover', borderRadius: 8 }} />
          </a>
        ))}
      </div>

      <h3>Reportes ({reports.length})</h3>
      {reports.length > 0 && (
        <ul className="list">
          {reports.map((r) => (
            <li key={r.id} className="list-row">
              <b>{r.kind}</b> {r.location} — {r.notes} <small>{r.created_at}</small>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={addReport} className="row" style={{ marginTop: 8 }}>
        <select value={report.kind} onChange={(e) => setReport({ ...report, kind: e.target.value })}>
          <option value="note">nota</option>
        </select>
        <input placeholder="ubicación" value={report.location} onChange={(e) => setReport({ ...report, location: e.target.value })} />
        <input placeholder="notas" value={report.notes} onChange={(e) => setReport({ ...report, notes: e.target.value })} />
        <button type="submit" className="primary">Agregar reporte</button>
      </form>

      <h3>Comentarios ({comments.length})</h3>
      {comments.length > 0 && (
        <ul className="list">
          {comments.map((c) => (
            <li key={c.id} className="list-row">{c.body} <small>{c.created_at}</small></li>
          ))}
        </ul>
      )}
      <form onSubmit={addComment} className="row" style={{ marginTop: 8 }}>
        <input placeholder="comentario" value={comment} onChange={(e) => setComment(e.target.value)} style={{ flex: 1 }} />
        <button type="submit" className="primary">Agregar</button>
      </form>

      {editing && (
        <Modal onClose={() => setEditing(false)} className="form">
          <h2 style={{ margin: 0 }}>Editar persona</h2>
          <PersonForm initial={person} submitLabel="Guardar" onSubmit={saveEdit} onCancel={() => setEditing(false)} />
        </Modal>
      )}
    </div>
  )
}
