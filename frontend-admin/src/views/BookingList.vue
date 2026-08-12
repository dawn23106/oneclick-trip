<template>
  <div class="booking-admin-page">
    <div class="booking-stats">
      <button
        v-for="item in statCards"
        :key="item.value"
        type="button"
        class="booking-stat-card"
        :class="{ active: status === item.value }"
        @click="selectStatus(item.value)"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.count }}</strong>
      </button>
    </div>

    <div class="table-card">
      <div class="card-header">
        <div class="header-left booking-filters">
          <h3>🎫 预订管理</h3>
          <el-input
            v-model="keyword"
            placeholder="草稿编号 / 用户 / 目的地"
            prefix-icon="Search"
            clearable
            class="admin-search"
            style="width:260px"
            @input="handleSearch"
          />
          <el-select v-model="status" placeholder="全部状态" clearable style="width:150px" @change="handleFilter">
            <el-option label="待确认" value="pending_confirmation" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="已过期" value="expired" />
          </el-select>
        </div>
        <div class="header-right">
          <el-button :loading="loading" @click="loadAll">刷新</el-button>
        </div>
      </div>

      <div class="card-body">
        <el-table :data="list" stripe style="width:100%" v-loading="loading">
          <el-table-column prop="draftId" label="预订草稿编号" min-width="235" show-overflow-tooltip />
          <el-table-column label="用户" width="130">
            <template #default="{ row }">
              <strong>{{ row.nickname || row.username || '-' }}</strong>
              <small class="user-id">ID {{ row.userId }}</small>
            </template>
          </el-table-column>
          <el-table-column prop="destination" label="目的地" width="110">
            <template #default="{ row }">{{ row.destination || '-' }}</template>
          </el-table-column>
          <el-table-column label="预订内容" min-width="160">
            <template #default="{ row }">
              <el-tag
                v-for="type in row.bookingTypes"
                :key="type"
                size="small"
                effect="plain"
                class="type-tag"
              >{{ typeLabel(type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="方案版本" width="105" align="center">
            <template #default="{ row }">V{{ row.planVersion }}</template>
          </el-table-column>
          <el-table-column label="状态" width="105">
            <template #default="{ row }">
              <el-tag :type="statusMeta(row.status).type" effect="light">
                {{ statusMeta(row.status).label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="175">
            <template #default="{ row }">{{ formatTime(row.createTime) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" link @click="viewDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @change="loadData"
        />
      </div>
    </div>

    <el-drawer v-model="drawerVisible" title="预订草稿详情" size="520px">
      <div v-loading="detailLoading">
        <template v-if="selectedBooking">
          <div class="booking-detail-status">
            <el-tag :type="statusMeta(selectedBooking.status).type" size="large">
              {{ statusMeta(selectedBooking.status).label }}
            </el-tag>
            <span>只展示业务信息，不展示确认 Token 等敏感内容</span>
          </div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="草稿编号">{{ selectedBooking.draftId }}</el-descriptions-item>
            <el-descriptions-item label="用户">
              {{ selectedBooking.nickname || selectedBooking.username || '-' }}（ID {{ selectedBooking.userId }}）
            </el-descriptions-item>
            <el-descriptions-item label="目的地">{{ selectedBooking.destination || '-' }}</el-descriptions-item>
            <el-descriptions-item label="会话编号">{{ selectedBooking.conversationId }}</el-descriptions-item>
            <el-descriptions-item label="方案编号">{{ selectedBooking.planId }}</el-descriptions-item>
            <el-descriptions-item label="方案版本">V{{ selectedBooking.planVersion }}</el-descriptions-item>
            <el-descriptions-item label="预订类型">
              {{ selectedBooking.bookingTypes.map(typeLabel).join('、') || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="选项编号">
              <div v-for="optionId in selectedBooking.selectedOptionIds" :key="optionId" class="option-id">
                {{ optionId }}
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatTime(selectedBooking.createTime) }}</el-descriptions-item>
            <el-descriptions-item label="过期时间">{{ formatTime(selectedBooking.expiresAt) }}</el-descriptions-item>
            <el-descriptions-item v-if="selectedBooking.confirmedAt" label="确认时间">
              {{ formatTime(selectedBooking.confirmedAt) }}
            </el-descriptions-item>
            <el-descriptions-item label="最后更新">{{ formatTime(selectedBooking.updateTime) }}</el-descriptions-item>
          </el-descriptions>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchBooking, fetchBookings, fetchBookingStats } from '../api/admin.js'

const loading = ref(false)
const detailLoading = ref(false)
const list = ref([])
const stats = ref({ total: 0, pending: 0, confirmed: 0, cancelled: 0, expired: 0 })
const page = ref(1)
const size = ref(20)
const total = ref(0)
const keyword = ref('')
const status = ref('')
const drawerVisible = ref(false)
const selectedBooking = ref(null)
let searchTimer = null

const statCards = computed(() => [
  { label: '全部草稿', value: '', count: stats.value.total || 0 },
  { label: '待确认', value: 'pending_confirmation', count: stats.value.pending || 0 },
  { label: '已确认', value: 'confirmed', count: stats.value.confirmed || 0 },
  { label: '已取消', value: 'cancelled', count: stats.value.cancelled || 0 },
  { label: '已过期', value: 'expired', count: stats.value.expired || 0 }
])

onMounted(loadAll)

async function loadAll() {
  await Promise.all([loadData(), loadStats()])
}

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, size: size.value }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    if (status.value) params.status = status.value
    const data = await fetchBookings(params)
    list.value = data.records || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(error.message || '加载预订列表失败')
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await fetchBookingStats()
  } catch (error) {
    ElMessage.error(error.message || '加载预订统计失败')
  }
}

function selectStatus(value) {
  status.value = value
  handleFilter()
}

function handleFilter() {
  page.value = 1
  loadData()
}

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadData()
  }, 300)
}

async function viewDetail(row) {
  selectedBooking.value = row
  drawerVisible.value = true
  detailLoading.value = true
  try {
    selectedBooking.value = await fetchBooking(row.draftId)
  } catch (error) {
    ElMessage.error(error.message || '加载预订详情失败')
  } finally {
    detailLoading.value = false
  }
}

function statusMeta(value) {
  return {
    pending_confirmation: { label: '待确认', type: 'warning' },
    confirmed: { label: '已确认', type: 'success' },
    cancelled: { label: '已取消', type: 'info' },
    expired: { label: '已过期', type: 'danger' }
  }[value] || { label: value || '未知', type: 'info' }
}

function typeLabel(value) {
  return {
    hotel: '酒店', train: '火车', flight: '航班', ticket: '门票', transport: '交通'
  }[value] || value
}

function formatTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 19) : '-'
}
</script>

<style scoped>
.booking-admin-page { display: grid; gap: 18px; }
.booking-stats { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.booking-stat-card { border: 1px solid var(--admin-border); border-radius: 14px; padding: 16px 18px; background: #fff; color: var(--admin-text); text-align: left; cursor: pointer; transition: .2s ease; }
.booking-stat-card:hover, .booking-stat-card.active { border-color: var(--admin-primary); box-shadow: 0 8px 24px rgba(31, 94, 68, .1); transform: translateY(-1px); }
.booking-stat-card span { display: block; color: var(--admin-text-muted); font-size: 13px; }
.booking-stat-card strong { display: block; margin-top: 8px; font-size: 26px; color: var(--admin-primary-dark); }
.booking-filters { flex-wrap: wrap; }
.user-id { display: block; margin-top: 2px; color: var(--admin-text-muted); }
.type-tag { margin: 2px 4px 2px 0; }
.booking-detail-status { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
.booking-detail-status span { color: var(--admin-text-muted); font-size: 12px; }
.option-id { padding: 3px 0; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; word-break: break-all; }
@media (max-width: 1100px) { .booking-stats { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
</style>
