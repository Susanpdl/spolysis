-- Optional primary-phase label so coaching, cues, and the IK window stay aligned.
-- Existing results remain readable when this column is null.
ALTER TABLE results ADD COLUMN IF NOT EXISTS fault_phase TEXT;
