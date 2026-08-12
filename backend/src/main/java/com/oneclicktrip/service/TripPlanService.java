package com.oneclicktrip.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.dto.AiTripPlanDetailResponse;
import com.oneclicktrip.dto.TripPlanDayResponse;
import com.oneclicktrip.dto.TripPlanItemResponse;
import com.oneclicktrip.dto.TripPlanResponse;
import com.oneclicktrip.dto.TripPlanSummaryResponse;
import com.oneclicktrip.dto.UpdateTripStatusRequest;
import com.oneclicktrip.entity.*;
import com.oneclicktrip.mapper.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class TripPlanService {
    private static final Logger log = LoggerFactory.getLogger(TripPlanService.class);

    private final CatalogService catalogService;
    private final TripPlanMapper tripPlanMapper;
    private final TripPlanDayMapper tripPlanDayMapper;
    private final TripPlanItemMapper tripPlanItemMapper;
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public TripPlanService(
            CatalogService catalogService,
            TripPlanMapper tripPlanMapper,
            TripPlanDayMapper tripPlanDayMapper,
            TripPlanItemMapper tripPlanItemMapper,
            JdbcTemplate jdbcTemplate,
            ObjectMapper objectMapper
    ) {
        this.catalogService = catalogService;
        this.tripPlanMapper = tripPlanMapper;
        this.tripPlanDayMapper = tripPlanDayMapper;
        this.tripPlanItemMapper = tripPlanItemMapper;
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    public List<TripPlanSummaryResponse> listUserPlans(Long userId) {
        // 将传统行程和当前 AI 行程合并为用户端统一列表。
        List<TripPlanSummaryResponse> summaries = new ArrayList<>();

        List<TripPlan> rulePlans = tripPlanMapper.selectList(Wrappers.<TripPlan>lambdaQuery()
                .eq(TripPlan::getUserId, userId)
                .orderByDesc(TripPlan::getUpdateTime));
        for (TripPlan rulePlan : rulePlans) {
            City city = catalogService.getCity(rulePlan.getCityId());
            summaries.add(new TripPlanSummaryResponse(
                    "RULE-" + rulePlan.getId(),
                    "RULE",
                    rulePlan.getId(),
                    String.valueOf(rulePlan.getId()),
                    null,
                    1,
                    city.getName(),
                    rulePlan.getTitle(),
                    rulePlan.getDays(),
                    rulePlan.getPeopleCount(),
                    rulePlan.getStartDate(),
                    rulePlan.getTotalBudget(),
                    "CNY",
                    rulePlan.getSourceType(),
                    rulePlan.getSummary(),
                    defaultText(rulePlan.getTripStatus(), "PLANNING"),
                    rulePlan.getCreateTime()
            ));
        }

        try {
            summaries.addAll(jdbcTemplate.query("""
                            SELECT id, conversation_id, plan_id, plan_version, destination,
                                   plan_json, trip_status, created_at
                            FROM ai_travel_plan_versions
                            WHERE user_id = ? AND is_current = 1 AND deleted = 0
                            ORDER BY created_at DESC
                            """,
                    (resultSet, rowNum) -> toAiSummary(
                            resultSet.getLong("id"),
                            resultSet.getString("conversation_id"),
                            resultSet.getString("plan_id"),
                            resultSet.getInt("plan_version"),
                            resultSet.getString("destination"),
                            resultSet.getString("plan_json"),
                            resultSet.getString("trip_status"),
                            resultSet.getTimestamp("created_at")
                    ),
                    String.valueOf(userId)));
        } catch (DataAccessException exception) {
            // The Java application can still run before the AI service creates its tables.
            log.warn("AI plan table is unavailable; returning rule plans only", exception);
        }

        summaries.sort(Comparator.comparing(
                TripPlanSummaryResponse::createTime,
                Comparator.nullsLast(Comparator.reverseOrder())
        ));
        return summaries;
    }

    public TripPlanResponse getUserRulePlan(Long userId, Long id) {
        // 传统行程必须同时匹配记录 ID 和当前用户。
        TripPlan plan = tripPlanMapper.selectById(id);
        if (plan == null || !userId.equals(plan.getUserId())) {
            throw new BusinessException("行程不存在或无权查看");
        }
        return getPlan(id);
    }

    public AiTripPlanDetailResponse getUserAiPlan(Long userId, Long recordId) {
        // AI 行程只允许读取当前版本且未被后台软删除的记录。
        List<AiTripPlanDetailResponse> plans;
        try {
            plans = jdbcTemplate.query("""
                            SELECT id, conversation_id, plan_id, plan_version, trip_status, plan_json
                            FROM ai_travel_plan_versions
                            WHERE id = ? AND user_id = ? AND is_current = 1 AND deleted = 0
                            """,
                    (resultSet, rowNum) -> {
                        JsonNode root = readPlanJson(resultSet.getString("plan_json"));
                        return new AiTripPlanDetailResponse(
                                resultSet.getLong("id"),
                                resultSet.getString("conversation_id"),
                                resultSet.getString("plan_id"),
                                resultSet.getInt("plan_version"),
                                defaultText(resultSet.getString("trip_status"), "PLANNING"),
                                root.path("plan"),
                                root.path("entities"),
                                root.path("selected_options")
                        );
                    },
                    recordId,
                    String.valueOf(userId));
        } catch (DataAccessException exception) {
            throw new BusinessException("AI 行程暂时无法读取");
        }

        if (plans.isEmpty()) {
            throw new BusinessException("行程不存在或无权查看");
        }
        return plans.get(0);
    }

    public AiTripPlanDetailResponse updateAiStatus(
            Long userId,
            Long recordId,
            UpdateTripStatusRequest request
    ) {
        // 仅更新行程使用状态，不修改不可变的方案 JSON 内容。
        String newStatus = validatedStatus(request.tripStatus());
        int updated = jdbcTemplate.update("""
                UPDATE ai_travel_plan_versions
                SET trip_status = ?
                WHERE id = ? AND user_id = ? AND is_current = 1 AND deleted = 0
                """, newStatus, recordId, String.valueOf(userId));
        if (updated == 0) {
            throw new BusinessException("行程不存在或无权修改");
        }
        return getUserAiPlan(userId, recordId);
    }

    public TripPlanResponse updateStatus(Long userId, Long id, UpdateTripStatusRequest request) {
        // 传统行程状态变更同样受记录归属校验保护。
        TripPlan plan = tripPlanMapper.selectById(id);
        if (plan == null || !userId.equals(plan.getUserId())) {
            throw new BusinessException("行程不存在或无权修改");
        }
        String newStatus = validatedStatus(request.tripStatus());
        plan.setTripStatus(newStatus);
        tripPlanMapper.updateById(plan);
        return getPlan(id);
    }

    public TripPlanResponse getPlan(Long id) {
        // 查询行程详情时，需要把主表、每天、每天的项目组装成前端容易展示的嵌套结构。
        TripPlan plan = tripPlanMapper.selectById(id);
        if (plan == null) {
            throw new BusinessException("行程不存在");
        }
        City city = catalogService.getCity(plan.getCityId());
        List<TripPlanDay> days = tripPlanDayMapper.selectList(Wrappers.<TripPlanDay>lambdaQuery()
                .eq(TripPlanDay::getPlanId, id)
                .orderByAsc(TripPlanDay::getDayNo));

        // 一次查出该行程所有天的项目，避免在下面的 days 循环中重复访问数据库。
        // 原实现：查询 1 次行程 + 1 次天数 + N 次项目（N 是天数），即 N+1 查询问题。
        List<TripPlanItem> allItems = days.isEmpty()
                ? List.of()
                : tripPlanItemMapper.selectList(Wrappers.<TripPlanItem>lambdaQuery()
                .in(TripPlanItem::getPlanDayId, days.stream().map(TripPlanDay::getId).toList())
                .orderByAsc(TripPlanItem::getSortOrder));

        // 按 planDayId 分组。后面组装第 N 天时，直接从内存中拿到该天的项目。
        Map<Long, List<TripPlanItem>> itemsByDayId = allItems.stream()
                .collect(Collectors.groupingBy(TripPlanItem::getPlanDayId));

        List<TripPlanDayResponse> dayResponses = days.stream()
                .map(day -> new TripPlanDayResponse(
                        day.getId(),
                        day.getDayNo(),
                        day.getTitle(),
                        day.getSummary(),
                        // 不再发 SQL；没有项目时返回空列表，避免空指针异常。
                        itemsByDayId.getOrDefault(day.getId(), List.of())
                                .stream()
                                .map(this::toItemResponse)
                                .collect(Collectors.toList())
                ))
                .collect(Collectors.toList());

        return new TripPlanResponse(
                plan.getId(),
                plan.getCityId(),
                city.getName(),
                plan.getDepartureCity(),
                plan.getTitle(),
                plan.getDays(),
                plan.getPeopleCount(),
                plan.getStartDate(),
                plan.getBudgetLevel(),
                plan.getPace(),
                plan.getInterests(),
                plan.getTotalBudget(),
                plan.getSummary(),
                plan.getSourceType(),
                defaultText(plan.getTripStatus(), "PLANNING"),
                dayResponses
        );
    }

    private TripPlanSummaryResponse toAiSummary(
            Long recordId,
            String conversationId,
            String planId,
            Integer version,
            String destination,
            String planJson,
            String tripStatus,
            Timestamp createdAt
    ) {
        JsonNode root = readPlanJson(planJson);
        JsonNode planNode = root.path("plan");
        JsonNode entitiesNode = root.path("entities");
        int days = planNode.path("days").isArray() ? planNode.path("days").size() : entitiesNode.path("days").asInt(0);
        int people = entitiesNode.path("people").asInt(1);
        BigDecimal totalBudget = parseMoney(planNode.path("total_cost").asText("0"));
        LocalDate startDate = parseDate(entitiesNode.path("start_date").asText(null));
        String title = destination + (days > 0 ? days + "天" : "") + "智能行程";
        String summary = firstText(planNode.path("assumptions"), "由 AI 多阶段规划生成，可回到原会话继续修改。");

        return new TripPlanSummaryResponse(
                "AI-" + recordId,
                "AI",
                recordId,
                planId,
                conversationId,
                version,
                destination,
                title,
                days,
                people,
                startDate,
                totalBudget,
                planNode.path("currency").asText("CNY"),
                "AI",
                summary,
                defaultText(tripStatus, "PLANNING"),
                createdAt == null ? null : createdAt.toLocalDateTime()
        );
    }

    private String validatedStatus(String value) {
        if (!"COMPLETED".equals(value) && !"PLANNING".equals(value)) {
            throw new BusinessException("仅支持切换为 COMPLETED 或 PLANNING");
        }
        return value;
    }

    private JsonNode readPlanJson(String planJson) {
        try {
            return objectMapper.readTree(planJson);
        } catch (JsonProcessingException exception) {
            throw new BusinessException("行程数据格式异常");
        }
    }

    private BigDecimal parseMoney(String value) {
        try {
            return new BigDecimal(value == null || value.isBlank() ? "0" : value);
        } catch (NumberFormatException exception) {
            return BigDecimal.ZERO;
        }
    }

    private LocalDate parseDate(String value) {
        try {
            return value == null || value.isBlank() || "null".equals(value) ? null : LocalDate.parse(value);
        } catch (RuntimeException exception) {
            return null;
        }
    }

    private String firstText(JsonNode values, String fallback) {
        if (values.isArray() && !values.isEmpty()) {
            String value = values.get(0).asText("");
            if (!value.isBlank()) {
                return value;
            }
        }
        return fallback;
    }

    private TripPlanItemResponse toItemResponse(TripPlanItem item) {
        return new TripPlanItemResponse(
                item.getId(),
                item.getItemType(),
                item.getTitle(),
                item.getDescription(),
                item.getAddress(),
                item.getStartTime(),
                item.getEndTime(),
                item.getCost(),
                item.getSortOrder()
        );
    }

    private String defaultText(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

}
