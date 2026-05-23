<template>
    <div class="page-container">
        <el-card shadow="never" class="search-card summary-search-card">
            <SearchCardIntro
                kicker="汇总明细工作台"
                title="先筛选，再勾选，再导出"
                :tip="
                    route.query.from === 'summary-report'
                        ? '已承接汇总报表筛选条件'
                        : '支持跨页保留选中结果'
                "
            />

            <el-form :model="searchForm" inline class="summary-filter-form">
                <el-form-item label="业务年月">
                    <el-date-picker
                        v-model="searchForm.summaryMonthRange"
                        type="monthrange"
                        start-placeholder="开始年月"
                        end-placeholder="结束年月"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 230px"
                    />
                </el-form-item>
                <el-form-item label="核算年月">
                    <el-date-picker
                        v-model="searchForm.sourceMonthRange"
                        type="monthrange"
                        start-placeholder="开始年月"
                        end-placeholder="结束年月"
                        range-separator="至"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 230px"
                    />
                </el-form-item>
                <el-form-item label="来源平台">
                    <el-select
                        v-model="searchForm.platforms"
                        placeholder="全部来源平台"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
                        style="width: 170px"
                        @change="handlePlatformChange"
                    >
                        <el-option
                            v-for="p in platformOptions"
                            :key="p.value"
                            :label="p.label"
                            :value="p.value"
                        >
                            <PlatformBadge :platform="p.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="归集平台">
                    <el-select
                        v-model="searchForm.reportPlatforms"
                        placeholder="全部归集平台"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
                        style="width: 170px"
                        @change="handleReportPlatformChange"
                    >
                        <el-option
                            v-for="p in reportPlatformOptions"
                            :key="p.value"
                            :label="p.label"
                            :value="p.value"
                        >
                            <PlatformBadge :platform="p.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shops"
                        placeholder="全部店铺"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
                        :loading="shopLoading"
                        style="width: 210px"
                    >
                        <el-option
                            v-for="shop in filteredShopOptions"
                            :key="shop.id"
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
                <el-form-item label="搜索">
                    <el-input
                        v-model="searchForm.keyword"
                        clearable
                        placeholder="店铺 / 平台"
                        style="width: 150px"
                        @keyup.enter="handleSearch"
                    />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch"
                        >搜索</el-button
                    >
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>

            <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
        </el-card>

        <el-card shadow="never" class="table-card summary-table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">汇总明细数据</span>
                        <span class="summary-count"
                            >共 {{ pagination.total }} 条 · 已选
                            {{ selectedCount }} 条</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <el-button
                            :disabled="selectedCount === 0"
                            @click="clearSelectedRows"
                        >
                            清空选中
                        </el-button>
                        <el-button
                            :loading="exportSelectedLoading"
                            :disabled="selectedCount === 0"
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
                ref="summaryTableRef"
                class="summary-table roomy-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                show-summary
                :summary-method="getSummary"
                :fit="false"
                style="width: 100%"
                height="calc(100vh - 278px)"
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
                    width="70"
                    align="center"
                    fixed="left"
                >
                    <template #default="{ $index }">
                        {{
                            (pagination.page - 1) * pagination.pageSize +
                            $index +
                            1
                        }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="source_date"
                    label="核算年月"
                    width="108"
                />
                <el-table-column
                    prop="summary_date"
                    label="业务年月"
                    width="108"
                />
                <el-table-column
                    prop="platform"
                    label="来源平台"
                    width="112"
                >
                    <template #default="{ row }">
                        <button
                            type="button"
                            class="inline-filter-trigger"
                            @click="applyQuickFilter('platform', row.platform)"
                        >
                            <PlatformBadge :platform="row.platform" />
                        </button>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="report_platform"
                    label="归集平台"
                    width="112"
                >
                    <template #default="{ row }">
                        <button
                            type="button"
                            class="inline-filter-trigger"
                            @click="
                                applyQuickFilter(
                                    'reportPlatform',
                                    row.report_platform,
                                )
                            "
                        >
                            <PlatformBadge :platform="row.report_platform" />
                        </button>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="shop_name"
                    label="店铺"
                    width="220"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <button
                            type="button"
                            class="inline-filter-link"
                            @click="applyQuickFilter('shop', row.shop_name)"
                        >
                            <ShopBadge
                                :label="row.shop_name"
                                :color="row.shop_color"
                                size="table"
                            />
                        </button>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="order_paid_amount"
                    label="订单实付金额"
                    width="145"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.order_paid_amount)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="refund_amount"
                    label="退款金额"
                    width="130"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.refund_amount)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="real_gmv"
                    label="实收GMV"
                    width="145"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.real_gmv)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="platform_other_income"
                    label="平台其他收入"
                    width="150"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.platform_other_income)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="platform_service_fee"
                    label="平台服务费"
                    width="145"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.platform_service_fee)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="return_and_other_fee"
                    label="退货费用及其他费用"
                    width="175"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.return_and_other_fee)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="daren_commission"
                    label="达人佣金"
                    width="135"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.daren_commission)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="zhaoshang_service_fee"
                    label="招商服务费"
                    width="145"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.zhaoshang_service_fee)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="outside_promotion_fee"
                    label="站外推广费"
                    width="145"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.outside_promotion_fee)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="service_provider_commission"
                    label="服务商佣金"
                    width="150"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.service_provider_commission)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="payment_donation_fee"
                    label="支付捐赠费用"
                    width="150"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.payment_donation_fee)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="shipping_insurance"
                    label="运费险"
                    width="120"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.shipping_insurance)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="bic"
                    label="BIC"
                    width="120"
                    align="right"
                    header-align="right"
                    class-name="money-column summary-edge-column"
                    header-class-name="summary-edge-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.bic)
                        }}</span>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty
                        description="暂无汇总明细数据，请先上传并处理文件"
                        :image-size="80"
                    />
                </template>
            </el-table>

            <!-- Pagination -->
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
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "Summaries" });

import { ref, reactive, computed, onMounted, nextTick } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import type { TableColumnCtx } from "element-plus/es/components/table/index.mjs";
import {
    getSummaryList,
    exportSummaryExcel,
    type SummaryRecord,
} from "@/api/summary";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import {
    buildExportFilename,
    formatMoney,
    getPlatformLabel,
    summarizeFilenameValues,
} from "@/utils/format";
import {
    getFallbackPlatforms,
    getReportPlatformCode,
    toReportPlatformOptions,
    toSourcePlatformOptions,
    type PlatformOption,
} from "@/utils/platform";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import type { ActiveFilterTag } from "@/components/activeFilterTags";

const route = useRoute();

interface FilterTag extends ActiveFilterTag {
    key:
        | "summaryMonthRange"
        | "sourceMonthRange"
        | "platforms"
        | "reportPlatforms"
        | "shops"
        | "keyword";
}

interface SummaryTableInstance {
    doLayout: () => void;
    clearSelection: () => void;
    toggleRowSelection: (row: SummaryRecord, selected?: boolean) => void;
}

// Search
const searchForm = reactive({
    summaryMonthRange: [] as string[],
    sourceMonthRange: [] as string[],
    platforms: [] as string[],
    reportPlatforms: [] as string[],
    shops: [] as string[],
    keyword: "",
});

const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toSourcePlatformOptions(platforms.value),
);
const reportPlatformOptions = ref<PlatformOption[]>(
    toReportPlatformOptions(platforms.value),
);

const loading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const tableData = ref<SummaryRecord[]>([]);
const selectedRowMap = ref(new Map<number, SummaryRecord>());
const shopLoading = ref(false);
const shopOptions = ref<Shop[]>([]);
const summaryTableRef = ref<SummaryTableInstance>();

const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

function parseMonthValue(value: string | undefined) {
    if (!value) return { year: undefined, month: undefined };
    const [year, month] = value.split("-");
    return {
        year: Number(year) || undefined,
        month: Number(month) || undefined,
    };
}

function formatMonthRangeLabel(range: string[]) {
    const [start, end] = range;
    if (!start && !end) return "";
    if (start && end && start !== end) return `${start} 至 ${end}`;
    return start || end || "";
}

const selectedSummaryStart = computed(() =>
    parseMonthValue(searchForm.summaryMonthRange[0]),
);
const selectedSummaryEnd = computed(() =>
    parseMonthValue(
        searchForm.summaryMonthRange[1] || searchForm.summaryMonthRange[0],
    ),
);
const selectedSourceStart = computed(() =>
    parseMonthValue(searchForm.sourceMonthRange[0]),
);
const selectedSourceEnd = computed(() =>
    parseMonthValue(
        searchForm.sourceMonthRange[1] || searchForm.sourceMonthRange[0],
    ),
);

const filteredShopOptions = computed(() => {
    const selectedReportPlatforms = selectedReportPlatformSet.value;
    if (!selectedReportPlatforms.size) return shopOptions.value;
    return shopOptions.value.filter((shop) =>
        selectedReportPlatforms.has(shop.platform_name),
    );
});

const selectedSourcePlatformsParam = computed(
    () => searchForm.platforms.join(",") || undefined,
);
const selectedReportPlatformsParam = computed(() => {
    const explicitReportPlatforms = searchForm.reportPlatforms.filter(Boolean);
    const derivedReportPlatforms = searchForm.platforms
        .map((platform) => getReportPlatformCode(platform, platforms.value))
        .filter(Boolean);
    return (
        Array.from(
            new Set([...explicitReportPlatforms, ...derivedReportPlatforms]),
        ).join(",") || undefined
    );
});
const selectedReportPlatformSet = computed(() => {
    const values =
        selectedReportPlatformsParam.value?.split(",").filter(Boolean) || [];
    return new Set(values);
});
const selectedShopsParam = computed(
    () => searchForm.shops.join(",") || undefined,
);
const keywordParam = computed(() => searchForm.keyword.trim() || undefined);
const selectedRows = computed(() => Array.from(selectedRowMap.value.values()));
const selectedCount = computed(() => selectedRowMap.value.size);
const activeFilterTags = computed<FilterTag[]>(() => {
    const tags: FilterTag[] = [];

    if (searchForm.summaryMonthRange.length) {
        tags.push({
            key: "summaryMonthRange",
            label: "业务年月",
            value: formatMonthRangeLabel(searchForm.summaryMonthRange),
        });
    }
    if (searchForm.sourceMonthRange.length) {
        tags.push({
            key: "sourceMonthRange",
            label: "核算年月",
            value: formatMonthRangeLabel(searchForm.sourceMonthRange),
        });
    }
    searchForm.platforms.forEach((value) => {
        tags.push({
            key: "platforms",
            label: "来源平台",
            value: getPlatformLabel(value),
        });
    });
    searchForm.reportPlatforms.forEach((value) => {
        tags.push({
            key: "reportPlatforms",
            label: "归集平台",
            value: getPlatformLabel(value),
        });
    });
    searchForm.shops.forEach((value) => {
        tags.push({ key: "shops", label: "店铺", value });
    });
    if (searchForm.keyword.trim()) {
        tags.push({
            key: "keyword",
            label: "关键词",
            value: searchForm.keyword.trim(),
        });
    }

    return tags;
});

// Money columns for summary
const moneyColumns = [
    "order_paid_amount",
    "refund_amount",
    "real_gmv",
    "platform_other_income",
    "platform_service_fee",
    "return_and_other_fee",
    "daren_commission",
    "zhaoshang_service_fee",
    "outside_promotion_fee",
    "service_provider_commission",
    "payment_donation_fee",
    "shipping_insurance",
    "bic",
];

function getSummary(param: {
    columns: TableColumnCtx<SummaryRecord>[];
    data: SummaryRecord[];
}) {
    const { columns, data } = param;
    const sums: string[] = [];
    columns.forEach((column, index) => {
        const prop = column.property as keyof SummaryRecord;
        if (prop === "source_date") {
            sums[index] = "合计";
            return;
        }
        if (!moneyColumns.includes(prop)) {
            sums[index] = "";
            return;
        }
        const values = data.map((item) => Number(item[prop]) || 0);
        const total = values.reduce((prev, curr) => prev + curr, 0);
        sums[index] = total.toLocaleString("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    });
    return sums;
}

async function fetchData() {
    loading.value = true;
    try {
        const res = await getSummaryList({
            page: pagination.page,
            page_size: pagination.pageSize,
            summary_start_year: selectedSummaryStart.value.year,
            summary_start_month: selectedSummaryStart.value.month,
            summary_end_year: selectedSummaryEnd.value.year,
            summary_end_month: selectedSummaryEnd.value.month,
            source_start_year: selectedSourceStart.value.year,
            source_start_month: selectedSourceStart.value.month,
            source_end_year: selectedSourceEnd.value.year,
            source_end_month: selectedSourceEnd.value.month,
            platform_name: selectedSourcePlatformsParam.value,
            report_platform_name: selectedReportPlatformsParam.value,
            shop_name: selectedShopsParam.value,
            keyword: keywordParam.value,
        });
        tableData.value = res.items || [];
        pagination.total = res.total || 0;
    } catch {
        // Error handled by interceptor
    } finally {
        loading.value = false;
        await nextTick();
        restoreSelection();
        summaryTableRef.value?.doLayout();
    }
}

async function fetchShopOptions() {
    shopLoading.value = true;
    try {
        const res = await getShopList({
            page: 1,
            page_size: 100,
            platform_name:
                selectedReportPlatformsParam.value ||
                selectedSourcePlatformsParam.value,
        });
        shopOptions.value = res.items || [];
    } catch {
        // Error handled by interceptor
    } finally {
        shopLoading.value = false;
    }
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
    platformOptions.value = toSourcePlatformOptions(platforms.value);
    reportPlatformOptions.value = toReportPlatformOptions(platforms.value);
}

function handlePlatformChange() {
    const availableShops = new Set(
        filteredShopOptions.value.map((shop) => shop.shop_name),
    );
    searchForm.shops = searchForm.shops.filter((shopName) =>
        availableShops.has(shopName),
    );
    fetchShopOptions();
}

function handleReportPlatformChange() {
    const availableShops = new Set(
        filteredShopOptions.value.map((shop) => shop.shop_name),
    );
    searchForm.shops = searchForm.shops.filter((shopName) =>
        availableShops.has(shopName),
    );
    fetchShopOptions();
}

function handleSearch() {
    pagination.page = 1;
    clearSelectedRows(false);
    fetchData();
}

function handleReset() {
    searchForm.summaryMonthRange = [];
    searchForm.sourceMonthRange = [];
    searchForm.platforms = [];
    searchForm.reportPlatforms = [];
    searchForm.shops = [];
    searchForm.keyword = "";
    pagination.page = 1;
    clearSelectedRows(false);
    fetchShopOptions();
    fetchData();
}

function handleSelectionChange(rows: SummaryRecord[]) {
    const currentPageIds = new Set(tableData.value.map((row) => row.id));
    const nextMap = new Map(selectedRowMap.value);

    currentPageIds.forEach((id) => {
        nextMap.delete(id);
    });
    rows.forEach((row) => {
        nextMap.set(row.id, row);
    });

    selectedRowMap.value = nextMap;
}

function restoreSelection() {
    if (!summaryTableRef.value) return;
    summaryTableRef.value.clearSelection();
    tableData.value.forEach((row) => {
        if (selectedRowMap.value.has(row.id)) {
            summaryTableRef.value?.toggleRowSelection(row, true);
        }
    });
}

function clearSelectedRows(clearTable = true) {
    selectedRowMap.value = new Map();
    if (clearTable) {
        summaryTableRef.value?.clearSelection();
    }
}

function removeFilterTag(tag: FilterTag) {
    if (tag.key === "summaryMonthRange") {
        searchForm.summaryMonthRange = [];
    } else if (tag.key === "sourceMonthRange") {
        searchForm.sourceMonthRange = [];
    } else if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter(
            (item) => getPlatformLabel(item) !== tag.value,
        );
    } else if (tag.key === "reportPlatforms") {
        searchForm.reportPlatforms = searchForm.reportPlatforms.filter(
            (item) => getPlatformLabel(item) !== tag.value,
        );
    } else if (tag.key === "shops") {
        searchForm.shops = searchForm.shops.filter(
            (item) => item !== tag.value,
        );
    } else if (tag.key === "keyword") {
        searchForm.keyword = "";
    }

    handleReportPlatformChange();
    handleSearch();
}

function applyQuickFilter(
    type: "platform" | "reportPlatform" | "shop",
    value: string,
) {
    if (!value) return;

    if (type === "platform") {
        searchForm.platforms = [value];
    } else if (type === "reportPlatform") {
        searchForm.reportPlatforms = [value];
    } else {
        searchForm.shops = [value];
    }

    handleReportPlatformChange();
    handleSearch();
}

async function handleExport(scope: "all" | "current_page" | "selected") {
    if (scope === "current_page" && tableData.value.length === 0) {
        ElMessage.warning("当前页暂无可导出的数据");
        return;
    }
    if (scope === "selected" && selectedCount.value === 0) {
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
        const blob = await exportSummaryExcel({
            summary_start_year: selectedSummaryStart.value.year,
            summary_start_month: selectedSummaryStart.value.month,
            summary_end_year: selectedSummaryEnd.value.year,
            summary_end_month: selectedSummaryEnd.value.month,
            source_start_year: selectedSourceStart.value.year,
            source_start_month: selectedSourceStart.value.month,
            source_end_year: selectedSourceEnd.value.year,
            source_end_month: selectedSourceEnd.value.month,
            platform_name: selectedSourcePlatformsParam.value,
            report_platform_name: selectedReportPlatformsParam.value,
            shop_name: selectedShopsParam.value,
            keyword: keywordParam.value,
            scope,
            ids:
                scope === "selected"
                    ? selectedRows.value.map((row) => row.id).join(",")
                    : undefined,
            page: scope === "current_page" ? pagination.page : undefined,
            page_size:
                scope === "current_page" ? pagination.pageSize : undefined,
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        const scopeLabel =
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中";
        link.download = buildExportFilename([
            formatMonthRangeLabel(searchForm.summaryMonthRange) ||
                "全部业务年月",
            formatMonthRangeLabel(searchForm.sourceMonthRange) ||
                "全部核算年月",
            `来源平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `归集平台${summarizeFilenameValues(searchForm.reportPlatforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shops, "全部")}`,
            searchForm.keyword.trim()
                ? `关键词${searchForm.keyword.trim()}`
                : "关键词全部",
            "汇总明细",
            scopeLabel,
        ]);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success("导出成功");
    } catch {
        ElMessage.error("导出失败，请稍后重试");
    } finally {
        loadingRef.value = false;
    }
}

onMounted(async () => {
    applyRouteQuery();
    await fetchPlatformOptions();
    await fetchShopOptions();
    fetchData();
});

usePageRefresh(async () => {
    await fetchPlatformOptions();
    await fetchShopOptions();
    await fetchData();
});

function queryString(value: unknown): string {
    if (Array.isArray(value)) return value.filter(Boolean).join(",");
    return typeof value === "string" ? value : "";
}

function splitQueryList(value: unknown): string[] {
    return queryString(value)
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
}

function applyRouteQuery() {
    const sourceMonth = queryString(route.query.sourceMonth);
    const summaryMonth = queryString(route.query.summaryMonth);
    if (sourceMonth) searchForm.sourceMonthRange = [sourceMonth, sourceMonth];
    if (summaryMonth)
        searchForm.summaryMonthRange = [summaryMonth, summaryMonth];
    searchForm.platforms = splitQueryList(route.query.platforms);
    searchForm.reportPlatforms = splitQueryList(route.query.reportPlatforms);
    searchForm.shops = splitQueryList(route.query.shops);
    searchForm.keyword = queryString(route.query.keyword);
}
</script>

<style scoped lang="scss">
.page-container {
    width: 100%;
    min-height: calc(100vh - 96px);
}

.summary-search-card {
    margin-bottom: 16px;
}

.table-card {
    min-width: 0;

    .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 14px;

        &-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-primary);
        }
    }

    .summary-title-group {
        display: flex;
        align-items: baseline;
        gap: 12px;
        min-width: 0;
    }

    .summary-count {
        color: var(--text-tertiary);
        font-size: 12px;
        font-weight: 500;
        white-space: nowrap;
    }

    :deep(.el-card__body) {
        overflow: hidden;
    }
}

.summary-table-card {
    min-height: 0;
}

:deep(.summary-table .summary-edge-column .cell),
:deep(.summary-table th.summary-edge-column .cell) {
    padding-right: 18px !important;
}

.pagination-area {
    flex-shrink: 0;
}

@media (max-width: 768px) {
    .table-card {
        .card-header {
            align-items: flex-start;
            flex-direction: column;
        }

        .summary-title-group {
            align-items: flex-start;
            flex-direction: column;
            gap: 4px;
        }
    }
}
</style>
