"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send, Loader2, Bot, User, Trash2, ThumbsUp, ThumbsDown,
  ShieldAlert, Plus, MessageSquare, ChevronLeft, Clock,
} from "lucide-react";
import { api, Conversation, ConversationMessage } from "../../services/api";
import { useAuth } from "../../contexts/auth-context";

function getBackendBase(): string {
  if (typeof window === "undefined") return "http://localhost:8004";
  const hostname = window.location.hostname;
  if (hostname.includes("azurecontainerapps.io")) {
    return `https://${hostname.replace("huron-dev-frontend", "huron-dev-backend")}`;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8004";
}

const getAuthHeader = (): Record<string, string> => {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

interface IndexInfo { name: string; dept: string; documents: number; }

interface UIMessage extends ConversationMessage {
  conversation_id?: string;
  sourceGuard?: { passed: boolean; score: number; warning: string | null };
  sources?:     Array<{ title: string }>;
}

export function ChatInterface() {
  const { user } = useAuth();

  // ── Conversation list ──────────────────────────────────────────────────────
  const [conversations, setConversations]   = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId]     = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen]       = useState(true);
  const [loadingConvs, setLoadingConvs]     = useState(true);

  // ── Messages ───────────────────────────────────────────────────────────────
  const [messages, setMessages]   = useState<UIMessage[]>([]);
  const [loadingMsgs, setLoadingMsgs] = useState(false);

  // ── Input / sending ────────────────────────────────────────────────────────
  const [input, setInput]   = useState("");
  const [sending, setSending] = useState(false);
  const [ratings, setRatings] = useState<Record<number, 1 | -1>>({});

  // ── Index selector ─────────────────────────────────────────────────────────
  const [selectedIndex, setSelectedIndex]       = useState("");
  const [availableIndexes, setAvailableIndexes] = useState<IndexInfo[]>([]);

  const messagesEndRef  = useRef<HTMLDivElement>(null);
  const autoRestored    = useRef(false);

  // ── Load indexes ───────────────────────────────────────────────────────────
  useEffect(() => {
    fetch(`${getBackendBase()}/api/v1/indexes`, { headers: getAuthHeader() })
      .then((r) => r.json())
      .then((data) => {
        if (data.indexes?.length) {
          setAvailableIndexes(data.indexes);
          const userDept = user?.department ?? "general";
          const preferred = data.indexes.find((i: IndexInfo) => i.dept === userDept);
          setSelectedIndex((preferred ?? data.indexes[0]).name);
        }
      })
      .catch(() => {});
  }, [user?.department]);

  // ── Load conversation list (+ auto-restore most recent on first mount) ──────
  const loadConversations = useCallback(async () => {
    setLoadingConvs(true);
    try {
      const data = await api.listConversations("chat");
      setConversations(data.conversations);

      if (!autoRestored.current && data.conversations.length > 0) {
        autoRestored.current = true;
        const latest = data.conversations[0];
        setActiveConvId(latest.id);
        setMessages([]);
        setRatings({});
        setLoadingMsgs(true);
        try {
          const msgData = await api.getMessages(latest.id);
          setMessages(msgData.messages as UIMessage[]);
        } catch {
          /* ignore — sidebar still shows the list */
        } finally {
          setLoadingMsgs(false);
        }
      }
    } catch {
      /* ignore */
    } finally {
      setLoadingConvs(false);
    }
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  // ── Scroll to bottom ───────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Select conversation ────────────────────────────────────────────────────
  const selectConversation = async (convId: string) => {
    setActiveConvId(convId);
    setMessages([]);
    setRatings({});
    setLoadingMsgs(true);
    try {
      const data = await api.getMessages(convId);
      setMessages(data.messages as UIMessage[]);
    } catch {
      /* ignore */
    } finally {
      setLoadingMsgs(false);
    }
  };

  // ── New conversation ───────────────────────────────────────────────────────
  const newConversation = async () => {
    try {
      const conv = await api.createConversation("chat", user?.department);
      setConversations((prev) => [conv, ...prev]);
      setActiveConvId(conv.id);
      setMessages([]);
      setRatings({});
    } catch {
      /* ignore */
    }
  };

  // ── Delete conversation ────────────────────────────────────────────────────
  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        setActiveConvId(null);
        setMessages([]);
      }
    } catch {
      /* ignore */
    }
  };

  // ── Send message ───────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const userText = input.trim();
    setInput("");

    // Create a conversation automatically if none is active
    let convId = activeConvId;
    if (!convId) {
      try {
        const conv = await api.createConversation("chat", user?.department);
        convId = conv.id;
        setActiveConvId(conv.id);
        setConversations((prev) => [conv, ...prev]);
      } catch {
        /* ignore */
      }
    }

    const userMsg: UIMessage = {
      id: Date.now(),
      conversation_id: convId ?? "",
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);

    // Save user message
    if (convId) {
      api.appendMessage(convId, "user", userText).catch(() => {});
    }

    const deptCode = availableIndexes.find((i) => i.name === selectedIndex)?.dept
      ?? user?.department ?? "general";

    try {
      const response = await fetch(`${getBackendBase()}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({
          messages: [...messages, userMsg].map((m) => ({ role: m.role, content: m.content })),
          department: deptCode,
        }),
      });
      const data = await response.json();
      const assistantMsg: UIMessage = {
        id: Date.now() + 1,
        conversation_id: convId ?? "",
        role: "assistant",
        content: data.response || data.detail || "No response received",
        source: data.source,
        source_label: data.source_label,
        sourceGuard: data.source_guard,
        sources: data.sources,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Save assistant message + refresh sidebar title
      if (convId) {
        api.appendMessage(
          convId, "assistant", assistantMsg.content,
          data.source, data.source_label,
        ).then(() => loadConversations()).catch(() => {});
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          conversation_id: convId ?? "",
          role: "assistant",
          content: "Sorry, I encountered an error connecting to the Huron backend.",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── Feedback ───────────────────────────────────────────────────────────────
  const handleFeedback = async (idx: number, rating: 1 | -1) => {
    if (ratings[idx] !== undefined) return;
    setRatings((prev) => ({ ...prev, [idx]: rating }));
    const msg = messages[idx];
    if (!msg) return;
    try {
      await api.submitFeedback({
        query:     messages[idx - 1]?.content ?? "",
        response:  msg.content,
        rating,
        source:    msg.source ?? "general_knowledge",
        dept_code: user?.department ?? "general",
      });
    } catch { /* ignore */ }
  };

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-[calc(100vh-8rem)] gap-0 overflow-hidden rounded-xl border border-border">

      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <div className={`flex flex-col border-r border-border bg-card transition-all duration-200 ${sidebarOpen ? "w-64 min-w-[200px]" : "w-0 overflow-hidden"}`}>
        <div className="flex items-center justify-between p-3 border-b border-border shrink-0">
          <span className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">History</span>
          <button
            onClick={newConversation}
            className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            title="New conversation"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loadingConvs ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-8 px-2">
              No conversations yet.<br />Send a message to start.
            </p>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors group flex items-start gap-2 ${
                  activeConvId === conv.id
                    ? "bg-primary/10 text-primary"
                    : "hover:bg-accent text-foreground"
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 mt-0.5 shrink-0 opacity-60" />
                <div className="flex-1 min-w-0">
                  <p className="truncate font-medium leading-tight">{conv.title}</p>
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mt-0.5">
                    <Clock className="h-2.5 w-2.5" />
                    {formatTime(conv.updated_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => deleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-500 transition-all shrink-0 mt-0.5"
                  title="Delete"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </button>
            ))
          )}
        </div>
      </div>

      {/* ── Main chat area ────────────────────────────────────────────────── */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground"
              title={sidebarOpen ? "Hide history" : "Show history"}
            >
              <ChevronLeft className={`h-4 w-4 transition-transform ${sidebarOpen ? "" : "rotate-180"}`} />
            </button>
            <Bot className="h-5 w-5 text-primary" />
            <span className="font-semibold">Chat Assistant</span>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={selectedIndex}
              onChange={(e) => setSelectedIndex(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-background border border-border text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {availableIndexes.length > 0 ? (
                availableIndexes.map((idx) => (
                  <option key={idx.name} value={idx.name}>
                    {idx.name} ({idx.documents} docs)
                  </option>
                ))
              ) : (
                <option value="">General knowledge mode</option>
              )}
            </select>
            <button
              onClick={newConversation}
              className="p-1.5 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground"
              title="New conversation"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto bg-background">
          {loadingMsgs ? (
            <div className="flex items-center justify-center h-full gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
              Loading conversation…
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <div className="text-center px-4">
                <Bot className="h-12 w-12 mx-auto mb-4 opacity-30" />
                <p className="font-medium">Start a conversation</p>
                <p className="text-sm mt-1 opacity-70">
                  {availableIndexes.length > 0
                    ? "Answers grounded in your department's indexed documents."
                    : "No documents indexed — answering from general AI knowledge."}
                </p>
              </div>
            </div>
          ) : (
            <div className="p-4 space-y-4">
              {messages.map((msg, idx) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0 mt-1">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}

                  <div className="max-w-[72%] flex flex-col gap-1">
                    <div className={`rounded-2xl px-4 py-3 ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-accent"}`}>
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>

                      {msg.sources && msg.sources.length > 0 && (
                        <p className="text-xs mt-2 opacity-70">
                          Sources: {msg.sources.map((s) => s.title).join(", ")}
                        </p>
                      )}

                      {msg.role === "assistant" && msg.source === "general_knowledge" && (
                        <div className="mt-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-600 dark:text-amber-400 font-medium">
                            ⚡ General knowledge
                          </span>
                          {msg.source_label && (
                            <span className="text-xs text-muted-foreground ml-1">{msg.source_label}</span>
                          )}
                        </div>
                      )}

                      {msg.role === "assistant" && msg.source === "rag" && msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-600 dark:text-green-400 font-medium">
                            📄 From knowledge base
                          </span>
                        </div>
                      )}

                      {msg.sourceGuard && !msg.sourceGuard.passed && (
                        <div className="mt-2 flex items-start gap-1.5 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                          <ShieldAlert className="h-3.5 w-3.5 text-red-500 shrink-0 mt-0.5" />
                          <div>
                            <p className="text-xs font-medium text-red-600 dark:text-red-400">Source guard warning</p>
                            <p className="text-xs text-muted-foreground mt-0.5">
                              {msg.sourceGuard.warning ?? "Response may not be fully grounded in source documents."}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Confidence: {Math.round(msg.sourceGuard.score * 100)}%
                            </p>
                          </div>
                        </div>
                      )}

                      <p className={`text-xs mt-1 ${msg.role === "user" ? "text-primary-foreground/70" : "text-muted-foreground"}`}>
                        {formatTime(msg.created_at)}
                      </p>
                    </div>

                    {msg.role === "assistant" && (
                      <div className="flex items-center gap-1 pl-1">
                        {([1, -1] as const).map((r) => (
                          <button
                            key={r}
                            onClick={() => handleFeedback(idx, r)}
                            disabled={ratings[idx] !== undefined}
                            className={`p-1.5 rounded-lg transition-colors disabled:cursor-default ${
                              ratings[idx] === r
                                ? r === 1 ? "text-green-600 bg-green-500/15" : "text-red-600 bg-red-500/15"
                                : r === 1 ? "text-muted-foreground hover:text-green-600 hover:bg-green-500/10"
                                          : "text-muted-foreground hover:text-red-600 hover:bg-red-500/10"
                            }`}
                          >
                            {r === 1 ? <ThumbsUp className="h-3.5 w-3.5" /> : <ThumbsDown className="h-3.5 w-3.5" />}
                          </button>
                        ))}
                        {ratings[idx] !== undefined && (
                          <span className="text-xs text-muted-foreground ml-1">
                            {ratings[idx] === 1 ? "Thanks!" : "We'll improve this."}
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  {msg.role === "user" && (
                    <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0 mt-1">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))}

              {sending && (
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
        <div className="px-4 py-3 border-t border-border shrink-0">
          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message… (Enter to send)"
              rows={1}
              className="flex-1 px-4 py-2.5 rounded-xl bg-background border border-border focus:outline-none focus:ring-2 focus:ring-ring resize-none text-sm"
            />
            <button
              onClick={handleSend}
              disabled={sending || !input.trim()}
              className="px-4 py-2.5 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {sending ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatInterface;
