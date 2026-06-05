<template>
    <div class="page-container transaction-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="业务年月">
                    <el-date-picker
                        v-model="searchForm.businessMonthRange"
                        type="monthrange"
                        start-placeholder="业务年月起"
                        end-placeholder="业务年月止"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 260px"
                    />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select
                        v-model="searchForm.platforms"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="平台"
                        style="width: 190px"
                        @change="handlePlatformChange"
                    >
                        <el-option
                            v-for="item in platformOptions"
                            :key="item.value"
                            :label="item.label"
                            :value="item.value"
                        >
                            <PlatformBadge :platform="item.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select
                        v-model="searchForm.orgIds"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="组织"
                        style="width: 190px"
                        @change="handleOrgChange"
                    >
                        <el-option
                            v-for="org in orgOptions"
                            :key="org.id"
                            :label="org.name"
                            :value="org.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shopIds"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="店铺"
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
                <el-form-item label="大分类">
                    <el-select
                        v-model="searchForm.majorCategoryIds"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="大分类"
                        style="width: 220px"
                    >
                        <el-option
                            v-for="item in majorCategories"
                            :key="item.id"
                            :label="item.name"
                            :value="item.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="科目">
                    <el-select
                        v-model="searchForm.subjectIds"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="科目"
                        style="width: 220px"
                        @change="handleSubjectChange"
                    >
                        <el-option
                            v-for="subject in subjects"
                            :key="subject.id"
                            :label="subjectDisplayName(subject)"
                            :value="subject.id"
                        >
                            <div class="subject-option">
                                <el-tag
                                    size="small"
                                    effect="plain"
                                    :type="accountTypeTagType(subject.account_type)"
                                >
                                    {{ subject.account_type }}
                                </el-tag>
                                <span>{{ subject.name }}</span>
                            </div>
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="重分类">
                    <el-select
                        v-model="searchForm.categoryIds"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="重分类"
                        style="width: 200px"
                    >
                        <el-option
                            v-for="category in categoryOptions"
                            :key="category.id"
                            :label="category.name"
                            :value="category.id"
                        />
                    </el-select>
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch"
                        >搜索</el-button
                    >
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>
            <ActiveFilterTags
                :tags="activeFilterTags"
                @remove="removeFilterTag"
                @clear="handleReset"
            />
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">明细数据</span>
                        <span class="summary-count"
                            >当前页 {{ tableData.length }} 条 · 已选
                            {{ selectedRows.length }} 条</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <el-button
                            :disabled="selectedRows.length === 0"
                            @click="clearSelectedRows"
                            >清空选中</el-button
                        >
                        <el-button
                            :loading="exportSelectedLoading"
                            :disabled="selectedRows.length === 0"
                            @click="handleExport('selected')"
                        >
                            <el-icon><Download /></el-icon> 导出选中
                        </el-button>
                        <el-button
                            :loading="exportCurrentPageLoading"
                            @click="handleExport('current_page')"
                        >
                            <el-icon><Download /></el-icon> 导出当前页
                        </el-button>
                        <el-button
                            type="primary"
                            :loading="exportAllLoading"
                            @click="handleExport('all')"
                        >
                            <el-icon><Download /></el-icon> 导出全部
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                ref="tableRef"
                class="summary-table roomy-table detail-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                show-summary
                :summary-method="detailSummaryMethod"
                :fit="true"
                style="width: 100%"
                row-key="id"
                @selection-change="handleSelectionChange"
            >
                <el-table-column
                    type="selection"
                    width="48"
                    fixed="left"
                    :reserve-selection="true"
                />
                <el-table-column
                    label="序号"
                    width="78"
                    fixed="left"
                    align="center"
                >
                    <template #default="{ $index }">{{
                        (pagination.page - 1) * pagination.pageSize + $index + 1
                    }}</template>
                </el-table-column>
                <el-table-column label="业务年月" width="120">
                    <template #default="{ row }">{{
                        formatMonth(row.accounting_year, row.accounting_month)
                    }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" label="组织" width="170" show-overflow-tooltip>
                    <template #default="{ row }">
                        {{ row.org_name || `组织#${row.org_id}` }}
                    </template>
                </el-table-column>
                <el-table-column prop="platform_code" label="平台" width="110">
                    <template #default="{ row }">
                        <PlatformBadge
                            v-if="row.platform_code"
                            :platform="row.platform_code"
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
                            :color="shopColorByName.get(row.shop_name || '')"
                            size="table"
                        />
                    </template>
                </el-table-column>
                <el-table-column
                    prop="cash_flow_group_name"
                    label="总分类"
                    min-width="180"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        {{ row.major_category_name || row.cash_flow_group_name || "-" }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="subject_name"
                    label="科目"
                    min-width="210"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <div class="subject-cell">
                            <el-tag
                                v-if="subjectById.get(row.subject_id || 0)?.account_type"
                                size="small"
                                effect="plain"
                                :type="accountTypeTagType(subjectById.get(row.subject_id || 0)?.account_type)"
                            >
                                {{ subjectById.get(row.subject_id || 0)?.account_type }}
                            </el-tag>
                            <span>{{ row.subject_name || "-" }}</span>
                        </div>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="reclassification_name"
                    label="重分类"
                    min-width="180"
                    show-overflow-tooltip
                />
                <el-table-column
                    prop="total_amount"
                    label="汇总数值"
                    min-width="160"
                    align="right"
                    header-align="right"
                    class-name="money-column detail-edge-column"
                    header-class-name="money-column detail-edge-column"
                >
                    <template #default="{ row }"
                        ><span class="font-mono money-cell">{{
                            formatAmount(
                                row.total_amount ?? row.calculated_amount,
                            )
                        }}</span></template
                    >
                </el-table-column>
            </el-table>

            <div class="pagination-area">
                <el-pagination
                    v-model:current-page="pagination.page"
                    v-model:page-size="pagination.pageSize"
                    :total="paginationDisplayTotal"
                    :page-sizes="PAGE_SIZE_OPTIONS"
                    :layout="LIGHT_PAGINATION_LAYOUT"
                    background
                    @size-change="fetchData"
                    @current-change="fetchData"
                />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionSummaries" });

import { ElMessage } from "element-plus";
import type { TableInstance } from "element-plus";
import { Download } from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import {
    listTransactionCategories,
    listTransactionMajorCategories,
    listTransactionDetails,
    listTransactionSubjects,
    type TransactionCategory,
    type TransactionDetail,
    type TransactionMajorCategory,
    type TransactionSubject,
    type TransactionExportScope,
} from "@/api/transactionAccounting";
import {
    DEFAULT_PAGE_SIZE,
    LIGHT_PAGINATION_LAYOUT,
    PAGE_SIZE_OPTIONS,
    visiblePaginationTotal,
} from "@/utils/pagination";
import {
    detailSummaryMethod,
    formatAmount,
    formatMonth,
    monthRangeLabel,
    splitMonthRange,
} from "./common";
import {
    buildExportFilename,
    getPlatformLabel,
    summarizeFilenameValues,
} from "@/utils/format";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import {
    getFallbackPlatforms,
    getReportPlatformCode,
    toSourcePlatformOptions,
    type PlatformOption,
} from "@/utils/platform";
import { usePageRefresh } from "@/composables/pageRefresh";

const loading = ref(false);
const tableRef = ref<TableInstance>();
const tableData = ref<TransactionDetail[]>([]);
const selectedRows = ref<TransactionDetail[]>([]);
const majorCategories = ref<TransactionMajorCategory[]>([]);
const subjects = ref<TransactionSubject[]>([]);
const categories = ref<TransactionCategory[]>([]);
const shopOptions = ref<Shop[]>([]);
const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toSourcePlatformOptions(platforms.value),
);
const shopLoading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: null as number | null });
const paginationDisplayTotal = computed(() =>
    visiblePaginationTotal(
        pagination.total,
        pagination.page,
        pagination.pageSize,
        tableData.value.length,
    ),
);
const searchForm = reactive({
    businessMonthRange: null as string[] | null,
    orgIds: [] as number[],
    platforms: [] as string[],
    shopIds: [] as number[],
    majorCategoryIds: [] as number[],
    subjectIds: [] as number[],
    categoryIds: [] as number[],
});

const categoryOptions = computed(() => {
    return categories.value.filter(
        (item) =>
            !searchForm.subjectIds.length ||
            searchForm.subjectIds.includes(item.subject_id),
    );
});

const selectedReportPlatformsParam = computed(() => {
    const values = new Set(
        searchForm.platforms
            .map((platform) => getReportPlatformCode(platform, platforms.value))
            .filter(Boolean),
    );
    return Array.from(values).join(",") || undefined;
});
const selectedOrgIdsParam = computed(() => searchForm.orgIds.join(",") || undefined);

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

const subjectById = computed(() => {
    const map = new Map<number, TransactionSubject>();
    subjects.value.forEach((subject) => {
        map.set(subject.id, subject);
    });
    return map;
});

interface DetailFilterTag extends ActiveFilterTag {
    key:
        | "businessMonthRange"
        | "orgIds"
        | "platforms"
        | "shopIds"
        | "majorCategoryIds"
        | "subjectIds"
        | "categoryIds";
}

const activeFilterTags = computed<DetailFilterTag[]>(() => {
    const tags: DetailFilterTag[] = [];
    if (searchForm.businessMonthRange?.length) {
        tags.push({
            key: "businessMonthRange",
            label: "业务年月",
            value: monthRangeLabel(searchForm.businessMonthRange),
        });
    }
    searchForm.orgIds.forEach((value) => {
        const org = orgOptions.value.find((item) => item.id === value);
        tags.push({
            key: "orgIds",
            label: "组织",
            value: org?.name || `组织#${value}`,
        });
    });
    searchForm.platforms.forEach((value) => {
        tags.push({
            key: "platforms",
            label: "平台",
            value: getPlatformLabel(value),
        });
    });
    searchForm.shopIds.forEach((value) => {
        const shop = shopOptions.value.find((item) => item.id === value);
        tags.push({ key: "shopIds", label: "店铺", value: shop?.shop_name || String(value) });
    });
    searchForm.majorCategoryIds.forEach((value) => {
        const majorCategory = majorCategories.value.find(
            (item) => item.id === value,
        );
        tags.push({
            key: "majorCategoryIds",
            label: "大分类",
            value: majorCategory?.name || String(value),
        });
    });
    searchForm.subjectIds.forEach((value) => {
        const subject = subjects.value.find((item) => item.id === value);
        tags.push({
            key: "subjectIds",
            label: "科目",
            value: subject ? subjectDisplayName(subject) : String(value),
        });
    });
    searchForm.categoryIds.forEach((value) => {
        const category = categories.value.find((item) => item.id === value);
        tags.push({
            key: "categoryIds",
            label: "重分类",
            value: category?.name || String(value),
        });
    });
    return tags;
});

function queryParams() {
    return {
        page: pagination.page,
        page_size: pagination.pageSize,
        org_id: selectedOrgIdsParam.value,
        platform_code: selectedReportPlatformsParam.value,
        shop_ids: searchForm.shopIds.join(",") || undefined,
        major_category_id: searchForm.majorCategoryIds.join(",") || undefined,
        subject_id: searchForm.subjectIds.join(",") || undefined,
        category_id: searchForm.categoryIds.join(",") || undefined,
        ...splitMonthRange(searchForm.businessMonthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await listTransactionDetails(queryParams());
        tableData.value = data.items;
        pagination.total = data.total ?? null;
    } finally {
        loading.value = false;
    }
}

async function loadOptions() {
    const [majorCategoryItems, subjectItems, categoryItems, platformItems] = await Promise.all([
        listTransactionMajorCategories(),
        listTransactionSubjects(),
        listTransactionCategories(),
        fetchPlatformOptions(),
    ]);
    majorCategories.value = majorCategoryItems;
    subjects.value = subjectItems;
    categories.value = categoryItems;
    platforms.value = platformItems;
    platformOptions.value = toSourcePlatformOptions(platforms.value);
    await fetchOrgOptions();
    await fetchShopOptions();
}

function handleSearch() {
    pagination.page = 1;
    selectedRows.value = [];
    fetchData();
}

function handleReset() {
    searchForm.businessMonthRange = null;
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.shopIds = [];
    searchForm.majorCategoryIds = [];
    searchForm.subjectIds = [];
    searchForm.categoryIds = [];
    fetchShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: DetailFilterTag) {
    if (tag.key === "businessMonthRange") {
        searchForm.businessMonthRange = null;
    } else if (tag.key === "orgIds") {
        searchForm.orgIds = searchForm.orgIds.filter((item) => {
            const org = orgOptions.value.find((orgItem) => orgItem.id === item);
            return (org?.name || `组织#${item}`) !== tag.value;
        });
        await handleOrgChange();
    } else if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter(
            (item) => getPlatformLabel(item) !== tag.value,
        );
        await handlePlatformChange();
    } else if (tag.key === "shopIds") {
        searchForm.shopIds = searchForm.shopIds.filter((item) => {
            const shop = shopOptions.value.find((shopItem) => shopItem.id === item);
            return (shop?.shop_name || String(item)) !== tag.value;
        });
    } else if (tag.key === "majorCategoryIds") {
        searchForm.majorCategoryIds = searchForm.majorCategoryIds.filter(
            (item) => {
                const majorCategory = majorCategories.value.find(
                    (majorCategoryItem) => majorCategoryItem.id === item,
                );
                return (majorCategory?.name || String(item)) !== tag.value;
            },
        );
    } else if (tag.key === "subjectIds") {
        searchForm.subjectIds = searchForm.subjectIds.filter((item) => {
            const subject = subjects.value.find(
                (subjectItem) => subjectItem.id === item,
            );
            return (subject ? subjectDisplayName(subject) : String(item)) !== tag.value;
        });
        handleSubjectChange();
    } else if (tag.key === "categoryIds") {
        searchForm.categoryIds = searchForm.categoryIds.filter((item) => {
            const category = categories.value.find(
                (categoryItem) => categoryItem.id === item,
            );
            return (category?.name || String(item)) !== tag.value;
        });
    }
    handleSearch();
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        return res.length ? res : getFallbackPlatforms();
    } catch {
        return getFallbackPlatforms();
    }
}

async function fetchOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    try {
        orgOptions.value = await getAllOrganizations();
    } catch {
        // Ignore
    }
}

async function fetchShopOptions() {
    shopLoading.value = true;
    try {
        const res = await getShopList({
            page: 1,
            page_size: 100,
            org_id: selectedOrgIdsParam.value,
            platform_name: selectedReportPlatformsParam.value,
        });
        shopOptions.value = res.items || [];
    } finally {
        shopLoading.value = false;
    }
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

async function handleOrgChange() {
    await fetchShopOptions();
    const availableShopIds = new Set(
        filteredShopOptions.value.map((shop) => shop.id),
    );
    searchForm.shopIds = searchForm.shopIds.filter((shopId) =>
        availableShopIds.has(shopId),
    );
}

function handleSubjectChange() {
    const availableCategoryIds = new Set(
        categoryOptions.value.map((category) => category.id),
    );
    searchForm.categoryIds = searchForm.categoryIds.filter((categoryId) =>
        availableCategoryIds.has(categoryId),
    );
}

function subjectName(id: number) {
    const subject = subjects.value.find((item) => item.id === id);
    return subject ? subjectDisplayName(subject) : String(id);
}

function categoryName(id: number) {
    return categories.value.find((category) => category.id === id)?.name || String(id);
}

function majorCategoryName(id: number) {
    return (
        majorCategories.value.find((item) => item.id === id)?.name || String(id)
    );
}

function subjectDisplayName(subject: TransactionSubject) {
    return `${subject.account_type} · ${subject.name}`;
}

function accountTypeTagType(accountType?: string | null) {
    return accountType === "动账账户" ? "warning" : "info";
}

function handleSelectionChange(rows: TransactionDetail[]) {
    selectedRows.value = rows;
}

function clearSelectedRows() {
    tableRef.value?.clearSelection();
    selectedRows.value = [];
}

async function handleExport(scope: TransactionExportScope) {
    if (scope === "current_page" && tableData.value.length === 0) {
        ElMessage.warning("当前页暂无可导出的数据");
        return;
    }
    if (scope === "selected" && selectedRows.value.length === 0) {
        ElMessage.warning("请先选择要导出的数据");
        return;
    }
    const loadingRef =
        scope === "all"
            ? exportAllLoading
            : scope === "current_page"
              ? exportCurrentPageLoading
              : exportSelectedLoading;
    loadingRef.value = true;
    try {
        const params = {
            ...queryParams(),
            scope,
            ids:
                scope === "selected"
                    ? selectedRows.value.map((row) => row.id).join(",")
                    : undefined,
            page: scope === "current_page" ? pagination.page : undefined,
            page_size:
                scope === "current_page" ? pagination.pageSize : undefined,
        };
        const scopeLabel =
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中";
        const filename = normalizeExportFilename(buildExportFilename([
            monthRangeLabel(searchForm.businessMonthRange) || "全部业务年月",
            `平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shopIds.map((id) => shopOptions.value.find((s) => s.id === id)?.shop_name || String(id)), "全部")}`,
            `大分类${summarizeFilenameValues(searchForm.majorCategoryIds.map(majorCategoryName), "全部")}`,
            `科目${summarizeFilenameValues(searchForm.subjectIds.map(subjectName), "全部")}`,
            `重分类${summarizeFilenameValues(searchForm.categoryIds.map(categoryName), "全部")}`,
            "科目明细",
            scopeLabel,
        ]));
        await submitExportJob({
            export_type: "transaction.details",
            title: "科目明细导出",
            filename,
            params,
        });
    } finally {
        loadingRef.value = false;
    }
}

onMounted(async () => {
    await loadOptions();
    await fetchData();
});

usePageRefresh(async () => {
    await loadOptions();
    await fetchData();
});
</script>

<style scoped lang="scss">
@use "./transaction.scss";

:deep(.detail-table) {
    width: 100%;
}

:deep(.detail-table .detail-edge-column .cell),
:deep(.detail-table th.detail-edge-column .cell) {
    padding-right: 18px !important;
}

.subject-option,
.subject-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.subject-option span,
.subject-cell span {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
