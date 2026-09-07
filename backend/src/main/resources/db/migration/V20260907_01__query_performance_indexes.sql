-- Composite indexes for the most frequent user lists and operations pages.
-- Every statement is idempotent because local development may also initialize
-- the current schema.sql before Flyway runs.

SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE trip_plan ADD KEY idx_plan_user_active_created (user_id, deleted, create_time)',
    'SELECT 1')
    FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'trip_plan'
     AND index_name = 'idx_plan_user_active_created'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE ai_conversation ADD KEY idx_ai_conversation_admin_update (deleted, update_time)',
    'SELECT 1')
    FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'ai_conversation'
     AND index_name = 'idx_ai_conversation_admin_update'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE ai_conversation ADD KEY idx_ai_conversation_status_update (status, deleted, update_time)',
    'SELECT 1')
    FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'ai_conversation'
     AND index_name = 'idx_ai_conversation_status_update'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @ddl = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE ai_agent_run_log ADD KEY idx_ai_agent_run_conversation_started (conversation_id, started_at, id)',
    'SELECT 1')
    FROM information_schema.statistics
   WHERE table_schema = DATABASE() AND table_name = 'ai_agent_run_log'
     AND index_name = 'idx_ai_agent_run_conversation_started'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
