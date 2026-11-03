"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Search, SendHorizontal } from "lucide-react";
import { api } from "@/lib/api";
import { getLastMeeting, setLastMeeting } from "@/lib/storage";
import type { AskResponse, MeetingSummary, SearchHit } from "@/lib/types";
import { Badge, Empty, ErrorBanner, EvidenceList, LabelChip, Spinner, fmtDate } from "@/components/ui";

const EXAMPLES = [
  "Who is responsible for the frontend?",
  "What decisions were made?",
  "What issues remain unresolved?",
  "What is the latest testing deadline?",
  "Which tasks are blocked?",
  "What does Ananya need to do?",
];

type Turn = { q: string; a?: AskResponse; err?: string };

function Ask() {
  const params = useSearchParams();
  const router = useRouter();
  const [meetings, setMeetings] = useState<MeetingSummary[] | null>(null);
  const [mid, setMid] = useState<string>("");
  const [mode, setMode] = useState<"ask" | "search">("ask");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [hits, setHits] = useState<{ q: string; items: SearchHit[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.meetings().then((r) => {
      setMeetings(r.meetings);
      const want = params.get("meeting") ?? getLastMeeting();
      const pick = r.meetings.find((m) => m.id === want) ?? r.meetings[0];
      if (pick) setMid(pick.id);
    }).catch((e: Error) => { setMeetings([]); setError(e.message); });
  }, [params]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [turns, hits]);

  function choose(id: string) {
    setMid(id); setTurns([]); setHits(null); setLastMeeting(id);
    router.replace(`/ask?meeting=${id}`);
  }

  async function submit(text: string) {
    const q = text.trim();
    if (!q || !mid || busy) return;
    setInput(""); setBusy(true); setError(null);
    if (mode === "search") {
      try { setHits({ q, items: (await api.search(mid, q)).hits }); } catch (e) { setError((e as Error).message); }
    } else {
      setTurns((t) => [...t, { q }]);
      try {
        const a = await api.ask(mid, q);
        setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, a } : x)));
      } catch (e) {
        setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, err: (e as Error).message } : x)));
      }
    }
    setBusy(false);
  }

  if (meetings === null) return <div className="flex justify-center gap-3 py-32 text-muted"><Spinner /> Loading…</div>;
  if (meetings.length === 0)
    return (
      <div className="mx-auto max-w-2xl px-5 py-24 text-center">
        {error && <div className="mb-6"><ErrorBanner message={error} /></div>}
        <h1 className="display text-4xl text-forest">Ask needs a <em>meeting</em>.</h1>
        <p className="mt-4 text-muted">Analyse a transcript first — answers are always drawn from one specific meeting.</p>
        <Link href="/workspace" className="btn btn-primary mt-8">Go to the workspace</Link>
      </div>
    );

  return (
    <div className="mx-auto max-w-4xl px-5 py-12 sm:px-8">
      <p className="eyebrow">Ask InsightMeet</p>
      <h1 className="display mt-3 text-4xl text-forest sm:text-5xl">Ask the <em>meeting</em>, not the internet.</h1>
      <p className="mt-4 max-w-2xl text-muted">Answers come only from the selected transcript and are shown with their supporting sentences. If the meeting never said it, you’ll be told it wasn’t found.</p>

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <label htmlFor="meeting" className="text-sm font-semibold text-forest">Meeting</label>
        <select id="meeting" value={mid} onChange={(e) => choose(e.target.value)} className="min-w-0 max-w-full flex-1 rounded-lg border border-line bg-[#fffdf8] px-3 py-2 text-sm sm:flex-none sm:min-w-72">
          {meetings.map((m) => <option key={m.id} value={m.id}>{m.title} — {fmtDate(m.created_at)}</option>)}
        </select>
        <Link href={`/meeting/${mid}`} className="text-sm text-emerald underline underline-offset-4">Open dashboard</Link>
        <div className="ml-auto inline-flex rounded-full border border-line p-0.5 text-sm" role="tablist" aria-label="Mode">
          {(["ask", "search"] as const).map((m) => (
            <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`rounded-full px-4 py-1.5 ${mode === m ? "bg-forest text-ivory" : "text-muted"}`}>{m === "ask" ? "Ask" : "Search"}</button>
          ))}
        </div>
      </div>

      {mode === "ask" && (
        <div className="mt-6 flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button key={e} onClick={() => submit(e)} disabled={busy} className="rounded-full border border-sage bg-[#fffdf8] px-3.5 py-1.5 text-sm text-forest transition-colors hover:bg-sage-soft disabled:opacity-50">{e}</button>
          ))}
        </div>
      )}

      <div className="mt-8 min-h-[12rem] space-y-8" aria-live="polite">
        {mode === "ask" && turns.length === 0 && <Empty>Pick an example or type your own question below.</Empty>}
        {mode === "ask" && turns.map((t, i) => (
          <div key={i}>
            <p className="font-serif text-xl italic text-forest">“{t.q}”</p>
            {!t.a && !t.err && <p className="mt-3 flex items-center gap-2 text-sm text-muted"><Spinner /> Searching the transcript…</p>}
            {t.err && <div className="mt-3"><ErrorBanner message={t.err} /></div>}
            {t.a && (
              <div className="paper mt-3 rounded-xl p-5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={t.a.found ? "green" : "amber"}>{t.a.found ? "found in transcript" : "not found in transcript"}</Badge>
                  <span className="text-xs text-muted">{t.a.method}{t.a.found ? ` · confidence ${t.a.confidence.toFixed(2)}` : ""}</span>
                </div>
                <p className="mt-3 whitespace-pre-line leading-relaxed text-charcoal">{t.a.answer.replace(/ \| /g, "\n• ").replace(/^([^:]{3,40}): (?=.*\n•)/, "$1:\n• ")}</p>
                <EvidenceList items={t.a.evidence} meetingId={mid} max={6} label="Supporting sentences" />
              </div>
            )}
          </div>
        ))}
        {mode === "search" && !hits && <Empty>Type a word or phrase to find the sentences that mention it.</Empty>}
        {mode === "search" && hits && (
          <div>
            <p className="text-sm text-muted">{hits.items.length} result(s) for “{hits.q}”</p>
            <ul className="mt-3 divide-y hairline border-y hairline">
              {hits.items.map((h) => (
                <li key={h.evidence.sentence_id} className="py-3 text-sm">
                  <LabelChip label={h.label} />
                  <EvidenceList items={[h.evidence]} meetingId={mid} label="" />
                </li>
              ))}
            </ul>
            {hits.items.length === 0 && <Empty>No sentence matches.</Empty>}
          </div>
        )}
        {error && <ErrorBanner message={error} />}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); void submit(input); }} className="sticky bottom-4 mt-6 flex gap-2 rounded-full border border-forest bg-[#fffdf8] p-1.5 shadow-lg">
        <label htmlFor="q" className="sr-only">{mode === "ask" ? "Your question" : "Search the transcript"}</label>
        {mode === "search" && <Search size={18} className="ml-3 self-center text-muted" />}
        <input id="q" value={input} onChange={(e) => setInput(e.target.value)} maxLength={500} placeholder={mode === "ask" ? "e.g. Who owns the database work?" : "e.g. sqlite"} className="min-w-0 flex-1 bg-transparent px-4 py-2 text-sm outline-none" />
        <button className="btn btn-primary !px-5" disabled={busy || !input.trim()} aria-label="Submit">{busy ? <Spinner /> : <SendHorizontal size={17} />}</button>
      </form>
    </div>
  );
}

export default function AskPage() {
  return <Suspense fallback={<div className="p-10 text-muted">Loading…</div>}><Ask /></Suspense>;
}
