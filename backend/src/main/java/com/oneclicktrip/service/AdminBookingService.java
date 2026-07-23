package com.oneclicktrip.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oneclicktrip.common.BusinessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

@Service
public class AdminBookingService {
    private static final Set<String> ALLOWED_STATUSES = Set.of(
            "PENDING_CONFIRMATION", "CONFIRMED", "CANCELLED", "EXPIRED"
    );

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public AdminBookingService(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public Map<String, Object> list(
            int page,
            int size,
            Long userId,
            String keyword,
            String rawStatus
    ) {
        expirePendingDrafts();
        String status = normalizeStatus(rawStatus);
        StringBuilder where = new StringBuilder(" WHERE 1 = 1");
        List<Object> parameters = new ArrayList<>();
        if (userId != null) {
            where.append(" AND d.user_id = ?");
            parameters.add(String.valueOf(userId));
        }
        if (status != null) {
            where.append(" AND d.status = ?");
            parameters.add(status);
        }
        if (keyword != null && !keyword.isBlank()) {
            String like = "%" + keyword.trim() + "%";
            where.append("""
                     AND (d.draft_id LIKE ? OR d.conversation_id LIKE ? OR d.plan_id LIKE ?
                          OR u.username LIKE ? OR u.nickname LIKE ? OR p.destination LIKE ?)
                    """);
            for (int index = 0; index < 6; index++) {
                parameters.add(like);
            }
        }

        String joins = """
                 FROM ai_booking_draft d
                 LEFT JOIN sys_user u ON CAST(u.id AS CHAR) = d.user_id
                 LEFT JOIN ai_travel_plan_versions p
                   ON p.user_id = d.user_id
                  AND p.conversation_id = d.conversation_id
                  AND p.plan_id = d.plan_id
                  AND p.plan_version = d.plan_version
                """;
        Long total = jdbcTemplate.queryForObject(
                "SELECT COUNT(*)" + joins + where,
                Long.class,
                parameters.toArray()
        );

        List<Object> pageParameters = new ArrayList<>(parameters);
        pageParameters.add(size);
        pageParameters.add((page - 1) * size);
        List<Map<String, Object>> records = jdbcTemplate.query(
                """
                        SELECT d.draft_id, d.user_id, u.username, u.nickname, d.status,
                               d.conversation_id, d.plan_id, d.plan_version, p.destination,
                               d.booking_types_json, d.selected_option_ids_json,
                               d.expires_at, d.confirmed_at, d.create_time, d.update_time
                        """ + joins + where + " ORDER BY d.create_time DESC LIMIT ? OFFSET ?",
                (resultSet, rowNum) -> bookingMap(
                        resultSet.getString("draft_id"),
                        resultSet.getString("user_id"),
                        resultSet.getString("username"),
                        resultSet.getString("nickname"),
                        resultSet.getString("status"),
                        resultSet.getString("conversation_id"),
                        resultSet.getString("plan_id"),
                        resultSet.getInt("plan_version"),
                        resultSet.getString("destination"),
                        resultSet.getString("booking_types_json"),
                        resultSet.getString("selected_option_ids_json"),
                        toLocalDateTime(resultSet.getTimestamp("expires_at")),
                        toLocalDateTime(resultSet.getTimestamp("confirmed_at")),
                        toLocalDateTime(resultSet.getTimestamp("create_time")),
                        toLocalDateTime(resultSet.getTimestamp("update_time"))
                ),
                pageParameters.toArray()
        );

        long safeTotal = total == null ? 0L : total;
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("records", records);
        result.put("total", safeTotal);
        result.put("size", size);
        result.put("current", page);
        result.put("pages", safeTotal == 0 ? 0 : (safeTotal + size - 1) / size);
        return result;
    }

    @Transactional
    public Map<String, Object> stats() {
        expirePendingDrafts();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", countByStatus(null));
        result.put("pending", countByStatus("PENDING_CONFIRMATION"));
        result.put("confirmed", countByStatus("CONFIRMED"));
        result.put("cancelled", countByStatus("CANCELLED"));
        result.put("expired", countByStatus("EXPIRED"));
        return result;
    }

    @Transactional
    public Map<String, Object> detail(String draftId) {
        expirePendingDrafts();
        List<Map<String, Object>> rows = jdbcTemplate.query(
                """
                        SELECT d.draft_id, d.user_id, u.username, u.nickname, d.status,
                               d.conversation_id, d.plan_id, d.plan_version, p.destination,
                               d.booking_types_json, d.selected_option_ids_json,
                               d.expires_at, d.confirmed_at, d.create_time, d.update_time
                        FROM ai_booking_draft d
                        LEFT JOIN sys_user u ON CAST(u.id AS CHAR) = d.user_id
                        LEFT JOIN ai_travel_plan_versions p
                          ON p.user_id = d.user_id
                         AND p.conversation_id = d.conversation_id
                         AND p.plan_id = d.plan_id
                         AND p.plan_version = d.plan_version
                        WHERE d.draft_id = ?
                        """,
                (resultSet, rowNum) -> bookingMap(
                        resultSet.getString("draft_id"),
                        resultSet.getString("user_id"),
                        resultSet.getString("username"),
                        resultSet.getString("nickname"),
                        resultSet.getString("status"),
                        resultSet.getString("conversation_id"),
                        resultSet.getString("plan_id"),
                        resultSet.getInt("plan_version"),
                        resultSet.getString("destination"),
                        resultSet.getString("booking_types_json"),
                        resultSet.getString("selected_option_ids_json"),
                        toLocalDateTime(resultSet.getTimestamp("expires_at")),
                        toLocalDateTime(resultSet.getTimestamp("confirmed_at")),
                        toLocalDateTime(resultSet.getTimestamp("create_time")),
                        toLocalDateTime(resultSet.getTimestamp("update_time"))
                ),
                draftId
        );
        if (rows.isEmpty()) {
            throw new BusinessException("预订草稿不存在");
        }
        return rows.get(0);
    }

    private Map<String, Object> bookingMap(
            String draftId,
            String userId,
            String username,
            String nickname,
            String status,
            String conversationId,
            String planId,
            int planVersion,
            String destination,
            String bookingTypesJson,
            String selectedOptionIdsJson,
            LocalDateTime expiresAt,
            LocalDateTime confirmedAt,
            LocalDateTime createTime,
            LocalDateTime updateTime
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("draftId", draftId);
        row.put("userId", userId);
        row.put("username", username);
        row.put("nickname", nickname == null || nickname.isBlank() ? username : nickname);
        row.put("status", status.toLowerCase(Locale.ROOT));
        row.put("conversationId", conversationId);
        row.put("planId", planId);
        row.put("planVersion", planVersion);
        row.put("destination", destination);
        row.put("bookingTypes", readStringList(bookingTypesJson));
        row.put("selectedOptionIds", readStringList(selectedOptionIdsJson));
        row.put("expiresAt", expiresAt);
        row.put("confirmedAt", confirmedAt);
        row.put("createTime", createTime);
        row.put("updateTime", updateTime);
        return row;
    }

    private long countByStatus(String status) {
        Long count = status == null
                ? jdbcTemplate.queryForObject("SELECT COUNT(*) FROM ai_booking_draft", Long.class)
                : jdbcTemplate.queryForObject(
                        "SELECT COUNT(*) FROM ai_booking_draft WHERE status = ?",
                        Long.class,
                        status
                );
        return count == null ? 0L : count;
    }

    private void expirePendingDrafts() {
        LocalDateTime now = LocalDateTime.now();
        jdbcTemplate.update(
                """
                        UPDATE ai_booking_draft
                        SET status = 'EXPIRED', update_time = ?
                        WHERE status = 'PENDING_CONFIRMATION' AND expires_at < ?
                        """,
                Timestamp.valueOf(now),
                Timestamp.valueOf(now)
        );
    }

    private String normalizeStatus(String rawStatus) {
        if (rawStatus == null || rawStatus.isBlank()) {
            return null;
        }
        String status = rawStatus.trim().toUpperCase(Locale.ROOT);
        if (!ALLOWED_STATUSES.contains(status)) {
            throw new BusinessException("不支持的预订状态筛选");
        }
        return status;
    }

    private List<String> readStringList(String value) {
        try {
            return objectMapper.readValue(value, new TypeReference<>() { });
        } catch (JsonProcessingException exception) {
            throw new BusinessException("预订草稿 JSON 数据格式异常");
        }
    }

    private LocalDateTime toLocalDateTime(Timestamp value) {
        return value == null ? null : value.toLocalDateTime();
    }
}
