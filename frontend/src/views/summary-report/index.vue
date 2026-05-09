<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-info">
        <h2 class="page-title">汇总报表</h2>
        <p class="page-desc">按数据表上传时文件名解析的年月汇总财务指标</p>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="searchForm" inline>
        <el-form-item label="数据年月">
          <el-date-picker
            v-model="searchForm.sourceMonth"
            type="month"
            placeholder="选择数据年月"
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

    <el-card shadow="never" class="table-card summary-table-card">
      <template #header>
        <div class="card-header">
          <div class="summary-title-group">
            <span class="card-header-title">汇总数据</span>
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
            <el-button :loading="exportCurrentPageLoading" @click="handleExport('current_page')">
              <el-icon><Download /></el-icon> 导出当前页
            </el-button>
            <el-button type="success" :loading="exportAllLoading" @click="handleExport('all')">
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
        <el-table-column prop="source_date" label="数据年月" width="108" align="center" />
        <el-table-column prop="platform" label="平台" width="104" align="center">
          <template #default="{ row }">
            <el-tag size="small" :class="getPlatformTagClass(row.platform)">{{ getPlatformLabel(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="shop_name" label="店铺" width="220" show-overflow-tooltip />
        <el-table-column prop="summary_count" label="明细行数" width="105" align="right" header-align="right">
          <template #default="{ row }">
            <span class="font-mono">{{ row.summary_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="original_gmv" label="原始GMV" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.original_gmv) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gmv_adjustment" label="GMV调整" width="130" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell" :class="adjustmentClass(row.gmv_adjustment)">
              {{ formatAdjustmentMoney(row.gmv_adjustment) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="real_gmv" label="调整后GMV" width="145" align="right" header-align="right" class-name="money-column">
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
        <el-table-column prop="original_return_cost" label="原始退货费用" width="150" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell">{{ formatMoney(row.original_return_cost) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="return_cost_adjustment" label="退货费用调整" width="145" align="right" header-align="right" class-name="money-column">
          <template #default="{ row }">
            <span class="font-mono money-cell" :class="adjustmentClass(row.return_cost_adjustment)">
              {{ formatAdjustmentMoney(row.return_cost_adjustment) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="return_and_other_fee" label="调整后退货费用" width="160" align="right" header-align="right" class-name="money-column">
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
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openAdjustmentDrawer(row)">
              调整
            </el-button>
            <el-button type="primary" link @click="openDetailDrawer(row)">
              查看明细
            </el-button>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无汇总数据，请先上传并处理文件" :image-size="80" />
        </template>
      </el-table>

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

    <SummaryDetailDrawer
      v-model="detailDrawerVisible"
      :context="detailContext"
    />

    <el-drawer
      v-model="adjustmentDrawerVisible"
      title="调整金额"
      size="620px"
      append-to-body
      destroy-on-close
      :close-on-click-modal="false"
      @closed="resetAdjustmentForm"
    >
      <div v-if="adjustmentContext" class="adjustment-panel">
        <div class="adjustment-context">
          <div>
            <span class="context-label">数据年月</span>
            <strong>{{ adjustmentContext.source_date }}</strong>
          </div>
          <div>
            <span class="context-label">平台</span>
            <strong>{{ getPlatformLabel(adjustmentContext.platform) }}</strong>
          </div>
          <div>
            <span class="context-label">店铺</span>
            <strong>{{ adjustmentContext.shop_name }}</strong>
          </div>
        </div>

        <el-form
          ref="adjustmentFormRef"
          :model="adjustmentForm"
          label-width="86px"
          class="adjustment-form"
        >
          <el-form-item label="调整字段" required>
            <el-segmented v-model="adjustmentForm.metric_key" :options="metricOptions" />
          </el-form-item>
          <el-form-item label="调整方向" required>
            <el-radio-group v-model="adjustmentForm.direction">
              <el-radio-button label="increase">增加</el-radio-button>
              <el-radio-button label="decrease">减少</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="调整金额" required>
            <el-input-number
              v-model="adjustmentForm.amount"
              :min="0"
              :precision="2"
              :step="100"
              controls-position="right"
              style="width: 220px"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input
              v-model="adjustmentForm.remark"
              type="textarea"
              :rows="3"
              maxlength="2000"
              show-word-limit
              placeholder="填写调整原因"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="adjustmentSaving" @click="submitAdjustment">
              {{ editingAdjustment ? '保存修改' : '新增调整' }}
            </el-button>
            <el-button v-if="editingAdjustment" @click="cancelEditAdjustment">取消编辑</el-button>
          </el-form-item>
        </el-form>

        <div class="adjustment-list-header">
          <span>历史调整</span>
          <el-button link type="primary" :loading="adjustmentLoading" @click="fetchAdjustments">刷新</el-button>
        </div>
        <el-table
          :data="adjustmentRows"
          v-loading="adjustmentLoading"
          border
          stripe
          size="small"
          class="adjustment-table"
        >
          <el-table-column prop="metric_label" label="字段" width="128" />
          <el-table-column label="方向" width="78" align="center">
            <template #default="{ row }">
              <el-tag :type="row.direction === 'increase' ? 'success' : 'danger'" size="small">
                {{ row.direction === 'increase' ? '增加' : '减少' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="金额" width="116" align="right" header-align="right">
            <template #default="{ row }">
              <span class="font-mono" :class="adjustmentClass(row.adjustment_amount)">
                {{ formatAdjustmentMoney(row.adjustment_amount) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.remark || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="96" align="center" fixed="right">
            <template #default="{ row }">
              <div class="adjustment-actions">
                <el-button type="primary" link @click="editAdjustment(row)">编辑</el-button>
                <el-button type="danger" link @click="removeAdjustment(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index.mjs'
import { ElMessageBox } from 'element-plus/es/components/message-box/index.mjs'
import type { TableColumnCtx } from 'element-plus/es/components/table/index.mjs'
import { getSummaryReportList, exportSummaryReportExcel, type SummaryReportRecord } from '@/api/summary'
import {
  createSummaryAdjustment,
  deleteSummaryAdjustment,
  getSummaryAdjustments,
  updateSummaryAdjustment,
  type SummaryAdjustment,
  type SummaryAdjustmentDirection,
  type SummaryAdjustmentMetric,
} from '@/api/summaryAdjustment'
import { getShopList, type Shop } from '@/api/shop'
import { formatMoney, getPlatformLabel, getPlatformTagClass } from '@/utils/format'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from '@/utils/pagination'
import SummaryDetailDrawer, { type SummaryDetailContext } from '@/components/SummaryDetailDrawer.vue'

const searchForm = reactive({
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

const loading = ref(false)
const exportAllLoading = ref(false)
const exportCurrentPageLoading = ref(false)
const exportSelectedLoading = ref(false)
const tableData = ref<SummaryReportRecord[]>([])
const selectedRows = ref<SummaryReportRecord[]>([])
const shopLoading = ref(false)
const shopOptions = ref<Shop[]>([])
const summaryTableRef = ref<{ doLayout: () => void }>()
const detailDrawerVisible = ref(false)
const detailContext = ref<SummaryDetailContext | null>(null)
const adjustmentDrawerVisible = ref(false)
const adjustmentContext = ref<SummaryReportRecord | null>(null)
const adjustmentRows = ref<SummaryAdjustment[]>([])
const adjustmentLoading = ref(false)
const adjustmentSaving = ref(false)
const editingAdjustment = ref<SummaryAdjustment | null>(null)
const adjustmentForm = reactive<{
  metric_key: SummaryAdjustmentMetric
  direction: SummaryAdjustmentDirection
  amount: number
  remark: string
}>({
  metric_key: 'gmv',
  direction: 'increase',
  amount: 0,
  remark: '',
})

const metricOptions = [
  { label: '实收GMV', value: 'gmv' },
  { label: '退货费用及其他费用', value: 'return_cost' },
]

const pagination = reactive({
  page: 1,
  pageSize: DEFAULT_PAGE_SIZE,
  total: 0,
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

const moneyColumns = [
  'original_gmv', 'gmv_adjustment', 'real_gmv',
  'platform_other_income', 'platform_service_fee',
  'original_return_cost', 'return_cost_adjustment', 'return_and_other_fee',
  'daren_commission', 'zhaoshang_service_fee',
  'outside_promotion_fee', 'service_provider_commission',
  'payment_donation_fee', 'shipping_insurance', 'bic',
]

function getSummary(param: {
  columns: TableColumnCtx<SummaryReportRecord>[]
  data: SummaryReportRecord[]
}) {
  const { columns, data } = param
  const sums: string[] = []
  columns.forEach((column, index) => {
    const prop = column.property as keyof SummaryReportRecord
    if (prop === 'source_date') {
      sums[index] = '合计'
      return
    }
    if (prop === 'summary_count') {
      const total = data.reduce((prev, item) => prev + Number(item.summary_count || 0), 0)
      sums[index] = String(total)
      return
    }
    if (!moneyColumns.includes(prop)) {
      sums[index] = ''
      return
    }
    const total = data.reduce((prev, item) => prev + (Number(item[prop]) || 0), 0)
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
    const res = await getSummaryReportList({
      page: pagination.page,
      page_size: pagination.pageSize,
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
  searchForm.sourceMonth = ''
  searchForm.platform = ''
  searchForm.shop = ''
  pagination.page = 1
  fetchShopOptions()
  fetchData()
}

function openDetailDrawer(row: SummaryReportRecord) {
  detailContext.value = {
    sourceYear: row.source_year,
    sourceMonth: row.source_month,
    sourceDate: row.source_date,
    platform: row.platform,
    shopName: row.shop_name,
    summaryCount: row.summary_count,
  }
  detailDrawerVisible.value = true
}

async function openAdjustmentDrawer(row: SummaryReportRecord) {
  adjustmentContext.value = row
  adjustmentDrawerVisible.value = true
  resetAdjustmentForm()
  await fetchAdjustments()
}

async function fetchAdjustments() {
  if (!adjustmentContext.value) return

  adjustmentLoading.value = true
  try {
    adjustmentRows.value = await getSummaryAdjustments({
      source_year: adjustmentContext.value.source_year,
      source_month: adjustmentContext.value.source_month,
      platform_name: adjustmentContext.value.platform_name,
      shop_id: adjustmentContext.value.shop_id,
    })
  } catch {
    // Error handled by interceptor
  } finally {
    adjustmentLoading.value = false
  }
}

async function submitAdjustment() {
  if (!adjustmentContext.value) return
  if (!adjustmentForm.amount || adjustmentForm.amount <= 0) {
    ElMessage.warning('请输入大于 0 的调整金额')
    return
  }

  adjustmentSaving.value = true
  try {
    if (editingAdjustment.value) {
      await updateSummaryAdjustment(editingAdjustment.value.id, {
        metric_key: adjustmentForm.metric_key,
        direction: adjustmentForm.direction,
        amount: adjustmentForm.amount,
        remark: adjustmentForm.remark || undefined,
      })
      ElMessage.success('调整记录已更新')
    } else {
      await createSummaryAdjustment({
        source_year: adjustmentContext.value.source_year,
        source_month: adjustmentContext.value.source_month,
        platform_name: adjustmentContext.value.platform_name,
        shop_id: adjustmentContext.value.shop_id,
        shop_name: adjustmentContext.value.shop_name,
        metric_key: adjustmentForm.metric_key,
        direction: adjustmentForm.direction,
        amount: adjustmentForm.amount,
        remark: adjustmentForm.remark || undefined,
      })
      ElMessage.success('调整记录已新增')
    }
    resetAdjustmentForm()
    await fetchAdjustments()
    await fetchData()
  } catch {
    // Error handled by interceptor
  } finally {
    adjustmentSaving.value = false
  }
}

function editAdjustment(row: SummaryAdjustment) {
  editingAdjustment.value = row
  adjustmentForm.metric_key = row.metric_key
  adjustmentForm.direction = row.direction
  adjustmentForm.amount = row.amount
  adjustmentForm.remark = row.remark || ''
}

function cancelEditAdjustment() {
  resetAdjustmentForm()
}

async function removeAdjustment(row: SummaryAdjustment) {
  try {
    await ElMessageBox.confirm('确定删除这条调整记录吗？删除后会从汇总报表中扣除该调整。', '删除确认', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
    })
    await deleteSummaryAdjustment(row.id)
    ElMessage.success('调整记录已删除')
    if (editingAdjustment.value?.id === row.id) {
      resetAdjustmentForm()
    }
    await fetchAdjustments()
    await fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      // Request errors are handled by interceptor.
    }
  }
}

function resetAdjustmentForm() {
  editingAdjustment.value = null
  adjustmentForm.metric_key = 'gmv'
  adjustmentForm.direction = 'increase'
  adjustmentForm.amount = 0
  adjustmentForm.remark = ''
}

function formatAdjustmentMoney(value: number) {
  const numericValue = Number(value || 0)
  if (numericValue === 0) return '0.00'
  const absText = formatMoney(Math.abs(numericValue))
  return numericValue > 0 ? `+${absText}` : `-${absText}`
}

function adjustmentClass(value: number) {
  const numericValue = Number(value || 0)
  return {
    'adjustment-positive': numericValue > 0,
    'adjustment-negative': numericValue < 0,
  }
}

function handleSelectionChange(rows: SummaryReportRecord[]) {
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
    const blob = await exportSummaryReportExcel({
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
    link.download = `汇总报表_${searchForm.sourceMonth || '全部数据年月'}_${scopeLabel}.xlsx`
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

  :deep(.el-table__cell) {
    height: 48px;
  }

  :deep(.summary-table .el-table__header),
  :deep(.summary-table .el-table__body),
  :deep(.summary-table .el-table__footer) {
    table-layout: fixed !important;
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

.adjustment-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.adjustment-context {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border-light);
  border-radius: 6px;
  background: var(--surface-highlight);

  div {
    min-width: 0;
  }

  strong {
    display: block;
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.6;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.context-label {
  display: block;
  color: var(--text-tertiary);
  font-size: 12px;
  line-height: 1.5;
}

.adjustment-form {
  padding-bottom: 2px;
  border-bottom: 1px solid var(--border-light);
}

.adjustment-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 14px;
}

.adjustment-table {
  width: 100%;
}

.adjustment-actions {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.adjustment-positive {
  color: var(--success);
}

.adjustment-negative {
  color: var(--error);
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

  .adjustment-context {
    grid-template-columns: 1fr;
  }
}
</style>
