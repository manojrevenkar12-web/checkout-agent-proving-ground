import { pct } from "../../shared/format";
import { WithReport } from "../../shared/ui/Gate";

const INGEST: Record<string, string> = { handwritten: "Hand-written parsers", model_every_item: "Model reads every item", self_checking: "Self-checking mappings" };
const SEARCH: Record<string, string> = {
  keywords_weekly_prices: "Keywords, prices from a weekly index",
  keywords_live_prices: "Keywords, live prices",
  understood_live_prices: "Query understanding, live prices",
};

export function DataView() {
  return (
    <WithReport label="Loading the ingestion report">
      {(rep) => (
        <div className="space-y-8">
          <section>
            <h1 className="max-w-[26ch] text-hero font-bold">Feeds that check themselves</h1>
            <p className="mt-3 max-w-prose text-lead text-muted">
              Retailers change feed formats and price encodings without notice. Self-checking mappings published {pct(rep.ingestion.self_checking?.wrong_share ?? 0, 2)} wrong prices; hand-written parsers{" "}
              {pct(rep.ingestion.handwritten?.wrong_share ?? 0, 2)}.
            </p>
          </section>
          <section className="max-w-[56rem] overflow-x-auto">
            <table className="w-full text-left">
              <thead className="text-small text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 font-semibold">Ingestion</th>
                  <th className="py-2 text-right font-semibold">Wrong prices published</th>
                  <th className="py-2 text-right font-semibold">Missing</th>
                  <th className="py-2 text-right font-semibold">Model cost per world</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(INGEST).map((k) => {
                  const x = rep.ingestion[k];
                  return (
                    <tr key={k} className={`border-b border-line ${k === "self_checking" ? "font-semibold text-ink" : ""}`}>
                      <td className="py-2">{INGEST[k]}</td>
                      <td className="py-2 text-right">{pct(x?.wrong_share ?? 0, 2)}</td>
                      <td className="py-2 text-right">{pct(x?.missing_share ?? 0, 2)}</td>
                      <td className="py-2 text-right">€{(x?.model_eur ?? 0).toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
          <section className="max-w-[56rem] overflow-x-auto">
            <h2 className="mb-3 text-title font-bold">Search over a moving catalogue</h2>
            <table className="w-full text-left">
              <thead className="text-small text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 font-semibold">Search</th>
                  <th className="py-2 text-right font-semibold">Wanted product in top 5</th>
                  <th className="py-2 text-right font-semibold">Above budget shown</th>
                  <th className="py-2 text-right font-semibold">Stale prices</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(SEARCH).map((k) => {
                  const x = rep.search[k];
                  return (
                    <tr key={k} className={`border-b border-line ${k === "understood_live_prices" ? "font-semibold text-ink" : ""}`}>
                      <td className="py-2">{SEARCH[k]}</td>
                      <td className="py-2 text-right">{pct(x?.hit_at_5 ?? 0)}</td>
                      <td className="py-2 text-right">{pct(x?.over_budget_shown ?? 0)}</td>
                      <td className="py-2 text-right">{pct(x?.stale_price_shown ?? 0)}</td>
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
