"use client";

import { useEffect, useRef, useState } from "react";
import { getClusters, getClusterDetail } from "@/lib/api";
import { SearchResultCard } from "@/components/SearchResultCard";
import { LANGUAGES } from "@/components/LangFilter";
import type { TopicDetail, TopicsResponse } from "@/types";

export default function TopicsPage() {
  const [data, setData] = useState<TopicsResponse | null>(null);
  const [detail, setDetail] = useState<TopicDetail | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const request = useRef(0);

  useEffect(() => {
    let active = true;
    getClusters().then(response => { if (active) setData(response); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "Topics are unavailable."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  async function openTopic(id: number, nextPage = 1) {
    const current = ++request.current;
    setSelected(id); setPage(nextPage); setDetail(null); setDetailLoading(true); setDetailError("");
    try {
      const response = await getClusterDetail(id, nextPage);
      if (current !== request.current) return;
      if (response.snapshot_id !== data?.snapshot_id || response.run_id !== data.run_id || response.settings_hash !== data.settings_hash) {
        setDetailError("Topic snapshot or run changed. Reload Topics to view the current articles.");
      } else setDetail(response);
    } catch (e) {
      if (current === request.current) setDetailError(e instanceof Error ? e.message : "Topic articles are unavailable.");
    } finally { if (current === request.current) setDetailLoading(false); }
  }

  function reload() {
    request.current++; setLoading(true); setError(""); setData(null); setSelected(null); setDetail(null); setDetailError(""); setDetailLoading(false); setAttempt(value => value + 1);
  }

  return <>
    <header className="page-heading"><span className="eyebrow">EXPLORE CONNECTIONS</span><h1>Topics in the corpus</h1><p>Inspect shared terms and the real articles grouped by the topic model.</p></header>
    {loading && <div className="state" role="status">Loading snapshot topics…</div>}
    {error && <div className="error" role="alert"><h2>Topics unavailable</h2><p>{error}</p><button className="secondary" onClick={reload}>Retry topics</button></div>}
    {data && <>
      <div className="section-heading"><h2>{data.topic_count} topics <span className="muted">· {data.run_id ? `${data.outlier_count} unassigned articles` : "Unassigned count unavailable"}</span></h2><button className="secondary" onClick={reload}>Reload topics</button></div>
      <div className="execution-meta"><span className="snapshot">Snapshot: {data.snapshot_id}</span><span>Algorithm: {data.algorithm ?? "Unavailable"}</span><span>Run: {data.run_id ?? "Not generated"}</span><span>Settings: {data.settings_hash ?? "Unavailable"}</span></div>
      <p className="form-note">Topics describe model groupings, not verified events. Unassigned articles are retained as a separate group.</p>
      {!data.run_id && <div className="state" role="status"><h2>No topic run available</h2><p>The active snapshot has no generated topics.</p></div>}
      {data.run_id && !data.clusters.length && <div className="state" role="status">No topic groups in this run.</div>}
      <div className="topic-grid">{data.clusters.map(topic => <article className="topic-card" key={topic.id}>
        <div className="section-heading"><span className="eyebrow">{topic.id === -1 ? "UNASSIGNED / NOISE" : `TOPIC ${topic.id}`}</span><span className="badge">{topic.size} articles</span></div>
        <h2>{topic.label}</h2><p className="topic-terms">{topic.top_terms.length ? topic.top_terms.join(" · ") : "No descriptive terms available"}</p>
        <dl className="distribution"><dt>Languages</dt><dd>{Object.entries(topic.lang_counts).map(([lang, count]) => `${LANGUAGES.find(l => l.code === lang)?.label ?? lang}: ${count}`).join(" · ") || "Unavailable"}</dd><dt>Publishers</dt><dd>{Object.entries(topic.source_counts).map(([source, count]) => `${source}: ${count}`).join(" · ") || "Unavailable"}</dd></dl>
        <button className="secondary" aria-pressed={selected === topic.id} onClick={() => void openTopic(topic.id)}>View {topic.id === -1 ? "unassigned " : ""}articles</button>
      </article>)}</div>
      {selected !== null && <section className="topic-detail" aria-labelledby="topic-detail-heading" aria-busy={detailLoading}>
        <div className="section-heading"><h2 id="topic-detail-heading">{detail?.cluster.label ?? (selected === -1 ? "Unassigned articles" : `Topic ${selected} articles`)}</h2>{detail && <span className="muted small">{detail.total} members</span>}</div>
        {detailLoading && <p className="state" role="status">Loading topic articles…</p>}
        {detailError && <div className="error" role="alert"><p>{detailError}</p><button className="secondary" onClick={reload}>Reload topics</button></div>}
        {detail && <>{!detail.articles.length && <p className="state" role="status">No articles on this page.</p>}<div className="results">{detail.articles.map(article => <SearchResultCard key={article.article_id} result={article} representative={detail.cluster.representative_article_ids.includes(article.article_id)}/>)}</div><nav className="pagination" aria-label="Topic article pages"><button className="secondary" disabled={page === 1} onClick={() => void openTopic(selected, page - 1)}>Previous</button><span role="status">Page {page} of {Math.max(1, Math.ceil(detail.total / 20))}</span><button className="secondary" disabled={page * 20 >= detail.total} onClick={() => void openTopic(selected, page + 1)}>Next</button></nav></>}
      </section>}
    </>}
  </>;
}
