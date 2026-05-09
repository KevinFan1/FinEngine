<template>
  <div class="page-container">
    <!-- Page header -->
    <div class="page-header">
      <div class="page-header-info">
        <h2 class="page-title">操作日志</h2>
        <p class="page-desc">查看系统操作记录，用于审计和问题追踪</p>
      </div>
    </div>

    <!-- Filter bar -->
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="模块">
          <el-select v-model="searchForm.module" placeholder="全部模块" clearable style="width: 130px">
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
          <el-select v-model="searchForm.action" placeholder="全部类型" clearable style="width: 130px">
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
        <span class="card-header-title">操作日志</span>
      </template>

      <el-table :data="tableData" v-loading="loading" stripe border style="width: 100%">
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
            <el-tag type="info" size="small">{{ moduleLabel(row.module) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ actionLabel(row.action) }}</el-tag>
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
        <div class="detail-row">
          <span class="detail-label">时间</span>
          <span>{{ formatDateTime(selectedLog.created_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">操作人</span>
          <strong>{{ selectedLog.display_name || selectedLog.username || '-' }}</strong>
        </div>
        <div class="detail-row">
          <span class="detail-label">模块</span>
          <el-tag type="info" size="small">{{ moduleLabel(selectedLog.module) }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">操作</span>
          <el-tag size="small">{{ actionLabel(selectedLog.action) }}</el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态</span>
          <el-tag :type="selectedLog.status === 'success' ? 'success' : 'danger'" size="small">
            {{ selectedLog.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">IP</span>
          <span>{{ selectedLog.ip || selectedLog.ip_address || '-' }}</span>
        </div>
        <div class="detail-row is-block">
          <span class="detail-label">描述</span>
          <p>{{ selectedLog.description || '-' }}</p>
        </div>
        <div v-if="selectedLog.error_msg" class="detail-row is-block">
          <span class="detail-label">错误信息</span>
          <p class="detail-error">{{ selectedLog.error_msg }}</p>
        </div>
        <div class="detail-row is-block">
          <span class="detail-label">User Agent</span>
          <p>{{ selectedLog.user_agent || '-' }}</p>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getAuditLogList, type AuditLog } from '@/api/audit'
import { formatDateTime } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'

// Search
const searchForm = reactive({
  module: '',
  action: '',
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
      module: searchForm.module || undefined,
      action: searchForm.action || undefined,
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
  searchForm.module = ''
  searchForm.action = ''
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
}

.page-header {
  margin-bottom: 16px;

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
}

.table-card {
  .card-header-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }
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
}

.detail-label {
  color: var(--text-tertiary);
  font-size: 13px;
}

.detail-error {
  color: var(--danger) !important;
}
</style>
