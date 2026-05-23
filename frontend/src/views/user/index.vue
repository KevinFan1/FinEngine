<template>
  <div class="page-container">
    <!-- Search bar -->
    <el-card shadow="never" class="search-card">
      <SearchCardIntro
        kicker="用户工作台"
        title="先筛选用户，再查看或维护账号"
        tip="支持按姓名、手机号和组织快速定位用户"
      />
      <el-form :model="searchForm" inline>
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.keyword"
            placeholder="姓名/手机号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="userStore.isSuperAdmin" label="组织">
          <el-select
            v-model="searchForm.orgIds"
            placeholder="全部组织"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            style="width: 220px"
          >
            <el-option
              v-for="org in orgOptions"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
    </el-card>

    <!-- Table area -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-header-title">用户列表</span>
          <el-button type="primary" @click="openUserDrawer()">
            <el-icon><Plus /></el-icon> 新增用户
          </el-button>
        </div>
      </template>

      <el-table class="summary-table roomy-table user-table" :data="tableData" v-loading="loading" stripe border style="width: 100%" height="calc(100vh - 278px)">
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="display_name" label="姓名" min-width="170" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="180" />
        <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="所属组织" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.org_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="130" align="center">
          <template #default="{ row }">
            <el-tag :type="roleTagMap[row.role] || 'info'" size="small">
              {{ getRoleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="isActive(row) ? 'success' : 'danger'" size="small">
              {{ isActive(row) ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最后登录" min-width="220">
          <template #default="{ row }">
            <span class="text-tertiary">{{ formatDateTime(row.last_login_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openUserDetailDrawer(row)">查看</el-button>
            <el-button type="primary" link @click="openUserDrawer(row)">编辑</el-button>
            <el-button type="warning" link @click="openResetPwdDrawer(row)">重置密码</el-button>
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
          <el-empty description="暂无用户数据" :image-size="80" />
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
      v-model="userDrawerVisible"
      :title="drawerTitle"
      size="560px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
    >
      <div v-if="drawerMode === 'detail' && selectedUser" class="detail-panel">
        <section class="detail-hero-card">
          <div>
            <span class="detail-kicker">USER #{{ selectedUser.id }}</span>
            <h3>{{ selectedUser.display_name || selectedUser.username }}</h3>
            <p>{{ selectedUser.username }}</p>
          </div>
          <div class="detail-badge-row">
            <el-tag :type="roleTagMap[selectedUser.role] || 'info'" size="small">
              {{ getRoleLabel(selectedUser.role) }}
            </el-tag>
            <el-tag :type="isActive(selectedUser) ? 'success' : 'danger'" size="small">
              {{ isActive(selectedUser) ? '启用' : '禁用' }}
            </el-tag>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>基础信息</span>
          </div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">手机号</span>
              <strong>{{ selectedUser.phone }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">邮箱</span>
              <strong>{{ selectedUser.email || '-' }}</strong>
            </div>
            <div v-if="userStore.isSuperAdmin" class="detail-item detail-item--wide">
              <span class="detail-label">所属组织</span>
              <strong>{{ selectedUser.org_name || '-' }}</strong>
            </div>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>时间信息</span>
          </div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">最后登录</span>
              <strong>{{ formatDateTime(selectedUser.last_login_at) }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <strong>{{ formatDateTime(selectedUser.created_at) }}</strong>
            </div>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>当前登录设备</span>
          </div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">登录时间</span>
              <strong>{{ formatDateTime(selectedUser.active_session_at) }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">登录 IP</span>
              <strong>{{ selectedUser.active_session_ip || '-' }}</strong>
            </div>
            <div class="detail-item detail-item--wide">
              <span class="detail-label">客户端</span>
              <strong>{{ selectedUser.active_session_user_agent || '-' }}</strong>
            </div>
          </div>
        </section>
      </div>
      <el-form
        v-else-if="drawerMode === 'reset'"
        ref="resetPwdFormRef"
        :model="resetPwdForm"
        :rules="resetPwdRules"
        label-width="90px"
      >
        <el-form-item label="用户">
          <span>{{ selectedUser?.display_name || selectedUser?.username || '-' }}</span>
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="resetPwdForm.password"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="resetPwdForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <el-form
        v-else
        ref="userFormRef"
        :model="userFormData"
        :rules="userFormRules"
        label-width="90px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="userFormData.username"
            placeholder="请输入用户名"
            :disabled="isEdit"
          />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="userFormData.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input
            v-model="userFormData.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="userFormData.display_name" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userFormData.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userFormData.role" placeholder="请选择角色" style="width: 100%">
            <el-option
              v-for="r in availableRoles"
              :key="r.value"
              :label="r.label"
              :value="r.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="userStore.isSuperAdmin" label="所属组织" prop="org_id">
          <el-select
            v-model="userFormData.org_id"
            placeholder="请选择组织"
            style="width: 100%"
            :disabled="!userStore.isSuperAdmin"
            clearable
          >
            <el-option
              v-for="org in orgOptions"
              :key="org.id"
              :label="org.name"
              :value="org.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="drawerMode !== 'detail'" class="drawer-footer">
        <el-button @click="userDrawerVisible = false">取消</el-button>
        <el-button
          v-if="drawerMode === 'reset'"
          type="primary"
          :loading="resetPwdLoading"
          @click="handleResetPwd"
        >
          确定
        </el-button>
        <el-button v-else type="primary" :loading="submitLoading" @click="handleUserSubmit">
          确定
        </el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'Users' })

import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  getUserList,
  createUser,
  updateUser,
  resetUserPassword,
  toggleUserStatus,
  type User,
  type UserForm,
} from '@/api/user'
import { getAllOrganizations, type Organization } from '@/api/organization'
import { formatDateTime, getRoleLabel } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import ActiveFilterTags from '@/components/ActiveFilterTags.vue'
import SearchCardIntro from '@/components/SearchCardIntro.vue'
import { usePageRefresh } from '@/composables/pageRefresh'
import type { ActiveFilterTag } from '@/components/activeFilterTags'

const userStore = useUserStore()

// Search
const searchForm = reactive({
  keyword: '',
  orgIds: [] as number[],
})

// Organization options
const orgOptions = ref<Organization[]>([])

interface UserFilterTag extends ActiveFilterTag {
  key: 'keyword' | 'orgIds'
}

const activeFilterTags = computed<UserFilterTag[]>(() => {
  const tags: UserFilterTag[] = []
  if (searchForm.keyword.trim()) tags.push({ key: 'keyword', label: '搜索', value: searchForm.keyword.trim() })
  searchForm.orgIds.forEach((value) => {
    const org = orgOptions.value.find((item) => item.id === value)
    tags.push({ key: 'orgIds', label: '组织', value: org?.name || String(value) })
  })
  return tags
})

// Role tag map
const roleTagMap: Record<string, string> = {
  superadmin: 'danger',
  org_admin: 'warning',
  member: '',
}

// Table
const loading = ref(false)
const tableData = ref<User[]>([])
const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
})

// Available roles based on current user
const availableRoles = computed(() => {
  if (userStore.isSuperAdmin) {
    return [
      { label: '超级管理员', value: 'superadmin' },
      { label: '组织管理员', value: 'org_admin' },
      { label: '普通成员', value: 'member' },
    ]
  }
  return [
    { label: '组织管理员', value: 'org_admin' },
    { label: '普通成员', value: 'member' },
  ]
})

function isActive(row: User): boolean {
  return row.status === '1' || row.status === 1 || row.status === 'active'
}

// Fetch data
async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
    }
    if (searchForm.orgIds.length) {
      params.org_id = searchForm.orgIds.join(',')
    }
    const res = await getUserList(params as any)
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function fetchOrgOptions() {
  try {
    orgOptions.value = await getAllOrganizations()
  } catch {
    // Ignore
  }
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.orgIds = []
  pagination.page = 1
  fetchData()
}

function removeFilterTag(tag: UserFilterTag) {
  if (tag.key === 'keyword') searchForm.keyword = ''
  if (tag.key === 'orgIds') {
    searchForm.orgIds = searchForm.orgIds.filter((item) => {
      const org = orgOptions.value.find((orgItem) => orgItem.id === item)
      return (org?.name || String(item)) !== tag.value
    })
  }
  handleSearch()
}

// --- User Drawer ---
const userDrawerVisible = ref(false)
const drawerMode = ref<'create' | 'edit' | 'detail' | 'reset'>('create')
const isEdit = ref(false)
const editId = ref<number | null>(null)
const selectedUser = ref<User | null>(null)
const userFormRef = ref<FormInstance>()
const submitLoading = ref(false)

const userFormData = reactive<UserForm & { email?: string }>({
  username: '',
  phone: '',
  password: '',
  display_name: '',
  email: '',
  role: 'member',
  org_id: null,
})

const userFormRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少 6 个字符', trigger: 'blur' },
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' },
    { max: 100, message: '显示名称最多 100 个字符', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱', trigger: 'blur' },
    { max: 200, message: '邮箱最多 200 个字符', trigger: 'blur' },
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}

const drawerTitle = computed(() => {
  if (drawerMode.value === 'detail') return '用户详情'
  if (drawerMode.value === 'reset') return '重置密码'
  return isEdit.value ? '编辑用户' : '新增用户'
})

function openUserDetailDrawer(row: User) {
  drawerMode.value = 'detail'
  selectedUser.value = row
  userDrawerVisible.value = true
}

function openUserDrawer(row?: User) {
  drawerMode.value = row ? 'edit' : 'create'
  selectedUser.value = row || null
  if (row) {
    isEdit.value = true
    editId.value = row.id
    userFormData.username = row.username
    userFormData.phone = row.phone
    userFormData.password = ''
    userFormData.display_name = row.display_name
    userFormData.email = row.email || ''
    userFormData.role = row.role
    userFormData.org_id = row.org_id
  } else {
    isEdit.value = false
    editId.value = null
    userFormData.username = ''
    userFormData.phone = ''
    userFormData.password = ''
    userFormData.display_name = ''
    userFormData.email = ''
    userFormData.role = 'member'
    userFormData.org_id = userStore.isSuperAdmin ? null : userStore.userInfo?.org_id || null
  }
  userDrawerVisible.value = true
}

async function handleUserSubmit() {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value && editId.value) {
      const updateData: any = {
        display_name: userFormData.display_name,
        phone: userFormData.phone,
        email: userFormData.email,
        role: userFormData.role,
      }
      if (userStore.isSuperAdmin) {
        updateData.org_id = userFormData.org_id
      }
      if (userFormData.password) {
        updateData.password = userFormData.password
      }
      await updateUser(editId.value, updateData)
      ElMessage.success('更新成功')
    } else {
      await createUser({
        username: userFormData.username,
        phone: userFormData.phone,
        password: userFormData.password!,
        display_name: userFormData.display_name,
        email: userFormData.email,
        role: userFormData.role,
        org_id: userStore.isSuperAdmin ? userFormData.org_id : userStore.userInfo?.org_id || null,
      })
      ElMessage.success('创建成功')
    }
    userDrawerVisible.value = false
    fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    submitLoading.value = false
  }
}

// --- Reset Password ---
const resetPwdTargetId = ref<number | null>(null)
const resetPwdFormRef = ref<FormInstance>()
const resetPwdLoading = ref(false)

const resetPwdForm = reactive({
  password: '',
  confirmPassword: '',
})

const resetPwdRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 50, message: '密码长度至少 6 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule: any, value: string, callback: any) => {
        if (value !== resetPwdForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

function openResetPwdDrawer(row: User) {
  drawerMode.value = 'reset'
  selectedUser.value = row
  resetPwdTargetId.value = row.id
  resetPwdForm.password = ''
  resetPwdForm.confirmPassword = ''
  userDrawerVisible.value = true
}

async function handleResetPwd() {
  const valid = await resetPwdFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!resetPwdTargetId.value) return

  resetPwdLoading.value = true
  try {
    await resetUserPassword(resetPwdTargetId.value, resetPwdForm.password)
    ElMessage.success('密码重置成功')
    userDrawerVisible.value = false
  } catch {
    // Error handled by interceptor
  } finally {
    resetPwdLoading.value = false
  }
}

async function handleToggleStatus(row: User) {
  const active = isActive(row)
  const action = active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}用户「${row.display_name}」吗？`,
      '操作确认',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    await toggleUserStatus(row.id, active ? '0' : '1')
    ElMessage.success(`${action}成功`)
    fetchData()
  } catch {
    // Cancelled or error
  }
}

onMounted(() => {
  fetchData()
  if (userStore.isSuperAdmin) {
    fetchOrgOptions()
  }
})

usePageRefresh(fetchData)
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
