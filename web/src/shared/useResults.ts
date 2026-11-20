import { useResource } from "./data";
import type { Results } from "./types";

export const useResults = () => useResource<Results>("/api/results");
