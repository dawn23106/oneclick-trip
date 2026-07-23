package com.oneclicktrip.controller.admin;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.service.AdminBookingService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/admin/bookings")
public class AdminBookingController {
    private final AdminBookingService bookingService;

    public AdminBookingController(AdminBookingService bookingService) {
        this.bookingService = bookingService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) Long userId,
            @RequestParam(required = false) String keyword,
            @RequestParam(required = false) String status
    ) {
        int safePage = Math.max(page, 1);
        int safeSize = Math.max(1, Math.min(size, 100));
        return ApiResponse.ok(bookingService.list(safePage, safeSize, userId, keyword, status));
    }

    @GetMapping("/stats")
    public ApiResponse<Map<String, Object>> stats() {
        return ApiResponse.ok(bookingService.stats());
    }

    @GetMapping("/{draftId}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable String draftId) {
        return ApiResponse.ok(bookingService.detail(draftId));
    }
}
