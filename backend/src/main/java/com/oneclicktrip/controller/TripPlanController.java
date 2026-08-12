package com.oneclicktrip.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.dto.AiTripPlanDetailResponse;
import com.oneclicktrip.dto.AiChatRequest;
import com.oneclicktrip.dto.GenerateTripPlanRequest;
import com.oneclicktrip.dto.TripPlanResponse;
import com.oneclicktrip.dto.TripPlanSummaryResponse;
import com.oneclicktrip.dto.UpdateTripStatusRequest;
import com.oneclicktrip.security.JwtUser;
import com.oneclicktrip.service.TripPlanService;
import com.oneclicktrip.service.AiAssistantService;
import com.oneclicktrip.service.CatalogService;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/trip-plans")
public class TripPlanController {
    private final TripPlanService tripPlanService;
    private final AiAssistantService aiAssistantService;
    private final CatalogService catalogService;

    public TripPlanController(
            TripPlanService tripPlanService,
            AiAssistantService aiAssistantService,
            CatalogService catalogService
    ) {
        this.tripPlanService = tripPlanService;
        this.aiAssistantService = aiAssistantService;
        this.catalogService = catalogService;
    }

    @PostMapping("/generate")
    public ApiResponse<JsonNode> generate(
            @Valid @RequestBody GenerateTripPlanRequest request,
            @AuthenticationPrincipal JwtUser currentUser
    ) {
        // 表单字段是确定性的输入契约；规划本身统一交给 LangGraph，而不是在 Java 中轮换景点。
        // Java 仍负责 JWT 身份、Bean Validation 和响应边界，Agent 负责研究、生成、评审与修订。
        String destination = catalogService.getCity(request.cityId()).getName();
        String message = buildPlanningMessage(request, destination);
        AiChatRequest aiRequest = new AiChatRequest(null, null, message, false);
        return ApiResponse.ok("AI 行程规划任务已创建", aiAssistantService.startChat(aiRequest, currentUser.userId()));
    }

    private String buildPlanningMessage(GenerateTripPlanRequest request, String destination) {
        String interests = request.interests() == null || request.interests().isEmpty()
                ? "无特别偏好"
                : String.join("、", request.interests());
        return "请为我生成一份完整且可校验的旅行计划。"
                + "出发地：" + textOr(request.departureCity(), "待确认") + "；"
                + "目的地：" + destination + "；"
                + "出发日期：" + (request.startDate() == null ? "待确认" : request.startDate()) + "；"
                + "天数：" + (request.days() == null ? 3 : request.days()) + "天；"
                + "人数：" + (request.peopleCount() == null ? 1 : request.peopleCount()) + "人；"
                + "预算档位：" + textOr(request.budgetLevel(), "MEDIUM") + "；"
                + "旅行节奏：" + textOr(request.pace(), "RELAXED") + "；"
                + "住宿偏好：" + textOr(request.hotelPreference(), "无特别要求") + "；"
                + "兴趣偏好：" + interests + "。"
                + "请结合长期偏好、旅游知识、天气和路线工具生成逐日安排，并完成预算、时间冲突、开放时间和路线合理性校验。";
    }

    private String textOr(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    @GetMapping
    public ApiResponse<List<TripPlanSummaryResponse>> list(@AuthenticationPrincipal JwtUser currentUser) {
        return ApiResponse.ok(tripPlanService.listUserPlans(currentUser.userId()));
    }

    @GetMapping("/{id}")
    public ApiResponse<TripPlanResponse> detail(
            @PathVariable Long id,
            @AuthenticationPrincipal JwtUser currentUser
    ) {
        return ApiResponse.ok(tripPlanService.getUserRulePlan(currentUser.userId(), id));
    }

    @GetMapping("/ai/{recordId}")
    public ApiResponse<AiTripPlanDetailResponse> aiDetail(
            @PathVariable Long recordId,
            @AuthenticationPrincipal JwtUser currentUser
    ) {
        return ApiResponse.ok(tripPlanService.getUserAiPlan(currentUser.userId(), recordId));
    }

    @PutMapping("/ai/{recordId}/status")
    public ApiResponse<AiTripPlanDetailResponse> updateAiStatus(
            @PathVariable Long recordId,
            @Valid @RequestBody UpdateTripStatusRequest request,
            @AuthenticationPrincipal JwtUser currentUser
    ) {
        return ApiResponse.ok(tripPlanService.updateAiStatus(currentUser.userId(), recordId, request));
    }

    @PutMapping("/{id}/status")
    public ApiResponse<TripPlanResponse> updateStatus(
            @PathVariable Long id,
            @Valid @RequestBody UpdateTripStatusRequest request,
            @AuthenticationPrincipal JwtUser currentUser
    ) {
        return ApiResponse.ok(tripPlanService.updateStatus(currentUser.userId(), id, request));
    }
}
