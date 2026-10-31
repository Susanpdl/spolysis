-- Optional per-displayed-joint phase map so secondary cues use that joint's peak.
-- Existing results remain readable when this column is null.
-- Apply 004_result_fault_phase.sql and this migration before production
-- completions write the new columns.
ALTER TABLE results ADD COLUMN IF NOT EXISTS fault_phases JSONB;
