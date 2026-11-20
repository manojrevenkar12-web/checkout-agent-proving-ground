export type Design = {
  correct_share: number;
  wrong_per_1000: number;
  duplicate_per_1000: number;
  silent_per_1000: number;
  rightly_not_bought_share: number;
  handoff_share: number;
  model_eur_per_correct: number;
  challenges: number;
  pages: number;
  contribution_eur: number;
  median_minutes: number;
  outcomes: Record<string, number>;
};

export type Report = {
  seeds: number[];
  worlds: { seed: number; intents: number; retailers: number; checkout_changes: number; feed_changes: number }[];
  checkout: Record<string, Design>;
  comparisons: Record<string, { mean: number; ci: [number, number]; n: number }>;
  by_day: Record<string, number[]>;
  change_days: Record<string, { changed: number; unchanged: number; changed_cells: number }>;
  ingestion: Record<string, { wrong_share: number; missing_share: number; model_eur: number; pages: number }>;
  search: Record<string, { hit_at_5: number; over_budget_shown: number; stale_price_shown: number }>;
};

export type Results = { dev: Report; heldout: Report | null; gate: { dev: { passed: boolean }; heldout: { passed: boolean } | null } };

export type IntentRow = { id: string; retailer: string; title: string; variant: string; qty: number; max_total: number; day: number; hour: number };

export type OrderResult = {
  key: string;
  replayed: boolean;
  state: string;
  order_id: string;
  reason: string;
  attempts: number;
  sessions?: string[][];
  seconds?: number;
  model_calls?: number;
};
