import { useEffect, useState } from 'react'
import { api, API } from '../api'
import FaceDetail from '../components/FaceDetail'
import { Loading, Empty, Badge, Chips, Pager } from '../components/ui'

const PAGE_SIZE = 24
const ASSIGNED = [
  ['no', 'No identificados'],
  ['yes', 'Identificados'],
  ['all', 'Todos'],
]
const LEVELS = ['', 'suggested', 'probable', 'confirmed', 'disputed', 'rejected']

export default function Faces() {
  const [data, setData] = useState(null)
  const [persons, setPersons] = useState([])
  const [assigned, setAssigned] = useState('no')
  const [level, setLevel] = useState('')
  const [page, setPage] = useState(0)
  const [sel, setSel] = useState(null) // selected face id (detail on the side)

  function load() {
    const params = new URLSearchParams({ assigned, limit: PAGE_SIZE, offset: page * PAGE_SIZE })
    if (level) params.set('confirmation', level)
    api(`/faces?${params}`).then((d) => {
      setData(d)
      // keep selection if still in the list, else default to the first face
      setSel((cur) => (d.faces.some((f) => f.id === cur) ? cur : d.faces[0]?.id ?? null))
    })
  }
  useEffect(load, [assigned, level, page])
  useEffect(() => { api('/persons').then((r) => setPersons(r.persons)) }, [])

  if (!data) return <Loading />
  const { faces, total, unidentified } = data
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div className="row" style={{ justifyContent: 'space-between', marginBottom: 12 }}>
        <h2 style={{ margin: 0 }}>Rostros</h2>
        <Badge>{unidentified} sin identificar</Badge>
      </div>

      <div className="row" style={{ marginBottom: 16 }}>
        <Chips options={ASSIGNED} value={assigned} onChange={(v) => { setAssigned(v); setPage(0) }} />
        <select value={level} onChange={(e) => { setLevel(e.target.value); setPage(0) }} style={{ marginLeft: 'auto' }}>
          {LEVELS.map((l) => <option key={l} value={l}>{l || 'cualquier nivel'}</option>)}
        </select>
      </div>

      {!faces.length ? (
        <Empty>Ningún rostro coincide.</Empty>
      ) : (
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          {/* list */}
          <div style={{ width: 260, flexShrink: 0 }}>
            <ul className="facelist">
              {faces.map((f) => (
                <li key={f.id}>
                  <button type="button" className={`facelist-row${sel === f.id ? ' active' : ''}`} onClick={() => setSel(f.id)}>
                    <img src={API + f.crop_url} alt={`face ${f.id}`} />
                    <span className="stack" style={{ gap: 2, alignItems: 'flex-start' }}>
                      <small>rostro #{f.id}</small>
                      <Badge>{f.confirmation}</Badge>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
            <Pager page={page} pageCount={pageCount} total={total} onChange={setPage} />
          </div>

          {/* detail on the side */}
          <div className="card" style={{ flex: 1, minWidth: 0 }}>
            {sel != null
              ? <FaceDetail key={sel} faceId={sel} persons={persons} onChanged={load} />
              : <Empty>Selecciona un rostro de la lista.</Empty>}
          </div>
        </div>
      )}
    </div>
  )
}
