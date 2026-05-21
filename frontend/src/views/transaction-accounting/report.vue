<template>
    <div class="page-container transaction-page">
        <el-card shadow="never" class="search-card">
            <SearchCardIntro
                kicker="资金报表"
                :title="`${searchForm.year} 年资金报表`"
                tip="科目全年展示，父级行由子科目合计"
            />

            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="业务年份">
                    <el-date-picker
                        v-model="yearPickerValue"
                        type="year"
                        placeholder="选择年份"
                        clearable
                        value-format="YYYY"
                        style="width: 150px"
                        @change="handleYearChange"
                    />
                </el-form-item>
                <el-form-item label="核算年月">
                    <el-date-picker
                        v-model="searchForm.uploadMonthRange"
                        type="monthrange"
                        start-placeholder="开始年月"
                        end-placeholder="结束年月"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 230px"
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
                        placeholder="全部平台"
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
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shopNames"
                        clearable
                        filterable
                        multiple
                        collapse-tags
                        collapse-tags-tooltip
                        placeholder="全部店铺"
                        :loading="shopLoading"
                        style="width: 210px"
                    >
                        <el-option
                            v-for="shop in filteredShopOptions"
                            :key="`${shop.platform_name}-${shop.shop_name}`"
                            :label="shop.shop_name"
                            :value="shop.shop_name"
                        >
                            <ShopBadge
                                :label="shop.shop_name"
                                :color="shop.shop_color"
                                size="compact"
                            />
                        </el-option>
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
                        placeholder="全部科目"
                        style="width: 220px"
                        @change="handleSubjectChange"
                    >
                        <el-option
                            v-for="subject in subjects"
                            :key="subject.id"
                            :label="subject.name"
                            :value="subject.id"
                        />
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
                        placeholder="全部重分类"
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

        <el-card shadow="never" class="table-card annual-report-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">年度资金矩阵</span>
                        <span class="summary-count"
                            >共 {{ tableData.length }} 个科目 ·
                            右侧为行合计</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <el-button
                            type="primary"
                            :loading="exportLoading"
                            @click="handleExport"
                        >
                            <el-icon><Download /></el-icon> 导出年度表
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table
                class="summary-table annual-report-table"
                :data="tableData"
                v-loading="loading"
                :fit="true"
                style="width: 100%"
                row-key="code"
                height="calc(100vh - 270px)"
                :row-class-name="annualRowClassName"
            >
                <el-table-column
                    prop="code"
                    label="序号"
                    width="64"
                    fixed="left"
                    align="center"
                    class-name="annual-code-column"
                    header-class-name="annual-code-column"
                />
                <el-table-column
                    prop="name"
                    :label="`${searchForm.year}年`"
                    width="246"
                    fixed="left"
                    align="left"
                    header-align="left"
                    class-name="annual-name-column"
                    header-class-name="annual-name-column"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <span
                            class="cash-subject-name"
                            :class="`cash-subject-name--level-${row.level}`"
                            :title="row.name"
                            >{{ row.name }}</span
                        >
                    </template>
                </el-table-column>
                <el-table-column
                    v-for="month in reportMonths"
                    :key="month"
                    :prop="`months.${month}`"
                    :label="month"
                    min-width="118"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                    header-class-name="money-column"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <span
                            class="font-mono money-cell"
                            :class="{
                                'money-cell--negative':
                                    Number(row.months[month] || 0) < 0,
                            }"
                            :title="formatAmount(row.months[month])"
                        >
                            {{ formatAmount(row.months[month]) }}
                        </span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="total_amount"
                    label="合计"
                    min-width="136"
                    fixed="right"
                    align="right"
                    header-align="right"
                    class-name="money-column annual-total-column summary-edge-column"
                    header-class-name="money-column annual-total-column summary-edge-column"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <span
                            class="font-mono money-cell annual-total-cell"
                            :class="{
                                'money-cell--negative':
                                    Number(row.total_amount || 0) < 0,
                            }"
                            :title="formatAmount(row.total_amount)"
                        >
                            {{ formatAmount(row.total_amount) }}
                        </span>
                    </template>
                </el-table-column>
            </el-table>
        </el-card>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "TransactionSummaryReport" });

import { ElMessage } from "element-plus";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import {
    exportTransactionAnnualSummaryExcel,
    getTransactionAnnualSummary,
    listTransactionCategories,
    listTransactionSubjects,
    type TransactionAnnualSummaryParams,
    type TransactionAnnualSummaryRow,
    type TransactionCategory,
    type TransactionSubject,
} from "@/api/transactionAccounting";
import {
    downloadBlob,
    formatAmount,
    monthRangeLabel,
    splitUploadMonthRange,
} from "./common";
import { getPlatformLabel } from "@/utils/format";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import {
    getFallbackPlatforms,
    getReportPlatformCode,
    toSourcePlatformOptions,
    type PlatformOption,
} from "@/utils/platform";

const currentYear = new Date().getFullYear();
const loading = ref(false);
const tableData = ref<TransactionAnnualSummaryRow[]>([]);
const reportMonths = ref<string[]>(buildYearMonths(currentYear));
const subjects = ref<TransactionSubject[]>([]);
const categories = ref<TransactionCategory[]>([]);
const shopOptions = ref<Shop[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toSourcePlatformOptions(platforms.value),
);
const shopLoading = ref(false);
const exportLoading = ref(false);
const searchForm = reactive({
    year: currentYear,
    uploadMonthRange: [] as string[],
    platforms: [] as string[],
    shopNames: [] as string[],
    subjectIds: [] as number[],
    categoryIds: [] as number[],
});
const yearPickerValue = ref(String(currentYear));

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

interface ReportFilterTag extends ActiveFilterTag {
    key:
        | "year"
        | "uploadMonthRange"
        | "platforms"
        | "shopNames"
        | "subjectIds"
        | "categoryIds";
}

const activeFilterTags = computed<ReportFilterTag[]>(() => {
    const tags: ReportFilterTag[] = [
        { key: "year", label: "业务年份", value: `${searchForm.year}` },
    ];
    if (searchForm.uploadMonthRange.length) {
        tags.push({
            key: "uploadMonthRange",
            label: "核算年月",
            value: monthRangeLabel(searchForm.uploadMonthRange),
        });
    }
    searchForm.platforms.forEach((value) =>
        tags.push({
            key: "platforms",
            label: "平台",
            value: getPlatformLabel(value),
        }),
    );
    searchForm.shopNames.forEach((value) =>
        tags.push({ key: "shopNames", label: "店铺", value }),
    );
    searchForm.subjectIds.forEach((value) => {
        const subject = subjects.value.find((item) => item.id === value);
        tags.push({
            key: "subjectIds",
            label: "科目",
            value: subject?.name || String(value),
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

function buildYearMonths(year: number) {
    return Array.from(
        { length: 12 },
        (_, index) => `${year}${String(index + 1).padStart(2, "0")}`,
    );
}

function queryParams(): TransactionAnnualSummaryParams {
    return {
        year: searchForm.year,
        platform_code: selectedReportPlatformsParam.value,
        shop_name: searchForm.shopNames.join(",") || undefined,
        subject_id: searchForm.subjectIds.join(",") || undefined,
        category_id: searchForm.categoryIds.join(",") || undefined,
        ...splitUploadMonthRange(searchForm.uploadMonthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await getTransactionAnnualSummary(queryParams());
        reportMonths.value = data.months.length
            ? data.months
            : buildYearMonths(searchForm.year);
        tableData.value = data.rows;
    } finally {
        loading.value = false;
    }
}

async function loadOptions() {
    const [subjectItems, categoryItems, platformItems] = await Promise.all([
        listTransactionSubjects(),
        listTransactionCategories(),
        fetchPlatformOptions(),
    ]);
    subjects.value = subjectItems;
    categories.value = categoryItems;
    platforms.value = platformItems;
    platformOptions.value = toSourcePlatformOptions(platforms.value);
    await fetchShopOptions();
}

function handleSearch() {
    fetchData();
}

function handleReset() {
    searchForm.year = currentYear;
    yearPickerValue.value = String(currentYear);
    searchForm.uploadMonthRange = [];
    searchForm.platforms = [];
    searchForm.shopNames = [];
    searchForm.subjectIds = [];
    searchForm.categoryIds = [];
    reportMonths.value = buildYearMonths(currentYear);
    fetchShopOptions();
    fetchData();
}

function handleYearChange(value: string | null) {
    const nextYear = value ? Number(value) : currentYear;
    searchForm.year = Number.isFinite(nextYear) ? nextYear : currentYear;
    yearPickerValue.value = String(searchForm.year);
    reportMonths.value = buildYearMonths(searchForm.year);
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        return res.length ? res : getFallbackPlatforms();
    } catch {
        return getFallbackPlatforms();
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
    } finally {
        shopLoading.value = false;
    }
}

async function handlePlatformChange() {
    await fetchShopOptions();
    const availableShopNames = new Set(
        filteredShopOptions.value.map((shop) => shop.shop_name),
    );
    searchForm.shopNames = searchForm.shopNames.filter((shopName) =>
        availableShopNames.has(shopName),
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

async function removeFilterTag(tag: ReportFilterTag) {
    if (tag.key === "year") {
        searchForm.year = currentYear;
        yearPickerValue.value = String(currentYear);
        reportMonths.value = buildYearMonths(currentYear);
    } else if (tag.key === "uploadMonthRange") {
        searchForm.uploadMonthRange = [];
    } else if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter(
            (item) => getPlatformLabel(item) !== tag.value,
        );
        await handlePlatformChange();
    } else if (tag.key === "shopNames") {
        searchForm.shopNames = searchForm.shopNames.filter(
            (item) => item !== tag.value,
        );
    } else if (tag.key === "subjectIds") {
        searchForm.subjectIds = searchForm.subjectIds.filter((item) => {
            const subject = subjects.value.find(
                (subjectItem) => subjectItem.id === item,
            );
            return (subject?.name || String(item)) !== tag.value;
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

async function handleExport() {
    if (tableData.value.length === 0) {
        ElMessage.warning("当前暂无可导出的数据");
        return;
    }
    exportLoading.value = true;
    try {
        const blob = await exportTransactionAnnualSummaryExcel(queryParams());
        downloadBlob(blob, `资金报表_${searchForm.year}年.xlsx`);
        ElMessage.success("导出成功");
    } finally {
        exportLoading.value = false;
    }
}

function annualRowClassName({ row }: { row: TransactionAnnualSummaryRow }) {
    const classes = [
        `annual-row--level-${row.level}`,
        `annual-row--type-${row.item_type}`,
    ];
    if (Number(row.total_amount || 0) < 0) {
        classes.push("annual-row--negative");
    }
    if (Number(row.total_amount || 0) > 0) {
        classes.push("annual-row--positive");
    }
    if (row.item_type === "check" && rowHasNonZeroAmount(row)) {
        classes.push("annual-row--check-warning");
    }
    return classes.join(" ");
}

function rowHasNonZeroAmount(row: TransactionAnnualSummaryRow) {
    const values = [row.total_amount, ...Object.values(row.months || {})];
    return values.some((value) => Math.abs(Number(value || 0)) > 0.000001);
}

onMounted(async () => {
    await loadOptions();
    await fetchData();
});
</script>

<style scoped lang="scss">
@use "./transaction.scss";

:deep(.summary-table .summary-edge-column .cell),
:deep(.summary-table th.summary-edge-column .cell) {
    padding-right: 18px !important;
}
</style>
