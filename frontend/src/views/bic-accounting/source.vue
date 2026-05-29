<template>
    <div class="page-container transaction-page">
        <el-card shadow="never" class="search-card">
            <el-form :model="searchForm" inline class="filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker v-model="searchForm.monthRange" type="monthrange" start-placeholder="核算年月起" end-placeholder="核算年月止" range-separator="至" clearable value-format="YYYY-MM" style="width: 260px" />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select v-model="searchForm.platforms" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="平台" style="width: 190px" @change="handlePlatformChange">
                        <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value">
                            <PlatformBadge :platform="item.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select v-model="searchForm.orgIds" placeholder="组织" multiple clearable collapse-tags collapse-tags-tooltip filterable style="width: 190px" @change="handleOrgChange">
                        <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select v-model="searchForm.shopIds" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="店铺" :loading="shopLoading" style="width: 210px">
                        <el-option v-for="shop in filteredShopOptions" :key="shop.id" :label="shop.shop_name" :value="shop.id">
                            <ShopBadge :label="shop.shop_name" :color="shop.shop_color" size="compact" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="服务商">
                    <el-input v-model="searchForm.serviceProvider" clearable placeholder="服务商，逗号分隔" style="width: 240px" @keyup.enter="handleSearch" />
                </el-form-item>
                <el-form-item label="QIC仓">
                    <el-input v-model="searchForm.qicWarehouse" clearable placeholder="QIC仓" style="width: 180px" @keyup.enter="handleSearch" />
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
                        <span class="card-header-title">源数据</span>
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

            <BicSourceRowsTable
                ref="tableRef"
                selectable
                :rows="tableData"
                :loading="loading"
                :offset="(pagination.page - 1) * pagination.pageSize"
                :show-org="userStore.isSuperAdmin"
                :shop-color-by-name="shopColorByName"
                @selection-change="handleSelectionChange"
            />

            <div class="pagination-area">
                <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="PAGE_SIZE_OPTIONS" :layout="PAGINATION_LAYOUT" background @size-change="fetchData" @current-change="fetchData" />
            </div>
        </el-card>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "BicDetails" });

import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { listBicSourceRows, type BicSourceExportScope, type BicSourceRow } from "@/api/bicAccounting";
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
import BicSourceRowsTable from "./BicSourceRowsTable.vue";
import { monthRangeLabel, splitMonthRange } from "./common";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";

type SourceRowsTableRef = InstanceType<typeof BicSourceRowsTable> & {
    clearSelection: () => void;
};

const loading = ref(false);
const tableRef = ref<SourceRowsTableRef>();
const tableData = ref<BicSourceRow[]>([]);
const selectedRows = ref<BicSourceRow[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const shopOptions = ref<Shop[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(toSourcePlatformOptions(platforms.value));
const shopLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const exportAllLoading = ref(false);
const searchForm = reactive({
    monthRange: null as string[] | null,
    orgIds: [] as number[],
    platforms: [] as string[],
    shopIds: [] as number[],
    serviceProvider: "",
    qicWarehouse: "",
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

interface SourceFilterTag extends ActiveFilterTag {
    key: "monthRange" | "orgIds" | "platforms" | "shopIds" | "serviceProvider" | "qicWarehouse";
}

const activeFilterTags = computed<SourceFilterTag[]>(() => {
    const tags: SourceFilterTag[] = [];
    if (searchForm.monthRange?.length) tags.push({ key: "monthRange", label: "核算年月", value: monthRangeLabel(searchForm.monthRange) });
    searchForm.orgIds.forEach((value) => {
        const org = orgOptions.value.find((item) => item.id === value);
        tags.push({ key: "orgIds", label: "组织", value: org?.name || `组织#${value}` });
    });
    searchForm.platforms.forEach((value) => tags.push({ key: "platforms", label: "平台", value: getPlatformLabel(value) }));
    searchForm.shopIds.forEach((value) => {
        const shop = shopOptions.value.find((item) => item.id === value);
        tags.push({ key: "shopIds", label: "店铺", value: shop?.shop_name || `店铺#${value}` });
    });
    if (searchForm.serviceProvider) tags.push({ key: "serviceProvider", label: "服务商", value: searchForm.serviceProvider });
    if (searchForm.qicWarehouse) tags.push({ key: "qicWarehouse", label: "QIC仓", value: searchForm.qicWarehouse });
    return tags;
});

function queryParams() {
    return {
        page: pagination.page,
        page_size: pagination.pageSize,
        org_id: selectedOrgIdsParam.value,
        platform_code: selectedReportPlatformsParam.value,
        shop_ids: searchForm.shopIds.join(",") || undefined,
        service_provider: searchForm.serviceProvider || undefined,
        qic_warehouse: searchForm.qicWarehouse || undefined,
        ...splitMonthRange(searchForm.monthRange),
    };
}

async function fetchData() {
    loading.value = true;
    try {
        const data = await listBicSourceRows(queryParams());
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
    const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
    searchForm.shopIds = searchForm.shopIds.filter((id) => availableShopIds.has(id));
}

async function handleOrgChange() {
    await fetchShopOptions();
    const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
    searchForm.shopIds = searchForm.shopIds.filter((id) => availableShopIds.has(id));
}

function handleSearch() {
    pagination.page = 1;
    clearSelectedRows();
    fetchData();
}

function handleReset() {
    searchForm.monthRange = null;
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.shopIds = [];
    searchForm.serviceProvider = "";
    searchForm.qicWarehouse = "";
    fetchShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: SourceFilterTag) {
    if (tag.key === "monthRange") searchForm.monthRange = null;
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
    if (tag.key === "shopIds") {
        searchForm.shopIds = searchForm.shopIds.filter((item) => {
            const shop = shopOptions.value.find((s) => s.id === item);
            return (shop?.shop_name || `店铺#${item}`) !== tag.value;
        });
    }
    if (tag.key === "serviceProvider") searchForm.serviceProvider = "";
    if (tag.key === "qicWarehouse") searchForm.qicWarehouse = "";
    handleSearch();
}

function handleSelectionChange(rows: BicSourceRow[]) {
    selectedRows.value = rows;
}

function clearSelectedRows() {
    selectedRows.value = [];
    tableRef.value?.clearSelection();
}

async function handleExport(scope: BicSourceExportScope) {
    if (scope === "selected" && selectedRows.value.length === 0) {
        ElMessage.warning("请先选择要导出的明细");
        return;
    }
    const params: any = { ...queryParams(), scope };
    if (scope === "selected") {
        params.ids = selectedRows.value.map((row) => row.id).join(",");
        delete params.page;
        delete params.page_size;
    }
    if (scope === "all") {
        delete params.page;
        delete params.page_size;
    }

    const loadingRef = scope === "selected" ? exportSelectedLoading : scope === "all" ? exportAllLoading : exportCurrentPageLoading;
    loadingRef.value = true;
    try {
        const filename = normalizeExportFilename(buildExportFilename([
            monthRangeLabel(searchForm.monthRange) || "全部核算年月",
            `平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shopIds.map((id) => shopOptions.value.find((s) => s.id === id)?.shop_name || `店铺#${id}`), "全部")}`,
            `服务商${searchForm.serviceProvider || "全部"}`,
            `QIC仓${searchForm.qicWarehouse || "全部"}`,
            "BIC源明细",
            scope === "all" ? "全部" : scope === "current_page" ? `第${pagination.page}页` : "选中",
        ]));
        await submitExportJob({
            export_type: "bic.source_rows",
            title: "BIC源明细导出",
            filename,
            params,
        });
    } finally {
        loadingRef.value = false;
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
@use "./transaction.scss";
</style>
