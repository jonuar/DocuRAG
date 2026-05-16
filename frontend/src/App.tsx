import { useEffect, useMemo, useRef, useState } from "react";
import type { ChatMode, SourceItem, Technology } from "./api";
import { fetchTechnologies, sendChat } from "./api";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  meta?: { latency_ms?: number };
};

type ChatThread = {
  id: string;
  title: string;
  last: string;
  updatedAt: number;
  messages: ChatMessage[];
};

function nowId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function initialThread(): ChatThread {
  const id = nowId();
  return {
    id,
    title: "DocuRAG Chat",
    last: "Ask about your indexed docs…",
    updatedAt: Date.now(),
    messages: [
      {
        id: nowId(),
        role: "assistant",
        content: "Hi. Ask a technical question and I’ll answer using your indexed documentation.",
      },
    ],
  };
}

export default function App() {
  const [techs, setTechs] = useState<Technology[]>([]);
  const [tech, setTech] = useState<string | null>(null);
  const [mode, setMode] = useState<ChatMode>("rag");

  const [threads, setThreads] = useState<ChatThread[]>(() => {
    return [initialThread()];
  });
  const [activeThreadId, setActiveThreadId] = useState(() => threads[0].id);
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState<string>("");

  const activeThread = useMemo(
    () => threads.find((t) => t.id === activeThreadId) ?? threads[0],
    [threads, activeThreadId]
  );

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const inFlightAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchTechnologies(ac.signal)
      .then((data) => {
        setTechs(data.technologies);
        if (!tech && data.technologies.length > 0) setTech(data.technologies[0].key);
      })
      .catch((e) => setStatus(String(e?.message ?? e)))
      .finally(() => void 0);
    return () => ac.abort();
  }, [tech]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeThread.messages.length]);

  async function onSend() {
    const message = input.trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);
    setStatus("");

    const ac = new AbortController();
    inFlightAbortRef.current = ac;

    const userMsg: ChatMessage = { id: nowId(), role: "user", content: message };
    const placeholder: ChatMessage = {
      id: nowId(),
      role: "assistant",
      content: "Thinking…",
    };

    setThreads((prev) =>
      prev.map((t) =>
        t.id === activeThreadId
          ? {
              ...t,
              last: message,
              updatedAt: Date.now(),
              messages: [...t.messages, userMsg, placeholder],
            }
          : t
      )
    );

    try {
      const result = await sendChat(message, tech, mode, ac.signal);
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id !== activeThreadId) return t;
          const msgs = [...t.messages];
          const idx = msgs.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            msgs[idx] = {
              id: placeholder.id,
              role: "assistant",
              content: result.answer,
              sources: result.sources,
              meta: { latency_ms: result.latency_ms },
            };
          }
          const title =
            t.title === "DocuRAG Chat" && message.length <= 42
              ? message
              : t.title;
          return { ...t, title, messages: msgs };
        })
      );
    } catch (e: any) {
      const isAbort =
        e?.name === "AbortError" ||
        String(e?.message ?? "").toLowerCase().includes("aborted");
      setThreads((prev) =>
        prev.map((t) => {
          if (t.id !== activeThreadId) return t;
          const msgs = [...t.messages];
          const idx = msgs.findIndex((m) => m.id === placeholder.id);
          if (idx >= 0) {
            msgs[idx] = {
              ...placeholder,
              content: isAbort
                ? "Request canceled."
                : "Request failed. Make sure the API is running on http://localhost:8000.\n\n" +
                  String(e?.message ?? e),
            };
          }
          return { ...t, messages: msgs };
        })
      );
    } finally {
      setBusy(false);
      inFlightAbortRef.current = null;
    }
  }

  function onStop() {
    inFlightAbortRef.current?.abort();
    inFlightAbortRef.current = null;
    setBusy(false);
  }

  function newChat() {
    const id = nowId();
    const t: ChatThread = {
      id,
      title: "New chat",
      last: "",
      updatedAt: Date.now(),
      messages: [
        {
          id: nowId(),
          role: "assistant",
          content: "New chat ready. Pick a technology and ask your question.",
        },
      ],
    };
    setThreads((prev) => [t, ...prev]);
    setActiveThreadId(id);
    setRenameId(null);
  }

  function startRename(threadId: string) {
    const t = threads.find((x) => x.id === threadId);
    if (!t) return;
    setRenameId(threadId);
    setRenameValue(t.title);
  }

  function commitRename(threadId: string) {
    const name = renameValue.trim();
    if (!name) return;
    setThreads((prev) => prev.map((t) => (t.id === threadId ? { ...t, title: name } : t)));
    setRenameId(null);
  }

  function cancelRename() {
    setRenameId(null);
  }

  function deleteThread(threadId: string) {
    setThreads((prev) => {
      const remaining = prev.filter((t) => t.id !== threadId);
      if (remaining.length === 0) {
        const fallback = initialThread();
        setActiveThreadId(fallback.id);
        return [fallback];
      }
      if (activeThreadId === threadId) setActiveThreadId(remaining[0].id);
      return remaining;
    });
    if (renameId === threadId) setRenameId(null);
  }

  return (
    <div className="app-shell">
      <div className="chrome">
        <div className="panel sidebar" aria-label="Sidebar">
          <div className="brand">
            <div className="avatar">D</div>
            <div>
              <strong>DocuRAG</strong>
              <span className="subtle">Local technical docs</span>
            </div>
          </div>
          <div className="nav">
            <button className="active">
              <span className="dot" />
              Chats
            </button>
            <button disabled title="Coming soon">
              <span className="dot" />
              Ingest (soon)
            </button>
          </div>
          <div className="sidebar-divider" />
          <div className="chats-header">
            <div className="panel-title">Your chats</div>
            <button className="icon-btn" onClick={newChat} title="New chat" aria-label="New chat">
              +
            </button>
          </div>
          <div className="list" style={{ overflow: "auto", paddingTop: 8, flex: 1 }}>
            {threads.map((t) => (
              <div
                key={t.id}
                className={`row ${t.id === activeThreadId ? "active" : ""}`}
                onClick={() => setActiveThreadId(t.id)}
                role="button"
                tabIndex={0}
              >
                <div className="avatar" style={{ width: 30, height: 30, borderRadius: 12 }}>
                  {t.title.slice(0, 1).toUpperCase()}
                </div>
                <div className="meta">
                  {renameId === t.id ? (
                    <input
                      className="rename-input"
                      value={renameValue}
                      autoFocus
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          commitRename(t.id);
                        } else if (e.key === "Escape") {
                          e.preventDefault();
                          cancelRename();
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      onBlur={() => commitRename(t.id)}
                      aria-label="Rename chat"
                    />
                  ) : (
                    <>
                      <strong>{t.title}</strong>
                      <span>{t.last || "—"}</span>
                    </>
                  )}
                </div>
                <div className="time">{formatTime(t.updatedAt)}</div>
                <div className="actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    className="icon-btn"
                    title="Rename"
                    aria-label="Rename"
                    onClick={() => startRename(t.id)}
                  >
                    ✎
                  </button>
                  <button
                    className="icon-btn danger"
                    title="Delete"
                    aria-label="Delete"
                    onClick={() => deleteThread(t.id)}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="sidebar-footer">
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
              API Docs
            </a>
            <span>v0.1</span>
          </div>
        </div>

        <div className="panel chat">
          <div className="panel-header">
            <div style={{ display: "grid", gap: 2 }}>
              <div className="panel-title">{activeThread.title}</div>
              <div className="subtle">
                {tech ? `Technology: ${tech}` : "Loading technologies…"}
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <select
                className="select"
                value={tech ?? ""}
                onChange={(e) => setTech(e.target.value || null)}
                aria-label="Technology"
              >
                {techs.length === 0 ? (
                  <option value="">No technologies</option>
                ) : (
                  techs.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.name} ({t.chunks})
                    </option>
                  ))
                )}
              </select>
              <select
                className="select"
                value={mode}
                onChange={(e) => setMode(e.target.value as ChatMode)}
                aria-label="Mode"
              >
                <option value="rag">RAG</option>
                <option value="agent">Agent</option>
              </select>
            </div>
          </div>

          <div className="chat-body">
            {activeThread.messages.map((m) => (
              <div key={m.id} className={`bubble ${m.role === "user" ? "user" : ""}`}>
                {m.content}
                {m.role === "assistant" && m.sources && m.sources.length > 0 ? (
                  <div className="sources">
                    <div>
                      Sources ({m.sources.length}){" "}
                      {m.meta?.latency_ms != null ? (
                        <span className="subtle">· {m.meta.latency_ms}ms</span>
                      ) : null}
                    </div>
                    {m.sources.map((s, idx) => (
                      <a key={`${s.url}_${idx}`} href={s.url} target="_blank" rel="noreferrer">
                        {s.section ? s.section : s.url}
                      </a>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-footer">
            <input
              className="input"
              placeholder="Write a message…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!busy) void onSend();
                }
              }}
              disabled={busy}
            />
            <button
              className="send"
              onClick={() => (busy ? onStop() : void onSend())}
              disabled={busy ? false : !input.trim()}
              title={busy ? "Stop (cancel request)" : "Send"}
            >
              {busy ? "Stop" : "Send"}
            </button>
            {status ? (
              <div style={{ gridColumn: "1 / -1" }} className="subtle">
                {status}
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
