<template>
    <div class="page-container checklist-page">
        <el-card shadow="never" class="search-card checklist-filter-card">
            <el-form :model="filters" inline class="filter-form">
                <el-form-item
                    v-if="userStore.isSuperAdmin"
                    label="组织"
                    class="filter-field"
                >
                    <el-select
                        v-model="filters.org_id"
                        clearable
                        filterable
                        placeholder="组织"
                    >
                        <el-option
                            v-for="org in orgOptions"
                            :key="org.id"
                            :label="org.name"
                            :value="org.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item
                    label="年月"
                    class="filter-field filter-field--month"
                >
                    <el-date-picker
                        v-model="filters.month"
                        type="month"
                        value-format="YYYY-MM"
                        placeholder="年月"
                        :clearable="false"
                        @change="handleMonthChange"
                    />
                </el-form-item>
                <el-form-item label="直播推广方" class="filter-field">
                    <el-select
                        v-model="filters.live_promoter_ids"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="
                            (keyword: string) =>
                                fetchEntityOptions('live_promoter', keyword)
                        "
                        :loading="entityLoading.live_promoter"
                        placeholder="先选年月，再选推广方"
                    >
                        <el-option
                            v-for="item in entityOptions.live_promoter"
                            :key="item.id"
                            :label="entityLabel(item)"
                            :value="item.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="商家" class="filter-field">
                    <el-select
                        v-model="filters.merchant_ids"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="
                            (keyword: string) =>
                                fetchEntityOptions('merchant', keyword)
                        "
                        :loading="entityLoading.merchant"
                        placeholder="先选年月，再选商家"
                    >
                        <el-option
                            v-for="item in entityOptions.merchant"
                            :key="item.id"
                            :label="entityLabel(item)"
                            :value="item.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="收款商家" class="filter-field">
                    <el-select
                        v-model="filters.receipt_merchant_ids"
                        multiple
                        clearable
                        filterable
                        remote
                        collapse-tags
                        collapse-tags-tooltip
                        :remote-method="
                            (keyword: string) =>
                                fetchEntityOptions('receipt_merchant', keyword)
                        "
                        :loading="entityLoading.receipt_merchant"
                        placeholder="先选年月，再选收款商家"
                    >
                        <el-option
                            v-for="item in entityOptions.receipt_merchant"
                            :key="item.id"
                            :label="entityLabel(item)"
                            :value="item.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="关键词" class="filter-field">
                    <el-input
                        v-model="filters.keyword"
                        clearable
                        placeholder="关键词：商品名称 / 店铺 / 商家"
                        @keyup.enter="handleSearch"
                    />
                </el-form-item>
                <el-form-item class="filter-actions">
                    <el-button type="primary" @click="handleSearch"
                        >查询</el-button
                    >
                    <el-button @click="resetFilters">重置</el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">对账清单汇总</span>
                        <span class="summary-count"
                            >共 {{ pagination.total }} 条</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <el-button @click="fetchData">刷新</el-button>
                        <el-button
                            :loading="exportCurrentPageLoading"
                            @click="handleExport('current_page')"
                            >导出当前页</el-button
                        >
                        <el-button
                            :loading="exportAllLoading"
                            @click="handleExport('all')"
                            >全部导出</el-button
                        >
                        <el-button
                            type="primary"
                            :loading="exportSelectedLoading"
                            :disabled="selectedRows.length === 0"
                            @click="handleExport('selected')"
                            >导出选中</el-button
                        >
                    </div>
                </div>
            </template>

            <el-table
                ref="summaryTable"
                v-loading="loading"
                :data="rows"
                border
                stripe
                row-key="key"
                class="summary-table roomy-table"
                @selection-change="handleSelectionChange"
            >
                <el-table-column
                    type="selection"
                    width="48"
                    reserve-selection
                />
                <el-table-column label="年月" width="110">
                    <template #default="{ row }">{{
                        formatChecklistMonth(
                            row.accounting_year,
                            row.accounting_month,
                        )
                    }}</template>
                </el-table-column>
                <el-table-column
                    v-if="userStore.isSuperAdmin"
                    prop="org_name"
                    label="组织"
                    width="150"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="live_promoter"
                    label="直播推广方"
                    min-width="170"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="merchant_name"
                    label="商家"
                    min-width="170"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="receipt_merchant"
                    label="收款商家"
                    min-width="180"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="product_quantity"
                    label="明细数量"
                    width="110"
                    align="right"
                />
                <el-table-column label="订单总金额" width="150" align="right">
                    <template #default="{ row }">{{
                        formatAmount(row.total_order_amount)
                    }}</template>
                </el-table-column>
                <el-table-column
                    label="直播佣金总金额"
                    width="160"
                    align="right"
                >
                    <template #default="{ row }">{{
                        formatAmount(row.total_live_commission)
                    }}</template>
                </el-table-column>
                <el-table-column
                    label="应付商家净额总金额"
                    width="180"
                    align="right"
                >
                    <template #default="{ row }">{{
                        formatAmount(row.total_merchant_net_amount)
                    }}</template>
                </el-table-column>
                <el-table-column label="操作" width="110" fixed="right">
                    <template #default="{ row }">
                        <el-button link type="primary" @click="openDetails(row)"
                            >查看明细</el-button
                        >
                    </template>
                </el-table-column>
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

        <el-drawer
            v-model="detailVisible"
            title="商品汇总明细"
            size="1080px"
            class="checklist-detail-drawer"
        >
            <section v-if="currentSummary" class="detail-summary-card">
                <div class="detail-summary-heading">
                    <span>{{
                        formatChecklistMonth(
                            currentSummary.accounting_year,
                            currentSummary.accounting_month,
                        )
                    }}</span>
                    <strong>{{ currentSummary.merchant_name }}</strong>
                </div>
                <div class="detail-summary-grid">
                    <div class="detail-summary-item">
                        <span>收款商家</span>
                        <strong>{{ currentSummary.receipt_merchant }}</strong>
                    </div>
                    <div class="detail-summary-item">
                        <span>直播推广方</span>
                        <strong>{{ currentSummary.live_promoter }}</strong>
                    </div>
                    <div class="detail-summary-item">
                        <span>明细数量</span>
                        <strong>{{ currentSummary.product_quantity }}</strong>
                    </div>
                    <div class="detail-summary-item">
                        <span>订单总金额</span>
                        <strong>{{
                            formatAmount(currentSummary.total_order_amount)
                        }}</strong>
                    </div>
                    <div class="detail-summary-item">
                        <span>直播佣金总金额</span>
                        <strong>{{
                            formatAmount(currentSummary.total_live_commission)
                        }}</strong>
                    </div>
                    <div class="detail-summary-item">
                        <span>应付商家净额总金额</span>
                        <strong>{{
                            formatAmount(
                                currentSummary.total_merchant_net_amount,
                            )
                        }}</strong>
                    </div>
                </div>
            </section>
            <div class="detail-toolbar">
                <el-input
                    v-model="detailKeyword"
                    clearable
                    placeholder="搜索商品名称"
                    class="detail-keyword-input"
                    @keyup.enter="handleDetailSearch"
                    @clear="handleDetailSearch"
                />
                <el-button type="primary" @click="handleDetailSearch"
                    >搜索</el-button
                >
                <el-button
                    :loading="detailExportLoading"
                    :disabled="!currentSummary"
                    @click="exportCurrentDetail"
                    >导出</el-button
                >
            </div>
            <el-table
                v-loading="detailLoading"
                :data="detailRows"
                border
                stripe
            >
                <el-table-column
                    prop="product_name"
                    label="商品名称"
                    min-width="520"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="product_quantity"
                    label="明细数量"
                    width="90"
                    align="right"
                />
                <el-table-column label="订单金额" width="140" align="right">
                    <template #default="{ row }">{{
                        formatAmount(row.total_order_amount)
                    }}</template>
                </el-table-column>
                <el-table-column label="直播佣金" width="140" align="right">
                    <template #default="{ row }">{{
                        formatAmount(row.total_live_commission)
                    }}</template>
                </el-table-column>
                <el-table-column label="净额" width="140" align="right">
                    <template #default="{ row }">{{
                        formatAmount(row.total_merchant_net_amount)
                    }}</template>
                </el-table-column>
            </el-table>
            <el-pagination
                v-model:current-page="detailPagination.page"
                v-model:page-size="detailPagination.pageSize"
                :total="detailPagination.total"
                :page-sizes="PAGE_SIZE_OPTIONS"
                :layout="PAGINATION_LAYOUT"
                background
                @size-change="fetchDetails"
                @current-change="fetchDetails"
            />
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    listReconciliationChecklistEntityOptions,
    listReconciliationChecklistSummary,
    listReconciliationChecklistSummaryDetails,
    type ReconciliationChecklistEntityOption,
    type ReconciliationChecklistSummary,
    type ReconciliationChecklistSummaryDetail,
} from "@/api/reconciliationChecklist";
import { useUserStore } from "@/stores/user";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import { buildExportFilename } from "@/utils/format";
import { formatAmount, formatChecklistMonth } from "./common";
import { useRoute, useRouter } from "vue-router";

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const orgOptions = ref<Organization[]>([]);
const loading = ref(false);
const detailLoading = ref(false);
const rows = ref<ReconciliationChecklistSummary[]>([]);
const selectedRowMap = ref(new Map<string, ReconciliationChecklistSummary>());
const selectedRows = ref<ReconciliationChecklistSummary[]>([]);
const summaryTable = ref<{ clearSelection?: () => void } | null>(null);
const detailRows = ref<ReconciliationChecklistSummaryDetail[]>([]);
const detailVisible = ref(false);
const currentSummary = ref<ReconciliationChecklistSummary | null>(null);
const detailKeyword = ref("");
type EntityType = ReconciliationChecklistEntityOption["entity_type"];

const entityOptions = reactive<
    Record<EntityType, ReconciliationChecklistEntityOption[]>
>({
    live_promoter: [],
    merchant: [],
    receipt_merchant: [],
});
const entityLoading = reactive<Record<EntityType, boolean>>({
    live_promoter: false,
    merchant: false,
    receipt_merchant: false,
});
const filters = reactive({
    org_id: undefined as number | undefined,
    month: "",
    merchant_ids: [] as number[],
    live_promoter_ids: [] as number[],
    receipt_merchant_ids: [] as number[],
    keyword: "",
});
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const detailPagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});
const exportSelectedLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportAllLoading = ref(false);
const detailExportLoading = ref(false);
const querySyncing = ref(false);
const SUMMARY_PAGE_STATE_KEY = "reconciliation-checklist:summary";
const SUMMARY_QUERY_KEYS = [
    "page",
    "page_size",
    "org_id",
    "month",
    "merchant_ids",
    "live_promoter_ids",
    "receipt_merchant_ids",
    "keyword",
] as const;

type ExportScope = "all" | "current_page" | "selected";

const monthParts = computed(() => {
    if (!filters.month) return {};
    const [year, month] = filters.month.split("-").map(Number);
    return { accounting_year: year, accounting_month: month };
});

function baseParams() {
    return {
        org_id: filters.org_id,
        ...monthParts.value,
        merchant_ids: filters.merchant_ids.join(",") || undefined,
        live_promoter_ids: filters.live_promoter_ids.join(",") || undefined,
        receipt_merchant_ids:
            filters.receipt_merchant_ids.join(",") || undefined,
        keyword: filters.keyword || undefined,
    };
}

function queryString(value: unknown): string {
    if (Array.isArray(value)) return value.filter(Boolean).join(",");
    return typeof value === "string" ? value : "";
}

function queryNumberList(value: unknown): number[] {
    const text = queryString(value);
    if (!text) return [];
    return text
        .split(",")
        .map((item) => Number(item))
        .filter((item) => Number.isFinite(item) && item > 0);
}

function currentMonth() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function applyRouteQuery() {
    const page = Number(route.query.page);
    const pageSize = Number(route.query.page_size);
    const orgId = Number(route.query.org_id);

    pagination.page = Number.isFinite(page) && page > 0 ? page : 1;
    pagination.pageSize =
        Number.isFinite(pageSize) && pageSize > 0
            ? pageSize
            : DEFAULT_PAGE_SIZE;
    filters.org_id = Number.isFinite(orgId) && orgId > 0 ? orgId : undefined;
    filters.month = queryString(route.query.month) || currentMonth();
    filters.merchant_ids = queryNumberList(route.query.merchant_ids);
    filters.live_promoter_ids = queryNumberList(route.query.live_promoter_ids);
    filters.receipt_merchant_ids = queryNumberList(
        route.query.receipt_merchant_ids,
    );
    filters.keyword = queryString(route.query.keyword);
}

function hasRouteState() {
    return SUMMARY_QUERY_KEYS.some((key) => {
        const value = route.query[key];
        return Array.isArray(value)
            ? value.some(Boolean)
            : value !== undefined && value !== "";
    });
}

function restorePageState() {
    if (hasRouteState()) {
        applyRouteQuery();
        return;
    }
    const raw = sessionStorage.getItem(SUMMARY_PAGE_STATE_KEY);
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
            merchant_ids?: number[];
            live_promoter_ids?: number[];
            receipt_merchant_ids?: number[];
            keyword?: string;
        };
        pagination.page = state.page && state.page > 0 ? state.page : 1;
        pagination.pageSize =
            state.pageSize && state.pageSize > 0
                ? state.pageSize
                : DEFAULT_PAGE_SIZE;
        filters.org_id = state.org_id || undefined;
        filters.month = state.month || currentMonth();
        filters.merchant_ids = state.merchant_ids || [];
        filters.live_promoter_ids = state.live_promoter_ids || [];
        filters.receipt_merchant_ids = state.receipt_merchant_ids || [];
        filters.keyword = state.keyword || "";
    } catch {
        applyRouteQuery();
    }
}

function persistPageState() {
    sessionStorage.setItem(
        SUMMARY_PAGE_STATE_KEY,
        JSON.stringify({
            page: pagination.page,
            pageSize: pagination.pageSize,
            org_id: filters.org_id ?? null,
            month: filters.month,
            merchant_ids: filters.merchant_ids,
            live_promoter_ids: filters.live_promoter_ids,
            receipt_merchant_ids: filters.receipt_merchant_ids,
            keyword: filters.keyword,
        }),
    );
}

function buildRouteQuery() {
    return {
        ...route.query,
        page: String(pagination.page),
        page_size: String(pagination.pageSize),
        org_id: filters.org_id ? String(filters.org_id) : undefined,
        month: filters.month || undefined,
        merchant_ids: filters.merchant_ids.join(",") || undefined,
        live_promoter_ids: filters.live_promoter_ids.join(",") || undefined,
        receipt_merchant_ids:
            filters.receipt_merchant_ids.join(",") || undefined,
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

function selectedPeriod() {
    const parts = monthParts.value;
    if (!parts.accounting_year || !parts.accounting_month) return null;
    return parts as { accounting_year: number; accounting_month: number };
}

function entityLabel(item: ReconciliationChecklistEntityOption) {
    return item.platform_code
        ? `${item.platform_code} / ${item.name}`
        : item.name;
}

function mergeEntityOption(
    entityType: EntityType,
    option: ReconciliationChecklistEntityOption,
) {
    if (
        !option.id ||
        entityOptions[entityType].some((item) => item.id === option.id)
    )
        return;
    entityOptions[entityType].push(option);
}

function hydrateOptionsFromRows(items: ReconciliationChecklistSummary[]) {
    for (const row of items) {
        if (row.live_promoter_id) {
            mergeEntityOption("live_promoter", {
                id: row.live_promoter_id,
                org_id: row.org_id,
                platform_code: "",
                entity_type: "live_promoter",
                name: row.live_promoter,
            });
        }
        if (row.merchant_id) {
            mergeEntityOption("merchant", {
                id: row.merchant_id,
                org_id: row.org_id,
                platform_code: "",
                entity_type: "merchant",
                name: row.merchant_name,
            });
        }
        if (row.receipt_merchant_id) {
            mergeEntityOption("receipt_merchant", {
                id: row.receipt_merchant_id,
                org_id: row.org_id,
                platform_code: "",
                entity_type: "receipt_merchant",
                name: row.receipt_merchant,
            });
        }
    }
}

async function fetchEntityOptions(entityType: EntityType, keyword = "") {
    const period = selectedPeriod();
    if (!period) {
        entityOptions[entityType] = [];
        return;
    }
    entityLoading[entityType] = true;
    try {
        entityOptions[entityType] =
            await listReconciliationChecklistEntityOptions({
                entity_type: entityType,
                accounting_year: period.accounting_year,
                accounting_month: period.accounting_month,
                org_id: filters.org_id,
                keyword: keyword || undefined,
                limit: 50,
            });
    } finally {
        entityLoading[entityType] = false;
    }
}

async function fetchAllEntityOptions() {
    await Promise.all([
        fetchEntityOptions("live_promoter"),
        fetchEntityOptions("merchant"),
        fetchEntityOptions("receipt_merchant"),
    ]);
}

async function fetchData() {
    await syncRouteQuery();
    persistPageState();
    loading.value = true;
    try {
        const res = await listReconciliationChecklistSummary({
            ...baseParams(),
            page: pagination.page,
            page_size: pagination.pageSize,
        });
        rows.value = res.items;
        hydrateOptionsFromRows(res.items);
        pagination.total = res.total || 0;
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    clearSelection();
    pagination.page = 1;
    fetchData();
}

function resetFilters() {
    filters.org_id = undefined;
    filters.month = currentMonth();
    filters.merchant_ids = [];
    filters.live_promoter_ids = [];
    filters.receipt_merchant_ids = [];
    filters.keyword = "";
    fetchAllEntityOptions();
    handleSearch();
}

function handleMonthChange() {
    filters.merchant_ids = [];
    filters.live_promoter_ids = [];
    filters.receipt_merchant_ids = [];
    fetchAllEntityOptions();
}

function handleSelectionChange(selection: ReconciliationChecklistSummary[]) {
    const currentPageKeys = new Set(rows.value.map((row) => row.key));
    for (const key of currentPageKeys) selectedRowMap.value.delete(key);
    for (const row of selection) selectedRowMap.value.set(row.key, row);
    selectedRows.value = Array.from(selectedRowMap.value.values());
}

function clearSelection() {
    selectedRowMap.value.clear();
    selectedRows.value = [];
    summaryTable.value?.clearSelection?.();
}

function openDetails(row: ReconciliationChecklistSummary) {
    currentSummary.value = row;
    detailPagination.page = 1;
    detailKeyword.value = "";
    detailVisible.value = true;
    fetchDetails();
}

function handleDetailSearch() {
    detailPagination.page = 1;
    fetchDetails();
}

async function fetchDetails() {
    if (!currentSummary.value) return;
    detailLoading.value = true;
    try {
        const row = currentSummary.value;
        const res = await listReconciliationChecklistSummaryDetails({
            org_id: row.org_id,
            accounting_year: row.accounting_year,
            accounting_month: row.accounting_month,
            merchant_name: row.merchant_name,
            live_promoter: row.live_promoter,
            receipt_merchant: row.receipt_merchant,
            merchant_id: row.merchant_id || undefined,
            live_promoter_id: row.live_promoter_id || undefined,
            receipt_merchant_id: row.receipt_merchant_id || undefined,
            page: detailPagination.page,
            page_size: detailPagination.pageSize,
            keyword: detailKeyword.value || undefined,
        });
        detailRows.value = res.items;
        detailPagination.total = res.total || 0;
    } finally {
        detailLoading.value = false;
    }
}

async function handleExport(scope: ExportScope) {
    if (scope === "selected" && selectedRows.value.length === 0) {
        ElMessage.warning("请选择要导出的汇总行");
        return;
    }
    const ids = selectedRows.value.map((row) => row.key);
    const monthLabel = filters.month || "全部月份";
    const loadingRef =
        scope === "selected"
            ? exportSelectedLoading
            : scope === "current_page"
              ? exportCurrentPageLoading
              : exportAllLoading;
    loadingRef.value = true;
    try {
        await submitExportJob({
            export_type: "reconciliation_checklist.summary",
            title: "对账清单导出",
            filename: normalizeExportFilename(
                buildExportFilename([
                    "对账清单",
                    monthLabel,
                    scope === "all"
                        ? "全部"
                        : scope === "current_page"
                          ? `第${pagination.page}页`
                          : "选中",
                ]),
            ),
            params: {
                ...baseParams(),
                scope,
                ids: scope === "selected" ? ids : undefined,
                page: scope === "current_page" ? pagination.page : undefined,
                page_size:
                    scope === "current_page" ? pagination.pageSize : undefined,
            },
        });
        ElMessage.success("已提交导出任务，请到下载中心查看");
    } finally {
        loadingRef.value = false;
    }
}

async function exportCurrentDetail() {
    if (!currentSummary.value) return;
    const row = currentSummary.value;
    detailExportLoading.value = true;
    try {
        await submitExportJob({
            export_type: "reconciliation_checklist.summary",
            title: "对账清单明细导出",
            filename: normalizeExportFilename(
                buildExportFilename([
                    "对账清单明细",
                    formatChecklistMonth(
                        row.accounting_year,
                        row.accounting_month,
                    ),
                    row.merchant_name,
                    row.receipt_merchant,
                ]),
            ),
            params: {
                org_id: row.org_id,
                accounting_year: row.accounting_year,
                accounting_month: row.accounting_month,
                merchant_name: row.merchant_name,
                live_promoter: row.live_promoter,
                receipt_merchant: row.receipt_merchant,
                merchant_ids: row.merchant_id
                    ? String(row.merchant_id)
                    : undefined,
                live_promoter_ids: row.live_promoter_id
                    ? String(row.live_promoter_id)
                    : undefined,
                receipt_merchant_ids: row.receipt_merchant_id
                    ? String(row.receipt_merchant_id)
                    : undefined,
                keyword: detailKeyword.value || undefined,
                scope: "selected",
                ids: [row.key],
            },
        });
    } finally {
        detailExportLoading.value = false;
    }
}

onMounted(async () => {
    restorePageState();
    if (!filters.month) filters.month = currentMonth();
    await fetchOrgs();
    await fetchAllEntityOptions();
    await fetchData();
});

watch(
    () => route.query,
    async () => {
        if (querySyncing.value) return;
        applyRouteQuery();
        await fetchAllEntityOptions();
        await fetchData();
    },
);
</script>

<style scoped lang="scss">
.checklist-page {
    display: flex;
    flex-direction: column;
    gap: 14px;
    min-height: 0;
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.checklist-filter-card {
    display: block;
    flex: 0 0 auto;
    margin-bottom: 0;
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
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)) auto;
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
    margin-top: 14px;
}

.detail-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}

.detail-summary-card {
    display: grid;
    gap: 12px;
    margin-bottom: 12px;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.detail-summary-heading {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    min-width: 0;
}

.detail-summary-heading span {
    flex: 0 0 auto;
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
    line-height: 1.6;
}

.detail-summary-heading strong {
    min-width: 0;
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
    line-height: 1.5;
    word-break: break-word;
}

.detail-summary-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px 14px;
}

.detail-summary-item {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.detail-summary-item span {
    color: var(--text-tertiary);
    font-size: 12px;
}

.detail-summary-item strong {
    min-width: 0;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.45;
    word-break: break-word;
}

.detail-keyword-input {
    width: 360px;
    max-width: 100%;
}

:deep(.checklist-detail-drawer .el-drawer__body) {
    overflow: auto;
}

@media (max-width: 760px) {
    :deep(.checklist-filter-card .el-form.el-form--inline) {
        display: grid !important;
        grid-template-columns: 1fr;
    }

    :deep(.checklist-filter-card .filter-form .el-form-item) {
        width: 100%;
    }

    :deep(.checklist-filter-card .filter-form .el-input),
    :deep(.checklist-filter-card .filter-form .el-select),
    :deep(.checklist-filter-card .filter-form .el-date-editor) {
        width: 100% !important;
    }

    .card-header {
        align-items: stretch;
        flex-direction: column;
    }

    .detail-toolbar {
        align-items: stretch;
        flex-direction: column;
    }

    .detail-keyword-input {
        width: 100%;
    }

    .detail-summary-grid {
        grid-template-columns: 1fr;
    }
}
</style>
