import { useState } from 'react'

// Case status options, shared with the list/detail views for Spanish labels.
export const STATUS_OPTIONS = [
  ['missing', 'Desaparecido'],
  ['searching', 'En búsqueda'],
  ['found', 'Encontrado'],
  ['reunited', 'Reunificado'],
  ['deceased', 'Fallecido'],
]
export const statusLabel = (s) => STATUS_OPTIONS.find(([v]) => v === s)?.[1] || s

const PERSONAL = [
  ['first_name', 'Nombre', 'Ej.: María'],
  ['last_name', 'Apellido', 'Ej.: González'],
  ['cedula', 'Cédula de identidad', 'Ej.: V-12345678'],
]
const LOCATION = [
  ['expected_location', 'Ubicación esperada', 'Ej.: ciudad o país de destino'],
  ['current_location', 'Ubicación actual', 'Ej.: dónde se encuentra ahora'],
  ['last_seen', 'Visto por última vez', 'Ej.: 12 mar 2026, Plaza Bolívar'],
]

// Shared person form for the "create" and "edit" modals, split into sections:
// personal info + (optional) location info. `initial` prefills it for editing.
export default function PersonForm({ initial = {}, submitLabel = 'Guardar', onSubmit, onCancel }) {
  const [v, setV] = useState({
    first_name: initial.first_name || '',
    last_name: initial.last_name || '',
    cedula: initial.cedula || '',
    expected_location: initial.expected_location || '',
    current_location: initial.current_location || '',
    last_seen: initial.last_seen || '',
    is_minor: !!initial.is_minor,
    status: initial.status || 'missing',
    notas: initial.notas || '',
  })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    try {
      await onSubmit(v)
    } finally {
      setBusy(false)
    }
  }

  const inputs = (rows) =>
    rows.map(([key, label, ph]) => (
      <label key={key} className="stack" style={{ gap: 2 }}>
        <small>{label}</small>
        <input value={v[key]} onChange={set(key)} placeholder={ph} />
      </label>
    ))

  return (
    <form onSubmit={submit} className="stack" style={{ gap: 14 }}>
      <fieldset className="stack" style={{ gap: 10, border: '1px solid var(--border)', borderRadius: 8, padding: 12 }}>
        <legend><strong>Información personal</strong></legend>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
          {inputs(PERSONAL)}
          <label className="stack" style={{ gap: 2 }}>
            <small>Estatus</small>
            <select value={v.status} onChange={set('status')}>
              {STATUS_OPTIONS.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
            </select>
          </label>
        </div>
        <label className="row" style={{ gap: 6 }}>
          <input type="checkbox" checked={v.is_minor}
            onChange={(e) => setV({ ...v, is_minor: e.target.checked })} />
          Menor de edad
        </label>
      </fieldset>

      <fieldset className="stack" style={{ gap: 10, border: '1px solid var(--border)', borderRadius: 8, padding: 12 }}>
        <legend>Información de ubicación <small>(opcional)</small></legend>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10 }}>
          {inputs(LOCATION)}
        </div>
      </fieldset>

      <label className="stack" style={{ gap: 2 }}>
        <small>Notas</small>
        <textarea rows={3} value={v.notas} onChange={set('notas')}
          placeholder="Cualquier detalle adicional" style={{ resize: 'vertical' }} />
      </label>

      <div className="row" style={{ justifyContent: 'flex-end' }}>
        {onCancel && <button type="button" className="ghost" onClick={onCancel}>Cancelar</button>}
        <button type="submit" className="primary" disabled={busy}>{submitLabel}</button>
      </div>
    </form>
  )
}
