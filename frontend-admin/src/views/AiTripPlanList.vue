<template>
  <div class="table-card">
    <div class="card-header">
      <div class="header-left">
        <h3>AI 行程管理</h3>
        <el-input
          v-model="keyword"
          placeholder="搜索目的地、方案号、会话号或用户"
          clearable
          style="width: 300px"
          @input="scheduleLoad"
        />
        <el-select v-model="deleted" style="width: 130px" @change="resetAndLoad">
          <el-option label="正常行程" value="active" />
          <el-option label="已删除" value="deleted" />
          <el-option label="全部" value="all" />
        </el-select>
      </div>
      <el-tag type="info" effect="plain">共 {{ total }} 条</el-tag>
    </div>

    <div class="card-body">
      <el-table v-loading="loading" :data="records" stripe>
        <el-table-column prop="id" label="记录ID" width="85" />
        <el-table-column prop="nickname" label="用户" width="120">
          <template #default="{ row }">{{ row.nickname || `用户 ${row.userId}` }}</template>
        </el-table-column>
        <el-table-column prop="destination" label="目的地" min-width="130" />
        <el-table-column prop="planId" label="方案编号" min-width="170" show-overflow-tooltip />
        <el-table-column label="版本" width="80" align="center">
          <template #default="{ row }">V{{ row.planVersion }}</template>
        </el-table-column>
        <el-table-column prop="tripStatus" label="行程状态" width="110" />
        <el-table-column label="当前版本" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.current ? 'success' : 'info'" size="small">
              {{ row.current ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数据状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.deleted ? 'danger' : 'success'" size="small">
              {{ row.deleted ? '已删除' : '正常' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="生成时间" width="170" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDetail(row.id)">详情</el-button>
            <el-popconfirm
              v-if="!row.deleted"
              title="删除后用户端将不能再读取或用于预订，确定继续吗？"
              @confirm="remove(row.id)"
            >
              <template #reference><el-button link type="danger">删除</el-button></template>
            </el-popconfirm>
            <el-popconfirm v-else title="确定恢复该行程版本吗？" @confirm="restore(row.id)">
              <template #reference><el-button link type="success">恢复</el-button></template>
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
        @change="load"
      />
    </div>

    <el-drawer v-model="drawer" title="AI 行程详情" size="620px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户">{{ detail.nickname || detail.userId }}</el-descriptions-item>
          <el-descriptions-item label="会话编号">{{ detail.conversationId }}</el-descriptions-item>
          <el-descriptions-item label="方案编号">{{ detail.planId }}</el-descriptions-item>
          <el-descriptions-item label="版本">V{{ detail.planVersion }}</el-descriptions-item>
          <el-descriptions-item label="目的地">{{ detail.destination }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.tripStatus }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ detail.createdAt }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.deleted" label="删除信息">
            {{ detail.deletedAt }}（管理员 {{ detail.deletedBy }}）
          </el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 20px 0 10px">结构化方案数据</h4>
        <pre class="plan-json">{{ prettyPlan }}</pre>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  deleteAiTripPlan,
  fetchAiTripPlan,
  fetchAiTripPlans,
  restoreAiTripPlan
} from '../api/admin.js'

const loading = ref(false)
const records = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const deleted = ref('active')
const drawer = ref(false)
const detail = ref(null)
let timer

const prettyPlan = computed(() => {
  if (!detail.value?.planJson) return '-'
  try { return JSON.stringify(JSON.parse(detail.value.planJson), null, 2) } catch { return detail.value.planJson }
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const data = await fetchAiTripPlans({
      page: page.value,
      size: size.value,
      keyword: keyword.value,
      deleted: deleted.value
    })
    records.value = data.records || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.message || '加载 AI 行程失败')
  } finally {
    loading.value = false
  }
}

function scheduleLoad() {
  clearTimeout(timer)
  timer = setTimeout(resetAndLoad, 300)
}

function resetAndLoad() {
  page.value = 1
  load()
}

async function showDetail(id) {
  try {
    detail.value = await fetchAiTripPlan(id)
    drawer.value = true
  } catch (error) {
    ElMessage.error(error.message || '加载行程详情失败')
  }
}

async function remove(id) {
  try {
    await deleteAiTripPlan(id)
    ElMessage.success('行程已软删除')
    load()
  } catch (error) {
    ElMessage.error(error.message || '删除失败')
  }
}

async function restore(id) {
  try {
    await restoreAiTripPlan(id)
    ElMessage.success('行程已恢复')
    load()
  } catch (error) {
    ElMessage.error(error.message || '恢复失败')
  }
}
</script>

<style scoped>
.plan-json {
  max-height: 520px;
  overflow: auto;
  padding: 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: #fafafa;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.55;
}
</style>
