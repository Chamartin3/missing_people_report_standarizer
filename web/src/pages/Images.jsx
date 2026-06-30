import { useEffect, useState } from 'react'
import { api, API } from '../api'
import { Loading, Empty, Badge, Pager, Chips, Modal } from '../components/ui'
import Review from '../components/Review'

const PAGE_SIZE = 24
const FILTERS = [['all', 'Todas'], ['true', 'Procesadas'], ['false', 'Pendientes']]

export default function Images() {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(0)
  const [filter, setFilter] = useState('all')
  const [review, setReview] = useState(null) // image_id being reviewed

  const load = () => {
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset: page * PAGE_SIZE })
    if (filter !== 'all') params.set('processed', filter)
    api(`/images?${params}`).then(setData)
  }
  useEffect(load, [page, filter])

  function closeReview() {
    setReview(null)
    load() // a processed image may have changed status
  }

  if (!data) return <Loading />
  const { images, total } = data
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Imágenes</h2>
        <Badge>{total} en total</Badge>
      </div>

      <Chips options={FILTERS} value={filter} onChange={(v) => { setFilter(v); setPage(0) }} />

      {!images.length ? (
        <Empty>Aún no hay imágenes.</Empty>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }}>
          {images.map((img) => (
            <figure key={img.id} className="card" style={{ margin: 0 }}>
              <button type="button" onClick={() => setReview(img.id)} title="Revisar imagen"
                style={{ padding: 0, border: 'none', background: 'none', cursor: 'pointer', display: 'block', width: '100%' }}>
                <img src={API + img.file_url} alt={`imagen ${img.id}`}
                  style={{ width: '100%', aspectRatio: 1, objectFit: 'cover', borderRadius: 8 }} />
              </button>
              <figcaption style={{ fontSize: 12, marginTop: 4 }}>
                <div>#{img.id} {img.source && `· ${img.source}`}</div>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <small>{(img.uploaded_at || '').slice(0, 16)}</small>
                  <Badge>{img.processed ? 'procesada' : 'pendiente'}</Badge>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      )}

      <Pager page={page} pageCount={pageCount} total={total} onChange={setPage} />

      {review != null && (
        <Modal onClose={closeReview} className="wide">
          <Review imageId={review} />
        </Modal>
      )}
    </div>
  )
}
