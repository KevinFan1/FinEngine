<template>
  <div class="page-container">
    <!-- Search bar -->
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="组织名称">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索组织名称或编码"
            clearable
            style="width: 240px"
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

    <!-- Table area -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">组织列表</span>
          <el-button type="primary" @click="openFormDrawer()">
            <el-icon><Plus /></el-icon> 新增组织
          </el-button>
        </div>
      </template>

      <el-table
        class="summary-table"
        :data="tableData"
        v-loading="loading"
        stripe
        border
        style="width: 100%"
        max-height="calc(100vh - 286px)"
      >
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="code" label="编码" width="140" show-overflow-tooltip />
        <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="text-tertiary">{{ row.remark || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="isActive(row) ? 'success' : 'danger'" size="small">
              {{ isActive(row) ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetailDrawer(row)">查看</el-button>
            <el-button type="primary" link @click="openFormDrawer(row)">编辑</el-button>
            <el-button
              :type="isActive(row) ? 'danger' : 'success'"
              link
              @click="handleToggleStatus(row)"
            >
              {{ isActive(row) ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无组织数据" :image-size="80" />
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
      v-model="drawerVisible"
      :title="drawerTitle"
      :size="drawerMode === 'detail' ? '600px' : '480px'"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-if="drawerMode === 'detail' && selectedOrg" class="detail-panel">
        <section class="detail-hero-card">
          <div>
            <span class="detail-kicker">ORG #{{ selectedOrg.id }}</span>
            <h3>{{ selectedOrg.name }}</h3>
            <p>{{ selectedOrg.code }}</p>
          </div>
          <div class="detail-badge-row">
            <el-tag :type="isActive(selectedOrg) ? 'success' : 'danger'" size="small">
              {{ isActive(selectedOrg) ? '启用' : '禁用' }}
            </el-tag>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>基础信息</span>
          </div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">组织编码</span>
              <strong>{{ selectedOrg.code }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <strong>{{ formatDateTime(selectedOrg.created_at) }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">更新时间</span>
              <strong>{{ formatDateTime(selectedOrg.updated_at) }}</strong>
            </div>
            <div class="detail-item detail-item--wide" v-if="selectedOrg.remark">
              <span class="detail-label">备注</span>
              <p>{{ selectedOrg.remark }}</p>
            </div>
          </div>
        </section>

        <!-- 配额管理 -->
        <QuotaManagement
          :org-id="selectedOrg.id"
          :is-super-admin="userStore.isSuperAdmin"
        />
      </div>
      <el-form
        v-else
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-divider content-position="left">基础信息</el-divider>
        <el-form-item label="组织名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入组织名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="组织编码" prop="code">
          <el-input
            v-model="formData.code"
            placeholder="请输入组织编码"
            :disabled="isEdit"
            maxlength="50"
          />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input
            v-model="formData.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入备注（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <!-- 配额设置（仅编辑时显示，且仅超级管理员可见） -->
        <template v-if="isEdit && userStore.isSuperAdmin">
          <el-divider content-position="left">配额设置</el-divider>
          <el-form-item label="套餐类型" prop="plan_type">
            <el-select v-model="formData.plan_type" placeholder="请选择套餐类型">
              <el-option label="免费版" value="free" />
              <el-option label="基础版" value="basic" />
              <el-option label="专业版" value="professional" />
              <el-option label="企业版" value="enterprise" />
            </el-select>
          </el-form-item>
          <el-form-item label="到期时间" prop="plan_expires_at">
            <el-date-picker
              v-model="formData.plan_expires_at"
              type="datetime"
              placeholder="选择到期时间"
              format="YYYY-MM-DD HH:mm:ss"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="最大用户数" prop="max_users">
            <el-input-number
              v-model="formData.max_users"
              :min="1"
              :max="10000"
              :step="1"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="每月上传额度(GB)" prop="max_storage_gb">
            <el-input-number
              v-model="formData.max_storage_gb"
              :min="0.01"
              :max="10000"
              :step="0.1"
              :precision="2"
              style="width: 100%"
            />
          </el-form-item>
        </template>
      </el-form>
      <div v-if="drawerMode !== 'detail'" class="drawer-footer">
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">
          确定
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'Organizations' })

import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  getOrganizationList,
  createOrganization,
  updateOrganization,
  toggleOrganizationStatus,
  type Organization,
} from '@/api/organization'
import { getOrgQuota, updateQuota } from '@/api/quota'
import { formatDateTime } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import { useUserStore } from '@/stores/user'
import QuotaManagement from '@/components/QuotaManagement.vue'

const userStore = useUserStore()

// Search
const searchForm = reactive({
  keyword: '',
})

// Table
const loading = ref(false)
const tableData = ref<Organization[]>([])
const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
})

// Drawer
const drawerVisible = ref(false)
const drawerMode = ref<'create' | 'edit' | 'detail'>('create')
const isEdit = ref(false)
const editId = ref<number | null>(null)
const selectedOrg = ref<Organization | null>(null)
const formRef = ref<FormInstance>()
const submitLoading = ref(false)

const formData = reactive({
  name: '',
  code: '',
  remark: '',
  // 配额字段（仅编辑时使用）
  plan_type: 'free',
  plan_expires_at: null as Date | string | null,
  max_users: 5,
  max_storage_gb: 1,
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入组织名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入组织编码', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '只能包含字母、数字、下划线和横线', trigger: 'blur' },
  ],
  remark: [
    { max: 2000, message: '备注最多 2000 个字符', trigger: 'blur' },
  ],
}

const drawerTitle = computed(() => {
  if (drawerMode.value === 'detail') return '组织详情'
  return isEdit.value ? '编辑组织' : '新增组织'
})

function isActive(row: Organization): boolean {
  return row.status === '1' || row.status === 1 || row.status === 'active'
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getOrganizationList({
      page: pagination.page,
      page_size: pagination.pageSize,
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

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  searchForm.keyword = ''
  pagination.page = 1
  fetchData()
}

function openDetailDrawer(row: Organization) {
  drawerMode.value = 'detail'
  selectedOrg.value = row
  drawerVisible.value = true
}

async function openFormDrawer(row?: Organization) {
  drawerMode.value = row ? 'edit' : 'create'
  selectedOrg.value = row || null
  if (row) {
    isEdit.value = true
    editId.value = row.id
    formData.name = row.name
    formData.code = row.code
    formData.remark = row.remark || ''

    // 加载配额数据（仅超级管理员）
    if (userStore.isSuperAdmin) {
      try {
        const quotaInfo = await getOrgQuota(row.id)
        formData.plan_type = quotaInfo.plan_type
        formData.plan_expires_at = quotaInfo.plan_expires_at
          ? new Date(quotaInfo.plan_expires_at)
          : null
        formData.max_users = quotaInfo.users.max
        formData.max_storage_gb = quotaInfo.storage.max_gb
      } catch (error) {
        console.error('加载配额信息失败:', error)
      }
    }
  } else {
    isEdit.value = false
    editId.value = null
    formData.name = ''
    formData.code = ''
    formData.remark = ''
    formData.plan_type = 'free'
    formData.plan_expires_at = null
    formData.max_users = 5
    formData.max_storage_gb = 1
  }
  drawerVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      // 更新组织基本信息
      await updateOrganization(editId.value, {
        name: formData.name,
        code: formData.code,
        remark: formData.remark,
      })

      // 更新配额信息（仅超级管理员）
      if (userStore.isSuperAdmin) {
        await updateQuota(editId.value, {
          plan_type: formData.plan_type,
          plan_expires_at: formData.plan_expires_at
            ? new Date(formData.plan_expires_at).toISOString()
            : null,
          max_users: formData.max_users,
          max_storage_gb: formData.max_storage_gb,
        })
      }

      ElMessage.success('更新成功')
    } else {
      await createOrganization({
        name: formData.name,
        code: formData.code,
        remark: formData.remark,
      })
      ElMessage.success('创建成功')
    }
    drawerVisible.value = false
    fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    submitLoading.value = false
  }
}

async function handleToggleStatus(row: Organization) {
  const active = isActive(row)
  const action = active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}组织「${row.name}」吗？`,
      '操作确认',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    await toggleOrganizationStatus(row.id, active ? '0' : '1')
    ElMessage.success(`${action}成功`)
    fetchData()
  } catch {
    // Cancelled or error
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
.page-container {
  width: 100%;
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
  }
}

.drawer-footer {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin: 24px -20px -20px;
  padding: 14px 20px;
  background: var(--bg-elevated);
  border-top: 1px solid var(--border-light);
}

.detail-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
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
    font-family: 'SF Mono', SFMono-Regular, Consolas, monospace;
    font-size: 12px;
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

.detail-card-header {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-item {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--border-color-light);
  border-radius: calc(var(--radius-card) - 2px);
  background: var(--bg-elevated);

  strong {
    overflow: hidden;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  p {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
    word-break: break-word;
  }
}

.detail-item--wide {
  grid-column: 1 / -1;
}

.detail-label {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 600;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
