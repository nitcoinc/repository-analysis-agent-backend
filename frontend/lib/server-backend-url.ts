/**
 * Backend base URL for server-side fetches (Route Handlers, Server Components).
 * Mirrors logic in ``next.config.js`` ``resolveBackendBaseUrl`` so WSL → Windows host works.
 */
import fs from 'fs'

export function getServerBackendBaseUrl(): string {
  const explicit = process.env.API_PROXY_TARGET?.trim()
  if (explicit) return explicit.replace(/\/+$/, '')

  const publicUrl = process.env.NEXT_PUBLIC_API_URL?.trim()
  if (publicUrl) return publicUrl.replace(/\/+$/, '')

  const useWin =
    process.env.WSL_USE_WINDOWS_HOST === '1' ||
    process.env.WSL_USE_WINDOWS_HOST === 'true'
  if (useWin) {
    try {
      const text = fs.readFileSync('/etc/resolv.conf', 'utf8')
      const m = text.match(/^nameserver\s+(\d{1,3}(?:\.\d{1,3}){3})\s*$/m)
      if (m) return `http://${m[1]}:8000`
    } catch {
      /* not WSL or unreadable */
    }
  }

  return 'http://127.0.0.1:8000'
}
