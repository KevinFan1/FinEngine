<template>
    <div class="page-container transaction-page">
        <div class="transaction-upload-shell">
            <section class="upload-rule-board" aria-label="文件命名规则和平台示例">
                <div class="rule-board-main">
                    <div class="rule-heading">
                        <div>
                            <span class="section-kicker">NAMING RULE</span>
                            <h2>文件命名规则</h2>
                        </div>
                        <p>先按规则命名，系统会识别核算年月、动账类型和店铺；当前仅支持抖音动账。</p>
                    </div>
                    <div class="rule-code-line" aria-label="标准文件命名格式">
                        <span class="rule-token rule-token--date">YY年MM月</span>
                        <span class="rule-separator">_</span>
                        <span class="rule-token rule-token--type">动账</span>
                        <span class="rule-separator">_</span>
                        <span class="rule-token rule-token--shop">店铺名称</span>
                        <span class="rule-extension">.xlsx / .xls / .csv</span>
                    </div>
                    <div class="rule-meta">
                        <p class="rule-example">
                            示例：<code>26年02月_动账_抖音旗舰店.xlsx</code>
                        </p>
                        <div class="rule-hint-list">
                            <span>核算年月支持 26年 或 2026年</span>
                            <span>月份支持 2月 或 02月</span>
                            <span>后续平台接入后沿用此入口</span>
                        </div>
                    </div>
                </div>

                <div class="rule-platforms" aria-label="平台示例参考">
                    <div class="reference-heading rule-platforms-heading">
                        <div>
                            <span class="section-kicker">REFERENCE</span>
                            <h3>已接入平台与支持类型</h3>
                        </div>
                        <el-icon><InfoFilled /></el-icon>
                    </div>
                    <div class="platform-card-list">
                        <div class="platform-card">
                            <div class="platform-card-line">
                                <PlatformBadge platform="douyin" show-mark size="default" />
                                <div class="type-list">
                                    <FileTypeBadge type="动账" />
                                </div>
                            </div>
                            <p class="platform-example">26年02月_动账_抖音旗舰店.xlsx</p>
                        </div>
                    </div>
                </div>
            </section>

            <div class="upload-main-grid">
                <section class="upload-workspace" aria-label="上传操作区">
                    <section class="upload-steps" aria-label="上传流程">
                        <div class="upload-step is-active">
                            <strong>1</strong>
                            <span>选择文件</span>
                        </div>
                        <div
                            class="upload-step"
                            :class="{ 'is-active': fileItems.length > 0 || isReadingHeaders }"
                        >
                            <strong>2</strong>
                            <span>检查表头</span>
                        </div>
                        <div
                            class="upload-step"
                            :class="{ 'is-active': canUpload || isUploading }"
                        >
                            <strong>3</strong>
                            <span>提交任务</span>
                        </div>
                    </section>

                    <el-card
                        v-if="userStore.isSuperAdmin"
                        shadow="never"
                        class="target-org-card"
                    >
                        <el-form inline>
                            <el-form-item label="上传到组织">
                                <el-select
                                    v-model="targetOrgId"
                                    placeholder="请选择组织"
                                    filterable
                                    style="width: 260px"
                                    :loading="orgLoading"
                                >
                                    <el-option
                                        v-for="org in orgOptions"
                                        :key="org.id"
                                        :label="org.name"
                                        :value="org.id"
                                    />
                                </el-select>
                            </el-form-item>
                        </el-form>
                    </el-card>

                    <el-card shadow="never" class="upload-card">
                        <div class="operation-heading">
                            <div>
                                <span class="section-kicker">STEP 01</span>
                                <h3>选择并预检动账文件</h3>
                            </div>
                            <span class="file-counter">{{ fileItems.length }} 个文件</span>
                        </div>

                        <div
                            class="drop-zone"
                            :class="{
                                'drop-zone--active': isDragging,
                                'drop-zone--scanning': isReadingHeaders,
                            }"
                            @dragover.prevent="isDragging = true"
                            @dragleave.prevent="isDragging = false"
                            @drop.prevent="handleDrop"
                            @click="triggerFileInput"
                        >
                            <input
                                ref="fileInputRef"
                                type="file"
                                multiple
                                accept=".xlsx,.xlsm,.xls,.csv"
                                style="display: none"
                                @change="handleFileInputChange"
                            />
                            <div v-if="isReadingHeaders" class="scan-line" aria-hidden="true"></div>
                            <div class="drop-zone-content">
                                <div class="upload-illustration" aria-hidden="true">
                                    <span class="file-layer file-layer--back"></span>
                                    <span class="file-layer file-layer--front">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                    </span>
                                    <el-icon><Upload /></el-icon>
                                </div>
                                <p class="drop-zone-text">
                                    {{ isReadingHeaders ? "正在扫描文件结构..." : "拖拽文件到此处" }}
                                    <em v-if="!isReadingHeaders">点击选择</em>
                                </p>
                                <p class="drop-zone-hint">
                                    支持 .xlsx / .xlsm / .xls / .csv；大文件建议优先使用 .csv，预检和解析更快；单文件最大 1024MB
                                </p>
                            </div>
                        </div>
                    </el-card>

                    <el-card
                        v-if="fileItems.length > 0 || isReadingHeaders"
                        shadow="never"
                        class="file-list-card"
                    >
                        <template #header>
                            <div class="card-header">
                                <div class="card-header-main">
                                    <div>
                                        <span class="section-kicker">STEP 02</span>
                                        <span class="card-header-title">确认识别结果</span>
                                    </div>
                                    <span
                                        v-if="queuePanelVisible"
                                        class="queue-state"
                                        :class="{ 'queue-state--running': isUploading }"
                                    >
                                        {{ isUploading ? "上传中" : "等待操作" }}
                                    </span>
                                </div>
                                <div class="card-header-actions">
                                    <el-button
                                        type="primary"
                                        :loading="isUploading"
                                        :disabled="!canUpload"
                                        @click="startUpload"
                                    >
                                        <el-icon><Upload /></el-icon>
                                        {{ isUploading ? "上传中..." : "开始上传" }}
                                    </el-button>
                                    <el-button
                                        :disabled="isUploading || fileItems.length === 0"
                                        @click="clearAll"
                                    >
                                        <el-icon><Delete /></el-icon>
                                        清空
                                    </el-button>
                                    <el-button
                                        v-if="failedReadyItems.length > 0"
                                        :disabled="isUploading"
                                        @click="retryFailedFiles"
                                    >
                                        重试失败
                                    </el-button>
                                    <el-button
                                        size="small"
                                        :disabled="isUploading || uploadStats.success === 0"
                                        @click="clearSuccessFiles"
                                    >
                                        清空成功
                                    </el-button>
                                    <el-button
                                        size="small"
                                        :disabled="failedItems.length === 0"
                                        @click="exportFailedList"
                                    >
                                        导出失败
                                    </el-button>
                                </div>
                            </div>
                            <div v-if="queuePanelVisible" class="queue-inline-panel">
                                <div class="queue-stat-grid">
                                    <div class="queue-stat">
                                        <span>总文件</span>
                                        <strong>{{ uploadStats.total }}</strong>
                                    </div>
                                    <div class="queue-stat">
                                        <span>可上传</span>
                                        <strong>{{ uploadStats.ready }}</strong>
                                    </div>
                                    <div class="queue-stat">
                                        <span>上传中</span>
                                        <strong>{{ uploadStats.uploading }}</strong>
                                    </div>
                                    <div class="queue-stat queue-stat--success">
                                        <span>成功</span>
                                        <strong>{{ uploadStats.success }}</strong>
                                    </div>
                                    <div class="queue-stat queue-stat--error">
                                        <span>失败</span>
                                        <strong>{{ uploadStats.error }}</strong>
                                    </div>
                                </div>
                                <el-progress :percentage="uploadOverallPercent" :stroke-width="10" />
                                <div class="queue-summary">{{ queueSummaryText }}</div>
                            </div>
                        </template>

                        <div
                            v-if="isReadingHeaders && fileItems.length === 0"
                            class="file-skeleton-list"
                        >
                            <div
                                v-for="row in skeletonRows"
                                :key="row"
                                class="file-skeleton-row"
                            >
                                <span class="skeleton-block skeleton-name"></span>
                                <span class="skeleton-block skeleton-short"></span>
                                <span class="skeleton-block skeleton-medium"></span>
                                <span class="skeleton-block skeleton-badge"></span>
                            </div>
                        </div>

                        <el-table
                            v-else
                            :data="fileItems"
                            stripe
                            style="width: 100%"
                            class="summary-table file-table"
                        >
                            <el-table-column type="index" label="#" width="50" align="center" />
                            <el-table-column
                                prop="name"
                                label="文件名"
                                min-width="220"
                                show-overflow-tooltip
                            />
                            <el-table-column label="核算年月" width="100">
                                <template #default="{ row }">
                                    <el-tag
                                        v-if="row.meta"
                                        type="info"
                                        size="small"
                                        class="soft-badge"
                                    >
                                        {{ row.meta.year }}-{{ String(row.meta.month).padStart(2, "0") }}
                                    </el-tag>
                                    <span v-else class="text-error">解析失败</span>
                                </template>
                            </el-table-column>
                            <el-table-column
                                label="识别店铺名称"
                                min-width="170"
                                show-overflow-tooltip
                            >
                                <template #default="{ row }">
                                    <span v-if="row.meta?.shop" class="shop-cell">
                                        <el-icon><Shop /></el-icon>
                                        <strong>{{ row.meta.shop }}</strong>
                                    </span>
                                    <span v-else class="text-error">解析失败</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="性质" width="90">
                                <template #default="{ row }">
                                    <FileTypeBadge v-if="row.meta" type="动账" />
                                    <span v-else class="text-error">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="平台识别" width="130">
                                <template #default="{ row }">
                                    <el-tooltip
                                        v-if="row.headerMatch"
                                        :content="row.headerMatch.message"
                                        placement="top"
                                    >
                                        <PlatformBadge
                                            v-if="row.headerMatch.status === 'matched'"
                                            platform="douyin"
                                        />
                                        <el-tag
                                            v-else
                                            :type="headerMatchTagType(row.headerMatch.status)"
                                            size="small"
                                            class="soft-badge"
                                        >
                                            {{ platformMatchLabel(row) }}
                                        </el-tag>
                                    </el-tooltip>
                                    <span v-else class="text-tertiary">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="检查结果" min-width="260" show-overflow-tooltip>
                                <template #default="{ row }">
                                    <span
                                        v-if="row.headerMatch.status === 'matched'"
                                        class="check-pill check-pill--success"
                                    >
                                        <span class="check-dot"></span>
                                        {{ validationMessage(row) }}
                                    </span>
                                    <span v-else class="check-pill check-pill--error">
                                        <span class="check-dot"></span>
                                        {{ validationMessage(row) }}
                                    </span>
                                </template>
                            </el-table-column>
                            <el-table-column label="状态" width="120" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.status === 'pending'" class="status-pill">等待上传</span>
                                    <span
                                        v-else-if="row.status === 'uploading'"
                                        class="status-pill status-pill--warning"
                                    >
                                        上传中
                                    </span>
                                    <span
                                        v-else-if="row.status === 'success'"
                                        class="status-pill status-pill--success"
                                    >
                                        已完成
                                    </span>
                                    <el-tooltip
                                        v-else
                                        :content="row.error || '上传失败'"
                                        placement="top"
                                    >
                                        <span class="status-pill status-pill--error">失败</span>
                                    </el-tooltip>
                                </template>
                            </el-table-column>
                            <el-table-column label="进度" width="160">
                                <template #default="{ row }">
                                    <el-progress
                                        v-if="row.status === 'uploading' || row.status === 'success'"
                                        :percentage="row.progress"
                                        :status="row.status === 'success' ? 'success' : ''"
                                        :stroke-width="8"
                                    />
                                    <el-tooltip
                                        v-else-if="row.status === 'error'"
                                        :content="row.error || '上传失败'"
                                        placement="top"
                                    >
                                        <span class="text-error">查看原因</span>
                                    </el-tooltip>
                                    <span v-else class="text-tertiary">-</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="120" align="center">
                                <template #default="{ row, $index }">
                                    <el-button
                                        v-if="row.status === 'error'"
                                        type="primary"
                                        link
                                        :disabled="isUploading || !isFileReadyForUpload(row)"
                                        @click="retryFile(row)"
                                    >
                                        重试
                                    </el-button>
                                    <el-button
                                        type="danger"
                                        link
                                        :disabled="isUploading"
                                        @click="removeFile($index)"
                                    >
                                        移除
                                    </el-button>
                                </template>
                            </el-table-column>

                            <template #empty>
                                <div class="file-empty-state">
                                    <div class="empty-illustration" aria-hidden="true">
                                        <span></span>
                                    </div>
                                    <p>等待选择文件</p>
                                </div>
                            </template>
                        </el-table>
                    </el-card>
                </section>

                <aside class="reference-panel" aria-label="文件名辅助生成">
                    <div class="reference-heading">
                        <div>
                            <span class="section-kicker">HELPER</span>
                            <h3>辅助生成</h3>
                        </div>
                        <el-icon><InfoFilled /></el-icon>
                    </div>

                    <section class="naming-rule-panel" aria-label="文件名生成器">
                        <div class="naming-assistant">
                            <div class="naming-fields">
                                <label class="naming-field">
                                    <span>核算年月</span>
                                    <el-date-picker
                                        v-model="namingMonth"
                                        type="month"
                                        value-format="YYYY-MM"
                                        format="YYYY年MM月"
                                        placeholder="选择核算年月"
                                        :clearable="false"
                                    />
                                </label>
                                <label class="naming-field">
                                    <span>性质</span>
                                    <el-select v-model="namingType" disabled>
                                        <el-option label="动账" value="动账">
                                            <FileTypeBadge type="动账" />
                                        </el-option>
                                    </el-select>
                                </label>
                                <label class="naming-field">
                                    <span>店铺名称</span>
                                    <el-select
                                        v-model="namingShopName"
                                        placeholder="选择或输入店铺名称"
                                        clearable
                                        filterable
                                        allow-create
                                        default-first-option
                                        reserve-keyword
                                        :loading="shopLoading"
                                        @visible-change="handleShopSelectVisibleChange"
                                        @clear="clearNamingShopName"
                                        @change="normalizeNamingShopName"
                                    >
                                        <el-option
                                            v-for="shop in shopOptions"
                                            :key="shop.id"
                                            :label="shop.shop_name"
                                            :value="shop.shop_name"
                                        >
                                            <div class="shop-option">
                                                <ShopBadge
                                                    :label="shop.shop_name"
                                                    :color="shop.shop_color"
                                                    size="compact"
                                                />
                                                <small>{{ shop.platform_name }}</small>
                                            </div>
                                        </el-option>
                                    </el-select>
                                </label>
                            </div>

                            <button
                                type="button"
                                class="generated-name-button"
                                :class="{ 'generated-name-button--ready': canCopyGeneratedName }"
                                :disabled="!canCopyGeneratedName"
                                @click="copyGeneratedFileName"
                            >
                                <strong>{{ generatedFileName || "生成的文件名会显示在这里" }}</strong>
                                <el-icon><CopyDocument /></el-icon>
                            </button>
                        </div>
                    </section>

                    <div class="check-note">
                        <span class="check-note-dot"></span>
                        <span>系统只读取文件开头前 20 行匹配抖音动账表头；表头顺序不同或多余列不影响识别。</span>
                    </div>
                </aside>
            </div>
        </div>

        <el-dialog
            v-model="uploadCompleteDialogVisible"
            title="上传完成"
            width="420px"
            append-to-body
            destroy-on-close
            :close-on-click-modal="false"
            :close-on-press-escape="false"
        >
            <div class="upload-complete-dialog">
                <el-icon class="upload-complete-icon"><CircleCheckFilled /></el-icon>
                <div>
                    <p class="upload-complete-title">成功上传 {{ uploadCompleteCount }} 个文件</p>
                    <p class="upload-complete-desc">
                        系统已创建动账资金核算任务，可以继续上传或前往任务列表查看进度。
                    </p>
                </div>
            </div>
            <template #footer>
                <el-button @click="handleContinueUpload">继续上传</el-button>
                <el-button type="primary" @click="goTaskList">查看任务列表</el-button>
            </template>
        </el-dialog>

        <div
            v-if="isUploading"
            class="upload-blocking-mask"
            role="alert"
            aria-live="assertive"
            aria-busy="true"
        >
            <div class="upload-blocking-card">
                <div class="upload-blocking-badge">上传进行中</div>
                <h3>请勿关闭页面或刷新浏览器</h3>
                <p>文件正在上传并创建动账资金核算任务，中途中断可能导致本次批量上传不完整。</p>
                <el-progress :percentage="uploadOverallPercent" :stroke-width="10" status="success" />
                <div class="upload-blocking-meta">
                    <span>当前文件</span>
                    <strong>{{ uploadingFileName || "正在准备上传..." }}</strong>
                </div>
                <div class="upload-blocking-meta">
                    <span>完成进度</span>
                    <strong>{{ uploadDialogDone }} / {{ uploadDialogTotal || readyUploadItems.length }}</strong>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionUploadCenter" });

import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import {
    CircleCheckFilled,
    CopyDocument,
    Delete,
    InfoFilled,
    Shop,
    Upload,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { getFileSpecs, type FileSpec } from "@/api/file_spec";
import { getOrganizationList, type Organization } from "@/api/organization";
import { getShopList, type Shop as ShopRecord } from "@/api/shop";
import {
    callbackTransactionUpload,
    initTransactionUpload,
    type TransactionOssCredential,
} from "@/api/transactionAccounting";
import PlatformBadge from "@/components/PlatformBadge.vue";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { useUserStore } from "@/stores/user";
import { decodeCsvBuffer } from "@/utils/csvEncoding";
import { buildUploadOssKey } from "@/utils/ossPath";

interface ParsedTransactionFileName {
    year: number;
    month: number;
    type: "动账";
    shop: string;
}

interface HeaderRowCandidate {
    headers: string[];
    rowIndex: number;
}

type HeaderMatchStatus =
    | "matched"
    | "mismatch"
    | "no_spec"
    | "read_failed"
    | "filename_failed";

interface HeaderMatchInfo {
    status: HeaderMatchStatus;
    message: string;
    matchedCount: number;
    expectedCount: number;
    headerRowIndex: number | null;
}

interface HeaderMatchResult {
    spec: FileSpec | null;
    headers: string[];
    info: HeaderMatchInfo;
}

interface FileItem {
    file: File;
    name: string;
    meta: ParsedTransactionFileName | null;
    matchedRule: FileSpec | null;
    headers: string[];
    headerRowIndex: number | null;
    headerMatch: HeaderMatchInfo;
    status: "pending" | "uploading" | "success" | "error";
    progress: number;
    error?: string;
    taskId?: number;
}

const fileInputRef = ref<HTMLInputElement>();
const isDragging = ref(false);
const isUploading = ref(false);
const isReadingHeaders = ref(false);
const fileItems = ref<FileItem[]>([]);
const fileSpecs = ref<FileSpec[]>([]);
const skeletonRows = [1, 2, 3];
const userStore = useUserStore();
const router = useRouter();
const orgLoading = ref(false);
const orgOptions = ref<Organization[]>([]);
const targetOrgId = ref<number | undefined>(undefined);
const shopLoading = ref(false);
const shopOptions = ref<ShopRecord[]>([]);
const namingMonth = ref("");
const namingType = ref<"动账">("动账");
const namingShopName = ref("");
const uploadCompleteDialogVisible = ref(false);
const uploadCompleteCount = ref(0);
const uploadingFileName = ref("");
const uploadDialogTotal = ref(0);
const uploadDialogDone = ref(0);
let xlsxModulePromise: Promise<typeof import("xlsx")> | null = null;
let ossModulePromise: Promise<typeof import("ali-oss")> | null = null;

const SHOP_PAGE_SIZE = 100;
const HEADER_SCAN_ROW_LIMIT = 20;
const CSV_HEADER_SCAN_BYTES = 256 * 1024;
const OSS_REQUEST_TIMEOUT = 2 * 60 * 1000;
const OSS_MULTIPART_PART_SIZE = 1024 * 1024;
const OSS_MULTIPART_PARALLEL = 2;
const UPLOAD_CONCURRENCY = 3;

const generatedFileName = computed(() => {
    const monthText = formatNamingMonth(namingMonth.value);
    const shopText = sanitizeFileNamePart(namingShopName.value);
    if (!monthText || !shopText) return "";
    return `${monthText}_动账_${shopText}.xlsx`;
});

const canCopyGeneratedName = computed(() => Boolean(generatedFileName.value));
const uploadableItems = computed(() =>
    fileItems.value.filter((item) => item.status !== "success"),
);
const readyUploadItems = computed(() =>
    uploadableItems.value.filter(isFileReadyForUpload),
);
const failedItems = computed(() =>
    fileItems.value.filter((item) => item.status === "error"),
);
const failedReadyItems = computed(() =>
    failedItems.value.filter(isFileReadyForUpload),
);
const queuePanelVisible = computed(
    () => fileItems.value.length > 0 || uploadDialogTotal.value > 0,
);
const uploadOverallPercent = computed(() => {
    const total = uploadDialogTotal.value || readyUploadItems.value.length;
    if (total === 0) return 0;
    const currentProgress = fileItems.value
        .filter((item) => item.status === "uploading")
        .reduce(
            (sum, item) =>
                sum + Math.max(0, Math.min(item.progress, 100)) / 100,
            0,
        );
    return Math.min(
        100,
        Math.round(((uploadDialogDone.value + currentProgress) / total) * 100),
    );
});
const uploadStats = computed(() => ({
    total: fileItems.value.length,
    ready: readyUploadItems.value.length,
    uploading: fileItems.value.filter((item) => item.status === "uploading").length,
    success: fileItems.value.filter((item) => item.status === "success").length,
    error: failedItems.value.length,
}));
const queueSummaryText = computed(() => {
    if (isUploading.value) {
        return `正在上传 ${uploadStats.value.uploading} 个文件，并发 3 个，失败不会阻塞后续文件。`;
    }
    if (uploadStats.value.error > 0) {
        return `已完成本轮上传，${uploadStats.value.error} 个文件失败，可只重试失败文件。`;
    }
    if (uploadStats.value.success > 0) {
        return `已成功上传 ${uploadStats.value.success} 个文件。`;
    }
    return "通过预检后，文件会进入上传队列并创建动账资金核算任务。";
});
const canUpload = computed(() => {
    return (
        readyUploadItems.value.length > 0 &&
        (!userStore.isSuperAdmin || Boolean(targetOrgId.value)) &&
        !isUploading.value
    );
});

loadFileSpecs();
loadOrgOptions();

function parseTransactionUploadFileName(filename: string): ParsedTransactionFileName | null {
    const nameWithoutExt = filename.replace(/\.(xlsx|xlsm|xls|csv)$/i, "");
    const match = nameWithoutExt.match(/^(\d{2}|\d{4})年(\d{1,2})月[ _](动账)[ _](.+)$/i);
    if (!match) return null;
    const year = match[1].length === 2 ? 2000 + Number(match[1]) : Number(match[1]);
    const month = Number(match[2]);
    const shop = match[4].trim();
    if (!shop || month < 1 || month > 12) return null;
    return { year, month, type: "动账", shop };
}

function formatNamingMonth(month: string): string {
    const match = month.match(/^(\d{4})-(\d{2})$/);
    if (!match) return "";
    return `${match[1].slice(-2)}年${match[2]}月`;
}

function sanitizeFileNamePart(value: string): string {
    return value
        .trim()
        .replace(/[\\/:*?"<>|]/g, "-")
        .replace(/\s+/g, "");
}

function normalizeNamingShopName() {
    namingShopName.value = namingShopName.value.trim();
}

function clearNamingShopName() {
    namingShopName.value = "";
}

async function fetchShopOptions() {
    if (shopLoading.value || shopOptions.value.length > 0) return;
    shopLoading.value = true;
    try {
        const allShops: ShopRecord[] = [];
        let page = 1;
        let total = 0;
        do {
            const res = await getShopList({ page, page_size: SHOP_PAGE_SIZE });
            const items = res.items || [];
            total = res.total || 0;
            allShops.push(...items);
            if (items.length < SHOP_PAGE_SIZE) break;
            page += 1;
        } while (allShops.length < total);
        shopOptions.value = allShops;
    } catch {
        // Error handled by interceptor; custom shop names still work.
    } finally {
        shopLoading.value = false;
    }
}

async function handleShopSelectVisibleChange(visible: boolean) {
    if (visible) await fetchShopOptions();
}

function fallbackCopyText(text: string): boolean {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    document.body.removeChild(textarea);
    return copied;
}

async function copyGeneratedFileName() {
    if (!generatedFileName.value) {
        ElMessage.warning("请先填写核算年月和店铺名称");
        return;
    }
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(generatedFileName.value);
        } else if (!fallbackCopyText(generatedFileName.value)) {
            throw new Error("fallback copy failed");
        }
        ElMessage.success("文件名已复制");
    } catch {
        if (fallbackCopyText(generatedFileName.value)) {
            ElMessage.success("文件名已复制");
            return;
        }
        ElMessage.error("复制失败，请手动复制");
    }
}

function validationMessage(row: FileItem): string {
    if (!row.meta) {
        return "文件名不符合规则：请使用 26年02月_动账_店铺名称";
    }
    if (!row.meta.shop) {
        return "文件名缺少店铺名称";
    }
    if (row.headerMatch.status === "matched") {
        return `检查通过：${row.headerMatch.message}`;
    }
    return row.headerMatch.message;
}

async function loadFileSpecs() {
    try {
        fileSpecs.value = await getFileSpecs({
            platform_code: "douyin",
            type_code: "动账",
        });
    } catch {
        // Silently fail; queue row will show no spec.
    }
}

async function loadOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    orgLoading.value = true;
    try {
        const res = await getOrganizationList({ page: 1, page_size: 100 });
        orgOptions.value = (res.items || []).filter(
            (org) => org.status === "1" || org.status === 1,
        );
        if (!targetOrgId.value && orgOptions.value.length === 1) {
            targetOrgId.value = orgOptions.value[0].id;
        }
    } catch {
        // Error handled by interceptor
    } finally {
        orgLoading.value = false;
    }
}

async function ensureFileSpecsLoaded() {
    if (fileSpecs.value.length > 0) return;
    await loadFileSpecs();
}

function triggerFileInput() {
    if (isUploading.value) return;
    fileInputRef.value?.click();
}

function handleFileInputChange(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files) {
        processFiles(Array.from(input.files));
        input.value = "";
    }
}

function handleDrop(e: DragEvent) {
    isDragging.value = false;
    if (e.dataTransfer?.files) {
        processFiles(Array.from(e.dataTransfer.files));
    }
}

async function processFiles(files: File[]) {
    if (isUploading.value) {
        ElMessage.warning("文件正在上传中，请等待完成后再选择新文件");
        return;
    }
    if (files.length === 0) return;

    uploadCompleteDialogVisible.value = false;
    await ensureFileSpecsLoaded();
    isReadingHeaders.value = true;

    try {
        for (const file of files) {
            if (!file.name.match(/\.(xlsx|xlsm|xls|csv)$/i)) {
                ElMessage.warning(`文件 ${file.name} 不是 Excel/CSV 文件，已跳过`);
                continue;
            }
            if (fileItems.value.some((item) => item.name === file.name)) {
                ElMessage.warning(`文件 ${file.name} 已存在，已跳过`);
                continue;
            }

            const meta = parseTransactionUploadFileName(file.name);
            let headers: string[] = [];
            let matchedRule: FileSpec | null = null;
            let headerMatch: HeaderMatchInfo = {
                status: "filename_failed",
                message: "文件名解析失败，格式示例：26年02月_动账_店铺名.xlsx",
                matchedCount: 0,
                expectedCount: 0,
                headerRowIndex: null,
            };

            if (meta && fileSpecs.value.length > 0) {
                try {
                    const headerRows = await readTabularHeaderRows(file);
                    const matchResult = matchPlatformByHeaderRows(headerRows);
                    matchedRule = matchResult.spec;
                    headers = matchResult.headers;
                    headerMatch = matchResult.info;
                } catch (err: any) {
                    headerMatch = {
                        status: "read_failed",
                        message: err?.message || "读取文件表头失败",
                        matchedCount: 0,
                        expectedCount: 0,
                        headerRowIndex: null,
                    };
                }
            } else if (meta) {
                headerMatch = {
                    status: "no_spec",
                    message: "未获取到抖音动账表头规格，无法识别平台",
                    matchedCount: 0,
                    expectedCount: 0,
                    headerRowIndex: null,
                };
            }

            fileItems.value.push({
                file,
                name: file.name,
                meta,
                matchedRule,
                headers,
                headerRowIndex: headerMatch.headerRowIndex,
                headerMatch,
                status: "pending",
                progress: 0,
            });
        }
    } finally {
        isReadingHeaders.value = false;
    }
}

async function readTabularHeaderRows(file: File): Promise<HeaderRowCandidate[]> {
    if (file.name.toLowerCase().endsWith(".csv")) {
        return readCsvHeaderRows(file);
    }
    const XLSX = await loadXlsx();
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = e.target?.result;
                if (!data) {
                    resolve([]);
                    return;
                }
                const wb = XLSX.read(data, {
                    type: "array",
                    sheetRows: HEADER_SCAN_ROW_LIMIT,
                    cellFormula: false,
                    cellHTML: false,
                    cellNF: false,
                    cellStyles: false,
                    cellText: false,
                });
                const ws = wb.Sheets[wb.SheetNames[0]];
                const rows = XLSX.utils.sheet_to_json<string[]>(ws, {
                    header: 1,
                    blankrows: true,
                    defval: "",
                    raw: false,
                });
                resolve(toHeaderRowCandidates(rows));
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = reject;
        reader.readAsArrayBuffer(file);
    });
}

async function readCsvHeaderRows(file: File): Promise<HeaderRowCandidate[]> {
    const buffer = await file
        .slice(0, Math.min(file.size, CSV_HEADER_SCAN_BYTES))
        .arrayBuffer();
    const text = decodeCsvBuffer(buffer);
    const rows = parseCsvPreviewRows(text, HEADER_SCAN_ROW_LIMIT);
    return toHeaderRowCandidates(rows);
}

function toHeaderRowCandidates(rows: unknown[][]): HeaderRowCandidate[] {
    return rows
        .slice(0, HEADER_SCAN_ROW_LIMIT)
        .map((row, index) => ({
            headers: row.map((cell) => String(cell || "").trim()),
            rowIndex: index + 1,
        }))
        .filter((row) => row.headers.some(Boolean));
}

function parseCsvPreviewRows(text: string, maxRows: number): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = "";
    let inQuotes = false;

    for (let index = 0; index < text.length && rows.length < maxRows; index += 1) {
        const char = text[index];
        const nextChar = text[index + 1];
        if (char === '"') {
            if (inQuotes && nextChar === '"') {
                cell += '"';
                index += 1;
            } else {
                inQuotes = !inQuotes;
            }
            continue;
        }
        if (char === "," && !inQuotes) {
            row.push(cell);
            cell = "";
            continue;
        }
        if ((char === "\n" || char === "\r") && !inQuotes) {
            if (char === "\r" && nextChar === "\n") index += 1;
            row.push(cell);
            rows.push(row);
            row = [];
            cell = "";
            continue;
        }
        cell += char;
    }
    if (rows.length < maxRows && (cell || row.length > 0)) {
        row.push(cell);
        rows.push(row);
    }
    return rows;
}

function loadXlsx() {
    if (!xlsxModulePromise) xlsxModulePromise = import("xlsx");
    return xlsxModulePromise;
}

function matchPlatformByHeaderRows(headerRows: HeaderRowCandidate[]): HeaderMatchResult {
    const typedCandidates = fileSpecs.value.filter(
        (spec) =>
            spec.platform_code === "douyin" &&
            spec.type_code.toLowerCase() === "动账".toLowerCase(),
    );
    if (typedCandidates.length === 0) {
        return {
            spec: null,
            info: {
                status: "no_spec",
                message: "接口未配置「抖音动账」表头规格",
                matchedCount: 0,
                expectedCount: 0,
                headerRowIndex: null,
            },
            headers: [],
        };
    }

    let bestMatched: {
        spec: FileSpec;
        headers: string[];
        matchedCount: number;
        expectedCount: number;
        headerRowIndex: number;
    } | null = null;

    for (const row of headerRows) {
        const actualHeaders = normalizeHeaders(row.headers);
        for (const spec of typedCandidates) {
            const expectedHeaders = normalizeHeaders(spec.headers || []);
            if (expectedHeaders.length === 0) continue;
            const matchedCount = countMatchedHeaders(actualHeaders, expectedHeaders);
            const requiredCount = requiredMatchCount(spec, expectedHeaders.length);
            if (matchedCount >= requiredCount) {
                if (
                    !bestMatched ||
                    matchedCount > bestMatched.matchedCount ||
                    (matchedCount === bestMatched.matchedCount &&
                        expectedHeaders.length < bestMatched.expectedCount)
                ) {
                    bestMatched = {
                        spec,
                        headers: row.headers,
                        matchedCount,
                        expectedCount: expectedHeaders.length,
                        headerRowIndex: row.rowIndex,
                    };
                }
            }
        }
    }

    if (bestMatched) {
        return {
            spec: bestMatched.spec,
            headers: bestMatched.headers,
            info: {
                status: "matched",
                message: `表头匹配 ${bestMatched.matchedCount}/${bestMatched.expectedCount} 个字段，识别平台：抖音（已忽略多余列和列顺序）`,
                matchedCount: bestMatched.matchedCount,
                expectedCount: bestMatched.expectedCount,
                headerRowIndex: bestMatched.headerRowIndex,
            },
        };
    }

    const closest = scoreClosest(typedCandidates, headerRows);
    return {
        spec: null,
        headers: closest?.headers || headerRows[0]?.headers || [],
        info: {
            status: "mismatch",
            message: closest
                ? `表头不一致，最接近「${closest.spec.name}」：匹配 ${closest.matchedCount}/${closest.expectedCount} 个字段`
                : "表头不一致，未匹配到抖音动账表头规格",
            matchedCount: closest?.matchedCount || 0,
            expectedCount: closest?.expectedCount || 0,
            headerRowIndex: closest ? closest.headerRowIndex : null,
        },
    };
}

function normalizeHeaders(headers: string[]): string[] {
    return Array.from(new Set(headers.map(canonicalHeader).filter(Boolean)));
}

function canonicalHeader(header: string): string {
    return String(header || "")
        .trim()
        .replace(/[\s　\uFEFF\u200B-\u200D]+/g, "")
        .replace(/帐/g, "账")
        .replace(/（/g, "(")
        .replace(/）/g, ")")
        .toLowerCase();
}

function countMatchedHeaders(actual: string[], expected: string[]): number {
    const actualSet = new Set(actual);
    return expected.filter((h) => actualSet.has(h)).length;
}

function requiredMatchCount(spec: FileSpec, expectedCount: number): number {
    const threshold = Number(spec.match_threshold);
    if (!Number.isFinite(threshold) || threshold <= 0) return expectedCount;
    return Math.min(expectedCount, Math.ceil(threshold));
}

function scoreClosest(candidates: FileSpec[], headerRows: HeaderRowCandidate[]) {
    let best: {
        spec: FileSpec;
        headers: string[];
        matchedCount: number;
        expectedCount: number;
        headerRowIndex: number;
    } | null = null;

    for (const row of headerRows) {
        const actualHeaders = normalizeHeaders(row.headers);
        for (const spec of candidates) {
            const expectedHeaders = normalizeHeaders(spec.headers || []);
            if (expectedHeaders.length === 0) continue;
            const matchedCount = countMatchedHeaders(actualHeaders, expectedHeaders);
            if (!best || matchedCount > best.matchedCount) {
                best = {
                    spec,
                    headers: row.headers,
                    matchedCount,
                    expectedCount: expectedHeaders.length,
                    headerRowIndex: row.rowIndex,
                };
            }
        }
    }
    return best;
}

function headerMatchTagType(status: HeaderMatchStatus): string {
    return (
        {
            matched: "success",
            mismatch: "danger",
            no_spec: "warning",
            read_failed: "danger",
            filename_failed: "danger",
        } as Record<HeaderMatchStatus, string>
    )[status];
}

function platformMatchLabel(row: FileItem): string {
    if (row.headerMatch.status === "matched") return "抖音";
    return (
        {
            matched: "已识别",
            mismatch: "表头不一致",
            no_spec: "无规格",
            read_failed: "读取失败",
            filename_failed: "解析失败",
        } as Record<HeaderMatchStatus, string>
    )[row.headerMatch.status];
}

function totalFileBytes(items: FileItem[]): number {
    return items.reduce((sum, item) => sum + item.file.size, 0);
}

function isFileReadyForUpload(item: FileItem): boolean {
    return (
        item.status !== "success" &&
        item.status !== "uploading" &&
        item.meta !== null &&
        item.matchedRule !== null &&
        item.headerMatch.status === "matched"
    );
}

function buildOssKey(sts: TransactionOssCredential, fileName: string): string {
    return buildUploadOssKey(sts.oss_key_prefix, "动账", fileName, sts.file_id);
}

function loadOss() {
    if (!ossModulePromise) ossModulePromise = import("ali-oss");
    return ossModulePromise;
}

async function createOssClient(sts: TransactionOssCredential) {
    const OSS = await loadOss();
    return new OSS.default({
        region: sts.region,
        bucket: sts.bucket,
        endpoint: sts.endpoint,
        accessKeyId: sts.access_key_id,
        accessKeySecret: sts.access_key_secret,
        stsToken: sts.security_token,
        secure: sts.endpoint.startsWith("https://"),
        timeout: OSS_REQUEST_TIMEOUT,
        retryMax: 0,
    });
}

async function uploadFileToOss(ossClient: any, ossKey: string, item: FileItem) {
    await ossClient.multipartUpload(ossKey, item.file, {
        timeout: OSS_REQUEST_TIMEOUT,
        partSize: OSS_MULTIPART_PART_SIZE,
        parallel: OSS_MULTIPART_PARALLEL,
        progress: async (percent: number) => {
            item.progress = Math.round(percent * 100);
        },
    });
}

function ossErrorMessage(err: any): string {
    if (
        err?.code === "ConnectionTimeoutError" ||
        err?.code === "ResponseTimeoutError"
    ) {
        return "文件上传超时，请重试";
    }
    return err?.message || err?.name || err?.code || "上传失败";
}

function isApiMessageShown(error: unknown): boolean {
    return Boolean(
        error &&
        typeof error === "object" &&
        (error as { __apiMessageShown?: boolean }).__apiMessageShown,
    );
}

function removeFile(index: number) {
    fileItems.value.splice(index, 1);
}

function clearAll() {
    fileItems.value = [];
    uploadDialogTotal.value = 0;
    uploadDialogDone.value = 0;
}

function clearSuccessFiles() {
    fileItems.value = fileItems.value.filter((item) => item.status !== "success");
}

function showUploadCompleteDialog(successCount: number) {
    uploadCompleteCount.value = successCount;
    uploadCompleteDialogVisible.value = true;
}

function handleContinueUpload() {
    uploadCompleteDialogVisible.value = false;
}

function goTaskList() {
    uploadCompleteDialogVisible.value = false;
    router.push("/transaction-tasks");
}

async function uploadSingleFile(item: FileItem): Promise<boolean> {
    if (!item.meta) return false;
    uploadingFileName.value = item.name;
    item.status = "uploading";
    item.progress = 0;
    item.error = undefined;
    item.taskId = undefined;

    try {
        const init = await initTransactionUpload(
            {
                original_name: item.name,
                file_size: item.file.size,
                platform_code: "douyin",
                shop_name: item.meta.shop,
                accounting_year: item.meta.year,
                accounting_month: item.meta.month,
            },
            userStore.isSuperAdmin ? targetOrgId.value : undefined,
        );
        const ossKey = buildOssKey(init.upload, item.file.name);
        const ossClient = await createOssClient(init.upload);
        await uploadFileToOss(ossClient, ossKey, item);
        const task = await callbackTransactionUpload({
            file_id: init.upload.file_id,
            oss_key: ossKey,
            file_size: item.file.size,
        });
        item.status = "success";
        item.progress = 100;
        item.taskId = task.id;
        return true;
    } catch (err: any) {
        item.status = "error";
        item.progress = 100;
        item.error = ossErrorMessage(err);
        if (
            item.error === (err?.message || err?.name || err?.code || "上传失败") &&
            isApiMessageShown(err)
        ) {
            item.error = "获取上传凭证失败，请稍后重试";
        }
        return false;
    } finally {
        uploadDialogDone.value += 1;
    }
}

async function runUploadQueue(itemsToUpload: FileItem[]) {
    if (itemsToUpload.length === 0) {
        ElMessage.warning("没有可上传的文件");
        return;
    }
    let successCount = 0;
    let failedCount = 0;
    uploadDialogTotal.value = itemsToUpload.length;
    uploadDialogDone.value = 0;
    uploadingFileName.value = "";
    isUploading.value = true;

    try {
        let cursor = 0;
        const workerCount = Math.min(UPLOAD_CONCURRENCY, itemsToUpload.length);
        const workers = Array.from({ length: workerCount }, async () => {
            while (cursor < itemsToUpload.length) {
                const item = itemsToUpload[cursor];
                cursor += 1;
                const ok = await uploadSingleFile(item);
                if (ok) successCount += 1;
                else failedCount += 1;
            }
        });
        await Promise.all(workers);

        if (successCount > 0) showUploadCompleteDialog(successCount);
        if (failedCount > 0) {
            ElMessage.warning(`本轮上传完成，${failedCount} 个文件失败，可只重试失败文件`);
        }
    } finally {
        isUploading.value = false;
        uploadingFileName.value = "";
    }
}

async function startUpload() {
    if (!canUpload.value) return;
    await runUploadQueue(readyUploadItems.value);
}

async function retryFailedFiles() {
    if (isUploading.value) return;
    await runUploadQueue(failedReadyItems.value);
}

async function retryFile(item: FileItem) {
    if (isUploading.value || !isFileReadyForUpload(item)) return;
    await runUploadQueue([item]);
}

function exportFailedList() {
    if (failedItems.value.length === 0) return;
    const rows = [
        ["文件名", "店铺", "性质", "失败原因"],
        ...failedItems.value.map((item) => [
            item.name,
            item.meta?.shop || "",
            "动账",
            item.error || item.headerMatch.message || "",
        ]),
    ];
    const csv = rows
        .map((row) =>
            row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(","),
        )
        .join("\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `资金核算上传失败清单_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
}
</script>

<style scoped lang="scss">
@use "./transaction.scss";

.transaction-upload-shell {
    display: grid;
    gap: 14px;
    align-items: start;
}

.upload-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 308px;
    gap: 14px;
    align-items: start;
    min-width: 0;
}

.upload-rule-board {
    display: grid;
    grid-template-columns: minmax(340px, 0.82fr) minmax(430px, 1.18fr);
    align-items: stretch;
    gap: 14px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);
}

.rule-board-main,
.rule-platforms {
    display: grid;
    align-content: start;
    gap: 12px;
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-color-light);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-elevated);
}

.rule-heading {
    display: grid;
    gap: 6px;
    min-width: 0;

    h2 {
        margin: 0;
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 800;
        line-height: 1.2;
    }

    p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 12px;
        line-height: 1.55;
    }
}

.rule-code-line {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px;
    max-width: 100%;
    min-height: 46px;
    padding: 8px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: 10px;
    background: var(--bg-card);
}

.rule-token,
.rule-extension,
.rule-separator {
    font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
    font-size: 12px;
    font-weight: 800;
    line-height: 1.25;
}

.rule-token {
    display: inline-flex;
    align-items: center;
    min-height: 26px;
    padding: 4px 8px;
    border: 1px solid var(--border-color-light);
    border-radius: 8px;
    background: var(--bg-card);
    color: var(--text-secondary);
}

.rule-extension,
.rule-separator {
    color: var(--text-tertiary);
}

.rule-meta {
    display: grid;
    gap: 7px;
}

.rule-example {
    margin: 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.6;

    code {
        color: var(--code-text);
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 12px;
        font-weight: 700;
    }
}

.rule-hint-list {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;

    span {
        display: inline-flex;
        align-items: center;
        min-height: 22px;
        padding: 2px 7px;
        border: 1px solid var(--surface-border);
        border-radius: 999px;
        background: var(--bg-card);
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 600;
    }
}

.upload-workspace {
    display: grid;
    gap: 10px;
    min-width: 0;
}

.upload-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    overflow: hidden;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
}

.upload-step {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    min-height: 40px;
    padding: 0 12px;
    border-right: 1px solid var(--border-color-light);
    color: var(--text-tertiary);
    font-size: 13px;
    font-weight: 600;

    &:last-child {
        border-right: 0;
    }

    strong {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border: 1px solid var(--border-light);
        border-radius: var(--radius-sm);
        color: var(--text-secondary);
        font-size: 12px;
        font-weight: 700;
    }

    span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    &.is-active {
        color: var(--text-primary);
        background: var(--primary-light-9);

        strong {
            border-color: var(--primary);
            background: var(--primary);
            color: var(--primary-contrast);
        }
    }
}

.section-kicker {
    display: block;
    margin-bottom: 4px;
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0;
}

.operation-heading,
.reference-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 17px;
        font-weight: 700;
        line-height: 1.25;
    }
}

.file-counter,
.queue-state {
    flex-shrink: 0;
    padding: 5px 10px;
    border-radius: 999px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.target-org-card,
.upload-card,
.file-list-card,
.reference-panel {
    border-radius: var(--radius-card);
}

.target-org-card :deep(.el-card__body),
.upload-card :deep(.el-card__body) {
    padding: 14px;
}

.drop-zone {
    position: relative;
    overflow: hidden;
    min-height: 190px;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius-card);
    padding: 28px 18px;
    text-align: center;
    cursor: pointer;
    background: var(--bg-card);
    transition:
        border-color 0.18s,
        background-color 0.18s,
        box-shadow 0.18s;

    &:hover,
    &--active {
        border-color: var(--input-hover-border);
        background: var(--bg-hover);
    }

    &--scanning {
        border-color: var(--input-hover-border);
        border-style: solid;
    }

    .scan-line {
        position: absolute;
        left: 5%;
        right: 5%;
        top: -18px;
        height: 18px;
        border-radius: var(--radius-sm);
        background: var(--primary-light-5);
        opacity: 0.72;
        animation: scan-line 0.5s ease-in-out infinite;
        pointer-events: none;
    }
}

.drop-zone-content {
    position: relative;
    z-index: 1;
}

.drop-zone-text {
    margin: 12px 0 5px;
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;

    em {
        margin-left: 6px;
        color: var(--text-secondary);
        font-style: normal;
        font-weight: 800;
    }
}

.drop-zone-hint {
    color: var(--text-tertiary);
    font-size: 12px;
}

.upload-illustration {
    position: relative;
    width: 82px;
    height: 76px;
    margin: 0 auto;

    .file-layer {
        position: absolute;
        display: block;
        border: 1px solid var(--border-color-light);
        border-radius: 12px;
    }

    .file-layer--back {
        left: 12px;
        top: 8px;
        width: 56px;
        height: 60px;
        background: var(--bg-elevated);
        transform: rotate(-9deg);
    }

    .file-layer--front {
        left: 22px;
        top: 0;
        width: 54px;
        height: 68px;
        padding: 16px 10px;
        background: var(--bg-card);

        span {
            display: block;
            height: 4px;
            margin-bottom: 8px;
            border-radius: 999px;
            background: var(--border-color);

            &:nth-child(2) {
                width: 72%;
            }

            &:nth-child(3) {
                width: 52%;
            }
        }
    }

    .el-icon {
        position: absolute;
        right: 2px;
        bottom: 0;
        width: 31px;
        height: 31px;
        border: 1px solid var(--border-color-light);
        border-radius: 50%;
        background: var(--bg-elevated);
        color: var(--primary);
        font-size: 18px;
    }
}

.file-list-card {
    :deep(.el-card__body) {
        padding: 0;
    }

    :deep(.el-card__header) {
        display: grid;
        gap: 12px;
    }

    .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }

    .card-header-title {
        display: block;
        color: var(--text-primary);
        font-size: 16px;
        font-weight: 600;
        line-height: 1.2;
    }
}

.card-header-main,
.card-header-actions {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}

.card-header-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.file-table {
    border-radius: 0;
}

.shop-cell {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 0;

    .el-icon {
        flex-shrink: 0;
        color: var(--primary);
        font-size: 15px;
    }

    strong {
        overflow: hidden;
        color: var(--text-primary);
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
}

.soft-badge,
.status-pill,
.check-pill {
    border-radius: 999px !important;
}

.check-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    max-width: 100%;
    padding: 4px 10px;
    border: 1px solid transparent;
    overflow: hidden;
    font-size: 12px;
    font-weight: 700;
    line-height: 1.4;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.check-pill--success {
    border-color: var(--border-color-light);
    background: var(--bg-elevated);
    color: var(--success);
}

.check-pill--error {
    border-color: var(--border-color-light);
    background: var(--bg-elevated);
    color: var(--error);
}

.check-dot {
    width: 6px;
    height: 6px;
    flex-shrink: 0;
    border-radius: 50%;
    background: currentColor;
}

.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 64px;
    padding: 4px 10px;
    background: var(--bg-hover);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 700;
}

.status-pill--warning {
    background: var(--warning-light);
    color: var(--warning);
}

.status-pill--success {
    background: var(--bg-elevated);
    color: var(--success);
}

.status-pill--error,
.text-error {
    color: var(--error);
}

.status-pill--error {
    background: var(--error-light);
}

.text-tertiary {
    color: var(--text-tertiary);
}

.file-skeleton-list {
    display: grid;
    gap: 0;
    padding: 8px 0;
}

.file-skeleton-row {
    display: grid;
    grid-template-columns: minmax(180px, 1.7fr) 0.6fr 1fr 0.7fr;
    gap: 18px;
    align-items: center;
    min-height: 58px;
    padding: 0 18px;
    border-bottom: 1px solid var(--border-color-light);
}

.skeleton-block {
    display: block;
    height: 13px;
    border-radius: 999px;
    background: var(--bg-hover);
    animation: pulse 1.2s ease-in-out infinite;
}

.skeleton-name {
    width: 82%;
}

.skeleton-short {
    width: 52%;
}

.skeleton-medium {
    width: 70%;
}

.skeleton-badge {
    width: 62px;
    height: 24px;
}

.file-empty-state {
    display: grid;
    place-items: center;
    gap: 10px;
    min-height: 160px;
    color: var(--text-tertiary);

    p {
        margin: 0;
        font-size: 13px;
    }
}

.empty-illustration {
    position: relative;
    width: 54px;
    height: 62px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-lg);
    background: var(--bg-elevated);

    span {
        position: absolute;
        left: 12px;
        right: 12px;
        top: 22px;
        height: 4px;
        border-radius: 999px;
        background: var(--primary-light-5);
    }
}

.queue-state--running {
    background: var(--primary-light-9);
    color: var(--primary);
}

.queue-inline-panel {
    display: grid;
    gap: 9px;
    padding: 10px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-elevated);
}

.queue-stat-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 8px;
}

.queue-stat {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-sm);
    background: var(--bg-card);

    span {
        color: var(--text-tertiary);
        font-size: 11px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 800;
        line-height: 1;
    }
}

.queue-stat--success strong {
    color: var(--success);
}

.queue-stat--error strong {
    color: var(--error);
}

.queue-summary {
    min-width: 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.6;
}

.reference-panel {
    position: sticky;
    top: 0;
    display: grid;
    gap: 10px;
    min-width: 0;
    padding: 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);
}

.naming-assistant {
    display: grid;
    gap: 9px;
}

.naming-fields {
    display: grid;
    gap: 8px;
}

.naming-field {
    display: grid;
    gap: 6px;
    min-width: 0;

    > span {
        color: var(--text-secondary);
        font-size: 11px;
        font-weight: 700;
    }

    :deep(.el-date-editor.el-input),
    :deep(.el-select),
    :deep(.el-input) {
        width: 100%;
    }
}

.generated-name-button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    min-height: 38px;
    padding: 8px 10px;
    border: 1px dashed var(--surface-border);
    border-radius: calc(var(--radius-card) - 2px);
    background: var(--bg-card);
    color: var(--text-tertiary);
    text-align: left;
    cursor: not-allowed;

    strong {
        min-width: 0;
        color: currentColor;
        font-family: "SF Mono", SFMono-Regular, Consolas, monospace;
        font-size: 12px;
        font-weight: 700;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    &--ready {
        border-style: solid;
        border-color: var(--input-hover-border);
        color: var(--text-primary);
        cursor: pointer;
    }
}

.shop-option {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    min-width: 0;

    small {
        flex: 0 0 auto;
        color: var(--text-tertiary);
        font-size: 11px;
    }
}

.platform-card-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
}

.platform-card {
    display: grid;
    gap: 7px;
    min-width: 0;
    padding: 9px 10px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-elevated);

    p {
        margin: 0;
        color: var(--text-tertiary);
        font-size: 11px;
        line-height: 1.35;
        word-break: break-all;
    }
}

.platform-card-line {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    overflow: hidden;
}

.type-list {
    display: flex;
    flex-wrap: nowrap;
    gap: 4px;
    min-width: 0;
    overflow: hidden;
}

.platform-example {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.check-note {
    display: flex;
    gap: 8px;
    padding: 11px;
    color: var(--text-secondary);
    font-size: 11px;
    line-height: 1.6;
}

.check-note-dot {
    width: 7px;
    height: 7px;
    flex: 0 0 auto;
    margin-top: 7px;
    border-radius: 50%;
    background: var(--success);
}

.upload-complete-dialog {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 4px 0;
}

.upload-complete-icon {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--success);
    font-size: 34px;
}

.upload-complete-title {
    margin: 0 0 6px;
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 600;
}

.upload-complete-desc {
    margin: 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.7;
}

.upload-blocking-mask {
    position: fixed;
    inset: 0;
    z-index: 3000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgba(15, 23, 42, 0.56);
    backdrop-filter: blur(2px);
}

.upload-blocking-card {
    display: grid;
    gap: 14px;
    width: min(460px, 100%);
    padding: 22px 22px 20px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);
    box-shadow: var(--shadow-card);

    h3 {
        margin: 0;
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 700;
        line-height: 1.3;
    }

    p {
        margin: -6px 0 0;
        color: var(--text-secondary);
        font-size: 13px;
        line-height: 1.7;
    }
}

.upload-blocking-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: fit-content;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 999px;
    background: var(--primary-light-9);
    color: var(--primary);
    font-size: 12px;
    font-weight: 700;
}

.upload-blocking-meta {
    display: grid;
    gap: 4px;

    span {
        color: var(--text-tertiary);
        font-size: 11px;
        font-weight: 700;
    }

    strong {
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
        line-height: 1.5;
        overflow-wrap: anywhere;
    }
}

@keyframes scan-line {
    0% {
        transform: translateY(0);
        opacity: 0;
    }

    15%,
    85% {
        opacity: 0.9;
    }

    100% {
        transform: translateY(250px);
        opacity: 0;
    }
}

@media (max-width: 1180px) {
    .upload-main-grid,
    .upload-rule-board {
        grid-template-columns: minmax(0, 1fr);
    }

    .reference-panel {
        position: static;
    }

    .queue-stat-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
    .operation-heading,
    .reference-heading,
    .file-list-card .card-header,
    .card-header-main {
        align-items: flex-start;
        flex-direction: column;
    }

    .upload-steps {
        grid-template-columns: 1fr;
    }

    .upload-step {
        border-right: 0;
        border-bottom: 1px solid var(--border-color-light);

        &:last-child {
            border-bottom: 0;
        }
    }

    .queue-stat-grid,
    .platform-card-list {
        grid-template-columns: 1fr;
    }

    .file-skeleton-row {
        grid-template-columns: 1fr;
        gap: 9px;
        padding: 14px 16px;
    }
}

@media (prefers-reduced-motion: reduce) {
    .drop-zone--active,
    .scan-line,
    .skeleton-block {
        animation: none;
    }
}
</style>
