import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, API } from '../api'
import AssignFace from './AssignFace'
import { statusLabel } from './PersonForm'
import { Loading, Badge, Empty } from './ui'

// Detail panel for one face, ordered: image → form → extracted text → faces.
// Unassigned: show the identify form + similar faces.
// Assigned: show the full person info instead of similars.
export default function FaceDetail({ faceId, persons = [], onChanged }) {
  const [data, setData] = useState(null)
  const [text, setText] = useState(null) // OCR of the source image
  const [personFull, setPersonFull] = useState(null) // full record once assigned
  const [selected, setSelected] = useState(() => new Set()) // similar faces to co-assign

  function load() {
    setData(null); setText(null); setPersonFull(null); setSelected(new Set())
    api(`/faces/${faceId}`).then((d) => {
      setData(d)
      api(`/images/${d.face.image_id}/text`).then((r) => setText(r.text)).catch(() => setText(''))
      if (d.person) api(`/persons/${d.person.id}`).then(setPersonFull)
    })
  }
  useEffect(load, [faceId])

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  if (!data) return <Loading />
  const { face, person, similar } = data
  const assignIds = [face.id, ...selected]

  // best similar match per existing person → quick-assign buttons
  const byPerson = new Map()
  for (const s of similar) {
    if (s.person_id == null) continue
    const cur = byPerson.get(s.person_id)
    if (!cur || s.similarity > cur.similarity) byPerson.set(s.person_id, s)
  }
  const candidates = [...byPerson.values()]

  return (
    <div className="stack">
      {/* 1 · the image, centered */}
      <div style={{ textAlign: 'center' }}>
        <img src={API + face.crop_url} alt={`face ${face.id}`} style={{ width: 200, borderRadius: 12, border: '1px solid var(--border)' }} />
        <div style={{ marginTop: 6 }}>
          <Badge>{face.confirmation}</Badge> <small>rostro #{face.id} · imagen #{face.image_id}</small>
        </div>
      </div>

      {/* 2 · the form (unassigned) or full person info (assigned) */}
      {person ? (
        <div className="stack" style={{ gap: 8 }}>
          <h3 style={{ margin: 0 }}>
            <Link to={`/person/${person.id}`}>{person.display_name || `Persona #${person.id}`}</Link>{' '}
            <Badge>{statusLabel(person.status)}</Badge>
            {personFull?.person?.is_minor && <Badge> menor</Badge>}
          </h3>
          {personFull && (
            <>
              <small>
                {personFull.faces.length} rostro(s) · {personFull.reports.length} reporte(s) · {personFull.comments.length} comentario(s)
              </small>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(64px, 1fr))' }}>
                {personFull.faces.map((f) => (
                  <img key={f.id} src={`${API}/faces/${f.id}/crop`} alt={`face ${f.id}`}
                    style={{ width: '100%', aspectRatio: 1, objectFit: 'cover', borderRadius: 6, border: '1px solid var(--border)' }} />
                ))}
              </div>
              <Link to={`/person/${person.id}`}>Abrir página completa de la persona →</Link>
            </>
          )}
        </div>
      ) : (
        <div className="stack" style={{ gap: 4 }}>
          <h3 style={{ margin: 0 }}>Identificar este rostro</h3>
          {selected.size > 0 && (
            <small>Asignando {assignIds.length} rostros (este + {selected.size} similares) a una persona.</small>
          )}
          <AssignFace
            faceId={face.id}
            candidates={candidates}
            persons={persons}
            onPersonsChanged={onChanged}
            onAssigned={async (_fid, personId) => {
              // Co-assign the similar faces the curator ticked as "misma persona".
              for (const sid of selected) {
                try {
                  await api(`/faces/${sid}/assign`, {
                    method: 'POST',
                    body: { person_id: personId, level: 'probable' },
                  })
                } catch { /* ignore a single failed co-assign */ }
              }
              onChanged?.()
              load()
            }}
          />
        </div>
      )}

      {/* 3 · extracted text section */}
      <div className="stack" style={{ gap: 4 }}>
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <span style={{ fontWeight: 600 }}>Texto extraído</span>
          <a href={API + face.image_url} target="_blank" rel="noreferrer"><small>imagen de origen ↗</small></a>
        </div>
        <textarea readOnly rows={4}
          value={text == null ? 'Extrayendo texto…' : text || '(no se encontró texto)'}
          style={{ width: '100%', fontFamily: 'inherit', resize: 'vertical' }} />
      </div>

      {/* origin image, collapsed by default */}
      <details>
        <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Ver imagen de origen</summary>
        <a href={API + face.image_url} target="_blank" rel="noreferrer">
          <img src={API + face.image_url} alt={`imagen ${face.image_id}`}
            style={{ width: '100%', borderRadius: 8, marginTop: 8, border: '1px solid var(--border)' }} />
        </a>
        <small>Clic en la imagen para abrirla en resolución completa.</small>
      </details>

      {/* 4 · faces list — similar faces, only while unassigned */}
      {!person && (
        <div>
          <h3 style={{ margin: '8px 0' }}>Rostros similares</h3>
          {similar.length === 0 ? (
            <Empty>No se encontraron rostros similares.</Empty>
          ) : (
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(90px, 1fr))' }}>
              {similar.map((s) => (
                <figure key={s.face_id} className="face" style={{ margin: 0, textAlign: 'center' }}>
                  <img src={API + s.crop_url} alt={`similar ${s.face_id}`}
                    style={{ width: '100%', aspectRatio: 1, objectFit: 'cover' }} />
                  <figcaption>
                    {(s.similarity * 100).toFixed(0)}%
                    {s.person_id != null ? (
                      <Link to={`/person/${s.person_id}`} style={{ display: 'block', fontSize: 12 }}>
                        {s.display_name || `#${s.person_id}`}
                      </Link>
                    ) : (
                      <label style={{ display: 'block', marginTop: 4, fontSize: 12 }}>
                        <input type="checkbox" checked={selected.has(s.face_id)} onChange={() => toggle(s.face_id)} /> misma persona
                      </label>
                    )}
                  </figcaption>
                </figure>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
