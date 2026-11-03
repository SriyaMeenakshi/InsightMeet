import Link from "next/link";
import { ArrowRight, ClipboardPaste, Upload } from "lucide-react";
import { HeroVisual } from "@/components/HeroVisual";
import { Reveal } from "@/components/Reveal";

const FEATURES = [
  {
    t: "Actions with a real owner",
    d: "Who is speaking is not who is responsible. InsightMeet separates the two, and tells you whether a commitment was firm, tentative, or only requested.",
  },
  {
    t: "Decisions, not wishful thinking",
    d: "“Maybe we should…” stays a suggestion until someone clearly agrees. Accepted, rejected and superseded ideas are tracked.",
  },
  {
    t: "Deadlines that remember",
    d: "Original and revised dates are kept side by side. Relative dates like “Friday” are resolved against your meeting date, never guessed.",
  },
  {
    t: "Issues and what they block",
    d: "Problems, their impact when the transcript states one, and whether they were fixed later in the same conversation.",
  },
  {
    t: "Relationships you can verify",
    d: "Task ownership, dependencies, blockers and the components a decision affects — each marked explicit or inferred.",
  },
  {
    t: "Ask your meeting",
    d: "Questions are answered from the transcript only. If the meeting never said it, InsightMeet says so.",
  },
];

const STEPS = [
  ["Read", "Speaker labels, sentences, tokens and lemmas — with the original text and character offsets untouched."],
  ["Classify", "TF-IDF + logistic regression plus transparent rules label every sentence: action, decision, issue, suggestion, information, question."],
  ["Extract", "Owners, deadlines, status, dependencies and conflicts are pulled from the sentences, with confidence and review flags."],
  ["Verify", "Every insight links back to its source sentence. Anything ambiguous goes to a review queue instead of being invented."],
];

export default function Home() {
  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <section className="on-dark relative overflow-hidden bg-forest text-ivory">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "repeating-linear-gradient(0deg, transparent 0 31px, rgba(245,242,234,1) 31px 32px)",
          }}
          aria-hidden="true"
        />
        <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-5 py-16 sm:px-8 md:py-24 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <Reveal inView={false}>
              <p className="eyebrow !text-sage">NLP meeting insight extraction</p>
            </Reveal>
            <Reveal inView={false} delay={0.08}>
              <h1 className="display mt-5 text-[2.9rem] text-ivory sm:text-6xl lg:text-[4.6rem]">
                Every meeting has a story. <em>Find what matters.</em>
              </h1>
            </Reveal>
            <Reveal inView={false} delay={0.18}>
              <p className="mt-6 max-w-xl text-[1.05rem] leading-relaxed text-ivory/75">
                InsightMeet turns messy, informal transcripts into actions, decisions, issues and deadlines — and ties
                every one of them to the sentence it came from. Where the meeting was unclear, it asks you instead of
                guessing.
              </p>
            </Reveal>
            <Reveal inView={false} delay={0.28}>
              <div className="mt-9 flex flex-wrap gap-3">
                <Link href="/workspace?mode=upload" className="btn btn-light">
                  <Upload size={17} /> Upload transcript
                </Link>
                <Link href="/workspace?mode=paste" className="btn btn-outline-light">
                  <ClipboardPaste size={17} /> Paste transcript
                </Link>
              </div>
              <p className="mt-4 text-sm text-ivory/60">
                No account, no API keys. <Link href="/workspace?example=1" className="underline underline-offset-4 hover:text-ivory">Try the built-in example</Link>.
              </p>
            </Reveal>
          </div>
          <HeroVisual />
        </div>
      </section>

      {/* ------------------------------------------------------------ features */}
      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 md:py-28">
        <Reveal>
          <div className="grid gap-6 md:grid-cols-[1fr_2fr] md:gap-16">
            <div>
              <p className="eyebrow">What it finds</p>
              <h2 className="display mt-3 text-4xl text-forest md:text-5xl">
                The parts of a meeting you’d <em>otherwise lose</em>.
              </h2>
            </div>
            <p className="max-w-xl self-end text-lg leading-relaxed text-muted">
              Meetings are corrected, repeated and half-committed. Plain keyword matching turns that into noise.
              InsightMeet models the difference between what was said, what was agreed, and what changed afterwards.
            </p>
          </div>
        </Reveal>
        <div className="mt-14 grid gap-x-12 gap-y-10 border-t border-forest pt-10 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.t} delay={(i % 3) * 0.07}>
              <div>
                <span className="font-serif text-sm italic text-emerald tabular-nums">0{i + 1}</span>
                <h3 className="mt-2 font-serif text-2xl leading-snug text-forest">{f.t}</h3>
                <p className="mt-2 text-[0.95rem] leading-relaxed text-muted">{f.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------ evidence */}
      <section className="bg-sage-soft/60 py-20 md:py-28">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-5 sm:px-8 lg:grid-cols-2">
          <Reveal>
            <p className="eyebrow">Evidence over inference</p>
            <h2 className="display mt-3 text-4xl text-forest md:text-5xl">
              The speaker isn’t the <em>owner</em>.
            </h2>
            <p className="mt-5 max-w-lg text-lg leading-relaxed text-muted">
              A naive extractor would assign this task to Sriya, because Sriya said it. InsightMeet reads who the task
              is about, keeps the exact sentence, and shows the deadline both as written and as a calendar date.
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="paper rounded-xl p-6 sm:p-8">
              <p className="font-mono text-sm leading-relaxed text-charcoal">
                <span className="text-emerald">[Sriya]</span> Rahul will finish the frontend by Thursday.
              </p>
              <div className="my-5 flex items-center gap-3 text-xs uppercase tracking-widest text-muted">
                <span className="h-px flex-1 bg-line" /> extracted <span className="h-px flex-1 bg-line" />
              </div>
              <dl className="grid grid-cols-[7.5rem_1fr] gap-y-3 text-sm">
                <dt className="text-muted">Task</dt><dd className="font-serif text-lg text-forest">Finish the frontend</dd>
                <dt className="text-muted">Owner</dt><dd><b>Rahul</b> <span className="text-muted">— named by Sriya</span></dd>
                <dt className="text-muted">Said by</dt><dd>Sriya</dd>
                <dt className="text-muted">Deadline</dt><dd>“Thursday” → <b>Thu 13 Mar 2025</b> <span className="text-muted">(meeting date 10 Mar)</span></dd>
                <dt className="text-muted">Evidence</dt><dd className="text-muted">sentence 1 · characters 7–50</dd>
              </dl>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ------------------------------------------------------------ how it works */}
      <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8 md:py-28">
        <Reveal>
          <p className="eyebrow">How it works</p>
          <h2 className="display mt-3 max-w-2xl text-4xl text-forest md:text-5xl">
            Classical NLP you can <em>inspect</em>.
          </h2>
        </Reveal>
        <ol className="mt-12 grid gap-8 border-t border-forest pt-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map(([t, d], i) => (
            <Reveal key={t} delay={i * 0.06}>
              <li className="list-none">
                <span className="font-serif text-4xl italic text-sage">{i + 1}</span>
                <h3 className="mt-2 font-serif text-2xl text-forest">{t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{d}</p>
              </li>
            </Reveal>
          ))}
        </ol>
        <p className="mt-10 max-w-2xl text-sm text-muted">
          Runs on your CPU with spaCy and scikit-learn. No paid APIs. The model’s evaluation, including its limits, is
          published inside every analysis.
        </p>
      </section>

      {/* ------------------------------------------------------------ audiences + CTA */}
      <section className="border-y hairline bg-ivory-deep/60">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 md:grid-cols-3">
          {[
            ["Students & project teams", "Who promised what for the next milestone — and which date is the current one."],
            ["Software teams", "Blockers, dependencies and the technology decisions that changed halfway through stand-up."],
            ["Remote professionals", "A trustworthy recap of a long call, with the receipts attached."],
          ].map(([t, d]) => (
            <div key={t}>
              <h3 className="font-serif text-xl text-forest">{t}</h3>
              <p className="mt-1.5 text-sm text-muted">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="on-dark bg-forest py-20 text-center text-ivory">
        <Reveal>
          <h2 className="display mx-auto max-w-3xl px-5 text-4xl sm:text-5xl">
            Bring a transcript. <em>Leave with the story.</em>
          </h2>
          <div className="mt-8 flex flex-wrap justify-center gap-3 px-5">
            <Link href="/workspace?mode=upload" className="btn btn-light">
              Upload transcript <ArrowRight size={16} />
            </Link>
            <Link href="/workspace?mode=paste" className="btn btn-outline-light">
              Paste transcript
            </Link>
          </div>
        </Reveal>
      </section>
    </>
  );
}
