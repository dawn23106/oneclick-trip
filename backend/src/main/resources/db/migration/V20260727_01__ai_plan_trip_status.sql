ALTER TABLE ai_travel_plan_versions
  ADD COLUMN trip_status VARCHAR(32) NOT NULL DEFAULT 'PLANNING' AFTER is_current;
