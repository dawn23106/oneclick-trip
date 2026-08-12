/**
 * Controller 层：后端接口入口。
 *
 * 前端请求会先进入这里，例如 /api/auth/login、/api/cities、/api/trip-plans/generate。
 * Controller 尽量只做“接收参数、调用 Service、包装返回结果”，不要把复杂业务写在这里。
 */
package com.oneclicktrip.controller;
