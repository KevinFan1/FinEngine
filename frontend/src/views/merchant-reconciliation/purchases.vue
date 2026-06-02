<template>
    <div class="page-container transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            multiple-shops
            keyword-placeholder="直播编号/商家/货品"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">采购明细</span>
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
                <el-table-column label="年月" width="110">
                    <template #default="{ row }">{{ formatAccountingPeriod(row.accounting_period) }}</template>
                </el-table-column>
                <el-table-column label="店铺" width="190" show-overflow-tooltip>
                    <template #default="{ row }"><ShopBadge :label="row.shop_name" :color="row.shop_color" size="table" /></template>
                </el-table-column>
                <el-table-column prop="live_room" label="直播间" width="150" show-overflow-tooltip />
                <el-table-column prop="merchant" label="商家" width="150" show-overflow-tooltip />
                <el-table-column prop="live_date" label="直播日期" width="120" />
                <el-table-column prop="live_code" label="直播编号" width="150" show-overflow-tooltip />
                <el-table-column prop="normalized_live_code" label="新直播编码" width="150" show-overflow-tooltip />
                <el-table-column prop="loan_return_order_no" label="借/退货单号" width="160" show-overflow-tooltip />
                <el-table-column prop="loan_return_date" label="借/退货日期" width="120" />
                <el-table-column prop="subject" label="主体" width="150" show-overflow-tooltip />
                <el-table-column prop="summary" label="摘要" width="140" show-overflow-tooltip />
                <el-table-column prop="product_name" label="货品名称" min-width="220" show-overflow-tooltip />
                <el-table-column prop="sale_price" label="卖价" width="110" align="right">
                    <template #default="{ row }">{{ formatAmount(row.sale_price) }}</template>
                </el-table-column>
                <el-table-column prop="borrow_quantity" label="借货数量" width="110" align="right">
                    <template #default="{ row }">{{ formatAmount(row.borrow_quantity) }}</template>
                </el-table-column>
                <el-table-column prop="borrow_weight_g" label="借货重量g" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.borrow_weight_g) }}</template>
                </el-table-column>
                <el-table-column prop="borrow_amount" label="借货金额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.borrow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="return_quantity" label="退货数量" width="110" align="right">
                    <template #default="{ row }">{{ formatAmount(row.return_quantity) }}</template>
                </el-table-column>
                <el-table-column prop="return_weight_g" label="退货重量g" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.return_weight_g) }}</template>
                </el-table-column>
                <el-table-column prop="return_amount" label="退货金额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.return_amount) }}</template>
                </el-table-column>
                <el-table-column prop="estimated_settlement_date" label="预计结款日期" width="130" />
                <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
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
import { listMerchantRedSheetPurchases, type MerchantRedSheetPurchase } from "@/api/merchantReconciliation";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatAccountingPeriod, formatAmount } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationPurchases" });

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
const tableData = ref<MerchantRedSheetPurchase[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });

async function fetchData() {
    const params = redSheetParams();
    if (!params) return;
    loading.value = true;
    try {
        const result = await listMerchantRedSheetPurchases({
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

function summaryMethod({ columns, data }: { columns: any[]; data: MerchantRedSheetPurchase[] }) {
    const moneyProps = new Set(["sale_price", "borrow_quantity", "borrow_weight_g", "borrow_amount", "return_quantity", "return_weight_g", "return_amount"]);
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
