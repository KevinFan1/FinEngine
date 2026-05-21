<template>
    <div class="page-container transaction-page">
        <el-card shadow="never" class="search-card">
            <SearchCardIntro
                kicker="动账任务工作台"
                title="先筛选任务，再查看动账处理结果"
                tip="支持按年月、平台、店铺和状态快速定位任务"
            />
            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker
                        v-model="searchForm.monthRange"
                        type="monthrange"
                        start-placeholder="开始年月"
                        end-placeholder="结束年月"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 230px"
                    />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select
                        v-model="searchForm.platforms"
                        placeholder="全部平台"
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
                <el-form-item label="状态">
                    <el-select
                        v-model="searchForm.statuses"
                        clearable
                        placeholder="全部状态"
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
                        v-model="searchForm.shopNames"
                        clearable
                        placeholder="全部店铺"
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        :loading="shopLoading"
                        style="width: 210px"
                    >
                        <el-option
                            v-for="shop in filteredShopOptions"
                            :key="`${shop.platform_name}-${shop.shop_name}`"
                            :label="shop.shop_name"
                            :value="shop.shop_name"
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
                    <el-input v-model="searchForm.keyword" clearable placeholder="文件名 / 店铺 / 错误" style="width: 210px" @keyup.enter="handleSearch" />
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
                        <span class="card-header-title">任务数据</span>
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
                        <el-button @click="fetchData">刷新</el-button>
                    </div>
                </div>
            </template>

            <el-table class="summary-table roomy-table task-table" :data="tableData" v-loading="loading" stripe border height="calc(100vh - 278px)">
                <el-table-column label="序号" width="70" align="center">
                    <template #default="{ $index }">
                        {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
                    </template>
                </el-table-column>
                <el-table-column prop="original_name" label="文件名" min-width="160" show-overflow-tooltip />
                <el-table-column label="性质" width="180">
                    <template #default>
                        <FileTypeBadge type="动账" />
                    </template>
                </el-table-column>
                <el-table-column label="年月" width="160">
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
                                    <em>成功</em>
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
                <el-table-column label="操作" width="190" align="center" fixed="right" class-name="task-action-column">
                    <template #default="{ row }">
                        <div class="task-action-group">
                            <el-button type="primary" link @click="openTaskDetail(row)">查看</el-button>
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
                        </div>
                    </div>
                    <div class="detail-result-card">
                        <span>处理结果</span>
                        <div class="result-stack result-stack--detail">
                            <span class="result-line result-line--success">
                                <em>成功</em>
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
                            <strong>{{ taskDetail.total_rows ?? 0 }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">未匹配</span>
                            <strong>{{ taskDetail.unmatched_rows ?? 0 }}</strong>
                        </div>
                    </div>
                </section>

                <section v-if="taskDetail.error_message" class="detail-card detail-card--danger">
                    <div class="detail-card-header">
                        <span>错误原因</span>
                    </div>
                    <p class="detail-error">{{ taskDetail.error_message }}</p>
                </section>

                <section v-if="taskDetail.result_summary" class="detail-card">
                    <div class="detail-card-header">
                        <span>结果摘要</span>
                    </div>
                    <div class="detail-summary-list">
                        <div v-for="item in taskSummaryItems(taskDetail.result_summary)" :key="item.label" class="detail-summary-item">
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
defineOptions({ name: "TransactionTasks" });

import { ElMessage } from "element-plus";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import { listTransactionTasks, rerunTransactionTask, type TransactionTask } from "@/api/transactionAccounting";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import { formatDateTime, getPlatformLabel } from "@/utils/format";
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
const tableData = ref<TransactionTask[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const rerunningTaskId = ref<number | null>(null);
const taskDetailDrawerVisible = ref(false);
const taskDetail = ref<TransactionTask | null>(null);
const searchForm = reactive({
    monthRange: [] as string[],
    platforms: [] as string[],
    statuses: [] as string[],
    shopNames: [] as string[],
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
const selectedStatusesParam = computed(
    () => searchForm.statuses.join(",") || undefined,
);
const selectedShopNamesParam = computed(
    () => searchForm.shopNames.join(",") || undefined,
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

interface TaskFilterTag extends ActiveFilterTag {
    key: "monthRange" | "platforms" | "statuses" | "shopNames" | "keyword";
}

const activeFilterTags = computed<TaskFilterTag[]>(() => {
    const tags: TaskFilterTag[] = [];
    if (searchForm.monthRange.length) tags.push({ key: "monthRange", label: "核算年月", value: monthRangeLabel(searchForm.monthRange) });
    searchForm.platforms.forEach((value) => tags.push({ key: "platforms", label: "平台", value: getPlatformLabel(value) }));
    searchForm.statuses.forEach((value) => tags.push({ key: "statuses", label: "状态", value: taskStatusLabel(value) }));
    searchForm.shopNames.forEach((value) => tags.push({ key: "shopNames", label: "店铺", value }));
    if (searchForm.keyword) tags.push({ key: "keyword", label: "搜索", value: searchForm.keyword });
    return tags;
});

function hasTaskResult(row: TransactionTask) {
    return ["success", "partial_success", "failed"].includes(row.status);
}

function taskSuccessCount(row: TransactionTask) {
    return row.matched_rows ?? 0;
}

function taskFailedCount(row: TransactionTask) {
    return (row.unmatched_rows ?? 0) + (row.failed_rows ?? 0);
}

function canRecalculate(row: TransactionTask) {
    return !["queued", "processing"].includes(row.status);
}

const resultSummaryLabels: Record<string, string> = {
    total_rows: "总行数",
    matched_rows: "匹配明细数",
    unmatched_rows: "未匹配行数",
    failed_rows: "失败行数",
    summary_groups: "汇总分组数",
};

function taskSummaryItems(value: Record<string, any>) {
    return Object.entries(value).map(([key, itemValue]) => ({
        label: resultSummaryLabels[key] || key,
        value: itemValue ?? "-",
    }));
}

function queryParams() {
    return {
        page: pagination.page,
        page_size: pagination.pageSize,
        status: selectedStatusesParam.value,
        platform_code: selectedPlatformsParam.value,
        shop_name: selectedShopNamesParam.value,
        keyword: searchForm.keyword || undefined,
        ...splitMonthRange(searchForm.monthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await listTransactionTasks(queryParams());
        tableData.value = data.items;
        pagination.total = data.total;
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

async function handlePlatformChange() {
    await fetchShopOptions();
    const availableShopNames = new Set(
        filteredShopOptions.value.map((shop) => shop.shop_name),
    );
    searchForm.shopNames = searchForm.shopNames.filter((shopName) =>
        availableShopNames.has(shopName),
    );
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.monthRange = [];
    searchForm.platforms = [];
    searchForm.statuses = [];
    searchForm.shopNames = [];
    searchForm.keyword = "";
    fetchShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: TaskFilterTag) {
    if (tag.key === "monthRange") searchForm.monthRange = [];
    if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter((item) => getPlatformLabel(item) !== tag.value);
        await fetchShopOptions();
        const availableShopNames = new Set(filteredShopOptions.value.map((shop) => shop.shop_name));
        searchForm.shopNames = searchForm.shopNames.filter((shopName) => availableShopNames.has(shopName));
    }
    if (tag.key === "statuses") searchForm.statuses = searchForm.statuses.filter((item) => taskStatusLabel(item) !== tag.value);
    if (tag.key === "shopNames") searchForm.shopNames = searchForm.shopNames.filter((item) => item !== tag.value);
    if (tag.key === "keyword") searchForm.keyword = "";
    handleSearch();
}

async function rerunTask(row: TransactionTask) {
    rerunningTaskId.value = row.id;
    try {
        await rerunTransactionTask(row.id);
        ElMessage.success("已重新提交统计任务");
        await fetchData();
    } finally {
        rerunningTaskId.value = null;
    }
}

function openTaskDetail(row: TransactionTask) {
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
    await fetchPlatformOptions();
    await fetchShopOptions();
    fetchData();
    startAutoRefresh();
});

onUnmounted(() => {
    stopAutoRefresh();
});
</script>

<style scoped lang="scss">
@use "./transaction.scss";
</style>
