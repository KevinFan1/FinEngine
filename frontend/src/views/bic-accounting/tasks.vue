<template>
    <div class="page-container page-container--flow transaction-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker
                        v-model="searchForm.monthRange"
                        type="monthrange"
                        start-placeholder="核算年月起"
                        end-placeholder="核算年月止"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 260px"
                    />
                </el-form-item>
                <el-form-item label="创建时间">
                    <el-date-picker
                        v-model="searchForm.createdTimeRange"
                        type="datetimerange"
                        range-separator="至"
                        start-placeholder="创建时间起"
                        end-placeholder="创建时间止"
                        clearable
                        value-format="YYYY-MM-DD HH:mm:ss"
                        :shortcuts="taskCreatedTimeShortcuts"
                        style="width: 420px"
                    />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select
                        v-model="searchForm.platforms"
                        placeholder="平台"
                        multiple
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        style="width: 170px"
                        @change="handlePlatformChange"
                    >
                        <el-option
                            v-for="p in platformOptions"
                            :key="p.value"
                            :label="p.label"
                            :value="p.value"
                        >
                            <PlatformBadge :platform="p.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select
                        v-model="searchForm.orgIds"
                        placeholder="组织"
                        multiple
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        style="width: 190px"
                        @change="handleOrgChange"
                    >
                        <el-option
                            v-for="org in orgOptions"
                            :key="org.id"
                            :label="org.name"
                            :value="org.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="状态">
                    <el-select
                        v-model="searchForm.statuses"
                        clearable
                        placeholder="状态"
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        style="width: 160px"
                    >
                        <el-option v-for="item in transactionStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shopIds"
                        clearable
                        placeholder="店铺"
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        :loading="shopLoading"
                        style="width: 210px"
                    >
                        <el-option
                            v-for="shop in filteredShopOptions"
                            :key="shop.id"
                            :label="shop.shop_name"
                            :value="shop.id"
                        >
                            <ShopBadge
                                :label="shop.shop_name"
                                :color="shop.shop_color"
                                size="compact"
                            />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="搜索">
                    <el-input v-model="searchForm.keyword" clearable placeholder="搜文件/店铺/错误" style="width: 210px" @keyup.enter="handleSearch" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">搜索</el-button>
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>

            <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">BIC任务</span>
                        <span class="summary-count">共 {{ pagination.total }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-tag
                            v-if="hasRunningTasks"
                            type="warning"
                            size="small"
                            class="animate-pulse"
                        >
                            <el-icon><Loading /></el-icon>
                            有任务运行中，自动刷新中...
                        </el-tag>
                        <div v-if="selectedCount > 0" class="batch-actions">
                            <span class="batch-actions-count">已选 {{ selectedCount }} 条</span>
                            <el-button
                                size="small"
                                type="primary"
                                :disabled="selectedRecalculableRows.length === 0"
                                :loading="batchRecalculating"
                                @click="handleBatchRecalculate"
                            >
                                批量重新统计
                            </el-button>
                        </div>
                        <el-button @click="fetchData">刷新</el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table roomy-table task-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                row-key="id"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="46" fixed="left" />
                <el-table-column label="序号" width="70" align="center">
                    <template #default="{ $index }">
                        {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
                    </template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" label="组织" width="170" show-overflow-tooltip>
                    <template #default="{ row }">
                        {{ row.org_name || `组织#${row.org_id}` }}
                    </template>
                </el-table-column>
                <el-table-column prop="original_name" label="文件名" min-width="160" show-overflow-tooltip />
                <el-table-column label="性质" width="180">
                    <template #default>
                        <FileTypeBadge type="bic" />
                    </template>
                </el-table-column>
                <el-table-column label="核算年月" width="160">
                    <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column prop="platform_code" label="平台" width="100">
                    <template #default="{ row }">
                        <PlatformBadge
                            v-if="row.platform_code"
                            :platform="row.platform_code"
                        />
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column prop="shop_name" label="店铺" width="180" show-overflow-tooltip>
                    <template #default="{ row }">
                        <ShopBadge
                            :label="row.shop_name || '-'"
                            :color="shopColorByName.get(row.shop_name || '')"
                            size="table"
                        />
                    </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="100" align="center">
                    <template #default="{ row }">
                        <el-tag
                            :type="taskStatusType(row.status)"
                            size="small"
                            :class="{ 'animate-pulse': row.status === 'processing' }"
                        >
                            {{ taskStatusLabel(row.status) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="处理结果" width="112" align="center">
                    <template #default="{ row }">
                        <template v-if="hasTaskResult(row)">
                            <div class="result-stack">
                                <span class="result-line result-line--success">
                                    <em>符合</em>
                                    <strong>{{ taskSuccessCount(row) }}</strong>
                                </span>
                                <span class="result-line result-line--failed">
                                    <em>失败</em>
                                    <strong>{{ taskFailedCount(row) }}</strong>
                                </span>
                            </div>
                        </template>
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="170" class-name="created-time-column">
                    <template #default="{ row }">
                        <div class="created-time-stack">
                            <span class="text-tertiary">{{ formatDateTime(row.created_at) }}</span>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column prop="started_at" label="开始时间" width="170">
                    <template #default="{ row }">
                        <span class="text-tertiary">{{ row.started_at ? formatDateTime(row.started_at) : "-" }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="finished_at" label="结束时间" width="170">
                    <template #default="{ row }">
                        <span class="text-tertiary">{{ row.finished_at ? formatDateTime(row.finished_at) : "-" }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="更新时间" width="170" class-name="created-time-column">
                    <template #default="{ row }">
                        <div class="created-time-stack">
                            <span class="text-tertiary">{{ formatDateTime(row.updated_at || row.created_at) }}</span>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="220" align="center" fixed="right" class-name="task-action-column">
                    <template #default="{ row }">
                        <div class="task-action-group">
                            <el-button type="primary" link @click="openTaskDetail(row)">查看</el-button>
                            <el-button
                                v-if="userStore.isSuperAdmin"
                                type="primary"
                                link
                                :loading="downloadingTaskId === row.id"
                                @click="handleDownloadSource(row)"
                            >
                                下载原表
                            </el-button>
                            <el-button
                                v-if="canRecalculate(row)"
                                type="primary"
                                link
                                :loading="rerunningTaskId === row.id"
                                @click="rerunTask(row)"
                            >
                                重新统计
                            </el-button>
                        </div>
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
            v-model="taskDetailDrawerVisible"
            title="任务详情"
            size="520px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="taskDetail" class="detail-panel">
                <section class="detail-hero-card">
                    <div class="detail-hero-main">
                        <span class="detail-kicker">TASK #{{ taskDetail.id }}</span>
                        <h3>{{ taskDetail.original_name || "-" }}</h3>
                        <div class="detail-badge-row">
                            <PlatformBadge
                                v-if="taskDetail.platform_code"
                                :platform="taskDetail.platform_code"
                            />
                            <el-tag :type="taskStatusType(taskDetail.status)" size="small">
                                {{ taskStatusLabel(taskDetail.status) }}
                            </el-tag>
                            <el-button
                                v-if="userStore.isSuperAdmin"
                                size="small"
                                :loading="downloadingTaskId === taskDetail.id"
                                @click="handleDownloadSource(taskDetail)"
                            >
                                下载原表
                            </el-button>
                        </div>
                    </div>
                    <div class="detail-result-card">
                        <span>处理结果</span>
                        <div class="result-stack result-stack--detail">
                            <span class="result-line result-line--success">
                                <em>符合</em>
                                <strong>{{ taskSuccessCount(taskDetail) }}</strong>
                            </span>
                            <span class="result-line result-line--failed">
                                <em>失败</em>
                                <strong>{{ taskFailedCount(taskDetail) }}</strong>
                            </span>
                        </div>
                    </div>
                </section>

                <section class="detail-card">
                    <div class="detail-card-header">
                        <span>基础信息</span>
                    </div>
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">核算年月</span>
                            <strong>{{ formatMonth(taskDetail.accounting_year, taskDetail.accounting_month) }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">店铺</span>
                            <strong>
                                <ShopBadge
                                    :label="taskDetail.shop_name || '-'"
                                    :color="shopColorByName.get(taskDetail.shop_name || '')"
                                    size="table"
                                />
                            </strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">总行数</span>
                            <strong>{{ taskDetail.processed_rows ?? 0 }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">失败行数</span>
                            <strong>{{ taskDetail.failed_rows ?? 0 }}</strong>
                        </div>
                    </div>
                </section>

                <section class="detail-card">
                    <div class="detail-card-header">
                        <span>时间信息</span>
                    </div>
                    <div class="detail-timeline">
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">创建时间</span>
                                <strong>{{ formatDateTime(taskDetail.created_at) }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">开始时间</span>
                                <strong>{{ taskDetail.started_at ? formatDateTime(taskDetail.started_at) : "-" }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">结束时间</span>
                                <strong>{{ taskDetail.finished_at ? formatDateTime(taskDetail.finished_at) : "-" }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">更新时间</span>
                                <strong>{{ formatDateTime(taskDetail.updated_at || taskDetail.created_at) }}</strong>
                            </div>
                        </div>
                    </div>
                </section>

                <section v-if="taskErrorReason(taskDetail)" class="detail-card detail-card--danger">
                    <div class="detail-card-header">
                        <span>错误原因</span>
                    </div>
                    <p class="detail-error">{{ taskErrorReason(taskDetail) }}</p>
                </section>

                <section v-if="taskDetail.result_summary" class="detail-card">
                    <div class="detail-card-header">
                        <span>结果摘要</span>
                    </div>
                    <div class="detail-summary-list">
                        <div v-for="item in taskSummaryItems(taskDetail.result_summary)" :key="item.key" class="detail-summary-item">
                            <span>{{ item.label }}</span>
                            <strong>{{ item.value }}</strong>
                        </div>
                    </div>
                </section>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "BicTasks" });

import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import {
    batchRecalculateBicTasks,
    getBicTaskSourceDownload,
    listBicTasks,
    rerunBicTask,
    type BicTask,
    type BicTaskBatchActionResult,
} from "@/api/bicAccounting";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import { formatDateTime, getPlatformLabel } from "@/utils/format";
import { dateRangeLabel, taskCreatedTimeShortcuts } from "@/utils/dateRange";
import { usePageRefresh } from "@/composables/pageRefresh";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import {
    getFallbackPlatforms,
    getReportPlatformCode,
    toSourcePlatformOptions,
    type PlatformOption,
} from "@/utils/platform";
import {
    formatMonth,
    monthRangeLabel,
    splitMonthRange,
    taskStatusLabel,
    taskStatusType,
    transactionStatusOptions,
} from "./common";

const loading = ref(false);
const tableData = ref<BicTask[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const rerunningTaskId = ref<number | null>(null);
const downloadingTaskId = ref<number | null>(null);
const batchRecalculating = ref(false);
const selectedRows = ref<BicTask[]>([]);
const taskDetailDrawerVisible = ref(false);
const taskDetail = ref<BicTask | null>(null);
const searchForm = reactive({
    monthRange: null as string[] | null,
    createdTimeRange: null as string[] | null,
    orgIds: [] as number[],
    platforms: [] as string[],
    statuses: [] as string[],
    shopIds: [] as number[],
    keyword: "",
});
const shopLoading = ref(false);
const shopOptions = ref<Shop[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toSourcePlatformOptions(platforms.value),
);

let refreshTimer: ReturnType<typeof setInterval> | null = null;

const hasRunningTasks = computed(() => {
    return tableData.value.some((t) => t.status === "processing" || t.status === "queued");
});

const selectedPlatformsParam = computed(
    () => searchForm.platforms.join(",") || undefined,
);
const selectedOrgIdsParam = computed(
    () => searchForm.orgIds.join(",") || undefined,
);
const selectedStatusesParam = computed(
    () => searchForm.statuses.join(",") || undefined,
);
const selectedShopIdsParam = computed(
    () => searchForm.shopIds.join(",") || undefined,
);
const selectedReportPlatformsParam = computed(() => {
    const values = new Set(
        searchForm.platforms
            .map((platform) => getReportPlatformCode(platform, platforms.value))
            .filter(Boolean),
    );
    return Array.from(values).join(",") || undefined;
});

const filteredShopOptions = computed(() => {
    if (!searchForm.platforms.length) return shopOptions.value;
    const reportPlatforms = new Set(
        searchForm.platforms
            .map((platform) => getReportPlatformCode(platform, platforms.value))
            .filter(Boolean),
    );
    return shopOptions.value.filter((shop) =>
        reportPlatforms.has(shop.platform_name),
    );
});

const shopColorByName = computed(() => {
    const map = new Map<string, string | undefined>();
    shopOptions.value.forEach((shop) => {
        if (!map.has(shop.shop_name)) {
            map.set(shop.shop_name, shop.shop_color);
        }
    });
    return map;
});

const selectedCount = computed(() => selectedRows.value.length);
const selectedRecalculableRows = computed(() =>
    selectedRows.value.filter((row) => canRecalculate(row)),
);

interface TaskFilterTag extends ActiveFilterTag {
    key: "monthRange" | "createdTimeRange" | "orgIds" | "platforms" | "statuses" | "shopIds" | "keyword";
}

const activeFilterTags = computed<TaskFilterTag[]>(() => {
    const tags: TaskFilterTag[] = [];
    if (searchForm.monthRange?.length) tags.push({ key: "monthRange", label: "核算年月", value: monthRangeLabel(searchForm.monthRange) });
    if (searchForm.createdTimeRange?.length) tags.push({ key: "createdTimeRange", label: "创建时间", value: dateRangeLabel(searchForm.createdTimeRange) });
    searchForm.orgIds.forEach((value) => {
        const org = orgOptions.value.find((item) => item.id === value);
        tags.push({ key: "orgIds", label: "组织", value: org?.name || `组织#${value}` });
    });
    searchForm.platforms.forEach((value) => tags.push({ key: "platforms", label: "平台", value: getPlatformLabel(value) }));
    searchForm.statuses.forEach((value) => tags.push({ key: "statuses", label: "状态", value: taskStatusLabel(value) }));
    searchForm.shopIds.forEach((value) => {
        const shop = shopOptions.value.find((s) => s.id === value);
        tags.push({ key: "shopIds", label: "店铺", value: shop?.shop_name || `店铺#${value}` });
    });
    if (searchForm.keyword) tags.push({ key: "keyword", label: "搜索", value: searchForm.keyword });
    return tags;
});

function hasTaskResult(row: BicTask) {
    return ["success", "partial_success", "failed", "expired"].includes(row.status);
}

function taskSuccessCount(row: BicTask) {
    return row.result_success ?? row.success_rows ?? 0;
}

function taskFailedCount(row: BicTask) {
    return row.result_failed ?? row.failed_rows ?? 0;
}

function canRecalculate(row: BicTask) {
    return !["queued", "processing", "expired"].includes(row.status);
}

const resultSummaryLabels: Record<string, string> = {
    type: "文件类型",
    total_rows: "总行数",
    success_rows: "符合条件行数",
    failed_rows: "失败行数",
    groups: "明细分组数",
    errors: "错误明细",
    detail_ids: "明细记录ID列表",
};

const hiddenResultSummaryKeys = new Set([
    "detail_ids",
    "明细记录ID",
    "明细记录ID列表",
]);

function hasChineseText(value: string) {
    return /[\u4e00-\u9fff]/.test(value);
}

function summaryLabel(key: string) {
    return resultSummaryLabels[key] || (hasChineseText(key) ? key : "");
}

function formatSummaryErrors(errors: unknown) {
    if (!errors) return "";
    if (Array.isArray(errors)) return errors.filter(Boolean).map(String).join("；");
    if (typeof errors === "string") return errors;
    return JSON.stringify(errors);
}

function taskErrorReason(row: BicTask) {
    return (
        row.error_reason ||
        row.error_message ||
        formatSummaryErrors(row.result_summary?.["错误明细"] || row.result_summary?.errors)
    );
}

function formatSummaryValue(key: string, value: unknown) {
    if (value == null || value === "") return "-";
    if (key === "type" && String(value).toLowerCase() === "bic") return "BIC";
    if (Array.isArray(value)) return value.filter((item) => item != null && item !== "").map(String).join("；") || "-";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function taskSummaryItems(value: Record<string, any>) {
    return Object.entries(value)
        .filter(([key]) => !hiddenResultSummaryKeys.has(key))
        .map(([key, itemValue]) => ({
            key,
            label: summaryLabel(key),
            value: formatSummaryValue(key, itemValue),
        }))
        .filter((item) => item.label);
}

function queryParams() {
    return {
        page: pagination.page,
        page_size: pagination.pageSize,
        org_id: selectedOrgIdsParam.value,
        status: selectedStatusesParam.value,
        platform_code: selectedPlatformsParam.value,
        shop_ids: selectedShopIdsParam.value,
        keyword: searchForm.keyword || undefined,
        created_start_time: searchForm.createdTimeRange?.[0] || undefined,
        created_end_time: searchForm.createdTimeRange?.[1] || undefined,
        ...splitMonthRange(searchForm.monthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await listBicTasks(queryParams());
        tableData.value = data.items;
        pagination.total = data.total ?? 0;
        const selectedIds = new Set(selectedRows.value.map((row) => row.id));
        selectedRows.value = tableData.value.filter((row) => selectedIds.has(row.id));
    } finally {
        loading.value = false;
    }
}

async function fetchShopOptions() {
    shopLoading.value = true;
    try {
        const res = await getShopList({
            page: 1,
            page_size: 100,
            org_id: selectedOrgIdsParam.value,
            platform_name: selectedReportPlatformsParam.value,
        });
        shopOptions.value = res.items || [];
    } catch {
        // Error handled by interceptor
    } finally {
        shopLoading.value = false;
    }
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
    platformOptions.value = toSourcePlatformOptions(platforms.value);
}

async function fetchOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    try {
        orgOptions.value = await getAllOrganizations();
    } catch {
        // Ignore
    }
}

async function handlePlatformChange() {
    await fetchShopOptions();
    const availableShopIds = new Set(
        filteredShopOptions.value.map((shop) => shop.id),
    );
    searchForm.shopIds = searchForm.shopIds.filter((shopId) =>
        availableShopIds.has(shopId),
    );
}

async function handleOrgChange() {
    await fetchShopOptions();
    const availableShopIds = new Set(
        filteredShopOptions.value.map((shop) => shop.id),
    );
    searchForm.shopIds = searchForm.shopIds.filter((shopId) =>
        availableShopIds.has(shopId),
    );
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.monthRange = null;
    searchForm.createdTimeRange = null;
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.statuses = [];
    searchForm.shopIds = [];
    searchForm.keyword = "";
    fetchShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: TaskFilterTag) {
    if (tag.key === "monthRange") searchForm.monthRange = null;
    if (tag.key === "createdTimeRange") searchForm.createdTimeRange = null;
    if (tag.key === "orgIds") {
        searchForm.orgIds = searchForm.orgIds.filter((item) => {
            const org = orgOptions.value.find((orgItem) => orgItem.id === item);
            return (org?.name || `组织#${item}`) !== tag.value;
        });
        await handleOrgChange();
    }
    if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter((item) => getPlatformLabel(item) !== tag.value);
        await fetchShopOptions();
        const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
        searchForm.shopIds = searchForm.shopIds.filter((shopId) => availableShopIds.has(shopId));
    }
    if (tag.key === "statuses") searchForm.statuses = searchForm.statuses.filter((item) => taskStatusLabel(item) !== tag.value);
    if (tag.key === "shopIds") {
        searchForm.shopIds = searchForm.shopIds.filter((id) => {
            const shop = shopOptions.value.find((s) => s.id === id);
            return (shop?.shop_name || `店铺#${id}`) !== tag.value;
        });
    }
    if (tag.key === "keyword") searchForm.keyword = "";
    handleSearch();
}

async function rerunTask(row: BicTask) {
    rerunningTaskId.value = row.id;
    try {
        await rerunBicTask(row.id);
        ElMessage.success("已重新提交统计任务");
        await fetchData();
    } finally {
        rerunningTaskId.value = null;
    }
}

async function handleDownloadSource(row: BicTask) {
    if (!userStore.isSuperAdmin || downloadingTaskId.value !== null) return;
    downloadingTaskId.value = row.id;
    try {
        const credential = await getBicTaskSourceDownload(row.id);
        const link = document.createElement("a");
        link.href = credential.download_url;
        link.download = credential.filename || row.original_name || "原表.xlsx";
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } finally {
        downloadingTaskId.value = null;
    }
}

function handleSelectionChange(rows: BicTask[]) {
    selectedRows.value = rows;
}

function showBatchResult(result: BicTaskBatchActionResult) {
    if (result.failed_count > 0) {
        const firstFailure = result.failed_items[0];
        ElMessage.warning(
            `已重新提交统计任务 ${result.success_count} 个，失败 ${result.failed_count} 个${
                firstFailure ? `：${firstFailure.message}` : ""
            }`,
        );
        return;
    }
    ElMessage.success(`已重新提交统计任务 ${result.success_count} 个`);
}

async function handleBatchRecalculate() {
    const rows = selectedRecalculableRows.value;
    if (!rows.length) {
        ElMessage.warning("请选择可重新统计的任务");
        return;
    }

    batchRecalculating.value = true;
    stopAutoRefresh();
    try {
        const result = await batchRecalculateBicTasks(rows.map((row) => row.id));
        showBatchResult(result);
        await fetchData();
    } catch {
        await fetchData();
    } finally {
        batchRecalculating.value = false;
        startAutoRefresh();
    }
}

function openTaskDetail(row: BicTask) {
    taskDetail.value = row;
    taskDetailDrawerVisible.value = true;
}

function startAutoRefresh() {
    stopAutoRefresh();
    refreshTimer = setInterval(() => {
        if (hasRunningTasks.value) {
            fetchData();
        }
    }, 5000);
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

onMounted(async () => {
    await fetchOrgOptions();
    await fetchPlatformOptions();
    await fetchShopOptions();
    fetchData();
    startAutoRefresh();
});

onUnmounted(() => {
    stopAutoRefresh();
});

usePageRefresh(fetchData);
</script>

<style scoped lang="scss">
@use "./transaction.scss";
</style>
