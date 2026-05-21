"use client";
import { useState, useRef, useEffect } from "react";
import { ACHARYA_META } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

const COLOR_STYLES: Record<string, { card: string; badge: string; dot: string; name: string }> = {
  blue:  { card: "bg-blue-50 border-blue-200",   badge: "bg-blue-100 text-blue-700",   dot: "bg-blue-500",   name: "text-blue-700" },
  amber: { card: "bg-amber-50 border-amber-200", badge: "bg-amber-100 text-amber-700", dot: "bg-amber-500", name: "text-amber-700" },
  green: { card: "bg-green-50 border-green-200", badge: "bg-green-100 text-green-700", dot: "bg-green-500", name: "text-green-700" },
};

const SAMPLE_QUESTIONS = [
  "What is the nature of the eternal soul?",
  "How does one overcome fear and grief?",
  "What is the difference between karma and bhakti yoga?",
  "Who is qualified to receive spiritual knowledge?",
];

interface Turn {
  userMessage: string;
  replies: ChatTurn[];
}

export default function AskPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Build flat history for API
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

  async function handleSend(msg?: string) {
    const message = (msg ?? input).trim();
    if (!message || loading) return;
    setInput("");
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: buildHistory() }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      setTurns(prev => [...prev, { userMessage: message, replies: data.replies }]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  const isEmpty = turns.length === 0 && !loading;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Ask the Acharyas</h1>
          <p className="text-stone-500 text-sm mt-0.5">A live panel discussion — all three respond to every message</p>
        </div>
        {turns.length > 0 && (
          <button
            onClick={() => { setTurns([]); setError(""); }}
            className="text-xs text-stone-400 hover:text-stone-600 border border-stone-200 px-3 py-1.5 rounded-lg transition-colors"
          >
            New conversation
          </button>
        )}
      </div>

      {/* Acharya legend */}
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

      {/* Conversation area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-1">

        {/* Empty state */}
        {isEmpty && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <p className="text-stone-400 text-sm max-w-sm">
              Ask any question about the Bhagavad-gita and all three acharyas will respond from their own philosophical tradition.
            </p>
            <div className="flex flex-col gap-2 w-full max-w-md">
              {SAMPLE_QUESTIONS.map(q => (
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

        {/* Turns */}
        {turns.map((turn, i) => (
          <div key={i} className="space-y-3">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-stone-800 text-white text-sm px-4 py-3 rounded-2xl rounded-tr-sm max-w-lg leading-relaxed">
                {turn.userMessage}
              </div>
            </div>

            {/* Acharya replies */}
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
          </div>
        ))}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            <div className="flex justify-end">
              <div className="bg-stone-800 text-white text-sm px-4 py-3 rounded-2xl rounded-tr-sm opacity-60">
                {input || "…"}
              </div>
            </div>
            {["blue", "amber", "green"].map(color => (
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
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
          }}
          placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
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
