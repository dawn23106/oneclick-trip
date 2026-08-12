package com.oneclicktrip.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.List;

public record UserBookingDraftCreateRequest(
        @NotBlank String conversationId,
        @NotBlank String planId,
        @NotNull @Positive Integer planVersion,
        @NotEmpty List<String> bookingTypes,
        @NotEmpty List<String> selectedOptionIds
) {
}
