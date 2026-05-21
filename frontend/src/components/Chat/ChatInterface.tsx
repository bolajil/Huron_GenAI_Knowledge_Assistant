/**
 * ChatInterface - Real Chat with Huron Knowledge Base
 * Uses real FAISS search and OpenAI
 */
"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, Bot, User, Trash2, ThumbsUp, ThumbsDown, ShieldAlert } from "lucide-react";
import { api } from "../../services/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004";

const getAuthHeader = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

interface SourceGuard {
  passed: boolean;
  score: number;
  warning: string | null;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  query?: string;           // the user question that triggered this assistant reply
  timestamp: Date;
  sources?: Array<{ title: string }>;
  source?: "rag" | "general_knowledge" | "error";
  sourceLabel?: string;
  sourceGuard?: SourceGuard;
  deptCode?: string;
}

interface IndexInfo {
  name: string;
  dept: string;
  documents: number;
}

export function ChatInterface() {
  const [messages, setMessages]           = useState<Message[]>([]);
  const [input, setInput]                 = useState("");
  const [loading, setLoading]             = useState(false);
  const [selectedIndex, setSelectedIndex] = useState("");
  const [availableIndexes, setAvailableIndexes] = useState<IndexInfo[]>([]);
  const [ratings, setRatings]             = useState<Record<number, 1 | -1>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchIndexes = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/indexes`, {
          headers: { ...getAuthHeader() },
        });
        const data = await response.json();
        if (data.indexes && data.indexes.length > 0) {
          setAvailableIndexes(data.indexes);
          setSelectedIndex(data.indexes[0].name);
        }
      } catch (err) {
        console.error("Failed to fetch indexes:", err);
      }
    };
    fetchIndexes();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleFeedback = async (idx: number, rating: 1 | -1) => {
    if (ratings[idx] !== undefined) return; // already rated
    setRatings((prev) => ({ ...prev, [idx]: rating }));
    const msg = messages[idx];
    if (!msg) return;
    try {
      await api.submitFeedback({
        query:     msg.query ?? "",
        response:  msg.content,
        rating,
        source:    msg.source ?? "general_knowledge",
        dept_code: msg.deptCode ?? "general",
      });
    } catch (err) {
      console.error("Feedback submit failed:", err);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    const userMessage: Message = { role: "user", content: userQuery, timestamp: new Date() };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // derive dept from selected index name (e.g. "vaultmind-huron-hr-general" → "hr")
    const deptCode = availableIndexes.find((i) => i.name === selectedIndex)?.dept ?? "general";

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          messages: messages.concat(userMessage).map((m) => ({
            role: m.role,
            content: m.content,
          })),
          department: deptCode,
        }),
      });

      const data = await response.json();
      const assistantMessage: Message = {
        role:        "assistant",
        content:     data.response || data.detail || "No response received",
        query:       userQuery,
        timestamp:   new Date(),
        sources:     data.sources,
        source:      data.source,
        sourceLabel: data.source_label,
        sourceGuard: data.source_guard,
        deptCode,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error connecting to the Huron backend.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearChat = () => {
    setMessages([]);
    setRatings({});
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Bot className="h-6 w-6 text-primary" />
            Chat Assistant
          </h2>
          <p className="text-muted-foreground mt-1">
            Have a conversation with your knowledge base
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedIndex}
            onChange={(e) => setSelectedIndex(e.target.value)}
            className="px-3 py-2 rounded-lg bg-background border border-input text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {availableIndexes.length > 0 ? (
              availableIndexes.map((idx) => (
                <option key={idx.name} value={idx.name}>
                  {idx.name} ({idx.documents} docs)
                </option>
              ))
            ) : (
              <option value="">No indexes — general knowledge mode</option>
            )}
          </select>
          <button onClick={clearChat} className="p-2 rounded-lg hover:bg-accent" title="Clear chat">
            <Trash2 className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-border bg-card">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Start a conversation by typing a message below</p>
              <p className="text-sm mt-1">
                {availableIndexes.length > 0
                  ? "Answers will be grounded in your department's indexed documents."
                  : "No documents indexed yet — answers will come from general AI knowledge."}
              </p>
            </div>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {messages.map((message, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}

                <div className="max-w-[72%] flex flex-col gap-1">
                  {/* Bubble */}
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-accent"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                    {/* Sources list */}
                    {message.sources && message.sources.length > 0 && (
                      <p className="text-xs mt-2 text-muted-foreground">
                        Sources: {message.sources.map((s) => s.title).join(", ")}
                      </p>
                    )}

                    {/* Source origin badge */}
                    {message.role === "assistant" && message.source === "general_knowledge" && (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
                        <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 font-medium">
                          ⚡ General knowledge
                        </span>
                        {message.sourceLabel && (
                          <span className="text-xs text-muted-foreground">{message.sourceLabel}</span>
                        )}
                      </div>
                    )}
                    {message.role === "assistant" &&
                      message.source === "rag" &&
                      message.sources &&
                      message.sources.length > 0 && (
                        <div className="mt-2">
                          <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-600 dark:text-green-400 font-medium">
                            📄 From knowledge base
                          </span>
                        </div>
                      )}

                    {/* Source guard warning */}
                    {message.role === "assistant" &&
                      message.sourceGuard &&
                      !message.sourceGuard.passed && (
                        <div className="mt-2 flex items-start gap-1.5 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                          <ShieldAlert className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
                          <div>
                            <span className="text-xs font-medium text-red-600 dark:text-red-400">
                              Source guard warning
                            </span>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {message.sourceGuard.warning ??
                                "This response may not be fully grounded in the source documents. Please verify before acting on it."}
                            </p>
                            <span className="text-xs text-muted-foreground">
                              Confidence: {Math.round(message.sourceGuard.score * 100)}%
                            </span>
                          </div>
                        </div>
                      )}

                    <p
                      className={`text-xs mt-1 ${
                        message.role === "user"
                          ? "text-primary-foreground/70"
                          : "text-muted-foreground"
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>

                  {/* Thumbs feedback — only on assistant messages */}
                  {message.role === "assistant" && (
                    <div className="flex items-center gap-1 pl-1">
                      <button
                        onClick={() => handleFeedback(idx, 1)}
                        disabled={ratings[idx] !== undefined}
                        title="Helpful"
                        className={`p-1.5 rounded-lg transition-colors ${
                          ratings[idx] === 1
                            ? "text-green-600 bg-green-500/15"
                            : "text-muted-foreground hover:text-green-600 hover:bg-green-500/10"
                        } disabled:cursor-default`}
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => handleFeedback(idx, -1)}
                        disabled={ratings[idx] !== undefined}
                        title="Not helpful"
                        className={`p-1.5 rounded-lg transition-colors ${
                          ratings[idx] === -1
                            ? "text-red-600 bg-red-500/15"
                            : "text-muted-foreground hover:text-red-600 hover:bg-red-500/10"
                        } disabled:cursor-default`}
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                      {ratings[idx] !== undefined && (
                        <span className="text-xs text-muted-foreground ml-1">
                          {ratings[idx] === 1 ? "Thanks for the feedback!" : "We'll improve this."}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {message.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0 mt-1">
                    <User className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-accent rounded-2xl px-4 py-3">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="mt-4 flex gap-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          rows={1}
          className="flex-1 px-4 py-3 rounded-xl bg-background border border-input focus:outline-none focus:ring-2 focus:ring-ring resize-none"
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </button>
      </div>
    </div>
  );
}

export default ChatInterface;
