<template>
  <div class="page-container">
    <!-- Page header -->
    <div class="page-header">
      <div class="page-header-info">
        <h2 class="page-title">动账明细</h2>
        <p class="page-desc">查看按业务年月落入汇总表的明细数据，支持筛选和导出</p>
      </div>
    </div>

    <!-- Filter bar -->
    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="业务年月">
          <el-date-picker
            v-model="searchForm.summaryMonth"
            type="month"
            placeholder="选择业务年月"
            clearable
            value-format="YYYY-MM"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="上传年月">
          <el-date-picker
            v-model="searchForm.sourceMonth"
            type="month"
            placeholder="选择上传年月"
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
            v-model="searchForm.shop"
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
              :value="shop.shop_name"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Table area -->
    <el-card shadow="never" class="table-card summary-table-card">
      <template #header>
        <div class="card-header">
          <div class="summary-title-group">
            <span class="card-header-title">动账明细数据</span>
            <span class="summary-count">共 {{ pagination.total }} 条 · 已选 {{ selectedRows.length }} 条</span>
          </div>
          <div class="card-header-actions">
            <el-button
              :loading="exportSelectedLoading"
              :disabled="selectedRows.length === 0"
              @click="handleExport('selected')"
            >
              <el-icon><Download /></el-icon> 导出选中
            </el-button>
            <el-button
              :loading="exportCurrentPageLoading"
              @click="handleExport('current_page')"
            >
              <el-icon><Download /></el-icon> 导出当前页
            </el-button>
            <el-button
              type="success"
              :loading="exportAllLoading"
              @click="handleExport('all')"
            >
              <el-icon><Download /></el-icon> 导出全部
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        ref="summaryTableRef"
        class="summary-table"
        :data="tableData"
        v-loading="loading"
        stripe
        border
        show-summary
        :summary-method="getSummary"
        :fit="false"
        style="width: 100%"
        :max-height="600"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="48" fixed="left" />
        <el-table-column label="序号" width="70" align="center" fixed="left">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="source_date" label="上传年月" width="108" align="center" />
        <el-table-column prop="summary_date" label="业务年月" width="108" align="center" />
        <el-table-column prop="platform" label="平台" width="104" align="center">
          <template #default="{ row }">
            <el-tag size="small" :class="getPlatformTagClass(row.platform)">{{ getPlatformLabel(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="店铺" width="220" show-overflow-tooltip />
        <el-table-column prop="real_gmv" label="实收GMV" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.real_gmv) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="platform_other_income" label="平台其他收入" width="150" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.platform_other_income) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="platform_service_fee" label="平台服务费" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.platform_service_fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="return_and_other_fee" label="退货费用及其他费用" width="175" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.return_and_other_fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="daren_commission" label="达人佣金" width="135" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.daren_commission) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="zhaoshang_service_fee" label="招商服务费" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.zhaoshang_service_fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="outside_promotion_fee" label="站外推广费" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.outside_promotion_fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="service_provider_commission" label="服务商佣金" width="150" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.service_provider_commission) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_donation_fee" label="支付捐赠费用" width="150" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.payment_donation_fee) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="shipping_insurance" label="运费险" width="120" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.shipping_insurance) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="bic" label="BIC" width="120" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.bic) }}</span>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无动账明细数据，请先上传并处理文件" :image-size="80" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import type { TableColumnCtx } from 'element-plus/es/components/table/index.mjs'
import { getSummaryList, exportSummaryExcel, type SummaryRecord } from '@/api/summary'
import { getShopList, type Shop } from '@/api/shop'
import { formatMoney, getPlatformLabel, getPlatformTagClass } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'

// Search
const searchForm = reactive({
  summaryMonth: '',
  sourceMonth: '',
  platform: '',
  shop: '',
})

const platformOptions = [
  { label: '抖音', value: 'douyin' },
  { label: '快手', value: 'kuaishou' },
  { label: '小红书', value: 'xiaohongshu' },
  { label: '微信小店', value: 'weixin_video' },
  { label: '天猫', value: 'tmall' },
  { label: '淘宝', value: 'taobao' },
]

// Table
const loading = ref(false)
const exportAllLoading = ref(false)
const exportCurrentPageLoading = ref(false)
const exportSelectedLoading = ref(false)
const tableData = ref<SummaryRecord[]>([])
const selectedRows = ref<SummaryRecord[]>([])
const shopLoading = ref(false)
const shopOptions = ref<Shop[]>([])
const summaryTableRef = ref<{ doLayout: () => void }>()

const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
})

const selectedSummaryYear = computed(() => {
  if (!searchForm.summaryMonth) return undefined
  const [year] = searchForm.summaryMonth.split('-')
  return Number(year) || undefined
})

const selectedSummaryMonth = computed(() => {
  if (!searchForm.summaryMonth) return undefined
  const [, month] = searchForm.summaryMonth.split('-')
  return Number(month) || undefined
})

const selectedSourceYear = computed(() => {
  if (!searchForm.sourceMonth) return undefined
  const [year] = searchForm.sourceMonth.split('-')
  return Number(year) || undefined
})

const selectedSourceMonth = computed(() => {
  if (!searchForm.sourceMonth) return undefined
  const [, month] = searchForm.sourceMonth.split('-')
  return Number(month) || undefined
})

const filteredShopOptions = computed(() => {
  if (!searchForm.platform) return shopOptions.value
  return shopOptions.value.filter((shop) => shop.platform_name === searchForm.platform)
})

// Money columns for summary
const moneyColumns = [
  'real_gmv', 'platform_other_income', 'platform_service_fee',
  'return_and_other_fee', 'daren_commission', 'zhaoshang_service_fee',
  'outside_promotion_fee', 'service_provider_commission',
  'payment_donation_fee', 'shipping_insurance', 'bic',
]

function getSummary(param: {
  columns: TableColumnCtx<SummaryRecord>[]
  data: SummaryRecord[]
}) {
  const { columns, data } = param
  const sums: string[] = []
  columns.forEach((column, index) => {
    const prop = column.property as keyof SummaryRecord
    if (prop === 'source_date') {
      sums[index] = '合计'
      return
    }
    if (!moneyColumns.includes(prop)) {
      sums[index] = ''
      return
    }
    const values = data.map((item) => Number(item[prop]) || 0)
    const total = values.reduce((prev, curr) => prev + curr, 0)
    sums[index] = total.toLocaleString('zh-CN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  })
  return sums
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getSummaryList({
      page: pagination.page,
      page_size: pagination.pageSize,
      summary_year: selectedSummaryYear.value,
      summary_month: selectedSummaryMonth.value,
      source_year: selectedSourceYear.value,
      source_month: selectedSourceMonth.value,
      platform_name: searchForm.platform || undefined,
      shop_name: searchForm.shop || undefined,
    })
    tableData.value = res.items || []
    selectedRows.value = []
    pagination.total = res.total || 0
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
    await nextTick()
    summaryTableRef.value?.doLayout()
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
  if (searchForm.shop && !filteredShopOptions.value.some((shop) => shop.shop_name === searchForm.shop)) {
    searchForm.shop = ''
  }
  fetchShopOptions()
}

function handleSearch() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  searchForm.summaryMonth = ''
  searchForm.sourceMonth = ''
  searchForm.platform = ''
  searchForm.shop = ''
  pagination.page = 1
  fetchShopOptions()
  fetchData()
}

function handleSelectionChange(rows: SummaryRecord[]) {
  selectedRows.value = rows
}

async function handleExport(scope: 'all' | 'current_page' | 'selected') {
  if (scope === 'current_page' && tableData.value.length === 0) {
    ElMessage.warning('当前页暂无可导出的数据')
    return
  }
  if (scope === 'selected' && selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要导出的数据')
    return
  }

  const loadingRef = scope === 'all'
    ? exportAllLoading
    : scope === 'current_page'
      ? exportCurrentPageLoading
      : exportSelectedLoading
  loadingRef.value = true
  try {
    const blob = await exportSummaryExcel({
      summary_year: selectedSummaryYear.value,
      summary_month: selectedSummaryMonth.value,
      source_year: selectedSourceYear.value,
      source_month: selectedSourceMonth.value,
      platform_name: searchForm.platform || undefined,
      shop_name: searchForm.shop || undefined,
      scope,
      ids: scope === 'selected' ? selectedRows.value.map((row) => row.id).join(',') : undefined,
      page: scope === 'current_page' ? pagination.page : undefined,
      page_size: scope === 'current_page' ? pagination.pageSize : undefined,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const scopeLabel = scope === 'all'
      ? '全部'
      : scope === 'current_page'
        ? `第${pagination.page}页`
        : '选中'
    link.download = `动账明细_${searchForm.summaryMonth || '全部业务年月'}_${searchForm.sourceMonth || '全部上传年月'}_${scopeLabel}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch {
    ElMessage.error('导出失败，请稍后重试')
  } finally {
    loadingRef.value = false
  }
}

onMounted(() => {
  fetchShopOptions()
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
  min-width: 0;

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

  .summary-title-group {
    display: flex;
    align-items: baseline;
    gap: 12px;
    min-width: 0;
  }

  .summary-count {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
  }

  :deep(.el-card__body) {
    overflow: visible;
  }
}

.summary-table-card {
  :deep(.el-table) {
    --el-table-header-bg-color: transparent;
    border-top: 1px solid var(--border-light);
  }

  :deep(.el-table__inner-wrapper) {
    min-width: 100%;
  }

  :deep(.el-table__header-wrapper),
  :deep(.el-table__fixed-header-wrapper) {
    th.el-table__cell {
      background:
        linear-gradient(180deg, var(--surface-highlight), transparent),
        var(--table-header-bg) !important;
    }
  }

  :deep(.el-table__body-wrapper) {
    &::-webkit-scrollbar {
      height: 10px;
    }

    &::-webkit-scrollbar-thumb {
      border: 2px solid transparent;
      background-clip: content-box;
    }
  }

  :deep(.el-table__cell) {
    height: 48px;
  }

  :deep(.summary-table .el-table__header),
  :deep(.summary-table .el-table__body),
  :deep(.summary-table .el-table__footer) {
    table-layout: fixed !important;
  }

  :deep(.summary-table .el-table__header .cell),
  :deep(.summary-table .el-table__body .cell),
  :deep(.summary-table .el-table__footer .cell) {
    box-sizing: border-box;
  }

  :deep(.summary-table th.el-table__cell.is-right .cell) {
    justify-content: flex-end !important;
    text-align: right !important;
    padding-left: 12px;
    padding-right: 16px;
  }

  :deep(.summary-table th.el-table__cell.is-left .cell) {
    justify-content: flex-start !important;
    text-align: left !important;
  }

  :deep(.summary-table th.el-table__cell.is-center .cell) {
    justify-content: center !important;
    text-align: center !important;
  }

  :deep(.money-column) {
    background: rgba(21, 91, 213, 0.015) !important;

    .cell {
      justify-content: flex-end;
      text-align: right !important;
      padding-left: 12px;
      padding-right: 16px;
    }
  }

  :deep(.money-cell) {
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0;
  }

  :deep(.el-table__fixed),
  :deep(.el-table__fixed-left),
  :deep(.el-table__fixed-right) {
    box-shadow: 8px 0 18px rgba(15, 23, 42, 0.06);
  }

  :deep(.el-table__footer) {
    td {
      font-weight: 600;
      background: var(--bg-elevated) !important;
      border-top: 1px solid var(--border-color);

      .cell {
        text-align: right;
        color: var(--text-primary);
      }
    }

    td:first-child .cell {
      text-align: center;
    }
  }
}

@media (max-width: 768px) {
  .table-card {
    .card-header {
      align-items: flex-start;
      flex-direction: column;
    }

    .summary-title-group {
      align-items: flex-start;
      flex-direction: column;
      gap: 4px;
    }
  }
}
</style>
