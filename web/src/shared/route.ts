import { useEffect, useState } from "react";

export type View = "outcomes" | "changes" | "data" | "order";
export const VIEWS: View[] = ["outcomes", "changes", "data", "order"];

function read(): View {
  const [, v] = window.location.hash.split("/");
  return VIEWS.includes(v as View) ? (v as View) : "outcomes";
}

export function useRoute(): View {
  const [r, setR] = useState(read);
  useEffect(() => {
    const on = () => setR(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return r;
}

export const go = (v: View) => {
  window.location.hash = `/${v}`;
};
