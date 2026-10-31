export type SportId = "tennis" | "table-tennis" | "soccer" | "basketball";

export interface SportDefinition {
  id: SportId;
  name: string;
  icon: string;
  description: string;
  available: boolean;
  strokes?: readonly { id: string; label: string }[];
}
