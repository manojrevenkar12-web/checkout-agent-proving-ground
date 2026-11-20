/**
 * Tokens for a checkout flight recorder. Cool paper ground and a dark blue-black ink, like a till receipt under
 * office light; one indigo for focus and the active view. Outcomes use status colours with words beside them, never
 * colour alone. Series use the validated categorical slots in fixed order: blue the platform, orange day-0 scripts,
 * aqua the model alone. Schibsted Grotesk throughout, with tabular figures.
 */
export const color = {
  ground: "#EEF0F3",
  sheet: "#FFFFFF",
  ink: "#121826",
  copy: "#2A3140",
  muted: "#586070",
  line: "#D4D9E0",
  focus: "#3A3FD9",
  focusWash: "#E3E4FB",
  good: "#0F6B3E",
  goodWash: "#DCF1E5",
  bad: "#B42318",
  badWash: "#FBE4E1",
  warn: "#8A5300",
  warnWash: "#FBEFD9",
  platform: "#2a78d6",
  scripted: "#eb6834",
  model: "#1baf7a",
} as const;

export const font = { ui: ["Schibsted Grotesk Variable", "Schibsted Grotesk", "system-ui", "sans-serif"] } as const;

export const type = {
  small: ["0.8125rem", "1.45"],
  body: ["0.9375rem", "1.55"],
  lead: ["1.1875rem", "1.4"],
  title: ["1.75rem", "1.15"],
  hero: ["2.5rem", "1.08"],
} as const;

export const space = { 0: "0", 1: "0.25rem", 2: "0.5rem", 3: "0.75rem", 4: "1rem", 5: "1.5rem", 6: "2rem", 7: "3rem", 8: "4rem" } as const;
export const radius = { none: "0", soft: "3px", card: "6px", pill: "999px" } as const;
export const measure = { prose: "66ch", page: "76rem", column: "36rem" } as const;
export const line = { hair: "1px", rule: "2px" } as const;
export const size = { chip: "1.375rem", bar: "0.875rem", label: "13rem", swatch: "0.625rem" } as const;
