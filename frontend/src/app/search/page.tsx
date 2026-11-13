"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { Search, ArrowRight, FileText } from "lucide-react";
import { LangFilter } from "@/components/LangFilter";
import { SearchResultCard } from "@/components/SearchResultCard";
import { searchArticles, summarizeSearch } from "@/lib/api";
import type { Language, SearchRequest, SearchResponse, SummaryResponse } from "@/types";
const modes = [{id:"bm25",label:"Keyword",help:"Match specific words and names in the articles."},{id:"dense",label:"Semantic",help:"Find related meaning across the corpus languages."},{id:"hybrid",label:"Hybrid",help:"Combine keyword matches with semantic similarity."}] as const;
export default function SearchPage() {
  const [query,setQuery]=useState("");
  const [mode,setMode]=useState<NonNullable<SearchRequest["mode"]>>("hybrid");
  const [languages,setLanguages]=useState<Language[]>([]);
  const [data,setData]=useState<SearchResponse|null>(null);
  const [searchedQuery,setSearchedQuery]=useState("");
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [summary,setSummary]=useState<SummaryResponse|null>(null);
  const [summaryError,setSummaryError]=useState("");
  const [summarizing,setSummarizing]=useState(false);
  const generation=useRef(0);
  async function search() {
    if (!query.trim()) return;
    const request=++generation.current;
    setLoading(true);setError("");setData(null);setSummary(null);setSummaryError("");setSummarizing(false);setSearchedQuery(query.trim());
    try { const response=await searchArticles({query:query.trim(),mode,lang_filter:languages.length?languages:null,top_k:20});if(generation.current===request)setData(response); }
    catch(e) {if(generation.current===request)setError(e instanceof Error?e.message:"Search is unavailable. Please retry.");}
    finally {if(generation.current===request)setLoading(false);}
  }
  async function summarize() {
    if(!data?.results.length)return;
    const request=generation.current;
    setSummarizing(true);setSummaryError("");
    try {const response=await summarizeSearch({query:searchedQuery,article_ids:data.results.slice(0,10).map(r=>r.article_id),snapshot_id:data.metadata.snapshot_id});if(generation.current===request)setSummary(response);}
    catch(e) {if(generation.current===request)setSummaryError(e instanceof Error?e.message:"Summary is unavailable.");}
    finally {if(generation.current===request)setSummarizing(false);}
  }
  return <><header className="page-heading"><span className="eyebrow">EXPLORE THE CORPUS</span><h1>Search the news</h1><p>Follow a story across English, Hindi, Bengali and Marathi sources.</p></header>
    <form className="search-panel" onSubmit={e=>{e.preventDefault();void search();}}>
      <label htmlFor="query" className="sr-only">Search query</label><div className="query-row"><Search size={21} aria-hidden="true"/><input id="query" required maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="A topic, a name, a question…"/><button className="primary" disabled={loading||!query.trim()}>{loading?"Searching…":"Search"}<ArrowRight size={16} aria-hidden="true"/></button></div>
      <div className="search-options"><fieldset><legend>Retrieval mode</legend><div className="segmented">{modes.map(m=><button className="chip" key={m.id} type="button" aria-pressed={mode===m.id} onClick={()=>setMode(m.id)}>{m.label}</button>)}</div><p className="control-help">{modes.find(m=>m.id===mode)?.help}</p></fieldset><LangFilter selected={languages} onChange={setLanguages}/></div><p className="form-note">Changes apply when you select Search. Results are ranked articles from the frozen snapshot.</p>
    </form>
    {loading && <div className="state" role="status"><span className="loading-dot"/>Searching the index…</div>}
    {error && <div className="error" role="alert"><h2>Search unavailable</h2><p>{error}</p><p>Check index availability and retry your search.</p><button className="secondary" onClick={()=>void search()}>Retry search</button></div>}
    {data && <><div className="section-heading"><h2>{data.results.length} articles <span className="muted">for “{searchedQuery}”</span></h2><span className="muted small">Ranked by retrieval score</span></div><div className="execution-meta"><span>Requested: {modes.find(m=>m.id===data.metadata.requested_mode)?.label}</span><span>Executed: {modes.find(m=>m.id===data.metadata.executed_mode)?.label}</span><span>Reranker: {data.metadata.reranker_status}</span><span>{Math.round(data.metadata.elapsed_ms)} ms</span><span className="snapshot">Snapshot: {data.metadata.snapshot_id}</span></div>
      {data.results.length===0?<div className="state" role="status"><h2>No articles found</h2><p>Try a broader query or include more languages.</p></div>:<><div className="results">{data.results.map((r,i)=><SearchResultCard key={r.article_id} result={r} index={i}/>)}</div><section className="summary-panel" aria-labelledby="summary-heading"><div className="section-heading"><div><h2 id="summary-heading"><FileText size={17} aria-hidden="true"/>Evidence summary <span className="badge">Optional</span></h2><p className="muted small">Uses up to the first 10 retrieved articles. Search results remain available.</p></div><button className="secondary" disabled={summarizing} onClick={()=>void summarize()}>{summarizing?"Requesting…":summary||summaryError?"Retry summary":"Request summary"}</button></div>{summarizing&&<p role="status">Requesting an evidence summary…</p>}{summaryError&&<div className="error" role="alert"><p>{summaryError}</p><p>If the snapshot has changed (409), run Search again before requesting a summary.</p></div>}{summary&&<div role="status">{summary.status==="available"&&summary.summary?<><p>{summary.summary}</p><ul className="citations">{summary.citations.map(c=><li key={c.citation_id}>[{c.citation_id}] {c.url&&/^https?:\/\//i.test(c.url)?<a href={c.url} target="_blank" rel="noopener noreferrer">{c.title}</a>:c.title} · {c.source}</li>)}</ul></>:<p className="notice">{summary.status==="insufficient_evidence"?"Insufficient usable evidence for a summary.":"Summary unavailable."} <span className="muted">{summary.reason?.replaceAll("_"," ")}</span></p>}</div>}</section></>}
    </>}
    {!loading&&!error&&!data&&<section className="getting-started"><span className="eyebrow">START WITH A QUESTION</span><h2>One query. Several perspectives.</h2><p>Use Keyword for exact names, Semantic for related ideas, or Hybrid to combine both.</p><div className="suggestions">{["Reserve Bank interest rates","India elections","भारतीय अर्थव्यवस्था"].map(q=><button className="secondary" key={q} onClick={()=>{setQuery(q);document.getElementById("query")?.focus();}}>{q}<ArrowRight size={14} aria-hidden="true"/></button>)}</div><Link className="text-link" href="/corpus">See what the corpus covers <ArrowRight size={14} aria-hidden="true"/></Link></section>}
  </>;
}
