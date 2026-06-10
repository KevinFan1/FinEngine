<template>
    <div class="page-container checklist-page manual-edit-page">
        <el-card
            shadow="never"
            class="search-card checklist-filter-card manual-edit-filter-card"
        >
            <template #header>
                <div class="manual-edit-filter-head">
                    <span class="card-header-title">商家修改</span>
                </div>
            </template>

            <el-form
                :model="form"
                label-position="top"
                class="manual-edit-filter-form"
                @submit.prevent
            >
                <div
                    class="manual-edit-filter-grid"
                    :class="{
                        'manual-edit-filter-grid--superadmin': userStore.isSuperAdmin,
                    }"
                >
                    <el-form-item
                        v-if="userStore.isSuperAdmin"
                        label="组织"
                        class="filter-field manual-edit-filter-org"
                    >
                        <el-select
                            v-model="form.org_id"
                            clearable
                            filterable
                            :loading="orgLoading"
                            placeholder="请选择组织"
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
                        label="子订单号"
                        class="filter-field manual-edit-filter-draft"
                    >
                        <div class="manual-edit-filter-draft-layout">
                            <el-input
                                v-model="form.draft"
                                type="textarea"
                                :rows="3"
                                resize="vertical"
                                placeholder="支持换行、英文逗号、中文逗号分隔子订单号"
                            />
                            <div class="manual-edit-filter-actions">
                                <el-button
                                    type="primary"
                                    :loading="loading"
                                    :disabled="queryDisabled"
                                    @click="handleQuery"
                                >
                                    查询
                                </el-button>
                                <el-button @click="handleReset">重置</el-button>
                            </div>
                            <div class="manual-edit-filter-meta">
                                <span
                                    >已识别
                                    {{ parsedSubOrders.length }} 个子订单号</span
                                >
                                <span
                                    >单次最多
                                    {{ MANUAL_EDIT_MAX_SUB_ORDERS }} 个</span
                                >
                            </div>
                        </div>
                    </el-form-item>
                </div>
            </el-form>
        </el-card>

        <el-alert
            v-if="parsedSubOrders.length > MANUAL_EDIT_MAX_SUB_ORDERS"
            :title="manualEditLimitMessage(parsedSubOrders.length)"
            type="warning"
            show-icon
            :closable="false"
            class="manual-edit-alert"
        />

        <el-alert
            v-if="missingSubOrderNos.length"
            :title="`未命中子订单号：${missingSubOrderNos.join('，')}`"
            type="warning"
            show-icon
            :closable="false"
            class="manual-edit-alert"
        />

        <el-card shadow="never" class="table-card manual-edit-table-card">
            <template #header>
                <div class="manual-edit-table-head">
                    <div class="summary-title-group">
                        <span class="card-header-title"
                            >商家修改命中 {{ matchedItems.length }} 条</span
                        >
                    </div>
                    <div class="manual-edit-toolbar">
                        <input
                            ref="fileInputRef"
                            type="file"
                            accept=".xlsx,.xlsm"
                            class="manual-edit-file-input"
                            @change="handleImportFileChange"
                        />
                        <el-button @click="triggerImport">
                            上传修改文件
                        </el-button>
                        <el-button
                            :disabled="matchedItems.length === 0"
                            @click="handleExport"
                        >
                            导出当前结果
                        </el-button>
                        <el-button
                            type="primary"
                            :loading="saving"
                            :disabled="saveDisabled"
                            @click="handleSave"
                        >
                            保存
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                v-loading="loading"
                :data="matchedItems"
                border
                stripe
                row-key="unique_id"
                class="summary-table manual-edit-table manual-edit-table--dense"
                style="width: 100%"
            >
                <template #empty>
                    <el-empty
                        description="请先输入子订单号并查询"
                        class="manual-edit-empty"
                    />
                </template>
                <el-table-column
                    label="序号"
                    width="62"
                    align="center"
                    fixed="left"
                >
                    <template #default="{ $index }">
                        {{ rowIndex($index) }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="sub_order_no"
                    label="子订单号"
                    min-width="180"
                    fixed="left"
                    show-overflow-tooltip
                />
                <el-table-column
                    label="结算时间"
                    min-width="152"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        {{ formatRawDateTime(row.settlement_time) }}
                    </template>
                </el-table-column>
                <el-table-column
                    v-for="column in amountColumns"
                    :key="column.key"
                    :prop="column.key"
                    :label="column.shortLabel"
                    :width="column.width"
                    align="right"
                >
                    <template #header>
                        <el-tooltip :content="column.label" placement="top">
                            <span class="manual-edit-compact-label">{{
                                column.shortLabel
                            }}</span>
                        </el-tooltip>
                    </template>
                </el-table-column>
                <el-table-column label="收款商家" min-width="240">
                    <template #default="{ row }">
                        <el-input
                            v-model="row.receipt_merchant"
                            placeholder="请输入收款商家"
                        />
                    </template>
                </el-table-column>
                <el-table-column label="应付商家净额" min-width="170">
                    <template #default="{ row }">
                        <el-input
                            v-model="row.merchant_net_amount"
                            placeholder="留空表示清空"
                        />
                    </template>
                </el-table-column>
                <el-table-column label="付款金额" min-width="170">
                    <template #default="{ row }">
                        <el-input
                            v-model="row.payment_amount"
                            placeholder="留空表示清空"
                        />
                    </template>
                </el-table-column>
                <el-table-column label="付款时间（商家）" width="220">
                    <template #default="{ row }">
                        <el-date-picker
                            v-model="row.merchant_payment_time"
                            type="datetime"
                            value-format="YYYY-MM-DD HH:mm:ss"
                            placeholder="请选择付款时间"
                            clearable
                        />
                    </template>
                </el-table-column>
            </el-table>
        </el-card>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    callbackReconciliationChecklistMerchantEditsUpload,
    queryReconciliationChecklistMerchantEdits,
    saveReconciliationChecklistMerchantEdits,
    uploadReconciliationChecklistMerchantEdits,
    type ReconciliationChecklistManualEditOssCredential,
    type ReconciliationChecklistMerchantEditItem,
} from "@/api/reconciliationChecklist";
import { useUserStore } from "@/stores/user";
import { formatRawDateTime } from "@/utils/format";
import { CHECKLIST_FILE_TYPE_MERCHANT } from "./common";
import {
    MANUAL_EDIT_AMOUNT_COLUMNS,
    MANUAL_EDIT_MAX_SUB_ORDERS,
    MANUAL_EDIT_STATE_KEYS,
    manualEditLimitMessage,
    parseManualEditSubOrders,
    validateManualEditUploadHeaders,
} from "./manualEdits";
import {
    exportManualEditWorkbook,
    type MerchantWorkbookRow,
} from "./manualEditWorkbook";

defineOptions({ name: "ReconciliationChecklistMerchantEdits" });

type MerchantEditPageState = {
    draft?: string;
    org_id?: number | null;
    matched_items?: ReconciliationChecklistMerchantEditItem[];
    missing_sub_order_nos?: string[];
};

const amountColumns = MANUAL_EDIT_AMOUNT_COLUMNS;
const MISSING_UNIQUE_ID_MESSAGE = "部分数据缺少唯一ID，请重新查询后再保存";
const OSS_REQUEST_TIMEOUT = 2 * 60 * 1000;
const OSS_MULTIPART_PART_SIZE = 1024 * 1024;
const OSS_MULTIPART_PARALLEL = 2;
const userStore = useUserStore();
const fileInputRef = ref<HTMLInputElement | null>(null);
const orgLoading = ref(false);
const loading = ref(false);
const saving = ref(false);
const importing = ref(false);
const orgOptions = ref<Organization[]>([]);
const matchedItems = ref<MerchantWorkbookRow[]>([]);
const missingSubOrderNos = ref<string[]>([]);
const form = reactive({
    draft: "",
    org_id: undefined as number | undefined,
});
let ossModulePromise: Promise<typeof import("ali-oss")> | null = null;

const parsedSubOrders = computed(() => parseManualEditSubOrders(form.draft));
const queryDisabled = computed(
    () =>
        loading.value ||
        saving.value ||
        importing.value ||
        parsedSubOrders.value.length === 0 ||
        parsedSubOrders.value.length > MANUAL_EDIT_MAX_SUB_ORDERS,
);
const saveDisabled = computed(
    () =>
        loading.value ||
        saving.value ||
        importing.value ||
        parsedSubOrders.value.length === 0 ||
        parsedSubOrders.value.length > MANUAL_EDIT_MAX_SUB_ORDERS ||
        matchedItems.value.length === 0,
);

function rowIndex(index: number) {
    return index + 1;
}

function currentOrgId() {
    if (userStore.isSuperAdmin) return form.org_id;
    return userStore.userInfo?.org_id ?? form.org_id;
}

function ensureDefaultOrgId() {
    if (!userStore.isSuperAdmin) {
        form.org_id = userStore.userInfo?.org_id ?? undefined;
    }
}

function toEditableAmount(value: unknown) {
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return "";
    return String(value);
}

function normalizeNullableAmount(value: string | null | undefined) {
    const text = String(value || "").trim();
    return text ? text : null;
}

function toMerchantRow(item: Partial<MerchantWorkbookRow>) {
    const row: MerchantWorkbookRow = {
        unique_id: typeof item?.unique_id === "string" ? item.unique_id : "",
        sub_order_no:
            typeof item?.sub_order_no === "string" ? item.sub_order_no : "",
        settlement_time:
            typeof item?.settlement_time === "string"
                ? item.settlement_time
                : null,
        receipt_merchant:
            typeof item?.receipt_merchant === "string"
                ? item.receipt_merchant
                : "",
        merchant_net_amount: toEditableAmount(item?.merchant_net_amount),
        payment_amount: toEditableAmount(item?.payment_amount),
        merchant_payment_time:
            typeof item?.merchant_payment_time === "string"
                ? item.merchant_payment_time
                : null,
    };
    for (const column of amountColumns) {
        row[column.key] =
            typeof item?.[column.key] === "string"
                ? item[column.key]
                : item?.[column.key] === null ||
                    item?.[column.key] === undefined
                  ? null
                  : String(item[column.key]);
    }
    return row;
}

function persistPageState() {
    const state: MerchantEditPageState = {
        draft: form.draft,
        org_id: form.org_id ?? null,
        matched_items: matchedItems.value,
        missing_sub_order_nos: missingSubOrderNos.value,
    };
    sessionStorage.setItem(
        MANUAL_EDIT_STATE_KEYS.merchant,
        JSON.stringify(state),
    );
}

function restorePageState() {
    const raw = sessionStorage.getItem(MANUAL_EDIT_STATE_KEYS.merchant);
    if (!raw) {
        ensureDefaultOrgId();
        return;
    }
    try {
        const state = JSON.parse(raw) as MerchantEditPageState;
        form.draft = typeof state.draft === "string" ? state.draft : "";
        form.org_id =
            typeof state.org_id === "number" ? state.org_id : undefined;
        matchedItems.value = Array.isArray(state.matched_items)
            ? state.matched_items
                  .map((item) => toMerchantRow(item))
                  .filter((item) => item.sub_order_no && item.unique_id)
            : [];
        missingSubOrderNos.value = Array.isArray(state.missing_sub_order_nos)
            ? state.missing_sub_order_nos.filter(
                  (item): item is string =>
                      typeof item === "string" && item.length > 0,
              )
            : [];
    } catch {
        form.draft = "";
        form.org_id = undefined;
        matchedItems.value = [];
        missingSubOrderNos.value = [];
    }
    ensureDefaultOrgId();
}

function hasMissingUniqueId() {
    return matchedItems.value.some((item) => !item.unique_id);
}

function validateBeforeSubmit(action: "query" | "save") {
    if (parsedSubOrders.value.length === 0) {
        ElMessage.warning("请先输入子订单号");
        return false;
    }
    if (parsedSubOrders.value.length > MANUAL_EDIT_MAX_SUB_ORDERS) {
        ElMessage.warning(manualEditLimitMessage(parsedSubOrders.value.length));
        return false;
    }
    if (!currentOrgId()) {
        ElMessage.warning("请选择组织");
        return false;
    }
    if (action === "save" && matchedItems.value.length === 0) {
        ElMessage.warning("暂无可保存的命中记录");
        return false;
    }
    if (action === "save" && hasMissingUniqueId()) {
        ElMessage.warning(MISSING_UNIQUE_ID_MESSAGE);
        return false;
    }
    return true;
}

async function fetchOrganizations() {
    if (!userStore.isSuperAdmin) return;
    orgLoading.value = true;
    try {
        orgOptions.value = await getAllOrganizations();
    } finally {
        orgLoading.value = false;
    }
}

async function handleQuery() {
    if (!validateBeforeSubmit("query")) return;
    loading.value = true;
    try {
        const result = await queryReconciliationChecklistMerchantEdits({
            org_id: currentOrgId() as number,
            sub_order_nos: parsedSubOrders.value,
        });
        matchedItems.value = result.matched_items.map((item) =>
            toMerchantRow(item),
        );
        missingSubOrderNos.value = result.missing_sub_order_nos;
        persistPageState();
        ElMessage.success(`查询完成，命中 ${matchedItems.value.length} 条`);
    } catch (error) {
        if (!isApiMessageShown(error)) {
            ElMessage.error("查询失败，请稍后重试");
        }
    } finally {
        loading.value = false;
    }
}

async function handleSave() {
    if (!validateBeforeSubmit("save")) return;
    saving.value = true;
    try {
        const result = await saveReconciliationChecklistMerchantEdits({
            org_id: currentOrgId() as number,
            items: matchedItems.value.map((item) => ({
                unique_id: item.unique_id || "",
                sub_order_no: item.sub_order_no,
                receipt_merchant: item.receipt_merchant.trim(),
                merchant_net_amount: normalizeNullableAmount(
                    item.merchant_net_amount,
                ),
                payment_amount: normalizeNullableAmount(item.payment_amount),
                merchant_payment_time: item.merchant_payment_time || null,
            })),
        });
        missingSubOrderNos.value = result.missing_sub_order_nos;
        persistPageState();
        if (result.success_count > 0) {
            ElMessage.success(`保存成功，成功 ${result.success_count} 条`);
        } else if (result.unchanged_count > 0 && result.failed_count === 0) {
            ElMessage.warning(
                `未保存新内容：${result.unchanged_count} 条记录未发生实际变更`,
            );
        } else {
            ElMessage.warning(
                result.error_messages[0] ||
                    `保存结果：成功 ${result.success_count} 条，失败 ${result.failed_count} 条，未变更 ${result.unchanged_count} 条`,
            );
        }
    } catch (error) {
        if (!isApiMessageShown(error)) {
            ElMessage.error("保存失败，请稍后重试");
        }
    } finally {
        saving.value = false;
    }
}

async function handleExport() {
    if (matchedItems.value.length === 0) {
        ElMessage.warning("请先查询数据后再导出");
        return;
    }
    await exportManualEditWorkbook("merchant", matchedItems.value);
}

function triggerImport() {
    fileInputRef.value?.click();
}

function buildOssKey(sts: ReconciliationChecklistManualEditOssCredential, fileName: string): string {
    return `${sts.oss_key_prefix}${Date.now()}_${fileName.replace(/[\\/]/g, "_")}`;
}

function loadOss() {
    if (!ossModulePromise) ossModulePromise = import("ali-oss");
    return ossModulePromise;
}

async function createOssClient(sts: ReconciliationChecklistManualEditOssCredential) {
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

async function uploadFileToOss(ossClient: any, ossKey: string, file: File) {
    await ossClient.multipartUpload(ossKey, file, {
        timeout: OSS_REQUEST_TIMEOUT,
        partSize: OSS_MULTIPART_PART_SIZE,
        parallel: OSS_MULTIPART_PARALLEL,
    });
}

async function handleImportFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = "";
    if (!file) return;
    importing.value = true;
    try {
        await validateManualEditUploadHeaders(file, CHECKLIST_FILE_TYPE_MERCHANT);
        const init = await uploadReconciliationChecklistMerchantEdits({
            org_id: currentOrgId() as number,
            original_name: file.name,
            file_size: file.size,
        });
        const ossKey = buildOssKey(init.upload, file.name);
        const ossClient = await createOssClient(init.upload);
        await uploadFileToOss(ossClient, ossKey, file);
        const task = await callbackReconciliationChecklistMerchantEditsUpload({
            file_id: init.upload.file_id,
            oss_key: ossKey,
            file_size: file.size,
        });
        await ElMessageBox.alert(
            `商家修改文件已成功上传，任务 #${task.task_id} 将由任务中心继续处理。`,
            "上传成功",
            {
                confirmButtonText: "知道了",
                type: "success",
            },
        );
    } catch (error) {
        if (!isApiMessageShown(error)) {
            ElMessage.error(
                (error as Error)?.message || "上传失败，请检查模板后重试",
            );
        }
    } finally {
        importing.value = false;
    }
}

function handleReset() {
    form.draft = "";
    form.org_id = userStore.isSuperAdmin
        ? undefined
        : (userStore.userInfo?.org_id ?? undefined);
    matchedItems.value = [];
    missingSubOrderNos.value = [];
    persistPageState();
}

function isApiMessageShown(error: unknown): boolean {
    return Boolean(
        error &&
        typeof error === "object" &&
        (error as { __apiMessageShown?: boolean }).__apiMessageShown,
    );
}

watch(
    [() => form.draft, () => form.org_id, matchedItems, missingSubOrderNos],
    () => {
        persistPageState();
    },
    { deep: true },
);

onMounted(async () => {
    restorePageState();
    await fetchOrganizations();
    persistPageState();
});
</script>

<style scoped>
.manual-edit-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.manual-edit-filter-head {
    display: flex;
    align-items: center;
}

.manual-edit-filter-form {
    min-width: 0;
}

.manual-edit-filter-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: "draft";
    gap: 12px;
    align-items: start;
}

.manual-edit-filter-grid--superadmin {
    grid-template-columns: 220px minmax(0, 1fr);
    grid-template-areas: "org draft";
}

.manual-edit-filter-org {
    grid-area: org;
}

.manual-edit-filter-draft {
    grid-area: draft;
    margin-bottom: 0;
}

.manual-edit-filter-draft-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
        "textarea actions"
        "meta .";
    gap: 6px 14px;
    align-items: end;
}

.manual-edit-filter-draft-layout :deep(.el-textarea) {
    grid-area: textarea;
}

.manual-edit-filter-form :deep(.el-form-item) {
    margin-bottom: 0;
}

.manual-edit-filter-form :deep(.el-form-item__label) {
    padding-bottom: 4px;
    line-height: 1.2;
    font-size: 12px;
    color: var(--text-secondary);
}

.manual-edit-filter-form :deep(.el-input__wrapper),
.manual-edit-filter-form :deep(.el-textarea__inner),
.manual-edit-filter-form :deep(.el-select__wrapper) {
    border-radius: 8px;
}

.manual-edit-filter-form :deep(.el-input__wrapper),
.manual-edit-filter-form :deep(.el-select__wrapper) {
    min-height: 34px;
}

.manual-edit-filter-form :deep(.el-textarea__inner) {
    min-height: 88px;
    padding-top: 7px;
    padding-bottom: 7px;
    line-height: 1.45;
}

.manual-edit-filter-meta {
    grid-area: meta;
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-size: 11px;
    color: var(--text-secondary);
}

.manual-edit-filter-actions {
    display: flex;
    grid-area: actions;
    align-self: end;
    justify-self: end;
    gap: 8px;
    white-space: nowrap;
}

.manual-edit-alert :deep(.el-alert) {
    padding-top: 8px;
    padding-bottom: 8px;
}

.manual-edit-table-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.manual-edit-head-note {
    font-size: 12px;
    color: var(--text-secondary);
}

.manual-edit-toolbar {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
}

.manual-edit-file-input {
    display: none;
}

.manual-edit-table :deep(.el-table__cell) {
    padding-top: 5px;
    padding-bottom: 5px;
}

.manual-edit-table :deep(.cell) {
    line-height: 1.3;
}

.manual-edit-table :deep(.el-input__wrapper),
.manual-edit-table :deep(.el-date-editor.el-input__wrapper) {
    min-height: 28px;
    border-radius: 8px;
}

.manual-edit-table :deep(.el-input__inner) {
    font-size: 12px;
}

.manual-edit-table--dense :deep(th.el-table__cell) {
    padding-top: 7px;
    padding-bottom: 7px;
}

.manual-edit-compact-label {
    display: inline-flex;
    align-items: center;
    justify-content: flex-end;
    width: 100%;
}

.manual-edit-empty {
    padding: 12px 0 2px;
}

.manual-edit-table-card {
    min-width: 0;
}

@media (max-width: 960px) {
    .manual-edit-filter-grid {
        grid-template-columns: 1fr;
        grid-template-areas: "draft";
    }

    .manual-edit-filter-grid--superadmin {
        grid-template-areas:
            "org"
            "draft";
    }

    .manual-edit-filter-draft-layout {
        grid-template-columns: 1fr;
        grid-template-areas:
            "textarea"
            "meta"
            "actions";
    }

    .manual-edit-filter-meta {
        flex-direction: column;
        align-items: flex-start;
    }

    .manual-edit-table-head {
        flex-direction: column;
        align-items: flex-start;
    }

    .manual-edit-filter-actions,
    .manual-edit-toolbar {
        width: 100%;
        justify-content: flex-start;
        padding-bottom: 0;
    }
}
</style>
