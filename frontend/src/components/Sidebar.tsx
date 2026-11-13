"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, MessageSquare, Layers, Database, Languages, ArrowUpRight } from "lucide-react";

const items = [{ href: "/search", label: "Search", icon: Search }, { href: "/ask", label: "Ask", icon: MessageSquare }, { href: "/topics", label: "Topics", icon: Layers }, { href: "/corpus", label: "Corpus", icon: Database }];
export function Sidebar() {
  const pathname = usePathname();
  return <aside className="sidebar"><Link href="/search" className="brand"><Languages size={25} aria-hidden="true"/><span>IndicNews<small>NEWS RESEARCH</small></span></Link><div className="nav-label">WORKSPACE</div><nav aria-label="Main navigation">{items.map(({href,label,icon:Icon}) => <Link href={href} key={href} aria-current={pathname === href ? "page" : undefined}><Icon size={18} aria-hidden="true"/>{label}{pathname === href && <ArrowUpRight size={15} className="nav-arrow" aria-hidden="true"/>}</Link>)}</nav><div className="sidebar-note"><span className="eyebrow">FOUR LANGUAGES</span><p lang="hi">English · हिन्दी<br/><span lang="bn">বাংলা</span> · मराठी</p><small>Explore sources. Compare coverage.<br/>Follow the evidence.</small></div></aside>;
}
