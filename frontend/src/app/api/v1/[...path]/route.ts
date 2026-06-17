import { NextRequest, NextResponse } from 'next/server';

// Read at request time — works correctly regardless of when the image was built.
const BACKEND = (process.env.BACKEND_URL || 'http://localhost:8004').replace(/\/$/, '');

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
    // Required for streaming request bodies (file uploads, SSE writes)
    ...(isBodyless ? {} : { duplex: 'half' }),
  } as RequestInit);

  // Stream the response body through unchanged (supports SSE and large payloads)
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

// Disable body size limit so file uploads pass through
export const config = { api: { bodyParser: false } };
