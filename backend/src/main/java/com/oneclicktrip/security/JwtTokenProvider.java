package com.oneclicktrip.security;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oneclicktrip.entity.User;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.stereotype.Component;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

@Component
@EnableConfigurationProperties(JwtProperties.class)
public class JwtTokenProvider {
    private final JwtProperties properties;
    private final ObjectMapper objectMapper;

    public JwtTokenProvider(JwtProperties properties, ObjectMapper objectMapper) {
        this.properties = properties;
        this.objectMapper = objectMapper;
    }

    public String createToken(User user) {
        long now = Instant.now().getEpochSecond();
        Map<String, Object> header = Map.of("alg", "HS256", "typ", "JWT");

        // payload 是 token 中真正携带的用户信息。
        // 这里只放用户 id、用户名、角色和过期时间，不放密码。
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("sub", user.getId().toString());
        payload.put("username", user.getUsername());
        payload.put("role", user.getRole());
        payload.put("iat", now);
        payload.put("exp", now + properties.expirationMinutes() * 60);

        String headerPart = base64Url(toJson(header));
        String payloadPart = base64Url(toJson(payload));
        String signature = sign(headerPart + "." + payloadPart);
        return headerPart + "." + payloadPart + "." + signature;
    }

    public JwtUser parse(String token) {
        try {
            String[] parts = token.split("\\.");
            if (parts.length != 3) {
                return null;
            }
            String unsigned = parts[0] + "." + parts[1];
            // 重新计算签名，确认 token 没有被用户篡改。
            if (!sign(unsigned).equals(parts[2])) {
                return null;
            }
            byte[] payloadBytes = Base64.getUrlDecoder().decode(parts[1]);
            Map<String, Object> payload = objectMapper.readValue(payloadBytes, new TypeReference<>() {});
            long exp = ((Number) payload.get("exp")).longValue();
            // 过期 token 直接视为无效，前端需要重新登录。
            if (Instant.now().getEpochSecond() > exp) {
                return null;
            }
            Long userId = Long.valueOf(payload.get("sub").toString());
            String username = payload.get("username").toString();
            String role = payload.get("role").toString();
            return new JwtUser(userId, username, role);
        } catch (Exception ex) {
            return null;
        }
    }

    private byte[] toJson(Object object) {
        try {
            return objectMapper.writeValueAsBytes(object);
        } catch (Exception ex) {
            throw new IllegalStateException("JWT 序列化失败", ex);
        }
    }

    private String sign(String content) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(properties.secret().getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return base64Url(mac.doFinal(content.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new IllegalStateException("JWT 签名失败", ex);
        }
    }

    private String base64Url(byte[] bytes) {
        // JWT 使用 URL 安全的 Base64，并且通常去掉末尾的等号填充。
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
