package com.oneclicktrip.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.MediaType;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Component
public class ApiRateLimitFilter extends OncePerRequestFilter {
    private static final long MINUTE = 60_000L;
    private static final long HOUR = 60 * MINUTE;

    private final Map<String, Window> windows = new ConcurrentHashMap<>();
    private final AtomicLong requests = new AtomicLong();
    private final Clock clock;

    public ApiRateLimitFilter() {
        this(Clock.systemUTC());
    }

    ApiRateLimitFilter(Clock clock) {
        this.clock = clock;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return policy(request) == null;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {
        Policy policy = policy(request);
        if (policy == null) {
            filterChain.doFilter(request, response);
            return;
        }

        long now = clock.millis();
        String key = policy.name() + ':' + identity(request);
        Window window = windows.compute(key, (ignored, current) -> {
            if (current == null || now >= current.startedAt() + policy.windowMillis()) {
                return new Window(now, 1);
            }
            return new Window(current.startedAt(), current.count() + 1);
        });

        if (requests.incrementAndGet() % 1_000 == 0) {
            windows.entrySet().removeIf(entry -> now >= entry.getValue().startedAt() + HOUR);
        }

        if (window.count() > policy.limit()) {
            long retryAfterSeconds = Math.max(
                    1,
                    (window.startedAt() + policy.windowMillis() - now + 999) / 1_000
            );
            response.setStatus(429);
            response.setHeader("Retry-After", Long.toString(retryAfterSeconds));
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write(
                    "{\"success\":false,\"message\":\"请求过于频繁，请稍后再试\",\"data\":null}"
            );
            return;
        }

        filterChain.doFilter(request, response);
    }

    private Policy policy(HttpServletRequest request) {
        if (!"POST".equalsIgnoreCase(request.getMethod())) {
            return null;
        }
        return switch (request.getRequestURI()) {
            case "/api/auth/login" -> new Policy("login", 10, MINUTE);
            case "/api/auth/register" -> new Policy("register", 5, HOUR);
            case "/api/ai/chat/async", "/api/ai/resume", "/api/trip-plans/generate" ->
                    new Policy("ai", 10, MINUTE);
            default -> null;
        };
    }

    private String identity(HttpServletRequest request) {
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication != null && authentication.isAuthenticated()
                && !"anonymousUser".equals(authentication.getPrincipal())) {
            return "user:" + authentication.getName();
        }
        return "ip:" + clientIp(request);
    }

    private String clientIp(HttpServletRequest request) {
        String remote = request.getRemoteAddr();
        if ("127.0.0.1".equals(remote) || "::1".equals(remote)) {
            String forwarded = request.getHeader("X-Real-IP");
            if (forwarded != null && !forwarded.isBlank()) {
                return forwarded.trim();
            }
        }
        return remote;
    }

    private record Policy(String name, int limit, long windowMillis) {
    }

    private record Window(long startedAt, int count) {
    }
}
