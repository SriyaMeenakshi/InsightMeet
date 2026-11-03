import Link from "next/link";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { Evidence, Label } from "@/lib/types";

export const LABEL_COLORS: Record<Label, string> = {
  ACTION: "#34765a",
  DECISION: "#183d32",
  ISSUE: "#a5483a",
  SUGGESTION: "#a6b9a5",
  INFORMATION: "#cfc9b8",
  QUESTION: "#b8861f",
};

export const LABEL_TEXT: Record<Label, string> = {
  ACTION: "Action",
  DECISION: "Decision",
  ISSUE: "Issue",
  SUGGESTION: "Suggestion",
  INFORMATION: "Information",
  QUESTION: "Question",
};

type Tone = "neutral" | "green" | "forest" | "clay" | "amber" | "sage";
const TONES: Record<Tone, string> = {
  neutral: "bg-ivory-deep text-muted border-line",
  green: "bg-sage-soft text-forest border-sage",
  forest: "bg-forest text-ivory border-forest",
  clay: "bg-clay-soft text-clay border-[#e2b9ae]",
  amber: "bg-amber-soft text-amber border-[#e4cf9d]",
  sage: "bg-white text-emerald border-sage",
};

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: React.ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[0.7rem] font-semibold leading-5 whitespace-nowrap ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}

export function LabelChip({ label }: { label: Label }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wider text-muted">
      <span className="h-2 w-2 rounded-full" style={{ background: LABEL_COLORS[label] }} />
      {LABEL_TEXT[label]}
    </span>
  );
}

export function SectionHead({
  n,
  title,
  blurb,
  id,
}: {
  n: string;
  title: React.ReactNode;
  blurb?: React.ReactNode;
  id?: string;
}) {
  return (
    <div id={id} className="mb-6 flex flex-col gap-2 border-t border-forest pt-4 sm:flex-row sm:items-baseline sm:gap-8">
      <span className="font-serif text-sm italic text-emerald tabular-nums sm:w-10">{n}</span>
      <div className="flex-1">
        <h2 className="font-serif text-3xl tracking-tight text-forest sm:text-[2.1rem]">{title}</h2>
        {blurb && <p className="mt-1.5 max-w-2xl text-sm text-muted">{blurb}</p>}
      </div>
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-line px-5 py-8 text-center text-sm text-muted">{children}</div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} size={18} aria-hidden="true" />;
}

export function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-[#e2b9ae] bg-clay-soft px-4 py-3 text-sm text-clay">
      <AlertTriangle size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1">{message}</div>
      {onRetry && (
        <button onClick={onRetry} className="font-semibold underline underline-offset-2">
          Retry
        </button>
      )}
    </div>
  );
}

/** A quoted sentence from the transcript with a link back to its position. */
export function EvidenceList({
  items,
  meetingId,
  max = 3,
  label = "Evidence",
}: {
  items: Evidence[];
  meetingId?: string | null;
  max?: number;
  label?: string;
}) {
  if (!items.length) return null;
  return (
    <div className="mt-3 space-y-2">
      <p className="eyebrow !text-[0.65rem] !text-muted">{label}</p>
      {items.slice(0, max).map((e) => (
        <blockquote key={e.sentence_id} className="border-l-2 border-sage pl-3 text-sm leading-relaxed">
          <p className="font-serif text-[0.95rem] italic text-charcoal">“{e.text.trim()}”</p>
          <p className="mt-0.5 text-xs text-muted">
            {e.speaker ?? "Unknown speaker"} · sentence {e.sentence_id + 1} · chars {e.start}–{e.end} ·{" "}
            <Link
              href={meetingId ? `/meeting/${meetingId}#s-${e.sentence_id}` : `#s-${e.sentence_id}`}
              className="font-medium text-emerald underline underline-offset-2 hover:text-forest"
            >
              view in transcript
            </Link>
          </p>
        </blockquote>
      ))}
      {items.length > max && <p className="text-xs text-muted">+ {items.length - max} more supporting sentence(s)</p>}
    </div>
  );
}

export function confidenceLabel(c: number): string {
  return c >= 0.8 ? "strong cue" : c >= 0.6 ? "moderate cue" : "weak cue";
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}
