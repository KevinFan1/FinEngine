<template>
  <div class="page-container">
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="搜索">
          <el-input
            v-model="searchForm.keyword"
            placeholder="店铺名称/主体名称"
            clearable
            style="width: 280px"
            @keyup.enter="fetchData"
          >
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="平台">
          <el-select
            v-model="searchForm.platformNames"
            placeholder="全部平台"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            filterable
            style="width: 180px"
          >
            <el-option v-for="p in platformOptions" :key="p.value" :label="p.label" :value="p.value">
              <PlatformBadge :platform="p.value" />
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card shop-table-card">
      <template #header>
        <div class="card-header">
          <div class="shop-title-group">
            <span class="card-header-title">店铺列表</span>
            <span class="shop-count">共 {{ pagination.total }} 条</span>
          </div>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon> 新增店铺
          </el-button>
        </div>
      </template>

      <!-- Table -->
      <el-table class="summary-table roomy-table" :data="tableData" v-loading="loading" stripe border style="width: 100%" height="calc(100vh - 278px)">
        <el-table-column label="序号" width="70" align="center">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="platform_name" label="平台" width="120">
          <template #default="{ row }">
            <PlatformBadge :platform="row.platform_name" />
          </template>
        </el-table-column>
        <el-table-column label="店铺色" width="92" align="center">
          <template #default="{ row }">
            <span class="shop-color-chip" :style="shopColorStyle(row.shop_color)">
              <span class="shop-color-dot"></span>
              色标
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="店铺名称" min-width="180" />
        <el-table-column prop="entity_name" label="主体名称" min-width="180">
          <template #default="{ row }">{{ row.entity_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="200">
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
              {{ row.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleView(row)">查看</el-button>
            <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无店铺数据" :image-size="80" />
        </template>
      </el-table>

      <div class="pagination-area">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize"
          :total="pagination.total" :page-sizes="PAGE_SIZE_OPTIONS" :layout="PAGINATION_LAYOUT" background
          @size-change="fetchData" @current-change="fetchData" />
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
      <div v-if="drawerMode === 'detail' && selectedShop" class="detail-panel">
        <section class="detail-hero-card">
          <div>
            <span class="detail-kicker">SHOP #{{ selectedShop.id }}</span>
            <h3>{{ selectedShop.shop_name }}</h3>
            <p>{{ selectedShop.entity_name || '未填写主体名称' }}</p>
          </div>
          <div class="detail-badge-row">
            <PlatformBadge :platform="selectedShop.platform_name" />
            <span class="shop-color-chip" :style="shopColorStyle(selectedShop.shop_color)">
              <span class="shop-color-dot"></span>
              店铺色
            </span>
            <el-tag :type="selectedShop.status === 1 ? 'success' : 'danger'" size="small">
              {{ selectedShop.status === 1 ? '启用' : '禁用' }}
            </el-tag>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>时间信息</span>
          </div>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <strong>{{ formatDateTime(selectedShop.created_at) }}</strong>
            </div>
            <div class="detail-item">
              <span class="detail-label">更新时间</span>
              <strong>{{ formatDateTime(selectedShop.updated_at) }}</strong>
            </div>
          </div>
        </section>

        <section class="detail-card">
          <div class="detail-card-header">
            <span>备注</span>
          </div>
          <p class="detail-note">{{ selectedShop.remark || '-' }}</p>
        </section>
      </div>
      <el-form v-else ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="平台" prop="platform_name">
          <el-select v-model="form.platform_name" placeholder="选择平台" style="width: 100%">
            <el-option v-for="p in platformOptions" :key="p.value" :label="p.label" :value="p.value">
              <PlatformBadge :platform="p.value" />
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="店铺名称" prop="shop_name">
          <el-input v-model="form.shop_name" placeholder="输入店铺名称" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="店铺颜色" prop="shop_color">
          <el-input v-model="form.shop_color" placeholder="#F59E0B，留空则自动分配" maxlength="20">
            <template #prefix>
              <span class="color-input-prefix" :style="shopColorStyle(form.shop_color)"></span>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="主体名称" prop="entity_name">
          <el-input v-model="form.entity_name" placeholder="输入主体名称（选填）" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="备注信息（选填）" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <div v-if="drawerMode !== 'detail'" class="drawer-footer">
        <el-button @click="drawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: 'Shops' })

import { ref, reactive, computed, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus/es/components/form/index.mjs'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import { ElMessageBox } from 'element-plus/es/components/message-box/index.mjs'
import { getShopList, createShop, updateShop, deleteShop, type Shop } from '@/api/shop'
import { getPlatformList, type Platform } from '@/api/platform'
import { formatDateTime } from '@/utils/format'
import { getFallbackPlatforms, toReportPlatformOptions, type PlatformOption } from '@/utils/platform'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import PlatformBadge from '@/components/PlatformBadge.vue'

const platforms = ref<Platform[]>(getFallbackPlatforms())
const platformOptions = ref<PlatformOption[]>(toReportPlatformOptions(platforms.value))

// Search
const searchForm = reactive({
  keyword: '',
  platformNames: [] as string[],
})

// Table
const loading = ref(false)
const tableData = ref<Shop[]>([])
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
const selectedShop = ref<Shop | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  platform_name: '',
  shop_name: '',
  shop_color: '',
  entity_name: '',
  remark: '',
})

const rules: FormRules = {
  platform_name: [
    { required: true, message: '请选择平台', trigger: 'change' },
  ],
  shop_name: [
    { required: true, message: '请输入店铺名称', trigger: 'blur' },
    { min: 2, max: 200, message: '长度在 2 到 200 个字符', trigger: 'blur' },
  ],
  shop_color: [
    { max: 20, message: '店铺颜色最多 20 个字符', trigger: 'blur' },
  ],
  entity_name: [
    { max: 200, message: '主体名称最多 200 个字符', trigger: 'blur' },
  ],
  remark: [
    { max: 2000, message: '备注最多 2000 个字符', trigger: 'blur' },
  ],
}

const drawerTitle = computed(() => {
  if (drawerMode.value === 'detail') return '店铺详情'
  return isEdit.value ? '编辑店铺' : '新增店铺'
})

async function fetchData() {
  loading.value = true
  try {
    const res = await getShopList({
      page: pagination.page,
      page_size: pagination.pageSize,
      keyword: searchForm.keyword || undefined,
      platform_name: searchForm.platformNames.join(',') || undefined,
    })
    tableData.value = res.items || []
    pagination.total = res.total || 0
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

async function fetchPlatformOptions() {
  try {
    const res = await getPlatformList()
    platforms.value = res.length ? res : getFallbackPlatforms()
  } catch {
    platforms.value = getFallbackPlatforms()
  }
  platformOptions.value = toReportPlatformOptions(platforms.value)
}

function handleReset() {
  searchForm.keyword = ''
  searchForm.platformNames = []
  pagination.page = 1
  fetchData()
}

function handleAdd() {
  drawerMode.value = 'create'
  isEdit.value = false
  editId.value = null
  selectedShop.value = null
  form.platform_name = ''
  form.shop_name = ''
  form.shop_color = ''
  form.entity_name = ''
  form.remark = ''
  drawerVisible.value = true
}

function handleView(row: Shop) {
  drawerMode.value = 'detail'
  selectedShop.value = row
  drawerVisible.value = true
}

function handleEdit(row: Shop) {
  drawerMode.value = 'edit'
  isEdit.value = true
  editId.value = row.id
  selectedShop.value = row
  form.platform_name = row.platform_name
  form.shop_name = row.shop_name
  form.shop_color = row.shop_color || ''
  form.entity_name = row.entity_name || ''
  form.remark = row.remark || ''
  drawerVisible.value = true
}

function normalizeHexColor(value?: string) {
  const color = String(value || '').trim()
  if (!color) return '#CBD5E1'
  return color.startsWith('#') ? color : `#${color}`
}

function shopColorStyle(color?: string) {
  const value = normalizeHexColor(color)
  return {
    '--shop-color': value,
    background: `color-mix(in srgb, ${value} 14%, white)`,
    borderColor: `color-mix(in srgb, ${value} 34%, white)`,
    color: value,
  }
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      await updateShop(editId.value, {
        platform_name: form.platform_name,
        shop_name: form.shop_name,
        shop_color: form.shop_color || undefined,
        entity_name: form.entity_name || undefined,
        remark: form.remark || undefined,
      })
      ElMessage.success('更新成功')
    } else {
      await createShop({
        platform_name: form.platform_name,
        shop_name: form.shop_name,
        shop_color: form.shop_color || undefined,
        entity_name: form.entity_name || undefined,
        remark: form.remark || undefined,
      })
      ElMessage.success('创建成功')
    }
    drawerVisible.value = false
    fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Shop) {
  try {
    await ElMessageBox.confirm(
      `确定要删除店铺「${row.shop_name}」吗？此操作不可恢复。`,
      '操作确认',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    await deleteShop(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch {
    // Cancelled or error
  }
}

onMounted(async () => {
  await fetchPlatformOptions()
  fetchData()
})
</script>

<style scoped lang="scss">
.shop-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.shop-count {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.shop-table-card {
  :deep(.el-card__body) {
    padding: 0;
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

.shop-color-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 10px;
  border: 1px solid var(--shop-color);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.shop-color-dot,
.color-input-prefix {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--shop-color);
}

.color-input-prefix {
  display: inline-flex;
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

.detail-label {
  color: var(--text-tertiary);
  font-size: 12px;
  font-weight: 600;
}

.detail-note {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
