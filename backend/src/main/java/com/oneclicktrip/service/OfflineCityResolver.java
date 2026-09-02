package com.oneclicktrip.service;

import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/**
 * 国内地图服务不可达时的离线兜底。数据只保存地级行政中心，不保存用户坐标。
 */
@Component
public class OfflineCityResolver {
    private static final String DATASET = "geodata/cn-prefecture-cities.tsv";
    private static final double MAX_DISTANCE_KM = 350;
    private static final double EARTH_RADIUS_KM = 6371.0088;

    private final List<CityPoint> cities;

    public OfflineCityResolver() {
        this.cities = loadCities();
    }

    Optional<ResolvedCity> findNearest(double latitude, double longitude) {
        // 兜底数据只覆盖中国，避免境外坐标被错误归到边境城市。
        if (latitude < 17.5 || latitude > 54.5 || longitude < 72 || longitude > 136) {
            return Optional.empty();
        }

        CityPoint nearest = null;
        double nearestDistance = Double.MAX_VALUE;
        for (CityPoint city : cities) {
            double distance = haversine(latitude, longitude, city.latitude(), city.longitude());
            if (distance < nearestDistance) {
                nearest = city;
                nearestDistance = distance;
            }
        }
        if (nearest == null || nearestDistance > MAX_DISTANCE_KM) {
            return Optional.empty();
        }
        return Optional.of(new ResolvedCity(nearest.name(), nearestDistance));
    }

    private static List<CityPoint> loadCities() {
        ClassPathResource resource = new ClassPathResource(DATASET);
        List<CityPoint> result = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(
                resource.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank() || line.startsWith("#")) {
                    continue;
                }
                String[] fields = line.split("\\t");
                if (fields.length != 3) {
                    continue;
                }
                result.add(new CityPoint(
                        fields[0].trim(),
                        Double.parseDouble(fields[1]),
                        Double.parseDouble(fields[2])
                ));
            }
        } catch (IOException | NumberFormatException exception) {
            throw new IllegalStateException("无法加载离线城市定位数据", exception);
        }
        if (result.isEmpty()) {
            throw new IllegalStateException("离线城市定位数据为空");
        }
        return List.copyOf(result);
    }

    private static double haversine(double latitude1, double longitude1,
                                    double latitude2, double longitude2) {
        double latitudeDelta = Math.toRadians(latitude2 - latitude1);
        double longitudeDelta = Math.toRadians(longitude2 - longitude1);
        double a = Math.pow(Math.sin(latitudeDelta / 2), 2)
                + Math.cos(Math.toRadians(latitude1))
                * Math.cos(Math.toRadians(latitude2))
                * Math.pow(Math.sin(longitudeDelta / 2), 2);
        return EARTH_RADIUS_KM * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    }

    record ResolvedCity(String name, double distanceKm) {
    }

    private record CityPoint(String name, double latitude, double longitude) {
    }
}
