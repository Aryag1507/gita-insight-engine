import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Gita Insight Engine",
  description: "Multi-acharya Bhagavad-gita commentary aggregator with AI synthesis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="h-full">
      <body className={`${geist.className} bg-stone-50 text-stone-900 min-h-screen`}>
        <header className="border-b border-stone-200 bg-white sticky top-0 z-10">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold text-lg text-stone-800 hover:text-amber-700 transition-colors">
              <span className="text-2xl">🕉</span>
              <span>Gita Insight Engine</span>
            </Link>
            <nav className="flex gap-6 text-sm text-stone-500">
              <Link href="/" className="hover:text-stone-800 transition-colors">Home</Link>
              <Link href="/chapter/1" className="hover:text-stone-800 transition-colors">Browse</Link>
            </nav>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-stone-200 mt-16 py-6 text-center text-xs text-stone-400">
          Commentaries sourced from Vedabase, Wisdomlib &amp; Bhagavad-gita.org · AI synthesis via Claude
        </footer>
      </body>
    </html>
  );
}
