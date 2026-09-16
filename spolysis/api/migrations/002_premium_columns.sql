-- Add premium 3D result columns to the results table.
-- delta_data was the original placeholder name; delta_summary is the actual column
-- used by the premium pipeline. Rename it and add the two missing columns.

ALTER TABLE results RENAME COLUMN delta_data TO delta_summary;

ALTER TABLE results
  ADD COLUMN IF NOT EXISTS skeleton_3d_url TEXT,
  ADD COLUMN IF NOT EXISTS fault_joints JSONB;
