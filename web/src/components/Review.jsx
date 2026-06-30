import { useEffect, useState } from 'react'
import { api, API } from '../api'
import AssignFace from './AssignFace'
import { Loading } from './ui'

const IMAGE_TYPES = [
  ['looking', 'Buscando a una persona'],
  ['status', 'Reportando el estado de una persona'],
  ['other', 'Otro'],
]
const typeLabel = (t) => IMAGE_TYPES.find(([v]) => v === t)?.[1] || t

// Review one stored image full-screen: image + its metadata on top, then one
// row per detected face, each assigned to a person via autocomplete.
export default function Review({ imageId }) {
  const [result, setResult] = useState(null)
  const [persons, setPersons] = useState([])
  const [assigned, setAssigned] = useState({}) // face_id -> person_id once assigned

  // Image-level info (replaces the old per-person Reporte modal).
  const [info, setInfo] = useState({ type: 'looking', source: '', contact: '', notes: '' })
  const [ocr, setOcr] = useState(null) // null | 'busy' | errorMessage
  const [saved, setSaved] = useState(null) // null | 'saving' | 'saved' | errorMessage

  const setField = (k) => (e) => setInfo((i) => ({ ...i, [k]: e.target.value }))
  const loadPersons = () => api('/persons').then((r) => setPersons(r.persons))

  useEffect(() => {
    api(`/images/${imageId}/process`, { method: 'POST' })
      .then(setResult)
      .catch((err) => setResult({ error: String(err.message) }))
    loadPersons()
  }, [imageId])

  async function extractText() {
    setOcr('busy')
    try {
      const { text } = await api(`/images/${imageId}/text`)
      setInfo((i) => ({ ...i, notes: [i.notes, text].filter(Boolean).join('\n') || '(no se encontró texto)' }))
      setOcr(null)
    } catch (err) {
      setOcr(String(err.message))
    }
  }

  // File the image info as one report per assigned person (reuses the report
  // endpoint; no dedicated image-metadata table).
  async function saveInfo() {
    const ids = [...new Set(Object.values(assigned))]
    if (!ids.length) return setSaved('Asigna al menos un rostro a una persona primero.')
    setSaved('saving')
    const notes = [`Tipo: ${typeLabel(info.type)}`, info.contact && `Contacto: ${info.contact}`, info.notes]
      .filter(Boolean)
      .join('\n')
    try {
      for (const personId of ids) {
        await api(`/persons/${personId}/reports`, {
          method: 'POST',
          body: { kind: 'note', location: info.source, notes, image_id: Number(imageId) },
        })
      }
      setSaved('saved')
    } catch (err) {
      setSaved(String(err.message))
    }
  }

  if (!result) return <Loading label="Detectando rostros…" />
  if (result.error) return <p className="banner error">{result.error}</p>

  const faces = result.faces || []
  const pending = faces.filter((f) => !assigned[f.face_id]).length

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div>
        <h2 style={{ margin: 0 }}>Revisar imagen #{imageId}</h2>
        <p style={{ margin: '4px 0 0' }}>Se detectaron {faces.length} rostro(s).</p>
      </div>

      {pending > 0 && (
        <p className="banner warn" style={{ margin: 0 }}>
          ⚠️ {pending} rostro(s) aún necesitan una persona — cada rostro debe pertenecer a alguien.
        </p>
      )}

      <img
        src={`${API}/images/${imageId}/file`}
        alt={`imagen original ${imageId}`}
        style={{ maxWidth: 480, maxHeight: '45vh', objectFit: 'contain', margin: '0 auto', borderRadius: 8, border: '1px solid var(--border)' }}
      />

      <fieldset className="stack" style={{ gap: 10, border: '1px solid var(--border)', borderRadius: 8, padding: 12 }}>
        <legend><strong>Información de la imagen</strong></legend>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
          <label className="stack" style={{ gap: 2 }}>
            <small>Tipo de imagen</small>
            <select value={info.type} onChange={setField('type')}>
              {IMAGE_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label className="stack" style={{ gap: 2 }}>
            <small>Fuente</small>
            <input value={info.source} onChange={setField('source')} placeholder="Ej.: WhatsApp, prensa, familiar" />
          </label>
          <label className="stack" style={{ gap: 2 }}>
            <small>Información de contacto</small>
            <input value={info.contact} onChange={setField('contact')} placeholder="Ej.: teléfono, correo" />
          </label>
        </div>

        <label className="stack" style={{ gap: 2 }}>
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <small>Texto extraído / notas</small>
            <button type="button" onClick={extractText} disabled={ocr === 'busy'}>
              {ocr === 'busy' ? 'Leyendo…' : 'Extraer texto de la imagen'}
            </button>
          </div>
          <textarea rows={4} value={info.notes} onChange={setField('notes')}
            placeholder="Escribe aquí o usa Extraer texto" />
        </label>
        {ocr && ocr !== 'busy' && <p className="banner error" style={{ margin: 0 }}>{ocr}</p>}

        <div className="row">
          <button type="button" className="primary" onClick={saveInfo} disabled={saved === 'saving'}>
            {saved === 'saving' ? 'Guardando…' : 'Guardar información'}
          </button>
          {saved === 'saved' && <span className="badge">Guardado ✔</span>}
        </div>
        {saved && !['saving', 'saved'].includes(saved) && <p className="banner error" style={{ margin: 0 }}>{saved}</p>}
      </fieldset>

      <h3 style={{ margin: 0 }}>Rostros</h3>
      <div className="facelist">
        {faces.map((f) => (
          <div key={f.face_id} className="face-row">
            <img src={API + f.crop_url} alt={`rostro ${f.face_id}`} />
            <AssignFace
              faceId={f.face_id}
              candidates={f.candidates}
              persons={persons}
              onAssigned={(faceId, personId) => setAssigned((a) => ({ ...a, [faceId]: personId }))}
              onPersonsChanged={loadPersons}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
