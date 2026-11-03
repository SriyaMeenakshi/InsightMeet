"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Download, MessageSquareText, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { setLastMeeting, clearLastMeeting } from "@/lib/storage";
import type { Analysis } from "@/lib/types";
import { Badge, Empty, ErrorBanner, EvidenceList, SectionHead, Spinner, fmtDate } from "@/components/ui";
import { DistributionDonut, ParticipantChart, TopicChart } from "@/components/dashboard/charts";
import {
  ActionsSection, DeadlinesSection, DecisionsSection, IssuesSection, MethodSection, RelationsSection, SuggestionsSection, TranscriptSection,
} from "@/components/dashboard/sections";

const NAV = [
  ["overview", "Overview"], ["review", "Needs review"], ["topics", "Topics"], ["participants", "Participants"],
  ["actions", "Action items"], ["decisions", "Decisions"], ["issues", "Issues"], ["deadlines", "Deadlines"],
  ["relations", "Relationships"], ["suggestions", "Suggestions"], ["transcript", "Classification"], ["method", "Method"],
] as const;

export default function MeetingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [a, setA] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState("overview");

  const load = () => {
    setError(null);
    api.meeting(id).then((x) => { setA(x); setLastMeeting(id); }).catch((e: Error) => setError(e.message));
  };
  useEffect(load, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!a) return;
    const io = new IntersectionObserver(
      (es) => es.forEach((e) => e.isIntersecting && setSection(e.target.id)),
      { rootMargin: "-20% 0px -70% 0px" },
    );
    NAV.forEach(([k]) => { const el = document.getElementById(k); if (el) io.observe(el); });
    return () => io.disconnect();
  }, [a]);

  if (error) return <div className="mx-auto max-w-3xl px-5 py-20"><ErrorBanner message={error} onRetry={load} /><Link href="/history" className="mt-6 inline-block text-emerald underline">Back to history</Link></div>;
  if (!a) return <div className="flex items-center justify-center gap-3 py-32 text-muted"><Spinner /> Loading analysis…</div>;

  const ov = a.overview;
  const stats: [string, number][] = [
    ["Sentences", ov.sentences], ["Participants", ov.participants], ["Action items", ov.action_items],
    ["Decisions", ov.decisions], ["Open issues", ov.issues_open], ["Need review", ov.needs_review],
  ];

  const exportJson = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(a, null, 2)], { type: "application/json" }));
    const l = document.createElement("a");
    l.href = url; l.download = `${a.title.replace(/[^\w-]+/g, "_") || "meeting"}.json`; l.click();
    URL.revokeObjectURL(url);
  };
  const remove = async () => {
    if (!window.confirm("Delete this meeting and its analysis permanently?")) return;
    try { await api.deleteMeeting(id); clearLastMeeting(id); router.push("/history"); } catch (e) { setError((e as Error).message); }
  };

  return (
    <div className="mx-auto max-w-7xl px-5 py-10 sm:px-8">
      <header className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="eyebrow">Meeting analysis</p>
          <h1 className="display mt-2 text-4xl text-forest sm:text-5xl">{a.title}</h1>
          <p className="mt-2 text-sm text-muted">
            {a.meeting_date ? `Meeting date ${fmtDate(a.meeting_date)}` : "No meeting date — relative deadlines left unresolved"} · analysed {fmtDate(a.created_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/ask?meeting=${id}`} className="btn btn-primary"><MessageSquareText size={16} /> Ask InsightMeet</Link>
          <button onClick={exportJson} className="btn btn-ghost"><Download size={16} /> Export JSON</button>
          <button onClick={remove} className="btn btn-ghost !border-clay !text-clay hover:!bg-clay hover:!text-white"><Trash2 size={16} /> Delete</button>
        </div>
      </header>

      {a.warnings.length > 0 && (
        <div className="mt-6 space-y-2">
          {a.warnings.map((w) => (
            <p key={w} className="flex gap-2 rounded-lg bg-amber-soft px-4 py-2.5 text-sm text-amber"><AlertTriangle size={16} className="mt-0.5 shrink-0" />{w}</p>
          ))}
        </div>
      )}

      <nav aria-label="Sections" className="sticky top-16 z-30 -mx-5 mt-6 overflow-x-auto border-b hairline bg-ivory/95 px-5 backdrop-blur-sm lg:hidden">
        <div className="flex gap-5 whitespace-nowrap py-3 text-sm">
          {NAV.map(([k, l]) => <a key={k} href={`#${k}`} className={section === k ? "font-semibold text-forest" : "text-muted"}>{l}</a>)}
        </div>
      </nav>

      <div className="mt-10 grid gap-12 lg:grid-cols-[11rem_1fr]">
        <aside className="hidden lg:block">
          <nav aria-label="Sections" className="sticky top-24 space-y-1 border-l hairline text-sm">
            {NAV.map(([k, l]) => (
              <a key={k} href={`#${k}`} className={`-ml-px block border-l-2 py-1.5 pl-4 transition-colors ${section === k ? "border-emerald font-semibold text-forest" : "border-transparent text-muted hover:text-forest"}`}>{l}</a>
            ))}
          </nav>
        </aside>

        <div className="min-w-0 space-y-20">
          <section>
            <SectionHead id="overview" n="01" title="Overview" blurb="An extractive summary: every highlighted sentence is quoted from the transcript." />
            <dl className="grid grid-cols-2 divide-x divide-y hairline border hairline sm:grid-cols-3 sm:divide-y-0 lg:grid-cols-6">
              {stats.map(([l, v]) => (
                <div key={l} className="px-4 py-4">
                  <dd className="font-serif text-4xl text-forest tabular-nums">{v}</dd>
                  <dt className="mt-0.5 text-xs uppercase tracking-wider text-muted">{l}</dt>
                </div>
              ))}
            </dl>
            <p className="mt-6 max-w-3xl font-serif text-xl leading-relaxed text-charcoal">{a.summary.overview}</p>
            <EvidenceList items={a.summary.highlights} meetingId={id} max={5} label="Key sentences" />
            <p className="mt-3 text-xs text-muted">{a.summary.method}</p>
          </section>

          <section>
            <SectionHead id="review" n="02" title="Needs your review" blurb="Items where the transcript was ambiguous. Nothing here has been guessed." />
            {a.review_queue.length === 0 ? <Empty>Nothing flagged — every extracted item had explicit support.</Empty> : (
              <ul className="divide-y hairline border-y hairline">
                {a.review_queue.map((r) => (
                  <li key={r.item_type + r.item_id} className="py-3 text-sm">
                    <p><Badge tone="amber">{r.item_type} {r.item_id}</Badge> <span className="ml-1 text-charcoal">{r.text}</span></p>
                    <ul className="mt-1 text-xs text-amber">{r.reasons.map((x) => <li key={x}>⚑ {x}</li>)}</ul>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <SectionHead id="topics" n="03" title="Topics & keyphrases" blurb="Topics group sentences by the project component they mention; keyphrases are ranked by frequency and distinctiveness." />
            <div className="grid gap-10 lg:grid-cols-2">
              <div>{a.topics.length ? <TopicChart topics={a.topics} /> : <Empty>No project components were mentioned.</Empty>}</div>
              <div>
                <ul className="flex flex-wrap gap-2">
                  {a.keyphrases.map((k) => (
                    <li key={k.phrase} className="rounded-full border border-sage bg-[#fffdf8] px-3 py-1 text-sm text-forest" style={{ opacity: 0.55 + k.score * 0.45 }}>
                      {k.phrase} <span className="text-xs text-muted">{k.mentions}</span>
                    </li>
                  ))}
                </ul>
                {a.entities.length > 0 && (
                  <div className="mt-8">
                    <p className="eyebrow !text-muted">Entities</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {a.entities.filter((e) => ["PERSON", "ORGANIZATION", "TECHNOLOGY", "PROJECT", "LOCATION"].includes(e.label)).map((e) => (
                        <Badge key={e.label + e.text} tone={e.label === "PERSON" ? "forest" : e.label === "TECHNOLOGY" ? "green" : "neutral"} title={`${e.source} · ${e.count} mention(s)`}>{e.text} <span className="opacity-60">{e.label.toLowerCase()}</span></Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <section>
            <SectionHead id="participants" n="04" title="Participants" blurb="Taken from speaker labels. Share of words spoken, and tasks each person owns." />
            {a.participants.length === 0 ? <Empty>No speaker labels were found in this transcript.</Empty> : (
              <div className="grid gap-10 lg:grid-cols-2">
                <ParticipantChart participants={a.participants} />
                <table className="w-full text-sm">
                  <thead><tr className="border-b hairline text-left text-xs uppercase tracking-wider text-muted"><th className="py-2">Name</th><th>Turns</th><th>Sentences</th><th>Tasks owned</th></tr></thead>
                  <tbody className="divide-y hairline">
                    {a.participants.map((p) => <tr key={p.name}><td className="py-2 font-semibold text-forest">{p.name}</td><td>{p.turns}</td><td>{p.sentences}</td><td>{p.actions_owned}</td></tr>)}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section><SectionHead id="actions" n="05" title="Action items" blurb="Owner, deadline, commitment strength and status — each with its supporting sentences." /><ActionsSection a={a} mid={id} /></section>
          <section><SectionHead id="decisions" n="06" title="Decisions" blurb="Only explicit or accepted decisions. Replaced decisions stay visible, struck through." /><DecisionsSection items={a.decisions} mid={id} /></section>
          <section><SectionHead id="issues" n="07" title="Issues & blockers" blurb="Impact is shown only when the transcript states it." /><IssuesSection items={a.issues} mid={id} /></section>
          <section><SectionHead id="deadlines" n="08" title="Deadlines" blurb="Original and revised dates are kept; the latest is marked." /><DeadlinesSection items={a.deadlines} mid={id} /></section>
          <section><SectionHead id="relations" n="09" title="Relationships & dependencies" blurb="Explicit = stated in a sentence. Inferred = derived from a technology or component keyword." /><RelationsSection items={a.relationships} mid={id} /></section>
          <section><SectionHead id="suggestions" n="10" title="Suggestions" blurb="Proposals and tentative ideas, and how the group responded." /><SuggestionsSection items={a.suggestions} mid={id} /></section>

          <section>
            <SectionHead id="transcript" n="11" title="Sentence classification & evidence" blurb="Every sentence in the original transcript, labelled. Evidence links elsewhere on this page jump here." />
            <DistributionDonut distribution={a.distribution} />
            <div className="mt-10"><TranscriptSection sentences={a.sentences} /></div>
          </section>

          <section><SectionHead id="method" n="12" title="Method & evaluation" blurb="How the numbers were produced, and how far to trust them." /><MethodSection a={a} /></section>
        </div>
      </div>
    </div>
  );
}
