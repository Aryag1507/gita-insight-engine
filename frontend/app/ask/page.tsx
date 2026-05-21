"use client";
import { useState } from "react";
import { ACHARYA_META } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AcharyaAnswer {
  acharya: string;
  name: string;
  answer: string;
  source_verses: string[];
}

interface QAResponse {
  question: string;
  answers: AcharyaAnswer[];
}

const SAMPLE_QUESTIONS = [
  "How should one approach their duties without attachment to results?",
  "What is the nature of the eternal soul?",
  "How does one overcome grief and lamentation?",
  "What is the highest form of yoga?",
  "How should a devotee relate to God?",
];

const COLOR_STYLES: Record<string, { card: string; badge: string; border: string; dot: string }> = {
  blue:  { card: "bg-blue-50 border-blue-200",   badge: "bg-blue-100 text-blue-700",   border: "border-blue-400", dot: "bg-blue-400" },
  amber: { card: "bg-amber-50 border-amber-200", badge: "bg-amber-100 text-amber-700", border: "border-amber-400", dot: "bg-amber-400" },
  green: { card: "bg-green-50 border-green-200", badge: "bg-green-100 text-green-700", border: "border-green-400", dot: "bg-green-400" },
};

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<QAResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAsk(q?: string) {
    const finalQ = (q ?? question).trim();
    if (!finalQ) return;
    if (q) setQuestion(q);

    setLoading(true);
    setError("");
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: finalQ }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data = await res.json();
      setResponse(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-stone-800">Ask the Acharyas</h1>
        <p className="text-stone-500 mt-2">
          Ask any philosophical question and receive answers in the authentic voice of each
          commentator, grounded in their Bhagavad-gita teachings.
        </p>
      </div>

      {/* Input */}
      <div className="bg-white border border-stone-200 rounded-2xl p-6 space-y-4">
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
          placeholder="Ask a philosophical question… e.g. What is the highest form of devotion?"
          rows={3}
          className="w-full border border-stone-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none bg-stone-50"
        />
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUESTIONS.slice(0, 3).map(q => (
              <button
                key={q}
                onClick={() => handleAsk(q)}
                className="text-xs text-stone-500 bg-stone-100 hover:bg-amber-100 hover:text-amber-700 px-3 py-1.5 rounded-full transition-colors"
              >
                {q.length > 45 ? q.slice(0, 45) + "…" : q}
              </button>
            ))}
          </div>
          <button
            onClick={() => handleAsk()}
            disabled={loading || !question.trim()}
            className="bg-amber-600 hover:bg-amber-700 disabled:bg-stone-200 disabled:text-stone-400 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors"
          >
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="grid gap-4">
          {["blue", "amber", "green"].map(color => (
            <div key={color} className={`border rounded-2xl p-6 animate-pulse ${COLOR_STYLES[color].card}`}>
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-3 h-3 rounded-full ${COLOR_STYLES[color].dot}`} />
                <div className="h-4 w-48 bg-stone-200 rounded" />
              </div>
              <div className="space-y-2">
                <div className="h-3 bg-stone-200 rounded w-full" />
                <div className="h-3 bg-stone-200 rounded w-5/6" />
                <div className="h-3 bg-stone-200 rounded w-4/6" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Answers */}
      {response && (
        <div className="space-y-5">
          <h2 className="text-sm font-semibold text-stone-500 uppercase tracking-wider">
            Responses to: <span className="text-stone-700 normal-case font-normal">"{response.question}"</span>
          </h2>

          {response.answers.map(answer => {
            const meta = ACHARYA_META[answer.acharya];
            const styles = COLOR_STYLES[meta?.color ?? "stone"] ?? COLOR_STYLES["blue"];

            return (
              <div key={answer.acharya} className={`border rounded-2xl p-6 ${styles.card}`}>
                {/* Acharya header */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full shrink-0 mt-0.5 ${styles.dot}`} />
                    <div>
                      <div className="font-semibold text-stone-800">{meta?.short ?? answer.acharya}</div>
                      <div className="text-xs text-stone-500">{answer.name}</div>
                    </div>
                  </div>
                  {answer.source_verses.length > 0 && (
                    <div className="flex flex-wrap gap-1 justify-end">
                      {answer.source_verses.map(v => (
                        <a
                          key={v}
                          href={`/verse/${v.replace("BG ", "").replace(".", "/")}`}
                          className={`text-xs px-2 py-0.5 rounded-full ${styles.badge} hover:opacity-80 transition-opacity`}
                        >
                          {v}
                        </a>
                      ))}
                    </div>
                  )}
                </div>

                {/* Answer text */}
                <p className="text-stone-700 leading-relaxed text-sm whitespace-pre-line">
                  {answer.answer}
                </p>
              </div>
            );
          })}
        </div>
      )}

      {/* Tip */}
      {!response && !loading && (
        <div className="text-center text-sm text-stone-400 py-8">
          Answers are grounded in the acharyas' actual Bhagavad-gita commentaries stored in the database.
        </div>
      )}
    </div>
  );
}
