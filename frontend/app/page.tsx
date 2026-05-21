"use client";
import { useState } from "react";
import Link from "next/link";
import { api, SearchResult, ACHARYA_META } from "@/lib/api";

const CHAPTERS = Array.from({ length: 18 }, (_, i) => i + 1);

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await api.search(query.trim());
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-center py-10 space-y-4">
        <h1 className="text-4xl font-bold text-stone-800 tracking-tight">
          Bhagavad-gita Commentary Engine
        </h1>
        <p className="text-stone-500 max-w-xl mx-auto text-lg">
          Compare Prabhupada, Vishvanatha Chakravarti, and Baladeva Vidyabhushana
          side-by-side — with AI-synthesized philosophical insights.
        </p>

        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 max-w-lg mx-auto mt-6">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search commentaries… e.g. karma, detachment, yoga"
            className="flex-1 border border-stone-300 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
          />
          <button
            type="submit"
            className="bg-amber-600 hover:bg-amber-700 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
          >
            Search
          </button>
        </form>
      </section>

      {/* Search Results */}
      {searched && (
        <section>
          <h2 className="text-lg font-semibold text-stone-700 mb-4">
            {loading ? "Searching…" : `${results.length} results for "${query}"`}
          </h2>
          <div className="space-y-3">
            {results.map((r, i) => {
              const meta = ACHARYA_META[r.matched_acharya];
              return (
                <Link
                  key={i}
                  href={`/verse/${r.chapter}/${r.verse_label}`}
                  className="block bg-white border border-stone-200 rounded-xl p-4 hover:border-amber-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-stone-800 text-sm">
                      BG {r.chapter}.{r.verse_label}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full bg-${meta?.color ?? "stone"}-100 text-${meta?.color ?? "stone"}-700`}>
                      {meta?.short ?? r.matched_acharya}
                    </span>
                  </div>
                  {r.translation && (
                    <p className="text-xs text-stone-400 mb-1 italic truncate">{r.translation}</p>
                  )}
                  <p className="text-sm text-stone-600 leading-relaxed">…{r.snippet}…</p>
                </Link>
              );
            })}
            {!loading && results.length === 0 && (
              <p className="text-stone-400 text-sm">No results found. Try a different term.</p>
            )}
          </div>
        </section>
      )}

      {/* Chapter Browser */}
      {!searched && (
        <section>
          <h2 className="text-lg font-semibold text-stone-700 mb-4">Browse by Chapter</h2>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {CHAPTERS.map(ch => (
              <Link
                key={ch}
                href={`/chapter/${ch}`}
                className="bg-white border border-stone-200 rounded-xl p-4 text-center hover:border-amber-300 hover:shadow-sm transition-all group"
              >
                <div className="text-xl font-bold text-stone-700 group-hover:text-amber-700 transition-colors">
                  {ch}
                </div>
                <div className="text-xs text-stone-400 mt-0.5">Chapter</div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Acharya Key */}
      {!searched && (
        <section className="bg-white border border-stone-200 rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-stone-500 uppercase tracking-wider mb-4">Commentators</h2>
          <div className="grid sm:grid-cols-3 gap-4">
            {Object.entries(ACHARYA_META).map(([key, meta]) => (
              <div key={key} className={`border-l-4 border-${meta.color}-400 pl-3`}>
                <div className={`text-sm font-semibold text-${meta.color}-700`}>{meta.short}</div>
                <div className="text-xs text-stone-500 mt-0.5">{meta.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
