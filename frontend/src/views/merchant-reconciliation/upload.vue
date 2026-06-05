<template>
    <div class="page-container">
        <div class="upload-shell">
            <section class="upload-rule-board" aria-label="商家对账导入说明">
                <div class="rule-board-main">
                    <div class="rule-heading">
                        <div>
                            <span class="section-kicker">MERCHANT RECONCILIATION</span>
                            <h2>商家对账上传中心</h2>
                        </div>
                        <p>红单和银行流水共用一个上传框。红单校验 sheet 名，银行流水校验文件名中的数据年月；处理结果统一在对账任务里查看。</p>
                    </div>
                    <div class="rule-code-line">
                        <span class="rule-token rule-token--type">YYYYMM货款</span>
                        <span class="rule-separator">+</span>
                        <span class="rule-token rule-token--shop">YYYYMM采购</span>
                        <span class="rule-separator">/</span>
                        <span class="rule-token rule-token--type">YYYYMM_银行流水_xxxx</span>
                        <span class="rule-extension">.xls / .xlsx / .xlsm / .csv</span>
                    </div>
                    <div class="rule-meta">
                        <p class="rule-example">示例：`202606货款`、`202606采购`、`202606_银行流水_壹韵.xls`</p>
                        <div class="rule-hint-list">
                            <span>模板下载只依赖月份</span>
                            <span>文件类型由预检自动识别</span>
                            <span>处理结果在对账任务里查看</span>
                        </div>
                    </div>
                </div>

                <div class="rule-platforms">
                    <div class="reference-heading rule-platforms-heading">
                        <div>
                            <span class="section-kicker">WORKFLOW</span>
                            <h3>上传流程</h3>
                        </div>
                    </div>
                    <div class="platform-card-list">
                        <div class="platform-card">
                            <div class="platform-card-line">
                                <span class="step-chip">1</span>
                                <strong>准备文件</strong>
                            </div>
                            <p class="platform-example">红单可下载模板，银行流水按文件名带账期</p>
                        </div>
                        <div class="platform-card">
                            <div class="platform-card-line">
                                <span class="step-chip">2</span>
                                <strong>统一预检</strong>
                            </div>
                            <p class="platform-example">自动区分红单和银行流水，显示数据年月和校验结果</p>
                        </div>
                        <div class="platform-card">
                            <div class="platform-card-line">
                                <span class="step-chip">3</span>
                                <strong>提交任务</strong>
                            </div>
                            <p class="platform-example">文件直传 OSS，异步任务解析入库并记录结果</p>
                        </div>
                    </div>
                </div>
            </section>

            <div class="upload-main-grid">
                <section class="upload-workspace">
                    <MerchantFilters
                        v-if="userStore.isSuperAdmin"
                        :model="searchForm"
                        :shops="[]"
                        :orgs="orgOptions"
                        :show-org="true"
                        :show-month="false"
                        :show-shop="false"
                        :show-keyword="false"
                        :show-actions="false"
                        :shop-loading="false"
                        @update:model="Object.assign(searchForm, $event)"
                    />

                    <section class="upload-steps" aria-label="上传流程">
                        <div class="upload-step is-active">
                            <strong>1</strong>
                            <span>准备文件</span>
                        </div>
                        <div class="upload-step" :class="{ 'is-active': uploadItems.length > 0 || isReadingFiles }">
                            <strong>2</strong>
                            <span>拖拽预检</span>
                        </div>
                        <div class="upload-step" :class="{ 'is-active': readyUploadItems.length > 0 || importing }">
                            <strong>3</strong>
                            <span>提交任务</span>
                        </div>
                    </section>

                    <el-card shadow="never" class="upload-card">
                        <div class="operation-heading">
                            <div>
                                <span class="section-kicker">STEP 01</span>
                                <h3>下载模板并准备文件</h3>
                            </div>
                            <div class="card-header-actions">
                                <el-button :loading="templateLoading" @click="openTemplateDialog">下载红单模板</el-button>
                            </div>
                        </div>

                        <div
                            class="drop-zone"
                            :class="{
                                'drop-zone--active': isDragging,
                                'drop-zone--scanning': isReadingFiles,
                            }"
                            @dragover.prevent="isDragging = true"
                            @dragleave.prevent="isDragging = false"
                            @drop.prevent="handleDrop"
                        >
                            <input
                                ref="fileInputRef"
                                type="file"
                                multiple
                                accept=".xls,.xlsx,.xlsm,.csv"
                                style="display: none"
                                @change="handleFileInputChange"
                            />
                            <div v-if="isReadingFiles" class="scan-line" aria-hidden="true"></div>
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
                                <p class="drop-zone-text">{{ isReadingFiles ? precheckDropText : "拖拽红单或银行流水到此处" }}</p>
                                <div v-if="!isReadingFiles" class="drop-zone-actions">
                                    <el-button size="small" @click="triggerFileInput">
                                        <el-icon><Upload /></el-icon>
                                        选择文件
                                    </el-button>
                                </div>
                                <p class="drop-zone-hint">
                                    {{ isReadingFiles ? precheckHintText : "红单支持 .xlsx / .xlsm；银行流水支持 .xls / .xlsx / .xlsm / .csv，文件名需符合 YYYYMM_银行流水_xxxx" }}
                                </p>
                            </div>
                        </div>
                    </el-card>

                    <el-card v-if="uploadItems.length > 0 || isReadingFiles" shadow="never" class="file-list-card">
                        <template #header>
                            <div class="card-header">
                                <div class="summary-title-group">
                                    <span class="card-header-title">预上传任务列表</span>
                                    <span class="summary-count">共 {{ uploadItems.length }} 个文件，可提交 {{ readyUploadItems.length }} 个</span>
                                </div>
                                <div class="card-header-actions">
                                    <el-button type="primary" :disabled="readyUploadItems.length === 0 || importing" :loading="importing" @click="confirmUploadAll">
                                        提交任务
                                    </el-button>
                                    <el-button :disabled="importing || uploadItems.length === 0" @click="clearAll">清空</el-button>
                                </div>
                            </div>
                        </template>

                        <el-table :data="uploadItems" stripe border class="summary-table roomy-table file-table">
                            <el-table-column type="index" label="#" width="50" align="center" />
                            <el-table-column label="类型" width="110" align="center">
                                <template #default="{ row }">
                                    <FileTypeBadge :type="row.type" />
                                </template>
                            </el-table-column>
                            <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
                            <el-table-column v-if="userStore.isSuperAdmin" label="组织" width="160" show-overflow-tooltip>
                                <template #default>{{ currentOrgLabel }}</template>
                            </el-table-column>
                            <el-table-column label="提取数据年月" width="120">
                                <template #default="{ row }">
                                    <el-tag v-if="row.accountingYear && row.accountingMonth" type="info" size="small" class="soft-badge">
                                        {{ row.accountingYear }}-{{ String(row.accountingMonth).padStart(2, "0") }}
                                    </el-tag>
                                    <span v-else class="text-error">无法识别</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="识别店铺" min-width="180" show-overflow-tooltip>
                                <template #default="{ row }">
                                    <div v-if="row.type === '红单' && row.shopNames?.length" class="shop-preview-list">
                                        <el-tag
                                            v-for="shopName in row.shopNames.slice(0, 3)"
                                            :key="shopName"
                                            type="info"
                                            size="small"
                                            class="soft-badge"
                                        >
                                            {{ shopName }}
                                        </el-tag>
                                        <span v-if="row.shopNames.length > 3" class="shop-preview-more">+{{ row.shopNames.length - 3 }}</span>
                                    </div>
                                    <span v-else-if="row.type === '红单'" class="text-error">未识别</span>
                                    <span v-else class="text-muted">不需要</span>
                                </template>
                            </el-table-column>
                            <el-table-column label="校验" min-width="260" show-overflow-tooltip>
                                <template #default="{ row }">
                                    <span :class="row.valid ? 'check-pill check-pill--success' : 'check-pill check-pill--error'">
                                        <span class="check-dot"></span>
                                        {{ row.message }}
                                    </span>
                                    <div v-if="row.error" class="upload-error-text">{{ row.error }}</div>
                                </template>
                            </el-table-column>
                            <el-table-column label="状态" width="110" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.status === 'success'" class="status-pill status-pill--success">已提交</span>
                                    <span v-else-if="row.status === 'uploading'" class="status-pill status-pill--warning">上传中</span>
                                    <span v-else-if="row.status === 'error'" class="status-pill status-pill--error">失败</span>
                                    <span v-else class="status-pill">待提交</span>
                                    <el-progress
                                        v-if="row.status === 'uploading'"
                                        class="upload-row-progress"
                                        :percentage="row.progress || 0"
                                        :stroke-width="3"
                                        :show-text="false"
                                    />
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="110" align="center">
                                <template #default="{ row, $index }">
                                    <el-button v-if="row.valid && row.status !== 'success'" type="primary" link :disabled="importing" @click="confirmUploadSingle(row)">
                                        提交
                                    </el-button>
                                    <el-button type="danger" link :disabled="importing" @click="removeUploadItem($index)">
                                        移除
                                    </el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
                </section>
            </div>
        </div>

        <el-dialog v-model="templateDialogVisible" title="下载红单模板" width="420px">
            <el-form>
                <el-form-item label="模板数据年月" required>
                    <el-date-picker v-model="templateMonth" type="month" value-format="YYYY-MM" placeholder="选择数据年月" style="width: 100%" />
                </el-form-item>
            </el-form>
            <template #footer>
                <el-button @click="templateDialogVisible = false">取消</el-button>
                <el-button type="primary" :loading="templateLoading" @click="handleDownloadTemplate">下载</el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Upload } from "@element-plus/icons-vue";
import { downloadRedSheetTemplate } from "@/api/merchantReconciliation";
import { createBatch, getOssSts, uploadCallback, type OssStsCredential } from "@/api/upload";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import MerchantFilters from "./components/MerchantFilters.vue";
import { downloadFile, loadXlsx } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationUpload" });

type UploadFileType = "红单" | "银行流水";

interface UploadQueueItem {
    file: File;
    name: string;
    type: UploadFileType;
    accountingYear?: number;
    accountingMonth?: number;
    shopNames: string[];
    valid: boolean;
    message: string;
    status: "pending" | "uploading" | "success" | "error";
    progress: number;
    error?: string;
}

interface RedSheetUploadContext {
    batchId: number;
    sts: OssStsCredential;
    ossClient: any;
}

const {
    userStore,
    searchForm,
    orgOptions,
    fetchOrgs,
} = useMerchantReconciliationFilters({ autoSelectFirstShop: false });

const importing = ref(false);
const templateLoading = ref(false);
const isDragging = ref(false);
const isReadingFiles = ref(false);
const templateDialogVisible = ref(false);
const templateMonth = ref(searchForm.month);
const fileInputRef = ref<HTMLInputElement | null>(null);
const uploadItems = ref<UploadQueueItem[]>([]);
let ossModulePromise: Promise<typeof import("ali-oss")> | null = null;

const readyUploadItems = computed(() => uploadItems.value.filter((item) => item.valid && item.status !== "success"));
const precheckDropText = computed(() => "正在识别文件类型、数据年月和校验信息...");
const precheckHintText = computed(() => "红单会读取 sheet 和采购店铺；银行流水会读取文件名中的数据年月。");
const currentOrgLabel = computed(() => {
    if (!userStore.isSuperAdmin) return "-";
    return orgOptions.value.find((org) => org.id === searchForm.orgId)?.name || "待选择";
});

function openTemplateDialog() {
    templateMonth.value = searchForm.month;
    templateDialogVisible.value = true;
}

async function handleDownloadTemplate() {
    const [year, month] = String(templateMonth.value || "").split("-").map(Number);
    if (!year || !month) {
        ElMessage.warning("请选择模板月份");
        return;
    }
    templateLoading.value = true;
    try {
        const blob = await downloadRedSheetTemplate({ accounting_year: year, accounting_month: month });
        downloadFile(blob, `${year}${String(month).padStart(2, "0")}红单导入模板.xlsx`);
        templateDialogVisible.value = false;
    } finally {
        templateLoading.value = false;
    }
}

function triggerFileInput() {
    fileInputRef.value?.click();
}

async function handleFileInputChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files || []);
    await addUploadFiles(files);
    input.value = "";
}

async function handleDrop(event: DragEvent) {
    isDragging.value = false;
    const files = Array.from(event.dataTransfer?.files || []).filter((file) => /\.(xls|xlsx|xlsm|csv)$/i.test(file.name));
    await addUploadFiles(files);
}

async function addUploadFiles(files: File[]) {
    if (!files.length) return;
    isReadingFiles.value = true;
    try {
        for (const file of files) {
            if (uploadItems.value.some((item) => item.name === file.name && item.file.size === file.size)) {
                continue;
            }
            const parsed = await inspectUploadFile(file);
            uploadItems.value.push({
                file,
                name: file.name,
                type: parsed.type,
                accountingYear: parsed.accountingYear,
                accountingMonth: parsed.accountingMonth,
                shopNames: parsed.shopNames,
                valid: parsed.valid,
                message: parsed.message,
                status: "pending",
                progress: 0,
            });
        }
    } finally {
        isReadingFiles.value = false;
    }
}

async function inspectUploadFile(file: File): Promise<{
    type: UploadFileType;
    valid: boolean;
    message: string;
    accountingYear?: number;
    accountingMonth?: number;
    shopNames: string[];
}> {
    if (/银行流水/i.test(file.name)) {
        return inspectBankFlowFilename(file.name);
    }
    return inspectRedSheetFile(file);
}

async function inspectRedSheetFile(file: File): Promise<{
    type: "红单";
    valid: boolean;
    message: string;
    accountingYear?: number;
    accountingMonth?: number;
    shopNames: string[];
}> {
    if (!/\.(xlsx|xlsm)$/i.test(file.name)) {
        return { type: "红单", valid: false, message: "红单仅支持 .xlsx / .xlsm，银行流水文件名需包含“银行流水”", accountingYear: undefined, accountingMonth: undefined, shopNames: [] };
    }
    try {
        const XLSX = await loadXlsx();
        const buffer = await file.arrayBuffer();
        const workbook = XLSX.read(buffer, { type: "array" });
        const sheetNames = workbook.SheetNames || [];
        const yearMonthSet = new Set(
            sheetNames
                .map((name) => String(name).match(/^(\d{6})(货款|采购)$/))
                .filter(Boolean)
                .map((match) => match?.[1] || ""),
        );
        if (yearMonthSet.size !== 1) {
            return {
                type: "红单",
                valid: false,
                message: "sheet 名不符合标准，必须同时包含同一个 YYYYMM 的货款和采购",
                accountingYear: undefined,
                accountingMonth: undefined,
                shopNames: [],
            };
        }
        const yearMonth = Array.from(yearMonthSet)[0];
        if (!sheetNames.includes(`${yearMonth}货款`) || !sheetNames.includes(`${yearMonth}采购`)) {
            return { type: "红单", valid: false, message: "缺少标准 sheet：YYYYMM货款 或 YYYYMM采购", accountingYear: undefined, accountingMonth: undefined, shopNames: [] };
        }
        const shopNames = extractPurchaseShopNames(XLSX, workbook.Sheets[`${yearMonth}采购`]);
        if (!shopNames.length) {
            return {
                type: "红单",
                valid: false,
                message: "采购 sheet 未识别到店铺列或店铺名称",
                accountingYear: Number(yearMonth.slice(0, 4)),
                accountingMonth: Number(yearMonth.slice(4, 6)),
                shopNames: [],
            };
        }
        return {
            type: "红单",
            valid: true,
            message: `识别成功：${yearMonth}货款 / ${yearMonth}采购，店铺 ${shopNames.length} 个`,
            accountingYear: Number(yearMonth.slice(0, 4)),
            accountingMonth: Number(yearMonth.slice(4, 6)),
            shopNames,
        };
    } catch {
        return { type: "红单", valid: false, message: "文件无法解析，请确认是标准 Excel 红单文件", accountingYear: undefined, accountingMonth: undefined, shopNames: [] };
    }
}

function extractPurchaseShopNames(XLSX: typeof import("xlsx"), sheet: any) {
    const rows = XLSX.utils.sheet_to_json<string[]>(sheet, { header: 1, raw: false, defval: "" });
    const headerRow = rows[0] || [];
    const shopColumnIndex = headerRow.findIndex((header) => String(header || "").trim() === "店铺");
    if (shopColumnIndex < 0) return [];
    const shopNames = new Set<string>();
    for (const row of rows.slice(1)) {
        const shopName = String(row[shopColumnIndex] || "").trim();
        if (shopName) {
            shopNames.add(shopName);
        }
    }
    return Array.from(shopNames);
}

function inspectBankFlowFilename(filename: string): {
    type: "银行流水";
    valid: boolean;
    message: string;
    accountingYear?: number;
    accountingMonth?: number;
    shopNames: string[];
} {
    const stem = filename.replace(/\.[^.]+$/, "");
    const match = stem.match(/(\d{4})(?:\s*年\s*|[-/.])?(\d{1,2})(?:\s*月)?[_\-\s]+银行流水/i);
    if (!match) {
        return { type: "银行流水", valid: false, message: "文件名需符合 YYYYMM_银行流水_xxxx", accountingYear: undefined, accountingMonth: undefined, shopNames: [] };
    }
    const accountingYear = Number(match[1]);
    const accountingMonth = Number(match[2]);
    if (!accountingYear || accountingMonth < 1 || accountingMonth > 12) {
        return { type: "银行流水", valid: false, message: "文件名数据年月不正确", accountingYear: undefined, accountingMonth: undefined, shopNames: [] };
    }
    return { type: "银行流水", valid: true, message: "文件名识别成功，账户和日期由后端解析", accountingYear, accountingMonth, shopNames: [] };
}

function removeUploadItem(index: number) {
    uploadItems.value.splice(index, 1);
}

function clearAll() {
    uploadItems.value = [];
}

function requireImportOrg() {
    if (!userStore.isSuperAdmin) return true;
    if (searchForm.orgId) return true;
    ElMessage.warning("请选择组织后上传");
    return false;
}

async function confirmUploadSingle(row: UploadQueueItem) {
    if (!requireImportOrg()) return;
    if (!row.accountingYear || !row.accountingMonth) {
        ElMessage.warning("请先确认数据年月识别正确");
        return;
    }
    const typeLabel = row.type;
    const extraText = row.type === "红单"
        ? `，识别到 ${row.shopNames.length} 个店铺`
        : "；账户名称、对方户名和直播日期会在后端解析";
    try {
        await ElMessageBox.confirm(
            `将按 ${row.accountingYear}-${String(row.accountingMonth).padStart(2, "0")} 提交${typeLabel}处理任务${extraText}；处理结果可在对账任务查看。`,
            `确认上传${typeLabel}`,
            { type: "warning", confirmButtonText: "提交", cancelButtonText: "取消" },
        );
    } catch {
        return;
    }
    importing.value = true;
    try {
        const context = await createUploadContext([row], `商家对账${row.type}上传`);
        await uploadRow(row, context);
    } finally {
        importing.value = false;
    }
}

async function confirmUploadAll() {
    if (!requireImportOrg()) return;
    if (!readyUploadItems.value.length) {
        ElMessage.warning("当前没有可上传文件");
        return;
    }
    try {
        const typeNames = Array.from(new Set(readyUploadItems.value.map((item) => item.type))).join("、");
        await ElMessageBox.confirm(
            `本次将提交 ${readyUploadItems.value.length} 个${typeNames}处理任务；文件会先上传到 OSS，处理结果在对账任务查看。`,
            "确认批量上传",
            { type: "warning", confirmButtonText: "开始提交", cancelButtonText: "取消" },
        );
    } catch {
        return;
    }
    importing.value = true;
    try {
        const context = await createUploadContext(readyUploadItems.value, "商家对账文件上传");
        for (const row of readyUploadItems.value) {
            await uploadRow(row, context);
        }
    } finally {
        importing.value = false;
    }
}

const STS_REFRESH_INTERVAL_MS = 5 * 60 * 1000;
const STS_REFRESH_SAFETY_MS = 60 * 1000;
const OSS_REQUEST_TIMEOUT = 2 * 60 * 1000;
const OSS_MULTIPART_PART_SIZE = 1024 * 1024;
const OSS_MULTIPART_PARALLEL = 2;

function loadOss() {
    if (!ossModulePromise) {
        ossModulePromise = import("ali-oss");
    }
    return ossModulePromise;
}

function toOssCredential(sts: OssStsCredential) {
    return {
        accessKeyId: sts.access_key_id,
        accessKeySecret: sts.access_key_secret,
        stsToken: sts.security_token,
    };
}

function stsRefreshInterval(sts: OssStsCredential): number {
    const expiresAt = Date.parse(sts.expiration);
    if (Number.isNaN(expiresAt)) return STS_REFRESH_INTERVAL_MS;
    const msUntilExpiration = expiresAt - Date.now() - STS_REFRESH_SAFETY_MS;
    return Math.max(30 * 1000, Math.min(STS_REFRESH_INTERVAL_MS, msUntilExpiration));
}

async function createOssClient(sts: OssStsCredential, batchId: number) {
    const OSS = await loadOss();
    return new OSS.default({
        region: sts.region,
        bucket: sts.bucket,
        endpoint: sts.endpoint,
        ...toOssCredential(sts),
        secure: sts.endpoint.startsWith("https://"),
        timeout: OSS_REQUEST_TIMEOUT,
        retryMax: 0,
        refreshSTSToken: async () => toOssCredential(await getOssSts(batchId)),
        refreshSTSTokenInterval: stsRefreshInterval(sts),
    });
}

function buildOssKey(sts: OssStsCredential, fileName: string): string {
    const safeName = fileName.replace(/[\\/]/g, "_");
    return `${sts.oss_key_prefix}${Date.now()}_${safeName}`;
}

async function createUploadContext(rows: UploadQueueItem[], remark = "商家对账文件上传"): Promise<RedSheetUploadContext> {
    const batch = await createBatch({
        file_count: rows.length,
        total_bytes: rows.reduce((sum, row) => sum + row.file.size, 0),
        org_id: userStore.isSuperAdmin ? searchForm.orgId : undefined,
        remark,
    });
    const sts = await getOssSts(batch.id);
    const ossClient = await createOssClient(sts, batch.id);
    return { batchId: batch.id, sts, ossClient };
}

function ossErrorMessage(error: any): string {
    if (error?.code === "ConnectionTimeoutError" || error?.code === "ResponseTimeoutError") {
        return "文件上传超时，请重试";
    }
    return error?.message || error?.name || error?.code || "上传失败";
}

async function uploadRow(row: UploadQueueItem, context: RedSheetUploadContext) {
    if (!row.accountingYear || !row.accountingMonth) return;
    row.status = "uploading";
    row.progress = 0;
    row.error = "";
    try {
        const ossKey = buildOssKey(context.sts, row.file.name);
        await context.ossClient.multipartUpload(ossKey, row.file, {
            timeout: OSS_REQUEST_TIMEOUT,
            partSize: OSS_MULTIPART_PART_SIZE,
            parallel: OSS_MULTIPART_PARALLEL,
            progress: async (percent: number) => {
                row.progress = Math.round(percent * 100);
            },
        });
        await uploadCallback({
            batch_id: context.batchId,
            original_name: row.file.name,
            oss_key: ossKey,
            file_size: row.file.size,
            parsed_year: row.accountingYear,
            parsed_month: row.accountingMonth,
            parsed_type: row.type,
            parsed_shop: row.type === "红单" && row.shopNames.length === 1 ? row.shopNames[0] : "",
            detected_platform: "douyin",
        });
        row.status = "success";
        row.progress = 100;
        ElMessage.success(`${row.name} 已提交处理任务`);
    } catch (error: any) {
        row.status = "error";
        row.error = ossErrorMessage(error);
    }
}

onMounted(async () => {
    await fetchOrgs();
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";

.upload-shell {
    display: grid;
    gap: 14px;
    align-items: start;
}

.upload-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
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

.section-kicker {
    display: block;
    margin-bottom: 4px;
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0;
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

.step-chip {
    display: inline-flex;
    width: 24px;
    height: 24px;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.12);
    color: var(--el-color-primary);
    font-size: 12px;
    font-weight: 700;
}

.reference-heading,
.operation-heading {
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

.drop-zone-text {
    margin: 12px 0 5px;
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
}

.drop-zone-actions {
    display: flex;
    justify-content: center;
    margin-bottom: 8px;
}

.drop-zone-hint {
    color: var(--text-tertiary);
    font-size: 12px;
}

.platform-card-list {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
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
}

.platform-card-line {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    overflow: hidden;
}

.platform-example {
    margin: 0;
    color: var(--text-tertiary);
    font-size: 11px;
    line-height: 1.35;
}

.file-list-card {
    :deep(.el-card__body) {
        padding: 0;
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

.upload-error-text {
    margin-top: 6px;
    color: var(--el-color-danger);
    font-size: 12px;
    line-height: 18px;
}

.shop-preview-list {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 5px;
    overflow: hidden;
}

.shop-preview-more {
    color: var(--text-tertiary);
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
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
    .upload-rule-board {
        grid-template-columns: minmax(0, 1fr);
    }

    .platform-card-list {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 768px) {
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

    .platform-card-list {
        grid-template-columns: 1fr;
    }
}
</style>
