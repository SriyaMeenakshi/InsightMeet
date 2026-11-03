import Link from "next/link";
import { Brand } from "./Brand";

export function Footer() {
  return (
    <footer className="bg-forest-deep text-ivory/80">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Brand light />
          <p className="mt-4 max-w-sm font-serif text-lg leading-snug text-ivory">
            Every meeting has a story. We keep the evidence.
          </p>
          <p className="mt-3 max-w-sm text-sm text-ivory/60">
            An NLP project that extracts actions, decisions, issues and deadlines from transcripts — runs locally, no
            paid APIs, no GPU.
          </p>
        </div>
        <div>
          <p className="eyebrow !text-sage">Product</p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li><Link className="hover:text-ivory" href="/workspace">Transcript workspace</Link></li>
            <li><Link className="hover:text-ivory" href="/ask">Ask InsightMeet</Link></li>
            <li><Link className="hover:text-ivory" href="/history">Meeting history</Link></li>
          </ul>
        </div>
        <div>
          <p className="eyebrow !text-sage">Project</p>
          <ul className="mt-4 space-y-2.5 text-sm">
            <li>FastAPI · spaCy · scikit-learn</li>
            <li>Next.js · Tailwind · Recharts</li>
            <li>SQLite storage on your machine</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-ivory/10 py-5 text-center text-xs text-ivory/50">
        InsightMeet · NLP-based meeting insight extraction · extracted items are decision support and should be reviewed.
      </div>
    </footer>
  );
}
