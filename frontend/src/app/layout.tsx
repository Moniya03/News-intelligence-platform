import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "IndicNews Intel - Multilingual News Intelligence Platform",
  description:
    "Cross-lingual intelligence, verification, and topic clustering across English, Hindi, Bengali, and Tamil news media.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-gray-950 text-gray-100 flex flex-col selection:bg-indigo-500 selection:text-white">
        <div className="flex min-h-screen">
          {/* Fixed Sidebar navigation (desktop 240px + mobile drawer) */}
          <Sidebar />

          {/* Main content wrapper */}
          <main className="flex-1 min-w-0 lg:pl-[240px] pt-14 lg:pt-0 flex flex-col min-h-screen">
            <div className="flex-1 flex flex-col w-full h-full">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
