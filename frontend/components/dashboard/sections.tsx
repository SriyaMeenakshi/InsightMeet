"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import type {
  ActionItem, Analysis, DeadlineEntry, DeadlineInfo, Decision, Issue, Label, ModelMetrics, Relationship, SentenceOut, Suggestion,
} from "@/lib/types";
import { api } from "@/lib/api";
import { Badge, Empty, EvidenceList, LABEL_COLORS, LABEL_TEXT, LabelChip, confidenceLabel } from "@/components/ui";
import { ConfusionMatrix } from "./charts";

export function Dl({ d }: { d: DeadlineInfo | null }) {
  if (!d) return <span className="text-muted">none stated</span>;
  if (d.resolved) {
    return (
      <span>
        <b className="font-semibold text-charcoal">{d.normalized}</b>{" "}
        <span className="text-xs text-muted">“{d.raw}”</span>
      </span>
    );
  }
  return (
    <span title={d.note ?? undefined}>
      “{d.raw}” <Badge tone="amber">date unresolved</Badge>
    </span>
  );
}

function Details({ summary, children }: { summary: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="inline-flex items-center gap-1 text-xs font-semibold text-emerald hover:text-forest"
      >
        <ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} /> {summary}
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

function Reasons({ reasons }: { reasons: string[] }) {
  if (!reasons.length) return null;
  return (
    <ul className="mt-2 space-y-1 rounded-md bg-amber-soft px-3 py-2 text-xs text-amber">
      {reasons.map((r) => (
        <li key={r}>⚑ {r}</li>
      ))}
    </ul>
  );
}

const COMMIT_TONE = { definite: "green", tentative: "amber", requested: "amber", unassigned: "neutral" } as const;

export function ActionsSection({ a, mid }: { a: Analysis; mid: string }) {
  const [owner, setOwner] = useState("all");
  const [flt, setFlt] = useState("all");
  const owners = useMemo(() => Array.from(new Set(a.action_items.flatMap((x) => x.owners))), [a]);
  const rows = a.action_items.filter((x) => {
    if (owner === "none" && x.owners.length) return false;
    if (owner !== "all" && owner !== "none" && !x.owners.includes(owner)) return false;
    if (flt === "open") return x.status === "open";
    if (flt === "done") return x.status === "done";
    if (flt === "blocked") return x.blocked;
    if (flt === "review") return x.needs_review;
    return true;
  });
  if (!a.action_items.length) return <Empty>No action items were found in this transcript.</Empty>;
  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3 text-sm">
        <select aria-label="Filter by owner" value={owner} onChange={(e) => setOwner(e.target.value)} className="rounded-lg border border-line bg-[#fffdf8] px-3 py-2">
          <option value="all">All owners</option>
          {owners.map((o) => <option key={o}>{o}</option>)}
          <option value="none">No owner</option>
        </select>
        <select aria-label="Filter by status" value={flt} onChange={(e) => setFlt(e.target.value)} className="rounded-lg border border-line bg-[#fffdf8] px-3 py-2">
          <option value="all">Any status</option>
          <option value="open">Open</option>
          <option value="done">Done</option>
          <option value="blocked">Blocked</option>
          <option value="review">Needs review</option>
        </select>
        <span className="self-center text-xs text-muted">{rows.length} of {a.action_items.length}</span>
      </div>
      <div className="divide-y hairline border-y hairline">
        {rows.map((x: ActionItem) => (
          <article key={x.id} className="grid gap-x-8 gap-y-2 py-5 md:grid-cols-[1.6fr_1fr_1.2fr]">
            <div>
              <p className="font-serif text-xl leading-snug text-forest">{x.task}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge tone={COMMIT_TONE[x.commitment]}>{x.commitment}</Badge>
                {x.status === "done" && <Badge tone="forest">done</Badge>}
                {x.blocked && <Badge tone="clay">blocked</Badge>}
                {x.needs_review && <Badge tone="amber">needs review</Badge>}
                {x.mentions > 1 && <Badge>mentioned {x.mentions}×</Badge>}
              </div>
            </div>
            <div className="text-sm">
              <p className="eyebrow !text-[0.62rem] !text-muted">Responsible</p>
              <p className="mt-0.5 text-charcoal">{x.owner ?? <span className="text-muted">not stated</span>}</p>
              {x.owner_basis && <p className="text-xs text-muted">{x.owner_basis}</p>}
              {x.said_by && x.owner && x.said_by !== x.owner && <p className="text-xs text-muted">said by {x.said_by}</p>}
            </div>
            <div className="text-sm">
              <p className="eyebrow !text-[0.62rem] !text-muted">Deadline</p>
              {x.original_deadline && x.deadline ? (
                <p className="mt-0.5">
                  <span className="text-muted line-through">{x.original_deadline.normalized}</span> → <Dl d={x.deadline} />
                </p>
              ) : (
                <p className="mt-0.5"><Dl d={x.deadline} /></p>
              )}
              <p className="mt-1 text-xs text-muted">{confidenceLabel(x.confidence)} ({x.confidence.toFixed(2)})</p>
            </div>
            <div className="md:col-span-3">
              {x.context && <p className="text-xs text-muted">Refers to: “{x.context}”</p>}
              <Reasons reasons={x.review_reasons} />
              <Details summary={`Supporting sentences (${x.evidence.length})`}>
                <EvidenceList items={x.evidence} meetingId={mid} max={6} />
              </Details>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function DecisionsSection({ items, mid }: { items: Decision[]; mid: string }) {
  if (!items.length) return <Empty>No confirmed decisions. Suggestions that nobody agreed to are listed separately.</Empty>;
  return (
    <div className="divide-y hairline border-y hairline">
      {items.map((d) => (
        <article key={d.id} className={`py-5 ${d.status === "superseded" ? "opacity-70" : ""}`}>
          <p className={`font-serif text-xl leading-snug text-forest ${d.status === "superseded" ? "line-through decoration-1" : ""}`}>{d.text}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone={d.status === "confirmed" ? "forest" : "neutral"}>{d.status}</Badge>
            <Badge tone="sage">{d.basis}</Badge>
            {d.decided_by && <Badge>by {d.decided_by}</Badge>}
            {d.superseded_by && <Badge tone="amber">replaced by {d.superseded_by}</Badge>}
            {d.supersedes && <Badge tone="green">replaces {d.supersedes}</Badge>}
            {d.components.map((c) => <Badge key={c}>{c}</Badge>)}
          </div>
          <Reasons reasons={d.review_reasons} />
          <EvidenceList items={d.evidence} meetingId={mid} />
        </article>
      ))}
    </div>
  );
}

export function IssuesSection({ items, mid }: { items: Issue[]; mid: string }) {
  if (!items.length) return <Empty>No issues or blockers were detected.</Empty>;
  return (
    <div className="divide-y hairline border-y hairline">
      {items.map((i) => (
        <article key={i.id} className="py-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <p className="max-w-3xl font-serif text-xl leading-snug text-forest">{i.problem}</p>
            <Badge tone={i.status === "open" ? "clay" : "green"}>{i.status}</Badge>
          </div>
          <dl className="mt-2 grid gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
            <div><dt className="eyebrow !text-[0.62rem] !text-muted">Component</dt><dd>{i.component ?? <span className="text-muted">not stated</span>}</dd></div>
            <div><dt className="eyebrow !text-[0.62rem] !text-muted">Impact (only if stated)</dt><dd>{i.impact ?? <span className="text-muted">not stated</span>}</dd></div>
            <div><dt className="eyebrow !text-[0.62rem] !text-muted">Raised by</dt><dd>{i.raised_by ?? "—"}</dd></div>
          </dl>
          <Reasons reasons={i.review_reasons} />
          <EvidenceList items={i.evidence} meetingId={mid} />
        </article>
      ))}
    </div>
  );
}

export function SuggestionsSection({ items, mid }: { items: Suggestion[]; mid: string }) {
  if (!items.length) return <Empty>No suggestions or tentative proposals were found.</Empty>;
  const tone = { unconfirmed: "amber", accepted: "green", rejected: "clay" } as const;
  return (
    <div className="divide-y hairline border-y hairline">
      {items.map((s) => (
        <article key={s.id} className="py-5">
          <p className="font-serif text-xl leading-snug text-forest">{s.text}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <Badge tone={tone[s.status]}>{s.status}</Badge>
            {s.proposer && <Badge>proposed by {s.proposer}</Badge>}
          </div>
          <EvidenceList items={s.response ? [...s.evidence, s.response] : s.evidence} meetingId={mid} label={s.response ? "Proposal and response" : "Evidence"} />
        </article>
      ))}
    </div>
  );
}

export function DeadlinesSection({ items, mid }: { items: DeadlineEntry[]; mid: string }) {
  if (!items.length) return <Empty>No deadlines were mentioned.</Empty>;
  const groups = new Map<string, DeadlineEntry[]>();
  items.forEach((e) => {
    const k = e.task_id ?? `x-${e.id}`;
    groups.set(k, [...(groups.get(k) ?? []), e]);
  });
  const list = Array.from(groups.values());
  const latest = (g: DeadlineEntry[]) => g.find((e) => e.is_latest) ?? g[g.length - 1];
  const dated = list.filter((g) => latest(g).deadline.date).sort((a, b) => latest(a).deadline.date!.localeCompare(latest(b).deadline.date!));
  const undated = list.filter((g) => !latest(g).deadline.date);
  const Row = ({ g }: { g: DeadlineEntry[] }) => {
    const l = latest(g);
    return (
      <li className="grid gap-2 py-4 sm:grid-cols-[11rem_1fr]">
        <div className="font-serif text-lg text-forest">{l.deadline.resolved ? l.deadline.normalized : `“${l.deadline.raw}”`}</div>
        <div>
          <p className="text-charcoal">{l.task ?? "Unspecified item"}{l.owner && <span className="text-muted"> — {l.owner}</span>}</p>
          {g.length > 1 && (
            <p className="mt-1 text-xs text-muted">
              History:{" "}
              {g.map((e, i) => (
                <span key={e.id}>
                  {i > 0 && " → "}
                  <span className={e.superseded ? "line-through" : "font-semibold text-emerald"}>{e.deadline.normalized}</span>{" "}
                  <span>({e.role})</span>
                </span>
              ))}
            </p>
          )}
          {!l.deadline.resolved && l.deadline.note && <p className="mt-1 text-xs text-amber">{l.deadline.note}</p>}
          <EvidenceList items={[l.evidence]} meetingId={mid} label="Source" />
        </div>
      </li>
    );
  };
  return (
    <div>
      {dated.length > 0 && (
        <>
          <p className="eyebrow mb-1">In calendar order (latest value per item)</p>
          <ol className="divide-y hairline border-y hairline">{dated.map((g) => <Row key={g[0].id} g={g} />)}</ol>
        </>
      )}
      {undated.length > 0 && (
        <>
          <p className="eyebrow mb-1 mt-8">Not resolved to a calendar date</p>
          <ol className="divide-y hairline border-y hairline">{undated.map((g) => <Row key={g[0].id} g={g} />)}</ol>
        </>
      )}
    </div>
  );
}

export function RelationsSection({ items, mid }: { items: Relationship[]; mid: string }) {
  if (!items.length) return <Empty>No relationships were detected.</Empty>;
  const groups: [Relationship["type"], string, string][] = [
    ["ASSIGNED_TO", "Responsible for", "person → task"],
    ["DEPENDS_ON", "Depends on", "task → prerequisite"],
    ["BLOCKS", "Blocks", "issue → activity"],
    ["AFFECTS", "Decision affects", "decision → component"],
  ];
  return (
    <div className="grid gap-10 lg:grid-cols-2">
      {groups.map(([t, title, hint]) => {
        const rs = items.filter((r) => r.type === t);
        return (
          <div key={t}>
            <h3 className="font-serif text-xl text-forest">{title} <span className="text-sm italic text-muted">{hint}</span></h3>
            {rs.length === 0 ? <p className="mt-2 text-sm text-muted">None found.</p> : (
              <ul className="mt-3 divide-y hairline border-y hairline">
                {rs.map((r) => (
                  <li key={r.id} className="py-3 text-sm">
                    <p>
                      <b className="text-charcoal">{r.source.text.length > 60 ? r.source.text.slice(0, 58) + "…" : r.source.text}</b>
                      <span className="mx-2 text-emerald">→</span>
                      {r.target.text.length > 60 ? r.target.text.slice(0, 58) + "…" : r.target.text}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      <Badge tone={r.explicit ? "green" : "amber"}>{r.explicit ? "explicit" : "inferred"}</Badge>
                      <span className="text-xs text-muted">{r.basis}</span>
                    </div>
                    <Details summary="Evidence"><EvidenceList items={r.evidence} meetingId={mid} /></Details>
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function TranscriptSection({ sentences }: { sentences: SentenceOut[] }) {
  const [active, setActive] = useState<Set<Label>>(new Set());
  const [q, setQ] = useState("");
  const [flash, setFlash] = useState<number | null>(null);

  useEffect(() => {
    const go = () => {
      const m = window.location.hash.match(/^#s-(\d+)$/);
      if (!m) return;
      const id = Number(m[1]);
      setActive(new Set());
      setQ("");
      setFlash(id);
      setTimeout(() => document.getElementById(`s-${id}`)?.scrollIntoView({ block: "center", behavior: "smooth" }), 60);
    };
    go();
    window.addEventListener("hashchange", go);
    return () => window.removeEventListener("hashchange", go);
  }, []);

  const rows = sentences.filter(
    (s) => (active.size === 0 || active.has(s.label)) && (!q.trim() || s.original.toLowerCase().includes(q.trim().toLowerCase()) || (s.speaker ?? "").toLowerCase().includes(q.trim().toLowerCase())),
  );
  const labels = Object.keys(LABEL_COLORS) as Label[];
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {labels.map((l) => {
          const on = active.has(l);
          return (
            <button
              key={l}
              aria-pressed={on}
              onClick={() => setActive((p) => { const n = new Set(p); if (n.has(l)) n.delete(l); else n.add(l); return n; })}
              className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${on ? "border-forest bg-forest text-ivory" : "border-line bg-[#fffdf8] text-muted hover:border-sage"}`}
            >
              <span className="mr-1.5 inline-block h-2 w-2 rounded-full" style={{ background: LABEL_COLORS[l] }} />
              {LABEL_TEXT[l]}
            </button>
          );
        })}
        <div className="relative ml-auto w-full sm:w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter sentences or speakers" aria-label="Filter transcript" className="w-full rounded-full border border-line bg-[#fffdf8] py-2 pl-9 pr-3 text-sm" />
        </div>
      </div>
      <div className="scrollbar-thin max-h-[34rem] overflow-y-auto border-y hairline">
        {rows.length === 0 && <p className="p-6 text-center text-sm text-muted">No sentences match.</p>}
        {rows.map((s) => (
          <div key={s.id} id={`s-${s.id}`} className={`grid grid-cols-[2.5rem_1fr] gap-x-3 border-b hairline px-2 py-2.5 text-sm last:border-b-0 sm:grid-cols-[2.5rem_6rem_1fr_9rem] ${flash === s.id ? "mark-flash" : ""}`}>
            <span className="tabular-nums text-xs text-muted">{s.id + 1}</span>
            <span className="hidden truncate font-semibold text-forest sm:block">{s.speaker ?? "—"}</span>
            <span className="leading-relaxed"><span className="font-semibold text-forest sm:hidden">{s.speaker ? s.speaker + ": " : ""}</span>{s.original}</span>
            <span className="col-start-2 sm:col-start-auto sm:text-right">
              <LabelChip label={s.label} />
              <span className="ml-2 text-[0.65rem] text-muted" title={`model said ${s.model_label} (${s.model_confidence})`}>{s.label_source}</span>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-xs text-muted">Showing {rows.length} of {sentences.length}. “rules” = a transparent cue matched; “model” = TF-IDF + logistic regression.</p>
    </div>
  );
}

export function MethodSection({ a }: { a: Analysis }) {
  const [m, setM] = useState<ModelMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { api.metrics().then(setM).catch((e: Error) => setErr(e.message)); }, []);
  const r = a.representation;
  const pct = (v: number) => (v * 100).toFixed(1) + "%";
  const names: Record<string, string> = { logreg: "TF-IDF + Logistic Regression", naive_bayes: "TF-IDF + Naive Bayes", svm: "TF-IDF + Linear SVM", logreg_plus_rules: "Logistic Regression + rules (served)" };
  return (
    <div className="space-y-10">
      <div>
        <h3 className="font-serif text-xl text-forest">Sparse vs dense representations (this transcript)</h3>
        {r.available && r.bag_of_words && r.tfidf ? (
          <>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[520px] text-sm">
                <thead><tr className="border-b hairline text-left text-xs uppercase tracking-wider text-muted"><th className="py-2">Representation</th><th>Type</th><th>Shape</th><th>Cells that are non-zero</th></tr></thead>
                <tbody className="divide-y hairline">
                  <tr><td className="py-2">Bag of Words</td><td>sparse</td><td>{r.bag_of_words.shape.join(" × ")}</td><td>{pct(r.bag_of_words.density)}</td></tr>
                  <tr><td className="py-2">TF-IDF</td><td>sparse</td><td>{r.tfidf.shape.join(" × ")}</td><td>{pct(r.tfidf.density)}</td></tr>
                  {r.lsa && <tr><td className="py-2">LSA (SVD of TF-IDF)</td><td>dense</td><td>{r.sentences} × {r.lsa.dimensions}</td><td>{pct(r.lsa.cell_density)} <span className="text-muted">({pct(r.lsa.explained_variance)} variance kept)</span></td></tr>}
                </tbody>
              </table>
            </div>
            <p className="mt-3 flex flex-wrap gap-1.5 text-xs">
              <span className="text-muted">Highest TF-IDF terms:</span>
              {r.tfidf.top_terms.map((t) => <Badge key={t.term} tone="sage">{t.term} · {t.weight}</Badge>)}
            </p>
            <p className="mt-2 max-w-3xl text-xs text-muted">{r.note}</p>
          </>
        ) : <p className="mt-2 text-sm text-muted">Not enough sentences to compute representations.</p>}
      </div>

      <div>
        <h3 className="font-serif text-xl text-forest">Sentence classifier evaluation</h3>
        {err && <p className="mt-2 text-sm text-clay">{err}</p>}
        {m && (
          <>
            <p className="mt-2 max-w-3xl text-sm text-muted">{m.split_policy} Sizes: {Object.entries(m.dataset.sizes).map(([k, v]) => `${k} ${v}`).join(", ")}.</p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead><tr className="border-b hairline text-left text-xs uppercase tracking-wider text-muted"><th className="py-2">Model</th><th>Split</th><th>Accuracy</th><th>Macro P</th><th>Macro R</th><th>Macro F1</th></tr></thead>
                <tbody className="divide-y hairline">
                  {Object.entries(m.results).flatMap(([k, splits]) =>
                    Object.entries(splits).filter(([s]) => s !== "validation").map(([s, v]) => (
                      <tr key={k + s}><td className="py-2">{names[k] ?? k}</td><td>{s === "test" ? "synthetic test" : s}</td><td>{pct(v.accuracy)}</td><td>{pct(v.macro_precision)}</td><td>{pct(v.macro_recall)}</td><td>{pct(v.macro_f1)}</td></tr>
                    )))}
                </tbody>
              </table>
            </div>
            <div className="mt-6">
              <p className="mb-2 text-sm font-semibold text-forest">Logistic regression confusion matrix (synthetic test split)</p>
              <ConfusionMatrix labels={m.labels} matrix={m.results.logreg.test.confusion_matrix} />
            </div>
            <p className="mt-4 max-w-3xl rounded-lg bg-amber-soft px-4 py-3 text-xs leading-relaxed text-amber">{m.caveat}</p>
          </>
        )}
        <p className="mt-4 text-xs text-muted">{a.nlp_info.confidence_note}</p>
      </div>
    </div>
  );
}
