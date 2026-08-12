ALTER TABLE ai_travel_plan_versions
  ADD COLUMN deleted TINYINT(1) NOT NULL DEFAULT 0 AFTER trip_status,
  ADD COLUMN deleted_at DATETIME NULL AFTER deleted,
  ADD COLUMN deleted_by BIGINT NULL AFTER deleted_at,
  ADD KEY idx_ai_plan_admin_deleted (deleted, created_at),
  ADD KEY idx_ai_plan_admin_destination (destination, deleted);
