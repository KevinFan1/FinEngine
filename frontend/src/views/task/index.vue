<template>
  <div class="page-container">
    <!-- Page header -->
    <div class="page-header">
      <div class="page-header-info">
        <h2 class="page-title">任务列表</h2>
        <p class="page-desc">查看和管理数据处理任务的执行状态</p>
      </div>
      <div class="page-header-actions">
        <el-button type="primary" @click="openUploadDrawer">
          <el-icon><Upload /></el-icon>
          上传文件
        </el-button>
      </div>
    </div>

    <!-- Filter bar -->
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="年月">
          <el-date-picker
            v-model="searchForm.sourceMonth"
            type="month"
            placeholder="全部年月"
            clearable
            value-format="YYYY-MM"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="平台">
          <el-select
            v-model="searchForm.platform"
            placeholder="全部平台"
            clearable
            style="width: 140px"
            @change="handlePlatformChange"
          >
            <el-option v-for="p in platformOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="店铺">
          <el-select
            v-model="searchForm.shopId"
            placeholder="全部店铺"
            clearable
            filterable
            :loading="shopLoading"
            style="width: 180px"
          >
            <el-option
              v-for="shop in filteredShopOptions"
              :key="shop.id"
              :label="shop.shop_name"
              :value="shop.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="性质">
          <el-select v-model="searchForm.parsedType" placeholder="全部性质" clearable style="width: 130px">
            <el-option v-for="t in typeOptions" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 140px">
            <el-option label="排队中" value="queued" />
            <el-option label="运行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.keyword"
            placeholder="文件名/店铺"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">任务列表</span>
          <div class="card-header-actions">
            <el-tag v-if="hasRunningTasks" type="warning" size="small" class="animate-pulse">
              <el-icon><Loading /></el-icon> 有任务运行中，自动刷新中...
            </el-tag>
          </div>
        </div>
      </template>

      <el-table class="task-table" :data="tableData" v-loading="loading" stripe border style="width: 100%">
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="filename" label="文件名" min-width="240" show-overflow-tooltip />
        <el-table-column prop="parsed_type" label="性质" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.parsed_type" size="small" effect="plain">
              {{ typeLabel(row.parsed_type) }}
            </el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="年月" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.parsed_year && row.parsed_month">
              {{ row.parsed_year }}-{{ String(row.parsed_month).padStart(2, '0') }}
            </span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="platform" label="平台" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.platform" size="small" :class="getPlatformTagClass(row.platform)">
              {{ getPlatformLabel(row.platform) }}
            </el-tag>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="店铺" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.shop_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)" size="small" :class="{ 'animate-pulse': row.status === 'running' }">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="160">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress || 0"
              :status="progressStatus(row.status)"
              :stroke-width="10"
            />
          </template>
        </el-table-column>
        <el-table-column label="处理结果" width="130" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'success' || row.status === 'failed'">
              <span v-if="row.result_success !== undefined" class="text-success">成功 {{ row.result_success }}</span>
              <span v-if="row.result_failed !== undefined && row.result_failed > 0" class="text-error"> / 失败 {{ row.result_failed }}</span>
            </template>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="错误原因" min-width="220">
          <template #default="{ row }">
            <el-tooltip
              v-if="taskErrorReason(row)"
              :content="taskErrorReason(row)"
              placement="top"
              effect="dark"
              :show-after="200"
              popper-class="task-error-tooltip"
            >
              <span class="error-reason-text">{{ truncateErrorReason(taskErrorReason(row)) }}</span>
            </el-tooltip>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" class-name="created-time-column">
          <template #default="{ row }">
            <span class="text-tertiary">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center" fixed="right" class-name="task-action-column">
          <template #default="{ row }">
            <div class="task-action-group">
              <el-button type="primary" link @click="openTaskDetail(row)">查看</el-button>
              <el-button
                v-if="row.status === 'failed'"
                type="primary"
                link
                :loading="retryingTaskId === row.id"
                @click="handleRetry(row)"
              >
                重试
              </el-button>
              <el-button
                v-else-if="canRecalculate(row)"
                type="primary"
                link
                :loading="recalculatingTaskId === row.id"
                @click="handleRecalculate(row)"
              >
                重新统计
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无任务数据" :image-size="80" />
        </template>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-area">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="PAGE_SIZE_OPTIONS"
          :layout="PAGINATION_LAYOUT"
          background
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="retryDialogVisible"
      title="重试确认"
      width="420px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
      :close-on-press-escape="retryingTaskId === null"
      :show-close="retryingTaskId === null"
      @closed="handleRetryDialogClosed"
    >
      <p class="retry-dialog-text">
        确定要重试任务「{{ retryTargetLabel }}」吗？
      </p>
      <template #footer>
        <el-button :disabled="retryingTaskId !== null" @click="retryDialogVisible = false">
          取消
        </el-button>
        <el-button type="primary" :loading="retryingTaskId !== null" @click="confirmRetry">
          确定重试
        </el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="uploadDrawerVisible"
      title="上传文件"
      size="720px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <UploadView
        embedded
        @uploaded="handleUploadFinished"
        @view-tasks="closeUploadDrawer"
        @continue-upload="handleContinueUpload"
      />
    </el-drawer>

    <el-drawer
      v-model="taskDetailDrawerVisible"
      title="任务详情"
      size="520px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-if="taskDetail" class="detail-panel">
        <div class="detail-row">
          <span class="detail-label">任务ID</span>
          <strong>{{ taskDetail.id }}</strong>
        </div>
        <div class="detail-row is-block">
          <span class="detail-label">文件名</span>
          <p>{{ taskDetail.filename }}</p>
        </div>
        <div class="detail-row">
          <span class="detail-label">年月</span>
          <span>
            <template v-if="taskDetail.parsed_year && taskDetail.parsed_month">
              {{ taskDetail.parsed_year }}-{{ String(taskDetail.parsed_month).padStart(2, '0') }}
            </template>
            <template v-else>-</template>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">平台</span>
          <el-tag v-if="taskDetail.platform" size="small" :class="getPlatformTagClass(taskDetail.platform)">
            {{ getPlatformLabel(taskDetail.platform) }}
          </el-tag>
          <span v-else>-</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">店铺</span>
          <span>{{ taskDetail.shop_name || '-' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态</span>
          <el-tag :type="statusTagType(taskDetail.status)" size="small">
            {{ statusLabel(taskDetail.status) }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">进度</span>
          <el-progress
            :percentage="taskDetail.progress || 0"
            :status="progressStatus(taskDetail.status)"
            :stroke-width="10"
          />
        </div>
        <div class="detail-row">
          <span class="detail-label">处理结果</span>
          <span>
            成功 {{ taskDetail.result_success ?? 0 }} / 失败 {{ taskDetail.result_failed ?? 0 }}
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间</span>
          <span>{{ formatDateTime(taskDetail.created_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">开始时间</span>
          <span>{{ formatDateTime(taskDetail.started_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">完成时间</span>
          <span>{{ formatDateTime(taskDetail.finished_at) }}</span>
        </div>
        <div v-if="taskErrorReason(taskDetail)" class="detail-row is-block">
          <span class="detail-label">错误原因</span>
          <p class="detail-error">{{ taskErrorReason(taskDetail) }}</p>
        </div>
        <div v-if="taskDetail.result_summary" class="detail-row is-block">
          <span class="detail-label">结果摘要</span>
          <pre>{{ formatJson(taskDetail.result_summary) }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import { getTaskList, retryTask, recalculateTask, type Task } from '@/api/task'
import { getShopList, type Shop } from '@/api/shop'
import { formatDateTime, getPlatformLabel, getPlatformTagClass } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import UploadView from '@/views/upload/index.vue'

// Search
const searchForm = reactive({
  sourceMonth: '',
  platform: '',
  shopId: undefined as number | undefined,
  parsedType: '',
  status: '',
  keyword: '',
})

const platformOptions = [
  { label: '抖音', value: 'douyin' },
  { label: '快手', value: 'kuaishou' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '微信小店', value: 'weixin_video' },
  { label: '天猫', value: 'tmall' },
  { label: '淘宝', value: 'taobao' },
]

const typeOptions = [
  { label: '动账', value: '动账' },
  { label: 'GMV', value: 'gmv' },
  { label: 'BIC', value: 'bic' },
  { label: '运费险', value: '运费险' },
  { label: '订单', value: '订单' },
  { label: '其他服务款', value: '其他服务款' },
]

// Table
const loading = ref(false)
const tableData = ref<Task[]>([])
const shopLoading = ref(false)
const shopOptions = ref<Shop[]>([])
const retryingTaskId = ref<number | null>(null)
const recalculatingTaskId = ref<number | null>(null)
const retryDialogVisible = ref(false)
const retryTarget = ref<Task | null>(null)
const uploadDrawerVisible = ref(false)
const taskDetailDrawerVisible = ref(false)
const taskDetail = ref<Task | null>(null)
const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
})

// Auto-refresh
let refreshTimer: ReturnType<typeof setInterval> | null = null

const hasRunningTasks = computed(() => {
  return tableData.value.some(t => t.status === 'running' || t.status === 'queued')
})

const retryTargetLabel = computed(() => {
  return retryTarget.value?.filename || retryTarget.value?.id || ''
})

const selectedYear = computed(() => {
  if (!searchForm.sourceMonth) return undefined
  const [year] = searchForm.sourceMonth.split('-')
  return Number(year) || undefined
})

const selectedMonth = computed(() => {
  if (!searchForm.sourceMonth) return undefined
  const [, month] = searchForm.sourceMonth.split('-')
  return Number(month) || undefined
})

const filteredShopOptions = computed(() => {
  if (!searchForm.platform) return shopOptions.value
  return shopOptions.value.filter((shop) => shop.platform_name === searchForm.platform)
})

function statusTagType(status: string): string {
  const map: Record<string, string> = {
    queued: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    cancelled: 'info',
  }
  return map[status] || 'info'
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    queued: '排队中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  }
  return map[status] || status
}

function progressStatus(status: string): '' | 'success' | 'exception' | 'warning' {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'exception'
  return ''
}

function typeLabel(type: string) {
  return typeOptions.find((item) => item.value === type)?.label || type
}

function canRecalculate(row: Task) {
  return ['动账', '运费险'].includes(row.parsed_type || '') && !['queued', 'running'].includes(row.status)
}

function taskErrorReason(row: Task) {
  return row.error_reason || row.error_message || formatSummaryErrors(row.result_summary?.errors)
}

function truncateErrorReason(reason: string, maxLength = 36) {
  if (reason.length <= maxLength) return reason
  return `${reason.slice(0, maxLength)}...`
}

function formatSummaryErrors(errors: unknown) {
  if (!errors) return ''
  if (Array.isArray(errors)) return errors.filter(Boolean).map(String).join('；')
  if (typeof errors === 'string') return errors
  return JSON.stringify(errors)
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

function openTaskDetail(row: Task) {
  taskDetail.value = row
  taskDetailDrawerVisible.value = true
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getTaskList({
      page: pagination.page,
      page_size: pagination.pageSize,
      parsed_year: selectedYear.value,
      parsed_month: selectedMonth.value,
      platform: searchForm.platform || undefined,
      shop_id: searchForm.shopId,
      parsed_type: searchForm.parsedType || undefined,
      status: searchForm.status || undefined,
      keyword: searchForm.keyword || undefined,
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function fetchShopOptions() {
  shopLoading.value = true
  try {
    const res = await getShopList({
      page: 1,
      page_size: 100,
      platform_name: searchForm.platform || undefined,
    })
    shopOptions.value = res.items || []
  } catch {
    // Error handled by interceptor
  } finally {
    shopLoading.value = false
  }
}

function handlePlatformChange() {
  if (searchForm.shopId && !filteredShopOptions.value.some((shop) => shop.id === searchForm.shopId)) {
    searchForm.shopId = undefined
  }
  fetchShopOptions()
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  searchForm.sourceMonth = ''
  searchForm.platform = ''
  searchForm.shopId = undefined
  searchForm.parsedType = ''
  searchForm.status = ''
  searchForm.keyword = ''
  pagination.page = 1
  fetchShopOptions()
  fetchData()
}

function openUploadDrawer() {
  uploadDrawerVisible.value = true
  stopAutoRefresh()
}

async function closeUploadDrawer() {
  uploadDrawerVisible.value = false
  await fetchData()
  startAutoRefresh()
}

async function handleUploadFinished() {
  await fetchData()
}

function handleContinueUpload() {
  fetchData()
}

async function handleRetry(row: Task) {
  retryTarget.value = row
  retryDialogVisible.value = true
  stopAutoRefresh()
}

function handleRetryDialogClosed() {
  retryTarget.value = null
  if (retryingTaskId.value === null) {
    startAutoRefresh()
  }
}

async function confirmRetry() {
  if (!retryTarget.value || retryingTaskId.value !== null) return

  const taskId = retryTarget.value.id
  retryingTaskId.value = taskId
  try {
    await retryTask(taskId)
    ElMessage.success('已重新提交任务')
    retryDialogVisible.value = false
    await fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    retryingTaskId.value = null
    startAutoRefresh()
  }
}

async function handleRecalculate(row: Task) {
  recalculatingTaskId.value = row.id
  stopAutoRefresh()
  try {
    await recalculateTask(row.id)
    ElMessage.success('已重新提交统计任务')
    await fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    recalculatingTaskId.value = null
    startAutoRefresh()
  }
}

function startAutoRefresh() {
  stopAutoRefresh()
  refreshTimer = setInterval(() => {
    if (hasRunningTasks.value) {
      fetchData()
    }
  }, 5000)
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  fetchShopOptions()
  fetchData()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
}

.page-header {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  .page-desc {
    font-size: 13px;
    color: var(--text-tertiary);
  }

  .page-header-actions {
    flex-shrink: 0;
  }
}

.table-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    &-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    &-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }
}

.task-action-group {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
  white-space: nowrap;

  :deep(.el-button) {
    margin-left: 0;
  }
}

:deep(.task-table .created-time-column .cell) {
  white-space: nowrap;
  word-break: keep-all;
}

:deep(.task-table .task-action-column .cell) {
  padding-left: 8px;
  padding-right: 8px;
}

.retry-dialog-text {
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.7;
  margin: 0;
  word-break: break-all;
}

.error-reason-text {
  display: inline-block;
  max-width: 100%;
  color: var(--danger);
  line-height: 1.4;
  cursor: default;
  vertical-align: middle;
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-row {
  display: grid;
  grid-template-columns: 86px 1fr;
  gap: 12px;
  align-items: center;
  color: var(--text-primary);
  line-height: 1.7;

  &.is-block {
    align-items: flex-start;
  }

  p {
    margin: 0;
    color: var(--text-secondary);
    word-break: break-word;
  }

  pre {
    margin: 0;
    max-height: 260px;
    overflow: auto;
    border: 1px solid var(--border-light);
    border-radius: 6px;
    background: var(--code-bg);
    color: var(--code-text);
    padding: 10px;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.detail-label {
  color: var(--text-tertiary);
  font-size: 13px;
}

.detail-error {
  color: var(--danger) !important;
}
</style>

<style lang="scss">
.task-error-tooltip {
  max-width: 520px;
  white-space: normal;
  word-break: break-all;
  line-height: 1.6;
}
</style>
