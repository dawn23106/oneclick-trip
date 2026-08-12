package com.oneclicktrip.dto;

import java.time.LocalDateTime;
import java.util.List;

public record BookingDraftSummaryResponse(
        String draftId,
        String status,
        String conversationId,
        String planId,
        Integer planVersion,
        String destination,
        List<String> bookingTypes,
        List<String> selectedOptionIds,
        LocalDateTime createdAt,
        LocalDateTime expiresAt
) {
}
