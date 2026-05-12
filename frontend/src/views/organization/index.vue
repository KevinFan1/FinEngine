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
      size="480px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-if="drawerMode === 'detail' && selectedOrg" class="detail-panel">
        <div class="detail-row">
          <span class="detail-label">组织名称</span>
          <strong>{{ selectedOrg.name }}</strong>
        </div>
        <div class="detail-row">
          <span class="detail-label">组织编码</span>
          <span>{{ selectedOrg.code }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">状态</span>
          <el-tag :type="isActive(selectedOrg) ? 'success' : 'danger'" size="small">
            {{ isActive(selectedOrg) ? '启用' : '禁用' }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="detail-label">创建时间</span>
          <span>{{ formatDateTime(selectedOrg.created_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">更新时间</span>
          <span>{{ formatDateTime(selectedOrg.updated_at) }}</span>
        </div>
        <div class="detail-row is-block">
          <span class="detail-label">备注</span>
          <p>{{ selectedOrg.remark || '-' }}</p>
        </div>
      </div>
      <el-form
        v-else
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="90px"
      >
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
import type { FormInstance, FormRules } from 'element-plus/es/components/form/index.mjs'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import { ElMessageBox } from 'element-plus/es/components/message-box/index.mjs'
import {
  getOrganizationList,
  createOrganization,
  updateOrganization,
  toggleOrganizationStatus,
  type Organization,
} from '@/api/organization'
import { formatDateTime } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'

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
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入组织名称', trigger: 'blur' },
    { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入组织编码', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '只能包含字母、数字、下划线和横线', trigger: 'blur' },
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
      name: searchForm.keyword || undefined,
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

function openFormDrawer(row?: Organization) {
  drawerMode.value = row ? 'edit' : 'create'
  selectedOrg.value = row || null
  if (row) {
    isEdit.value = true
    editId.value = row.id
    formData.name = row.name
    formData.code = row.code
    formData.remark = row.remark || ''
  } else {
    isEdit.value = false
    editId.value = null
    formData.name = ''
    formData.code = ''
    formData.remark = ''
  }
  drawerVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      await updateOrganization(editId.value, {
        name: formData.name,
        code: formData.code,
        remark: formData.remark,
      })
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

.detail-row {
  display: grid;
  grid-template-columns: 90px 1fr;
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
</style>
