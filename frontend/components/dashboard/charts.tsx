"use client";

import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Label, Participant, Topic } from "@/lib/types";
import { LABEL_COLORS, LABEL_TEXT } from "@/components/ui";

const tooltipStyle = {
  background: "#fffdf8",
  border: "1px solid #dcd6c6",
  borderRadius: 8,
  fontSize: 12,
  boxShadow: "0 8px 24px -16px rgba(24,61,50,.4)",
};

export function TopicChart({ topics }: { topics: Topic[] }) {
  const data = topics.slice(0, 8).map((t) => ({ name: t.topic, mentions: t.mentions }));
  return (
    <div role="img" aria-label={`Bar chart of topic mentions: ${data.map((d) => `${d.name} ${d.mentions}`).join(", ")}`}>
      <ResponsiveContainer width="100%" height={data.length * 38 + 16}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 24, top: 0, bottom: 0 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={118}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 13, fill: "#242a26" }}
          />
          <Tooltip cursor={{ fill: "rgba(166,185,165,.2)" }} contentStyle={tooltipStyle} />
          <Bar dataKey="mentions" name="sentences" radius={[0, 4, 4, 0]} barSize={18} fill="#34765a" label={{ position: "right", fontSize: 12, fill: "#5c655f" }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ParticipantChart({ participants }: { participants: Participant[] }) {
  const data = participants.map((p) => ({ name: p.name, share: Math.round(p.share * 100) }));
  return (
    <div role="img" aria-label={`Share of words spoken: ${data.map((d) => `${d.name} ${d.share}%`).join(", ")}`}>
      <ResponsiveContainer width="100%" height={data.length * 38 + 16}>
        <BarChart data={data} layout="vertical" margin={{ left: 0, right: 36, top: 0, bottom: 0 }}>
          <XAxis type="number" hide domain={[0, 100]} />
          <YAxis type="category" dataKey="name" width={96} tickLine={false} axisLine={false} tick={{ fontSize: 13, fill: "#242a26" }} />
          <Tooltip cursor={{ fill: "rgba(166,185,165,.2)" }} contentStyle={tooltipStyle} />
          <Bar dataKey="share" name="% of words" radius={[0, 4, 4, 0]} barSize={18} fill="#183d32" label={{ position: "right", fontSize: 12, fill: "#5c655f", formatter: (v: unknown) => `${v}%` }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function DistributionDonut({ distribution }: { distribution: Record<Label, number> }) {
  const labels = Object.keys(LABEL_COLORS) as Label[];
  const data = labels.map((l) => ({ name: LABEL_TEXT[l], key: l, value: distribution[l] ?? 0 })).filter((d) => d.value > 0);
  const total = data.reduce((a, d) => a + d.value, 0);
  return (
    <div className="grid items-center gap-6 sm:grid-cols-[220px_1fr]">
      <div className="relative mx-auto h-[220px] w-[220px]" role="img" aria-label={`Sentence type distribution: ${data.map((d) => `${d.name} ${d.value}`).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={66} outerRadius={104} paddingAngle={2} stroke="#f5f2ea" strokeWidth={2}>
              {data.map((d) => (
                <Cell key={d.key} fill={LABEL_COLORS[d.key]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-serif text-3xl text-forest tabular-nums">{total}</span>
          <span className="text-[0.65rem] uppercase tracking-widest text-muted">sentences</span>
        </div>
      </div>
      <ul className="space-y-2.5">
        {labels.map((l) => {
          const v = distribution[l] ?? 0;
          const pct = total ? Math.round((v / total) * 100) : 0;
          return (
            <li key={l} className="flex items-center gap-3 text-sm">
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: LABEL_COLORS[l] }} />
              <span className="w-24 text-charcoal">{LABEL_TEXT[l]}</span>
              <span className="h-1.5 flex-1 rounded-full bg-ivory-deep">
                <span className="block h-full rounded-full" style={{ width: `${pct}%`, background: LABEL_COLORS[l] }} />
              </span>
              <span className="w-14 text-right tabular-nums text-muted">
                {v} · {pct}%
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function ConfusionMatrix({ labels, matrix }: { labels: string[]; matrix: number[][] }) {
  const rowMax = matrix.map((r) => Math.max(...r, 1));
  return (
    <div className="overflow-x-auto">
      <table className="min-w-[460px] border-separate border-spacing-1 text-center text-xs">
        <caption className="sr-only">Confusion matrix: rows are true labels, columns are predicted labels</caption>
        <thead>
          <tr>
            <th className="p-1 text-left font-normal text-muted">true ↓ / predicted →</th>
            {labels.map((l) => (
              <th key={l} className="p-1 font-semibold text-muted">
                {l.slice(0, 4)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th className="p-1 text-left font-semibold text-muted">{labels[i]}</th>
              {row.map((v, j) => {
                const a = v / rowMax[i];
                const diag = i === j;
                return (
                  <td
                    key={j}
                    className="h-9 w-12 rounded tabular-nums"
                    style={{
                      background: v === 0 ? "transparent" : diag ? `rgba(52,118,90,${0.18 + a * 0.75})` : `rgba(165,72,58,${0.12 + a * 0.6})`,
                      color: a > 0.55 ? "#fff" : "#242a26",
                    }}
                  >
                    {v || "·"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
