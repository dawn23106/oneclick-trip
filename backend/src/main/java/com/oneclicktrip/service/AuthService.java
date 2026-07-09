package com.oneclicktrip.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.dto.LoginRequest;
import com.oneclicktrip.dto.LoginResponse;
import com.oneclicktrip.dto.RegisterRequest;
import com.oneclicktrip.entity.User;
import com.oneclicktrip.mapper.UserMapper;
import com.oneclicktrip.security.JwtTokenProvider;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    public AuthService(UserMapper userMapper, PasswordEncoder passwordEncoder, JwtTokenProvider jwtTokenProvider) {
        this.userMapper = userMapper;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    public LoginResponse login(LoginRequest request) {
        // 先按用户名查启用中的用户，再用 PasswordEncoder 比对密码。
        // 不要自己用字符串直接比较密码，因为后续注册用户的密码会被加密存储。
        User user = userMapper.selectOne(Wrappers.<User>lambdaQuery()
                .eq(User::getUsername, request.username())
                .eq(User::getStatus, 1)
                .last("LIMIT 1"));
        if (user == null || !passwordEncoder.matches(request.password(), user.getPasswordHash())) {
            throw new BusinessException("用户名或密码错误");
        }
        String token = jwtTokenProvider.createToken(user);
        return toLoginResponse(token, user);
    }

    public LoginResponse register(RegisterRequest request) {
        // 注册前先检查用户名是否重复。
        Long exists = userMapper.selectCount(Wrappers.<User>lambdaQuery()
                .eq(User::getUsername, request.username()));
        if (exists != null && exists > 0) {
            throw new BusinessException("用户名已存在");
        }

        User user = new User();
        user.setUsername(request.username());
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setNickname(request.nickname());
        user.setMobile(request.mobile());
        user.setAvatarUrl("avatar-backpack");
        user.setRole("USER");
        user.setStatus(1);
        userMapper.insert(user);

        // 注册成功后直接签发 token，让用户不用再手动登录一次。
        String token = jwtTokenProvider.createToken(user);
        return toLoginResponse(token, user);
    }

    private LoginResponse toLoginResponse(String token, User user) {
        return new LoginResponse(
                token,
                user.getId(),
                user.getUsername(),
                user.getNickname(),
                user.getAvatarUrl(),
                user.getRole()
        );
    }
}
