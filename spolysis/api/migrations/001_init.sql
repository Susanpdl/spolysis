-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  tier TEXT NOT NULL CHECK (tier IN ('free', 'premium')),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending', 'processing', 'completed', 'failed', 'rejected')
  ),
  video_r2_key TEXT NOT NULL,
  temporal_run_id TEXT,
  rejection_reason TEXT,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS jobs_user_id_idx ON jobs(user_id);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs(status);
CREATE INDEX IF NOT EXISTS jobs_created_at_idx ON jobs(created_at DESC);

-- Results table
CREATE TABLE IF NOT EXISTS results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE NOT NULL UNIQUE,
  stroke_type TEXT NOT NULL,
  fault_label TEXT,
  confidence FLOAT NOT NULL,
  recommendation TEXT NOT NULL,
  reference_clip_url TEXT,
  delta_data JSONB,
  overlay_video_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS results_job_id_idx ON results(job_id);

-- Auto-update updated_at on jobs
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_jobs_updated_at
  BEFORE UPDATE ON jobs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "users_own_jobs" ON jobs;
CREATE POLICY "users_own_jobs" ON jobs FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "users_own_results" ON results;
CREATE POLICY "users_own_results" ON results FOR ALL USING (
  job_id IN (SELECT id FROM jobs WHERE user_id = auth.uid())
);
