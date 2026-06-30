import { useEffect } from 'react'
import { API } from '../api'

// Base UI primitives shared across pages. Plain CSS classes live in styles.css.

// Centered overlay dialog. Click backdrop or press Escape to close.
export function Modal({ children, onClose, className = '' }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className={`modal card stack ${className}`} onClick={(e) => e.stopPropagation()}>
        <button className="ghost modal-close" onClick={onClose} aria-label="Close">✕</button>
        {children}
      </div>
    </div>
  )
}

export function Loading({ label = 'Loading…' }) {
  return (
    <div className="state">
      <div className="spinner" />
      {label}
    </div>
  )
}

export function Empty({ children }) {
  return <div className="state">{children}</div>
}

export function Badge({ children }) {
  return <span className="badge">{children}</span>
}

// Single-select filter chips. options: ['a','b'] or [['a','Label A'], ...].
export function Chips({ options, value, onChange }) {
  return (
    <div className="chips">
      {options.map((o) => {
        const [v, label] = Array.isArray(o) ? o : [o, o]
        return (
          <button key={v} type="button" className={`chip${value === v ? ' active' : ''}`} onClick={() => onChange(v)}>
            {label}
          </button>
        )
      })}
    </div>
  )
}

// Zero-based prev/next pager. Renders nothing for a single page.
export function Pager({ page, pageCount, total, onChange }) {
  if (pageCount <= 1) return null
  return (
    <div className="row" style={{ justifyContent: 'center', marginTop: 16 }}>
      <button disabled={page === 0} onClick={() => onChange(page - 1)}>‹ Prev</button>
      <small>Page {page + 1} / {pageCount}{total != null ? ` · ${total} total` : ''}</small>
      <button disabled={page >= pageCount - 1} onClick={() => onChange(page + 1)}>Next ›</button>
    </div>
  )
}

// Grid of image cards — used by Faces and Upload.
export function FaceGrid({ children }) {
  return <div className="grid">{children}</div>
}

// One face crop card: image on top, action UI as children below.
export function FaceCard({ faceId, cropUrl, children }) {
  return (
    <div className="card">
      <img src={API + cropUrl} alt={`face ${faceId}`} />
      {children}
    </div>
  )
}
