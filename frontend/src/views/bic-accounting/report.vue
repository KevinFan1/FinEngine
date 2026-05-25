<template>
    <div class="page-container transaction-page">
        <el-card shadow="never" class="search-card">
            <SearchCardIntro
                kicker="BIC报表"
                title="按店铺查看 BIC 汇总"
                tip="报表汇总来源于 BIC 明细数据"
            />

            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker v-model="searchForm.monthRange" type="monthrange" start-placeholder="开始年月" end-placeholder="结束年月" range-separator="至" clearable value-format="YYYY-MM" style="width: 230px" />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select v-model="searchForm.platforms" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="全部平台" style="width: 190px" @change="handlePlatformChange">
                        <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value">
                            <PlatformBadge :platform="item.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select v-model="searchForm.orgIds" placeholder="全部组织" multiple clearable collapse-tags collapse-tags-tooltip filterable style="width: 190px" @change="handleOrgChange">
                        <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select v-model="searchForm.shopNames" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="全部店铺" :loading="shopLoading" style="width: 210px">
                        <el-option v-for="shop in filteredShopOptions" :key="`${shop.platform_name}-${shop.shop_name}`" :label="shop.shop_name" :value="shop.shop_name">
                            <ShopBadge :label="shop.shop_name" :color="shop.shop_color" size="compact" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="服务商">
                    <el-input v-model="searchForm.serviceProvider" clearable placeholder="输入服务商" style="width: 180px" @keyup.enter="handleSearch" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleSearch">搜索</el-button>
                    <el-button @click="handleReset">重置</el-button>
                </el-form-item>
            </el-form>
            <ActiveFilterTags :tags="activeFilterTags" @remove="removeFilterTag" @clear="handleReset" />
        </el-card>

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">报表数据</span>
                        <span class="summary-count">共 {{ pagination.total }} 条 · 已选 {{ selectedRows.length }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="selectedRows.length === 0" @click="clearSelectedRows">清空选中</el-button>
                        <el-button :loading="exportSelectedLoading" :disabled="selectedRows.length === 0" @click="handleExport('selected')"><el-icon><Download /></el-icon> 导出选中</el-button>
                        <el-button :loading="exportCurrentPageLoading" @click="handleExport('current_page')"><el-icon><Download /></el-icon> 导出当前页</el-button>
                        <el-button type="primary" :loading="exportAllLoading" @click="handleExport('all')"><el-icon><Download /></el-icon> 导出全部</el-button>
                    </div>
                </div>
            </template>

            <el-table ref="tableRef" class="summary-table roomy-table detail-table" :data="tableData" v-loading="loading" stripe border show-summary :summary-method="summaryMethod" row-key="id" height="calc(100vh - 278px)" @selection-change="handleSelectionChange">
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="78" fixed="left" align="center">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column prop="platform_code" label="平台" width="110">
                    <template #default="{ row }"><PlatformBadge :platform="row.platform_code" /></template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" label="组织" width="170" show-overflow-tooltip>
                    <template #default="{ row }">
                        {{ row.org_name || `组织#${row.org_id}` }}
                    </template>
                </el-table-column>
                <el-table-column prop="service_provider" label="服务商" min-width="150" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.service_provider || "-" }}</template>
                </el-table-column>
                <el-table-column prop="store_short_id" label="店铺id" width="120" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.store_short_id || "-" }}</template>
                </el-table-column>
                <el-table-column prop="shop_name" label="店铺名称" min-width="180" show-overflow-tooltip>
                    <template #default="{ row }"><ShopBadge :label="row.shop_name || '-'" :color="shopColorByName.get(row.shop_name || '')" size="table" /></template>
                </el-table-column>
                <el-table-column prop="merchant" label="公司名称" min-width="190" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.merchant || "-" }}</template>
                </el-table-column>
                <el-table-column prop="tax_no" label="税号" min-width="170" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.tax_no || "-" }}</template>
                </el-table-column>
                <el-table-column prop="shop_type" label="抬头类型" width="120" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.shop_type || "-" }}</template>
                </el-table-column>
                <el-table-column prop="registered_address" label="注册地址" min-width="260" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.registered_address || "-" }}</template>
                </el-table-column>
                <el-table-column prop="total_amount" label="结算金额" min-width="160" align="right" header-align="right" class-name="money-column summary-edge-column" header-class-name="money-column summary-edge-column">
                    <template #default="{ row }"><span class="font-mono money-cell">{{ formatAmount(row.total_amount) }}</span></template>
                </el-table-column>
            </el-table>

            <div class="pagination-area">
                <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="PAGE_SIZE_OPTIONS" :layout="PAGINATION_LAYOUT" background @size-change="fetchData" @current-change="fetchData" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "BicReport" });

import type { TableInstance } from "element-plus";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import SearchCardIntro from "@/components/SearchCardIntro.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { exportBicReportsExcel, listBicReports, type BicExportScope, type BicReport } from "@/api/bicAccounting";
import { getPlatformList, type Platform } from "@/api/platform";
import { getShopList, type Shop } from "@/api/shop";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import { usePageRefresh } from "@/composables/pageRefresh";
import {
    buildExportFilename,
    getPlatformLabel,
    summarizeFilenameValues,
} from "@/utils/format";
import { getFallbackPlatforms, getReportPlatformCode, toSourcePlatformOptions, type PlatformOption } from "@/utils/platform";
import { downloadBlob, formatAmount, monthRangeLabel, splitMonthRange } from "./common";

const loading = ref(false);
const tableRef = ref<TableInstance>();
const tableData = ref<BicReport[]>([]);
const selectedRows = ref<BicReport[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const shopOptions = ref<Shop[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(toSourcePlatformOptions(platforms.value));
const shopLoading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const searchForm = reactive({
    monthRange: [] as string[],
    orgIds: [] as number[],
    platforms: [] as string[],
    shopNames: [] as string[],
    serviceProvider: "",
});

const selectedReportPlatformsParam = computed(() => {
    const values = new Set(searchForm.platforms.map((platform) => getReportPlatformCode(platform, platforms.value)).filter(Boolean));
    return Array.from(values).join(",") || undefined;
});
const selectedOrgIdsParam = computed(() => searchForm.orgIds.join(",") || undefined);

const filteredShopOptions = computed(() => {
    if (!searchForm.platforms.length) return shopOptions.value;
    const reportPlatforms = new Set(searchForm.platforms.map((platform) => getReportPlatformCode(platform, platforms.value)).filter(Boolean));
    return shopOptions.value.filter((shop) => reportPlatforms.has(shop.platform_name));
});

const shopColorByName = computed(() => {
    const map = new Map<string, string | undefined>();
    shopOptions.value.forEach((shop) => {
        if (!map.has(shop.shop_name)) map.set(shop.shop_name, shop.shop_color);
    });
    return map;
});

interface ReportFilterTag extends ActiveFilterTag {
    key: "monthRange" | "orgIds" | "platforms" | "shopNames" | "serviceProvider";
}

const activeFilterTags = computed<ReportFilterTag[]>(() => {
    const tags: ReportFilterTag[] = [];
    if (searchForm.monthRange.length) tags.push({ key: "monthRange", label: "核算年月", value: monthRangeLabel(searchForm.monthRange) });
    searchForm.orgIds.forEach((value) => {
        const org = orgOptions.value.find((item) => item.id === value);
        tags.push({ key: "orgIds", label: "组织", value: org?.name || `组织#${value}` });
    });
    searchForm.platforms.forEach((value) => tags.push({ key: "platforms", label: "平台", value: getPlatformLabel(value) }));
    searchForm.shopNames.forEach((value) => tags.push({ key: "shopNames", label: "店铺", value }));
    if (searchForm.serviceProvider) tags.push({ key: "serviceProvider", label: "服务商", value: searchForm.serviceProvider });
    return tags;
});

function queryParams() {
    return {
        page: pagination.page,
        page_size: pagination.pageSize,
        org_id: selectedOrgIdsParam.value,
        platform_code: selectedReportPlatformsParam.value,
        shop_name: searchForm.shopNames.join(",") || undefined,
        service_provider: searchForm.serviceProvider || undefined,
        ...splitMonthRange(searchForm.monthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await listBicReports(queryParams());
        tableData.value = data.items;
        pagination.total = data.total;
    } finally {
        loading.value = false;
    }
}

async function fetchShopOptions() {
    shopLoading.value = true;
    try {
        const res = await getShopList({ page: 1, page_size: 100, org_id: selectedOrgIdsParam.value, platform_name: selectedReportPlatformsParam.value });
        shopOptions.value = res.items || [];
    } finally {
        shopLoading.value = false;
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

async function fetchPlatformOptions() {
    try {
        const res = await getPlatformList();
        platforms.value = res.length ? res : getFallbackPlatforms();
    } catch {
        platforms.value = getFallbackPlatforms();
    }
    platformOptions.value = toSourcePlatformOptions(platforms.value);
}

async function handlePlatformChange() {
    await fetchShopOptions();
    const availableShopNames = new Set(filteredShopOptions.value.map((shop) => shop.shop_name));
    searchForm.shopNames = searchForm.shopNames.filter((shopName) => availableShopNames.has(shopName));
}

async function handleOrgChange() {
    await fetchShopOptions();
    const availableShopNames = new Set(filteredShopOptions.value.map((shop) => shop.shop_name));
    searchForm.shopNames = searchForm.shopNames.filter((shopName) => availableShopNames.has(shopName));
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.monthRange = [];
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.shopNames = [];
    searchForm.serviceProvider = "";
    fetchShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: ReportFilterTag) {
    if (tag.key === "monthRange") searchForm.monthRange = [];
    if (tag.key === "orgIds") {
        searchForm.orgIds = searchForm.orgIds.filter((item) => {
            const org = orgOptions.value.find((orgItem) => orgItem.id === item);
            return (org?.name || `组织#${item}`) !== tag.value;
        });
        await handleOrgChange();
    }
    if (tag.key === "platforms") {
        searchForm.platforms = searchForm.platforms.filter((item) => getPlatformLabel(item) !== tag.value);
        await handlePlatformChange();
    }
    if (tag.key === "shopNames") searchForm.shopNames = searchForm.shopNames.filter((item) => item !== tag.value);
    if (tag.key === "serviceProvider") searchForm.serviceProvider = "";
    handleSearch();
}

function handleSelectionChange(rows: BicReport[]) {
    selectedRows.value = rows;
}

function clearSelectedRows() {
    selectedRows.value = [];
    tableRef.value?.clearSelection();
}

async function handleExport(scope: BicExportScope) {
    const params: any = { ...queryParams(), scope };
    if (scope === "selected") params.ids = selectedRows.value.map((row) => row.id).join(",");
    if (scope === "current_page") {
        params.page = pagination.page;
        params.page_size = pagination.pageSize;
    }
    if (scope === "all") {
        delete params.page;
        delete params.page_size;
    }
    const loadingRef = scope === "selected" ? exportSelectedLoading : scope === "current_page" ? exportCurrentPageLoading : exportAllLoading;
    loadingRef.value = true;
    try {
        const blob = await exportBicReportsExcel(params);
        const filename = buildExportFilename([
            monthRangeLabel(searchForm.monthRange) || "全部核算年月",
            `平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shopNames, "全部")}`,
            `服务商${searchForm.serviceProvider || "全部"}`,
            "BIC报表",
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中",
        ]);
        downloadBlob(blob, filename);
    } finally {
        loadingRef.value = false;
    }
}

function summaryMethod({ columns, data }: { columns: any[]; data: BicReport[] }) {
    return columns.map((column, index) => {
        if (index === 1) return "合计";
        if (column.property === "total_amount") return formatAmount(data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0));
        return "";
    });
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
@use "./transaction.scss";

:deep(.summary-table .summary-edge-column .cell),
:deep(.summary-table th.summary-edge-column .cell) {
    padding-right: 18px !important;
}
</style>
