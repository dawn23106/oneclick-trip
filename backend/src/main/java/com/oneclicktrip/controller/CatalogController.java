package com.oneclicktrip.controller;

import com.oneclicktrip.common.ApiResponse;
import com.oneclicktrip.entity.*;
import com.oneclicktrip.service.CatalogService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api")
public class CatalogController {
    private final CatalogService catalogService;

    public CatalogController(CatalogService catalogService) {
        this.catalogService = catalogService;
    }

    @GetMapping("/cities")
    public ApiResponse<List<City>> cities() {
        // 首页热门目的地、规划页目的地选择都从这里拿城市列表。
        return ApiResponse.ok(catalogService.listCities());
    }

    @GetMapping("/cities/{id}")
    public ApiResponse<City> city(@PathVariable Long id) {
        return ApiResponse.ok(catalogService.getCity(id));
    }

    @GetMapping("/cities/{id}/spots")
    public ApiResponse<List<ScenicSpot>> spots(@PathVariable Long id) {
        // 景点攻略页和规则版行程生成都会使用城市景点数据。
        return ApiResponse.ok(catalogService.listSpots(id));
    }

    @GetMapping("/cities/{id}/foods")
    public ApiResponse<List<Food>> foods(@PathVariable Long id) {
        // 美食页和行程生成中的午餐/晚餐安排都会使用这里的数据。
        return ApiResponse.ok(catalogService.listFoods(id));
    }

    @GetMapping("/cities/{id}/hotels")
    public ApiResponse<List<Hotel>> hotels(@PathVariable Long id) {
        return ApiResponse.ok(catalogService.listHotels(id));
    }

    @GetMapping("/trip-templates")
    public ApiResponse<List<TripTemplate>> templates(@RequestParam(required = false) Long cityId) {
        return ApiResponse.ok(catalogService.listTemplates(cityId));
    }
}
