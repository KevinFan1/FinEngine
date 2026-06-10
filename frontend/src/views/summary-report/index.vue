<template>
    <div class="page-container page-container--flow">
        <el-card shadow="never" class="search-card summary-search-card">
            <el-form :model="searchForm" inline class="summary-filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker
                        v-model="searchForm.accountingMonth"
                        type="month"
                        placeholder="选择核算年月"
                        clearable
                        value-format="YYYY-MM"
                        style="width: 180px"
                    />
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select
                        v-model="searchForm.orgIds"
                        placeholder="组织"
                        clearable
                        collapse-tags
                        collapse-tags-tooltip
                        filterable
                        multiple
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
                <el-form-item label="归集平台">
                    <el-select
                        v-model="searchForm.platforms"
                        placeholder="归集平台"
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
                <el-form-item label="店铺">
                    <el-select
                        v-model="searchForm.shopIds"
                        placeholder="店铺"
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
                <el-form-item label="搜索">
                    <el-input
                        v-model="searchForm.keyword"
                        clearable
                        placeholder="搜店铺/平台"
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
                        <span class="card-header-title">汇总数据</span>
                        <span class="summary-count"
                            >共 {{ pagination.total }} 条 · 已选
                            {{ selectedCount }} 条</span
                        >
                    </div>
                    <div class="card-header-actions">
                        <el-checkbox v-model="includeDongzhangDetailsInExport">
                            导出附带源明细
                        </el-checkbox>
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
                    v-if="userStore.isSuperAdmin"
                    label="组织"
                    width="170"
                    fixed="left"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        {{ row.org_name || `组织#${row.org_id}` }}
                    </template>
                </el-table-column>
                <el-table-column
                    prop="source_date"
                    label="核算年月"
                    width="108"
                />
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
                    min-width="220"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <button
                            type="button"
                            class="inline-filter-link"
                            @click="applyQuickFilter('shop', row.shop_name)"
                        >
                            <ShopBadge
                                :label="row.shop_name || '-'"
                                :color="row.shop_color"
                                size="table"
                            />
                        </button>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="order_paid_amount"
                    label="订单实付金额"
                    width="130"
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
                    width="120"
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
                    prop="original_gmv"
                    label="实收GMV"
                    width="120"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.original_gmv)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="platform_other_income"
                    label="平台其他收入"
                    width="120"
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
                    width="120"
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
                    prop="original_return_cost"
                    label="退货费用及其他费用"
                    width="130"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.original_return_cost)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    prop="daren_commission"
                    label="达人佣金"
                    width="120"
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
                    width="120"
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
                    width="120"
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
                    width="135"
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
                    width="120"
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
                    width="108"
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
                    width="108"
                    align="right"
                    header-align="right"
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.bic)
                        }}</span>
                    </template>
                </el-table-column>
                <el-table-column
                    label="操作"
                    width="72"
                    align="center"
                    fixed="right"
                >
                    <template #default="{ row }">
                        <el-button
                            type="primary"
                            link
                            @click="openDetailDrawer(row)"
                        >
                            明细
                        </el-button>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty
                        description="暂无汇总数据，请先上传并处理文件"
                        :image-size="80"
                    />
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

        <SummaryDetailDrawer
            v-model="detailDrawerVisible"
            :context="detailContext"
            :selected-org-ids="searchForm.orgIds"
        />
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "SummaryReport" });

import { ref, reactive, computed, onMounted, nextTick } from "vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import type { TableColumnCtx } from "element-plus/es/components/table/index.mjs";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import {
    getSummaryReportList,
    type SummaryReportRecord,
} from "@/api/summary";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import {
    buildExportFilename,
    formatMoney,
    getPlatformLabel,
    summarizeFilenameValues,
} from "@/utils/format";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import {
    getFallbackPlatforms,
    toReportPlatformOptions,
    type PlatformOption,
} from "@/utils/platform";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { usePageRefresh } from "@/composables/pageRefresh";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import SummaryDetailDrawer, {
    type SummaryDetailContext,
} from "@/components/SummaryDetailDrawer.vue";
import { buildSingleMonthParams } from "@/views/accountingFilters";

const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);

interface FilterTag extends ActiveFilterTag {
    key: "accountingMonth" | "orgIds" | "platforms" | "shopIds" | "keyword";
}

interface SummaryTableInstance {
    doLayout: () => void;
    clearSelection: () => void;
    toggleRowSelection: (row: SummaryReportRecord, selected?: boolean) => void;
}

const searchForm = reactive({
    accountingMonth: "",
    orgIds: [] as number[],
    platforms: [] as string[],
    shopIds: [] as number[],
    keyword: "",
});

const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(
    toReportPlatformOptions(platforms.value),
);

const loading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const tableData = ref<SummaryReportRecord[]>([]);
const selectedRows = ref<SummaryReportRecord[]>([]);
const shopLoading = ref(false);
const shopOptions = ref<Shop[]>([]);
const summaryTableRef = ref<SummaryTableInstance>();
const detailDrawerVisible = ref(false);
const detailContext = ref<SummaryDetailContext | null>(null);
const includeDongzhangDetailsInExport = ref(false);

const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

const selectedAccountingMonthParams = computed(() =>
    buildSingleMonthParams(searchForm.accountingMonth, "accounting"),
);

const selectedOrgIdsParam = computed(
    () => searchForm.orgIds.join(",") || undefined,
);

const filteredShopOptions = computed(() => {
    if (!searchForm.platforms.length) return shopOptions.value;
    const selectedPlatforms = new Set(searchForm.platforms);
    return shopOptions.value.filter((shop) =>
        selectedPlatforms.has(shop.platform_name),
    );
});

const selectedReportPlatformsParam = computed(
    () => searchForm.platforms.join(",") || undefined,
);
const selectedShopIdsParam = computed(
    () => searchForm.shopIds.join(",") || undefined,
);
const keywordParam = computed(() => searchForm.keyword.trim() || undefined);
const selectedCount = computed(() => selectedRows.value.length);
const activeFilterTags = computed<FilterTag[]>(() => {
    const tags: FilterTag[] = [];

    if (searchForm.accountingMonth) {
        tags.push({
            key: "accountingMonth",
            label: "核算年月",
            value: searchForm.accountingMonth,
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
            label: "归集平台",
            value: getPlatformLabel(value),
        });
    });
    searchForm.shopIds.forEach((id) => {
        const shop = shopOptions.value.find((item) => item.id === id);
        tags.push({ key: "shopIds", label: "店铺", value: shop?.shop_name || `店铺#${id}` });
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

const moneyColumns = [
    "order_paid_amount",
    "refund_amount",
    "original_gmv",
    "platform_other_income",
    "platform_service_fee",
    "original_return_cost",
    "daren_commission",
    "zhaoshang_service_fee",
    "outside_promotion_fee",
    "service_provider_commission",
    "payment_donation_fee",
    "shipping_insurance",
    "bic",
];

function getSummary(param: {
    columns: TableColumnCtx<SummaryReportRecord>[];
    data: SummaryReportRecord[];
}) {
    const { columns, data } = param;
    const sums: string[] = [];
    columns.forEach((column, index) => {
        const prop = column.property as keyof SummaryReportRecord;
        if (prop === "source_date") {
            sums[index] = "合计";
            return;
        }
        if (!moneyColumns.includes(prop)) {
            sums[index] = "";
            return;
        }
        const total = data.reduce(
            (prev, item) => prev + (Number(item[prop]) || 0),
            0,
        );
        sums[index] = total.toLocaleString("zh-CN", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    });
    return sums;
}

function openDetailDrawer(row: SummaryReportRecord) {
    detailContext.value = {
        sourceYear: row.source_year,
        sourceMonth: row.source_month,
        sourceDate: row.source_date,
        orgId: row.org_id,
        orgName: row.org_name,
        platform: row.source_platform_code || undefined,
        reportPlatform: row.report_platform || row.platform,
        shopName: row.shop_name,
        shopColor: row.shop_color,
        summaryCount: row.summary_count,
    };
    detailDrawerVisible.value = true;
}

async function fetchData() {
    loading.value = true;
    try {
        const res = await getSummaryReportList({
            page: pagination.page,
            page_size: pagination.pageSize,
            org_id: selectedOrgIdsParam.value,
            ...selectedAccountingMonthParams.value,
            report_platform_name: selectedReportPlatformsParam.value,
            shop_ids: selectedShopIdsParam.value,
            keyword: keywordParam.value,
        });
        tableData.value = res.items || [];
        selectedRows.value = [];
        pagination.total = res.total || 0;
    } catch {
        // Error handled by interceptor
    } finally {
        loading.value = false;
        await nextTick();
        summaryTableRef.value?.doLayout();
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
    } catch {
        // Error handled by interceptor
    } finally {
        shopLoading.value = false;
    }
}

function handlePlatformChange() {
    const availableShopIds = new Set(
        filteredShopOptions.value.map((shop) => shop.id),
    );
    searchForm.shopIds = searchForm.shopIds.filter((id) =>
        availableShopIds.has(id),
    );
    fetchShopOptions();
}

function handleOrgChange() {
    const availableShopIds = new Set(
        filteredShopOptions.value.map((shop) => shop.id),
    );
    searchForm.shopIds = searchForm.shopIds.filter((id) =>
        availableShopIds.has(id),
    );
    fetchShopOptions();
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.accountingMonth = "";
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.shopIds = [];
    searchForm.keyword = "";
    pagination.page = 1;
    fetchShopOptions();
    fetchData();
}

function clearSelectedRows() {
    selectedRows.value = [];
    summaryTableRef.value?.clearSelection();
}

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
    platformOptions.value = toReportPlatformOptions(platforms.value);
}

function handleSelectionChange(rows: SummaryReportRecord[]) {
    selectedRows.value = rows;
}

function removeFilterTag(tag: FilterTag) {
    if (tag.key === "accountingMonth") {
        searchForm.accountingMonth = "";
    } else if (tag.key === "orgIds") {
        searchForm.orgIds = searchForm.orgIds.filter((item) => {
            const org = orgOptions.value.find((orgItem) => orgItem.id === item);
            return (org?.name || `组织#${item}`) !== tag.value;
        });
    } else if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter(
            (item) => getPlatformLabel(item) !== tag.value,
        );
    } else if (tag.key === "shopIds") {
        searchForm.shopIds = searchForm.shopIds.filter((id) => {
            const shop = shopOptions.value.find((item) => item.id === id);
            return (shop?.shop_name || `店铺#${id}`) !== tag.value;
        });
    } else if (tag.key === "keyword") {
        searchForm.keyword = "";
    }

    handleOrgChange();
    handleSearch();
}

function applyQuickFilter(type: "reportPlatform" | "shop", value: string) {
    if (!value) return;

    if (type === "reportPlatform") {
        searchForm.platforms = [value];
    } else {
        const shop = shopOptions.value.find((s) => s.shop_name === value);
        if (shop) {
            searchForm.shopIds = [shop.id];
        }
    }

    handlePlatformChange();
    handleSearch();
}

async function handleExport(scope: "all" | "current_page" | "selected") {
    if (scope === "current_page" && tableData.value.length === 0) {
        ElMessage.warning("当前页暂无可导出的数据");
        return;
    }
    if (scope === "selected" && selectedRows.value.length === 0) {
        ElMessage.warning("请先选择要导出的汇总数据");
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
            org_id: selectedOrgIdsParam.value,
            ...selectedAccountingMonthParams.value,
            report_platform_name: selectedReportPlatformsParam.value,
            shop_ids: selectedShopIdsParam.value,
            keyword: keywordParam.value,
            scope,
            ids:
                scope === "selected"
                    ? selectedRows.value.map((row) => row.id).join(",")
                    : undefined,
            page: scope === "current_page" ? pagination.page : undefined,
            page_size:
                scope === "current_page" ? pagination.pageSize : undefined,
            include_dongzhang_details: includeDongzhangDetailsInExport.value,
        };
        const scopeLabel =
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中";
        const filename = normalizeExportFilename(buildExportFilename([
            searchForm.accountingMonth || "全部核算年月",
            `归集平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shopIds.map(id => shopOptions.value.find(s => s.id === id)?.shop_name || `店铺#${id}`), "全部")}`,
            searchForm.keyword.trim()
                ? `关键词${searchForm.keyword.trim()}`
                : "关键词全部",
            "汇总报表",
            includeDongzhangDetailsInExport.value ? "附带源明细" : null,
            scopeLabel,
        ]));
        await submitExportJob({
            export_type: "summary.report",
            title: "汇总报表导出",
            filename,
            params,
        });
    } catch (e) {
        if (!isApiMessageShown(e)) ElMessage.error("导出失败，请稍后重试");
    } finally {
        loadingRef.value = false;
    }
}

function isApiMessageShown(error: unknown): boolean {
    return Boolean(
        error &&
        typeof error === "object" &&
        (error as { __apiMessageShown?: boolean }).__apiMessageShown,
    );
}

async function fetchOrgOptions() {
    if (!userStore.isSuperAdmin) return;
    try {
        orgOptions.value = await getAllOrganizations();
    } catch {
        // Ignore
    }
}

onMounted(async () => {
    await fetchOrgOptions();
    await fetchPlatformOptions();
    await fetchShopOptions();
    fetchData();
});

usePageRefresh(async () => {
    await fetchPlatformOptions();
    await fetchShopOptions();
    await fetchData();
});
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
