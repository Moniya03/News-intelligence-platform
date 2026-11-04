"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  Bot,
  User,
  Quote,
  ShieldAlert,
  ArrowRight,
  RotateCcw,
  Copy,
  Check,
  AlertCircle,
} from "lucide-react";
import { LangFilter } from "@/components/LangFilter";
import { CitationCard } from "@/components/CitationCard";
import { CredibilityMeter } from "@/components/CredibilityMeter";
import { ChatAnswerSkeleton } from "@/components/LoadingSkeleton";
import { chatQuery } from "@/lib/api";
import { ChatResponse } from "@/types";

interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content?: string;
  data?: ChatResponse;
  error?: string;
  isMockFallback?: boolean;
  timestamp: string;
}

const EXAMPLE_QUERIES = [
  "What is the current state of Indian politics?",
  "What happened with the cricket World Cup?",
  "Latest news on climate change in South Asia?",
];

// Lightweight Markdown Formatter
function FormattedAnswer({ text }: { text: string }) {
  const lines = text.split("\n");

  const renderInline = (str: string) => {
    // Process **bold** and `code`
    const parts = str.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={idx} className="font-semibold text-gray-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 rounded bg-gray-800 text-indigo-300 font-mono text-xs border border-gray-700/60"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="space-y-2 text-sm leading-relaxed text-gray-200">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        if (trimmed.startsWith("### ")) {
          return (
            <h4
              key={idx}
              className="text-base font-semibold text-indigo-300 pt-2 pb-1 border-b border-gray-800/60"
            >
              {renderInline(trimmed.replace(/^###\s*/, ""))}
            </h4>
          );
        }

        if (trimmed.startsWith("## ")) {
          return (
            <h3
              key={idx}
              className="text-lg font-bold text-gray-100 pt-2 pb-1 border-b border-gray-800/80"
            >
              {renderInline(trimmed.replace(/^##\s*/, ""))}
            </h3>
          );
        }

        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-2 shrink-0" />
              <div className="flex-1">{renderInline(trimmed.replace(/^[-*]\s*/, ""))}</div>
            </div>
          );
        }

        // Ordered list like 1. 2.
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2.5 pl-2">
              <span className="font-mono text-xs text-indigo-400 bg-indigo-950/60 border border-indigo-800/40 px-1.5 py-0.5 rounded font-semibold shrink-0">
                {numMatch[1]}
              </span>
              <div className="flex-1">{renderInline(numMatch[2])}</div>
            </div>
          );
        }

        return <p key={idx}>{renderInline(trimmed)}</p>;
      })}
    </div>
  );
}

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [selectedLangs, setSelectedLangs] = useState<string[]>([]);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const threadEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (customQuery?: string) => {
    const textToSend = (customQuery ?? query).trim();
    if (!textToSend || isLoading) return;

    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `assist-${Date.now()}`;

    // Add user message to state
    const userMsg: MessageItem = {
      id: userMessageId,
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setQuery("");
    setIsLoading(true);

    try {
      const response = await chatQuery(
        textToSend,
        selectedLangs.length > 0 ? selectedLangs : null
      );

      const assistantMsg: MessageItem = {
        id: assistantMessageId,
        role: "assistant",
        data: response,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to obtain synthesis response.";
      setMessages((prev) => [
        ...prev,
        {
          id: assistantMessageId,
          role: "assistant",
          error: errorMessage,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full min-h-[calc(100vh-3.5rem)] lg:min-h-screen bg-gray-950">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-20 bg-gray-950/80 backdrop-blur-md border-b border-gray-800/80 px-4 sm:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold text-gray-100 tracking-tight flex items-center gap-2">
              <span>Multilingual News Intelligence</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Cross-Lingual RAG
              </span>
            </h1>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Query across English, Hindi, Bengali, and Tamil news sources with consensus verification
          </p>
        </div>

        {/* Language Multi-Select Filter Bar */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 hidden sm:inline">Focus:</span>
          <LangFilter selected={selectedLangs} onChange={setSelectedLangs} />
        </div>
      </header>

      {/* Main Conversation Stream */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 max-w-5xl w-full mx-auto space-y-6">
        {messages.length === 0 ? (
          /* Welcome State */
          <div className="flex flex-col items-center justify-center min-h-[60vh] text-center max-w-2xl mx-auto py-8">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center mb-5 shadow-xl shadow-indigo-500/20 ring-1 ring-white/10">
              <Sparkles className="w-8 h-8 text-white" />
            </div>

            <h2 className="text-2xl font-bold text-gray-100 tracking-tight mb-2">
              Cross-Lingual Intelligence at Scale
            </h2>
            <p className="text-sm text-gray-400 max-w-lg mb-8 leading-relaxed">
              Ask questions across India&apos;s leading multilingual news media. Our
              system translates, retrieves, verifies facts across 4 languages, and calculates
              cross-source agreement.
            </p>

            {/* Example Queries */}
            <div className="w-full space-y-2.5 text-left">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider px-1">
                Explore Example Topics
              </div>
              <div className="grid grid-cols-1 gap-2.5">
                {EXAMPLE_QUERIES.map((example, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(example)}
                    className="flex items-center justify-between p-3.5 rounded-xl bg-gray-900/60 hover:bg-gray-900 border border-gray-800/80 hover:border-indigo-500/50 text-sm text-gray-200 transition-all duration-200 group text-left cursor-pointer shadow-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-xs font-mono group-hover:bg-indigo-500/20">
                        {idx + 1}
                      </span>
                      <span className="font-medium group-hover:text-indigo-200">
                        {example}
                      </span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                  </button>
                ))}
              </div>
            </div>

            {/* Corpus Capabilities */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs text-gray-400">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                <span>English (The Hindu, Express)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>Hindi (Dainik Bhaskar, Jagran)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>Bengali (Anandabazar, Bartaman)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-purple-500" />
                <span>Tamil (Dinamalar, Thanthi)</span>
              </div>
            </div>
          </div>
        ) : (
          /* Message List */
          messages.map((msg) => (
            <div key={msg.id} className="space-y-4">
              {msg.role === "user" ? (
                /* User Query Card */
                <div className="flex items-start justify-end gap-3 pl-8">
                  <div className="max-w-2xl bg-indigo-600/20 border border-indigo-500/30 text-gray-100 rounded-2xl rounded-tr-sm px-4 py-3 shadow-sm">
                    <p className="text-sm font-medium leading-relaxed">
                      {msg.content}
                    </p>
                    <div className="text-[10px] text-indigo-300/70 text-right mt-1 font-mono">
                      {msg.timestamp}
                    </div>
                  </div>
                  <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center shrink-0">
                    <User className="w-4 h-4 text-indigo-300" />
                  </div>
                </div>
              ) : (
                /* Assistant Synthesis Card */
                <div className="flex items-start gap-3 pr-2 sm:pr-8">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shrink-0 shadow-md shadow-indigo-500/20 mt-1">
                    <Bot className="w-4 h-4 text-white" />
                  </div>

                  <div className="flex-1 space-y-4 min-w-0">
                    {msg.error ? (
                      /* Error Notice */
                      <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-4 text-rose-200 text-sm flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          <div className="font-semibold">Unable to process query</div>
                          <p className="text-xs text-rose-300/80">{msg.error}</p>
                          <button
                            onClick={() => handleSend(messages[messages.length - 2]?.content)}
                            className="mt-2 text-xs font-semibold underline text-rose-300 hover:text-white"
                          >
                            Retry query
                          </button>
                        </div>
                      </div>
                    ) : msg.data ? (
                      <div className="bg-gray-900/90 border border-gray-800/90 rounded-2xl p-5 sm:p-6 shadow-xl space-y-5">
                        {/* Answer Top Bar */}
                        <div className="flex items-center justify-between border-b border-gray-800/70 pb-3">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-gray-200 uppercase tracking-wider">
                              Verified Synthesis
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-800 text-gray-400 border border-gray-700/60">
                              4-Language Corpus
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleCopy(msg.id, msg.data!.answer)}
                              className="text-gray-400 hover:text-gray-200 text-xs flex items-center gap-1 px-2 py-1 rounded bg-gray-800/60 hover:bg-gray-800 transition-colors"
                              title="Copy Answer"
                            >
                              {copiedId === msg.id ? (
                                <>
                                  <Check className="w-3 h-3 text-emerald-400" />
                                  <span className="text-emerald-400 text-[11px]">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  <span className="text-[11px]">Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>

                        {/* Synthesis Content */}
                        <FormattedAnswer text={msg.data.answer} />

                        {/* Citations Panel */}
                        {msg.data.citations && msg.data.citations.length > 0 && (
                          <div className="space-y-3 pt-3 border-t border-gray-800/60">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-300 uppercase tracking-wider">
                                <Quote className="w-3.5 h-3.5 text-indigo-400" />
                                <span>
                                  Source Citations ({msg.data.citations.length})
                                </span>
                              </div>
                              <span className="text-[11px] text-gray-400">
                                Ranked by relevance & cross-veracity
                              </span>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              {msg.data.citations.map((cit, i) => (
                                <CitationCard key={cit.chunk_id || i} citation={cit} index={i} />
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Credibility Meter */}
                        {msg.data.credibility && (
                          <div className="pt-2">
                            <CredibilityMeter credibility={msg.data.credibility} />
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                </div>
              )}
            </div>
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 pr-8">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/50 flex items-center justify-center shrink-0 animate-pulse">
              <Bot className="w-4 h-4 text-indigo-300" />
            </div>
            <div className="flex-1 bg-gray-900/60 border border-gray-800/80 rounded-2xl p-5">
              <ChatAnswerSkeleton />
            </div>
          </div>
        )}

        <div ref={threadEndRef} />
      </div>

      {/* Bottom Input Area */}
      <div className="sticky bottom-0 z-20 bg-gray-950/95 backdrop-blur-md border-t border-gray-800/80 px-4 sm:px-8 py-4">
        <div className="max-w-4xl mx-auto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="relative flex items-center rounded-2xl bg-gray-900/90 border border-gray-800 focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/40 transition-all shadow-lg"
          >
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question across Hindi, Bengali, Tamil, & English news..."
              rows={1}
              className="w-full bg-transparent px-4 py-3.5 text-sm text-gray-100 placeholder-gray-400 focus:outline-none resize-none min-h-[48px] max-h-32"
            />

            <div className="flex items-center gap-2 pr-3">
              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="w-9 h-9 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white flex items-center justify-center transition-all cursor-pointer shadow-md shadow-indigo-600/30"
                title="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </form>

          <div className="mt-2 flex items-center justify-between text-[11px] text-gray-400 px-1">
            <span>
              Press <kbd className="px-1 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">Enter</kbd> to submit, <kbd className="px-1 py-0.5 rounded bg-gray-800 text-gray-400 font-mono">Shift+Enter</kbd> for new line
            </span>
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline">Active filters:</span>
              <span className="font-mono text-indigo-400">
                {selectedLangs.length === 0 ? "All 4 Languages" : selectedLangs.join(", ").toUpperCase()}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
