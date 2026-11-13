"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { Search, ArrowRight } from "lucide-react";
import { LangFilter } from "@/components/LangFilter";
import { SearchResultCard } from "@/components/SearchResultCard";
import { searchArticles } from "@/lib/api";
import type { Language, SearchRequest, SearchResponse } from "@/types";
const modes = [{id:"bm25",label:"Keyword",help:"Match specific words and names in the articles."},{id:"dense",label:"Semantic",help:"Find related meaning across the corpus languages."},{id:"hybrid",label:"Hybrid",help:"Combine keyword matches with semantic similarity."}] as const;
export default function SearchPage() {
  const [query,setQuery]=useState("");
  const [mode,setMode]=useState<NonNullable<SearchRequest["mode"]>>("hybrid");
  const [languages,setLanguages]=useState<Language[]>([]);
  const [data,setData]=useState<SearchResponse|null>(null);
  const [searchedQuery,setSearchedQuery]=useState("");
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const generation=useRef(0);
  async function search() {
    if (!query.trim()) return;
    const request=++generation.current;
    setLoading(true);setError("");setData(null);setSearchedQuery(query.trim());
    try { const response=await searchArticles({query:query.trim(),mode,lang_filter:languages.length?languages:null,top_k:20});if(generation.current===request)setData(response); }
    catch(e) {if(generation.current===request)setError(e instanceof Error?e.message:"Search is unavailable. Please retry.");}
    finally {if(generation.current===request)setLoading(false);}
  }
  return <><header className="page-heading"><span className="eyebrow">EXPLORE THE CORPUS</span><h1>Search the news</h1><p>Follow a story across English, Hindi, Bengali and Marathi sources.</p></header>
    <form className="search-panel" onSubmit={e=>{e.preventDefault();void search();}}>
      <label htmlFor="query" className="sr-only">Search query</label><div className="query-row"><Search size={21} aria-hidden="true"/><input id="query" required maxLength={2000} value={query} onChange={e=>setQuery(e.target.value)} placeholder="A topic, a name, a question…"/><button className="primary" disabled={loading||!query.trim()}>{loading?"Searching…":"Search"}<ArrowRight size={16} aria-hidden="true"/></button></div>
      <div className="search-options"><fieldset><legend>Retrieval mode</legend><div className="segmented">{modes.map(m=><button className="chip" key={m.id} type="button" aria-pressed={mode===m.id} onClick={()=>setMode(m.id)}>{m.label}</button>)}</div><p className="control-help">{modes.find(m=>m.id===mode)?.help}</p></fieldset><LangFilter selected={languages} onChange={setLanguages}/></div><p className="form-note">Changes apply when you select Search. Results are ranked articles from the frozen snapshot.</p>
    </form>
    {loading && <div className="state" role="status"><span className="loading-dot"/>Searching the index…</div>}
    {error && <div className="error" role="alert"><h2>Search unavailable</h2><p>{error}</p><p>Check index availability and retry your search.</p><button className="secondary" onClick={()=>void search()}>Retry search</button></div>}
    {data && <><div className="section-heading"><h2>{data.results.length} articles <span className="muted">for “{searchedQuery}”</span></h2><span className="muted small">Ranked by retrieval score</span></div><div className="execution-meta"><span>Requested: {modes.find(m=>m.id===data.metadata.requested_mode)?.label}</span><span>Executed: {modes.find(m=>m.id===data.metadata.executed_mode)?.label}</span><span>Reranker: {data.metadata.reranker_status}</span><span>{Math.round(data.metadata.elapsed_ms)} ms</span><span className="snapshot">Snapshot: {data.metadata.snapshot_id}</span></div>
      {data.results.length===0?<div className="state" role="status"><h2>No articles found</h2><p>Try a broader query or include more languages.</p></div>:<><div className="results">{data.results.map((r,i)=><SearchResultCard key={r.article_id} result={r} index={i}/>)}</div></>}
    </>}
    {!loading&&!error&&!data&&<section className="getting-started"><span className="eyebrow">START WITH A QUESTION</span><h2>One query. Several perspectives.</h2><p>Use Keyword for exact names, Semantic for related ideas, or Hybrid to combine both.</p><div className="suggestions">{["Reserve Bank interest rates","India elections","भारतीय अर्थव्यवस्था"].map(q=><button className="secondary" key={q} onClick={()=>{setQuery(q);document.getElementById("query")?.focus();}}>{q}<ArrowRight size={14} aria-hidden="true"/></button>)}</div><Link className="text-link" href="/corpus">See what the corpus covers <ArrowRight size={14} aria-hidden="true"/></Link></section>}
  </>;
}
