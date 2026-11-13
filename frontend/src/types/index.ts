export type Language = "en" | "hi" | "bn" | "mr";
export type SearchMode = "hybrid" | "dense" | "bm25";

export interface SearchRequest {
  query: string;
  lang_filter?: Language[] | null;
  mode?: SearchMode;
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
  published_at?: string | null;
  snapshot_id: string;
}

export interface SearchResponse {
  results: SearchResult[];
  metadata: {
    snapshot_id: string;
    requested_mode: SearchMode;
    executed_mode: SearchMode;
    reranker_status: "disabled" | "applied" | "unavailable";
    elapsed_ms: number;
  };
}

export interface Topic {
  id: number;
  label: string;
  size: number;
  lang_counts: Record<string, number>;
  source_counts: Record<string, number>;
  top_terms: string[];
  representative_article_ids: string[];
}

export interface TopicsResponse {
  snapshot_id: string;
  run_id: string | null;
  settings_hash: string | null;
  algorithm: string | null;
  topic_count: number;
  outlier_count: number;
  clusters: Topic[];
}

export interface TopicArticle {
  article_id: string;
  title: string;
  lang: string;
  source: string;
  category: string;
  url: string | null;
  published_at: string;
}

export interface TopicDetail {
  snapshot_id: string;
  run_id: string;
  settings_hash: string;
  articles: TopicArticle[];
  total: number;
  cluster: Topic;
}

export interface CorpusResponse {
  snapshot_id: string;
  article_count: number;
  chunk_count: number;
  language_counts: Record<string, number>;
  source_counts: Record<string, number>;
  source_adapter_counts: Record<string, number>;
  category_counts: Record<string, number>;
  coverage: Record<string, Record<string, Record<string, number>>>;
  published_from: string;
  published_to: string;
  last_successful_crawl_at: string | null;
  collection_status: string;
  collection_name: string | null;
  topic_counts: Record<string, number> | null;
  topic_status: string;
  rejected_count: number | null;
  crawl_status: string;
  duplicate_count: number | null;
}

export interface AskRequest {
  question: string;
}

export interface AskCitation {
  citation_id: string;
  chunk_id: string;
  article_id: string;
  passage: string;
  url: string;
  title: string;
  source: string;
  language: string;
  published_at: string | null;
}

export interface AskResponse {
  status: "answered" | "insufficient_evidence" | "generation_unavailable" | "evidence_integrity_error";
  answer_segments: Array<{ text: string; citation_ids: string[] }>;
  gap: string | null;
  citations: AskCitation[];
  snapshot_id: string | null;
  reason?: string;
}

export interface HealthResponse {
  status: string;
  services?: { mongodb: boolean; weaviate: boolean };
}
