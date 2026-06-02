<template>
    <div class="page-container transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            keyword-placeholder="账户名称/对方户名/用途/流水号"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">银行流水</span>
                        <span class="summary-count">共 {{ pagination.total }} 条</span>
                    </div>
                    <el-button @click="fetchData">刷新</el-button>
                </div>
            </template>

            <el-table class="summary-table roomy-table" :data="tableData" v-loading="loading" stripe border show-summary :summary-method="summaryMethod">
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column label="年月" width="110" fixed="left">
                    <template #default="{ row }">{{ formatAccountingPeriod(row.accounting_period) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="160" show-overflow-tooltip />
                <el-table-column prop="bank_name" label="银行" width="110" show-overflow-tooltip />
                <el-table-column prop="account_name" label="账户名称" min-width="210" show-overflow-tooltip />
                <el-table-column prop="transaction_time" label="交易时间" width="170" />
                <el-table-column prop="counterparty_name" label="对方户名" min-width="220" show-overflow-tooltip />
                <el-table-column prop="debit_amount" label="支出金额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.debit_amount) }}</template>
                </el-table-column>
                <el-table-column prop="credit_amount" label="收入金额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.credit_amount) }}</template>
                </el-table-column>
                <el-table-column prop="flow_amount" label="流水净额" width="120" align="right">
                    <template #default="{ row }">{{ formatAmount(row.flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="live_date" label="直播日期" width="190" show-overflow-tooltip>
                    <template #default="{ row }">
                        <el-tag v-if="row.live_date" size="small" type="success">{{ row.live_date }}</el-tag>
                        <span v-else class="text-muted">未解析</span>
                    </template>
                </el-table-column>
                <el-table-column prop="purpose" label="用途/备注" min-width="260" show-overflow-tooltip />
                <el-table-column prop="summary" label="摘要" width="130" show-overflow-tooltip />
                <el-table-column prop="transaction_flow_no" label="流水号" min-width="180" show-overflow-tooltip />
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
import { listMerchantBankFlowRows, type MerchantBankFlowRow } from "@/api/merchantReconciliation";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatAccountingPeriod, formatAmount, selectedMonthParts } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationBankFlows" });

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
const tableData = ref<MerchantBankFlowRow[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });

function queryParams() {
    const selected = selectedMonthParts(searchForm.month);
    return {
        org_id: searchForm.orgId,
        accounting_year: selected.accounting_year || undefined,
        accounting_month: selected.accounting_month || undefined,
        keyword: searchForm.keyword || undefined,
        page: pagination.page,
        page_size: pagination.pageSize,
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const result = await listMerchantBankFlowRows(queryParams());
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

function summaryMethod({ columns, data }: { columns: any[]; data: MerchantBankFlowRow[] }) {
    const moneyProps = new Set(["debit_amount", "credit_amount", "flow_amount"]);
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

.text-muted {
    color: var(--text-tertiary);
}
</style>
