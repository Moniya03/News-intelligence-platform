"use client";

import { useEffect, useState } from "react";
import { corpusSummary } from "@/lib/api";
import { displayDate } from "@/components/SearchResultCard";
import { LANGUAGES } from "@/components/LangFilter";
import type { CorpusResponse } from "@/types";

export default function CorpusPage() {
  const [data, setData] = useState<CorpusResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    corpusSummary().then(response => { if (active) setData(response); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : "Corpus coverage is unavailable."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [attempt]);

  return <>
    <header className="page-heading"><span className="eyebrow">UNDERSTAND THE EVIDENCE</span><h1>Corpus coverage</h1><p>A view of the active frozen snapshot, its publishers, and its gaps.</p></header>
    {loading && <div className="state" role="status">Loading corpus coverage…</div>}
    {error && <div className="error" role="alert"><h2>Corpus unavailable</h2><p>{error}</p><button className="secondary" onClick={() => { setLoading(true); setError(""); setAttempt(value => value + 1); }}>Retry corpus</button></div>}
    {data && <>
      <div className="stat-grid"><div className="stat"><span>Frozen articles</span><strong>{data.article_count.toLocaleString()}</strong><small>2,000 article collection target</small></div><div className="stat"><span>Indexed chunks in snapshot</span><strong>{data.chunk_count.toLocaleString()}</strong><small>Snapshot manifest count; not live index health</small></div><div className="stat"><span>Publisher families</span><strong>{Object.keys(data.source_counts).length}</strong><small>{Object.keys(data.source_adapter_counts).length} source-language adapters represented</small></div></div>
      <div className="execution-meta"><span className="snapshot">Snapshot: {data.snapshot_id}</span><span>Published: {displayDate(data.published_from)} – {displayDate(data.published_to)}</span></div>
      <section className="coverage-section"><div className="section-heading"><h2>Language coverage</h2><span className="muted small">Target: approximately 500 articles per language</span></div><div className="language-grid">{LANGUAGES.map(language => { const count = data.language_counts[language.code] ?? 0; return <div className="language-coverage" key={language.code}><div><span lang={language.code}>{language.native}</span><strong>{count.toLocaleString()}</strong></div><meter min={0} max={Math.max(500, count)} value={count} aria-label={`${language.label} articles against a target of 500`}/><small>{count === 0 ? "No articles in this snapshot" : `${Math.max(0, 500 - count)} below the 500 article target`}</small></div>; })}</div></section>
      <div className="two-columns"><section className="panel"><h2>Publishers</h2><dl className="count-list">{Object.entries(data.source_counts).map(([source, count]) => <div key={source}><dt>{source}</dt><dd>{count.toLocaleString()}</dd></div>)}</dl></section><section className="panel"><h2>Categories</h2><p className="muted small">An article may belong to several categories.</p><dl className="count-list">{Object.entries(data.category_counts).map(([category, count]) => <div key={category}><dt>{category}</dt><dd>{count.toLocaleString()}</dd></div>)}</dl></section></div>
      <section className="coverage-section"><h2>Source and category coverage</h2><p className="muted small">Counts from the frozen snapshot. Zero cells identify missing category coverage in each represented adapter.</p><div className="table-scroll" tabIndex={0} role="region" aria-label="Source and category coverage table"><table><caption className="sr-only">Articles by source-language adapter and category</caption><thead><tr><th scope="col">Source adapter</th><th scope="col">Articles</th>{Object.keys(data.category_counts).map(category => <th scope="col" key={category}>{category}</th>)}</tr></thead><tbody>{Object.entries(data.source_adapter_counts).map(([adapter, count]) => <tr key={adapter}><th scope="row">{adapter}</th><td>{count}</td>{Object.keys(data.category_counts).map(category => <td key={category}>{data.coverage.adapter_category_counts?.[adapter]?.[category] ?? "Unavailable"}</td>)}</tr>)}</tbody></table></div></section>
      <section className="panel"><h2>Collection and processing</h2><dl className="facts"><dt>Latest successful collection</dt><dd>{data.last_successful_crawl_at ? displayDate(data.last_successful_crawl_at) : "Unavailable — no verified collection timestamp"}</dd><dt>Crawl status</dt><dd>{data.crawl_status.replaceAll("_", " ")}</dd><dt>Index collection</dt><dd>{data.collection_name ?? "Unavailable"} · {data.collection_status} (configuration only)</dd><dt>Topic processing</dt><dd>{data.topic_status.replaceAll("_", " ")}</dd><dt>Rejected articles</dt><dd>{data.rejected_count === null ? "Unavailable" : data.rejected_count.toLocaleString()}</dd><dt>Duplicates</dt><dd>{data.duplicate_count === null ? "Unavailable" : data.duplicate_count.toLocaleString()}</dd></dl><p className="form-note">Snapshot counts do not confirm that search services are online. Unavailable operational statistics are not zero.</p></section>
    </>}
  </>;
}
