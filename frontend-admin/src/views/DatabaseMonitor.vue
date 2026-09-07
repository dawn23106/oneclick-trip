<template>
  <div class="database-page">
    <el-alert
      v-if="snapshot.available === false"
      type="warning"
      :closable="false"
      show-icon
      :title="snapshot.message || '数据库性能统计暂不可用'"
    />

    <section class="metric-strip">
      <div class="metric-item">
        <span>累计 SQL 执行</span>
        <strong>{{ number(summary.totalExecutions) }}</strong>
        <small>performance_schema 聚合值</small>
      </div>
      <div class="metric-item">
        <span>累计数据库耗时</span>
        <strong>{{ duration(summary.totalTimeMs) }}</strong>
        <small>所有语句执行时间之和</small>
      </div>
      <div class="metric-item" :class="{ warning: summary.riskyDigestCount }">
        <span>高风险语句类型</span>
        <strong>{{ number(summary.riskyDigestCount) }}</strong>
        <small>最大耗时 ≥ {{ snapshot.slowThresholdMs || 1000 }} ms</small>
      </div>
      <div class="metric-item" :class="{ alert: summary.noIndexExecutions }">
        <span>未使用索引次数</span>
        <strong>{{ number(summary.noIndexExecutions) }}</strong>
        <small>需要结合扫描行数判断</small>
      </div>
      <div class="metric-item" :class="{ warning: summary.diskTempTables }">
        <span>磁盘临时表</span>
        <strong>{{ number(summary.diskTempTables) }}</strong>
        <small>排序与分组优化线索</small>
      </div>
    </section>

    <div class="table-card">
      <div class="card-header monitor-header">
        <div>
          <h3>SQL 性能摘要</h3>
          <p>仅展示参数脱敏后的 SQL 模板；按聚合指标定位高耗时、全表扫描和深分页风险。</p>
        </div>
        <div class="actions">
          <el-select v-model="order" style="width: 150px" @change="load">
            <el-option label="累计耗时" value="total" />
            <el-option label="平均耗时" value="average" />
            <el-option label="最大耗时" value="maximum" />
            <el-option label="扫描行数" value="rows" />
          </el-select>
          <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        </div>
      </div>

      <div class="card-body">
        <el-table :data="snapshot.queries || []" stripe v-loading="loading">
          <el-table-column label="状态" width="84">
            <template #default="{ row }">
              <el-tag :type="row.slow ? 'danger' : riskType(row)" effect="plain" size="small">
                {{ row.slow ? '慢 SQL' : riskType(row) === 'warning' ? '关注' : '正常' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="SQL 模板" min-width="380">
            <template #default="{ row }">
              <code class="sql-template">{{ row.sqlTemplate }}</code>
              <div class="digest">{{ row.digest }}</div>
            </template>
          </el-table-column>
          <el-table-column label="执行次数" width="100" align="right">
            <template #default="{ row }">{{ number(row.executions) }}</template>
          </el-table-column>
          <el-table-column label="平均耗时" width="110" align="right">
            <template #default="{ row }">{{ duration(row.averageTimeMs) }}</template>
          </el-table-column>
          <el-table-column label="最大耗时" width="110" align="right">
            <template #default="{ row }"><strong>{{ duration(row.maximumTimeMs) }}</strong></template>
          </el-table-column>
          <el-table-column label="扫描 / 返回" width="130" align="right">
            <template #default="{ row }">{{ number(row.rowsExamined) }} / {{ number(row.rowsSent) }}</template>
          </el-table-column>
          <el-table-column label="索引 / 临时表" width="135" align="right">
            <template #default="{ row }">{{ number(row.noIndexExecutions) }} / {{ number(row.diskTempTables) }}</template>
          </el-table-column>
          <el-table-column label="最后出现" width="170">
            <template #default="{ row }">{{ dateTime(row.lastSeen) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty description="暂无 SQL 性能摘要；运行部分业务后再刷新" />
          </template>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { fetchDatabaseMonitor } from '../api/admin.js'

const loading = ref(false)
const order = ref('total')
const snapshot = ref({ available: true, slowThresholdMs: 1000, summary: {}, queries: [] })
const summary = computed(() => snapshot.value.summary || {})

onMounted(load)

async function load() {
  loading.value = true
  try {
    snapshot.value = await fetchDatabaseMonitor({ limit: 30, order: order.value })
  } catch (error) {
    ElMessage.error(error.message || '加载数据库性能信息失败')
  } finally {
    loading.value = false
  }
}

function number(value) {
  return new Intl.NumberFormat('zh-CN').format(Number(value) || 0)
}

function duration(value) {
  const ms = Number(value) || 0
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${ms.toFixed(ms < 10 ? 2 : 0)} ms`
}

function dateTime(value) {
  return value ? String(value).replace('T', ' ') : '-'
}

function riskType(row) {
  return row.noIndexExecutions > 0 || row.diskTempTables > 0 ? 'warning' : 'success'
}
</script>

<style scoped>
.database-page { display: grid; gap: 20px; }
.metric-strip { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); background: #fff; border: 1px solid var(--admin-border); border-radius: 14px; overflow: hidden; }
.metric-item { display: grid; gap: 6px; padding: 20px; border-right: 1px solid var(--admin-border); }
.metric-item:last-child { border-right: 0; }
.metric-item span, .metric-item small { color: var(--admin-text-muted); }
.metric-item strong { color: var(--admin-text); font-size: 26px; }
.metric-item.warning strong { color: #d48806; }
.metric-item.alert strong { color: #d4380d; }
.monitor-header, .actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.monitor-header p { margin: 6px 0 0; color: var(--admin-text-muted); }
.sql-template { display: block; max-width: 680px; color: #17345c; white-space: normal; overflow-wrap: anywhere; line-height: 1.55; }
.digest { margin-top: 5px; color: var(--admin-text-muted); font-size: 11px; font-family: monospace; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 1200px) { .metric-strip { grid-template-columns: repeat(2, 1fr); } .metric-item { border-bottom: 1px solid var(--admin-border); } }
</style>
