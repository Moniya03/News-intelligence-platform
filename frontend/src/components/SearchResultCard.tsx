import { ArrowUpRight } from "lucide-react";
import type { SearchResult, TopicArticle } from "@/types";
import { LANGUAGES } from "./LangFilter";
export function displayDate(value?:string|null) {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric",timeZone:"UTC"});
}
export function SearchResultCard({result,index,representative=false}:{result:SearchResult|TopicArticle;index?:number;representative?:boolean}) {
  const url = result.url && /^https?:\/\//i.test(result.url) ? result.url : null;
  return <article className="article"><div className="article-meta"><span className="language-tag">{LANGUAGES.find(l=>l.code===result.lang)?.label ?? result.lang}</span><span>{result.source || "Source unavailable"}</span><span>{displayDate(result.published_at)}</span>{result.category && <span>{result.category}</span>}</div><h3 lang={result.lang}>{url?<a href={url} target="_blank" rel="noopener noreferrer">{result.title}<ArrowUpRight size={15} aria-hidden="true"/></a>:result.title}</h3>{"snippet" in result && <p className="snippet" lang={result.lang}>{result.snippet}</p>}<div className="article-footer">{url?<a href={url} target="_blank" rel="noopener noreferrer" className="source-url">{url}</a>:<span>Source URL unavailable</span>}{"score" in result && <span className="score">Retrieval score {result.score.toFixed(3)}</span>}{representative && <span className="badge">Representative article</span>}{index!==undefined && <span className="result-rank">{String(index+1).padStart(2,"0")}</span>}</div></article>;
}
