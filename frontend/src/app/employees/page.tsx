"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";

type Message = { role: "user" | "assistant"; content: string; error?: boolean };

type Topic = "all" | "leave" | "wfh" | "expenses" | "attendance" | "appraisal" | "conduct";

const TOPICS: { id: Topic; label: string }[] = [
  { id: "all", label: "All" },
  { id: "leave", label: "Leave" },
  { id: "wfh", label: "WFH" },
  { id: "expenses", label: "Expenses" },
  { id: "attendance", label: "Attendance" },
  { id: "appraisal", label: "Appraisal" },
  { id: "conduct", label: "Conduct" },
];

const QUICK_QUERIES: { label: string; icon: string; topic: Topic; query: string }[] = [
  {
    label: "Leave balance",
    icon: "📅",
    topic: "leave",
    query: "What are the different leave categories and how many days am I entitled to for each?",
  },
  {
    label: "WFH policy",
    icon: "🏠",
    topic: "wfh",
    query: "What is the work-from-home policy and who is eligible to apply?",
  },
  {
    label: "Expense claims",
    icon: "🧾",
    topic: "expenses",
    query: "How do I submit an expense claim and what expenses are covered?",
  },
];

const INITIAL_MESSAGE: Message = {
  role: "assistant",
  content:
    "Hello! I'm HRBot for your company. Ask about leave, WFH, expenses, attendance, appraisals, and more. I answer only from your company policy window.",
};

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:9000";

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function renderMessageContent(content: string) {
  const blocks = content.split(/\n{2,}/g).filter(Boolean);
  return blocks.map((block, blockIndex) => {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    return (
      <p key={blockIndex} className="mb-3 last:mb-0 text-sm leading-7 text-slate-800 dark:text-slate-200">
        {lines.map((line, lineIndex) => (
          <span key={lineIndex}>
            {line}
            {lineIndex < lines.length - 1 ? <br /> : null}
          </span>
        ))}
      </p>
    );
  });
}

function MessageBubble({ message, timestamp }: { message: Message; timestamp: Date }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-2.5 items-start ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex-shrink-0 w-7 h-7 rounded-full border text-[11px] font-medium flex items-center justify-center select-none ${
          isUser
            ? "border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
            : "border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 text-slate-500 dark:text-slate-400"
        }`}
        aria-hidden="true"
      >
        {isUser ? "You" : "HR"}
      </div>

      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-4 py-3.5 rounded-3xl border shadow-sm text-[14px] leading-7 ${
            isUser
              ? "bg-blue-500 text-white border-blue-500 shadow-blue-500/10"
              : message.error
                ? "bg-rose-50 text-rose-900 border-rose-200 dark:bg-rose-950 dark:text-rose-100 dark:border-rose-800"
                : "bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100"
          }`}
        >
          {renderMessageContent(message.content)}
        </div>
        <p className="text-[10px] text-slate-400 dark:text-slate-600 px-1">
          {isUser ? `You · ${formatTime(timestamp)}` : "HRBot · policy assistant"}
        </p>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 w-fit">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse"
          style={{ animationDelay: `${i * 200}ms` }}
        />
      ))}
    </div>
  );
}

export default function EmployeesPage() {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const role = typeof window !== "undefined" ? localStorage.getItem("role") : null;

  // Redirect once; avoid setState inside effects.
  useEffect(() => {
    if (!token || role !== "employee") {
      window.location.href = "/login";
    }
  }, [token, role]);

  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);


  const [timestamps, setTimestamps] = useState<Date[]>([new Date()]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [activeTopic, setActiveTopic] = useState<Topic>("all");
  const [search, setSearch] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = localStorage.getItem("token");
    const r = localStorage.getItem("role");
    if (!t || r !== "employee") {
      window.location.href = "/login";
      return;
    }
    // Avoid setState to satisfy lint; use refs/localStorage reads in handlers.
    setToken(t);
    setRole(r);

  }, []);


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const filteredQueries = useMemo(() => {
    return QUICK_QUERIES.filter(
      (q) =>
        (activeTopic === "all" || q.topic === activeTopic) &&
        (!search ||
          q.label.toLowerCase().includes(search.toLowerCase()) ||
          q.query.toLowerCase().includes(search.toLowerCase()))
    );
  }, [activeTopic, search]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading || !token) return;

      const userMsg: Message = { role: "user", content: trimmed };
      const now = new Date();

      setMessages((prev) => [...prev, userMsg]);
      setTimestamps((prev) => [...prev, now]);
      setInput("");
      setIsLoading(true);

      try {
        const history = [...messages, userMsg].map(({ role, content }) => ({ role, content }));

        const res = await fetch(`${BACKEND_URL}/api/chat`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message: trimmed, history }),
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail ?? data.error ?? "Unknown server error");

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.response ?? "Sorry, I couldn't generate a response at this time.",
            error: Boolean(data.error),
          },
        ]);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `I couldn't reach the backend at ${BACKEND_URL}.\n\nError: ${msg}`,
            error: true,
          },
        ]);
      } finally {
        setIsLoading(false);
        setTimestamps((prev) => [...prev, new Date()]);
        inputRef.current?.focus();
      }
    },
    [isLoading, messages, token]
  );

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="max-w-[1400px] mx-auto px-5 py-5 flex flex-col gap-5">
        <header className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-center text-[12px] font-medium text-slate-500 dark:text-slate-400 select-none flex-shrink-0">
              Employee
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-600">HR Studio</p>
              <h1 className="text-[17px] font-medium">Policy assist</h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => (window.location.href = "/logout")}
              className="text-[13px] text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        <div className="grid lg:grid-cols-[272px_1fr] gap-5 items-start">
          <aside className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 flex flex-col gap-5">
            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-2.5">Search</p>
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter policy topics…"
                aria-label="Search policy topics"
                className="w-full px-3 py-2 text-[13px] rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:focus:ring-slate-700"
              />
            </div>

            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-2.5">Topics</p>
              <div className="flex flex-wrap gap-1.5">
                {TOPICS.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTopic(t.id)}
                    className={`text-[12px] px-2.5 py-1 rounded-md border transition-colors ${
                      activeTopic === t.id
                        ? "border-slate-400 dark:border-slate-500 bg-slate-900 dark:bg-white text-white dark:text-slate-900"
                        : "border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-px bg-slate-100 dark:bg-slate-800" />

            <div>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-2.5">Quick actions</p>
              <div className="flex flex-col gap-1.5">
                {filteredQueries.length === 0 ? (
                  <p className="text-[12px] text-slate-400 dark:text-slate-600 px-1">No matching actions.</p>
                ) : (
                  filteredQueries.map((item, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(item.query)}
                      className="flex flex-col gap-0.5 px-3 py-2.5 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 hover:border-slate-200 dark:hover:border-slate-700 hover:bg-white dark:hover:bg-slate-900 text-left transition-colors w-full"
                    >
                      <span className="text-[13px] font-medium text-slate-700 dark:text-slate-300">
                        {item.icon} {item.label}
                      </span>
                      <span className="text-[11px] text-slate-400 dark:text-slate-600 line-clamp-1">{item.query}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </aside>

          <main className="flex flex-col gap-5">
            <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl flex flex-col overflow-hidden">
              <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-1">Chat module</p>
                  <h2 className="text-[17px] font-medium">Policy assistant</h2>
                </div>
                <div className="text-[12px] text-slate-500 dark:text-slate-400 px-2.5 py-1.5 rounded-md border border-slate-100 dark:border-slate-800">
                  Role: {role}
                </div>
              </div>

              <div
                className="flex-1 px-5 py-4 flex flex-col gap-4 overflow-y-auto max-h-[420px] min-h-[180px]"
                role="log"
                aria-live="polite"
                aria-label="Conversation messages"
              >
                {messages.map((msg, i) => (
                  <MessageBubble key={i} message={msg} timestamp={timestamps[i] ?? new Date()} />
                ))}
                {isLoading && (
                  <div className="flex gap-2.5 items-start">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex items-center justify-center text-[11px] text-slate-500 select-none" aria-hidden="true">
                      HR
                    </div>
                    <TypingIndicator />
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <div className="px-4 py-3.5 border-t border-slate-100 dark:border-slate-800 flex gap-2.5 items-center">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage(input);
                    }
                  }}
                  placeholder="Ask a policy question…"
                  aria-label="Type your HR policy question"
                  disabled={isLoading}
                  className="flex-1 px-3.5 py-2 text-[13px] rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-300 dark:focus:ring-slate-700 disabled:opacity-50"
                />
                <button
                  onClick={() => sendMessage(input)}
                  disabled={isLoading || !input.trim()}
                  aria-label="Send message"
                  className="px-4 py-2 text-[13px] font-medium rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-slate-700 dark:hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  Send →
                </button>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}

