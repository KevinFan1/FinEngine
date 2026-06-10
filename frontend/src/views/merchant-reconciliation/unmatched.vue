<template>
    <div class="page-container page-container--flow transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            keyword-placeholder="商品编码/商品名称/订单号/达人"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">未匹配维护</span>
                        <span class="summary-count">共 {{ pagination.total }} 条 · 未匹配GMV {{ formatAmount(stats.total_gmv) }}</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="!hasMonth" :loading="exportLoading" @click="handleExport">
                            <el-icon><Download /></el-icon>
                            导出维护清单
                        </el-button>
                        <el-button :disabled="!hasMonth" :loading="loading" @click="fetchData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table class="summary-table roomy-table" :data="tableData" v-loading="loading" stripe border>
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="150" show-overflow-tooltip />
                <el-table-column label="店铺" width="180" show-overflow-tooltip>
                    <template #default="{ row }"><ShopBadge :label="row.shop_name" :color="row.shop_color" size="table" /></template>
                </el-table-column>
                <el-table-column prop="product_code" label="商品编码" width="150" fixed="left" show-overflow-tooltip />
                <el-table-column prop="product_name" label="商品名称" min-width="260" show-overflow-tooltip />
                <el-table-column prop="match_error" label="未匹配原因" width="180" show-overflow-tooltip>
                    <template #default="{ row }">
                        <el-tag type="danger" effect="plain" size="small">{{ row.match_error || "未匹配" }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="gmv" label="实收GMV" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.gmv) }}</template>
                </el-table-column>
                <el-table-column prop="live_amount" label="应付净额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.live_amount) }}</template>
                </el-table-column>
                <el-table-column prop="major_merchant_name" label="大商家" width="160" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" width="160" show-overflow-tooltip />
                <el-table-column prop="live_room" label="直播间" width="150" show-overflow-tooltip />
                <el-table-column prop="live_date" label="直播日期" width="120">
                    <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                </el-table-column>
                <el-table-column prop="order_no" label="订单号" width="180" show-overflow-tooltip />
                <el-table-column prop="sub_order_no" label="子订单号" width="180" show-overflow-tooltip />
                <el-table-column prop="transaction_flow_no" label="动账流水号" min-width="180" show-overflow-tooltip />
            </el-table>

            <div class="pagination-area">
                <el-pagination
                    v-model:current-page="pagination.page"
                    v-model:page-size="pagination.pageSize"
                    :page-sizes="PAGE_SIZE_OPTIONS"
                    :layout="PAGINATION_LAYOUT"
                    :total="pagination.total"
                    background
                    @size-change="handleSizeChange"
                    @current-change="handlePageChange"
                />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Download, Refresh } from "@element-plus/icons-vue";
import ShopBadge from "@/components/ShopBadge.vue";
import {
    exportMerchantReconciliationUnmatchedDetails,
    listMerchantReconciliationUnmatchedDetails,
    type MerchantReconciliationDetail,
    type MerchantReconciliationStats,
} from "@/api/merchantReconciliation";
import { formatRawDate } from "@/utils/format";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import MerchantFilters from "./components/MerchantFilters.vue";
import { downloadFile, formatAmount, selectedMonthParts } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationUnmatched" });

const {
    userStore,
    searchForm,
    douyinShops,
    orgOptions,
    shopLoading,
    fetchOrgs,
    fetchShops,
    handleOrgChange,
    resetFilters,
} = useMerchantReconciliationFilters({ autoSelectFirstShop: false });

const loading = ref(false);
const exportLoading = ref(false);
const tableData = ref<MerchantReconciliationDetail[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const stats = reactive<MerchantReconciliationStats>({
    total_gmv: "0",
    total_bic: "0",
    total_allocated_bic: "0",
    total_insurance_fee: "0",
    total_allocated_insurance_fee: "0",
    total_live_amount: "0",
    matched_rows: 0,
    unmatched_rows: 0,
});
const hasMonth = computed(() => Boolean(searchForm.month));

function queryParams(showMessage = true) {
    const month = selectedMonthParts(searchForm.month);
    if (!month.accounting_year || !month.accounting_month) {
        if (showMessage) ElMessage.warning("请选择数据年月");
        return null;
    }
    return {
        accounting_year: month.accounting_year,
        accounting_month: month.accounting_month,
        org_id: searchForm.orgId,
        shop_id: typeof searchForm.shopId === "number" ? searchForm.shopId : undefined,
        keyword: searchForm.keyword || undefined,
    };
}

async function fetchData() {
    const params = queryParams(true);
    if (!params) return;
    loading.value = true;
    try {
        const result = await listMerchantReconciliationUnmatchedDetails({
            ...params,
            page: pagination.page,
            page_size: pagination.pageSize,
        });
        tableData.value = result.items || [];
        pagination.total = result.total || 0;
        Object.assign(stats, result.stats || {});
    } finally {
        loading.value = false;
    }
}

async function handleExport() {
    const params = queryParams(true);
    if (!params) return;
    exportLoading.value = true;
    try {
        const blob = await exportMerchantReconciliationUnmatchedDetails(params);
        downloadFile(blob, `${params.accounting_year}${String(params.accounting_month).padStart(2, "0")}_商家对账未匹配明细.xlsx`);
    } finally {
        exportLoading.value = false;
    }
}

async function handleSearch() {
    pagination.page = 1;
    await fetchData();
}

async function handleReset() {
    resetFilters();
    await fetchShops();
    pagination.page = 1;
    tableData.value = [];
    pagination.total = 0;
}

async function handleSizeChange(size: number) {
    pagination.pageSize = size;
    pagination.page = 1;
    await fetchData();
}

async function handlePageChange(page: number) {
    pagination.page = page;
    await fetchData();
}

onMounted(async () => {
    await fetchOrgs();
    await fetchShops();
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";
</style>
