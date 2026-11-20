import { useCallback, useEffect, useState } from "react";
import type { OrderResult } from "./types";

export class Problem extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(path, { ...init, headers: { accept: "application/json", "content-type": "application/json" } });
  } catch {
    throw new Problem(0, "The service is not reachable. Start it with `uvicorn cap.service.api:app --port 8080`.");
  }
  const body = await r.json().catch(() => ({}));
  if (r.status === 404) throw new Problem(404, (body as { detail?: string }).detail ?? "Not found.");
  if (!r.ok) throw new Problem(r.status, (body as { detail?: string }).detail ?? `The service answered ${r.status}.`);
  return body as T;
}

export type Resource<T> = { data: T | null; error: Problem | null; loading: boolean; retry: () => void };

export function useResource<T>(path: string): Resource<T> {
  const [s, setS] = useState<{ data: T | null; error: Problem | null; loading: boolean }>({ data: null, error: null, loading: true });
  const [n, setN] = useState(0);
  useEffect(() => {
    let live = true;
    setS((x) => ({ ...x, loading: true, error: null }));
    call<T>(path)
      .then((data) => live && setS({ data, error: null, loading: false }))
      .catch((error: Problem) => live && setS({ data: null, error, loading: false }));
    return () => {
      live = false;
    };
  }, [path, n]);
  return { ...s, retry: useCallback(() => setN((x) => x + 1), []) };
}

export const placeOrder = (intentId: string, key: string) =>
  call<OrderResult>("/api/orders", { method: "POST", body: JSON.stringify({ idempotency_key: key, intent_id: intentId }) });
