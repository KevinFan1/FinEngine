<template>
    <div class="page-container download-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" inline>
                <el-form-item label="状态">
                    <el-select v-model="searchForm.status" clearable placeholder="状态">
                        <el-option label="排队中" value="queued" />
                        <el-option label="生成中" value="running" />
                        <el-option label="可下载" value="success" />
                        <el-option label="失败" value="failed" />
                        <el-option label="已过期" value="expired" />
                    </el-select>
                </el-form-item>
                <el-form-item label="模块">
                    <el-select v-model="searchForm.module" clearable placeholder="模块">
                        <el-option label="汇总" value="summary" />
                        <el-option label="资金科目核算" value="transaction_accounting" />
                        <el-option label="BIC对账" value="bic_accounting" />
                    </el-select>
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
                        <span class="card-header-title">导出任务</span>
                        <span class="summary-count">{{ tableSummary }}</span>
                    </div>
                    <div class="card-header-actions">
                        <el-tag v-if="hasActiveJobs" type="warning" size="small" class="animate-pulse">
                            <el-icon><Loading /></el-icon>
                            有 {{ activeJobCount }} 个任务生成中，自动刷新中...
                        </el-tag>
                        <el-button :loading="loading" @click="fetchData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table roomy-table download-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                row-key="id"
            >
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">
                        {{ rowIndex($index) }}
                    </template>
                </el-table-column>
                <el-table-column prop="title" label="名称" min-width="240" show-overflow-tooltip />
                <el-table-column prop="filename" label="文件名称" min-width="240" show-overflow-tooltip />
                <el-table-column prop="operator_name" label="操作人" width="140" show-overflow-tooltip>
                    <template #default="{ row }">
                        <span class="text-tertiary">{{ row.operator_name || "-" }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="module" label="模块" width="150">
                    <template #default="{ row }">
                        <el-tag class="module-tag" size="small" effect="plain">
                            {{ moduleLabel(row.module) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="110" align="center">
                    <template #default="{ row }">
                        <el-tag :type="statusTagType(row.status)" size="small">
                            {{ statusLabel(row.status) }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="file_size" label="文件大小" width="110" align="right">
                    <template #default="{ row }">
                        <span class="text-tertiary">{{ formatBytes(row.file_size) }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="170">
                    <template #default="{ row }">
                        <span class="time-cell">{{ formatDateTime(row.created_at) }}</span>
                    </template>
                </el-table-column>
                <el-table-column prop="finished_at" label="完成时间" width="170">
                    <template #default="{ row }">
                        <span class="time-cell">{{ row.finished_at ? formatDateTime(row.finished_at) : "-" }}</span>
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="150" fixed="right" align="center" class-name="download-action-column">
                    <template #default="{ row }">
                        <div class="task-action-group">
                            <el-button link type="primary" @click="openDetail(row)">
                                查看
                            </el-button>
                            <el-button
                                v-if="row.status === 'success'"
                                link
                                type="primary"
                                :loading="downloadingId === row.id"
                                @click="handleDownload(row)"
                            >
                                <el-icon><Download /></el-icon>
                                下载
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
                    :page-sizes="[20, 50, 100]"
                    layout="total, sizes, prev, pager, next, jumper"
                    background
                    @size-change="fetchData"
                    @current-change="fetchData"
                />
            </div>
        </el-card>

        <el-drawer
            v-model="detailDrawerVisible"
            title="任务详情"
            size="520px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
        >
            <div v-if="selectedJob" class="detail-panel">
                <section class="detail-hero-card">
                    <div class="detail-hero-main">
                        <span class="detail-kicker">任务 #{{ selectedJob.id }}</span>
                        <h3>{{ selectedJob.title }}</h3>
                        <p>{{ selectedJob.filename }}</p>
                        <div class="detail-badge-row">
                            <el-tag size="small" effect="plain" round>{{ moduleLabel(selectedJob.module) }}</el-tag>
                            <el-tag :type="statusTagType(selectedJob.status)" size="small">
                                {{ statusLabel(selectedJob.status) }}
                            </el-tag>
                        </div>
                    </div>
                    <div class="detail-result-card">
                        <span>处理结果</span>
                        <div class="result-stack result-stack--detail">
                            <span class="result-line">
                                <em>状态</em>
                                <strong>{{ statusLabel(selectedJob.status) }}</strong>
                            </span>
                            <span class="result-line">
                                <em>行数</em>
                                <strong>{{ selectedJob.row_count ? formatCount(selectedJob.row_count) : "-" }}</strong>
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
                            <span class="detail-label">任务名称</span>
                            <strong>{{ selectedJob.title }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">所属模块</span>
                            <strong>{{ moduleLabel(selectedJob.module) }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">文件大小</span>
                            <strong>{{ formatBytes(selectedJob.file_size) }}</strong>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">结果行数</span>
                            <strong>{{ selectedJob.row_count ? `${formatCount(selectedJob.row_count)} 行` : "-" }}</strong>
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
                                <strong>{{ formatDateTime(selectedJob.created_at) }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">开始时间</span>
                                <strong>{{ selectedJob.started_at ? formatDateTime(selectedJob.started_at) : "-" }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">完成时间</span>
                                <strong>{{ selectedJob.finished_at ? formatDateTime(selectedJob.finished_at) : "-" }}</strong>
                            </div>
                        </div>
                        <div class="detail-time-item">
                            <span class="detail-dot"></span>
                            <div>
                                <span class="detail-label">过期时间</span>
                                <strong>{{ selectedJob.expires_at ? formatDateTime(selectedJob.expires_at) : "-" }}</strong>
                            </div>
                        </div>
                    </div>
                </section>

                <section v-if="selectedJob.error_message" class="detail-card detail-card--danger">
                    <div class="detail-card-header">
                        <span>失败原因</span>
                    </div>
                    <p class="detail-error">{{ selectedJob.error_message }}</p>
                </section>

                <div class="detail-footer">
                    <el-button
                        v-if="selectedJob.status === 'success'"
                        type="primary"
                        :loading="downloadingId === selectedJob.id"
                        @click="handleDownload(selectedJob)"
                    >
                        <el-icon><Download /></el-icon>
                        下载文件
                    </el-button>
                </div>
            </div>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "DownloadCenter" });

import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Download, Loading, Refresh } from "@element-plus/icons-vue";
import {
    downloadExportJobFile,
    listExportJobs,
    type ExportJob,
    type ExportJobStatus,
} from "@/api/exportJob";
import { formatDateTime } from "@/utils/format";

const loading = ref(false);
const downloadingId = ref<number | null>(null);
const tableData = ref<ExportJob[]>([]);
const detailDrawerVisible = ref(false);
const selectedJob = ref<ExportJob | null>(null);
const pagination = reactive({ page: 1, pageSize: 20, total: 0 });
const searchForm = reactive({
    status: "" as ExportJobStatus | "",
    module: "",
});
let refreshTimer: number | undefined;

const activeJobCount = computed(() =>
    tableData.value.filter((job) => ["queued", "running"].includes(job.status)).length,
);
const hasActiveJobs = computed(() => activeJobCount.value > 0);

const tableSummary = computed(() => {
    if (hasActiveJobs.value) return `${activeJobCount.value} 个任务生成中`;
    return pagination.total > 0 ? `共 ${pagination.total} 个任务` : "暂无任务";
});

function moduleLabel(module: string) {
    return {
        summary: "汇总",
        transaction_accounting: "资金科目核算",
        bic_accounting: "BIC对账",
    }[module] || module;
}

function statusLabel(status: ExportJobStatus) {
    return {
        queued: "排队中",
        running: "生成中",
        success: "可下载",
        failed: "失败",
        expired: "已过期",
    }[status] || status;
}

function statusTagType(status: ExportJobStatus) {
    if (status === "success") return "success";
    if (status === "failed" || status === "expired") return "danger";
    if (status === "running") return "warning";
    return "info";
}

function formatBytes(value?: number | null) {
    if (!value) return "-";
    if (value >= 1024 * 1024 * 1024) return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
    if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} MB`;
    if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
    return `${value} B`;
}

function formatCount(value?: number | null) {
    return Number(value || 0).toLocaleString("zh-CN");
}

function rowIndex(index: number) {
    return (pagination.page - 1) * pagination.pageSize + index + 1;
}

function openDetail(row: ExportJob) {
    selectedJob.value = row;
    detailDrawerVisible.value = true;
}

async function fetchData() {
    if (loading.value) return;

    loading.value = true;
    try {
        const res = await listExportJobs({
            page: pagination.page,
            page_size: pagination.pageSize,
            status: searchForm.status || undefined,
            module: searchForm.module || undefined,
        });
        tableData.value = res.items;
        pagination.total = res.total;
    } catch {
        ElMessage.error("获取下载任务失败");
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.status = "";
    searchForm.module = "";
    handleSearch();
}

async function handleDownload(row: ExportJob) {
    downloadingId.value = row.id;
    try {
        await downloadExportJobFile(row.id);
        ElMessage.success("下载已开始");
    } catch {
        ElMessage.error("下载失败，请稍后重试");
    } finally {
        downloadingId.value = null;
    }
}

onMounted(() => {
    fetchData();
    refreshTimer = window.setInterval(() => {
        if (tableData.value.some((job) => ["queued", "running"].includes(job.status))) {
            fetchData();
        }
    }, 6000);
});

onUnmounted(() => {
    if (refreshTimer) window.clearInterval(refreshTimer);
});
</script>

<style scoped lang="scss">
.download-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 14px;
}

.summary-title-group {
    display: flex;
    align-items: baseline;
    gap: 12px;
    min-width: 0;
}

.card-header-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
}

.summary-count {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
}

.card-header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}

.download-table {
    :deep(.el-table__cell) {
        padding: 0;
    }
}

.time-cell {
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    font-weight: 400;
    color: var(--text-primary);
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

    p {
        margin: 0;
        color: var(--text-tertiary);
        font-size: 12px;
        line-height: 1.6;
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

.detail-footer {
    display: flex;
    justify-content: flex-end;
}

.module-tag {
    max-width: 100%;
    font-weight: 500;
}

:deep(.download-action-column .cell) {
    padding-left: 8px;
    padding-right: 8px;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
    padding-top: 18px;
}

@media (max-width: 768px) {
    .download-page {
        gap: 14px;
    }

    .card-header {
        align-items: flex-start;
        flex-direction: column;
    }

    .summary-title-group {
        align-items: flex-start;
        flex-direction: column;
        gap: 4px;
    }

    .card-header-actions {
        width: 100%;
        justify-content: space-between;
        flex-wrap: wrap;
    }

    .detail-hero-card,
    .detail-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 640px) {
    .job-title-line,
    .job-meta-line {
        align-items: flex-start;
        flex-direction: column;
        gap: 4px;
    }

    .job-meta-line span + span::before {
        content: "";
        margin-right: 0;
    }

    .pagination-area {
        justify-content: center;
    }
}
</style>
