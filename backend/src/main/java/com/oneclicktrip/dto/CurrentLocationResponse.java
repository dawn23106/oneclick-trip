package com.oneclicktrip.dto;

public record CurrentLocationResponse(
        String city,
        String district,
        String province,
        String displayName,
        double latitude,
        double longitude,
        String source
) {
}
