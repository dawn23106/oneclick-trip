package com.oneclicktrip.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.List;

@Service
public class DatabaseMonitorService {

    private static final long PICOSECONDS_PER_MILLISECOND = 1_000_000_000L;
    private final JdbcTemplate jdbcTemplate;
    private final long slowThresholdMs;

    public DatabaseMonitorService(
            JdbcTemplate jdbcTemplate,
            @Value("${app.database-monitor.slow-threshold-ms:1000}") long slowThresholdMs
    ) {
        this.jdbcTemplate = jdbcTemplate;
        this.slowThresholdMs = Math.max(100, Math.min(slowThresholdMs, 60_000));
    }

    public Snapshot snapshot(int requestedLimit, String requestedOrder) {
        int limit = Math.max(5, Math.min(requestedLimit, 100));
        String orderColumn = switch (requestedOrder == null ? "total" : requestedOrder) {
            case "average" -> "AVG_TIMER_WAIT";
            case "maximum" -> "MAX_TIMER_WAIT";
            case "rows" -> "SUM_ROWS_EXAMINED";
            default -> "SUM_TIMER_WAIT";
        };
        try {
            Summary summary = jdbcTemplate.queryForObject("""
                    SELECT COALESCE(SUM(COUNT_STAR), 0) total_executions,
                           COALESCE(SUM(SUM_TIMER_WAIT), 0) total_time,
                           COALESCE(SUM(SUM_NO_INDEX_USED), 0) no_index_executions,
                           COALESCE(SUM(SUM_CREATED_TMP_DISK_TABLES), 0) disk_temp_tables,
                           COALESCE(SUM(CASE WHEN MAX_TIMER_WAIT >= ? THEN 1 ELSE 0 END), 0) risky_digests
                      FROM performance_schema.events_statements_summary_by_digest
                     WHERE SCHEMA_NAME = DATABASE()
                    """, (rs, rowNum) -> new Summary(
                    rs.getLong("total_executions"),
                    millis(rs.getLong("total_time")),
                    rs.getLong("no_index_executions"),
                    rs.getLong("disk_temp_tables"),
                    rs.getLong("risky_digests")
            ), slowThresholdMs * PICOSECONDS_PER_MILLISECOND);

            List<QueryMetric> queries = jdbcTemplate.query("""
                    SELECT DIGEST, DIGEST_TEXT, COUNT_STAR, SUM_TIMER_WAIT,
                           AVG_TIMER_WAIT, MAX_TIMER_WAIT, SUM_LOCK_TIME,
                           SUM_ROWS_SENT, SUM_ROWS_EXAMINED, SUM_NO_INDEX_USED,
                           SUM_CREATED_TMP_DISK_TABLES, FIRST_SEEN, LAST_SEEN
                      FROM performance_schema.events_statements_summary_by_digest
                     WHERE SCHEMA_NAME = DATABASE() AND DIGEST_TEXT IS NOT NULL
                     ORDER BY %s DESC
                     LIMIT ?
                    """.formatted(orderColumn), (rs, rowNum) -> new QueryMetric(
                    rs.getString("DIGEST"),
                    rs.getString("DIGEST_TEXT"),
                    rs.getLong("COUNT_STAR"),
                    millis(rs.getLong("SUM_TIMER_WAIT")),
                    millis(rs.getLong("AVG_TIMER_WAIT")),
                    millis(rs.getLong("MAX_TIMER_WAIT")),
                    millis(rs.getLong("SUM_LOCK_TIME")),
                    rs.getLong("SUM_ROWS_SENT"),
                    rs.getLong("SUM_ROWS_EXAMINED"),
                    rs.getLong("SUM_NO_INDEX_USED"),
                    rs.getLong("SUM_CREATED_TMP_DISK_TABLES"),
                    localDateTime(rs.getTimestamp("FIRST_SEEN")),
                    localDateTime(rs.getTimestamp("LAST_SEEN")),
                    rs.getLong("MAX_TIMER_WAIT") >= slowThresholdMs * PICOSECONDS_PER_MILLISECOND
            ), limit);
            return new Snapshot(true, slowThresholdMs, summary, queries, null);
        } catch (DataAccessException exception) {
            return new Snapshot(
                    false,
                    slowThresholdMs,
                    new Summary(0, 0, 0, 0, 0),
                    List.of(),
                    "数据库性能统计暂不可读，请检查 performance_schema 最小读取权限"
            );
        }
    }

    private static double millis(long picoseconds) {
        return Math.round(picoseconds / 10_000_000.0) / 100.0;
    }

    private static LocalDateTime localDateTime(Timestamp value) {
        return value == null ? null : value.toLocalDateTime();
    }

    public record Snapshot(
            boolean available,
            long slowThresholdMs,
            Summary summary,
            List<QueryMetric> queries,
            String message
    ) {}

    public record Summary(
            long totalExecutions,
            double totalTimeMs,
            long noIndexExecutions,
            long diskTempTables,
            long riskyDigestCount
    ) {}

    public record QueryMetric(
            String digest,
            String sqlTemplate,
            long executions,
            double totalTimeMs,
            double averageTimeMs,
            double maximumTimeMs,
            double lockTimeMs,
            long rowsSent,
            long rowsExamined,
            long noIndexExecutions,
            long diskTempTables,
            LocalDateTime firstSeen,
            LocalDateTime lastSeen,
            boolean slow
    ) {}
}
