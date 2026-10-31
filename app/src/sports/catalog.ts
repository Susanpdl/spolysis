import { basketball } from "./basketball";
import { soccer } from "./soccer";
import { tableTennis } from "./tableTennis";
import { tennis } from "./tennis";
import type { SportDefinition, SportId } from "./types";

export type { SportId } from "./types";
export type { TennisStrokeType as StrokeType } from "./tennis";

export const SPORTS: readonly SportDefinition[] = [
  tennis,
  tableTennis,
  soccer,
  basketball,
];

export function getSport(id: SportId): SportDefinition {
  const sport = SPORTS.find((option) => option.id === id);
  if (!sport) throw new Error(`Unknown sport: ${id}`);
  return sport;
}
