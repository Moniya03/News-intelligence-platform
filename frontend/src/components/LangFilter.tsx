import type { Language } from "@/types";
export const LANGUAGES: {code: Language; label: string; native: string}[] = [{code:"en",label:"English",native:"English"},{code:"hi",label:"Hindi",native:"हिन्दी"},{code:"bn",label:"Bengali",native:"বাংলা"},{code:"mr",label:"Marathi",native:"मराठी"}];
export function LangFilter({selected,onChange}:{selected:Language[];onChange:(languages:Language[])=>void}) {
  return <fieldset><legend>Languages</legend><div className="chips"><button type="button" className="chip" aria-pressed={selected.length===0} onClick={()=>onChange([])}>All languages</button>{LANGUAGES.map(l=><button type="button" className="chip" key={l.code} aria-label={l.label} aria-pressed={selected.includes(l.code)} onClick={()=>onChange(selected.includes(l.code)?selected.filter(c=>c!==l.code):[...selected,l.code])}><span lang={l.code}>{l.native}</span></button>)}</div></fieldset>;
}
