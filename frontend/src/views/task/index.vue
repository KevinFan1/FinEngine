<template>
    <div class="page-container">
        <!-- Filter bar -->
        <el-card shadow="never" class="search-card">
            <SearchCardIntro
                kicker="任务工作台"
                title="先筛选任务，再查看处理结果"
                tip="支持按年月、平台、店铺、性质和状态快速收敛范围"
            />
            <el-form :model="searchForm" inline>
                <el-form-item label="年月">
                    <el-date-picker
                        v-model="searchForm.sourceMonth"
                        type="month"
                        placeholder="全部年月"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 150px"
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
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shopIds"
                        placeholder="全部店铺"
                        multiple
                        clearable
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
                <el-form-item label="性质">
                    <el-select
                        v-model="searchForm.parsedTypes"
                        placeholder="全部性质"
                        multiple
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        style="width: 160px"
                    >
                        <el-option
                            v-for="t in typeOptions"
                            :key="t.value"
                            :label="t.label"
                            :value="t.value"
                        >
                            <FileTypeBadge :type="t.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="状态">
                    <el-select
                        v-model="searchForm.statuses"
                        placeholder="全部状态"
                        multiple
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        style="width: 160px"
                    >
                        <el-option label="排队中" value="queued" />
                        <el-option label="运行中" value="running" />
                        <el-option label="成功" value="success" />
                        <el-option label="失败" value="failed" />
                        <el-option label="已取消" value="cancelled" />
                    </el-select>
                </el-form-item>
                <el-form-item label="搜索">
                    <el-input
                        v-model="searchForm.keyword"
                        placeholder="文件名/店铺"
                        clearable
                        style="width: 200px"
                        @keyup.enter="handleSearch"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch"
                        >搜索</el-button
                    >
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>
            <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
        </el-card>

        <!-- Table -->
        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <span class="card-header-title">任务列表</span>
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
                            <span class="batch-actions-count"
                                >已选 {{ selectedCount }} 条</span
                            >
                            <el-button
                                size="small"
                                :disabled="selectedRetryableRows.length === 0"
                                :loading="batchRetrying"
                                @click="handleBatchRetry"
                            >
                                批量重试
                            </el-button>
                            <el-button
                                size="small"
                                type="primary"
                                :disabled="
                                    selectedRecalculableRows.length === 0
                                "
                                :loading="batchRecalculating"
                                @click="handleBatchRecalculate"
                            >
                                批量重新统计
                            </el-button>
                        </div>
                        <el-button type="primary" @click="openUploadDrawer">
                            <el-icon><Upload /></el-icon>
                            上传文件
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table roomy-table task-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                style="width: 100%"
                height="calc(100vh - 278px)"
                row-key="id"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="46" fixed="left" />
                <el-table-column label="序号" width="70" align="center">
                    <template #default="{ $index }">
                        {{
                            (pagination.page - 1) * pagination.pageSize +
                            $index +
                            1
                        }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="filename"
                    label="文件名"
                    min-width="160"
                    show-overflow-tooltip
                />
                <el-table-column prop="parsed_type" label="性质" width="180">
                    <template #default="{ row }">
                        <FileTypeBadge
                            v-if="row.parsed_type"
                            :type="row.parsed_type"
                        />
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column label="年月" width="160">
                    <template #default="{ row }">
                        <span v-if="row.parsed_year && row.parsed_month">
                            {{ row.parsed_year }}-{{
                                String(row.parsed_month).padStart(2, "0")
                            }}
                        </span>
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column prop="platform" label="平台" width="100">
                    <template #default="{ row }">
                        <PlatformBadge
                            v-if="row.platform"
                            :platform="row.platform"
                        />
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="shop_name"
                    label="店铺"
                    width="180"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <ShopBadge
                            :label="row.shop_name || '-'"
                            :color="row.shop_color"
                            size="table"
                        />
                    </template>
                </el-table-column>
                <el-table-column
                    prop="status"
                    label="状态"
                    width="100"
                    align="center"
                >
                    <template #default="{ row }">
                        <el-tag
                            :type="statusTagType(row.status)"
                            size="small"
                            :class="{
                                'animate-pulse': row.status === 'running',
                            }"
                        >
                            {{ statusLabel(row.status) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="处理结果" width="112" align="center">
                    <template #default="{ row }">
                        <template
                            v-if="
                                row.status === 'success' ||
                                row.status === 'failed'
                            "
                        >
                            <div class="result-stack">
                                <span class="result-line result-line--success">
                                    <em>成功</em>
                                    <strong>{{
                                        row.result_success ?? 0
                                    }}</strong>
                                </span>
                                <span class="result-line result-line--failed">
                                    <em>失败</em>
                                    <strong>{{
                                        row.result_failed ?? 0
                                    }}</strong>
                                </span>
                            </div>
                        </template>
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="created_at"
                    label="创建时间"
                    width="170"
                    class-name="created-time-column"
                >
                    <template #default="{ row }">
                        <div class="created-time-stack">
                            <span class="text-tertiary">{{
                                formatDateTime(row.created_at)
                            }}</span>
                            <el-tag
                                v-if="isActionExpired(row)"
                                type="info"
                                size="small"
                            >
                                已过期
                            </el-tag>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column
                    label="操作"
                    width="190"
                    align="center"
                    fixed="right"
                    class-name="task-action-column"
                >
                    <template #default="{ row }">
                        <div class="task-action-group">
                            <el-button
                                type="primary"
                                link
                                @click="openTaskDetail(row)"
                                >查看</el-button
                            >
                            <el-button
                                v-if="row.status === 'failed'"
                                type="primary"
                                link
                                :loading="retryingTaskId === row.id"
                                :disabled="isActionExpired(row)"
                                @click="handleRetry(row)"
                            >
                                重试
                            </el-button>
                            <el-button
                                v-if="canRecalculate(row)"
                                type="primary"
                                link
                                :loading="recalculatingTaskId === row.id"
                                :disabled="isActionExpired(row)"
                                @click="handleRecalculate(row)"
                            >
                                重新统计
                            </el-button>
                        </div>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty description="暂无任务数据" :image-size="80" />
                </template>
            </el-table>

            <!-- Pagination -->
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

        <el-dialog
            v-model="retryDialogVisible"
            title="重试确认"
            width="420px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
            :close-on-press-escape="retryingTaskId === null"
            :show-close="retryingTaskId === null"
            @closed="handleRetryDialogClosed"
        >
            <p class="retry-dialog-text">
                确定要重试任务「{{ retryTargetLabel }}」吗？
            </p>
            <template #footer>
                <el-button
                    :disabled="retryingTaskId !== null"
                    @click="retryDialogVisible = false"
                >
                    取消
                </el-button>
                <el-button
                    type="primary"
                    :loading="retryingTaskId !== null"
                    @click="confirmRetry"
                >
                    确定重试
                </el-button>
            </template>
        </el-dialog>

        <el-drawer
            v-model="uploadDrawerVisible"
            title="上传文件"
            size="720px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <UploadView
                embedded
                @uploaded="handleUploadFinished"
                @view-tasks="closeUploadDrawer"
                @continue-upload="handleContinueUpload"
            />
        </el-drawer>

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
                        <span class="detail-kicker"
                            >TASK #{{ taskDetail.id }}</span
                        >
                        <h3>{{ taskDetail.filename }}</h3>
                        <div class="detail-badge-row">
                            <FileTypeBadge
                                v-if="taskDetail.parsed_type"
                                :type="taskDetail.parsed_type"
                            />
                            <PlatformBadge
                                v-if="taskDetail.platform"
                                :platform="taskDetail.platform"
                            />
                            <el-tag
                                :type="statusTagType(taskDetail.status)"
                                size="small"
                            >
                                {{ statusLabel(taskDetail.status) }}
                            </el-tag>
                            <el-tag
                                v-if="isActionExpired(taskDetail)"
                                type="info"
                                size="small"
                            >
                                已过期
                            </el-tag>
                        </div>
                    </div>
                    <div class="detail-result-card">
                        <span>处理结果</span>
                        <div class="result-stack result-stack--detail">
                            <span class="result-line result-line--success">
                                <em>成功</em>
                                <strong>{{
                                    taskDetail.result_success ?? 0
                                }}</strong>
                            </span>
                            <span class="result-line result-line--failed">
                                <em>失败</em>
                                <strong>{{
                                    taskDetail.result_failed ?? 0
                                }}</strong>
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
                            <span class="detail-label">年月</span>
                            <strong>
                                <template
                                    v-if="
                                        taskDetail.parsed_year &&
                                        taskDetail.parsed_month
                                    "
                                >
                                    {{ taskDetail.parsed_year }}-{{
                                        String(
                                            taskDetail.parsed_month,
                                        ).padStart(2, "0")
                                    }}
                                </template>
                                <template v-else>-</template>
                            </strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">店铺</span>
                            <strong
                                ><ShopBadge
                                    :label="taskDetail.shop_name || '-'"
                                    :color="taskDetail.shop_color"
                                    size="table"
                            /></strong>
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
                                <strong>{{
                                    formatDateTime(taskDetail.created_at)
                                }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">开始时间</span>
                                <strong>{{
                                    formatDateTime(taskDetail.started_at)
                                }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">完成时间</span>
                                <strong>{{
                                    formatDateTime(taskDetail.finished_at)
                                }}</strong>
                            </div>
                        </div>
                    </div>
                </section>

                <section
                    v-if="taskErrorReason(taskDetail)"
                    class="detail-card detail-card--danger"
                >
                    <div class="detail-card-header">
                        <span>错误原因</span>
                    </div>
                    <p class="detail-error">
                        {{ taskErrorReason(taskDetail) }}
                    </p>
                </section>

                <section v-if="taskDetail.result_summary" class="detail-card">
                    <div class="detail-card-header">
                        <span>结果摘要</span>
                    </div>
                    <pre class="detail-summary-json">{{
                        formatJson(taskDetail.result_summary)
                    }}</pre>
                </section>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Tasks" });

import {
    ref,
    reactive,
    computed,
    onMounted,
    onUnmounted,
    onActivated,
    onDeactivated,
} from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import {
    getTaskList,
    retryTask,
    recalculateTask,
    batchRetryTasks,
    batchRecalculateTasks,
    type Task,
    type TaskBatchActionResult,
} from "@/api/task";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import { formatDateTime, getPlatformLabel } from "@/utils/format";
import { usePageRefresh } from "@/composables/pageRefresh";
import {
    getFallbackPlatforms,
    getReportPlatformCode,
    toSourcePlatformOptions,
    type PlatformOption,
} from "@/utils/platform";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import UploadView from "@/views/upload/index.vue";
import PlatformBadge from "@/components/PlatformBadge.vue";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";

// Search
const searchForm = reactive({
    sourceMonth: "",
    platforms: [] as string[],
    shopIds: [] as number[],
    parsedTypes: [] as string[],
    statuses: [] as string[],
    keyword: "",
});

const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toSourcePlatformOptions(platforms.value),
);

const typeOptions = [
    { label: "动账", value: "动账" },
    { label: "GMV", value: "gmv" },
    { label: "BIC", value: "bic" },
    { label: "运费险", value: "运费险" },
    { label: "订单", value: "订单" },
    { label: "其他服务款", value: "其他服务款" },
];

// Table
const loading = ref(false);
const tableData = ref<Task[]>([]);
const shopLoading = ref(false);
const shopOptions = ref<Shop[]>([]);
const retryingTaskId = ref<number | null>(null);
const recalculatingTaskId = ref<number | null>(null);
const batchRetrying = ref(false);
const batchRecalculating = ref(false);
const retryDialogVisible = ref(false);
const retryTarget = ref<Task | null>(null);
const selectedRows = ref<Task[]>([]);
const uploadDrawerVisible = ref(false);
const taskDetailDrawerVisible = ref(false);
const taskDetail = ref<Task | null>(null);
const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

// Auto-refresh
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const hasRunningTasks = computed(() => {
    return tableData.value.some(
        (t) => t.status === "running" || t.status === "queued",
    );
});

const retryTargetLabel = computed(() => {
    return retryTarget.value?.filename || retryTarget.value?.id || "";
});

const selectedYear = computed(() => {
    if (!searchForm.sourceMonth) return undefined;
    const [year] = searchForm.sourceMonth.split("-");
    return Number(year) || undefined;
});

const selectedMonth = computed(() => {
    if (!searchForm.sourceMonth) return undefined;
    const [, month] = searchForm.sourceMonth.split("-");
    return Number(month) || undefined;
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

const selectedPlatformsParam = computed(
    () => searchForm.platforms.join(",") || undefined,
);
const selectedShopIdsParam = computed(
    () => searchForm.shopIds.join(",") || undefined,
);
const selectedParsedTypesParam = computed(
    () => searchForm.parsedTypes.join(",") || undefined,
);
const selectedStatusesParam = computed(
    () => searchForm.statuses.join(",") || undefined,
);
const selectedReportPlatformsParam = computed(() => {
    const values = new Set(
        searchForm.platforms
            .map((platform) => getReportPlatformCode(platform, platforms.value))
            .filter(Boolean),
    );
    return Array.from(values).join(",") || undefined;
});

const selectedCount = computed(() => selectedRows.value.length);
const selectedRetryableRows = computed(() =>
    selectedRows.value.filter(
        (row) => row.status === "failed" && !isActionExpired(row),
    ),
);
const selectedRecalculableRows = computed(() =>
    selectedRows.value.filter((row) => canRecalculate(row)),
);

interface TaskFilterTag extends ActiveFilterTag {
    key: "sourceMonth" | "platforms" | "shopIds" | "parsedTypes" | "statuses" | "keyword";
}

const activeFilterTags = computed<TaskFilterTag[]>(() => {
    const tags: TaskFilterTag[] = [];
    if (searchForm.sourceMonth) tags.push({ key: "sourceMonth", label: "年月", value: searchForm.sourceMonth });
    searchForm.platforms.forEach((value) => tags.push({ key: "platforms", label: "平台", value: getPlatformLabel(value) }));
    searchForm.shopIds.forEach((value) => {
        const shop = shopOptions.value.find((item) => item.id === value);
        tags.push({ key: "shopIds", label: "店铺", value: shop?.shop_name || String(value) });
    });
    searchForm.parsedTypes.forEach((value) => tags.push({ key: "parsedTypes", label: "性质", value: typeOptions.find((item) => item.value === value)?.label || value }));
    searchForm.statuses.forEach((value) => tags.push({ key: "statuses", label: "状态", value: statusLabel(value) }));
    if (searchForm.keyword.trim()) tags.push({ key: "keyword", label: "搜索", value: searchForm.keyword.trim() });
    return tags;
});

function statusTagType(status: string): string {
    const map: Record<string, string> = {
        queued: "info",
        running: "warning",
        success: "success",
        failed: "danger",
        cancelled: "info",
    };
    return map[status] || "info";
}

function statusLabel(status: string): string {
    const map: Record<string, string> = {
        queued: "排队中",
        running: "运行中",
        success: "成功",
        failed: "失败",
        cancelled: "已取消",
    };
    return map[status] || status;
}

function isActionExpired(row: Task) {
    if (row.action_expired) return true;
    if (!row.created_at) return false;
    const createdAt = new Date(row.created_at).getTime();
    if (Number.isNaN(createdAt)) return false;
    return Date.now() - createdAt > 30 * 24 * 60 * 60 * 1000;
}

function canRecalculate(row: Task) {
    return !["queued", "running"].includes(row.status) && !isActionExpired(row);
}

function taskErrorReason(row: Task) {
    return (
        row.error_reason ||
        row.error_message ||
        formatSummaryErrors(row.result_summary?.errors)
    );
}

function formatSummaryErrors(errors: unknown) {
    if (!errors) return "";
    if (Array.isArray(errors))
        return errors.filter(Boolean).map(String).join("；");
    if (typeof errors === "string") return errors;
    return JSON.stringify(errors);
}

function formatJson(value: unknown) {
    return JSON.stringify(value, null, 2);
}

function openTaskDetail(row: Task) {
    taskDetail.value = row;
    taskDetailDrawerVisible.value = true;
}

function handleSelectionChange(rows: Task[]) {
    selectedRows.value = rows;
}

async function fetchData() {
    loading.value = true;
    try {
        const res = await getTaskList({
            page: pagination.page,
            page_size: pagination.pageSize,
            parsed_year: selectedYear.value,
            parsed_month: selectedMonth.value,
            platform: selectedPlatformsParam.value,
            shop_id: selectedShopIdsParam.value,
            parsed_type: selectedParsedTypesParam.value,
            status: selectedStatusesParam.value,
            keyword: searchForm.keyword || undefined,
        });
        tableData.value = res.items || [];
        pagination.total = res.total || 0;
        selectedRows.value = selectedRows.value.filter((selected) =>
            tableData.value.some((row) => row.id === selected.id),
        );
    } catch {
        // Error handled by interceptor
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
    searchForm.sourceMonth = "";
    searchForm.platforms = [];
    searchForm.shopIds = [];
    searchForm.parsedTypes = [];
    searchForm.statuses = [];
    searchForm.keyword = "";
    pagination.page = 1;
    fetchShopOptions();
    fetchData();
}

async function removeFilterTag(tag: TaskFilterTag) {
    if (tag.key === "sourceMonth") {
        searchForm.sourceMonth = "";
    } else if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter((item) => getPlatformLabel(item) !== tag.value);
        await fetchShopOptions();
        const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
        searchForm.shopIds = searchForm.shopIds.filter((shopId) => availableShopIds.has(shopId));
    } else if (tag.key === "shopIds") {
        searchForm.shopIds = searchForm.shopIds.filter((item) => {
            const shop = shopOptions.value.find((shopItem) => shopItem.id === item);
            return (shop?.shop_name || String(item)) !== tag.value;
        });
    } else if (tag.key === "parsedTypes") {
        searchForm.parsedTypes = searchForm.parsedTypes.filter((item) => (typeOptions.find((type) => type.value === item)?.label || item) !== tag.value);
    } else if (tag.key === "statuses") {
        searchForm.statuses = searchForm.statuses.filter((item) => statusLabel(item) !== tag.value);
    } else if (tag.key === "keyword") {
        searchForm.keyword = "";
    }
    handleSearch();
}

function openUploadDrawer() {
    uploadDrawerVisible.value = true;
    stopAutoRefresh();
}

async function closeUploadDrawer() {
    uploadDrawerVisible.value = false;
    await fetchData();
    startAutoRefresh();
}

async function handleUploadFinished() {
    await fetchData();
}

function handleContinueUpload() {
    fetchData();
}

async function handleRetry(row: Task) {
    if (isActionExpired(row)) {
        ElMessage.warning(row.action_expire_reason || "任务已过期，不能重试");
        await fetchData();
        return;
    }
    retryTarget.value = row;
    retryDialogVisible.value = true;
    stopAutoRefresh();
}

function handleRetryDialogClosed() {
    retryTarget.value = null;
    if (retryingTaskId.value === null) {
        startAutoRefresh();
    }
}

async function confirmRetry() {
    if (!retryTarget.value || retryingTaskId.value !== null) return;

    if (isActionExpired(retryTarget.value)) {
        ElMessage.warning(
            retryTarget.value.action_expire_reason || "任务已过期，不能重试",
        );
        retryDialogVisible.value = false;
        await fetchData();
        return;
    }

    const taskId = retryTarget.value.id;
    retryingTaskId.value = taskId;
    try {
        await retryTask(taskId);
        ElMessage.success("已重新提交任务");
        retryDialogVisible.value = false;
        await fetchData();
    } catch {
        // Error handled by interceptor
    } finally {
        retryingTaskId.value = null;
        startAutoRefresh();
    }
}

async function handleRecalculate(row: Task) {
    if (isActionExpired(row)) {
        ElMessage.warning(
            row.action_expire_reason || "任务已过期，不能重新统计",
        );
        await fetchData();
        return;
    }
    recalculatingTaskId.value = row.id;
    stopAutoRefresh();
    try {
        await recalculateTask(row.id);
        ElMessage.success("已重新提交统计任务");
        await fetchData();
    } catch {
        // Error handled by interceptor
    } finally {
        recalculatingTaskId.value = null;
        startAutoRefresh();
    }
}

function showBatchResult(result: TaskBatchActionResult, successText: string) {
    if (result.failed_count > 0) {
        const firstFailure = result.failed_items[0];
        ElMessage.warning(
            `${successText} ${result.success_count} 个，失败 ${result.failed_count} 个${
                firstFailure ? `：${firstFailure.message}` : ""
            }`,
        );
        return;
    }
    ElMessage.success(`${successText} ${result.success_count} 个`);
}

async function handleBatchRetry() {
    const rows = selectedRetryableRows.value;
    if (!rows.length) {
        ElMessage.warning("请选择未过期的失败任务");
        return;
    }

    batchRetrying.value = true;
    stopAutoRefresh();
    try {
        const result = await batchRetryTasks(rows.map((row) => row.id));
        showBatchResult(result, "已重新提交任务");
        await fetchData();
    } catch {
        await fetchData();
    } finally {
        batchRetrying.value = false;
        startAutoRefresh();
    }
}

async function handleBatchRecalculate() {
    const rows = selectedRecalculableRows.value;
    if (!rows.length) {
        ElMessage.warning("请选择可重新统计且未过期的任务");
        return;
    }

    batchRecalculating.value = true;
    stopAutoRefresh();
    try {
        const result = await batchRecalculateTasks(rows.map((row) => row.id));
        showBatchResult(result, "已重新提交统计任务");
        await fetchData();
    } catch {
        await fetchData();
    } finally {
        batchRecalculating.value = false;
        startAutoRefresh();
    }
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

onActivated(() => {
    startAutoRefresh();
});

onDeactivated(() => {
    stopAutoRefresh();
});

onUnmounted(() => {
    stopAutoRefresh();
});

usePageRefresh(fetchData);
</script>

<style scoped lang="scss">
.page-container {
    width: 100%;
}

.table-card {
    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        &-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
        }

        &-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
    }
}

.batch-actions {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.batch-actions-count {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
}

.task-action-group {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: 100%;
    min-width: 0;
    white-space: nowrap;

    :deep(.el-button) {
        margin-left: 0;
    }
}

.created-time-stack {
    display: inline-grid;
    gap: 4px;
    justify-items: start;
    line-height: 1.25;
}

:deep(.task-table .created-time-column .cell) {
    white-space: nowrap;
    word-break: keep-all;
}

:deep(.task-table .task-action-column .cell) {
    padding-left: 8px;
    padding-right: 8px;
}

.result-stack {
    display: inline-grid;
    gap: 3px;
    justify-items: stretch;
    min-width: 76px;
    line-height: 1.25;
}

.result-stack--detail {
    justify-items: start;
}

.result-line {
    display: inline-flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    min-height: 20px;
    font-size: 12px;

    em {
        color: var(--text-tertiary);
        font-style: normal;
        font-weight: 600;
    }

    strong {
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 13px;
        font-weight: 700;
    }
}

.result-line--success strong {
    color: var(--success);
}

.result-line--failed strong {
    color: var(--warning);
}

.retry-dialog-text {
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.7;
    margin: 0;
    word-break: break-all;
}

.detail-panel {
    display: grid;
    gap: 12px;
}

.detail-hero-card,
.detail-card {
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.detail-hero-card {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 132px;
    gap: 12px;
    align-items: stretch;
    padding: 14px;
}

.detail-hero-main {
    display: grid;
    align-content: start;
    gap: 10px;
    min-width: 0;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 15px;
        font-weight: 700;
        line-height: 1.5;
        word-break: break-all;
    }
}

.detail-kicker {
    color: var(--text-tertiary);
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 11px;
    font-weight: 700;
}

.detail-badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    min-width: 0;
}

.detail-result-card {
    display: grid;
    align-content: center;
    justify-items: stretch;
    gap: 8px;
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);

    > span {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 700;
    }
}

.detail-card {
    display: grid;
    gap: 12px;
    padding: 14px;
}

.detail-card--danger {
    border-color: var(--error);
    background: var(--error-light);
}

.detail-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;

    span {
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
    }
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}

.detail-item {
    display: grid;
    gap: 5px;
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);

    strong {
        overflow: hidden;
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.detail-label {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.detail-timeline {
    display: grid;
    gap: 10px;
}

.detail-time-item {
    display: grid;
    grid-template-columns: 14px minmax(0, 1fr);
    gap: 8px;
    align-items: start;
    min-width: 0;

    strong {
        display: block;
        margin-top: 2px;
        color: var(--text-primary);
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 12px;
        font-weight: 700;
    }
}

.detail-dot {
    width: 8px;
    height: 8px;
    margin-top: 6px;
    border-radius: 50%;
    background: var(--primary);
    box-shadow: 0 0 0 4px var(--primary-light-9);
}

.detail-error {
    margin: 0;
    color: var(--danger) !important;
    font-size: 13px;
    line-height: 1.7;
    word-break: break-word;
}

.detail-summary-json {
    margin: 0;
    max-height: 280px;
    overflow: auto;
    border: 1px solid var(--border-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--code-bg);
    color: var(--code-text);
    padding: 10px;
    font-size: 12px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}

@media (max-width: 768px) {
    .detail-hero-card,
    .detail-grid {
        grid-template-columns: 1fr;
    }
}
</style>
