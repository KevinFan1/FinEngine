<template>
    <div class="page-container page-container--flow transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            multiple-shops
            keyword-placeholder="直播间/商家/主体/结算状态"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">货款明细</span>
                        <span class="summary-count">共 {{ pagination.total }} 条</span>
                    </div>
                    <el-button @click="fetchData">刷新</el-button>
                </div>
            </template>

            <el-table class="summary-table roomy-table" :data="tableData" v-loading="loading" stripe border show-summary :summary-method="summaryMethod">
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="160" show-overflow-tooltip />
                <el-table-column label="数据年月" width="110">
                    <template #default="{ row }">{{ formatAccountingPeriod(row.accounting_period) }}</template>
                </el-table-column>
                <el-table-column label="店铺" width="190" show-overflow-tooltip>
                    <template #default="{ row }"><ShopBadge :label="row.shop_name" :color="row.shop_color" size="table" /></template>
                </el-table-column>
                <el-table-column prop="live_room" label="直播间" width="150" show-overflow-tooltip />
                <el-table-column prop="live_date" label="直播日期" width="120">
                    <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                </el-table-column>
                <el-table-column prop="merchant" label="商家" width="150" show-overflow-tooltip />
                <el-table-column prop="borrow_total_amount" label="借货总金额" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.borrow_total_amount) }}</template>
                </el-table-column>
                <el-table-column prop="return_total_amount" label="退货总金额" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.return_total_amount) }}</template>
                </el-table-column>
                <el-table-column prop="business_fee_deduction" label="冲减业务费用" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.business_fee_deduction) }}</template>
                </el-table-column>
                <el-table-column prop="deduction_amount" label="冲减金额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.deduction_amount) }}</template>
                </el-table-column>
                <el-table-column prop="payable_goods_amount" label="应付货款金额" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.payable_goods_amount) }}</template>
                </el-table-column>
                <el-table-column prop="return_rate" label="退货率" width="110" align="right">
                    <template #default="{ row }">{{ formatPercent(row.return_rate) }}</template>
                </el-table-column>
                <el-table-column prop="settlement_subject" label="结算主体" width="160" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" width="150" show-overflow-tooltip />
                <el-table-column prop="collection_merchant" label="回款商家" width="150" show-overflow-tooltip />
                <el-table-column prop="is_settled" label="是否已结款" width="110" />
                <el-table-column prop="is_collected" label="是否已回款" width="110" />
                <el-table-column prop="paid_amount" label="已付" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.paid_amount) }}</template>
                </el-table-column>
                <el-table-column prop="borrow_minus_return" label="借-退" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.borrow_minus_return) }}</template>
                </el-table-column>
                <el-table-column prop="settlement_status" label="结算状态" min-width="120" show-overflow-tooltip />
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
import { onMounted, reactive, ref } from "vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { listMerchantRedSheetPayments, type MerchantRedSheetPayment } from "@/api/merchantReconciliation";
import { formatRawDate } from "@/utils/format";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatAccountingPeriod, formatAmount, formatPercent } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationPayments" });

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
    redSheetParams,
} = useMerchantReconciliationFilters({ multipleShops: true });

const loading = ref(false);
const tableData = ref<MerchantRedSheetPayment[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });

async function fetchData() {
    const params = redSheetParams();
    if (!params) return;
    loading.value = true;
    try {
        const result = await listMerchantRedSheetPayments({
            ...params,
            page: pagination.page,
            page_size: pagination.pageSize,
        });
        tableData.value = result.items || [];
        pagination.total = result.total || 0;
    } finally {
        loading.value = false;
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
    await fetchData();
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

function summaryMethod({ columns, data }: { columns: any[]; data: MerchantRedSheetPayment[] }) {
    const moneyProps = new Set(["borrow_total_amount", "return_total_amount", "business_fee_deduction", "deduction_amount", "payable_goods_amount", "paid_amount", "borrow_minus_return"]);
    return columns.map((column, index) => {
        if (index === 0) return "合计";
        if (!moneyProps.has(column.property)) return "";
        return formatAmount(data.reduce((total, row) => total + Number((row as any)[column.property] || 0), 0));
    });
}

onMounted(async () => {
    await fetchOrgs();
    await fetchShops();
    await fetchData();
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";
</style>
