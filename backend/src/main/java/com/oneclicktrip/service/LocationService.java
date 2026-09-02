package com.oneclicktrip.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.common.LocationServiceException;
import com.oneclicktrip.dto.CurrentLocationResponse;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.List;

@Service
public class LocationService {
    private static final List<String> CITY_FIELDS = List.of(
            "city", "municipality", "town", "county"
    );

    private final RestClient nominatimRestClient;

    public LocationService(@Qualifier("nominatimRestClient") RestClient nominatimRestClient) {
        this.nominatimRestClient = nominatimRestClient;
    }

    /**
     * 浏览器只提供经纬度；城市识别由后端统一完成，原始坐标不会写入用户资料或会话。
     */
    public CurrentLocationResponse reverseGeocode(double latitude, double longitude) {
        validateCoordinates(latitude, longitude);
        final JsonNode payload;
        try {
            payload = nominatimRestClient.get()
                    .uri(uriBuilder -> uriBuilder
                            .path("/reverse")
                            .queryParam("lat", latitude)
                            .queryParam("lon", longitude)
                            .queryParam("format", "jsonv2")
                            .queryParam("accept-language", "zh-CN,zh")
                            .queryParam("addressdetails", 1)
                            .queryParam("zoom", 10)
                            .build())
                    .retrieve()
                    .body(JsonNode.class);
        } catch (RestClientException exception) {
            throw new LocationServiceException("定位服务暂时不可用，请手动填写出发城市", exception);
        }

        JsonNode address = payload == null ? null : payload.path("address");
        String displayName = payload == null ? "" : payload.path("display_name").asText("");
        String province = text(address, "state");
        String rawCity = firstText(address, CITY_FIELDS);
        String city = resolveCity(rawCity, province, displayName);
        if (city.isBlank()) {
            throw new BusinessException("暂时无法识别当前位置所属城市，请手动填写出发地");
        }

        String district = isDistrict(rawCity)
                ? rawCity
                : firstText(address, List.of("city_district", "district", "suburb", "county"));

        return new CurrentLocationResponse(
                normalizeCity(city),
                district,
                province,
                displayName,
                latitude,
                longitude,
                "nominatim-reverse"
        );
    }

    private static void validateCoordinates(double latitude, double longitude) {
        if (!Double.isFinite(latitude) || latitude < -90 || latitude > 90
                || !Double.isFinite(longitude) || longitude < -180 || longitude > 180) {
            throw new BusinessException("定位坐标不合法");
        }
    }

    private static String firstText(JsonNode node, List<String> fields) {
        if (node == null || node.isMissingNode()) {
            return "";
        }
        return fields.stream()
                .map(field -> text(node, field))
                .filter(value -> !value.isBlank())
                .findFirst()
                .orElse("");
    }

    private static String text(JsonNode node, String field) {
        return node == null || node.isMissingNode() ? "" : node.path(field).asText("").trim();
    }

    private static String normalizeCity(String city) {
        return city.endsWith("市") && city.length() > 1
                ? city.substring(0, city.length() - 1)
                : city;
    }

    private static String resolveCity(String rawCity, String province, String displayName) {
        if (province.endsWith("市")) {
            return province;
        }
        if (!rawCity.isBlank() && !isDistrict(rawCity)) {
            return rawCity;
        }
        for (String segment : displayName.split("[,，]")) {
            String candidate = segment.trim();
            if (candidate.endsWith("市")) {
                return candidate;
            }
        }
        return rawCity;
    }

    private static boolean isDistrict(String value) {
        return value.endsWith("区") || value.endsWith("县") || value.endsWith("旗");
    }
}
