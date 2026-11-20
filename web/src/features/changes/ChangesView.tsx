import { LABEL, ORDER, pct, per1000 } from "../../shared/format";
import { WithReport } from "../../shared/ui/Gate";

export function ChangesView() {
  return (
    <WithReport label="Loading the design report">
      {(rep) => (
        <div className="space-y-8">
          <section>
            <h1 className="max-w-[26ch] text-hero font-bold">Retailers change. Checkouts keep working.</h1>
            <p className="mt-3 max-w-prose text-lead text-muted">
              On a day a retailer renamed its buttons, added a pop-up or moved its add-on, the platform bought {pct(rep.change_days.platform?.changed ?? 0)} of intents exactly right; day-0 scripts managed{" "}
              {pct(rep.change_days.scripted?.changed ?? 0)}.
            </p>
          </section>
          <section className="max-w-[60rem] overflow-x-auto">
            <h2 className="mb-3 text-title font-bold">Every design on the same luck</h2>
            <table className="w-full min-w-[44rem] text-left">
              <thead className="text-small text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 font-semibold">Design</th>
                  <th className="py-2 text-right font-semibold">Exactly right</th>
                  <th className="py-2 text-right font-semibold">Wrong / 1,000</th>
                  <th className="py-2 text-right font-semibold">Duplicates / 1,000</th>
                  <th className="py-2 text-right font-semibold">On change days</th>
                </tr>
              </thead>
              <tbody>
                {ORDER.filter((d) => rep.checkout[d]).map((d) => {
                  const x = rep.checkout[d];
                  const c = rep.change_days[d];
                  return (
                    <tr key={d} className={`border-b border-line ${d === "platform" ? "font-semibold text-ink" : ""}`}>
                      <td className="py-2">{LABEL[d]}</td>
                      <td className="py-2 text-right">{pct(x?.correct_share ?? 0)}</td>
                      <td className="py-2 text-right">{per1000(x?.wrong_per_1000 ?? 0)}</td>
                      <td className="py-2 text-right">{per1000(x?.duplicate_per_1000 ?? 0)}</td>
                      <td className="py-2 text-right">{c ? pct(c.changed) : "not tracked"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </WithReport>
  );
}
