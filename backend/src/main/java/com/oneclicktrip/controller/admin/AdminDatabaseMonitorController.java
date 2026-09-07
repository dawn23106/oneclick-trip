package com.oneclicktrip.controller.admin;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.service.DatabaseMonitorService;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api/admin/database-monitor")
public class AdminDatabaseMonitorController {

    private final DatabaseMonitorService monitorService;

    public AdminDatabaseMonitorController(DatabaseMonitorService monitorService) {
        this.monitorService = monitorService;
    }

    @GetMapping
    public ApiResponse<DatabaseMonitorService.Snapshot> snapshot(
            @RequestParam(defaultValue = "20") @Min(5) @Max(100) int limit,
            @RequestParam(defaultValue = "total") String order
    ) {
        return ApiResponse.ok(monitorService.snapshot(limit, order));
    }
}
