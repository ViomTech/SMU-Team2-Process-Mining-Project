// src/fetch-shim.ts
type ReqInfo = Request | string | URL;

const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, ""); // e.g. https://triplethreatx2.duckdns.org
const ORIGINAL_FETCH = window.fetch.bind(window);

function extractUrl(input: ReqInfo): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  if (input instanceof Request) return input.url;
  return String(input);
}

function mergeHeaders(a?: HeadersInit, b?: HeadersInit): HeadersInit | undefined {
  if (!a && !b) return undefined;
  const h = new Headers(a || {});
  if (b) new Headers(b).forEach((v, k) => h.set(k, v));
  return h;
}

function rewriteIfBackendPath(url: string): string {
  // leave absolute URLs / data / blob untouched
  if (/^(https?:|data:|blob:)/i.test(url)) return url;

  // normalise: /api/... or api/... → API_BASE + /api/...
  if (url.startsWith("/api/") || url.startsWith("api/")) {
    const tail = url.replace(/^\/?api\//, "api/");
    return `${API_BASE}/${tail}`;
  }

  // handle auth on the same backend (blueprint mounted at /auth)
  if (url.startsWith("/auth/") || url.startsWith("auth/")) {
    const tail = url.replace(/^\/?auth\//, "auth/");
    return `${API_BASE}/${tail}`;
  }

  // otherwise (static files, SPA routes) leave it alone
  return url;
}

window.fetch = (input: ReqInfo, init: RequestInit = {}) => {
  const originalUrl = extractUrl(input);
  const rewrittenUrl = rewriteIfBackendPath(originalUrl);

  // clone/merge options; always include cookies unless caller set them
  const next: RequestInit = { ...init };
  if (!next.credentials) next.credentials = "include";

  // preserve Request props if a Request object was passed
  if (input instanceof Request) {
    next.method ??= input.method;
    next.headers = mergeHeaders(input.headers, next.headers);
    if (next.body === undefined && input.body !== null) next.body = input.body as any;
  }

  // if caller passed a plain object as body, JSON-stringify + add header
  if (
    next.body &&
    typeof next.body === "object" &&
    !(next.body instanceof FormData) &&
    !(next.body instanceof Blob) &&
    // @ts-ignore
    !next.body.arrayBuffer
  ) {
    next.body = JSON.stringify(next.body);
    next.headers = mergeHeaders(next.headers, { "Content-Type": "application/json" });
  }

  return ORIGINAL_FETCH(rewrittenUrl, next);
};
