"use client";
import { useState, useRef, useEffect } from "react";
import { ACHARYA_META } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const DEBATES_KEY = "gita_debates";

interface DebateMessage {
  role: string;
  content: string;
}

interface DebateTurn {
  speaker: string;
  name: string;
  content: string;
  source_verses: string[];
}

interface SavedDebate {
  id: string;
  topic: string;
  history: DebateMessage[];
  displayedTurns: DebateTurn[];
  createdAt: number;
  updatedAt: number;
}

const COLOR_STYLES: Record<string, { card: string; badge: string; dot: string; name: string; border: string }> = {
  blue:  { card: "bg-blue-50",   badge: "bg-blue-100 text-blue-700",   dot: "bg-blue-500",   name: "text-blue-700",  border: "border-blue-200" },
  amber: { card: "bg-amber-50",  badge: "bg-amber-100 text-amber-700", dot: "bg-amber-500",  name: "text-amber-700", border: "border-amber-200" },
  green: { card: "bg-green-50",  badge: "bg-green-100 text-green-700", dot: "bg-green-500",  name: "text-green-700", border: "border-green-200" },
};

const SAMPLE_TOPICS = [
  "Does liberation require complete renunciation of action?",
  "Is the personal or impersonal aspect of the Absolute primary?",
  "What is the relationship between knowledge and devotion?",
  "Is the soul identical to, or distinct from, Brahman?",
];

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function timeAgo(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function DebatePage() {
  const [debates, setDebates] = useState<SavedDebate[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [interjection, setInterjection] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Load from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(DEBATES_KEY);
      if (saved) {
        const parsed: SavedDebate[] = JSON.parse(saved);
        setDebates(parsed);
        if (parsed.length > 0) setActiveId(parsed[0].id);
      }
    } catch {}
    setHydrated(true);
  }, []);

  // Save to localStorage whenever debates change
  useEffect(() => {
    if (!hydrated) return;
    try { localStorage.setItem(DEBATES_KEY, JSON.stringify(debates)); } catch {}
  }, [debates, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [debates, activeId, loading]);

  const active = debates.find(d => d.id === activeId) ?? null;

  function updateActive(patch: Partial<SavedDebate>) {
    setDebates(prev => prev.map(d => d.id === activeId ? { ...d, ...patch, updatedAt: Date.now() } : d));
  }

  async function startDebate(t?: string) {
    const chosenTopic = (t ?? topic).trim();
    if (!chosenTopic || loading) return;
    setTopic("");
    setError("");

    const newDebate: SavedDebate = {
      id: uid(),
      topic: chosenTopic,
      history: [{ role: "topic", content: chosenTopic }],
      displayedTurns: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setDebates(prev => [newDebate, ...prev]);
    setActiveId(newDebate.id);
    await fetchTurns(newDebate, "");
  }

  async function continueDebate() {
    if (!active || loading) return;
    const inj = interjection.trim();
    setInterjection("");
    await fetchTurns(active, inj);
  }

  async function fetchTurns(debate: SavedDebate, inj: string) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/debate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topic: debate.topic,
          history: debate.history,
          turns: 3,
          user_interjection: inj,
        }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data: { topic: string; turns: DebateTurn[] } = await res.json();

      const newHistory: DebateMessage[] = [
        ...debate.history,
        ...(inj ? [{ role: "user", content: inj }] : []),
        ...data.turns.map(t => ({ role: t.speaker, content: t.content })),
      ];

      setDebates(prev => prev.map(d =>
        d.id === debate.id
          ? {
              ...d,
              history: newHistory,
              displayedTurns: [...d.displayedTurns, ...data.turns],
              updatedAt: Date.now(),
            }
          : d
      ));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function deleteDebate(id: string) {
    setDebates(prev => {
      const next = prev.filter(d => d.id !== id);
      if (activeId === id) setActiveId(next[0]?.id ?? null);
      return next;
    });
  }

  const showCanvas = activeId !== null;

  return (
    <div className="flex h-[calc(100vh-120px)] gap-4">

      {/* ── Sidebar ── */}
      <div className={`flex flex-col shrink-0 transition-all duration-200 ${sidebarOpen ? "w-56" : "w-10"}`}>
        {/* Sidebar toggle + New button */}
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setSidebarOpen(o => !o)}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d={sidebarOpen ? "M11 19l-7-7 7-7M18 19l-7-7 7-7" : "M13 5l7 7-7 7M6 5l7 7-7 7"} />
            </svg>
          </button>
          {sidebarOpen && (
            <button
              onClick={() => { setActiveId(null); setTopic(""); setError(""); }}
              className="flex-1 text-xs text-stone-600 bg-white border border-stone-200 hover:border-amber-300 hover:text-amber-700 px-2 py-1.5 rounded-lg transition-colors text-left"
            >
              + New debate
            </button>
          )}
        </div>

        {/* Debate list */}
        {sidebarOpen && (
          <div className="flex-1 overflow-y-auto space-y-1">
            {debates.length === 0 && (
              <p className="text-xs text-stone-400 px-1 pt-2">No debates yet</p>
            )}
            {debates.map(d => (
              <div
                key={d.id}
                onClick={() => { setActiveId(d.id); setError(""); }}
                className={`group relative w-full text-left px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                  d.id === activeId
                    ? "bg-amber-50 border border-amber-200"
                    : "hover:bg-stone-100 border border-transparent"
                }`}
              >
                <p className={`text-xs font-medium leading-snug line-clamp-2 pr-5 ${d.id === activeId ? "text-amber-800" : "text-stone-700"}`}>
                  {d.topic}
                </p>
                <p className="text-[10px] text-stone-400 mt-1">{timeAgo(d.updatedAt)} · {d.displayedTurns.length} turns</p>
                {/* Delete button */}
                <button
                  onClick={e => { e.stopPropagation(); deleteDebate(d.id); }}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 text-stone-300 hover:text-red-400 transition-all p-0.5 rounded"
                  title="Delete"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Main canvas ── */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Header */}
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-stone-800">
            {active ? active.topic : "Acharya Debate"}
          </h1>
          <p className="text-stone-500 text-sm mt-0.5">
            {active
              ? "The three acharyas debate this topic with each other"
              : "Set a topic and watch the acharyas argue it out in real time"}
          </p>
        </div>

        {/* Legend */}
        <div className="flex gap-4 mb-4">
          {Object.entries(ACHARYA_META).map(([key, meta]) => {
            const s = COLOR_STYLES[meta.color];
            return (
              <div key={key} className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${s.dot}`} />
                <span className={`text-xs font-medium ${s.name}`}>{meta.short}</span>
              </div>
            );
          })}
        </div>

        {/* Turns area */}
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">

          {/* New debate empty state */}
          {!showCanvas && (
            <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
              <p className="text-stone-400 text-sm max-w-sm">
                Set a philosophical topic and watch the three acharyas debate it live — each pressing their own tradition.
              </p>
              <div className="flex flex-col gap-2 w-full max-w-md">
                {SAMPLE_TOPICS.map(q => (
                  <button
                    key={q}
                    onClick={() => startDebate(q)}
                    className="text-sm text-left text-stone-600 bg-white border border-stone-200 hover:border-amber-300 hover:text-amber-700 px-4 py-3 rounded-xl transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Active debate turns */}
          {active?.displayedTurns.map((turn, i) => {
            const meta = ACHARYA_META[turn.speaker];
            const s = COLOR_STYLES[meta?.color ?? "blue"];
            return (
              <div key={i} className={`border ${s.border} rounded-2xl p-4 ${s.card}`}>
                <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${s.dot}`} />
                    <span className={`text-xs font-semibold ${s.name}`}>
                      {meta?.short ?? turn.speaker}
                    </span>
                  </div>
                  {turn.source_verses.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {turn.source_verses.slice(0, 3).map(v => (
                        <a
                          key={v}
                          href={`/verse/${v.replace("BG ", "").replace(".", "/")}`}
                          className={`text-xs px-2 py-0.5 rounded-full ${s.badge} hover:opacity-80 transition-opacity`}
                        >
                          {v}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-line">
                  {turn.content}
                </p>
              </div>
            );
          })}

          {/* Loading skeleton */}
          {loading && (
            <div className="space-y-3">
              {["blue", "amber", "green"].map(color => (
                <div key={color} className={`border rounded-2xl p-4 animate-pulse ${COLOR_STYLES[color].card} ${COLOR_STYLES[color].border}`}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className={`w-2 h-2 rounded-full ${COLOR_STYLES[color].dot}`} />
                    <div className="h-3 w-28 bg-stone-200 rounded" />
                  </div>
                  <div className="space-y-2">
                    <div className="h-3 bg-stone-200 rounded w-full" />
                    <div className="h-3 bg-stone-200 rounded w-5/6" />
                    <div className="h-3 bg-stone-200 rounded w-3/4" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-sm text-red-700">{error}</div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Bottom controls */}
        {!showCanvas ? (
          <div className="mt-4 bg-white border border-stone-200 rounded-2xl p-3 flex gap-3 items-end">
            <textarea
              value={topic}
              onChange={e => setTopic(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); startDebate(); } }}
              placeholder="Enter a philosophical topic… (Enter to start)"
              rows={2}
              className="flex-1 resize-none text-sm focus:outline-none bg-transparent text-stone-800 placeholder-stone-400"
            />
            <button
              onClick={() => startDebate()}
              disabled={loading || !topic.trim()}
              className="bg-amber-600 hover:bg-amber-700 disabled:bg-stone-200 disabled:text-stone-400 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shrink-0"
            >
              Start
            </button>
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            <div className="bg-white border border-stone-200 rounded-2xl p-3 flex gap-3 items-end">
              <input
                type="text"
                value={interjection}
                onChange={e => setInterjection(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); continueDebate(); } }}
                placeholder="Interject with a question (optional)…"
                className="flex-1 text-sm focus:outline-none bg-transparent text-stone-800 placeholder-stone-400 py-1"
              />
              <button
                onClick={continueDebate}
                disabled={loading}
                className="bg-amber-600 hover:bg-amber-700 disabled:bg-stone-200 disabled:text-stone-400 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shrink-0"
              >
                {loading ? "…" : "Continue"}
              </button>
            </div>
            <p className="text-xs text-stone-400 text-center">
              Each click generates 3 more turns · {active?.displayedTurns.length ?? 0} turns so far
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
