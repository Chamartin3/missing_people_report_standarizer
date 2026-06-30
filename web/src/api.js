export const API = import.meta.env.VITE_API ?? 'http://localhost:8000'

export const token = () => localStorage.getItem('token')
export const setToken = (t) =>
  t ? localStorage.setItem('token', t) : localStorage.removeItem('token')

// One fetch wrapper: injects bearer token, JSON-encodes body, throws on non-2xx.
// Pass {form: FormData} for multipart (upload) — no Content-Type so the browser
// sets the boundary.
export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const t = token()
  if (t) headers.Authorization = `Bearer ${t}`

  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(API + path, { method, headers, body: payload })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.status === 204 ? null : res.json()
}
