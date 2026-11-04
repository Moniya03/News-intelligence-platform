export type Language = "en" | "hi" | "bn" | "ta";

export interface Citation {
  chunk_id: string;
  article_id: string;
  title: string;
  lang: "en" | "hi" | "bn" | "ta" | string;
  source: string;
  url: string | null;
  snippet: string;
  veracity: "Likely reliable" | "Uncertain" | "Likely misleading";
  reason: string;
}

export interface Credibility {
  agreement_score: number; // 0.0 - 1.0
  agreement_label: string; // e.g. "High cross-source agreement"
}

export interface ChatRequest {
  query: string;
  lang_filter?: string[] | null; // ["en", "hi", "bn", "ta"]
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  credibility: Credibility;
}

export interface SearchRequest {
  query: string;
  lang_filter?: string[] | null;
  mode?: "hybrid" | "dense" | "bm25";
  top_k?: number;
}

export interface SearchResult {
  article_id: string;
  title: string;
  lang: string;
  source: string;
  category: string;
  snippet: string;
  score: number;
  url: string | null;
}

export interface ClusterLangCounts {
  en: number;
  hi: number;
  bn: number;
  ta: number;
  [key: string]: number;
}

export interface Cluster {
  id: number;
  label: string;
  size: number;
  lang_counts: ClusterLangCounts;
  top_terms: string[];
}

export interface ClusterArticle {
  article_id: string;
  title: string;
  lang: string;
  source: string;
  category: string;
  url: string | null;
}

export interface ClusterDetail {
  cluster: Cluster;
  articles: ClusterArticle[];
  total: number;
}

export interface HealthResponse {
  status: string;
  version?: string;
  models_loaded?: boolean;
}
