# 一键游微信小程序

这是独立于 `frontend` 的原生微信小程序 C 端，能够直接导入微信开发者工具。现已接入项目现有 Spring Boot API，包含账号登录、首页推荐、AI 异步规划、历史会话、行程列表、行程详情和个人中心。

## 本地运行

1. 先启动 MySQL、Spring Boot 后端和 Python Agent。后端地址默认为 `http://127.0.0.1:8080`。
2. 打开微信开发者工具，选择“导入项目”，项目目录选择本文件所在的 `miniprogram` 目录。
3. 没有小程序 AppID 时可先使用测试号；有 AppID 后，在开发者工具项目设置中替换 `touristappid`。
4. 本地开发时，在“详情 → 本地设置”中勾选“不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书”。
5. 编译后使用演示账号登录：用户名 `user`，密码 `123456`。

接口地址在 `utils/config.js` 中维护：

```js
BASE_URL: 'http://127.0.0.1:8080'
```

## 真机调试

手机里的 `127.0.0.1` 指向手机自身，不能访问电脑。真机调试时需要：

1. 手机与电脑连接同一局域网；
2. 将 `BASE_URL` 改成电脑局域网地址，例如 `http://192.168.1.8:8080`；
3. Windows 防火墙允许 Java/8080 端口接收局域网请求；
4. 确保 Spring Boot、FastAPI 和数据库都已启动。

## 正式发布

发布版本不能使用本机地址。需要准备已备案的 HTTPS API 域名，在微信公众平台将其加入 `request` 合法域名，并把 `BASE_URL` 改成该域名。当前版本复用了项目原有的账号密码登录；若要实现微信一键登录，还需在拿到正式 AppID 和 AppSecret 后新增 `wx.login` 对应的后端换码接口，AppSecret 只能放在后端。

## 页面结构

```text
pages/home          首页与旅行灵感
pages/ai            AI 规划与历史会话
pages/trips         已保存行程
pages/trip-detail   规则/AI 行程详情
pages/profile       个人中心与资料编辑
pages/login         登录与注册
```
