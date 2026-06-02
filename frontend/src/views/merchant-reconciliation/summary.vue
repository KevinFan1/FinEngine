<template>
    <div class="page-container transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            show-bank-status
            keyword-placeholder="我方主体/收款商家"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">汇总数据</span>
                        <span class="summary-count">{{ tableSummaryText }}</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="loading" @click="selectCurrentMonth">
                            <el-icon><Calendar /></el-icon>
                            本月
                        </el-button>
                        <el-button type="primary" :disabled="!hasSelectedMonth" :loading="exportLoading" @click="handleExport">
                            <el-icon><Download /></el-icon>
                            导出
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth" :loading="openingDrawerLoading" @click="openOpeningDrawer">
                            <el-icon><EditPen /></el-icon>
                            维护期初金额
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth" @click="fetchData(true)">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>
            </template>

            <div v-if="!hasSelectedMonth" class="summary-empty-guide">
                <div class="summary-empty-icon">
                    <el-icon><Calendar /></el-icon>
                </div>
                <div class="summary-empty-content">
                    <p class="summary-empty-kicker">需要先确定业务年月</p>
                    <h2>选择月份后生成商家应付、冲减和未付流水汇总</h2>
                    <p>汇总会按我方主体与收款商家聚合，适合导出给财务复核。当前不是 0 条数据，而是还没有选定查询口径。</p>
                    <div class="summary-empty-actions">
                        <el-button type="primary" @click="selectCurrentMonth">
                            <el-icon><Calendar /></el-icon>
                            查看本月
                        </el-button>
                        <el-button @click="handleReset">清空筛选</el-button>
                    </div>
                </div>
                <div class="summary-empty-preview" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                </div>
            </div>

            <el-table
                v-else
                class="summary-table roomy-table merchant-summary-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                show-summary
                :summary-method="summaryMethod"
            >
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column label="年月" width="110" fixed="left">
                    <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="160" show-overflow-tooltip />
                <el-table-column prop="our_subject" label="我方主体" width="180" show-overflow-tooltip />
                <el-table-column prop="merchant_receipt_subject" label="商家收款主体" min-width="320" show-overflow-tooltip />
                <el-table-column prop="gmv" label="实收GMV" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.gmv) }}</template>
                </el-table-column>
                <el-table-column prop="merchant_payable_net_amount" label="应付商家净额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.merchant_payable_net_amount) }}</template>
                </el-table-column>
                <el-table-column prop="opening_balance" label="期初余额" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.opening_balance) }}</template>
                </el-table-column>
                <el-table-column prop="business_fee_deduction" label="冲减业务费用" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.business_fee_deduction) }}</template>
                </el-table-column>
                <el-table-column prop="other_deduction_amount" label="其他冲减金额" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.other_deduction_amount) }}</template>
                </el-table-column>
                <el-table-column prop="payable_goods_balance" label="应付货款余额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.payable_goods_balance) }}</template>
                </el-table-column>
                <el-table-column prop="paid_flow_amount" label="已付流水" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.paid_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="unpaid_flow_amount" label="未付流水" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.unpaid_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="bank_flow_amount" label="银行流水汇总" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.bank_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="bank_payment_diff" label="银行付款差" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.bank_payment_diff) }}</template>
                </el-table-column>
                <el-table-column prop="bank_status" label="银行流水状态" width="130" align="center">
                    <template #default="{ row }">
                        <el-tag :type="bankStatusMeta(row.bank_status).type" size="small">{{ bankStatusMeta(row.bank_status).label }}</el-tag>
                    </template>
                </el-table-column>
            </el-table>

            <div v-if="hasSelectedMonth" class="pagination-area">
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

        <el-drawer
            v-model="openingDrawerVisible"
            title="维护期初金额"
            size="760px"
            class="opening-balance-drawer"
        >
            <div class="opening-toolbar">
                <el-input
                    v-model="openingKeyword"
                    clearable
                    placeholder="搜索我方主体/收款商家"
                >
                    <template #prefix>
                        <el-icon><Search /></el-icon>
                    </template>
                </el-input>
                <el-button :loading="openingDrawerLoading" @click="fetchOpeningBalances">
                    <el-icon><Refresh /></el-icon>
                    刷新
                </el-button>
            </div>

            <el-table
                class="summary-table roomy-table opening-balance-table"
                :data="filteredOpeningRows"
                v-loading="openingDrawerLoading"
                stripe
                border
            >
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="140" show-overflow-tooltip />
                <el-table-column prop="our_subject" label="我方主体" min-width="180" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" min-width="220" show-overflow-tooltip />
                <el-table-column prop="opening_balance" label="期初金额" width="180" align="right">
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.editing_balance"
                            :precision="2"
                            :step="100"
                            controls-position="right"
                            class="opening-balance-input"
                        />
                    </template>
                </el-table-column>
            </el-table>

            <template #footer>
                <div class="opening-drawer-footer">
                    <span>{{ openingFooterText }}</span>
                    <div>
                        <el-button @click="openingDrawerVisible = false">取消</el-button>
                        <el-button type="primary" :loading="openingSaving" :disabled="openingChangedRows.length === 0" @click="saveOpeningBalances">
                            保存
                        </el-button>
                    </div>
                </div>
            </template>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Calendar, Download, EditPen, Refresh, Search } from "@element-plus/icons-vue";
import {
    listMerchantOpeningBalances,
    listMerchantReconciliationSummary,
    upsertMerchantOpeningBalances,
    type MerchantOpeningBalance,
    type MerchantReconciliationSummary,
} from "@/api/merchantReconciliation";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import { buildExportFilename, summarizeFilenameValues } from "@/utils/format";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatAmount, formatMonth } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationSummary" });

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
const openingDrawerVisible = ref(false);
const openingDrawerLoading = ref(false);
const openingSaving = ref(false);
const openingKeyword = ref("");
const tableData = ref<MerchantReconciliationSummary[]>([]);
type OpeningBalanceRow = MerchantOpeningBalance & {
    editing_balance: number;
    original_balance: number;
};
const openingRows = ref<OpeningBalanceRow[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const hasSelectedMonth = computed(() => Boolean(searchForm.month));
const tableSummaryText = computed(() => {
    if (!hasSelectedMonth.value) return "待选择业务年月";
    return `共 ${pagination.total} 条`;
});

function currentMonthValue() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function queryParams(showMessage = true) {
    const [year, month] = String(searchForm.month || "").split("-").map(Number);
    if (!year || !month) {
        if (showMessage) {
            ElMessage.warning("请选择业务年月");
        }
        return null;
    }
    return {
        accounting_year: year,
        accounting_month: month,
        shop_id: typeof searchForm.shopId === "number" ? searchForm.shopId : undefined,
        org_id: searchForm.orgId,
        keyword: searchForm.keyword || undefined,
        bank_status: searchForm.bankStatus || undefined,
        page: pagination.page,
        page_size: pagination.pageSize,
    };
}

function bankStatusMeta(status: string) {
    const map: Record<string, { label: string; type: "success" | "warning" | "danger" | "info" }> = {
        matched: { label: "已匹配", type: "success" },
        diff: { label: "有差异", type: "danger" },
        pending: { label: "待匹配", type: "info" },
    };
    return map[status] || map.pending;
}

async function fetchData(showMessage = true) {
    const params = queryParams(showMessage);
    if (!params) {
        tableData.value = [];
        pagination.total = 0;
        return;
    }
    loading.value = true;
    try {
        const result = await listMerchantReconciliationSummary(params);
        tableData.value = result.items || [];
        pagination.total = result.total || 0;
    } finally {
        loading.value = false;
    }
}

async function selectCurrentMonth() {
    searchForm.month = currentMonthValue();
    pagination.page = 1;
    await fetchData(false);
}

async function handleExport() {
    const params = queryParams(true);
    if (!params) return;
    exportLoading.value = true;
    try {
        const selectedShop = douyinShops.value.find((shop) => shop.id === Number(searchForm.shopId || 0));
        await submitExportJob({
            export_type: "merchant_reconciliation.summary",
            title: "商家对账汇总导出",
            filename: normalizeExportFilename(buildExportFilename([
                searchForm.month || "全部业务年月",
                `店铺${summarizeFilenameValues([selectedShop?.shop_name || ""], "全部")}`,
                "商家对账汇总",
            ])),
            params,
        });
    } finally {
        exportLoading.value = false;
    }
}

function openingQueryParams(showMessage = true) {
    const params = queryParams(showMessage);
    if (!params) return null;
    return {
        accounting_year: params.accounting_year,
        accounting_month: params.accounting_month,
        shop_id: params.shop_id,
        org_id: params.org_id,
    };
}

const openingChangedRows = computed(() =>
    openingRows.value.filter((row) => Number(row.editing_balance || 0).toFixed(2) !== Number(row.original_balance || 0).toFixed(2)),
);

const filteredOpeningRows = computed(() => {
    const keyword = openingKeyword.value.trim().toLowerCase();
    if (!keyword) return openingRows.value;
    return openingRows.value.filter((row) =>
        String(row.our_subject || "").toLowerCase().includes(keyword)
        || String(row.receipt_merchant || "").toLowerCase().includes(keyword),
    );
});

const openingFooterText = computed(() => {
    if (openingRows.value.length === 0) return "暂无可维护数据";
    return `当前显示 ${filteredOpeningRows.value.length} 条，已修改 ${openingChangedRows.value.length} 条`;
});

async function openOpeningDrawer() {
    if (!openingQueryParams(true)) return;
    openingDrawerVisible.value = true;
    await fetchOpeningBalances();
}

async function fetchOpeningBalances() {
    const params = openingQueryParams(true);
    if (!params) return;
    openingDrawerLoading.value = true;
    try {
        const rows = await listMerchantOpeningBalances(params);
        openingRows.value = (rows || []).map((row) => {
            const balance = Number(row.opening_balance || 0);
            return {
                ...row,
                editing_balance: balance,
                original_balance: balance,
            };
        });
    } finally {
        openingDrawerLoading.value = false;
    }
}

async function saveOpeningBalances() {
    const params = queryParams(true);
    if (!params) return;
    const rows = openingChangedRows.value;
    if (rows.length === 0) {
        ElMessage.info("没有需要保存的期初金额");
        return;
    }
    openingSaving.value = true;
    try {
        const result = await upsertMerchantOpeningBalances({
            accounting_year: params.accounting_year,
            accounting_month: params.accounting_month,
            platform_code: "douyin",
            items: rows.map((row) => ({
                org_id: row.org_id,
                our_subject: row.our_subject,
                receipt_merchant: row.receipt_merchant,
                opening_balance: row.editing_balance || 0,
                remark: row.remark || "",
            })),
        });
        ElMessage.success(`已保存 ${result.total_count || rows.length} 条期初金额`);
        openingRows.value = openingRows.value.map((row) => ({
            ...row,
            original_balance: Number(row.editing_balance || 0),
        }));
        await fetchData(false);
    } finally {
        openingSaving.value = false;
    }
}

async function handleSearch() {
    pagination.page = 1;
    await fetchData(true);
}

async function handleReset() {
    resetFilters();
    await fetchShops();
    pagination.page = 1;
    await fetchData(false);
}

async function handleSizeChange(size: number) {
    pagination.pageSize = size;
    pagination.page = 1;
    await fetchData(false);
}

async function handlePageChange(page: number) {
    pagination.page = page;
    await fetchData(false);
}

function summaryMethod({ columns, data }: { columns: any[]; data: MerchantReconciliationSummary[] }) {
    const moneyProps = new Set(["gmv", "merchant_payable_net_amount", "opening_balance", "business_fee_deduction", "other_deduction_amount", "payable_goods_balance", "paid_flow_amount", "unpaid_flow_amount", "bank_flow_amount", "bank_payment_diff"]);
    return columns.map((column, index) => {
        if (index === 0) return "合计";
        if (!moneyProps.has(column.property)) return "";
        return formatAmount(data.reduce((total, row) => total + Number((row as any)[column.property] || 0), 0));
    });
}

onMounted(async () => {
    await fetchOrgs();
    await fetchShops();
    await fetchData(false);
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";

.summary-note {
    margin-bottom: 12px;
}

.opening-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
}

.opening-toolbar .el-input {
    max-width: 320px;
}

.opening-balance-table {
    width: 100%;
}

.opening-balance-input {
    width: 150px;
}

.opening-drawer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    color: var(--text-secondary);
}

.merchant-summary-table {
    width: 100%;

    :deep(.el-table__header),
    :deep(.el-table__body),
    :deep(.el-table__footer) {
        table-layout: auto !important;
    }

    :deep(.el-table__header colgroup col[width="320"]),
    :deep(.el-table__body colgroup col[width="320"]),
    :deep(.el-table__footer colgroup col[width="320"]) {
        width: auto !important;
    }

    :deep(.el-table__empty-block) {
        min-height: 220px;
    }
}

.summary-empty-guide {
    position: relative;
    display: grid;
    grid-template-columns: 54px minmax(0, 1fr) 220px;
    gap: 18px;
    align-items: center;
    min-height: 230px;
    padding: 26px;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius-card);
    background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
    overflow: hidden;
}

.summary-empty-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border: 1px solid var(--primary-light-7);
    border-radius: var(--radius-card);
    background: var(--primary-light-9);
    color: var(--primary);
    font-size: 26px;
}

.summary-empty-content {
    min-width: 0;

    h2 {
        margin: 0 0 8px;
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 700;
        line-height: 1.35;
        letter-spacing: 0;
    }

    p {
        max-width: 660px;
        margin: 0;
        color: var(--text-secondary);
        font-size: 13px;
        line-height: 1.65;
    }
}

.summary-empty-kicker {
    margin-bottom: 5px !important;
    color: var(--primary) !important;
    font-size: 12px !important;
    font-weight: 700;
}

.summary-empty-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
}

.summary-empty-preview {
    display: grid;
    gap: 10px;
    padding: 16px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);

    span {
        display: block;
        height: 20px;
        border-radius: 4px;
        background: linear-gradient(90deg, var(--primary-light-9), var(--bg-hover));

        &:nth-child(2) {
            width: 82%;
        }

        &:nth-child(3) {
            width: 64%;
        }
    }
}

@media (max-width: 920px) {
    .table-card :deep(.card-header) {
        align-items: stretch;
        flex-direction: column;
    }

    .table-card :deep(.card-header-actions) {
        justify-content: flex-start;
    }

    .summary-empty-guide {
        grid-template-columns: 54px minmax(0, 1fr);
    }

    .summary-empty-preview {
        display: none;
    }
}

@media (max-width: 640px) {
    .summary-empty-guide {
        grid-template-columns: 1fr;
        padding: 18px;
    }

    .summary-empty-content h2 {
        font-size: 16px;
    }
}
</style>
