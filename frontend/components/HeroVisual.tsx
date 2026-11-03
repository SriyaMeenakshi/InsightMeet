"use client";

import { motion, useReducedMotion } from "framer-motion";

const LINES: { who: string; text: string; mark?: "action" | "decision" | "issue" | "suggestion" }[] = [
  { who: "Sriya", text: "ok guys lets start, the demo is coming up" },
  { who: "Rahul", text: "the login page is still broken on safari. i'll fix it by friday", mark: "action" },
  { who: "Ananya", text: "testing is blocked because the login isnt working", mark: "issue" },
  { who: "Sriya", text: "maybe we should use MongoDB for the database?", mark: "suggestion" },
  { who: "Rahul", text: "hmm i dont think so. sqlite is fine and cheaper" },
  { who: "Sriya", text: "fine, lets use SQLite for now", mark: "decision" },
  { who: "Sriya", text: "Rahul will finish the frontend by thursday", mark: "action" },
  { who: "Rahul", text: "that wont work, lets push it to monday" },
];

const MARK: Record<string, string> = {
  action: "bg-emerald/25 border-emerald",
  decision: "bg-forest/30 border-sage",
  issue: "bg-clay/25 border-[#d9826f]",
  suggestion: "bg-sage/25 border-sage/60 border-dashed",
};

export function HeroVisual() {
  const reduce = useReducedMotion();
  const fade = (d: number) =>
    reduce
      ? {}
      : { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.7, delay: d, ease: [0.22, 1, 0.36, 1] as const } };

  return (
    <div className="relative mx-auto w-full max-w-[560px] select-none" aria-hidden="true">
      {/* the messy transcript */}
      <motion.div {...fade(0.15)} className="relative rounded-xl border border-ivory/15 bg-forest-deep/70 p-5 shadow-2xl">
        <div className="mb-3 flex items-center justify-between text-[0.65rem] uppercase tracking-[0.16em] text-sage">
          <span>raw transcript</span>
          <span>8 of 30 lines</span>
        </div>
        <div className="space-y-2 font-mono text-[0.78rem] leading-relaxed text-ivory/80">
          {LINES.map((l, i) => (
            <p key={i} className="flex gap-2">
              <span className="w-14 shrink-0 text-sage/80">{l.who.toLowerCase()}:</span>
              <span className={l.mark ? `rounded-sm border-b px-0.5 ${MARK[l.mark]}` : ""}>{l.text}</span>
            </p>
          ))}
        </div>
      </motion.div>

      {/* extracted insights */}
      <motion.div
        {...fade(0.55)}
        className="relative z-10 -mt-6 ml-6 rounded-lg border border-line bg-[#fffdf8] p-4 text-charcoal shadow-xl sm:ml-16"
      >
        <p className="eyebrow !text-[0.62rem]">Action item · revised deadline</p>
        <p className="mt-1 font-serif text-lg leading-snug text-forest">Finish the frontend</p>
        <p className="mt-1 text-xs text-muted">
          Owner <b className="text-charcoal">Rahul</b> (named by Sriya) · <span className="line-through">Thu 13 Mar</span>{" "}
          <b className="text-emerald">Mon 17 Mar</b>
        </p>
      </motion.div>
      <motion.div
        {...fade(0.75)}
        className="relative z-20 -mt-2 mr-4 ml-0 w-[88%] rounded-lg border border-line bg-[#fffdf8] p-4 text-charcoal shadow-xl"
      >
        <p className="eyebrow !text-[0.62rem] !text-forest">Decision · accepted suggestion</p>
        <p className="mt-1 font-serif text-lg leading-snug text-forest">Use SQLite for now</p>
        <p className="mt-1 text-xs text-muted">MongoDB suggestion was rejected · 2 supporting sentences</p>
      </motion.div>
      <motion.div
        {...fade(0.95)}
        className="relative z-30 -mt-2 ml-auto mr-0 w-[78%] rounded-lg border border-[#e2b9ae] bg-[#fffdf8] p-4 text-charcoal shadow-xl"
      >
        <p className="eyebrow !text-[0.62rem] !text-clay">Issue · blocks testing</p>
        <p className="mt-1 font-serif text-lg leading-snug text-forest">Login isn’t working</p>
        <p className="mt-1 text-xs text-muted">Later marked resolved in sentence 23</p>
      </motion.div>
    </div>
  );
}
