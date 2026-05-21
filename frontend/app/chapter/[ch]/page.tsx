import Link from "next/link";
import { api } from "@/lib/api";

export default async function ChapterPage({ params }: { params: Promise<{ ch: string }> }) {
  const { ch } = await params;
  const chapter = parseInt(ch);
  const verses = await api.listVerses(chapter);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/" className="text-stone-400 hover:text-stone-600 text-sm">← Home</Link>
        <span className="text-stone-300">/</span>
        <h1 className="text-2xl font-bold text-stone-800">Chapter {chapter}</h1>
      </div>

      {verses.length === 0 && (
        <p className="text-stone-400">No verses ingested yet for this chapter. Run <code className="bg-stone-100 px-1 rounded">python ingest.py --chapters {chapter}</code></p>
      )}

      <div className="grid gap-3">
        {verses.map(v => (
          <Link
            key={v.verse_label}
            href={`/verse/${v.chapter}/${v.verse_label}`}
            className="bg-white border border-stone-200 rounded-xl p-4 hover:border-amber-300 hover:shadow-sm transition-all group"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <span className="text-xs font-semibold text-amber-600 uppercase tracking-wider">
                  BG {v.chapter}.{v.verse_label}
                </span>
                {v.translation && (
                  <p className="text-sm text-stone-600 mt-1 leading-relaxed line-clamp-2">
                    {v.translation}
                  </p>
                )}
                {v.transliteration && (
                  <p className="text-xs text-stone-400 mt-1 italic truncate">
                    {v.transliteration}
                  </p>
                )}
              </div>
              <span className="text-stone-300 group-hover:text-amber-400 transition-colors shrink-0 text-lg">→</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
