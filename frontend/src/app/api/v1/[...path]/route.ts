import { NextRequest, NextResponse } from 'next/server';

// Read at request time — correct regardless of when the image was built.
const BACKEND = (process.env.BACKEND_URL || 'http://localhost:8004').replace(/\/$/, '');

// Disable Next.js response caching — every request must reach the backend.
export const dynamic = 'force-dynamic';

async function proxy(req: NextRequest): Promise<NextResponse> {
  const path = req.nextUrl.pathname;   // /api/v1/...
  const search = req.nextUrl.search;
  const target = `${BACKEND}${path}${search}`;

  const headers = new Headers(req.headers);
  headers.delete('host');

  const isBodyless = ['GET', 'HEAD'].includes(req.method);

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body: isBodyless ? undefined : req.body,
    ...(isBodyless ? {} : { duplex: 'half' }),
  } as RequestInit);

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: upstream.headers,
  });
}

export const GET     = proxy;
export const POST    = proxy;
export const PUT     = proxy;
export const PATCH   = proxy;
export const DELETE  = proxy;
export const OPTIONS = proxy;
