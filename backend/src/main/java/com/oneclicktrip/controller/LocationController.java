package com.oneclicktrip.controller;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.dto.CurrentLocationResponse;
import com.oneclicktrip.service.LocationService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/location")
public class LocationController {
    private final LocationService locationService;

    public LocationController(LocationService locationService) {
        this.locationService = locationService;
    }

    @GetMapping("/reverse")
    public ApiResponse<CurrentLocationResponse> reverse(
            @RequestParam double latitude,
            @RequestParam double longitude
    ) {
        return ApiResponse.ok(locationService.reverseGeocode(latitude, longitude));
    }
}
