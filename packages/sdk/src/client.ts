// Empty NEXT_PUBLIC_API_URL = same-origin (Next.js rewrites to API on VPS).
const API_URL =
  process.env.NEXT_PUBLIC_API_URL === undefined
    ? "http://localhost:8000"
    : process.env.NEXT_PUBLIC_API_URL;

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}
