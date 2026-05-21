import Link from "next/link";
import { api, ACHARYA_META, VerseDetail } from "@/lib/api";
import { notFound } from "next/navigation";

const COLOR_MAP: Record<string, string> = {
  blue:  "border-blue-400 bg-blue-50",
  amber: "border-amber-400 bg-amber-50",
  green: "border-green-400 bg-green-50",
};
const BADGE_MAP: Record<string, string> = {
  blue:  "bg-blue-100 text-blue-700",
  amber: "bg-amber-100 text-amber-700",
  green: "bg-green-100 text-green-700",
};

export default async function VersePage({
  params,
}: {
  params: Promise<{ chapter: string; verse: string }>;
}) {
  const { chapter, verse } = await params;
  let data: VerseDetail;
  try {
    data = await api.getVerse(parseInt(chapter), verse);
  } catch {
    notFound();
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-stone-400">
        <Link href="/" className="hover:text-stone-600">Home</Link>
        <span>/</span>
        <Link href={`/chapter/${chapter}`} className="hover:text-stone-600">Chapter {chapter}</Link>
        <span>/</span>
        <span className="text-stone-700 font-medium">BG {chapter}.{verse}</span>
      </div>

      {/* Verse Header */}
      <section className="bg-white border border-stone-200 rounded-2xl p-6 space-y-4">
        <h1 className="text-2xl font-bold text-stone-800">BG {chapter}.{verse}</h1>
        {data.sanskrit && (
          <p className="text-xl text-stone-700 font-medium leading-relaxed">{data.sanskrit}</p>
        )}
        {data.transliteration && (
          <p className="text-stone-500 italic text-sm leading-relaxed">{data.transliteration}</p>
        )}
        {data.translation && (
          <blockquote className="border-l-4 border-amber-400 pl-4 text-stone-700 leading-relaxed">
            {data.translation}
          </blockquote>
        )}
        {data.word_for_word && (
          <details className="text-xs text-stone-400">
            <summary className="cursor-pointer hover:text-stone-600 select-none">Word-for-word</summary>
            <p className="mt-2 leading-relaxed">{data.word_for_word}</p>
          </details>
        )}
      </section>

      {/* Commentaries */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold text-stone-700">Commentaries</h2>
        {data.commentaries.length === 0 && (
          <p className="text-stone-400 text-sm">No commentaries ingested yet for this verse.</p>
        )}
        <div className="grid gap-4">
          {data.commentaries.map(c => {
            const meta = ACHARYA_META[c.acharya];
            const colorClass = COLOR_MAP[meta?.color ?? "stone"] ?? "border-stone-300 bg-stone-50";
            const badgeClass = BADGE_MAP[meta?.color ?? "stone"] ?? "bg-stone-100 text-stone-600";
            return (
              <div key={c.acharya} className={`border-l-4 rounded-xl p-5 ${colorClass}`}>
                <div className="flex items-center justify-between mb-3">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${badgeClass}`}>
                    {meta?.short ?? c.acharya}
                  </span>
                  {c.source_url && (
                    <a href={c.source_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-stone-400 hover:text-stone-600 underline">
                      Source ↗
                    </a>
                  )}
                </div>
                <p className="text-sm text-stone-700 leading-relaxed whitespace-pre-line">
                  {c.text}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* AI Insight */}
      {data.insight && (
        <section className="space-y-5">
          <h2 className="text-lg font-semibold text-stone-700">AI Philosophical Synthesis</h2>

          {/* Synthesis */}
          {data.insight.synthesis && (
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
              <h3 className="text-xs font-semibold text-amber-600 uppercase tracking-wider mb-3">Synthesis</h3>
              <p className="text-stone-700 leading-relaxed">{data.insight.synthesis}</p>
            </div>
          )}

          {/* Themes */}
          {data.insight.themes.length > 0 && (
            <div className="bg-white border border-stone-200 rounded-2xl p-6">
              <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-wider mb-4">Key Themes</h3>
              <div className="space-y-3">
                {data.insight.themes.map((t, i) => (
                  <div key={i}>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-stone-800 text-sm">{t.theme}</span>
                      {t.acharyas.map(a => {
                        const m = ACHARYA_META[a.toLowerCase()];
                        return (
                          <span key={a} className={`text-xs px-2 py-0.5 rounded-full ${BADGE_MAP[m?.color ?? "stone"] ?? ""}`}>
                            {m?.short ?? a}
                          </span>
                        );
                      })}
                    </div>
                    <p className="text-sm text-stone-500 mt-0.5 leading-relaxed">{t.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agreements & Divergences */}
          <div className="grid sm:grid-cols-2 gap-4">
            {data.insight.agreements.length > 0 && (
              <div className="bg-green-50 border border-green-200 rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-3">✓ Agreements</h3>
                <ul className="space-y-2">
                  {data.insight.agreements.map((a, i) => (
                    <li key={i} className="text-sm text-stone-700 leading-relaxed">
                      <span className="text-green-500 mr-1">•</span>{a.point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {data.insight.divergences.length > 0 && (
              <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-rose-600 uppercase tracking-wider mb-3">⚖ Divergences</h3>
                <div className="space-y-3">
                  {data.insight.divergences.map((d, i) => (
                    <div key={i}>
                      <p className="text-xs font-medium text-stone-600 mb-1">{d.point}</p>
                      {Object.entries(d.positions).map(([a, stance]) => {
                        const m = ACHARYA_META[a.toLowerCase()];
                        return (
                          <p key={a} className="text-xs text-stone-500 leading-relaxed">
                            <span className={`font-semibold text-${m?.color ?? "stone"}-600`}>{m?.short ?? a}:</span>{" "}
                            {stance}
                          </p>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {!data.insight && (
        <div className="bg-stone-100 rounded-xl p-4 text-sm text-stone-500">
          No AI insight generated yet for this verse.
          Run: <code className="bg-stone-200 px-1 rounded">python analyze.py --verse {chapter}.{verse}</code>
        </div>
      )}
    </div>
  );
}
