package com.oneclicktrip.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.assertj.core.api.Assertions.assertThat;

class ApiRateLimitFilterTest {
    private final ApiRateLimitFilter filter = new ApiRateLimitFilter(
            Clock.fixed(Instant.parse("2026-08-09T04:00:00Z"), ZoneOffset.UTC)
    );

    @Test
    void limitsLoginAttemptsPerClient() throws Exception {
        for (int index = 0; index < 10; index++) {
            MockHttpServletResponse response = invoke("/api/auth/login", "203.0.113.8");
            assertThat(response.getStatus()).isEqualTo(200);
        }

        MockHttpServletResponse limited = invoke("/api/auth/login", "203.0.113.8");

        assertThat(limited.getStatus()).isEqualTo(429);
        assertThat(limited.getHeader("Retry-After")).isEqualTo("60");
        assertThat(limited.getContentAsString()).contains("请求过于频繁");
    }

    @Test
    void keepsDifferentClientsInDifferentBuckets() throws Exception {
        for (int index = 0; index < 10; index++) {
            invoke("/api/auth/login", "203.0.113.8");
        }

        assertThat(invoke("/api/auth/login", "203.0.113.9").getStatus()).isEqualTo(200);
    }

    @Test
    void ignoresUnrestrictedEndpoints() throws Exception {
        for (int index = 0; index < 20; index++) {
            assertThat(invoke("/api/health", "203.0.113.8").getStatus()).isEqualTo(200);
        }
    }

    private MockHttpServletResponse invoke(String uri, String remoteAddress) throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("POST", uri);
        request.setRemoteAddr(remoteAddress);
        MockHttpServletResponse response = new MockHttpServletResponse();
        filter.doFilter(request, response, new MockFilterChain());
        return response;
    }
}
