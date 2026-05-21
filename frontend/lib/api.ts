const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Commentary {
  acharya: string;
  text: string;
  source_url?: string;
}

export interface Theme {
  theme: string;
  description: string;
  acharyas: string[];
}

export interface Agreement {
  point: string;
  acharyas: string[];
}

export interface Divergence {
  point: string;
  positions: Record<string, string>;
}

export interface Insight {
  acharyas_included: string[];
  themes: Theme[];
  agreements: Agreement[];
  divergences: Divergence[];
  synthesis?: string;
  model_used?: string;
}

export interface Verse {
  chapter: number;
  verse_label: string;
  sanskrit?: string;
  transliteration?: string;
  word_for_word?: string;
  translation?: string;
}

export interface VerseDetail extends Verse {
  commentaries: Commentary[];
  insight?: Insight;
}

export interface SearchResult {
  chapter: number;
  verse_label: string;
  translation?: string;
  matched_acharya: string;
  snippet: string;
}

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  listVerses: (chapter?: number) =>
    apiFetch<Verse[]>(`/verses${chapter ? `?chapter=${chapter}` : ""}`),

  getVerse: (chapter: number, verseLabel: string) =>
    apiFetch<VerseDetail>(`/verses/${chapter}/${verseLabel}`),

  search: (q: string, chapter?: number) =>
    apiFetch<SearchResult[]>(
      `/search?q=${encodeURIComponent(q)}${chapter ? `&chapter=${chapter}` : ""}`
    ),
};

export const ACHARYA_META: Record<string, { color: string; label: string; short: string }> = {
  prabhupada: { color: "blue",   label: "A.C. Bhaktivedanta Swami Prabhupada", short: "Prabhupada" },
  vishvanatha: { color: "amber", label: "Vishvanatha Chakravarti Thakura",      short: "Vishvanatha" },
  baladeva:   { color: "green",  label: "Baladeva Vidyabhushana",               short: "Baladeva" },
};
