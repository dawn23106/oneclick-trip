package com.oneclicktrip.service;

import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.dto.CurrentLocationResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class LocationServiceTest {
    @Test
    void reverseGeocodeReturnsNormalizedCityWithoutPersistingCoordinates() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("https://nominatim.example.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo(startsWith(
                        "https://nominatim.example.test/reverse?lat=32.0603&lon=118.7969"
                )))
                .andRespond(withSuccess("""
                        {
                          "display_name": "中国, 江苏省, 南京市, 玄武区",
                          "address": {
                            "city": "南京市",
                            "city_district": "玄武区",
                            "state": "江苏省"
                          }
                        }
                        """, MediaType.APPLICATION_JSON));

        LocationService service = new LocationService(builder.build());
        CurrentLocationResponse result = service.reverseGeocode(32.0603, 118.7969);

        assertThat(result.city()).isEqualTo("南京");
        assertThat(result.district()).isEqualTo("玄武区");
        assertThat(result.province()).isEqualTo("江苏省");
        assertThat(result.source()).isEqualTo("nominatim-reverse");
        server.verify();
    }

    @Test
    void reverseGeocodeUsesMunicipalityWhenCityFieldIsMissing() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("https://nominatim.example.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo(startsWith("https://nominatim.example.test/reverse")))
                .andRespond(withSuccess("""
                        {
                          "display_name": "中国, 北京市, 海淀区",
                          "address": {"state": "北京市", "city_district": "海淀区"}
                        }
                        """, MediaType.APPLICATION_JSON));

        CurrentLocationResponse result = new LocationService(builder.build())
                .reverseGeocode(39.9042, 116.4074);

        assertThat(result.city()).isEqualTo("北京");
        server.verify();
    }

    @Test
    void reverseGeocodeCorrectsDistrictMislabelledAsCityByProvider() {
        RestClient.Builder builder = RestClient.builder()
                .baseUrl("https://nominatim.example.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        server.expect(requestTo(startsWith("https://nominatim.example.test/reverse")))
                .andRespond(withSuccess("""
                        {
                          "display_name": "玄武门街道, 玄武区, 南京市, 江苏省, 中国",
                          "address": {"city": "玄武区", "suburb": "玄武门街道", "state": "江苏省"}
                        }
                        """, MediaType.APPLICATION_JSON));

        CurrentLocationResponse result = new LocationService(builder.build())
                .reverseGeocode(32.0603, 118.7969);

        assertThat(result.city()).isEqualTo("南京");
        assertThat(result.district()).isEqualTo("玄武区");
        server.verify();
    }

    @Test
    void reverseGeocodeRejectsInvalidCoordinatesBeforeCallingProvider() {
        LocationService service = new LocationService(RestClient.create());

        assertThatThrownBy(() -> service.reverseGeocode(91, 118.8))
                .isInstanceOf(BusinessException.class)
                .hasMessage("定位坐标不合法");
    }
}
