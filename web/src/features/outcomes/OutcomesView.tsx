import { motion } from "framer-motion";
import { LABEL, eur, pct, per1000 } from "../../shared/format";
import { WithReport } from "../../shared/ui/Gate";
import { motion as m } from "../../theme/motion";
import { DayChart } from "./DayChart";

const COLS = ["platform", "model_only", "scripted"];

export function OutcomesView() {
  return (
    <WithReport label="Loading the outcome report">
      {(rep, held) => {
        const p = rep.checkout.platform;
        const rows: [string, (k: string) => string][] = [
          ["Bought exactly right (of purchasable intents)", (k) => pct(rep.checkout[k]?.correct_share ?? 0)],
          ["Wrong orders per 1,000", (k) => per1000(rep.checkout[k]?.wrong_per_1000 ?? 0)],
          ["Duplicate orders per 1,000", (k) => per1000(rep.checkout[k]?.duplicate_per_1000 ?? 0)],
          ["Shopper told something untrue, per 1,000", (k) => per1000(rep.checkout[k]?.silent_per_1000 ?? 0)],
          ["Impossible intents rightly not bought", (k) => pct(rep.checkout[k]?.rightly_not_bought_share ?? 0)],
          ["Model cost per correct order", (k) => `€${(rep.checkout[k]?.model_eur_per_correct ?? 0).toFixed(4)}`],
          ["Contribution per world", (k) => eur(rep.checkout[k]?.contribution_eur ?? 0)],
        ];
        return (
          <div className="space-y-8">
            <section>
              <h1 className="max-w-[24ch] text-hero font-bold">Bought exactly right, or not bought at all</h1>
              <p className="mt-3 max-w-prose text-lead text-muted">
                {pct(p?.correct_share ?? 0)} of purchasable intents bought exactly right with {per1000(p?.wrong_per_1000 ?? 0)} wrong and {per1000(p?.duplicate_per_1000 ?? 0)} duplicate orders per 1,000, on{" "}
                {rep.seeds.length} simulated worlds where retailers change their checkouts and push back on bots.
                {held && ` Held-out worlds: ${pct(held.checkout.platform?.correct_share ?? 0)}.`}
              </p>
            </section>
            <section aria-label="Receipt" className="max-w-[56rem] overflow-x-auto rounded-card border border-line bg-sheet p-5">
              <table className="w-full min-w-[40rem] text-left">
                <thead className="text-small text-muted">
                  <tr className="border-b border-line">
                    <th className="py-2 font-semibold">For every shopper intent</th>
                    {COLS.map((c) => (
                      <th key={c} className="py-2 text-right font-semibold">
                        {LABEL[c]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map(([name, f], i) => (
                    <motion.tr key={name} className="border-b border-dashed border-line" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * m.stagger, duration: m.settle }}>
                      <td className="py-2">{name}</td>
                      {COLS.map((c, j) => (
                        <td key={c} className={`py-2 text-right ${j === 0 ? "font-bold text-ink" : ""}`}>
                          {f(c)}
                        </td>
                      ))}
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="max-w-[56rem]">
              <h2 className="mb-3 text-title font-bold">Day by day</h2>
              <DayChart byDay={rep.by_day} />
            </section>
          </div>
        );
      }}
    </WithReport>
  );
}
