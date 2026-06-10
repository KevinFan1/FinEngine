<template>
    <div class="page-container page-container--flow checklist-page">
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
                    label="状态"
                    class="filter-field filter-field--status"
                >
                    <el-select
                        v-model="filters.status"
                        clearable
                        placeholder="任务状态"
                    >
                        <el-option label="排队中" value="queued" />
                        <el-option label="运行中" value="running" />
                        <el-option label="成功" value="success" />
                        <el-option label="部分成功" value="partial_success" />
                        <el-option label="失败" value="failed" />
                        <el-option label="已过期" value="expired" />
                    </el-select>
                </el-form-item>
                <el-form-item
                    label="关键词"
                    class="filter-field filter-field--keyword"
                >
                    <el-input
                        v-model="filters.keyword"
                        clearable
                        placeholder="关键词：文件名 / 错误信息"
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
                        <span class="card-header-title">任务中心</span>
                        <span class="summary-count"
                            >共 {{ pagination.total }} 条</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <div
                            v-if="selectedRows.length > 0"
                            class="batch-actions"
                        >
                            <span class="batch-actions-count"
                                >已选 {{ selectedRows.length }} 条</span
                            >
                            <el-button
                                size="small"
                                type="primary"
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
                v-loading="loading"
                :data="rows"
                border
                stripe
                row-key="id"
                class="summary-table roomy-table task-table"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="46" fixed="left" />
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">
                        {{ rowIndex($index) }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="original_name"
                    label="文件名"
                    min-width="240"
                    show-overflow-tooltip
                />
                <el-table-column label="任务类型" width="112" align="center">
                    <template #default="{ row }">
                        <span class="status-pill task-type-pill">{{ taskTypeLabel(row.task_type) }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    v-if="userStore.isSuperAdmin"
                    prop="org_name"
                    label="组织"
                    width="160"
                    show-overflow-tooltip
                />
                <el-table-column label="状态" width="110" align="center">
                    <template #default="{ row }">
                        <span :class="statusClass(row.status)">{{
                            taskStatusLabel(row.status)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column label="处理结果" width="120" align="center">
                    <template #default="{ row }">
                        <div class="result-stack">
                            <span class="result-line result-line--success">
                                <em>成功</em>
                                <strong>{{ row.success_rows || 0 }}</strong>
                            </span>
                            <span class="result-line result-line--failed">
                                <em>忽略</em>
                                <strong>{{ row.failed_rows || 0 }}</strong>
                            </span>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column label="创建时间" width="170">
                    <template #default="{ row }">{{
                        formatDateTime(row.created_at)
                    }}</template>
                </el-table-column>
                <el-table-column label="开始时间" width="170">
                    <template #default="{ row }">{{
                        row.started_at ? formatDateTime(row.started_at) : "-"
                    }}</template>
                </el-table-column>
                <el-table-column label="结束时间" width="170">
                    <template #default="{ row }">{{
                        row.finished_at ? formatDateTime(row.finished_at) : "-"
                    }}</template>
                </el-table-column>
                <el-table-column label="更新时间" width="170">
                    <template #default="{ row }">{{
                        formatDateTime(row.updated_at || row.created_at)
                    }}</template>
                </el-table-column>

                <el-table-column
                    label="操作"
                    width="220"
                    fixed="right"
                    align="center"
                >
                    <template #default="{ row }">
                        <div class="task-action-group">
                            <el-button
                                link
                                type="primary"
                                @click="openDetails(row)"
                                >查看</el-button
                            >
                            <el-button
                                v-if="userStore.isSuperAdmin"
                                link
                                type="primary"
                                :loading="downloadingTaskId === row.id"
                                @click="downloadSource(row)"
                            >
                                下载原表
                            </el-button>
                            <el-button
                                link
                                type="primary"
                                :loading="rerunningTaskId === row.id"
                                @click="retry(row)"
                                >重新统计</el-button
                            >
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
            v-model="detailVisible"
            title="任务详情"
            size="520px"
            append-to-body
            destroy-on-close
        >
            <div v-if="currentTask" class="detail-panel">
                <section class="detail-hero-card">
                    <div class="detail-hero-main">
                        <span class="detail-kicker"
                            >TASK #{{ currentTask.id }}</span
                        >
                        <h3>{{ currentTask.original_name }}</h3>
                        <div class="detail-badge-row">
                            <span :class="statusClass(currentTask.status)">{{
                                taskStatusLabel(currentTask.status)
                            }}</span>
                            <el-button
                                v-if="userStore.isSuperAdmin"
                                size="small"
                                :loading="downloadingTaskId === currentTask.id"
                                @click="downloadSource(currentTask)"
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
                                <strong>{{
                                    currentTask.success_rows || 0
                                }}</strong>
                            </span>
                            <span class="result-line result-line--failed">
                                <em>忽略</em>
                                <strong>{{
                                    currentTask.failed_rows || 0
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
                            <span class="detail-label">总行数</span>
                            <strong>{{ currentTask.total_rows || 0 }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">新增 / 更新</span>
                            <strong
                                >{{ currentTask.inserted_rows || 0 }} /
                                {{ currentTask.updated_rows || 0 }}</strong
                            >
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
                                <strong>{{ formatDateTime(currentTask.created_at) }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">开始时间</span>
                                <strong>{{
                                    currentTask.started_at
                                        ? formatDateTime(currentTask.started_at)
                                        : "-"
                                }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">结束时间</span>
                                <strong>{{
                                    currentTask.finished_at
                                        ? formatDateTime(currentTask.finished_at)
                                        : "-"
                                }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">更新时间</span>
                                <strong>{{
                                    formatDateTime(
                                        currentTask.updated_at || currentTask.created_at,
                                    )
                                }}</strong>
                            </div>
                        </div>
                    </div>
                </section>

                <section
                    v-if="currentTask.error_message"
                    class="detail-card detail-card--danger"
                >
                    <div class="detail-card-header">
                        <span>提示</span>
                    </div>
                    <p class="detail-error">{{ currentTask.error_message }}</p>
                </section>

                <section
                    v-if="taskSummaryItems(currentTask).length"
                    class="detail-card"
                >
                    <div class="detail-card-header">
                        <span>结果摘要</span>
                    </div>
                    <div class="detail-summary-list">
                        <div
                            v-for="item in taskSummaryItems(currentTask)"
                            :key="item.key"
                            class="detail-summary-item"
                        >
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    batchRecalculateReconciliationChecklistTasks,
    getReconciliationChecklistTaskSourceDownload,
    listReconciliationChecklistTasks,
    retryReconciliationChecklistTask,
    type ReconciliationChecklistTask,
    type ReconciliationChecklistTaskBatchActionResult,
} from "@/api/reconciliationChecklist";
import { useUserStore } from "@/stores/user";
import { formatDateTime } from "@/utils/format";
import { resultSummaryItems } from "@/utils/resultSummary";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import { useRoute, useRouter } from "vue-router";

const userStore = useUserStore();
const route = useRoute();
const router = useRouter();
const orgOptions = ref<Organization[]>([]);
const loading = ref(false);
const rows = ref<ReconciliationChecklistTask[]>([]);
const selectedRows = ref<ReconciliationChecklistTask[]>([]);
const currentTask = ref<ReconciliationChecklistTask | null>(null);
const detailVisible = ref(false);
const rerunningTaskId = ref<number | null>(null);
const downloadingTaskId = ref<number | null>(null);
const batchRecalculating = ref(false);
const filters = reactive({
    org_id: undefined as number | undefined,
    status: "",
    keyword: "",
});
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const querySyncing = ref(false);
const TASK_PAGE_STATE_KEY = "reconciliation-checklist:tasks";
const TASK_QUERY_KEYS = [
    "page",
    "page_size",
    "org_id",
    "status",
    "keyword",
] as const;
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const hasRunningTasks = computed(() => {
    return rows.value.some((task) =>
        ["queued", "running"].includes(task.status),
    );
});

function taskStatusLabel(status: string) {
    return (
        (
            {
                queued: "排队中",
                running: "运行中",
                success: "成功",
                partial_success: "部分成功",
                failed: "失败",
                expired: "已过期",
            } as Record<string, string>
        )[status] || status
    );
}

function taskTypeLabel(taskType: string | undefined | null) {
    return (
        (
            {
                source_import: "底表导入",
                invoice_edit: "发票修改",
                merchant_edit: "商家修改",
            } as Record<string, string>
        )[taskType || "source_import"] || taskType || "底表导入"
    );
}

function statusClass(status: string) {
    return (
        {
            queued: "status-pill",
            running: "status-pill status-pill--info",
            success: "status-pill status-pill--success",
            partial_success: "status-pill status-pill--warning",
            failed: "status-pill status-pill--error",
            expired: "status-pill status-pill--muted",
        }[status] || "status-pill"
    );
}

function rowIndex(index: number) {
    return (pagination.page - 1) * pagination.pageSize + index + 1;
}

function queryString(value: unknown): string {
    if (Array.isArray(value)) return value.filter(Boolean).join(",");
    return typeof value === "string" ? value : "";
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
    filters.status = queryString(route.query.status);
    filters.keyword = queryString(route.query.keyword);
}

function hasRouteState() {
    return TASK_QUERY_KEYS.some((key) => {
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
    const raw = sessionStorage.getItem(TASK_PAGE_STATE_KEY);
    if (!raw) {
        applyRouteQuery();
        return;
    }
    try {
        const state = JSON.parse(raw) as {
            page?: number;
            pageSize?: number;
            org_id?: number | null;
            status?: string;
            keyword?: string;
        };
        pagination.page = state.page && state.page > 0 ? state.page : 1;
        pagination.pageSize =
            state.pageSize && state.pageSize > 0
                ? state.pageSize
                : DEFAULT_PAGE_SIZE;
        filters.org_id = state.org_id || undefined;
        filters.status = state.status || "";
        filters.keyword = state.keyword || "";
    } catch {
        applyRouteQuery();
    }
}

function persistPageState() {
    sessionStorage.setItem(
        TASK_PAGE_STATE_KEY,
        JSON.stringify({
            page: pagination.page,
            pageSize: pagination.pageSize,
            org_id: filters.org_id ?? null,
            status: filters.status,
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
        status: filters.status || undefined,
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

async function fetchData() {
    await syncRouteQuery();
    persistPageState();
    loading.value = true;
    try {
        const res = await listReconciliationChecklistTasks({
            page: pagination.page,
            page_size: pagination.pageSize,
            org_id: filters.org_id,
            status: filters.status || undefined,
            keyword: filters.keyword || undefined,
        });
        rows.value = res.items;
        pagination.total = res.total || 0;
    } finally {
        loading.value = false;
    }
}

function handleSelectionChange(selection: ReconciliationChecklistTask[]) {
    selectedRows.value = selection;
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function resetFilters() {
    filters.org_id = undefined;
    filters.status = "";
    filters.keyword = "";
    handleSearch();
}

async function retry(row: ReconciliationChecklistTask) {
    await ElMessageBox.confirm(
        `确认重新统计 ${row.original_name}？`,
        "重新统计",
        { type: "warning" },
    );
    rerunningTaskId.value = row.id;
    stopAutoRefresh();
    try {
        await retryReconciliationChecklistTask(row.id);
        ElMessage.success("已提交重新统计");
        await fetchData();
    } finally {
        rerunningTaskId.value = null;
        startAutoRefresh();
    }
}

function showBatchResult(result: ReconciliationChecklistTaskBatchActionResult) {
    if (result.failed_count > 0) {
        const firstFailure = result.failed_items[0];
        ElMessage.warning(
            `已重新提交 ${result.success_count} 个，失败 ${result.failed_count} 个${firstFailure ? `：${firstFailure.message}` : ""}`,
        );
        return;
    }
    ElMessage.success(`已重新提交 ${result.success_count} 个`);
}

async function handleBatchRecalculate() {
    if (!selectedRows.value.length) {
        ElMessage.warning("请选择任务");
        return;
    }
    batchRecalculating.value = true;
    stopAutoRefresh();
    try {
        const result = await batchRecalculateReconciliationChecklistTasks(
            selectedRows.value.map((row) => row.id),
        );
        showBatchResult(result);
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

function openDetails(row: ReconciliationChecklistTask) {
    currentTask.value = row;
    detailVisible.value = true;
}

function taskSummaryItems(task: ReconciliationChecklistTask) {
    return resultSummaryItems(task.result_summary, {
        excludeKeys: task.error_message ? ["错误明细", "errors"] : [],
    });
}

async function downloadSource(row: ReconciliationChecklistTask) {
    if (!userStore.isSuperAdmin || downloadingTaskId.value !== null) return;
    downloadingTaskId.value = row.id;
    try {
        const credential = await getReconciliationChecklistTaskSourceDownload(
            row.id,
        );
        const link = document.createElement("a");
        link.href = credential.download_url;
        link.download =
            credential.filename || row.original_name || "对账清单原表.xlsx";
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    } finally {
        downloadingTaskId.value = null;
    }
}

onMounted(async () => {
    restorePageState();
    await fetchOrgs();
    await fetchData();
    startAutoRefresh();
});

onUnmounted(() => {
    stopAutoRefresh();
});

watch(
    () => route.query,
    async () => {
        if (querySyncing.value) return;
        applyRouteQuery();
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

:deep(.search-card .el-card__body) {
    padding-bottom: 6px;
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
    grid-template-columns:
        minmax(180px, 220px) minmax(160px, 180px) minmax(220px, 300px)
        auto;
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
:deep(.checklist-filter-card .filter-field .el-select) {
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

.task-type-pill {
    background: #eef4ff;
    color: #1d4ed8;
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

.batch-actions {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 8px;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    background: var(--bg-elevated);
}

.batch-actions-count {
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.task-action-group {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    flex-wrap: wrap;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-shrink: 0;
    min-width: 0;
    margin-top: 0;
    padding: 12px 18px;
    border-top: 1px solid var(--border-light);
    background: var(--bg-elevated);
    overflow-x: auto;
    overflow-y: hidden;

    :deep(.el-pagination) {
        flex-shrink: 0;
        min-width: max-content;
    }
}
.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 72px;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--bg-hover);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
    line-height: 1.4;
}

.status-pill--info {
    background: var(--info-light);
    color: var(--info);
}

.status-pill--success {
    background: var(--success-light);
    color: var(--success);
}

.status-pill--warning {
    background: var(--warning-light);
    color: var(--warning);
}

.status-pill--error {
    background: var(--error-light);
    color: var(--error);
}

.status-pill--muted {
    background: var(--bg-hover);
    color: var(--text-tertiary);
}

.result-stack {
    display: inline-grid;
    gap: 4px;
}

.result-stack--compact {
    gap: 2px;
}

.result-line {
    display: inline-flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    min-width: 74px;
    font-size: 12px;
    line-height: 1.2;
}

.result-line em {
    font-style: normal;
    color: var(--text-tertiary);
}

.result-line strong {
    color: var(--text-primary);
}

.result-line--success strong {
    color: var(--success);
}

.result-line--failed strong {
    color: var(--error);
}

.task-warning-text {
    color: var(--warning);
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
}

.detail-hero-main h3 {
    margin: 0;
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
    line-height: 1.5;
    word-break: break-all;
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
}

.detail-result-card > span {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
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
}

.detail-card-header span {
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
}

.detail-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}

.detail-item {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.detail-label {
    color: var(--text-tertiary);
    font-size: 12px;
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
}

.detail-time-item strong {
    display: block;
    margin-top: 2px;
    color: var(--text-primary);
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    font-weight: 700;
}

.detail-dot {
    width: 8px;
    height: 8px;
    margin-top: 6px;
    border-radius: 50%;
    background: var(--primary);
    box-shadow: 0 0 0 4px var(--primary-light-9);
}

.detail-item strong {
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.4;
}

.detail-error {
    margin: 0;
    white-space: pre-wrap;
    color: var(--error);
    font-size: 13px;
    line-height: 1.6;
}

.detail-summary-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}

.detail-summary-item {
    display: grid;
    gap: 5px;
    min-width: 0;
    padding: 10px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);
}

.detail-summary-item span {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 600;
}

.detail-summary-item strong {
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-word;
}

.text-tertiary {
    color: var(--text-tertiary);
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
    :deep(.checklist-filter-card .filter-form .el-select) {
        width: 100% !important;
    }

    .detail-hero-card,
    .detail-grid,
    .detail-summary-list {
        grid-template-columns: 1fr;
    }
}
</style>
