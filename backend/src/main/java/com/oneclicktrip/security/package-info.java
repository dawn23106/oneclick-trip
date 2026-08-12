/**
 * Security 层：登录 token、当前用户身份、权限校验相关代码。
 *
 * 登录成功后后端签发 JWT，前端请求时带上 JWT，JwtAuthenticationFilter 再把它解析成当前用户。
 */
package com.oneclicktrip.security;
