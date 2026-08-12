package com.oneclicktrip.controller.admin;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.security.JwtUser;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/ai-trip-plans")
public class AdminAiTripPlanController {
    private final JdbcTemplate jdbcTemplate;

    public AdminAiTripPlanController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String keyword,
            @RequestParam(defaultValue = "active") String deleted) {
        int safePage = Math.max(page, 1);
        int safeSize = Math.min(Math.max(size, 1), 100);
        String stateSql = switch (deleted) {
            case "deleted" -> "p.deleted = 1";
            case "all" -> "1 = 1";
            default -> "p.deleted = 0";
        };
        String normalizedKeyword = keyword == null ? "" : keyword.trim();
        String searchSql = normalizedKeyword.isEmpty()
                ? ""
                : " AND (p.destination LIKE ? OR p.plan_id LIKE ? OR p.conversation_id LIKE ? OR u.username LIKE ? OR u.nickname LIKE ?)";
        String fromSql = " FROM ai_travel_plan_versions p LEFT JOIN sys_user u ON u.id = CAST(p.user_id AS UNSIGNED) WHERE "
                + stateSql + searchSql;

        Object[] searchArgs = normalizedKeyword.isEmpty()
                ? new Object[0]
                : new Object[]{"%" + normalizedKeyword + "%", "%" + normalizedKeyword + "%",
                    "%" + normalizedKeyword + "%", "%" + normalizedKeyword + "%", "%" + normalizedKeyword + "%"};

        Long total = jdbcTemplate.queryForObject("SELECT COUNT(*)" + fromSql, Long.class, searchArgs);
        Object[] listArgs = new Object[searchArgs.length + 2];
        System.arraycopy(searchArgs, 0, listArgs, 0, searchArgs.length);
        listArgs[listArgs.length - 2] = safeSize;
        listArgs[listArgs.length - 1] = (safePage - 1) * safeSize;

        List<Map<String, Object>> records = jdbcTemplate.query(
                """
                SELECT p.id, p.user_id, p.conversation_id, p.plan_id, p.plan_version,
                       p.destination, p.trip_status, p.is_current, p.deleted, p.deleted_at,
                       p.deleted_by, p.created_at, u.username, u.nickname
                """ + fromSql + " ORDER BY p.created_at DESC, p.id DESC LIMIT ? OFFSET ?",
                (rs, rowNum) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("userId", rs.getString("user_id"));
                    row.put("nickname", rs.getString("nickname") != null ? rs.getString("nickname") : rs.getString("username"));
                    row.put("conversationId", rs.getString("conversation_id"));
                    row.put("planId", rs.getString("plan_id"));
                    row.put("planVersion", rs.getInt("plan_version"));
                    row.put("destination", rs.getString("destination"));
                    row.put("tripStatus", rs.getString("trip_status"));
                    row.put("current", rs.getBoolean("is_current"));
                    row.put("deleted", rs.getBoolean("deleted"));
                    row.put("deletedAt", rs.getTimestamp("deleted_at"));
                    row.put("deletedBy", rs.getObject("deleted_by"));
                    row.put("createdAt", rs.getTimestamp("created_at"));
                    return row;
                }, listArgs);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("records", records);
        result.put("total", total == null ? 0 : total);
        result.put("current", safePage);
        result.put("size", safeSize);
        return ApiResponse.ok(result);
    }

    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable Long id) {
        List<Map<String, Object>> rows = jdbcTemplate.query(
                """
                SELECT p.*, u.username, u.nickname
                FROM ai_travel_plan_versions p
                LEFT JOIN sys_user u ON u.id = CAST(p.user_id AS UNSIGNED)
                WHERE p.id = ?
                """,
                (rs, rowNum) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getLong("id"));
                    row.put("userId", rs.getString("user_id"));
                    row.put("nickname", rs.getString("nickname") != null ? rs.getString("nickname") : rs.getString("username"));
                    row.put("conversationId", rs.getString("conversation_id"));
                    row.put("planId", rs.getString("plan_id"));
                    row.put("planVersion", rs.getInt("plan_version"));
                    row.put("destination", rs.getString("destination"));
                    row.put("tripStatus", rs.getString("trip_status"));
                    row.put("current", rs.getBoolean("is_current"));
                    row.put("deleted", rs.getBoolean("deleted"));
                    row.put("deletedAt", rs.getTimestamp("deleted_at"));
                    row.put("deletedBy", rs.getObject("deleted_by"));
                    row.put("createdAt", rs.getTimestamp("created_at"));
                    row.put("planJson", rs.getString("plan_json"));
                    return row;
                }, id);
        if (rows.isEmpty()) {
            throw new BusinessException("AI 行程不存在");
        }
        return ApiResponse.ok(rows.get(0));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Void> delete(@PathVariable Long id, @AuthenticationPrincipal JwtUser admin) {
        int updated = jdbcTemplate.update(
                "UPDATE ai_travel_plan_versions SET deleted = 1, deleted_at = ?, deleted_by = ? WHERE id = ? AND deleted = 0",
                Timestamp.valueOf(LocalDateTime.now()), admin.userId(), id);
        if (updated == 0) {
            throw new BusinessException("AI 行程不存在或已删除");
        }
        return ApiResponse.ok(null);
    }

    @PostMapping("/{id}/restore")
    public ApiResponse<Void> restore(@PathVariable Long id) {
        int updated = jdbcTemplate.update(
                "UPDATE ai_travel_plan_versions SET deleted = 0, deleted_at = NULL, deleted_by = NULL WHERE id = ? AND deleted = 1",
                id);
        if (updated == 0) {
            throw new BusinessException("AI 行程不存在或未删除");
        }
        return ApiResponse.ok(null);
    }
}
