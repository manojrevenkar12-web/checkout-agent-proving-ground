export const pct = (v: number, d = 1) => `${(v * 100).toFixed(d)}%`;
export const per1000 = (v: number) => v.toFixed(1);
export const eur = (v: number, d = 0) => `€${v.toLocaleString("en", { minimumFractionDigits: d, maximumFractionDigits: d })}`;

export const LABEL: Record<string, string> = {
  platform: "Proving-ground platform",
  model_only: "Computer-use model alone",
  scripted: "Scripts recorded on day 0",
  platform_no_guards: "Platform without code guards",
  platform_no_ledger: "Platform without the order ledger",
  platform_no_recipes: "Platform without recipes",
  platform_no_pacing: "Platform without pacing",
};
export const ORDER = ["platform", "model_only", "scripted", "platform_no_guards", "platform_no_ledger", "platform_no_recipes", "platform_no_pacing"];
