<template>
  <div>
    <div class="table-card">
      <div class="card-header">
        <div class="header-left">
          <h3>AI 会话列表</h3>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索用户 / 标题 / 会话 ID"
            prefix-icon="Search"
            clearable
            class="admin-search"
            style="width: 280px"
            @input="handleSearch"
          />
          <el-tag v-if="filteredUserId" closable type="success" effect="plain" @close="clearUserFilter">
            用户：{{ route.query.user || filteredUserId }}
          </el-tag>
        </div>
        <div class="header-right">
          <el-tag type="info" effect="plain">共 {{ total }} 段会话</el-tag>
        </div>
      </div>

      <div class="card-body">
        <el-table :data="conversations" stripe style="width: 100%" v-loading="loading">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="用户" min-width="145">
            <template #default="{ row }">
              <strong>{{ row.nickname || row.username }}</strong>
              <div class="muted-line">{{ row.username }} · UID {{ row.userId }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="会话标题" min-width="190" show-overflow-tooltip />
          <el-table-column prop="lastMessagePreview" label="最后消息" min-width="240" show-overflow-tooltip />
          <el-table-column label="消息数" width="90" align="center">
            <template #default="{ row }">{{ row.messageCount }} 条</template>
          </el-table-column>
          <el-table-column label="健康状态" width="118">
            <template #default="{ row }">
              <el-tag :type="healthTagType(row.healthStatus)" size="small" effect="plain">
                {{ healthLabel(row.healthStatus) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="运行追踪" width="116" align="center">
            <template #default="{ row }">
              <span class="trace-count">{{ row.totalRuns || 0 }} 次</span>
              <span v-if="abnormalRunCount(row)" class="trace-problem">
                {{ abnormalRunCount(row) }} 次需排查
              </span>
            </template>
          </el-table-column>
          <el-table-column label="最后更新" width="170">
            <template #default="{ row }"><span class="muted-line">{{ formatDate(row.updateTime) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="130" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="viewDetail(row)">查看</el-button>
              <el-popconfirm title="确定删除这段会话吗？" @confirm="removeConversation(row)">
                <template #reference><el-button size="small" type="danger" link>删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @change="loadConversations"
        />
      </div>
    </div>

    <el-drawer v-model="drawerVisible" title="会话详情" size="min(760px, 96vw)">
      <template v-if="selectedConversation">
        <el-descriptions :column="1" border class="conversation-meta">
          <el-descriptions-item label="用户">
            {{ selectedConversation.nickname || selectedConversation.username }}
            （{{ selectedConversation.username }} / UID {{ selectedConversation.userId }}）
          </el-descriptions-item>
          <el-descriptions-item label="标题">{{ selectedConversation.title }}</el-descriptions-item>
          <el-descriptions-item label="会话 ID">{{ selectedConversation.conversationId }}</el-descriptions-item>
          <el-descriptions-item label="消息数">{{ selectedConversation.messageCount }} 条</el-descriptions-item>
          <el-descriptions-item label="生命周期">
            {{ selectedConversation.status === 'ACTIVE' ? '可继续对话' : selectedConversation.status }}
          </el-descriptions-item>
          <el-descriptions-item label="健康状态">
            <el-tag :type="healthTagType(selectedConversation.healthStatus)" size="small" effect="plain">
              {{ healthLabel(selectedConversation.healthStatus) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-alert
          v-if="traceSummary.healthStatus === 'FAILED'"
          title="该会话存在 Agent 运行失败"
          :description="traceDescription"
          type="error"
          show-icon
          :closable="false"
          class="trace-alert"
        />
        <el-alert
          v-else-if="traceSummary.healthStatus === 'TOOL_ERROR'"
          title="该会话存在工具调用异常"
          :description="traceDescription"
          type="error"
          show-icon
          :closable="false"
          class="trace-alert"
        />
        <el-alert
          v-else-if="traceSummary.healthStatus === 'DEGRADED'"
          title="该会话曾使用降级数据或规则兜底"
          :description="traceDescription"
          type="warning"
          show-icon
          :closable="false"
          class="trace-alert"
        />

        <section class="trace-panel">
          <div class="section-heading">
            <div>
              <h4>关联 Agent 运行</h4>
              <p>这里仅展示会话级摘要；节点、工具和错误详情请前往 Agent 运行管理排查</p>
            </div>
            <el-tag size="small" :type="healthTagType(traceSummary.healthStatus)" effect="plain">
              {{ traceSummary.totalRuns || 0 }} 次运行
            </el-tag>
          </div>

          <div class="trace-metrics">
            <div><span>全部运行</span><strong>{{ traceSummary.totalRuns || 0 }}</strong></div>
            <div class="danger"><span>运行失败</span><strong>{{ traceSummary.failedRuns || 0 }}</strong></div>
            <div class="danger"><span>工具异常</span><strong>{{ traceSummary.toolErrorRuns || 0 }}</strong></div>
            <div class="warning"><span>降级运行</span><strong>{{ traceSummary.degradedRuns || 0 }}</strong></div>
          </div>
          <div class="trace-action">
            <span v-if="traceSummary.totalRuns">将按当前会话 ID 自动筛选对应运行记录</span>
            <span v-else>该会话尚无 Agent 运行日志</span>
            <el-button
              type="primary"
              :disabled="!traceSummary.totalRuns"
              @click="goToAgentRuns"
            >
              前往 Agent 运行管理
            </el-button>
          </div>
        </section>

        <section class="plan-version-panel">
          <div class="section-heading">
            <h4>关联行程版本</h4>
            <el-tag size="small" type="info" effect="plain">{{ selectedPlanVersions.length }} 个版本</el-tag>
          </div>
          <el-table v-if="selectedPlanVersions.length" :data="selectedPlanVersions" size="small" border>
            <el-table-column label="版本" width="88">
              <template #default="{ row }">V{{ row.planVersion }}</template>
            </el-table-column>
            <el-table-column label="目的地" prop="destination" width="110" />
            <el-table-column label="方案" min-width="190">
              <template #default="{ row }">{{ row.plan?.title || row.planId }}</template>
            </el-table-column>
            <el-table-column label="状态" width="88">
              <template #default="{ row }">
                <el-tag :type="row.current ? 'success' : 'info'" size="small" effect="plain">
                  {{ row.current ? '当前' : '历史' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="保存时间" min-width="155">
              <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
          <div v-else class="message-empty compact">该会话尚未保存行程方案</div>
        </section>

        <div class="message-history">
          <h4>消息记录</h4>
          <div v-if="!selectedMessages.length" class="message-empty">这段会话还没有消息</div>
          <div
            v-for="message in selectedMessages"
            :key="message.id"
            class="admin-message"
            :class="message.role === 'USER' ? 'user' : 'assistant'"
          >
            <div class="message-label">
              <strong>{{ message.role === 'USER' ? '用户' : 'AI Agent' }}</strong>
              <span>{{ formatDate(message.createTime) }}</span>
            </div>
            <p>{{ message.content }}</p>
            <div v-if="message.intent || message.status === 'FAILED'" class="message-tags">
              <el-tag v-if="message.intent" size="small" effect="plain">{{ message.intent }}</el-tag>
              <el-tag v-if="message.status === 'FAILED'" size="small" type="danger" effect="plain">失败</el-tag>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { deleteConversation, fetchConversation, fetchConversations } from '../api/admin.js'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const conversations = ref([])
const page = ref(1)
const size = ref(10)
const total = ref(0)
const searchKeyword = ref('')
const filteredUserId = ref(route.query.userId || '')
const drawerVisible = ref(false)
const selectedConversation = ref(null)
const selectedMessages = ref([])
const selectedPlanVersions = ref([])
const traceSummary = ref({})
let searchTimer = null

const traceDescription = computed(() => {
  const summary = traceSummary.value || {}
  return `共 ${summary.totalRuns || 0} 次运行，其中运行失败 ${summary.failedRuns || 0} 次、工具异常 ${summary.toolErrorRuns || 0} 次、降级 ${summary.degradedRuns || 0} 次。请前往 Agent 运行管理查看具体节点和错误码。`
})

onMounted(loadConversations)

async function loadConversations() {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (filteredUserId.value) params.userId = filteredUserId.value
    const data = await fetchConversations(params)
    conversations.value = data.records || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.message || '加载会话列表失败')
    conversations.value = []
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadConversations()
  }, 300)
}

async function viewDetail(row) {
  try {
    const data = await fetchConversation(row.id)
    selectedConversation.value = data.conversation
    selectedMessages.value = data.messages || []
    selectedPlanVersions.value = data.planVersions || []
    traceSummary.value = data.traceSummary || {}
    drawerVisible.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载会话详情失败')
  }
}

async function removeConversation(row) {
  try {
    await deleteConversation(row.id)
    ElMessage.success('会话已删除')
    loadConversations()
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  }
}

function clearUserFilter() {
  filteredUserId.value = ''
  router.replace({ path: '/conversations' })
  page.value = 1
  loadConversations()
}

function goToAgentRuns() {
  const conversationId = selectedConversation.value?.conversationId
  if (!conversationId) return
  drawerVisible.value = false
  router.push({ path: '/agent-runs', query: { conversationId } })
}

function formatDate(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function healthLabel(value) {
  return {
    FAILED: '运行失败',
    TOOL_ERROR: '工具异常',
    DEGRADED: '降级运行',
    HEALTHY: '运行正常',
    NO_RUN: '无运行记录'
  }[value] || value || '未知'
}

function healthTagType(value) {
  if (value === 'FAILED' || value === 'TOOL_ERROR') return 'danger'
  if (value === 'DEGRADED') return 'warning'
  if (value === 'HEALTHY') return 'success'
  return 'info'
}

function abnormalRunCount(row) {
  return Number(row.abnormalRuns || 0)
}

</script>

<style scoped>
.muted-line {
  margin-top: 3px;
  color: var(--admin-text-muted);
  font-size: 12px;
}

.conversation-meta {
  margin-bottom: 16px;
}

.trace-alert { margin-bottom: 16px; }
.trace-panel { margin-bottom: 24px; padding: 18px; border: 1px solid var(--admin-border); background: #fbfdfc; }
.section-heading > div > p { margin: 4px 0 0; color: var(--admin-text-muted); font-size: 12px; }
.trace-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 14px 0 16px; border: 1px solid var(--admin-border); background: #fff; }
.trace-metrics > div { padding: 12px 14px; border-right: 1px solid var(--admin-border); }
.trace-metrics > div:last-child { border-right: 0; }
.trace-metrics span { display: block; color: var(--admin-text-muted); font-size: 11px; }
.trace-metrics strong { display: block; margin-top: 5px; font-size: 20px; }
.trace-metrics .danger strong, .trace-problem { color: #c2413c; }
.trace-metrics .warning strong { color: #ad6800; }
.trace-count, .trace-problem { display: block; font-size: 12px; line-height: 1.45; }
.trace-problem { font-weight: 700; }
.trace-action { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.trace-action span { color: var(--admin-text-muted); font-size: 12px; }

.message-history h4 {
  margin: 0 0 14px;
  font-size: 15px;
}

.plan-version-panel {
  margin-bottom: 22px;
}

.section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-heading h4 {
  margin: 0;
  font-size: 15px;
}

.message-empty.compact {
  padding: 24px 0;
  border: 1px dashed var(--admin-border);
}

.admin-message {
  max-width: 88%;
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--admin-border);
  border-radius: 8px;
  background: #fff;
}

.admin-message.user {
  margin-left: auto;
  border-color: #bfe8db;
  background: #f0faf6;
}

.message-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--admin-text-muted);
  font-size: 11px;
}

.message-label strong {
  color: var(--admin-text);
  font-size: 12px;
}

.admin-message p {
  margin: 8px 0 0;
  color: var(--admin-text);
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.message-tags {
  display: flex;
  gap: 6px;
  margin-top: 9px;
}

.message-empty {
  padding: 50px 0;
  color: var(--admin-text-muted);
  text-align: center;
}

@media (max-width: 760px) {
  .trace-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .trace-metrics > div:nth-child(2) { border-right: 0; }
  .trace-action { align-items: stretch; flex-direction: column; }
}
</style>
