<template>
    <div class="page-container page-container--flow checklist-page">
        <el-card shadow="never" class="search-card checklist-filter-card">
            <el-form :model="filters" inline class="filter-form">
                <el-form-item v-if="userStore.isSuperAdmin" label="组织" class="filter-field">
                    <el-select v-model="filters.org_id" clearable filterable placeholder="组织">
                        <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
                    </el-select>
                </el-form-item>
                <el-form-item label="数据年月" class="filter-field filter-field--month">
                    <el-date-picker
                        v-model="filters.month"
                        type="month"
                        value-format="YYYY-MM"
                        placeholder="选择数据年月"
                        clearable
                        @change="handlePeriodChange"
                    />
                </el-form-item>
                <el-form-item label="商户主体名称" class="filter-field">
                    <el-select
                        v-model="filters.merchant_subject_names"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="(keyword: string) => fetchOptions('merchant_subject', keyword)"
                        :loading="optionLoading.merchant_subject"
                        placeholder="商户主体名称"
                    >
                        <el-option v-for="item in options.merchant_subject" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item label="收款商家" class="filter-field">
                    <el-select
                        v-model="filters.receipt_merchants"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="(keyword: string) => fetchOptions('receipt_merchant', keyword)"
                        :loading="optionLoading.receipt_merchant"
                        placeholder="收款商家"
                    >
                        <el-option v-for="item in options.receipt_merchant" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item v-if="summaryMode === 'product'" label="商品名称" class="filter-field">
                    <el-select
                        v-model="filters.product_names"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="(keyword: string) => fetchOptions('product_name', keyword)"
                        :loading="optionLoading.product_name"
                        placeholder="商品名称"
                    >
                        <el-option v-for="item in options.product_name" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item v-if="summaryMode === 'receipt'" label="直播平台" class="filter-field">
                    <el-select
                        v-model="filters.live_platforms"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="(keyword: string) => fetchOptions('live_platform', keyword)"
                        :loading="optionLoading.live_platform"
                        placeholder="进驻的直播平台"
                    >
                        <el-option v-for="item in options.live_platform" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item label="关键词" class="filter-field">
                    <el-input v-model="filters.keyword" clearable :placeholder="keywordPlaceholder" @keyup.enter="handleSearch" />
                </el-form-item>
                <el-form-item class="filter-actions">
                    <el-button type="primary" @click="handleSearch">查询</el-button>
                    <el-button @click="resetFilters">重置</el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">{{ pageTitle }}</span>
                        <span class="summary-count">共 {{ pagination.total }} 条 · 已选 {{ selectedCount }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="selectedCount === 0" @click="clearSelectedRows">清空选中</el-button>
                        <el-button :loading="exportSelectedLoading" :disabled="selectedCount === 0" @click="handleExport('selected')">导出选中</el-button>
                        <el-button @click="fetchData">刷新</el-button>
                        <el-button :loading="exportCurrentPageLoading" @click="handleExport('current_page')">导出当前页</el-button>
                        <el-button type="primary" :loading="exportAllLoading" @click="handleExport('all')">全部导出</el-button>
                    </div>
                </div>
            </template>

            <el-table
                v-if="summaryMode === 'product'"
                v-loading="loading"
                :data="productRows"
                border
                stripe
                row-key="key"
                class="summary-table roomy-table"
                style="width: 100%"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ rowIndex($index) }}</template>
                </el-table-column>
                <el-table-column label="数据年月" width="110">
                    <template #default="{ row }">{{ formatChecklistMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="150" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" min-width="170" show-overflow-tooltip />
                <el-table-column prop="merchant_subject_name" label="商户主体名称" min-width="180" show-overflow-tooltip />
                <el-table-column prop="product_name" label="商品名称" min-width="260" show-overflow-tooltip />
                <el-table-column prop="product_quantity" label="商品数量" width="110" align="right" />
                <el-table-column label="用户实付" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_user_paid_amount) }}</template>
                </el-table-column>
                <el-table-column label="直播推广佣金" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_live_commission) }}</template>
                </el-table-column>
                <el-table-column
                    label="应付商家净额"
                    width="150"
                    align="right"
                    class-name="summary-edge-column"
                    header-class-name="summary-edge-column"
                >
                    <template #default="{ row }">{{ formatAmount(row.total_merchant_net_amount) }}</template>
                </el-table-column>
            </el-table>

            <el-table
                v-else-if="summaryMode === 'receipt'"
                v-loading="loading"
                :data="receiptRows"
                border
                stripe
                row-key="key"
                class="summary-table roomy-table"
                style="width: 100%"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ rowIndex($index) }}</template>
                </el-table-column>
                <el-table-column label="数据年月" width="110">
                    <template #default="{ row }">{{ formatChecklistMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="150" show-overflow-tooltip />
                <el-table-column prop="merchant_subject_name" label="商户主体名称" min-width="190" show-overflow-tooltip />
                <el-table-column prop="live_platform" label="进驻的直播平台" min-width="150" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" min-width="190" show-overflow-tooltip />
                <el-table-column prop="order_count" label="订单数" width="100" align="right" />
                <el-table-column label="用户实付" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_user_paid_amount) }}</template>
                </el-table-column>
                <el-table-column label="直播推广佣金" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_live_commission) }}</template>
                </el-table-column>
                <el-table-column
                    label="应付商家净额"
                    width="150"
                    align="right"
                    class-name="summary-edge-column"
                    header-class-name="summary-edge-column"
                >
                    <template #default="{ row }">{{ formatAmount(row.total_merchant_net_amount) }}</template>
                </el-table-column>
            </el-table>

            <el-table
                v-else
                v-loading="loading"
                :data="payableBalanceRows"
                border
                stripe
                row-key="key"
                class="summary-table roomy-table"
                style="width: 100%"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ rowIndex($index) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="150" show-overflow-tooltip />
                <el-table-column prop="merchant_subject_name" label="商户主体名称" min-width="210" show-overflow-tooltip />
                <el-table-column label="结算时间（年月）" width="140">
                    <template #default="{ row }">{{ formatChecklistMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column prop="receipt_merchant" label="收款商家" min-width="210" show-overflow-tooltip />
                <el-table-column label="用户实付" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_user_paid_amount) }}</template>
                </el-table-column>
                <el-table-column label="应付商家净额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_merchant_net_amount) }}</template>
                </el-table-column>
                <el-table-column label="付款金额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.total_payment_amount) }}</template>
                </el-table-column>
                <el-table-column
                    label="应付商家净额余额"
                    width="180"
                    align="right"
                    class-name="summary-edge-column"
                    header-class-name="summary-edge-column"
                >
                    <template #default="{ row }">{{ formatAmount(row.total_merchant_net_balance) }}</template>
                </el-table-column>
            </el-table>

            <div class="pagination-area" style="padding: 12px 18px; margin-top: 0; border-top: 1px solid var(--border-light); background: var(--bg-elevated);">
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
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    listReconciliationChecklistOptions,
    listReconciliationChecklistPayableBalanceSummary,
    listReconciliationChecklistProductSummary,
    listReconciliationChecklistReceiptSummary,
    type ReconciliationChecklistOption,
    type ReconciliationChecklistPayableBalanceSummary,
    type ReconciliationChecklistProductSummary,
    type ReconciliationChecklistReceiptSummary,
} from "@/api/reconciliationChecklist";
import { useUserStore } from "@/stores/user";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import { buildExportFilename } from "@/utils/format";
import { formatAmount, formatChecklistMonth } from "./common";
import { useRoute, useRouter } from "vue-router";

type SummaryMode = "product" | "receipt" | "payable_balance";
type ExportScope = "all" | "current_page" | "selected";
type OptionKind = "merchant_subject" | "receipt_merchant" | "live_platform" | "product_name";
type SummaryRow =
    | ReconciliationChecklistProductSummary
    | ReconciliationChecklistReceiptSummary
    | ReconciliationChecklistPayableBalanceSummary;

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const orgOptions = ref<Organization[]>([]);
const loading = ref(false);
const productRows = ref<ReconciliationChecklistProductSummary[]>([]);
const receiptRows = ref<ReconciliationChecklistReceiptSummary[]>([]);
const payableBalanceRows = ref<ReconciliationChecklistPayableBalanceSummary[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const selectedRowMap = ref(new Map<string, SummaryRow>());
const selectedCount = computed(() => selectedRowMap.value.size);
const selectedRows = computed(() => Array.from(selectedRowMap.value.values()));
const exportSelectedLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportAllLoading = ref(false);
const querySyncing = ref(false);
const SUMMARY_PAGE_STATE_KEY_PREFIX = "reconciliation-checklist:summary:";
const SUMMARY_QUERY_KEYS = [
    "page",
    "page_size",
    "org_id",
    "month",
    "merchant_subject_name",
    "receipt_merchant",
    "product_name",
    "live_platform",
    "keyword",
] as const;

const summaryMode = computed<SummaryMode>(() => {
    const raw = route.meta.checklistSummaryMode;
    return raw === "product" || raw === "payable_balance" ? raw : "receipt";
});
const pageTitle = computed(() => {
    if (summaryMode.value === "product") return "商家明细";
    if (summaryMode.value === "payable_balance") return "余额明细";
    return "商家总表";
});
const keywordPlaceholder = computed(() => {
    if (summaryMode.value === "product") return "主体 / 收款商家 / 商品";
    if (summaryMode.value === "receipt") return "主体 / 收款商家 / 平台";
    return "主体 / 收款商家";
});

const filters = reactive({
    org_id: undefined as number | undefined,
    month: "",
    merchant_subject_names: [] as string[],
    receipt_merchants: [] as string[],
    product_names: [] as string[],
    live_platforms: [] as string[],
    keyword: "",
});

const options = reactive<Record<OptionKind, ReconciliationChecklistOption[]>>({
    merchant_subject: [],
    receipt_merchant: [],
    live_platform: [],
    product_name: [],
});
const optionLoading = reactive<Record<OptionKind, boolean>>({
    merchant_subject: false,
    receipt_merchant: false,
    live_platform: false,
    product_name: false,
});

const monthParts = computed(() => {
    if (!filters.month) return {};
    const [year, month] = filters.month.split("-").map(Number);
    if (!year || !month) return {};
    return { accounting_year: year, accounting_month: month };
});

function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function currentRows(): SummaryRow[] {
    if (summaryMode.value === "product") return productRows.value;
    if (summaryMode.value === "payable_balance") return payableBalanceRows.value;
    return receiptRows.value;
}

function joinValues(values: string[]) {
    return values.map((item) => item.trim()).filter(Boolean).join(",") || undefined;
}

function rowIndex(index: number) {
    return (pagination.page - 1) * pagination.pageSize + index + 1;
}

function queryString(value: unknown): string {
    if (Array.isArray(value)) return value.filter(Boolean).join(",");
    return typeof value === "string" ? value : "";
}

function queryStringList(value: unknown): string[] {
    const text = queryString(value);
    return text ? text.split(",").map((item) => item.trim()).filter(Boolean) : [];
}

function baseParams() {
    return {
        org_id: filters.org_id,
        ...monthParts.value,
        merchant_subject_name: joinValues(filters.merchant_subject_names),
        receipt_merchant: joinValues(filters.receipt_merchants),
        product_name: summaryMode.value === "product" ? joinValues(filters.product_names) : undefined,
        live_platform: summaryMode.value === "receipt" ? joinValues(filters.live_platforms) : undefined,
        keyword: filters.keyword || undefined,
    };
}

function applyRouteQuery() {
    const page = Number(route.query.page);
    const pageSize = Number(route.query.page_size);
    const orgId = Number(route.query.org_id);
    pagination.page = Number.isFinite(page) && page > 0 ? page : 1;
    pagination.pageSize = Number.isFinite(pageSize) && pageSize > 0 ? pageSize : DEFAULT_PAGE_SIZE;
    filters.org_id = Number.isFinite(orgId) && orgId > 0 ? orgId : undefined;
    filters.month = queryString(route.query.month) || currentMonth();
    filters.merchant_subject_names = queryStringList(route.query.merchant_subject_name);
    filters.receipt_merchants = queryStringList(route.query.receipt_merchant);
    filters.product_names = queryStringList(route.query.product_name);
    filters.live_platforms = queryStringList(route.query.live_platform);
    filters.keyword = queryString(route.query.keyword);
}

function pageStateKey() {
    return `${SUMMARY_PAGE_STATE_KEY_PREFIX}${summaryMode.value}`;
}

function hasRouteState() {
    return SUMMARY_QUERY_KEYS.some((key) => {
        const value = route.query[key];
        return Array.isArray(value) ? value.some(Boolean) : value !== undefined && value !== "";
    });
}

function restorePageState() {
    if (hasRouteState()) {
        applyRouteQuery();
        return;
    }
    const raw = sessionStorage.getItem(pageStateKey());
    if (!raw) {
        applyRouteQuery();
        return;
    }
    try {
        const state = JSON.parse(raw) as {
            page?: number;
            pageSize?: number;
            org_id?: number | null;
            month?: string;
            merchant_subject_names?: string[];
            receipt_merchants?: string[];
            product_names?: string[];
            live_platforms?: string[];
            keyword?: string;
        };
        pagination.page = state.page && state.page > 0 ? state.page : 1;
        pagination.pageSize = state.pageSize && state.pageSize > 0 ? state.pageSize : DEFAULT_PAGE_SIZE;
        filters.org_id = state.org_id || undefined;
        filters.month = state.month || currentMonth();
        filters.merchant_subject_names = Array.isArray(state.merchant_subject_names) ? state.merchant_subject_names : [];
        filters.receipt_merchants = Array.isArray(state.receipt_merchants) ? state.receipt_merchants : [];
        filters.product_names = Array.isArray(state.product_names) ? state.product_names : [];
        filters.live_platforms = Array.isArray(state.live_platforms) ? state.live_platforms : [];
        filters.keyword = state.keyword || "";
    } catch {
        applyRouteQuery();
    }
}

function persistPageState() {
    sessionStorage.setItem(
        pageStateKey(),
        JSON.stringify({
            page: pagination.page,
            pageSize: pagination.pageSize,
            org_id: filters.org_id ?? null,
            month: filters.month,
            merchant_subject_names: filters.merchant_subject_names,
            receipt_merchants: filters.receipt_merchants,
            product_names: filters.product_names,
            live_platforms: filters.live_platforms,
            keyword: filters.keyword,
        }),
    );
}

function buildRouteQuery() {
    return {
        page: String(pagination.page),
        page_size: String(pagination.pageSize),
        org_id: filters.org_id ? String(filters.org_id) : undefined,
        month: filters.month || undefined,
        merchant_subject_name: joinValues(filters.merchant_subject_names),
        receipt_merchant: joinValues(filters.receipt_merchants),
        product_name: summaryMode.value === "product" ? joinValues(filters.product_names) : undefined,
        live_platform: summaryMode.value === "receipt" ? joinValues(filters.live_platforms) : undefined,
        keyword: filters.keyword || undefined,
    };
}

async function syncRouteQuery() {
    querySyncing.value = true;
    try {
        await router.replace({ query: buildRouteQuery() });
    } finally {
        querySyncing.value = false;
    }
}

async function fetchOrgs() {
    if (userStore.isSuperAdmin) orgOptions.value = await getAllOrganizations();
}

async function fetchOptions(kind: OptionKind, keyword = "") {
    optionLoading[kind] = true;
    try {
        options[kind] = await listReconciliationChecklistOptions({
            kind,
            ...monthParts.value,
            org_id: filters.org_id,
            keyword: keyword || undefined,
            limit: 50,
        });
    } finally {
        optionLoading[kind] = false;
    }
}

async function fetchAllOptions() {
    await Promise.all([
        fetchOptions("merchant_subject"),
        fetchOptions("receipt_merchant"),
        fetchOptions("product_name"),
        fetchOptions("live_platform"),
    ]);
}

function clearRows() {
    productRows.value = [];
    receiptRows.value = [];
    payableBalanceRows.value = [];
}

async function fetchData() {
    await syncRouteQuery();
    persistPageState();
    loading.value = true;
    try {
        const params = {
            ...baseParams(),
            page: pagination.page,
            page_size: pagination.pageSize,
        };
        clearRows();
        if (summaryMode.value === "product") {
            const res = await listReconciliationChecklistProductSummary(params);
            productRows.value = res.items;
            pagination.total = res.total || 0;
        } else if (summaryMode.value === "payable_balance") {
            const res = await listReconciliationChecklistPayableBalanceSummary(params);
            payableBalanceRows.value = res.items;
            pagination.total = res.total || 0;
        } else {
            const res = await listReconciliationChecklistReceiptSummary(params);
            receiptRows.value = res.items;
            pagination.total = res.total || 0;
        }
    } finally {
        loading.value = false;
    }
}

function handleSelectionChange(rows: SummaryRow[]) {
    const currentPageKeys = new Set(currentRows().map((row) => row.key));
    const nextMap = new Map(selectedRowMap.value);
    currentPageKeys.forEach((key) => nextMap.delete(key));
    rows.forEach((row) => nextMap.set(row.key, row));
    selectedRowMap.value = nextMap;
}

function clearSelectedRows() {
    selectedRowMap.value = new Map();
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handlePeriodChange() {
    filters.merchant_subject_names = [];
    filters.receipt_merchants = [];
    filters.product_names = [];
    filters.live_platforms = [];
    fetchAllOptions();
}

function resetFilters() {
    filters.org_id = undefined;
    filters.month = currentMonth();
    filters.merchant_subject_names = [];
    filters.receipt_merchants = [];
    filters.product_names = [];
    filters.live_platforms = [];
    filters.keyword = "";
    clearSelectedRows();
    fetchAllOptions();
    handleSearch();
}

function exportMeta() {
    if (summaryMode.value === "product") {
        return {
            exportType: "reconciliation_checklist.product_summary",
            title: "商家明细导出",
            filenamePrefix: "商家明细",
        };
    }
    if (summaryMode.value === "payable_balance") {
        return {
            exportType: "reconciliation_checklist.payable_balance_summary",
            title: "商家应付余额明细导出",
            filenamePrefix: "商家应付余额明细",
        };
    }
    return {
        exportType: "reconciliation_checklist.receipt_summary",
        title: "商家总表导出",
        filenamePrefix: "商家总表",
    };
}

async function handleExport(scope: ExportScope) {
    if (scope === "selected" && selectedRows.value.length === 0) {
        ElMessage.warning("请先选择要导出的汇总数据");
        return;
    }
    const loadingRef =
        scope === "selected" ? exportSelectedLoading : scope === "current_page" ? exportCurrentPageLoading : exportAllLoading;
    const meta = exportMeta();
    loadingRef.value = true;
    try {
        await submitExportJob({
            export_type: meta.exportType,
            title: meta.title,
            filename: normalizeExportFilename(
                buildExportFilename([
                    meta.filenamePrefix,
                    filters.month || "全部年月",
                    scope === "current_page" ? `第${pagination.page}页` : scope === "selected" ? "选中" : "全部",
                ]),
            ),
            params: {
                ...baseParams(),
                scope,
                ids: scope === "selected" ? selectedRows.value.map((row) => row.key) : undefined,
                page: scope === "current_page" ? pagination.page : undefined,
                page_size: scope === "current_page" ? pagination.pageSize : undefined,
            },
        });
    } finally {
        loadingRef.value = false;
    }
}

onMounted(async () => {
    restorePageState();
    if (!filters.month) filters.month = currentMonth();
    await fetchOrgs();
    await fetchAllOptions();
    await fetchData();
});

watch(
    () => summaryMode.value,
    () => {
        clearSelectedRows();
    },
);

watch(
    () => route.fullPath,
    async () => {
        if (querySyncing.value) return;
        restorePageState();
        await fetchAllOptions();
        await fetchData();
    },
);
</script>

<style scoped lang="scss">
.checklist-page {
    display: block;
    height: auto;
    min-height: 100%;
    gap: 14px;
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.checklist-filter-card {
    display: block;
    margin-bottom: 14px;
    overflow: visible;
}

:deep(.checklist-filter-card .el-card__body) {
    flex: none;
    height: auto;
    overflow: visible;
    padding: 12px 16px;
}

:deep(.checklist-filter-card .el-form.el-form--inline) {
    display: grid !important;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) auto;
    align-items: center;
    gap: 10px 12px;
}

:deep(.checklist-filter-card .filter-form .el-form-item) {
    margin: 0;
    min-width: 0;
}

:deep(.checklist-filter-card .filter-form .el-form-item__content) {
    margin-left: 0 !important;
}

:deep(.checklist-filter-card .filter-field .el-input),
:deep(.checklist-filter-card .filter-field .el-select),
:deep(.checklist-filter-card .filter-field .el-date-editor) {
    width: 100% !important;
}

:deep(.checklist-filter-card .filter-actions .el-form-item__content) {
    flex-wrap: nowrap;
    gap: 8px;
}

.summary-title-group {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
    flex-wrap: wrap;
}

.card-header-title {
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
}

.summary-count {
    color: var(--text-tertiary);
    font-size: 12px;
}

.card-header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-shrink: 0;
    min-width: 0;
    margin-top: 0;
    padding: 12px 18px !important;
    border-top: 1px solid var(--border-light);
    background: var(--bg-elevated);
    overflow-x: auto;
    overflow-y: hidden;

    :deep(.el-pagination) {
        flex-shrink: 0;
        min-width: max-content;
    }
}

:deep(.table-card .el-card__body) {
    overflow: hidden;
}

:deep(.table-card .el-table) {
    flex: 0 0 auto;
}

:deep(.summary-table .summary-edge-column .cell),
:deep(.summary-table th.summary-edge-column .cell) {
    padding-right: 18px !important;
}

:deep(.table-card .pagination-area) {
    padding: 12px 18px !important;
    margin-top: 0;
    border-top: 1px solid var(--border-light);
    background: var(--bg-elevated);
}

@media (max-width: 900px) {
    .card-header {
        align-items: flex-start;
        flex-direction: column;
    }

    :deep(.checklist-filter-card .el-form.el-form--inline) {
        grid-template-columns: 1fr;
    }

    .card-header-actions {
        width: 100%;
    }
}
</style>
