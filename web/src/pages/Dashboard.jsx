import { useEffect, useRef, useState } from 'react'
import { api, API } from '../api'
import { Loading, Modal } from '../components/ui'
import Review from '../components/Review'

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [dup, setDup] = useState(null) // { id, url } when an upload collides
  const [review, setReview] = useState(null) // image_id being reviewed
  const fileRef = useRef(null)

  const refresh = () => api('/dashboard').then(setData)
  useEffect(() => { refresh() }, [])

  async function store(file, force) {
    const form = new FormData()
    form.append('file', file)
    if (force) form.append('force', 'true')
    return api('/images', { method: 'POST', form })
  }

  async function onUpload(e) {
    e.preventDefault()
    const file = fileRef.current?.files[0]
    if (!file) return
    setBusy(true); setError(null); setDup(null)
    try {
      const res = await store(file, false)
      if (res.status === 'duplicate') setDup({ id: res.image_id, url: URL.createObjectURL(file) })
      else openReview(res.image_id)
    } catch (err) {
      setError(String(err.message))
    } finally {
      setBusy(false)
    }
  }

  async function uploadAsNew() {
    const file = fileRef.current?.files[0]
    if (!file) return
    setBusy(true)
    try {
      const res = await store(file, true)
      openReview(res.image_id)
    } catch (err) {
      setError(String(err.message))
    } finally {
      setBusy(false)
    }
  }

  function openReview(id) {
    setDup(null)
    setReview(id)
  }
  function closeReview() {
    setReview(null)
    if (fileRef.current) fileRef.current.value = ''
    refresh()
  }

  if (!data) return <Loading />

  const { images, faces_unassigned, people, recent } = data
  const pending = recent.filter((r) => !r.processed)

  return (
    <div className="stack">
      <h2 style={{ marginBottom: 4 }}>Panel</h2>

      <form onSubmit={onUpload} className="stack" style={{ alignItems: 'center', margin: '8px 0 8px' }}>
        <input ref={fileRef} type="file" name="file" accept="image/*" />
        <button type="submit" className="primary" disabled={busy}>
          {busy ? 'Subiendo…' : 'Subir imagen'}
        </button>
        {error && <p className="banner error">{error}</p>}
      </form>

      <div className="stats">
        <div className="stat">
          <div className="num">{images.total}</div>
          <div className="label">Imágenes cargadas</div>
          <div className="sub">{images.processed} procesadas · {images.unprocessed} sin procesar</div>
        </div>
        <div className={`stat${faces_unassigned > 0 ? ' warn' : ''}`}>
          <div className="num">{faces_unassigned}</div>
          <div className="label">Rostros sin persona</div>
          {faces_unassigned > 0 && <div className="sub">⚠️ asígnalos en la página de Rostros</div>}
        </div>
        <div className="stat">
          <div className="num">{people}</div>
          <div className="label">Personas</div>
        </div>
      </div>

      {pending.length > 0 && (
        <section style={{ marginTop: 24 }}>
          <h3>Pendientes de procesar</h3>
          <table className="datatable">
            <thead>
              <tr><th style={{ width: 64 }}>Imagen</th><th>Origen</th><th>Subida</th><th style={{ width: 100 }}></th></tr>
            </thead>
            <tbody>
              {pending.map((r) => (
                <tr key={r.id}>
                  <td><small>#{r.id}</small></td>
                  <td>{r.source || '—'}</td>
                  <td><small>{new Date(r.uploaded_at).toLocaleString()}</small></td>
                  <td><button className="ghost" onClick={() => openReview(r.id)}>Procesar →</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section style={{ marginTop: 24 }}>
        <h3>Actividad reciente</h3>
        {!recent.length ? (
          <p className="state">Aún no se ha subido nada. Sube una imagen arriba ↑</p>
        ) : (
          <table className="datatable">
            <thead>
              <tr><th style={{ width: 64 }}>Imagen</th><th>Estado</th><th>Origen</th><th>Subida</th></tr>
            </thead>
            <tbody>
              {recent.map((r) => (
                <tr key={r.id}>
                  <td><button className="ghost" onClick={() => openReview(r.id)}>#{r.id}</button></td>
                  <td>{r.processed ? '✅ procesada' : '⏳ sin procesar'}</td>
                  <td>{r.source || '—'}</td>
                  <td><small>{new Date(r.uploaded_at).toLocaleString()}</small></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {dup && (
        <Modal onClose={() => setDup(null)} className="wide">
          <h2 style={{ margin: 0 }}>⚠️ Esta imagen ya estaba cargada</h2>
          <p style={{ margin: 0 }}>
            Coincide con la imagen #{dup.id}. Compáralas — ¿es la misma o una nueva?
          </p>
          <div className="row" style={{ alignItems: 'flex-start' }}>
            <figure style={{ margin: 0, flex: 1 }}>
              <img src={dup.url} alt="recién seleccionada" style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border)' }} />
              <figcaption><small>Seleccionada ahora</small></figcaption>
            </figure>
            <figure style={{ margin: 0, flex: 1 }}>
              <img src={`${API}/images/${dup.id}/file`} alt={`existente ${dup.id}`} style={{ width: '100%', borderRadius: 8, border: '1px solid var(--border)' }} />
              <figcaption><small>Ya cargada · imagen #{dup.id}</small></figcaption>
            </figure>
          </div>
          <div className="row" style={{ justifyContent: 'center' }}>
            <button onClick={() => openReview(dup.id)}>Es la misma — revisar la #{dup.id}</button>
            <button className="primary" disabled={busy} onClick={uploadAsNew}>
              {busy ? 'Subiendo…' : 'Es nueva — subir de todos modos'}
            </button>
          </div>
        </Modal>
      )}

      {review != null && (
        <Modal onClose={closeReview} className="full">
          <Review imageId={review} />
        </Modal>
      )}
    </div>
  )
}
