import type { ReactNode } from "react";
import { useResults } from "../useResults";
import type { Report } from "../types";
import { Empty, ErrorState, Loading } from "./states";

/** Every report view loads through this: skeleton, error with retry, empty when nothing was evaluated yet. */
export function WithReport({ label, children }: { label: string; children: (r: Report, held: Report | null) => ReactNode }) {
  const { data, error, loading, retry } = useResults();
  if (loading) return <Loading label={label} rows={8} />;
  if (error) return error.status === 404 ? <Empty title="No evaluation yet">Run `python -m cap.eval.cli evaluate` to write reports/dev.json.</Empty> : <ErrorState error={error} retry={retry} />;
  if (!data) return null;
  return <>{children(data.dev, data.heldout)}</>;
}
