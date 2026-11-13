import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "IndicNews · Research workspace",
  description: "Explore a frozen multilingual news corpus in English, Hindi, Bengali and Marathi.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body><a className="skip-link" href="#main">Skip to content</a><Sidebar /><main id="main" tabIndex={-1}><div className="workspace-top"><span>News intelligence platform</span><span>Research workspace</span></div><div className="workspace">{children}</div></main></body></html>;
}
