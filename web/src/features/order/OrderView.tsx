import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { type Problem, placeOrder, useResource } from "../../shared/data";
import type { IntentRow, OrderResult } from "../../shared/types";
import { Empty, ErrorState, Loading } from "../../shared/ui/states";
import { motion as m } from "../../theme/motion";

const STATE_WORD: Record<string, string> = {
  confirmed: "Bought",
  abstained: "Not bought, and the shopper was told why",
  declined: "Payment declined",
  unknown: "Waiting to reconcile",
  failed: "Not bought yet",
};

/** Hand one of the demo world's intents to the agent; the same key never buys twice. */
export function OrderView() {
  const [day, setDay] = useState(3);
  const intents = useResource<IntentRow[]>(`/api/intents?day=${day}&limit=8`);
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<{ intent: IntentRow; res: OrderResult } | null>(null);
  const [error, setError] = useState<{ problem: Problem; intent: IntentRow } | null>(null);

  const buy = async (intent: IntentRow) => {
    setBusy(intent.id);
    setError(null);
    try {
      setResult({ intent, res: await placeOrder(intent.id, `ui-${intent.id}`.replace(/[^A-Za-z0-9_-]/g, "-").slice(0, 80)) });
    } catch (e) {
      setError({ problem: e as Problem, intent });
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid max-w-page gap-8 lg:grid-cols-[1fr_1fr]">
      <section>
        <h1 className="text-hero font-bold">Buy with the agent</h1>
        <p className="mt-3 max-w-prose text-lead text-muted">Intents from the demo world. Buying the same one again replays the ledger instead of paying twice.</p>
        <label className="mt-5 flex items-center gap-3 text-small font-semibold text-ink">
          Day
          <select value={day} onChange={(e) => setDay(Number(e.target.value))} className="rounded-soft border border-line bg-sheet px-3 py-2 font-normal">
            {Array.from({ length: 20 }, (_, i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </select>
        </label>
        <div className="mt-4">
          {intents.loading && <Loading label="Loading intents" rows={6} />}
          {intents.error && <ErrorState error={intents.error} retry={intents.retry} />}
          {intents.data && intents.data.length === 0 && <Empty title="No intents on this day">Pick another day.</Empty>}
          {intents.data && intents.data.length > 0 && (
            <ul className="divide-y divide-line rounded-card border border-line bg-sheet">
              {intents.data.map((i) => (
                <li key={i.id} className="flex items-center justify-between gap-3 p-3">
                  <span>
                    <b className="text-ink">{i.title}</b>, {i.variant} × {i.qty}
                    <span className="block text-small text-muted">
                      {i.retailer} · budget €{i.max_total.toFixed(2)}
                    </span>
                  </span>
                  <button type="button" disabled={busy !== null} onClick={() => buy(i)} className="shrink-0 rounded-soft bg-focus px-4 py-2 font-semibold text-sheet disabled:opacity-60">
                    {busy === i.id ? "Buying" : "Buy"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
      <section aria-label="Result">
        {busy && <Loading label="The agent is checking out" rows={10} />}
        {error && !busy && <ErrorState error={error.problem} retry={() => buy(error.intent)} />}
        {!busy && !error && !result && <Empty title="Nothing bought yet">Choose an intent; its checkout prints here, step by step.</Empty>}
        {!busy && result && (
          <div className="rounded-card border border-line bg-sheet p-5">
            <p className="text-small text-muted">{result.intent.retailer}</p>
            <p className="text-lead font-bold text-ink">
              {STATE_WORD[result.res.state] ?? result.res.state}
              {result.res.order_id && <span className="font-normal"> · order {result.res.order_id}</span>}
            </p>
            {result.res.reason && <p className="mt-1 text-muted">{result.res.reason}</p>}
            <p className="mt-1 text-small text-muted">
              {result.res.replayed ? "Replayed from the ledger; nothing was paid again." : `${result.res.seconds ?? 0} s in the browser · ${result.res.model_calls ?? 0} model calls`}
            </p>
            <ol className="mt-4 space-y-1 text-small">
              <AnimatePresence>
                {(result.res.sessions ?? []).flat().map((s, i) => (
                  <motion.li key={`${i}-${s}`} className="border-b border-dashed border-line py-1" initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * m.stagger, duration: m.settle }}>
                    {s}
                  </motion.li>
                ))}
              </AnimatePresence>
            </ol>
          </div>
        )}
      </section>
    </div>
  );
}
