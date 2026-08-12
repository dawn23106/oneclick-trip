package com.oneclicktrip.controller;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.dto.BookingDraftResponse;
import com.oneclicktrip.dto.BookingDraftSummaryResponse;
import com.oneclicktrip.dto.UserBookingDraftCreateRequest;
import com.oneclicktrip.security.JwtUser;
import com.oneclicktrip.service.BookingDraftService;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/bookings")
public class BookingController {
    private final BookingDraftService bookingDraftService;

    public BookingController(BookingDraftService bookingDraftService) {
        this.bookingDraftService = bookingDraftService;
    }

    @GetMapping
    public ApiResponse<List<BookingDraftSummaryResponse>> list(
            @AuthenticationPrincipal JwtUser user,
            @RequestParam(required = false) String status
    ) {
        return ApiResponse.ok(bookingDraftService.listForUser(user.userId(), status));
    }

    @PostMapping
    public ApiResponse<BookingDraftResponse> create(
            @AuthenticationPrincipal JwtUser user,
            @Valid @RequestBody UserBookingDraftCreateRequest request
    ) {
        return ApiResponse.ok("预订草稿已创建", bookingDraftService.createForUser(user.userId(), request));
    }

    @GetMapping("/{draftId}")
    public ApiResponse<BookingDraftResponse> detail(
            @AuthenticationPrincipal JwtUser user,
            @PathVariable String draftId
    ) {
        return ApiResponse.ok(bookingDraftService.get(draftId, String.valueOf(user.userId())));
    }

    @PostMapping("/{draftId}/confirm")
    public ApiResponse<BookingDraftResponse> confirm(
            @AuthenticationPrincipal JwtUser user,
            @PathVariable String draftId
    ) {
        return ApiResponse.ok("预订草稿已确认", bookingDraftService.confirmForUser(draftId, user.userId()));
    }

    @PostMapping("/{draftId}/cancel")
    public ApiResponse<BookingDraftResponse> cancel(
            @AuthenticationPrincipal JwtUser user,
            @PathVariable String draftId
    ) {
        return ApiResponse.ok("预订草稿已取消", bookingDraftService.cancelForUser(draftId, user.userId()));
    }
}
