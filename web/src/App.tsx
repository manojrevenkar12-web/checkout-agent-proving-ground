import { ChangesView } from "./features/changes/ChangesView";
import { DataView } from "./features/data/DataView";
import { OrderView } from "./features/order/OrderView";
import { OutcomesView } from "./features/outcomes/OutcomesView";
import { type View, go, useRoute } from "./shared/route";

const TABS: { view: View; label: string }[] = [
  { view: "outcomes", label: "Outcomes" },
  { view: "changes", label: "Retailer changes" },
  { view: "data", label: "Feeds and search" },
  { view: "order", label: "Buy with the agent" },
];

export function App() {
  const view = useRoute();
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-sheet">
        <div className="mx-auto flex max-w-page flex-wrap items-end justify-between gap-4 px-6 pt-5">
          <div className="pb-4">
            <p className="text-lead font-bold text-ink">Checkout agent proving ground</p>
            <p className="text-small text-muted">Shopping agents that buy on the open web without buying wrong, measured on simulated retailers</p>
          </div>
          <nav aria-label="Views" className="flex flex-wrap gap-1">
            {TABS.map((t) => (
              <button key={t.view} type="button" onClick={() => go(t.view)} aria-current={view === t.view ? "page" : undefined}
                className={`border-b-rule px-3 pb-3 pt-2 font-semibold transition-colors ${view === t.view ? "border-focus text-ink" : "border-transparent text-muted hover:text-ink"}`}>
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-page px-6 py-7">
        {view === "outcomes" && <OutcomesView />}
        {view === "changes" && <ChangesView />}
        {view === "data" && <DataView />}
        {view === "order" && <OrderView />}
      </main>
    </div>
  );
}
