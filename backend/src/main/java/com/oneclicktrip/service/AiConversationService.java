package com.oneclicktrip.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.oneclicktrip.common.BusinessException;
import com.oneclicktrip.dto.AiChatResponse;
import com.oneclicktrip.dto.AiConversationDetailResponse;
import com.oneclicktrip.dto.AiConversationSummaryResponse;
import com.oneclicktrip.dto.AiMessageResponse;
import com.oneclicktrip.entity.AiConversation;
import com.oneclicktrip.entity.AiMessage;
import com.oneclicktrip.mapper.AiConversationMapper;
import com.oneclicktrip.mapper.AiMessageMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
public class AiConversationService {
    private final AiConversationMapper conversationMapper;
    private final AiMessageMapper messageMapper;
    private final ObjectMapper objectMapper;

    public AiConversationService(
            AiConversationMapper conversationMapper,
            AiMessageMapper messageMapper,
            ObjectMapper objectMapper
    ) {
        this.conversationMapper = conversationMapper;
        this.messageMapper = messageMapper;
        this.objectMapper = objectMapper;
    }

    public List<AiConversationSummaryResponse> list(Long userId) {
        // 会话列表仅返回当前用户未删除的会话摘要。
        return conversationMapper.selectList(Wrappers.<AiConversation>lambdaQuery()
                        .eq(AiConversation::getUserId, userId)
                        .eq(AiConversation::getDeleted, 0)
                        .orderByDesc(AiConversation::getUpdateTime))
                .stream().map(this::toSummary).toList();
    }

    public AiConversationSummaryResponse create(Long userId, String requestedTitle) {
        // 未提供标题时使用稳定的默认标题，后续可根据首条消息更新。
        AiConversation conversation = new AiConversation();
        conversation.setConversationId(UUID.randomUUID().toString());
        conversation.setUserId(userId);
        conversation.setTitle(hasText(requestedTitle) ? limit(requestedTitle.trim(), 128) : "新对话");
        conversation.setStatus("ACTIVE");
        conversation.setMessageCount(0);
        conversation.setDeleted(0);
        conversationMapper.insert(conversation);
        return toSummary(conversationMapper.selectById(conversation.getId()));
    }

    public AiConversationDetailResponse detail(Long userId, String conversationId) {
        // 先校验会话归属，再加载并按时间顺序返回消息。
        AiConversation conversation = requireOwned(userId, conversationId);
        List<AiMessageResponse> messages = messages(conversation.getId());
        return new AiConversationDetailResponse(toSummary(conversation), messages);
    }

    public AiConversationSummaryResponse rename(Long userId, String conversationId, String title) {
        // 重命名只修改会话元数据，不影响 LangGraph checkpoint。
        AiConversation conversation = requireOwned(userId, conversationId);
        conversation.setTitle(limit(title.trim(), 128));
        conversationMapper.updateById(conversation);
        return toSummary(conversationMapper.selectById(conversation.getId()));
    }

    public void delete(Long userId, String conversationId) {
        // 用户侧删除采用逻辑删除，保留审计和 Agent 运行记录。
        AiConversation conversation = requireOwned(userId, conversationId);
        conversationMapper.deleteById(conversation.getId());
    }

    public AiConversation findOrCreate(Long userId, String conversationId, String firstMessage) {
        // Agent 首次调用时创建会话；已有会话必须属于同一 JWT 用户。
        AiConversation existing = conversationMapper.selectOne(Wrappers.<AiConversation>lambdaQuery()
                .eq(AiConversation::getConversationId, conversationId)
                .last("LIMIT 1"));
        if (existing != null) {
            if (!userId.equals(existing.getUserId()) || Integer.valueOf(1).equals(existing.getDeleted())) {
                throw new BusinessException("无权访问该会话");
            }
            return existing;
        }

        AiConversation conversation = new AiConversation();
        conversation.setConversationId(conversationId);
        conversation.setUserId(userId);
        conversation.setTitle(titleFrom(firstMessage));
        conversation.setStatus("ACTIVE");
        conversation.setMessageCount(0);
        conversation.setDeleted(0);
        conversationMapper.insert(conversation);
        return conversationMapper.selectById(conversation.getId());
    }

    public AiConversation findOwned(Long userId, String conversationId) {
        return requireOwned(userId, conversationId);
    }

    public void recordUserMessage(AiConversation conversation, String content) {
        // 用户消息在转发 AI 前后均由业务层统一持久化。
        if ((conversation.getMessageCount() == null || conversation.getMessageCount() == 0)
                && "新对话".equals(conversation.getTitle())) {
            conversation.setTitle(titleFrom(content));
        }
        insertMessage(conversation.getId(), "USER", content, "COMPLETED", null, null);
        refreshSummary(conversation, content);
    }

    public void recordAssistantMessage(AiConversation conversation, AiChatResponse response) {
        // 保存展示文本及必要的结构化 Agent 状态，便于恢复会话详情。
        updateTitleFromAgent(conversation, response);
        String stateJson = null;
        try {
            if (response.agentState() != null) {
                stateJson = objectMapper.writeValueAsString(response.agentState());
            }
        } catch (Exception ignored) {
            // 文本消息仍可正常保存，结构化展示数据缺失时前端会降级为普通回复。
        }
        insertMessage(
                conversation.getId(),
                "ASSISTANT",
                response.message(),
                response.status(),
                response.intent(),
                stateJson
        );
        refreshSummary(conversation, response.message());
    }

    private void updateTitleFromAgent(AiConversation conversation, AiChatResponse response) {
        // 第一轮结束后使用模型识别出的目的地和意图生成语义标题，避免直接截断用户原话。
        if (conversation.getMessageCount() == null || conversation.getMessageCount() > 1) {
            return;
        }
        JsonNode state = response.agentState();
        if (state == null || state.isNull()) {
            return;
        }
        String destination = state.path("current_plan").path("destination").asText();
        if (!hasText(destination)) {
            destination = state.path("entities").path("destination").asText();
        }
        String intentLabel = switch (response.intent() == null ? "" : response.intent()) {
            case "trip_plan" -> "智能行程规划";
            case "modify_plan" -> "行程修改";
            case "weather_query" -> "旅行天气查询";
            case "hotel_query" -> "酒店推荐";
            case "transport_query" -> "交通方案比较";
            case "booking", "booking_confirm" -> "旅行预订";
            case "memory_manage" -> "旅行偏好管理";
            default -> "旅行咨询";
        };
        String generatedTitle = hasText(destination) ? destination + "·" + intentLabel : intentLabel;
        conversation.setTitle(limit(generatedTitle, 128));
    }

    public void recordFailure(AiConversation conversation, String message) {
        // 将远端执行失败转为可追踪的会话消息，而不是静默丢失。
        insertMessage(conversation.getId(), "ASSISTANT", message, "FAILED", null, null);
        refreshSummary(conversation, message);
    }

    private AiConversation requireOwned(Long userId, String conversationId) {
        AiConversation conversation = conversationMapper.selectOne(Wrappers.<AiConversation>lambdaQuery()
                .eq(AiConversation::getConversationId, conversationId)
                .eq(AiConversation::getUserId, userId)
                .eq(AiConversation::getDeleted, 0)
                .last("LIMIT 1"));
        if (conversation == null) {
            throw new BusinessException("会话不存在");
        }
        return conversation;
    }

    private void insertMessage(
            Long conversationId,
            String role,
            String content,
            String status,
            String intent,
            String stateJson
    ) {
        AiMessage message = new AiMessage();
        message.setAiConversationId(conversationId);
        message.setRole(role);
        message.setContent(content == null ? "" : content);
        message.setStatus(status);
        message.setIntent(intent);
        message.setAgentStateJson(stateJson);
        messageMapper.insert(message);
    }

    private void refreshSummary(AiConversation conversation, String preview) {
        Long count = messageMapper.selectCount(Wrappers.<AiMessage>lambdaQuery()
                .eq(AiMessage::getAiConversationId, conversation.getId()));
        conversation.setLastMessagePreview(limit(preview, 255));
        conversation.setMessageCount(count.intValue());
        conversation.setUpdateTime(LocalDateTime.now());
        conversationMapper.updateById(conversation);
    }

    private List<AiMessageResponse> messages(Long conversationId) {
        return messageMapper.selectList(Wrappers.<AiMessage>lambdaQuery()
                        .eq(AiMessage::getAiConversationId, conversationId)
                        .orderByAsc(AiMessage::getId))
                .stream().map(this::toMessage).toList();
    }

    private AiMessageResponse toMessage(AiMessage message) {
        JsonNode state = null;
        if (hasText(message.getAgentStateJson())) {
            try {
                state = objectMapper.readTree(message.getAgentStateJson());
            } catch (Exception ignored) {
                state = null;
            }
        }
        return new AiMessageResponse(
                message.getId(),
                message.getRole(),
                message.getContent(),
                message.getStatus(),
                message.getIntent(),
                state,
                message.getCreateTime()
        );
    }

    private AiConversationSummaryResponse toSummary(AiConversation conversation) {
        return new AiConversationSummaryResponse(
                conversation.getId(),
                conversation.getConversationId(),
                conversation.getTitle(),
                conversation.getStatus(),
                conversation.getLastMessagePreview(),
                conversation.getMessageCount(),
                conversation.getCreateTime(),
                conversation.getUpdateTime()
        );
    }

    private String titleFrom(String message) {
        if (!hasText(message)) {
            return "新对话";
        }
        String cleaned = message.trim().replaceAll("\\s+", " ");
        return cleaned.length() <= 24 ? cleaned : cleaned.substring(0, 24) + "...";
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private String limit(String value, int maxLength) {
        if (value == null) {
            return "";
        }
        return value.length() <= maxLength ? value : value.substring(0, maxLength);
    }
}
