-- Existing analyses stay readable; every newly created analysis uses the 3D path.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS stroke_type TEXT
  CHECK (stroke_type IN ('forehand', 'backhand', 'serve', 'volley'));
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS handedness TEXT NOT NULL DEFAULT 'right'
  CHECK (handedness IN ('right', 'left'));
ALTER TABLE jobs ALTER COLUMN tier SET DEFAULT 'premium';

-- Clients access analysis data through the authenticated API.
-- Prevent clients from forging results or changing job ownership through PostgREST.
DROP POLICY IF EXISTS "users_own_jobs" ON jobs;
DROP POLICY IF EXISTS "users_own_results" ON results;
CREATE POLICY "users_read_jobs" ON jobs FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "users_read_results" ON results FOR SELECT USING (
  job_id IN (SELECT id FROM jobs WHERE user_id = auth.uid())
);
