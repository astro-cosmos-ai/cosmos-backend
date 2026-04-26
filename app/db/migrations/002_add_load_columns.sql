ALTER TABLE charts ADD COLUMN IF NOT EXISTS varshaphal_raw jsonb;
ALTER TABLE charts ADD COLUMN IF NOT EXISTS transit_snapshot jsonb;
