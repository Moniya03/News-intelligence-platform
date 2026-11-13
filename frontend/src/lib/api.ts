import {
  CorpusResponse,
  HealthResponse,
  SearchRequest,
  SearchResponse,
  SummaryRequest,
  SummaryResponse,
  TopicDetail,
  TopicsResponse,
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

export async function searchArticles(req: SearchRequest): Promise<SearchResponse> {
  const res = await fetchWithTimeout(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await requireSuccess(res);
  return await res.json();
}

export async function summarizeSearch(req: SummaryRequest): Promise<SummaryResponse> {
  const res = await fetchWithTimeout(`${API_URL}/api/search/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  await requireSuccess(res);
  const response: SummaryResponse = await res.json();
  if (response.snapshot_id !== req.snapshot_id) {
    throw new Error("Summary snapshot changed. Run Search again before requesting a summary.");
  }
  return response;
}

export async function getClusters(): Promise<TopicsResponse> {
  const res = await fetchWithTimeout(`${API_URL}/api/clusters`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  await requireSuccess(res);
  return await res.json();
}

export async function getClusterDetail(id: number, page = 1, limit = 20): Promise<TopicDetail> {
  const res = await fetchWithTimeout(`${API_URL}/api/clusters/${id}?page=${page}&limit=${limit}`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  await requireSuccess(res);
  return await res.json();
}

export async function corpusSummary(): Promise<CorpusResponse> {
  const res = await fetchWithTimeout(`${API_URL}/api/corpus`, {
    method: "GET",
    headers: { Accept: "application/json" },
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
