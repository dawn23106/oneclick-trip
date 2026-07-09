package com.oneclicktrip.controller;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.dto.GenerateTripPlanRequest;
import com.oneclicktrip.dto.TripPlanResponse;
import com.oneclicktrip.service.TripPlanService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/trip-plans")
public class TripPlanController {
    private final TripPlanService tripPlanService;

    public TripPlanController(TripPlanService tripPlanService) {
        this.tripPlanService = tripPlanService;
    }

    @PostMapping("/generate")
    public ApiResponse<TripPlanResponse> generate(@Valid @RequestBody GenerateTripPlanRequest request) {
        // 当前是规则版生成：根据数据库里的景点、美食、酒店拼出基础行程。
        // 以后接入 AI 后，可以在 Service 内换成“规则初稿 + AI 优化”。
        return ApiResponse.ok("已生成规则版行程", tripPlanService.generate(request));
    }

    @GetMapping("/{id}")
    public ApiResponse<TripPlanResponse> detail(@PathVariable Long id) {
        return ApiResponse.ok(tripPlanService.getPlan(id));
    }
}
