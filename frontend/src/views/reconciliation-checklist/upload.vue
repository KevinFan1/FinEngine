<template>
    <div class="page-container">
        <div class="upload-shell">
            <div class="upload-main-grid">
                <section class="upload-workspace">
                    <el-card v-if="userStore.isSuperAdmin" shadow="never" class="target-org-card">
                        <el-form inline>
                            <el-form-item label="上传到组织">
                                <el-select
                                    v-model="orgId"
                                    placeholder="请选择组织"
                                    filterable
                                    style="width: 260px"
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

                    <div class="page-header">
                        <div>
                            <h2>底表上传</h2>
                            <p>确认表头匹配后再提交任务。</p>
                        </div>
                        <el-button @click="handleTemplateDownload">下载模板</el-button>
                    </div>

                    <section class="upload-steps" aria-label="上传流程">
                        <div class="upload-step is-active">
                            <strong>1</strong>
                            <span>下载模板</span>
                        </div>
                        <div class="upload-step" :class="{ 'is-active': items.length > 0 || isReadingHeaders }">
                            <strong>2</strong>
                            <span>检查表头</span>
                        </div>
                        <div class="upload-step" :class="{ 'is-active': readyItems.length > 0 || uploading }">
                            <strong>3</strong>
                            <span>提交任务</span>
                        </div>
                    </section>

                    <el-card shadow="never" class="upload-card">
                        <div class="operation-heading">
                            <div>
                                <h3>选择并预检对账清单</h3>
                            </div>
                            <span class="header-hint">只读取前 5 行检查表头</span>
                        </div>

                        <div
                            class="drop-zone"
                            :class="{
                                'drop-zone--active': dragging,
                                'drop-zone--scanning': isReadingHeaders,
                            }"
                            @dragover.prevent="dragging = true"
                            @dragleave.prevent="dragging = false"
                            @drop.prevent="handleDrop"
                        >
                            <input
                                ref="fileInput"
                                type="file"
                                multiple
                                accept=".xlsx,.xlsm"
                                style="display: none"
                                @change="handleFileInput"
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
                                    {{ isReadingHeaders ? readingText : "拖拽对账清单到此处" }}
                                </p>
                                <div v-if="!isReadingHeaders" class="drop-zone-actions">
                                    <el-button size="small" @click="fileInput?.click()">
                                        <el-icon><Upload /></el-icon>
                                        选择文件
                                    </el-button>
                                </div>
                                <p class="drop-zone-hint">
                                    {{ isReadingHeaders ? readingHint : "支持 .xlsx / .xlsm，上传前只读取前 5 行检查表头是否匹配" }}
                                </p>
                            </div>
                        </div>
                    </el-card>

                    <el-card v-if="items.length > 0 || isReadingHeaders" shadow="never" class="file-list-card">
                        <template #header>
                            <div class="card-header">
                                <div class="summary-title-group">
                                    <span class="card-header-title">预上传任务列表</span>
                                    <span class="summary-count">共 {{ items.length }} 个文件，可提交 {{ readyItems.length }} 个</span>
                                </div>
                                <div class="card-header-actions">
                                    <el-button
                                        type="primary"
                                        :disabled="readyItems.length === 0 || uploading"
                                        :loading="uploading"
                                        @click="submitAll"
                                    >
                                        提交任务
                                    </el-button>
                                    <el-button :disabled="uploading || items.length === 0" @click="clearAll">清空</el-button>
                                </div>
                            </div>
                        </template>

                        <el-table :data="items" stripe border class="summary-table roomy-table file-table">
                            <el-table-column type="index" label="#" width="50" align="center" />
                            <el-table-column label="类型" width="150" align="center">
                                <template #default="{ row }">
                                    <FileTypeBadge :type="row.fileType || '对账清单'" />
                                </template>
                            </el-table-column>
                            <el-table-column prop="name" label="文件名" min-width="260" show-overflow-tooltip />
                            <el-table-column v-if="userStore.isSuperAdmin" label="组织" width="180" show-overflow-tooltip>
                                <template #default>{{ currentOrgLabel }}</template>
                            </el-table-column>
                            <el-table-column label="表头校验" min-width="280" show-overflow-tooltip>
                                <template #default="{ row }">
                                    <span :class="row.valid ? 'check-pill check-pill--success' : 'check-pill check-pill--error'">
                                        <span class="check-dot"></span>
                                        {{ row.message }}
                                    </span>
                                    <div v-if="row.error" class="upload-error-text">{{ row.error }}</div>
                                </template>
                            </el-table-column>
                            <el-table-column label="状态" width="120" align="center">
                                <template #default="{ row }">
                                    <span v-if="row.status === 'success'" class="status-pill status-pill--success">已提交</span>
                                    <span v-else-if="row.status === 'uploading'" class="status-pill status-pill--warning">上传中</span>
                                    <span v-else-if="row.status === 'error'" class="status-pill status-pill--error">失败</span>
                                    <span v-else class="status-pill">待提交</span>
                                    <el-progress
                                        v-if="row.status === 'uploading'"
                                        class="upload-row-progress"
                                        :percentage="row.progress"
                                        :stroke-width="3"
                                        :show-text="false"
                                    />
                                </template>
                            </el-table-column>
                            <el-table-column label="操作" width="120" align="center">
                                <template #default="{ row, $index }">
                                    <el-button
                                        v-if="row.valid && row.status !== 'success'"
                                        type="primary"
                                        link
                                        :disabled="uploading"
                                        @click="submitOne(row)"
                                    >
                                        提交
                                    </el-button>
                                    <el-button type="danger" link :disabled="uploading" @click="removeItem($index)">
                                        移除
                                    </el-button>
                                </template>
                            </el-table-column>
                        </el-table>
                    </el-card>
                </section>
            </div>
        </div>

        <div
            v-if="uploading"
            class="upload-blocking-mask"
            role="alert"
            aria-live="assertive"
            aria-busy="true"
        >
            <div class="upload-blocking-card">
                <div class="upload-blocking-badge">上传进行中</div>
                <h3>正在上传对账清单</h3>
                <p>文件正在上传并创建处理任务，请勿关闭页面或刷新浏览器。</p>
                <el-progress :percentage="uploadOverallPercent" :stroke-width="10" status="success" />
                <div class="upload-blocking-meta">
                    <span>当前文件</span>
                    <strong>{{ uploadingFileName || "正在准备上传..." }}</strong>
                </div>
                <div class="upload-blocking-meta">
                    <span>完成进度</span>
                    <strong>{{ uploadDialogDone }} / {{ uploadDialogTotal || readyItems.length }}</strong>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Upload } from "@element-plus/icons-vue";
import FileTypeBadge from "@/components/FileTypeBadge.vue";
import { createBatch, getOssSts, uploadCallback, type OssStsCredential } from "@/api/upload";
import { getAllOrganizations, type Organization } from "@/api/organization";
import { useUserStore } from "@/stores/user";
import { ApiBusinessError } from "@/api";
import { buildUploadOssKey } from "@/utils/ossPath";
import {
    CHECKLIST_FILE_TYPE,
    checklistFileTypeLabel,
    downloadChecklistTemplate,
} from "./common";

type UploadStatus = "pending" | "uploading" | "success" | "error";
const HEADER_CHECK_TIMEOUT = 15000;

interface HeaderCheckResult {
    headerRowFound: boolean;
    valid: boolean;
    missing: string[];
    fileType: string;
    empty: boolean;
}

interface HeaderWorkerSuccess {
    id: number;
    ok: true;
    result: HeaderCheckResult;
}

interface HeaderWorkerFailure {
    id: number;
    ok: false;
    error: string;
}

type HeaderWorkerResponse = HeaderWorkerSuccess | HeaderWorkerFailure;

interface UploadItem {
    id: number;
    file: File;
    name: string;
    valid: boolean;
    fileType: string;
    message: string;
    error: string;
    status: UploadStatus;
    progress: number;
}

interface UploadContext {
    batchId: number;
    sts: OssStsCredential;
    ossClient: any;
}

const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const orgId = ref<number | undefined>();
const fileInput = ref<HTMLInputElement | null>(null);
const items = ref<UploadItem[]>([]);
const dragging = ref(false);
const uploading = ref(false);
const uploadingFileName = ref("");
const uploadDialogTotal = ref(0);
const uploadDialogDone = ref(0);
const isReadingHeaders = ref(false);
const readingText = ref("正在检查表头");
const readingHint = ref("只会读取前几行查找表头");
let ossModulePromise: Promise<typeof import("ali-oss")> | null = null;
let headerWorkerRequestId = 0;
let uploadItemId = 0;

const readyItems = computed(() => items.value.filter((item) => item.valid && item.status !== "success"));
const uploadOverallPercent = computed(() => {
    const total = uploadDialogTotal.value || readyItems.value.length;
    if (!total) return 0;
    const currentProgress = items.value
        .filter((item) => item.status === "uploading")
        .reduce((sum, item) => sum + Math.max(0, Math.min(item.progress, 100)) / 100, 0);
    return Math.min(100, Math.round(((uploadDialogDone.value + currentProgress) / total) * 100));
});
const currentOrgLabel = computed(() => {
    if (!userStore.isSuperAdmin) return userStore.user?.org_name || "-";
    return orgOptions.value.find((org) => org.id === orgId.value)?.name || "-";
});

function nextFrame() {
    return new Promise<void>((resolve) => {
        requestAnimationFrame(() => resolve());
    });
}

async function fetchOrgs() {
    if (!userStore.isSuperAdmin) return;
    orgOptions.value = await getAllOrganizations();
    orgId.value = orgOptions.value[0]?.id;
}

async function handleTemplateDownload() {
    try {
        await downloadChecklistTemplate("source");
    } catch {
        // Error handled by interceptor / browser
    }
}

async function handleFileInput(event: Event) {
    const files = Array.from((event.target as HTMLInputElement).files || []);
    await addFiles(files);
    if (fileInput.value) fileInput.value.value = "";
}

async function handleDrop(event: DragEvent) {
    dragging.value = false;
    await addFiles(Array.from(event.dataTransfer?.files || []));
}

async function addFiles(files: File[]) {
    const candidates = files.filter((file) => /\.(xlsx|xlsm)$/i.test(file.name));
    if (candidates.length !== files.length) {
        ElMessage.warning("仅支持 .xlsx / .xlsm 文件");
    }
    if (!candidates.length) return;

    const queue: UploadItem[] = [];
    for (const file of candidates) {
        const item: UploadItem = {
            id: uploadItemId + 1,
            file,
            name: file.name,
            valid: false,
            fileType: "",
            message: "校验中",
            error: "",
            status: "pending",
            progress: 0,
        };
        uploadItemId = item.id;
        items.value.push(item);
        queue.push(item);
    }

    isReadingHeaders.value = true;
    readingText.value = queue.length > 1 ? `正在检查 1/${queue.length}` : "正在检查表头";
    try {
        await nextFrame();
        for (let index = 0; index < queue.length; index += 1) {
            if (queue.length > 1) {
                readingText.value = `正在检查 ${index + 1}/${queue.length}`;
                await nextFrame();
            }
            await precheck(queue[index]);
            await nextFrame();
        }
    } finally {
        isReadingHeaders.value = false;
        readingText.value = "正在检查表头";
    }
}

async function precheck(item: UploadItem) {
    try {
        const result = await inspectChecklistHeaders(item.file);
        if (result.empty) {
            patchItem(item, {
                valid: true,
                fileType: result.fileType,
                message: "空数据，可提交任务",
                error: "",
                status: "pending",
            });
            return;
        }
        if (!result.headerRowFound) {
            patchItem(item, {
                valid: false,
                message: "未找到模板表头",
                error: "前 5 行未找到模板表头",
                status: "pending",
            });
            return;
        }
        patchItem(item, {
            valid: result.valid,
            fileType: result.fileType,
            message: result.valid ? `识别为${checklistFileTypeLabel(result.fileType)}，可提交任务` : `缺少：${result.missing.join("、")}`,
            error: result.valid ? "" : `缺少：${result.missing.join("、")}`,
            status: "pending",
        });
    } catch (error: any) {
        patchItem(item, {
            valid: false,
            status: "error",
            message: "校验失败",
            error: error?.message || "无法读取文件表头",
        });
    }
}

function patchItem(item: UploadItem, patch: Partial<UploadItem>) {
    Object.assign(item, patch);
    const index = items.value.findIndex((row) => row.id === item.id);
    if (index >= 0) {
        items.value[index] = { ...items.value[index], ...patch };
    }
}

async function inspectChecklistHeaders(file: File): Promise<HeaderCheckResult> {
    const buffer = await file.arrayBuffer();
    return new Promise((resolve, reject) => {
        const requestId = headerWorkerRequestId + 1;
        headerWorkerRequestId = requestId;
        const worker = new Worker(new URL("./checklistHeader.worker.ts", import.meta.url), { type: "module" });
        const timer = window.setTimeout(() => {
            cleanup();
            worker.terminate();
            reject(new Error("表头检查超时，请重试"));
        }, HEADER_CHECK_TIMEOUT);

        const cleanup = () => {
            window.clearTimeout(timer);
            worker.removeEventListener("message", handleMessage);
            worker.removeEventListener("error", handleError);
        };

        const handleMessage = (event: MessageEvent<HeaderWorkerResponse>) => {
            if (event.data.id !== requestId) return;
            cleanup();
            worker.terminate();
            if (event.data.ok) {
                resolve(event.data.result);
                return;
            }
            reject(new Error(event.data.error || "表头检查失败"));
        };

        const handleError = () => {
            cleanup();
            worker.terminate();
            reject(new Error("表头检查失败"));
        };

        worker.addEventListener("message", handleMessage);
        worker.addEventListener("error", handleError);
        worker.postMessage({ id: requestId, buffer }, [buffer]);
    });
}

function clearAll() {
    items.value = [];
}

function removeItem(index: number) {
    items.value.splice(index, 1);
}

function loadOss() {
    if (!ossModulePromise) ossModulePromise = import("ali-oss");
    return ossModulePromise;
}

function toOssCredential(sts: OssStsCredential) {
    return { accessKeyId: sts.access_key_id, accessKeySecret: sts.access_key_secret, stsToken: sts.security_token };
}

async function createOssClient(sts: OssStsCredential, batchId: number) {
    const OSS = await loadOss();
    return new OSS.default({
        region: sts.region,
        bucket: sts.bucket,
        endpoint: sts.endpoint,
        ...toOssCredential(sts),
        secure: sts.endpoint.startsWith("https://"),
        timeout: 2 * 60 * 1000,
        refreshSTSToken: async () => toOssCredential(await getOssSts(batchId)),
        refreshSTSTokenInterval: 4 * 60 * 1000,
    });
}

function buildOssKey(sts: OssStsCredential, fileType: string, fileName: string) {
    return buildUploadOssKey(sts.oss_key_prefix, fileType, fileName);
}

async function createUploadContext(rows: UploadItem[]): Promise<UploadContext> {
    const batch = await createBatch({
        file_count: rows.length,
        total_bytes: rows.reduce((sum, row) => sum + row.file.size, 0),
        org_id: userStore.isSuperAdmin ? orgId.value : undefined,
        remark: "底表上传",
    });
    const sts = await getOssSts(batch.id);
    const ossClient = await createOssClient(sts, batch.id);
    return { batchId: batch.id, sts, ossClient };
}

function uploadErrorMessage(error: unknown) {
    if (error instanceof ApiBusinessError) return error.message;
    if (error && typeof error === "object" && "message" in error) {
        return String((error as { message?: string }).message || "上传失败");
    }
    return "上传失败";
}

async function submitAll() {
    if (userStore.isSuperAdmin && !orgId.value) {
        ElMessage.warning("请选择组织");
        return;
    }
    if (!readyItems.value.length) {
        ElMessage.warning("没有可提交的文件");
        return;
    }
    try {
        await ElMessageBox.confirm(`本次将提交 ${readyItems.value.length} 个对账清单处理任务。`, "确认提交", { type: "warning" });
    } catch {
        return;
    }
    uploading.value = true;
    uploadingFileName.value = "";
    uploadDialogDone.value = 0;
    uploadDialogTotal.value = readyItems.value.length;
    try {
        const context = await createUploadContext(readyItems.value);
        for (const item of readyItems.value) {
            await uploadOne(item, context);
        }
    } finally {
        uploading.value = false;
        uploadingFileName.value = "";
    }
}

async function submitOne(item: UploadItem) {
    if (userStore.isSuperAdmin && !orgId.value) {
        ElMessage.warning("请选择组织");
        return;
    }
    uploading.value = true;
    uploadingFileName.value = "";
    uploadDialogDone.value = 0;
    uploadDialogTotal.value = 1;
    try {
        const context = await createUploadContext([item]);
        await uploadOne(item, context);
    } finally {
        uploading.value = false;
        uploadingFileName.value = "";
    }
}

async function uploadOne(item: UploadItem, context: UploadContext) {
    uploadingFileName.value = item.name;
    patchItem(item, { status: "uploading", progress: 0, error: "" });
    try {
        const ossKey = buildOssKey(context.sts, item.fileType || CHECKLIST_FILE_TYPE, item.file.name);
        await context.ossClient.multipartUpload(ossKey, item.file, {
            timeout: 2 * 60 * 1000,
            partSize: 1024 * 1024,
            parallel: 2,
            progress: async (percent: number) => {
                patchItem(item, { progress: Math.round(percent * 100) });
            },
        });
        await uploadCallback({
            batch_id: context.batchId,
            original_name: item.file.name,
            oss_key: ossKey,
            file_size: item.file.size,
            parsed_type: item.fileType || CHECKLIST_FILE_TYPE,
            parsed_shop: "",
            detected_platform: "",
        });
        patchItem(item, { status: "success", progress: 100, message: "已提交处理任务" });
        ElMessage.success(`${item.name} 已提交处理任务`);
    } catch (error) {
        patchItem(item, { status: "error", message: "提交失败", error: uploadErrorMessage(error) });
    } finally {
        uploadDialogDone.value += 1;
    }
}

onMounted(fetchOrgs);
</script>

<style scoped lang="scss">
.upload-shell {
    display: grid;
    gap: 16px;
}

.upload-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 16px;
}

.upload-workspace {
    display: grid;
    gap: 16px;
}

.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;

    h2 {
        margin: 0 0 4px;
        color: var(--text-primary);
        font-size: 26px;
        line-height: 1.2;
    }

    p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 13px;
    }
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

.header-hint {
    color: var(--text-tertiary);
    font-size: 12px;
}

.target-org-card,
.upload-card,
.file-list-card {
    border-radius: var(--radius-card);
}

.upload-steps {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    overflow: hidden;
    background: var(--bg-card);
}

.upload-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    border-right: 1px solid var(--border-color-light);
    color: var(--text-secondary);

    &:last-child {
        border-right: 0;
    }

    strong {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--bg-hover);
        color: var(--text-primary);
        font-size: 14px;
    }

    span {
        font-size: 14px;
        font-weight: 600;
    }

    &.is-active {
        color: var(--text-primary);
        background: var(--bg-elevated);

        strong {
            background: var(--primary-light-5);
            color: var(--primary);
        }
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

.file-list-card {
    :deep(.el-card__body) {
        padding: 0;
    }
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
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

.status-pill--error {
    background: var(--error-light);
    color: var(--error);
}

.upload-error-text {
    margin-top: 6px;
    color: var(--el-color-danger);
    font-size: 12px;
    line-height: 18px;
}

.upload-row-progress {
    margin-top: 6px;
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

@media (max-width: 768px) {
    .page-header {
        align-items: stretch;
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

    .card-header {
        align-items: flex-start;
        flex-direction: column;
    }
}
</style>
