import { motion } from "framer-motion";
import { color } from "../../theme/tokens";

const SERIES: [string, string, string][] = [
  ["platform", color.platform, "Platform"],
  ["model_only", color.model, "Model alone"],
  ["scripted", color.scripted, "Day-0 scripts"],
];

/** Share of purchasable intents bought exactly right, per simulated day. */
export function DayChart({ byDay }: { byDay: Record<string, number[]> }) {
  const w = 720;
  const h = 260;
  const l = 44;
  const r = 130;
  const t = 12;
  const b = 28;
  const n = byDay.platform?.length ?? 0;
  const X = (i: number) => l + (i * (w - l - r)) / Math.max(1, n - 1);
  const Y = (v: number) => t + (1 - v) * (h - t - b);
  return (
    <figure>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Exactly right, day by day, for the platform, the model alone and day-0 scripts">
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={l} x2={w - r} y1={Y(v)} y2={Y(v)} stroke={color.line} />
            <text x={l - 6} y={Y(v) + 4} fontSize="11" textAnchor="end" fill={color.muted}>
              {v * 100}%
            </text>
          </g>
        ))}
        {SERIES.map(([k, c, name]) => {
          const vals = byDay[k] ?? [];
          const d = vals.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
          const last = vals[vals.length - 1] ?? 0;
          return (
            <g key={k}>
              <motion.path d={d} fill="none" stroke={c} strokeWidth={2} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }} />
              <text x={X(n - 1) + 8} y={Y(last) + 4} fontSize="12" fill={color.ink}>
                {name} {Math.round(last * 100)}%
              </text>
            </g>
          );
        })}
        <text x={l} y={h - 6} fontSize="11" fill={color.muted}>
          day 0
        </text>
        <text x={w - r} y={h - 6} fontSize="11" textAnchor="end" fill={color.muted}>
          day {n - 1}
        </text>
      </svg>
    </figure>
  );
}
