package com.oneclicktrip;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
@MapperScan("com.oneclicktrip.mapper")
public class OneclickTripApplication {
    /**
     * 后端启动入口。
     *
     * 运行这个 main 方法后，Spring Boot 会启动 Web 服务、加载 Controller/Service/Mapper，
     * 并连接 application.yml 中配置的 MySQL 数据库。
     */
    public static void main(String[] args) {
        SpringApplication.run(OneclickTripApplication.class, args);
    }
}
