"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Search, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { clearLastMeeting } from "@/lib/storage";
import type { MeetingSummary } from "@/lib/types";
import { Badge, Empty, ErrorBanner, Spinner, fmtDate } from "@/components/ui";

export default function HistoryPage() {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<MeetingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((query: string) => {
    api.meetings(query).then((r) => { setItems(r.meetings); setError(null); }).catch((e: Error) => { setError(e.message); setItems([]); });
  }, []);

  useEffect(() => {
    const t = setTimeout(() => load(q), 250);
    return () => clearTimeout(t);
  }, [q, load]);

  async function remove(m: MeetingSummary) {
    if (!window.confirm(`Delete “${m.title}” permanently?`)) return;
    try {
      await api.deleteMeeting(m.id);
      clearLastMeeting(m.id);
      setItems((x) => (x ? x.filter((i) => i.id !== m.id) : x));
    } catch (e) { setError((e as Error).message); }
  }

  return (
    <div className="mx-auto max-w-5xl px-5 py-12 sm:px-8">
      <p className="eyebrow">Meeting history</p>
      <h1 className="display mt-3 text-4xl text-forest sm:text-5xl">Every meeting, <em>on file</em>.</h1>
      <div className="relative mt-8 max-w-md">
        <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
        <input value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search meetings" placeholder="Search titles and transcripts" className="w-full rounded-full border border-line bg-[#fffdf8] py-2.5 pl-10 pr-4 text-sm" />
      </div>
      <div className="mt-6">{error && <ErrorBanner message={error} onRetry={() => load(q)} />}</div>
      {items === null ? (
        <div className="flex justify-center gap-3 py-20 text-muted"><Spinner /> Loading…</div>
      ) : items.length === 0 && !error ? (
        <div className="mt-6"><Empty>{q ? "No meetings match your search." : <>No meetings yet. <Link href="/workspace" className="font-semibold text-emerald underline">Analyse your first transcript</Link>.</>}</Empty></div>
      ) : (
        <ul className="mt-4 divide-y hairline border-y hairline">
          {items.map((m) => (
            <li key={m.id} className="grid gap-3 py-5 sm:grid-cols-[1fr_auto] sm:items-center">
              <div>
                <Link href={`/meeting/${m.id}`} className="font-serif text-2xl text-forest hover:text-emerald">{m.title}</Link>
                <p className="mt-1 text-xs text-muted">Analysed {fmtDate(m.created_at)}{m.meeting_date ? ` · meeting date ${fmtDate(m.meeting_date)}` : ""}</p>
                <p className="mt-2 line-clamp-2 max-w-2xl text-sm text-muted">{m.snippet}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Badge>{m.counts.participants} people</Badge>
                  <Badge tone="green">{m.counts.action_items} actions</Badge>
                  <Badge tone="forest">{m.counts.decisions} decisions</Badge>
                  <Badge tone={m.counts.issues_open ? "clay" : "neutral"}>{m.counts.issues_open} open issues</Badge>
                </div>
              </div>
              <div className="flex gap-2">
                <Link href={`/meeting/${m.id}`} className="btn btn-ghost !py-2">Open</Link>
                <Link href={`/ask?meeting=${m.id}`} className="btn btn-ghost !py-2">Ask</Link>
                <button onClick={() => remove(m)} className="btn !py-2 text-clay hover:bg-clay-soft" aria-label={`Delete ${m.title}`}><Trash2 size={16} /></button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
