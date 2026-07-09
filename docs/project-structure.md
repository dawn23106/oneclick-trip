# 项目目录说明

这个项目现在是一个“非 AI MVP”：先把 Vue 前端、Spring Boot 后端、MySQL 数据库和基础旅游业务跑通，AI 助手暂时只是占位接口。

## 一眼看懂整体结构

```text
oneclick-trip/
├─ backend/                 Java Spring Boot 后端
├─ frontend/                Vue 3 前端
├─ docs/                    项目说明和接口测试文档
├─ tools/                   本机辅助脚本
├─ docker-compose.yml       可选的 MySQL Docker 启动配置
├─ README.md                项目启动和协作说明
├─ .gitignore               Git 忽略规则
└─ .gitattributes           Git 换行和二进制文件规则
```

## 后端目录

```text
backend/
├─ pom.xml
├─ .mvn/maven.config
└─ src/main/
   ├─ java/com/oneclicktrip/
   │  ├─ OneclickTripApplication.java
   │  ├─ common/
   │  ├─ config/
   │  ├─ controller/
   │  ├─ dto/
   │  ├─ entity/
   │  ├─ mapper/
   │  ├─ security/
   │  └─ service/
   └─ resources/
      ├─ application-example.yml
      ├─ application.yml
      ├─ schema.sql
      ├─ data.sql
      └─ static/oneclick-trip-assets/
```

`pom.xml`：后端依赖清单，类似 Java 项目的“菜单”。Spring Boot、MyBatis-Plus、MySQL 驱动、Security 都在这里声明。

`.mvn/maven.config`：让 Maven 依赖缓存放在项目自己的 `.m2-repository` 里，避免使用系统目录时遇到权限问题。

`OneclickTripApplication.java`：后端启动入口。运行它，Spring Boot 服务就会启动。

`common/`：通用返回格式和异常处理。比如所有接口都返回 `ApiResponse`。

`config/`：全局配置。现在主要是 `SecurityConfig`，控制哪些接口需要登录、跨域怎么放行、密码如何编码。

`controller/`：接口入口。前端请求先到这里，例如：

```text
POST /api/auth/login
GET  /api/cities
POST /api/trip-plans/generate
GET  /api/users/me
```

`service/`：业务逻辑。真正判断登录、生成行程、修改资料的代码在这里。

`mapper/`：数据库访问层。继承 MyBatis-Plus 的 `BaseMapper` 后，就能操作对应表。

`entity/`：数据库表对应的 Java 类。例如 `User` 对应 `sys_user` 表。

`dto/`：接口请求和响应对象。前端传什么、后端返回什么，主要看这里。

`security/`：JWT 登录态相关代码。登录成功后生成 token，之后每次请求靠 token 识别当前用户。

`schema.sql`：建表脚本。

`data.sql`：初始化演示数据，比如 `admin / 123456`、城市、景点、美食。

`application-example.yml`：示例配置，可以提交到 GitHub。

`application.yml`：你自己的本地配置，里面可以写本机 MySQL 密码，已被 `.gitignore` 忽略，不应该提交。

## 前端目录

```text
frontend/
├─ package.json
├─ package-lock.json
├─ vite.config.js
├─ index.html
├─ public/oneclick-trip-assets/
└─ src/
   ├─ main.js
   ├─ App.vue
   ├─ styles.css
   └─ api/client.js
```

`package.json`：前端依赖和命令。`npm run dev`、`npm run build` 就在这里定义。

`vite.config.js`：Vite 配置。它把 `/api` 代理到后端 `http://127.0.0.1:8080`。

`index.html`：前端页面入口。

`src/main.js`：Vue 应用启动入口。

`src/App.vue`：目前的大页面文件。登录页、首页、AI 助手页、规划页、行程详情页、景点页、美食页、我的页都写在这里，通过 `activePage` 控制显示哪个页面。

`src/api/client.js`：前端请求后端接口的统一封装。它会自动带上 JWT token，并统一处理接口错误。

`src/styles.css`：页面样式。

`public/oneclick-trip-assets/`：前端图片资源。页面里用 `/oneclick-trip-assets/xxx.png` 访问。

## 一次请求怎么流动

以“登录”为例：

```text
前端 App.vue 点击登录
  ↓
frontend/src/api/client.js 调用 POST /api/auth/login
  ↓
backend/controller/AuthController.java 接收请求
  ↓
backend/service/AuthService.java 校验账号密码
  ↓
backend/mapper/UserMapper.java 查询 sys_user 表
  ↓
JwtTokenProvider 生成 token
  ↓
返回给前端，前端保存 token 到 localStorage
```

以“生成行程”为例：

```text
前端规划页点击“生成规则版行程”
  ↓
POST /api/trip-plans/generate
  ↓
TripPlanController
  ↓
TripPlanService
  ↓
CatalogService 查询城市、景点、美食、酒店
  ↓
写入 trip_plan、trip_plan_day、trip_plan_item
  ↓
返回 TripPlanResponse 给前端行程详情页展示
```

## 现在最建议先读的文件

第一次看项目，建议按这个顺序：

```text
README.md
docs/project-structure.md
frontend/src/App.vue
frontend/src/api/client.js
backend/src/main/java/com/oneclicktrip/controller/AuthController.java
backend/src/main/java/com/oneclicktrip/service/AuthService.java
backend/src/main/java/com/oneclicktrip/controller/TripPlanController.java
backend/src/main/java/com/oneclicktrip/service/TripPlanService.java
backend/src/main/resources/schema.sql
backend/src/main/resources/data.sql
```

不要一开始就从所有 `entity`、`mapper` 读起，那些更像“数据库字段说明”和“数据库操作入口”，先理解业务流会轻松很多。
