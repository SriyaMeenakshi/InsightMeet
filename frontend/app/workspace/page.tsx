"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CalendarDays, FileText, Sparkles, Trash2, UploadCloud, X } from "lucide-react";
import { api } from "@/lib/api";
import { setLastMeeting } from "@/lib/storage";
import { ErrorBanner, Spinner } from "@/components/ui";
import { Reveal } from "@/components/Reveal";

const MAX_CHARS = 200_000;
const MAX_BYTES = 2 * 1024 * 1024;

function Workspace() {
  const router = useRouter();
  const params = useSearchParams();
  const fileRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadExample = useCallback(async () => {
    setError(null);
    try {
      const ex = await api.example();
      setText(ex.transcript);
      setTitle(ex.title);
      setDate(ex.meeting_date);
      setFileName(null);
      setNotice("Example transcript loaded. Edit it or press Analyze.");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    if (params.get("example")) void loadExample();
    else if (params.get("mode") === "paste") textRef.current?.focus();
    else if (params.get("mode") === "upload") fileRef.current?.focus();
  }, [params, loadExample]);

  async function handleFile(file: File | undefined | null) {
    if (!file) return;
    setError(null);
    setNotice(null);
    const ext = file.name.toLowerCase().split(".").pop();
    if (ext !== "txt" && ext !== "docx") {
      setError("Unsupported file type. Please choose a .txt or .docx file.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("That file is larger than 2 MB. Please upload a smaller transcript.");
      return;
    }
    setReading(true);
    try {
      const res = await api.extractText(file);
      setText(res.text);
      setFileName(res.filename);
      if (!title) setTitle(res.filename.replace(/\.[^.]+$/, ""));
      setNotice(`Loaded ${res.characters.toLocaleString("en-US")} characters from ${res.filename}. You can edit the text before analysing.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function analyze() {
    setError(null);
    setNotice(null);
    if (!text.trim()) {
      setError("Please paste or upload a transcript first.");
      return;
    }
    if (text.length > MAX_CHARS) {
      setError(`The transcript is ${text.length.toLocaleString("en-US")} characters; the limit is ${MAX_CHARS.toLocaleString("en-US")}.`);
      return;
    }
    setAnalyzing(true);
    try {
      const res = await api.analyze({ transcript: text, title: title.trim(), meeting_date: date });
      if (res.meeting_id) setLastMeeting(res.meeting_id);
      router.push(`/meeting/${res.meeting_id}`);
    } catch (e) {
      setError((e as Error).message);
      setAnalyzing(false);
    }
  }

  function clearAll() {
    setText("");
    setTitle("");
    setDate("");
    setFileName(null);
    setError(null);
    setNotice(null);
    textRef.current?.focus();
  }

  const over = text.length > MAX_CHARS;

  return (
    <div className="mx-auto max-w-7xl px-5 py-12 sm:px-8 md:py-16">
      <Reveal inView={false}>
        <p className="eyebrow">Transcript workspace</p>
        <h1 className="display mt-3 max-w-3xl text-4xl text-forest sm:text-5xl">
          Bring the conversation. <em>We’ll find the story.</em>
        </h1>
      </Reveal>

      <div className="mt-10 grid gap-10 lg:grid-cols-[1.7fr_1fr]">
        <section aria-label="Transcript input" className="space-y-5">
          {/* upload */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              void handleFile(e.dataTransfer.files?.[0]);
            }}
            className={`flex flex-col items-center gap-2 rounded-xl border-2 border-dashed px-6 py-7 text-center transition-colors ${
              dragging ? "border-emerald bg-sage-soft" : "border-line bg-white/50 hover:border-sage"
            }`}
          >
            <UploadCloud className="text-emerald" size={26} />
            <p className="text-sm text-charcoal">
              {reading ? (
                <span className="inline-flex items-center gap-2"><Spinner /> Reading file…</span>
              ) : (
                <>
                  Drag a <b>.txt</b> or <b>.docx</b> transcript here, or{" "}
                  <button
                    type="button"
                    onClick={() => fileRef.current?.click()}
                    className="font-semibold text-emerald underline underline-offset-4 hover:text-forest"
                  >
                    browse files
                  </button>
                </>
              )}
            </p>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.docx,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              aria-label="Upload transcript file"
              onChange={(e) => void handleFile(e.target.files?.[0])}
            />
            {fileName && (
              <span className="mt-1 inline-flex items-center gap-2 rounded-full border border-sage bg-sage-soft px-3 py-1 text-xs text-forest">
                <FileText size={13} /> {fileName}
                <button onClick={() => setFileName(null)} aria-label="Remove file label"><X size={13} /></button>
              </span>
            )}
          </div>

          {/* editor */}
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label htmlFor="transcript" className="text-sm font-semibold text-forest">
                Transcript
              </label>
              <span className={`text-xs tabular-nums ${over ? "font-semibold text-clay" : "text-muted"}`}>
                {text.length.toLocaleString("en-US")} / {MAX_CHARS.toLocaleString("en-US")} characters
              </span>
            </div>
            <textarea
              id="transcript"
              ref={textRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              spellCheck={false}
              placeholder={"Sriya: ok guys lets start. we need to finish the dashboard by friday\nRahul: i'll fix the login page tomorrow\nAnanya: testing is blocked because the login isn't working"}
              className="scrollbar-thin min-h-[22rem] w-full resize-y rounded-xl border border-line bg-[#fffdf8] p-4 font-mono text-[0.84rem] leading-relaxed text-charcoal shadow-inner placeholder:text-muted/60"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="title" className="mb-1.5 block text-sm font-semibold text-forest">
                Meeting title <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
                placeholder="Sprint planning"
                className="w-full rounded-lg border border-line bg-[#fffdf8] px-3.5 py-2.5 text-sm"
              />
            </div>
            <div>
              <label htmlFor="date" className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-forest">
                <CalendarDays size={14} /> Meeting date <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-lg border border-line bg-[#fffdf8] px-3.5 py-2.5 text-sm"
              />
              <p className="mt-1 text-xs text-muted">
                Needed to turn “Friday” or “tomorrow” into a calendar date. Without it they stay unresolved.
              </p>
            </div>
          </div>

          {error && <ErrorBanner message={error} />}
          {notice && !error && (
            <p role="status" className="rounded-lg bg-sage-soft px-4 py-2.5 text-sm text-forest">{notice}</p>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button className="btn btn-primary" onClick={analyze} disabled={analyzing || reading || !text.trim() || over}>
              {analyzing ? <><Spinner /> Analysing…</> : <><Sparkles size={16} /> Analyze transcript</>}
            </button>
            <button className="btn btn-ghost" onClick={clearAll} disabled={analyzing || (!text && !title && !date)}>
              <Trash2 size={15} /> Clear
            </button>
            <button className="btn text-forest underline underline-offset-4 hover:text-emerald" onClick={loadExample} disabled={analyzing}>
              Use example transcript
            </button>
          </div>
          {analyzing && (
            <p className="text-sm text-muted" role="status">
              Running preprocessing, classification and extraction on your CPU — the first analysis after starting the
              backend can take a few seconds.
            </p>
          )}
        </section>

        <aside className="space-y-8 lg:pt-8">
          <Reveal inView={false} delay={0.1}>
            <h2 className="font-serif text-2xl text-forest">What works best</h2>
            <ul className="mt-4 space-y-4 text-sm leading-relaxed text-muted">
              <li>
                <b className="text-charcoal">Speaker labels.</b> Lines like <code className="rounded bg-ivory-deep px-1">Name: message</code>{" "}
                or <code className="rounded bg-ivory-deep px-1">[10:02] Name: message</code>. Without them, owners can only come from
                names mentioned in the text.
              </li>
              <li>
                <b className="text-charcoal">Messy is fine.</b> Lower-case, missing apostrophes, corrections and repeated points are expected.
              </li>
              <li>
                <b className="text-charcoal">Word documents.</b> .docx paragraphs and two-column speaker/text tables are read.
              </li>
              <li>
                <b className="text-charcoal">Your text stays local.</b> Analyses are stored in a SQLite file on the machine running the
                backend — nothing is sent to an external service.
              </li>
            </ul>
          </Reveal>
          <Reveal inView={false} delay={0.2}>
            <div className="rounded-xl border border-line bg-white/60 p-5">
              <p className="eyebrow !text-[0.65rem]">Honest by design</p>
              <p className="mt-2 font-serif text-lg leading-snug text-forest">
                When the transcript is ambiguous, you’ll see a review flag, not a confident guess.
              </p>
            </div>
          </Reveal>
        </aside>
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={<div className="p-10 text-muted">Loading workspace…</div>}>
      <Workspace />
    </Suspense>
  );
}
