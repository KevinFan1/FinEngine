<template>
    <div class="page-container page-container--flow file-spec-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" class="spec-filter-form">
                <div class="spec-filter-grid">
                    <el-form-item label="平台">
                    <el-select v-model="searchForm.platformId" clearable filterable placeholder="平台">
                        <el-option v-for="platform in platformOptions" :key="platform.id" :label="platform.name" :value="platform.id">
                            <PlatformBadge :platform="platform.code || platform.name" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="业务类型">
                    <el-select v-model="searchForm.typeCode" clearable filterable allow-create default-first-option placeholder="业务类型">
                        <el-option v-for="item in typeCodeOptions" :key="item" :label="item" :value="item" />
                    </el-select>
                </el-form-item>
                <el-form-item label="状态">
                    <el-select v-model="searchForm.status" clearable placeholder="状态">
                        <el-option label="启用" :value="1" />
                        <el-option label="禁用" :value="0" />
                    </el-select>
                </el-form-item>
                <el-form-item label="关键词">
                    <el-input v-model="searchForm.keyword" clearable placeholder="名称、类型、所属时间列" @keyup.enter="handleSearch" />
                </el-form-item>
                    <div class="spec-filter-actions">
                        <el-button type="primary" @click="handleSearch">搜索</el-button>
                        <el-button @click="handleReset">重置</el-button>
                    </div>
                </div>
            </el-form>
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div>
                        <span class="card-header-title">规格列表</span>
                        <span class="spec-count">共 {{ pagination.total }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button @click="fetchData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                        <el-button type="primary" @click="handleAdd">
                            <el-icon><Plus /></el-icon>
                            新增规格
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table v-loading="loading" :data="tableData" stripe border class="summary-table roomy-table" style="width: 100%">
                <el-table-column label="序号" width="70" align="center">
                    <template #default="{ $index }">
                        {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
                    </template>
                </el-table-column>
                <el-table-column label="平台" width="130">
                    <template #default="{ row }">
                        <PlatformBadge :platform="row.platform_code || row.platform_name || String(row.platform_id)" />
                    </template>
                </el-table-column>
                <el-table-column prop="type_code" label="业务类型" width="120" />
                <el-table-column prop="name" label="规格名称" min-width="170" show-overflow-tooltip />
                <el-table-column label="表头数量" width="90" align="right">
                    <template #default="{ row }">{{ row.headers?.length || 0 }}</template>
                </el-table-column>
                <el-table-column prop="match_threshold" label="匹配阈值" width="100" align="right" />
                <el-table-column prop="upload_period_header" label="所属时间列" min-width="150" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.upload_period_header || "-" }}</template>
                </el-table-column>
                <el-table-column label="表头预览" min-width="260" show-overflow-tooltip>
                    <template #default="{ row }">{{ headerPreview(row.headers) }}</template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="90" align="center">
                    <template #default="{ row }">
                        <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                            {{ row.status === 1 ? "启用" : "禁用" }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="更新时间" width="170">
                    <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="150" fixed="right" align="center">
                    <template #default="{ row }">
                        <el-button type="primary" link @click="handleEdit(row)">编辑</el-button>
                        <el-button type="danger" link @click="handleDelete(row)">删除</el-button>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty description="暂无文件规格" :image-size="80" />
                </template>
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

        <el-drawer v-model="drawerVisible" :title="editId ? '编辑文件规格' : '新增文件规格'" size="640px">
            <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="spec-form">
                <el-form-item label="平台" prop="platform_id">
                    <el-select v-model="form.platform_id" filterable placeholder="选择平台" style="width: 100%">
                        <el-option v-for="platform in platformOptions" :key="platform.id" :label="platform.name" :value="platform.id">
                            <PlatformBadge :platform="platform.code || platform.name" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="业务类型" prop="type_code">
                    <el-select v-model="form.type_code" filterable allow-create default-first-option placeholder="业务类型" style="width: 100%">
                        <el-option v-for="item in typeCodeOptions" :key="item" :label="item" :value="item" />
                    </el-select>
                </el-form-item>
                <el-form-item label="规格名称" prop="name">
                    <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="如：抖音动账" />
                </el-form-item>
                <el-form-item label="匹配阈值" prop="match_threshold">
                    <el-input-number v-model="form.match_threshold" :min="1" :max="200" controls-position="right" />
                </el-form-item>
                <el-form-item label="所属时间列" prop="upload_period_header">
                    <el-input v-model="form.upload_period_header" clearable maxlength="100" placeholder="如：动账时间、结算时间、订单创建时间" />
                </el-form-item>
                <el-form-item label="状态" prop="status">
                    <el-radio-group v-model="form.status">
                        <el-radio-button :label="1">启用</el-radio-button>
                        <el-radio-button :label="0">禁用</el-radio-button>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="表头列表" prop="headerItems">
                    <div class="header-editor">
                        <div
                            v-for="(item, index) in form.headerItems"
                            :key="item.key"
                            class="header-editor-row"
                        >
                            <span class="header-editor-index">{{ index + 1 }}</span>
                            <el-input
                                v-model="item.value"
                                clearable
                                maxlength="100"
                                :placeholder="`表头 ${index + 1}`"
                            />
                            <el-tooltip content="删除表头" placement="top">
                                <el-button
                                    :icon="Delete"
                                    circle
                                    :disabled="form.headerItems.length <= 1"
                                    @click="removeHeaderItem(index)"
                                />
                            </el-tooltip>
                        </div>
                        <div class="header-editor-actions">
                            <el-button @click="addHeaderItem">
                                <el-icon><Plus /></el-icon>
                                新增表头
                            </el-button>
                        </div>
                    </div>
                </el-form-item>
            </el-form>
            <template #footer>
                <div class="drawer-footer">
                    <el-button @click="drawerVisible = false">取消</el-button>
                    <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
                </div>
            </template>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "FileSpecs" });

import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from "element-plus";
import { Delete, Plus, Refresh } from "@element-plus/icons-vue";
import {
    createFileSpec,
    deleteFileSpec,
    getFileSpecsAdmin,
    type FileSpec,
    type FileSpecPayload,
    updateFileSpec,
} from "@/api/file_spec";
import { getPlatformList, type Platform } from "@/api/platform";
import PlatformBadge from "@/components/PlatformBadge.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import { formatDateTime } from "@/utils/format";
import { getFallbackPlatforms } from "@/utils/platform";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";

interface FileSpecForm {
    platform_id: number | null;
    type_code: string;
    name: string;
    match_threshold: number;
    upload_period_header: string;
    status: number;
    headerItems: HeaderItem[];
}

interface HeaderItem {
    key: number;
    value: string;
}

const loading = ref(false);
const submitting = ref(false);
const drawerVisible = ref(false);
const editId = ref<number | null>(null);
const tableData = ref<FileSpec[]>([]);
const platforms = ref<Platform[]>([]);
const formRef = ref<FormInstance>();

const searchForm = reactive({
    platformId: undefined as number | undefined,
    typeCode: "",
    status: undefined as number | undefined,
    keyword: "",
});

const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

const form = reactive<FileSpecForm>({
    platform_id: null,
    type_code: "动账",
    name: "",
    match_threshold: 5,
    upload_period_header: "",
    status: 1,
    headerItems: [],
});
let headerItemSeed = 0;

const typeCodeOptions = ["订单", "动账", "gmv", "bic", "运费险", "其他服务款"];

const platformOptions = computed(() => platforms.value);

const rules: FormRules = {
    platform_id: [{ required: true, message: "请选择平台", trigger: "change" }],
    type_code: [{ required: true, message: "请输入业务类型", trigger: "blur" }],
    name: [{ required: true, message: "请输入规格名称", trigger: "blur" }],
    match_threshold: [{ required: true, message: "请输入匹配阈值", trigger: "change" }],
    headerItems: [
        {
            validator: (_rule, value: HeaderItem[], callback) => {
                try {
                    normalizeHeaders((value || []).map((item) => item.value));
                    callback();
                } catch (error: any) {
                    callback(new Error(error?.message || "请输入表头列表"));
                }
            },
            trigger: "blur",
        },
    ],
};

function headerPreview(headers: string[]) {
    const values = (headers || []).filter(Boolean);
    if (!values.length) return "-";
    const preview = values.slice(0, 6).join("、");
    return values.length > 6 ? `${preview}...` : preview;
}

function normalizeHeaders(values: string[]) {
    const headers: string[] = [];
    values.forEach((item) => {
        const value = item.trim();
        if (!value) return;
        if (headers.includes(value)) {
            throw new Error(`表头「${value}」重复`);
        }
        headers.push(value);
    });
    if (!headers.length) throw new Error("表头列表不能为空");
    return headers;
}

function createHeaderItem(value = ""): HeaderItem {
    headerItemSeed += 1;
    return { key: headerItemSeed, value };
}

function headersToItems(headers: string[]) {
    const values = (headers || []).filter(Boolean);
    return (values.length ? values : [""]).map((value) => createHeaderItem(value));
}

function addHeaderItem() {
    form.headerItems.push(createHeaderItem());
}

function removeHeaderItem(index: number) {
    if (form.headerItems.length <= 1) return;
    form.headerItems.splice(index, 1);
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
}

async function fetchData() {
    loading.value = true;
    try {
        const res = await getFileSpecsAdmin({
            page: pagination.page,
            page_size: pagination.pageSize,
            platform_id: searchForm.platformId,
            type_code: searchForm.typeCode || undefined,
            status: searchForm.status,
            keyword: searchForm.keyword.trim() || undefined,
        });
        tableData.value = res.items || [];
        pagination.total = res.total || 0;
    } catch {
        // Error handled by interceptor.
    } finally {
        loading.value = false;
    }
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.platformId = undefined;
    searchForm.typeCode = "";
    searchForm.status = undefined;
    searchForm.keyword = "";
    handleSearch();
}

function resetForm() {
    form.platform_id = platformOptions.value[0]?.id || null;
    form.type_code = "动账";
    form.name = "";
    form.match_threshold = 5;
    form.upload_period_header = "";
    form.status = 1;
    form.headerItems = [createHeaderItem()];
    editId.value = null;
    formRef.value?.clearValidate();
}

function handleAdd() {
    resetForm();
    drawerVisible.value = true;
}

function handleEdit(row: FileSpec) {
    editId.value = row.id;
    form.platform_id = row.platform_id;
    form.type_code = row.type_code;
    form.name = row.name;
    form.match_threshold = row.match_threshold;
    form.upload_period_header = row.upload_period_header || "";
    form.status = row.status;
    form.headerItems = headersToItems(row.headers);
    drawerVisible.value = true;
    formRef.value?.clearValidate();
}

async function handleSubmit() {
    const valid = await formRef.value?.validate().catch(() => false);
    if (!valid || !form.platform_id) return;

    let headers: string[];
    try {
        headers = normalizeHeaders(form.headerItems.map((item) => item.value));
    } catch (error: any) {
        ElMessage.error(error?.message || "表头格式不正确");
        return;
    }

    const payload: FileSpecPayload = {
        platform_id: form.platform_id,
        type_code: form.type_code.trim(),
        name: form.name.trim(),
        headers,
        match_threshold: form.match_threshold,
        upload_period_header: form.upload_period_header.trim() || null,
        status: form.status,
    };

    submitting.value = true;
    try {
        if (editId.value) {
            await updateFileSpec(editId.value, payload);
            ElMessage.success("更新成功");
        } else {
            await createFileSpec(payload);
            ElMessage.success("创建成功");
        }
        drawerVisible.value = false;
        await fetchData();
    } catch {
        // Error handled by interceptor.
    } finally {
        submitting.value = false;
    }
}

async function handleDelete(row: FileSpec) {
    try {
        await ElMessageBox.confirm(
            `确定要删除文件规格「${row.name}」吗？删除后上传识别不会再使用该规格。`,
            "操作确认",
            {
                type: "warning",
                confirmButtonText: "确定",
                cancelButtonText: "取消",
            },
        );
        await deleteFileSpec(row.id);
        ElMessage.success("删除成功");
        await fetchData();
    } catch {
        // Cancelled or error.
    }
}

onMounted(async () => {
    await fetchPlatformOptions();
    await fetchData();
});

usePageRefresh(async () => {
    await fetchPlatformOptions();
    await fetchData();
});
</script>

<style scoped lang="scss">
.file-spec-page {
    .search-card,
    .table-card {
        border-radius: 8px;
    }
}

.spec-filter-form {
    :deep(.el-form-item) {
        margin: 0;
    }

    :deep(.el-form-item__content) {
        min-width: 0;
    }

    :deep(.el-select),
    :deep(.el-input) {
        width: 100%;
    }
}

.spec-filter-grid {
    display: grid;
    grid-template-columns:
        minmax(170px, 220px)
        minmax(150px, 190px)
        minmax(120px, 150px)
        minmax(220px, 1fr)
        auto;
    align-items: end;
    gap: 12px;
}

.spec-filter-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    min-width: 156px;
}

.card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.card-header-title {
    font-weight: 700;
}

.spec-count {
    margin-left: 10px;
    color: var(--text-tertiary);
    font-size: 13px;
}

.card-header-actions {
    display: flex;
    gap: 10px;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
}

.spec-form {
    padding-right: 8px;
}

.header-editor {
    display: flex;
    flex-direction: column;
    gap: 10px;
    width: 100%;
}

.header-editor-row {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr) 36px;
    align-items: center;
    gap: 8px;
}

.header-editor-index {
    color: var(--text-tertiary);
    font-size: 13px;
    text-align: right;
}

.header-editor-actions {
    display: flex;
    justify-content: flex-start;
}

.drawer-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}

@media (max-width: 768px) {
    .spec-filter-grid {
        grid-template-columns: 1fr;
    }

    .spec-filter-actions {
        justify-content: flex-start;
    }

    .card-header {
        align-items: flex-start;
        flex-direction: column;
    }
}
</style>
