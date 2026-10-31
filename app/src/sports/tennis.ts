import type { SportDefinition } from "./types";

export const tennisStrokes = [
  { id: "forehand", label: "Forehand" },
  { id: "backhand", label: "Backhand" },
  { id: "serve", label: "Serve" },
  { id: "volley", label: "Volley" },
] as const;

export type TennisStrokeType = (typeof tennisStrokes)[number]["id"];

export const tennis: SportDefinition = {
  id: "tennis",
  name: "Tennis",
  icon: "🎾",
  description: "Review your strokes and compare your movement in 3D.",
  available: true,
  strokes: tennisStrokes,
};
