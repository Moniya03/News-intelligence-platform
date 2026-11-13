"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, BookOpen, LoaderCircle } from "lucide-react";
import { askQuestion } from "@/lib/api";
import { displayDate } from "@/components/SearchResultCard";
import { LANGUAGES } from "@/components/LangFilter";
import type { AskResponse } from "@/types";

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [askedQuestion, setAskedQuestion] = useState("");
  const [data, setData] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const length = [...question].length;

  async function ask() {
    if (loading || !question.trim() || length > 2000) return;
    setLoading(true);
    setError("");
    setData(null);
    setAskedQuestion(question.trim());
    try {
      setData(await askQuestion({ question: question.trim() }));
    } catch (e) {
      setError(e instanceof Error && e.name !== "AbortError" ? e.message : "This request took too long. Please try again.");
    } finally {
      setLoading(false);
      requestAnimationFrame(() => resultHeading.current?.focus());
    }
  }

  function inspectCitation(index: number) {
    const passage = document.getElementById(`evidence-${index}`) as HTMLDetailsElement | null;
    if (passage) {
      passage.open = true;
      passage.querySelector("summary")?.focus();
      passage.scrollIntoView({ block: "nearest" });
    }
  }

  const integrityError = data?.status === "evidence_integrity_error";
  const citations = integrityError ? [] : data?.citations ?? [];

  return <>
    <header className="page-heading"><span className="eyebrow">ASK THE CORPUS</span><h1>A question. An answer you can inspect.</h1><p>Ask in English, Hindi, Bengali or Marathi. Explore an answer with passages from the frozen news corpus.</p></header>
    <form className="search-panel ask-form" onSubmit={e => { e.preventDefault(); void ask(); }} aria-busy={loading}>
      <label htmlFor="question">What would you like to know?</label>
      <textarea id="question" required rows={3} value={question} disabled={loading} onChange={e => setQuestion(e.target.value)} placeholder="What does the reporting say about India's economy?" aria-describedby="question-help question-count" aria-invalid={length > 2000 || undefined}/>
      <div className="ask-form-footer"><div><p id="question-help">Each question stands alone. Answers may use reporting in any corpus language.</p><p id="question-count" className={length > 2000 ? "over-limit" : undefined}>{length.toLocaleString()} / 2,000 characters</p></div><button className="primary" disabled={loading || !question.trim() || length > 2000}>{loading ? "Preparing answer…" : "Ask a question"}<ArrowRight size={16} aria-hidden="true"/></button></div>
    </form>
    {loading && <div className="state ask-loading" role="status"><LoaderCircle className="ask-spinner" size={25} aria-hidden="true"/><div><strong>Following the evidence…</strong><p>Finding passages and preparing your answer. The complete response will appear here.</p></div></div>}
    {error && <div className="error" role="alert"><h2 tabIndex={-1} ref={resultHeading}>Ask unavailable</h2><p>{error}</p><button className="secondary" onClick={() => void ask()}>Retry question</button></div>}
    {data && <section className="ask-response" aria-label="Response">
      <div className="section-heading"><h2 tabIndex={-1} ref={resultHeading}>{data.status === "answered" ? "Answer" : integrityError ? "Evidence could not be checked" : data.status === "insufficient_evidence" ? "The corpus is insufficient" : "Answer unavailable"}</h2><span className="muted small">For this question</span></div>
      <p className="muted small">{askedQuestion}</p>
      {data.status === "answered" ? <div className="ask-answer">
        {data.answer_segments.map((segment, index) => <p className="answer-segment" key={index}>{segment.text}<span className="claim-citations">{segment.citation_ids.map(id => {
          const citationIndex = citations.findIndex(c => c.citation_id === id);
          return citationIndex < 0 ? null : <a href={`#evidence-${citationIndex}`} key={id} onClick={e => { e.preventDefault(); inspectCitation(citationIndex); }} aria-label={`Inspect passage ${citationIndex + 1}`}>[{citationIndex + 1}]</a>;
        })}</span></p>)}
        {data.gap && <div className="ask-gap"><strong>What remains unanswered</strong><p>{data.gap}</p></div>}
      </div> : <div className="state" role="status"><p>{integrityError ? "We could not verify the retrieved evidence against the corpus. No answer or passages are shown. Please try again." : data.status === "insufficient_evidence" ? "The available corpus does not provide enough evidence to answer this question." : data.reason === "context_limit" ? "The retrieved passages could not fit into an answer request. You can still inspect the evidence below." : "An answer could not be completed. You can still inspect the retrieved evidence below."}</p>{!integrityError && data.status === "insufficient_evidence" && data.gap && <p className="notice">{data.gap}</p>}</div>}
      {citations.length > 0 && <section className="ask-evidence" aria-labelledby="evidence-heading"><div className="section-heading"><h2 id="evidence-heading"><BookOpen size={18} aria-hidden="true"/>Retrieved passages <span className="badge">{citations.length}</span></h2></div><p>Open a passage to read the exact corpus text and visit its source. Citations let you inspect support for each claim; they do not guarantee that a claim is correct.</p>
        {citations.map((citation, index) => <details className="evidence-item" id={`evidence-${index}`} key={citation.citation_id}><summary><span className="evidence-number">[{index + 1}]</span><span lang={citation.language}>{citation.title}</span></summary><div className="evidence-body"><div className="article-meta"><span>{citation.source}</span><span className="language-tag">{LANGUAGES.find(l => l.code === citation.language)?.label ?? citation.language}</span><span>{displayDate(citation.published_at)}</span></div><blockquote lang={citation.language}>{citation.passage}</blockquote>{/^https?:\/\//i.test(citation.url) ? <a className="text-link" href={citation.url} target="_blank" rel="noopener noreferrer">Read original article <ArrowUpRight size={14} aria-hidden="true"/></a> : <span className="muted small">Source link unavailable</span>}</div></details>)}
      </section>}
      {data.snapshot_id && <div className="execution-meta"><span className="snapshot">Snapshot: {data.snapshot_id}</span></div>}
    </section>}
    {!loading && !error && !data && <section className="getting-started"><span className="eyebrow">FOLLOW THE EVIDENCE</span><h2>Start with the reporting.</h2><p>Answers are limited to the available articles. Missing evidence stays unanswered, and citations lead back to the original passages.</p><div className="suggestions"><Link href="/search" className="secondary">Explore articles <ArrowRight size={14} aria-hidden="true"/></Link><Link href="/corpus" className="secondary">See corpus coverage <ArrowRight size={14} aria-hidden="true"/></Link></div></section>}
  </>;
}
