<template>
  <div class="page-container">
    <!-- Filter bar -->
    <el-card shadow="never" class="search-card audit-search-card">
      <el-form :model="searchForm" inline class="audit-filter-form">
        <el-form-item label="模块">
          <el-select
            v-model="searchForm.modules"
            placeholder="模块"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            style="width: 160px"
          >
            <el-option
              v-for="item in moduleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select
            v-model="searchForm.actions"
            placeholder="操作类型"
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
        <el-form-item v-if="isSuperAdmin" label="组织">
          <el-select
            v-model="searchForm.orgIds"
            placeholder="组织"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            style="width: 190px"
          >
            <el-option
              v-for="org in orgOptions"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="操作日期起"
            end-placeholder="操作日期止"
            value-format="YYYY-MM-DD"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
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
        <el-table-column v-if="isSuperAdmin" prop="org_name" label="组织" width="160" show-overflow-tooltip>
          <template #default="{ row }">
            {{ getOrgName(row) }}
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
            <p v-if="isSuperAdmin">{{ getOrgName(selectedLog) }}</p>
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

import { ref, reactive, onMounted, computed } from 'vue'
import { getAuditLogList, type AuditLog } from '@/api/audit'
import { formatDateTime } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import { useUserStore } from '@/stores/user'
import { getAllOrganizations, type Organization } from '@/api/organization'
import ActiveFilterTags from '@/components/ActiveFilterTags.vue'
import { usePageRefresh } from '@/composables/pageRefresh'
import type { ActiveFilterTag } from '@/components/activeFilterTags'

const userStore = useUserStore()
const isSuperAdmin = computed(() => userStore.isSuperAdmin)

// Search
const searchForm = reactive({
  modules: [] as string[],
  actions: [] as string[],
  username: '',
  orgIds: [] as number[],
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
const orgOptions = ref<Organization[]>([])

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
  transaction_accounting: '动账资金核算',
  bic_accounting: 'BIC核算',
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
  update_me: '更新资料',
  change_pwd: '修改密码',
  upload: '上传',
  upload_start: '发起上传',
  upload_file: '上传文件',
  task_rerun: '重跑任务',
  import: '导入',
  download: '下载',
  export: '导出',
  view: '查看',
  config_change: '配置变更',
}

const moduleOptions = Object.entries(moduleMap).map(([value, label]) => ({ value, label }))
const actionOptions = Object.entries(actionMap).map(([value, label]) => ({ value, label }))

interface AuditFilterTag extends ActiveFilterTag {
  key: 'modules' | 'actions' | 'username' | 'orgIds' | 'dateRange'
}

const activeFilterTags = computed<AuditFilterTag[]>(() => {
  const tags: AuditFilterTag[] = []
  searchForm.modules.forEach((module) => {
    tags.push({ key: 'modules', label: '模块', value: moduleLabel(module) })
  })
  searchForm.actions.forEach((action) => {
    tags.push({ key: 'actions', label: '操作类型', value: actionLabel(action) })
  })
  if (searchForm.username) {
    tags.push({ key: 'username', label: '操作人', value: searchForm.username })
  }
  searchForm.orgIds.forEach((value) => {
    const org = orgOptions.value.find((item) => item.id === value)
    tags.push({ key: 'orgIds', label: '组织', value: org?.name || `组织#${value}` })
  })
  if (searchForm.dateRange?.length === 2) {
    tags.push({ key: 'dateRange', label: '时间范围', value: `${searchForm.dateRange[0]} 至 ${searchForm.dateRange[1]}` })
  }
  return tags
})

function moduleLabel(val: string): string {
  return moduleMap[val] || val
}

function actionLabel(val: string): string {
  return actionMap[val] || val
}

function getOrgName(row: AuditLog): string {
  if (row.org_name) return row.org_name
  if (!row.org_id) return '-'
  return `组织#${row.org_id}`
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize,
      org_id: searchForm.orgIds.join(',') || undefined,
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
  searchForm.orgIds = []
  searchForm.dateRange = null
  pagination.page = 1
  fetchData()
}

function removeFilterTag(tag: AuditFilterTag) {
  if (tag.key === 'modules') {
    searchForm.modules = searchForm.modules.filter((module) => moduleLabel(module) !== tag.value)
  } else if (tag.key === 'actions') {
    searchForm.actions = searchForm.actions.filter((action) => actionLabel(action) !== tag.value)
  } else if (tag.key === 'username') {
    searchForm.username = ''
  } else if (tag.key === 'orgIds') {
    searchForm.orgIds = searchForm.orgIds.filter((item) => {
      const org = orgOptions.value.find((orgItem) => orgItem.id === item)
      return (org?.name || `组织#${item}`) !== tag.value
    })
  } else if (tag.key === 'dateRange') {
    searchForm.dateRange = null
  }
  handleSearch()
}

function openDetailDrawer(row: AuditLog) {
  selectedLog.value = row
  detailDrawerVisible.value = true
}

async function fetchOrgOptions() {
  if (!isSuperAdmin.value) return
  try {
    orgOptions.value = await getAllOrganizations()
  } catch {
    // Ignore
  }
}

onMounted(async () => {
  await fetchOrgOptions()
  fetchData()
})

usePageRefresh(fetchData)
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
  min-height: calc(100vh - 96px);
}

.audit-search-card {
  margin-bottom: 16px;
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
