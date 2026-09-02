package com.oneclicktrip.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.web.client.RestClientBuilderConfigurer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpHeaders;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

import java.time.Duration;

@Configuration
public class MapClientConfig {
    @Bean("nominatimRestClient")
    public RestClient nominatimRestClient(
            RestClientBuilderConfigurer configurer,
            @Value("${app.map.nominatim-base-url:https://nominatim.openstreetmap.org}") String baseUrl,
            @Value("${app.map.user-agent:oneclick-trip/0.8 (educational travel planner)}") String userAgent,
            @Value("${app.map.timeout:8s}") Duration timeout
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeout);
        requestFactory.setReadTimeout(timeout);

        return configurer.configure(RestClient.builder())
                .baseUrl(baseUrl)
                .defaultHeader(HttpHeaders.USER_AGENT, userAgent)
                .requestFactory(requestFactory)
                .build();
    }
}
