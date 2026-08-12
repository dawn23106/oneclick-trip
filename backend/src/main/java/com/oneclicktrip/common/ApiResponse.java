package com.oneclicktrip.common;

/**
 * 统一接口返回格式。
 *
 * 前端拿到的每个接口响应都会长这样：
 * {
 *   "success": true,
 *   "message": "ok",
 *   "data": ...
 * }
 */
public record ApiResponse<T>(boolean success, String message, T data) {
    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, "ok", data);
    }

    public static <T> ApiResponse<T> ok(String message, T data) {
        return new ApiResponse<>(true, message, data);
    }

    public static <T> ApiResponse<T> fail(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
