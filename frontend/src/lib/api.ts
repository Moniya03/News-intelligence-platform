import {
  ChatResponse,
  Cluster,
  ClusterDetail,
  HealthResponse,
  SearchRequest,
  SearchResult,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 7000): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function requireSuccess(res: Response): Promise<void> {
  if (res.ok) return;
  const body = await res.json().catch(() => null);
  const detail = typeof body?.detail === "string" ? body.detail : res.statusText;
  throw new Error(`Request failed (${res.status}): ${detail}`);
}

export async function chatQuery(query: string, langFilter?: string[] | null): Promise<ChatResponse> {
  const res = await fetchWithTimeout(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      lang_filter: langFilter && langFilter.length > 0 ? langFilter : null,
    }),
  });
  await requireSuccess(res);
  return await res.json();
}

export async function searchArticles(req: SearchRequest): Promise<SearchResult[]> {
  const res = await fetchWithTimeout(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await requireSuccess(res);
  const data = await res.json();
  return (data?.results ?? data) as SearchResult[];
}

export async function getClusters(): Promise<Cluster[]> {
  const res = await fetchWithTimeout(`${API_URL}/api/clusters`, {
    method: "GET",
    headers: { "Accept": "application/json" },
  });
  await requireSuccess(res);
  const data = await res.json();
  return (data?.clusters ?? data) as Cluster[];
}

export async function getClusterDetail(id: number, page = 1, limit = 20): Promise<ClusterDetail> {
  const res = await fetchWithTimeout(`${API_URL}/api/clusters/${id}?page=${page}&limit=${limit}`, {
    method: "GET",
    headers: { "Accept": "application/json" },
  });
  await requireSuccess(res);
  return await res.json();
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetchWithTimeout(`${API_URL}/api/health`, { method: "GET" }, 3000);
    if (!res.ok) return { status: "unhealthy" };
    return await res.json();
  } catch {
    return { status: "offline" };
  }
}
