<template>
    <div class="page-container page-container--flow transaction-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="数据年月">
                    <el-date-picker
                        v-model="searchForm.sourceMonth"
                        type="month"
                        placeholder="选择数据年月"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 160px"
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
                        placeholder="状态"
                        multiple
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        style="width: 160px"
                    >
                        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                </el-form-item>
                <el-form-item label="搜索">
                    <el-input
                        v-model="searchForm.keyword"
                        clearable
                        placeholder="搜文件名/错误原因"
                        style="width: 220px"
                        @keyup.enter="handleSearch"
                    >
                        <template #prefix>
                            <el-icon><Search /></el-icon>
                        </template>
                    </el-input>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">搜索</el-button>
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">对账任务</span>
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
                                :disabled="selectedRetryableRows.length === 0"
                                :loading="batchRetrying"
                                @click="handleBatchRetry"
                            >
                                批量重新处理
                            </el-button>
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
                <el-table-column prop="filename" label="文件名" min-width="190" show-overflow-tooltip />
                <el-table-column label="性质" width="120" align="center">
                    <template #default="{ row }">
                        <FileTypeBadge :type="taskType(row)" />
                    </template>
                </el-table-column>
                <el-table-column label="数据年月" width="120">
                    <template #default="{ row }">{{ formatMonth(row.parsed_year, row.parsed_month) }}</template>
                </el-table-column>
                <el-table-column prop="platform" label="平台" width="100">
                    <template #default="{ row }">
                        <PlatformBadge v-if="row.platform" :platform="row.platform" />
                        <span v-else class="text-tertiary">-</span>
                    </template>
                </el-table-column>
                <el-table-column prop="shop_name" label="识别店铺" width="170" show-overflow-tooltip>
                    <template #default="{ row }">
                        <ShopBadge
                            :label="taskShopLabel(row)"
                            :color="row.shop_color"
                            size="table"
                        />
                    </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="100" align="center">
                    <template #default="{ row }">
                        <el-tag
                            :type="statusTagType(row.status)"
                            size="small"
                            :class="{ 'animate-pulse': row.status === 'running' }"
                        >
                            {{ statusText(row.status) }}
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
                <el-table-column label="提示" min-width="220" show-overflow-tooltip>
                    <template #default="{ row }">
                        <span v-if="tableHint(row)" class="task-warning-text">{{ tableHint(row) }}</span>
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
                            <el-tag v-if="isActionExpired(row)" type="info" size="small">已过期</el-tag>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="260" align="center" fixed="right" class-name="task-action-column">
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
                                v-if="canRetry(row)"
                                type="primary"
                                link
                                :loading="retryingTaskId === row.id"
                                :disabled="isActionExpired(row)"
                                @click="handleRetry(row)"
                            >
                                {{ retryActionLabel(row) }}
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
                    <el-empty description="暂无对账任务" :image-size="80" />
                </template>
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

        <el-dialog
            v-model="retryDialogVisible"
            :title="retryDialogTitle"
            width="420px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
            :close-on-press-escape="retryingTaskId === null"
            :show-close="retryingTaskId === null"
            @closed="handleRetryDialogClosed"
        >
            <p class="retry-dialog-text">
                确定要{{ retryDialogActionText }}任务「{{ retryTargetLabel }}」吗？
            </p>
            <template #footer>
                <el-button :disabled="retryingTaskId !== null" @click="retryDialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="retryingTaskId !== null" @click="confirmRetry">确定{{ retryDialogActionText }}</el-button>
            </template>
        </el-dialog>

        <el-drawer
            v-model="taskDetailDrawerVisible"
            title="任务详情"
            size="560px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="taskDetail" v-loading="taskDetailLoading" class="detail-panel">
                <section class="detail-hero-card">
                    <div class="detail-hero-main">
                        <span class="detail-kicker">TASK #{{ taskDetail.id }}</span>
                        <h3>{{ taskDetail.filename || "-" }}</h3>
                        <div class="detail-badge-row">
                            <FileTypeBadge :type="taskType(taskDetail)" />
                            <PlatformBadge v-if="taskDetail.platform" :platform="taskDetail.platform" />
                            <el-tag :type="statusTagType(taskDetail.status)" size="small">
                                {{ statusText(taskDetail.status) }}
                            </el-tag>
                            <el-tag v-if="isActionExpired(taskDetail)" type="info" size="small">已过期</el-tag>
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
                            <span class="detail-label">数据年月</span>
                            <strong>{{ formatMonth(taskDetail.parsed_year, taskDetail.parsed_month) }}</strong>
                        </div>
                        <div v-if="userStore.isSuperAdmin" class="detail-item">
                            <span class="detail-label">组织</span>
                            <strong>{{ taskDetail.org_name || `组织#${taskDetail.org_id}` }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">识别店铺</span>
                            <strong>
                                <ShopBadge
                                    :label="taskShopLabel(taskDetail)"
                                    :color="taskDetail.shop_color"
                                    size="table"
                                />
                            </strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">处理行数</span>
                            <strong>{{ taskProcessedCount(taskDetail) }}</strong>
                        </div>
                        <div v-if="taskType(taskDetail) === '红单'" class="detail-item">
                            <span class="detail-label">采购行数</span>
                            <strong>{{ summaryNumber(taskDetail, "purchase_rows") }}</strong>
                        </div>
                        <div v-if="taskType(taskDetail) === '红单'" class="detail-item">
                            <span class="detail-label">货款行数</span>
                            <strong>{{ summaryNumber(taskDetail, "payment_rows") }}</strong>
                        </div>
                        <div v-if="taskType(taskDetail) === '银行流水'" class="detail-item">
                            <span class="detail-label">已解析直播日期</span>
                            <strong>{{ summaryNumber(taskDetail, "matched_row_count") }}</strong>
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
                                <strong>{{ formatDateTime(taskDetail.started_at) }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">结束时间</span>
                                <strong>{{ formatDateTime(taskDetail.finished_at) }}</strong>
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

                <section v-if="taskWarnings(taskDetail).length" class="detail-card detail-card--warning">
                    <div class="detail-card-header">
                        <span>处理提示</span>
                    </div>
                    <ul class="detail-warning-list">
                        <li v-for="warning in taskWarnings(taskDetail).slice(0, 20)" :key="warning">{{ warning }}</li>
                    </ul>
                    <p v-if="taskWarnings(taskDetail).length > 20" class="detail-more-text">
                        另有 {{ taskWarnings(taskDetail).length - 20 }} 条提示，请查看任务结果摘要。
                    </p>
                </section>

                <section v-if="taskErrorReason(taskDetail)" class="detail-card detail-card--danger">
                    <div class="detail-card-header">
                        <span>错误原因</span>
                    </div>
                    <p class="detail-error">{{ taskErrorReason(taskDetail) }}</p>
                </section>

                <section v-if="taskSummaryItems(taskDetail).length" class="detail-card">
                    <div class="detail-card-header">
                        <span>结果摘要</span>
                    </div>
                    <div class="detail-summary-list">
                        <div v-for="item in taskSummaryItems(taskDetail)" :key="item.key" class="detail-summary-item">
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
defineOptions({ name: "MerchantReconciliationTasks" });

import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Loading, Search } from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    batchRecalculateTasks,
    batchRetryTasks,
    getTaskDetail,
    getTaskList,
    getTaskSourceDownload,
    recalculateTask,
    retryTask,
    type Task,
    type TaskBatchActionResult,
} from "@/api/task";
import { taskCreatedTimeShortcuts } from "@/utils/dateRange";
import { formatDateTime } from "@/utils/format";
import { usePageRefresh } from "@/composables/pageRefresh";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { formatMonth } from "./common";
import { isMerchantReconciliationRecalculateOnlyTaskType } from "@/views/accountingFilters";

const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const loading = ref(false);
const taskDetailLoading = ref(false);
const tableData = ref<Task[]>([]);
const selectedRows = ref<Task[]>([]);
const retryingTaskId = ref<number | null>(null);
const recalculatingTaskId = ref<number | null>(null);
const batchRetrying = ref(false);
const batchRecalculating = ref(false);
const downloadingTaskId = ref<number | null>(null);
const retryDialogVisible = ref(false);
const retryTarget = ref<Task | null>(null);
const taskDetailDrawerVisible = ref(false);
const taskDetail = ref<Task | null>(null);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const searchForm = reactive({
    sourceMonth: "",
    createdTimeRange: null as string[] | null,
    orgIds: [] as number[],
    statuses: [] as string[],
    keyword: "",
});

const statusOptions = [
    { label: "排队中", value: "queued" },
    { label: "运行中", value: "running" },
    { label: "成功", value: "success" },
    { label: "部分成功", value: "partial_success" },
    { label: "失败", value: "failed" },
    { label: "已过期", value: "expired" },
    { label: "已取消", value: "cancelled" },
];

let refreshTimer: ReturnType<typeof setInterval> | null = null;

const hasRunningTasks = computed(() => tableData.value.some((task) => task.status === "queued" || task.status === "running"));
const selectedCount = computed(() => selectedRows.value.length);
const selectedRetryableRows = computed(() => selectedRows.value.filter((row) => canRetry(row)));
const selectedRecalculableRows = computed(() => selectedRows.value.filter((row) => canRecalculate(row)));
const retryTargetLabel = computed(() => retryTarget.value?.filename || retryTarget.value?.id || "");
const retryDialogActionText = computed(() => (retryTarget.value ? retryActionText(retryTarget.value) : "重试"));
const retryDialogTitle = computed(() => `${retryDialogActionText.value}确认`);
const batchRetryActionText = computed(() => {
    if (!selectedRetryableRows.value.length) return "重新提交";
    return selectedRetryableRows.value.every((row) => taskType(row) === "银行流水") ? "重新处理" : "重新提交";
});
const selectedOrgIdsParam = computed(() => searchForm.orgIds.join(",") || undefined);
const selectedStatusesParam = computed(() => searchForm.statuses.join(",") || undefined);
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

function statusText(status: string) {
    const statusMap: Record<string, string> = {
        queued: "排队中",
        running: "运行中",
        success: "成功",
        partial_success: "部分成功",
        failed: "失败",
        expired: "已过期",
        cancelled: "已取消",
    };
    return statusMap[status] || status || "-";
}

function statusTagType(status: string) {
    const typeMap: Record<string, "success" | "danger" | "warning" | "info"> = {
        success: "success",
        partial_success: "warning",
        failed: "danger",
        expired: "info",
        cancelled: "info",
        running: "warning",
        queued: "info",
    };
    return typeMap[status] || "info";
}

function hasTaskResult(row: Task) {
    return ["success", "partial_success", "failed", "expired"].includes(row.status);
}

function taskProcessedCount(row: Task) {
    return row.processed_rows ?? 0;
}

function taskType(row: Task | null | undefined) {
    return String(row?.parsed_type || taskSummary(row as Task).type || "红单");
}

function taskShopLabel(row: Task) {
    return taskType(row) === "银行流水" ? "不按店铺" : row.shop_name || "多店铺/待识别";
}

function taskSuccessCount(row: Task) {
    return row.success_rows ?? row.result_success ?? 0;
}

function taskFailedCount(row: Task) {
    return row.failed_rows ?? row.result_failed ?? 0;
}

function isActionExpired(row: Task) {
    if (row.status === "expired") return true;
    if (row.action_expired) return true;
    if (!row.created_at) return false;
    const createdAt = new Date(row.created_at).getTime();
    if (Number.isNaN(createdAt)) return false;
    return Date.now() - createdAt > 30 * 24 * 60 * 60 * 1000;
}

function canRecalculate(row: Task) {
    if (taskType(row) !== "红单") return false;
    return !["queued", "running", "expired"].includes(row.status) && !isActionExpired(row);
}

function canRetry(row: Task) {
    if (isActionExpired(row) || row.status === "expired") return false;
    if (isMerchantReconciliationRecalculateOnlyTaskType(taskType(row))) {
        return false;
    }
    if (taskType(row) === "银行流水") {
        return !["queued", "running"].includes(row.status);
    }
    return row.status === "failed";
}

function retryActionText(row: Task) {
    return taskType(row) === "银行流水" ? "重新处理" : "重试";
}

function retryActionLabel(row: Task) {
    return retryActionText(row);
}

function retryExpiredMessage(row: Task) {
    return row.action_expire_reason || (taskType(row) === "银行流水" ? "任务已过期，不能重新处理" : "任务已过期，不能重试");
}

function taskSummary(row: Task) {
    return (row?.result_summary || {}) as Record<string, unknown>;
}

function normalizeTextList(value: unknown) {
    if (!value) return [];
    if (Array.isArray(value)) return value.filter(Boolean).map(String);
    if (typeof value === "string") return value ? [value] : [];
    return [JSON.stringify(value)];
}

function taskWarnings(row: Task) {
    return normalizeTextList(taskSummary(row).warnings);
}

function warningPreview(row: Task) {
    const warnings = taskWarnings(row);
    if (!warnings.length) return "";
    const suffix = warnings.length > 1 ? ` 等 ${warnings.length} 条` : "";
    return `${warnings[0]}${suffix}`;
}

function formatSummaryErrors(errors: unknown) {
    return normalizeTextList(errors).join("；");
}

function taskErrorReason(row: Task) {
    return (
        row.error_reason ||
        row.error_message ||
        formatSummaryErrors(taskSummary(row).errors)
    );
}

function tableHint(row: Task) {
    return warningPreview(row) || taskErrorReason(row);
}

const resultSummaryLabels: Record<string, string> = {
    type: "文件类型",
    red_sheet_id: "红单记录ID",
    bank_flow_file_id: "银行流水记录ID",
    total_rows: "总行数",
    success_rows: "成功行数",
    failed_rows: "失败行数",
    purchase_rows: "采购行数",
    payment_rows: "货款行数",
    matched_row_count: "已解析直播日期",
};
const hiddenSummaryKeys = new Set(["warnings", "errors"]);

function formatSummaryValue(value: unknown) {
    if (value == null || value === "") return "-";
    if (Array.isArray(value)) return value.filter(Boolean).map(String).join("；") || "-";
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
}

function taskSummaryItems(row: Task) {
    return Object.entries(taskSummary(row))
        .filter(([key]) => !hiddenSummaryKeys.has(key))
        .map(([key, value]) => ({
            key,
            label: resultSummaryLabels[key] || key,
            value: formatSummaryValue(value),
        }));
}

function summaryNumber(row: Task, key: string) {
    return Number(taskSummary(row)[key] || 0);
}

async function fetchData() {
    loading.value = true;
    try {
        const result = await getTaskList({
            page: pagination.page,
            page_size: pagination.pageSize,
            org_id: userStore.isSuperAdmin ? selectedOrgIdsParam.value : undefined,
            platform: "douyin",
            parsed_type: "红单,银行流水",
            parsed_year: selectedYear.value,
            parsed_month: selectedMonth.value,
            status: selectedStatusesParam.value,
            keyword: searchForm.keyword || undefined,
            created_start_time: searchForm.createdTimeRange?.[0] || undefined,
            created_end_time: searchForm.createdTimeRange?.[1] || undefined,
        });
        tableData.value = result.items || [];
        pagination.total = result.total || 0;
        const selectedIds = new Set(selectedRows.value.map((row) => row.id));
        selectedRows.value = tableData.value.filter((row) => selectedIds.has(row.id));
    } finally {
        loading.value = false;
    }
}

async function fetchOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    try {
        orgOptions.value = await getAllOrganizations();
    } catch {
        // Error handled by interceptor
    }
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.sourceMonth = "";
    searchForm.createdTimeRange = null;
    searchForm.orgIds = [];
    searchForm.statuses = [];
    searchForm.keyword = "";
    pagination.page = 1;
    fetchData();
}

function handleSizeChange(size: number) {
    pagination.pageSize = size;
    pagination.page = 1;
    fetchData();
}

function handlePageChange(page: number) {
    pagination.page = page;
    fetchData();
}

function handleSelectionChange(rows: Task[]) {
    selectedRows.value = rows;
}

async function openTaskDetail(row: Task) {
    taskDetail.value = row;
    taskDetailDrawerVisible.value = true;
    taskDetailLoading.value = true;
    try {
        taskDetail.value = await getTaskDetail(row.id);
    } finally {
        taskDetailLoading.value = false;
    }
}

async function handleDownloadSource(row: Task) {
    if (!userStore.isSuperAdmin || downloadingTaskId.value !== null) return;
    downloadingTaskId.value = row.id;
    try {
        const credential = await getTaskSourceDownload(row.id);
        const link = document.createElement("a");
        link.href = credential.download_url;
        link.download = credential.filename || row.filename || "原表.xlsx";
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } finally {
        downloadingTaskId.value = null;
    }
}

async function handleRetry(row: Task) {
    if (!canRetry(row)) {
        ElMessage.warning(taskType(row) === "银行流水" ? "当前银行流水任务不能重新处理" : "当前任务不能重试");
        if (isActionExpired(row)) {
            await fetchData();
        }
        return;
    }
    if (isActionExpired(row)) {
        ElMessage.warning(retryExpiredMessage(row));
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

    if (!canRetry(retryTarget.value)) {
        ElMessage.warning(
            taskType(retryTarget.value) === "银行流水"
                ? "当前银行流水任务不能重新处理"
                : "当前任务不能重试",
        );
        retryDialogVisible.value = false;
        await fetchData();
        return;
    }
    if (isActionExpired(retryTarget.value)) {
        ElMessage.warning(retryExpiredMessage(retryTarget.value));
        retryDialogVisible.value = false;
        await fetchData();
        return;
    }

    const taskId = retryTarget.value.id;
    retryingTaskId.value = taskId;
    try {
        await retryTask(taskId);
        ElMessage.success(`已${retryActionText(retryTarget.value)}任务`);
        retryDialogVisible.value = false;
        await fetchData();
        if (taskDetail.value?.id === taskId) {
            taskDetail.value = await getTaskDetail(taskId);
        }
    } finally {
        retryingTaskId.value = null;
        startAutoRefresh();
    }
}

async function handleRecalculate(row: Task) {
    if (isActionExpired(row)) {
        ElMessage.warning(row.action_expire_reason || "任务已过期，不能重新统计");
        await fetchData();
        return;
    }
    recalculatingTaskId.value = row.id;
    stopAutoRefresh();
    try {
        await recalculateTask(row.id);
        ElMessage.success("已重新提交统计任务");
        await fetchData();
        if (taskDetail.value?.id === row.id) {
            taskDetail.value = await getTaskDetail(row.id);
        }
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
        ElMessage.warning("请选择可重新提交且未过期的任务");
        return;
    }

    batchRetrying.value = true;
    stopAutoRefresh();
    try {
        const result = await batchRetryTasks(rows.map((row) => row.id));
        showBatchResult(result, `已${batchRetryActionText.value}任务`);
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
    await fetchOrgOptions();
    await fetchData();
    startAutoRefresh();
});

onUnmounted(() => {
    stopAutoRefresh();
});

usePageRefresh(fetchData);
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";

.task-warning-text {
    color: var(--warning);
    font-size: 12px;
    line-height: 1.5;
}

.retry-dialog-text {
    color: var(--text-primary);
    font-size: 14px;
    line-height: 1.7;
    margin: 0;
    word-break: break-all;
}

.detail-card--warning {
    border-color: var(--warning);
    background: var(--warning-light);
}

.detail-warning-list {
    display: grid;
    gap: 6px;
    margin: 0;
    padding-left: 18px;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.65;
}

.detail-more-text {
    margin: 0;
    color: var(--text-tertiary);
    font-size: 12px;
}
</style>
