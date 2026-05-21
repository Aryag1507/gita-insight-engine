"use client";
import { useState, useRef, useEffect } from "react";
import { ACHARYA_META } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STORAGE_KEY = "gita_chat_turns";
const SELECTED_KEY = "gita_chat_selected";

interface ChatMessage {
  role: "user" | "prabhupada" | "vishvanatha" | "baladeva";
  content: string;
}

interface ChatTurn {
  acharya: string;
  name: string;
  reply: string;
  source_verses: string[];
}

interface Turn {
  userMessage: string;
  replies: ChatTurn[];
  pendingAcharyas: string[];
}

const ALL_ACHARYAS = ["prabhupada", "vishvanatha", "baladeva"];

const COLOR_STYLES: Record<string, { card: string; badge: string; dot: string; name: string; selector: string; selectorActive: string }> = {
  blue:  {
    card: "bg-blue-50 border-blue-200",
    badge: "bg-blue-100 text-blue-700",
    dot: "bg-blue-500",
    name: "text-blue-700",
    selector: "border-blue-200 text-blue-700 hover:bg-blue-50",
    selectorActive: "bg-blue-600 border-blue-600 text-white",
  },
  amber: {
    card: "bg-amber-50 border-amber-200",
    badge: "bg-amber-100 text-amber-700",
    dot: "bg-amber-500",
    name: "text-amber-700",
    selector: "border-amber-200 text-amber-700 hover:bg-amber-50",
    selectorActive: "bg-amber-600 border-amber-600 text-white",
  },
  green: {
    card: "bg-green-50 border-green-200",
    badge: "bg-green-100 text-green-700",
    dot: "bg-green-500",
    name: "text-green-700",
    selector: "border-green-200 text-green-700 hover:bg-green-50",
    selectorActive: "bg-green-600 border-green-600 text-white",
  },
};

const SAMPLE_QUESTIONS: Record<string, string[]> = {
  all: [
    "What is the nature of the eternal soul?",
    "How does one overcome fear and grief?",
    "What is the difference between karma and bhakti yoga?",
    "Who is qualified to receive spiritual knowledge?",
  ],
  prabhupada: [
    "What does it mean to be Krishna conscious?",
    "Why is devotional service the highest path?",
    "What is maya, and how do we overcome it?",
    "Who is a bona fide spiritual master?",
  ],
  vishvanatha: [
    "What is the inner meaning of surrender in verse 18.66?",
    "How does rasa relate to liberation?",
    "What is the difference between vaidhi and raganuga bhakti?",
    "What is the mood of the gopis toward Krishna?",
  ],
  baladeva: [
    "How does the Gita establish the distinction between jiva and Brahman?",
    "What is the Vedantic proof that the soul is eternal?",
    "How does Krishna's role as teacher establish his supremacy?",
    "What is the logical basis for accepting scriptural authority?",
  ],
};

// null = all three
type AcharyaSelection = string | null;

export default function AskPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [selected, setSelected] = useState<AcharyaSelection>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const [hydrated, setHydrated] = useState(false);

  // Load persisted state
  useEffect(() => {
    try {
      const savedTurns = localStorage.getItem(STORAGE_KEY);
      if (savedTurns) setTurns(JSON.parse(savedTurns));
      const savedSelected = localStorage.getItem(SELECTED_KEY);
      if (savedSelected) setSelected(savedSelected === "null" ? null : savedSelected);
    } catch {}
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(turns));
      localStorage.setItem(SELECTED_KEY, String(selected));
    } catch {}
  }, [turns, selected, hydrated]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  function buildHistory(): ChatMessage[] {
    const history: ChatMessage[] = [];
    for (const turn of turns) {
      history.push({ role: "user", content: turn.userMessage });
      for (const reply of turn.replies) {
        history.push({ role: reply.acharya as ChatMessage["role"], content: reply.reply });
      }
    }
    return history;
  }

  async function fetchReplies(
    message: string,
    acharyas: string[],
    isNewTurn: boolean,
    existingHistory: ChatMessage[],
  ) {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: existingHistory, acharyas }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data: { message: string; replies: ChatTurn[] } = await res.json();

      if (isNewTurn) {
        const pending = ALL_ACHARYAS.filter(a => !acharyas.includes(a));
        setTurns(prev => [...prev, { userMessage: message, replies: data.replies, pendingAcharyas: pending }]);
      } else {
        setTurns(prev => {
          const next = [...prev];
          const last = { ...next[next.length - 1] };
          last.replies = [...last.replies, ...data.replies];
          last.pendingAcharyas = last.pendingAcharyas.filter(
            a => !data.replies.some(r => r.acharya === a)
          );
          next[next.length - 1] = last;
          return next;
        });
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSend(msg?: string) {
    const message = (msg ?? input).trim();
    if (!message || loading) return;
    setInput("");
    const acharyas = selected ? [selected] : ALL_ACHARYAS;
    await fetchReplies(message, acharyas, true, buildHistory());
  }

  async function handleContinue(turnIndex: number) {
    if (loading) return;
    const turn = turns[turnIndex];
    if (!turn.pendingAcharyas.length) return;

    const history: ChatMessage[] = [];
    for (let i = 0; i <= turnIndex; i++) {
      history.push({ role: "user", content: turns[i].userMessage });
      for (const reply of turns[i].replies) {
        history.push({ role: reply.acharya as ChatMessage["role"], content: reply.reply });
      }
    }
    await fetchReplies(turn.userMessage, turn.pendingAcharyas, false, history);
  }

  function handleSelectAcharya(key: AcharyaSelection) {
    setSelected(key);
    // Clear conversation when switching so context stays clean
    setTurns([]);
    setError("");
  }

  const sampleQs = SAMPLE_QUESTIONS[selected ?? "all"];
  const isEmpty = turns.length === 0 && !loading;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-stone-800">Ask the Acharyas</h1>
        <p className="text-stone-500 text-sm mt-0.5">
          {selected
            ? `Speaking with ${ACHARYA_META[selected]?.name ?? selected} only`
            : "All three acharyas respond — or pick one below"}
        </p>
      </div>

      {/* Acharya selector */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {/* All */}
        <button
          onClick={() => handleSelectAcharya(null)}
          className={`text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
            selected === null
              ? "bg-stone-800 border-stone-800 text-white"
              : "border-stone-200 text-stone-600 hover:bg-stone-100"
          }`}
        >
          All three
        </button>

        {/* Individual acharyas */}
        {ALL_ACHARYAS.map(key => {
          const meta = ACHARYA_META[key];
          const s = COLOR_STYLES[meta?.color ?? "blue"];
          const isActive = selected === key;
          return (
            <button
              key={key}
              onClick={() => handleSelectAcharya(key)}
              className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors ${
                isActive ? s.selectorActive : s.selector
              }`}
            >
              <div className={`w-1.5 h-1.5 rounded-full ${isActive ? "bg-white" : s.dot}`} />
              {meta?.short ?? key}
            </button>
          );
        })}

        {turns.length > 0 && (
          <button
            onClick={() => { setTurns([]); setError(""); }}
            className="ml-auto text-xs text-stone-400 hover:text-stone-600 border border-stone-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            New conversation
          </button>
        )}
      </div>

      {/* Conversation area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-1">

        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <p className="text-stone-400 text-sm max-w-sm">
              {selected
                ? `Ask ${ACHARYA_META[selected]?.name ?? selected} anything about the Bhagavad-gita.`
                : "Ask any question about the Bhagavad-gita. All three acharyas will respond from their own tradition."}
            </p>
            <div className="flex flex-col gap-2 w-full max-w-md">
              {sampleQs.map(q => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-sm text-left text-stone-600 bg-white border border-stone-200 hover:border-amber-300 hover:text-amber-700 px-4 py-3 rounded-xl transition-all"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="space-y-3">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-stone-800 text-white text-sm px-4 py-3 rounded-2xl rounded-tr-sm max-w-lg leading-relaxed">
                {turn.userMessage}
              </div>
            </div>

            {/* Replies */}
            <div className="grid gap-3">
              {turn.replies.map(reply => {
                const meta = ACHARYA_META[reply.acharya];
                const s = COLOR_STYLES[meta?.color ?? "blue"];
                return (
                  <div key={reply.acharya} className={`border rounded-2xl p-4 ${s.card}`}>
                    <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
                        <span className={`text-xs font-semibold ${s.name}`}>{meta?.short ?? reply.acharya}</span>
                      </div>
                      {reply.source_verses.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {reply.source_verses.slice(0, 4).map(v => (
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
                      {reply.reply}
                    </p>
                  </div>
                );
              })}
            </div>

            {/* Continue — only on last turn when some acharyas haven't responded and we're in "All" mode */}
            {i === turns.length - 1 && turn.pendingAcharyas.length > 0 && !loading && !selected && (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleContinue(i)}
                  className="text-xs text-amber-700 border border-amber-300 hover:bg-amber-50 px-3 py-1.5 rounded-lg transition-colors"
                >
                  Hear from {turn.pendingAcharyas.map(a => ACHARYA_META[a]?.short ?? a).join(" & ")} →
                </button>
                <span className="text-xs text-stone-400">
                  {turn.pendingAcharyas.length} acharya{turn.pendingAcharyas.length > 1 ? "s" : ""} haven't responded yet
                </span>
              </div>
            )}
          </div>
        ))}

        {/* Loading skeleton */}
        {loading && (
          <div className="space-y-3">
            {turns.length === 0 && (
              <div className="flex justify-end">
                <div className="bg-stone-800 text-white text-sm px-4 py-3 rounded-2xl rounded-tr-sm opacity-60">
                  {input || "…"}
                </div>
              </div>
            )}
            {(selected ? [ACHARYA_META[selected]?.color ?? "blue"] : ["blue", "amber", "green"]).map(color => (
              <div key={color} className={`border rounded-2xl p-4 animate-pulse ${COLOR_STYLES[color].card}`}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-2 h-2 rounded-full ${COLOR_STYLES[color].dot}`} />
                  <div className="h-3 w-24 bg-stone-200 rounded" />
                </div>
                <div className="space-y-2">
                  <div className="h-3 bg-stone-200 rounded w-full" />
                  <div className="h-3 bg-stone-200 rounded w-4/5" />
                  <div className="h-3 bg-stone-200 rounded w-3/5" />
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

      {/* Input bar */}
      <div className="mt-4 bg-white border border-stone-200 rounded-2xl p-3 flex gap-3 items-end">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder={
            selected
              ? `Ask ${ACHARYA_META[selected]?.short ?? selected}…`
              : "Ask all three acharyas… (Enter to send)"
          }
          rows={2}
          className="flex-1 resize-none text-sm focus:outline-none bg-transparent text-stone-800 placeholder-stone-400"
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          className="bg-amber-600 hover:bg-amber-700 disabled:bg-stone-200 disabled:text-stone-400 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors shrink-0"
        >
          {loading ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
