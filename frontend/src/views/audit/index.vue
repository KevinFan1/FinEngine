<template>
  <div class="page-container">
    <!-- Filter bar -->
    <el-card shadow="never" class="search-card audit-search-card">
      <div class="search-card-head">
        <div>
          <p class="search-card-kicker">AUDIT TRAIL</p>
          <h2 class="search-card-title">先定位操作，再查看日志详情</h2>
        </div>
        <div class="search-card-tip">
          支持按模块、操作类型、操作人和时间范围快速筛选
        </div>
      </div>

      <el-form :model="searchForm" inline class="audit-filter-form">
        <el-form-item label="模块">
          <el-select
            v-model="searchForm.modules"
            placeholder="全部模块"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            style="width: 160px"
          >
            <el-option label="认证" value="auth" />
            <el-option label="组织" value="org" />
            <el-option label="用户" value="user" />
            <el-option label="上传" value="upload" />
            <el-option label="任务" value="task" />
            <el-option label="汇总" value="summary" />
            <el-option label="导出" value="export" />
            <el-option label="系统" value="system" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select
            v-model="searchForm.actions"
            placeholder="全部类型"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            style="width: 160px"
          >
            <el-option
              v-for="item in actionOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作人">
          <el-input
            v-model="searchForm.username"
            placeholder="操作人"
            clearable
            style="width: 140px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 260px"
          />
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
          <div class="audit-title-group">
            <span class="card-header-title">操作日志</span>
            <span class="audit-count">共 {{ pagination.total }} 条</span>
          </div>
        </div>
      </template>

      <el-table
        class="summary-table roomy-table"
        :data="tableData"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        height="calc(100vh - 278px)"
      >
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            <span class="text-tertiary">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="username" label="操作人" width="130" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.display_name || row.username }}
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="90" align="center">
          <template #default="{ row }">
            <el-tag class="audit-type-pill" size="small">{{ moduleLabel(row.module) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-tag class="audit-type-pill" size="small">{{ actionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="280" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="140">
          <template #default="{ row }">{{ row.ip || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetailDrawer(row)">查看</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无操作日志" :image-size="80" />
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

    <el-drawer
      v-model="detailDrawerVisible"
      title="日志详情"
      size="540px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-if="selectedLog" class="detail-panel">
        <section class="detail-hero-card">
          <div>
            <span class="detail-kicker">{{ formatDateTime(selectedLog.created_at) }}</span>
            <h3>{{ selectedLog.display_name || selectedLog.username || '-' }}</h3>
            <p>{{ selectedLog.ip || selectedLog.ip_address || '-' }}</p>
          </div>
          <div class="detail-badge-row">
            <el-tag class="audit-type-pill" size="small">{{ moduleLabel(selectedLog.module) }}</el-tag>
            <el-tag class="audit-type-pill" size="small">{{ actionLabel(selectedLog.action) }}</el-tag>
            <el-tag :type="selectedLog.status === 'success' ? 'success' : 'danger'" size="small">
              {{ selectedLog.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>描述</span>
          </div>
          <p class="detail-note">{{ selectedLog.description || '-' }}</p>
        </section>

        <section v-if="selectedLog.error_msg" class="detail-card detail-card--danger">
          <div class="detail-card-header">
            <span>错误信息</span>
          </div>
          <p class="detail-error">{{ selectedLog.error_msg }}</p>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>User Agent</span>
          </div>
          <p class="detail-note">{{ selectedLog.user_agent || '-' }}</p>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'AuditLogs' })

import { ref, reactive, onMounted } from 'vue'
import { getAuditLogList, type AuditLog } from '@/api/audit'
import { formatDateTime } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'

// Search
const searchForm = reactive({
  modules: [] as string[],
  actions: [] as string[],
  username: '',
  dateRange: null as [string, string] | null,
})

// Table
const loading = ref(false)
const tableData = ref<AuditLog[]>([])
const detailDrawerVisible = ref(false)
const selectedLog = ref<AuditLog | null>(null)
const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
})

const moduleMap: Record<string, string> = {
  auth: '认证',
  org: '组织',
  user: '用户',
  shop: '店铺',
  upload: '上传',
  task: '任务',
  summary: '汇总',
  export: '导出',
  platform: '平台',
  category_dict: '分类字典',
  system: '系统',
  summary_adjustment: '汇总调整',
}

const actionMap: Record<string, string> = {
  login: '登录',
  logout: '退出',
  create: '创建',
  update: '更新',
  delete: '删除',
  enable: '启用',
  disable: '禁用',
  reset_pwd: '重置密码',
  upload: '上传',
  upload_start: '发起上传',
  upload_file: '上传文件',
  download: '下载',
  export: '导出',
  view: '查看',
  config_change: '配置变更',
}

const actionOptions = Object.entries(actionMap).map(([value, label]) => ({ value, label }))

function moduleLabel(val: string): string {
  return moduleMap[val] || val
}

function actionLabel(val: string): string {
  return actionMap[val] || val
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize,
      module: searchForm.modules.join(',') || undefined,
      action: searchForm.actions.join(',') || undefined,
      username: searchForm.username || undefined,
    }
    if (searchForm.dateRange && searchForm.dateRange.length === 2) {
      params.start_time = searchForm.dateRange[0]
      params.end_time = searchForm.dateRange[1]
    }
    const res = await getAuditLogList(params as any)
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  searchForm.modules = []
  searchForm.actions = []
  searchForm.username = ''
  searchForm.dateRange = null
  pagination.page = 1
  fetchData()
}

function openDetailDrawer(row: AuditLog) {
  selectedLog.value = row
  detailDrawerVisible.value = true
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
  min-height: calc(100vh - 96px);
}

.audit-search-card {
  margin-bottom: 16px;
}

.search-card-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.search-card-kicker {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.search-card-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 700;
  line-height: 1.2;
}

.search-card-tip {
  display: flex;
  align-items: center;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.audit-filter-form {
  row-gap: 6px;
}

.table-card {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;

    &-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }
}

.audit-title-group {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}

.audit-count {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.audit-type-pill {
  min-width: 52px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px !important;
  color: var(--el-color-primary) !important;
  background: var(--el-color-primary-light-9) !important;
  border: 1px solid var(--el-color-primary-light-7) !important;
  font-size: 12px;
  font-weight: 600;
  line-height: 22px;
}

@media (max-width: 768px) {
  .search-card-head {
    flex-direction: column;
  }
}

.detail-panel {
  display: grid;
  gap: 12px;
}

.detail-hero-card,
.detail-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-card);
  background: var(--bg-card);
}

.detail-hero-card {
  display: grid;
  gap: 12px;
  padding: 14px;

  h3 {
    margin: 4px 0;
    color: var(--text-primary);
    font-size: 17px;
    font-weight: 700;
    line-height: 1.4;
  }

  p {
    margin: 0;
    color: var(--text-secondary);
    word-break: break-word;
  }
}

.detail-kicker {
  color: var(--text-tertiary);
  font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
  font-size: 11px;
  font-weight: 700;
}

.detail-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-card {
  display: grid;
  gap: 12px;
  padding: 14px;
}

.detail-card--danger {
  border-color: var(--error);
  background: var(--error-light);
}

.detail-card-header {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.detail-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.detail-error {
  margin: 0;
  color: var(--danger) !important;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}
</style>
