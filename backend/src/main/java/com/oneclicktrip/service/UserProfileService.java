package com.oneclicktrip.service;

import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.dto.UpdateUserProfileRequest;
import com.oneclicktrip.dto.UserProfileResponse;
import com.oneclicktrip.entity.User;
import com.oneclicktrip.mapper.UserMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserProfileService {
    private final UserMapper userMapper;

    public UserProfileService(UserMapper userMapper) {
        this.userMapper = userMapper;
    }

    public UserProfileResponse getProfile(Long userId) {
        return toResponse(getActiveUser(userId));
    }

    @Transactional
    public UserProfileResponse updateProfile(Long userId, UpdateUserProfileRequest request) {
        // 只允许用户修改昵称和头像，账号名、角色这类敏感字段不从前端更新。
        User user = getActiveUser(userId);
        user.setNickname(request.nickname().trim());
        user.setAvatarUrl(request.avatarUrl().trim());
        userMapper.updateById(user);
        return toResponse(user);
    }

    private User getActiveUser(Long userId) {
        // 所有“当前用户”操作都先校验用户是否存在且启用。
        User user = userMapper.selectById(userId);
        if (user == null || user.getStatus() == null || user.getStatus() != 1) {
            throw new BusinessException("用户不存在或已停用");
        }
        return user;
    }

    private UserProfileResponse toResponse(User user) {
        return new UserProfileResponse(
                user.getId(),
                user.getUsername(),
                user.getNickname(),
                user.getAvatarUrl(),
                user.getRole()
        );
    }
}
