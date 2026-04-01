import { NextRequest, NextResponse } from 'next/server'

import { getServerBackendBaseUrl } from '@/lib/server-backend-url'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/** Avoid dev rewrite proxy ECONNRESET on large/slow temporal responses. */
export async function GET(request: NextRequest) {
  const qs = request.nextUrl.searchParams.toString()
  const backend = getServerBackendBaseUrl()
  const url = `${backend}/api/temporal-data${qs ? `?${qs}` : ''}`

  const apiKey =
    request.headers.get('x-api-key') ||
    process.env.NEXT_PUBLIC_API_KEY ||
    'dev-local-key'

  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 120_000)

  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'X-API-Key': apiKey,
      },
      signal: ctrl.signal,
      cache: 'no-store',
    })

    const body = await res.text()
    return new NextResponse(body, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'application/json',
      },
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return NextResponse.json(
      { detail: `Temporal proxy failed: ${msg}` },
      { status: 502 }
    )
  } finally {
    clearTimeout(t)
  }
}
