package com.oneclicktrip.service;

import com.oneclicktrip.dto.AiChatRequest;
import com.oneclicktrip.dto.AiChatResponse;
import com.oneclicktrip.entity.AiCallLog;
import com.oneclicktrip.mapper.AiCallLogMapper;
import org.springframework.stereotype.Service;

@Service
public class AiAssistantService {
    private final AiCallLogMapper aiCallLogMapper;

    public AiAssistantService(AiCallLogMapper aiCallLogMapper) {
        this.aiCallLogMapper = aiCallLogMapper;
    }

    public AiChatResponse chat(AiChatRequest request) {
        // 这里是 AI 层的预留位置。
        // 以后可以把 request.message() 转发给 FastAPI，再把 FastAPI 返回的方案写回 Java 业务库。
        String message = "AI 助手暂未接入。当前版本已支持城市、景点、美食、酒店和规则版行程生成，后续会在这里接入 FastAPI AI 引擎。";

        // 即使是占位回复，也先记录日志，后面方便统计用户问了什么。
        AiCallLog log = new AiCallLog();
        log.setUserId(request.userId());
        log.setRequestText(request.message());
        log.setResponseText(message);
        log.setStatus("PLACEHOLDER");
        aiCallLogMapper.insert(log);

        return new AiChatResponse(
                "PLACEHOLDER",
                message,
                "请先使用 /api/trip-plans/generate 生成基础行程"
        );
    }
}
