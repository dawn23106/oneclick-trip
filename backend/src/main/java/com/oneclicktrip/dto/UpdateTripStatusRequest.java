package com.oneclicktrip.dto;

import jakarta.validation.constraints.NotBlank;

public record UpdateTripStatusRequest(
        @NotBlank String tripStatus
) {
}
