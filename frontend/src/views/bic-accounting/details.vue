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
                        <span class="card-header-title">汇总数据</span>
                        <span class="summary-count">共 {{ pagination.total }} 条 · 已选 {{ selectedRows.length }} 条</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="selectedRows.length === 0" @click="clearSelectedRows">清空选中</el-button>
                        <el-button :loading="exportSelectedLoading" :disabled="selectedRows.length === 0" @click="handleExport('selected')"><el-icon><Download /></el-icon> 导出选中</el-button>
                        <el-button :loading="exportCurrentPageLoading" @click="handleExport('current_page')"><el-icon><Download /></el-icon> 导出当前页</el-button>
                        <el-button type="primary" :loading="exportAllLoading" @click="handleExport('all')"><el-icon><Download /></el-icon> 导出全部</el-button>
                        <el-button type="primary" plain @click="openReconciliationDialog"><el-icon><Download /></el-icon> 汇总导出</el-button>
                    </div>
                </div>
            </template>

            <el-table ref="tableRef" class="summary-table roomy-table detail-table" :data="tableData" v-loading="loading" stripe border show-summary :summary-method="summaryMethod" row-key="id" @selection-change="handleSelectionChange">
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="78" fixed="left" align="center">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column prop="accounting_year" label="核算年月" width="112" align="center">
                    <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
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
                <el-table-column prop="qic_warehouse" label="QIC仓" min-width="160" show-overflow-tooltip>
                    <template #default="{ row }">{{ row.qic_warehouse || "-" }}</template>
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
                <el-table-column label="源数据" width="110" fixed="right" align="center">
                    <template #default="{ row }">
                        <el-button link type="primary" @click="openSourceRows(row)">查看</el-button>
                    </template>
                </el-table-column>
            </el-table>

            <div class="pagination-area">
                <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="PAGE_SIZE_OPTIONS" :layout="PAGINATION_LAYOUT" background @size-change="fetchData" @current-change="fetchData" />
            </div>
        </el-card>

        <el-drawer v-model="sourceDrawerVisible" :title="sourceDrawerTitle" size="92%" class="bic-source-drawer">
            <el-form :model="drawerSearchForm" inline class="filter-form drawer-filter-form">
                <el-form-item label="核算年月">
                    <el-date-picker v-model="drawerSearchForm.monthRange" type="monthrange" start-placeholder="核算年月起" end-placeholder="核算年月止" range-separator="至" clearable value-format="YYYY-MM" style="width: 260px" />
                </el-form-item>
                <el-form-item label="平台">
                    <el-select v-model="drawerSearchForm.platforms" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="平台" style="width: 190px">
                        <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value">
                            <PlatformBadge :platform="item.value" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                    <el-select v-model="drawerSearchForm.orgIds" placeholder="组织" multiple clearable collapse-tags collapse-tags-tooltip filterable style="width: 190px">
                        <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
                    </el-select>
                </el-form-item>
                <el-form-item label="店铺">
                    <el-select v-model="drawerSearchForm.shopIds" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="店铺" style="width: 210px">
                        <el-option v-for="shop in filteredShopOptions" :key="shop.id" :label="shop.shop_name" :value="shop.id">
                            <ShopBadge :label="shop.shop_name" :color="shop.shop_color" size="compact" />
                        </el-option>
                    </el-select>
                </el-form-item>
                <el-form-item label="服务商">
                    <el-input v-model="drawerSearchForm.serviceProvider" clearable placeholder="服务商，逗号分隔" style="width: 240px" @keyup.enter="handleDrawerSearch" />
                </el-form-item>
                <el-form-item label="QIC仓">
                    <el-input v-model="drawerSearchForm.qicWarehouse" clearable placeholder="QIC仓" style="width: 180px" @keyup.enter="handleDrawerSearch" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleDrawerSearch">搜索</el-button>
                    <el-button @click="handleDrawerReset">重置</el-button>
                </el-form-item>
            </el-form>
            <BicSourceRowsTable
                :rows="sourceRows"
                :loading="sourceLoading"
                :offset="(sourcePagination.page - 1) * sourcePagination.pageSize"
                :show-org="userStore.isSuperAdmin"
                :shop-color-by-name="shopColorByName"
                height="calc(100vh - 340px)"
            />
            <div class="pagination-area">
                <el-pagination v-model:current-page="sourcePagination.page" v-model:page-size="sourcePagination.pageSize" :total="sourcePagination.total" :page-sizes="PAGE_SIZE_OPTIONS" :layout="PAGINATION_LAYOUT" background @size-change="fetchSourceRows" @current-change="fetchSourceRows" />
            </div>
        </el-drawer>

        <el-dialog v-model="reconciliationDialogVisible" width="760px" top="8vh" :close-on-click-modal="false" class="bic-reconciliation-dialog">
            <template #header>
                <div class="reconciliation-dialog-header">
                    <div>
                        <div class="reconciliation-dialog-kicker">BIC汇总导出</div>
                        <div class="reconciliation-dialog-title">导出 BIC 对账表</div>
                        <div class="reconciliation-dialog-subtitle">单次仅支持单个月份和单个服务商，其他条件用于缩小本次导出范围。</div>
                    </div>
                    <el-button text @click="syncReconciliationFormFromListFilters">带入列表条件</el-button>
                </div>
            </template>

            <div class="reconciliation-dialog-body">
                <section class="reconciliation-panel">
                    <div class="reconciliation-panel-header">
                        <div class="reconciliation-panel-title">基础条件</div>
                        <div class="reconciliation-panel-note">这两项决定导出的主范围</div>
                    </div>
                    <el-form :model="reconciliationForm" label-position="top" class="reconciliation-form">
                        <div class="reconciliation-form-grid">
                            <el-form-item label="核算月份" required>
                                <el-date-picker v-model="reconciliationForm.accountingMonth" type="month" value-format="YYYY-MM" placeholder="选择单个月份" style="width: 100%" />
                            </el-form-item>
                            <el-form-item label="服务商" required>
                                <el-select v-model="reconciliationForm.serviceProvider" clearable filterable allow-create default-first-option reserve-keyword placeholder="输入或选择单个服务商" style="width: 100%">
                                    <el-option v-for="item in reconciliationProviderOptions" :key="item" :label="item" :value="item" />
                                </el-select>
                            </el-form-item>
                        </div>
                    </el-form>
                </section>

                <section class="reconciliation-panel">
                    <div class="reconciliation-panel-header">
                        <div>
                            <div class="reconciliation-panel-title">附加范围</div>
                            <div class="reconciliation-panel-note">只影响这次导出，不会改动当前列表筛选</div>
                        </div>
                        <el-button text @click="reconciliationAdvancedVisible = !reconciliationAdvancedVisible">{{ reconciliationAdvancedVisible ? "收起条件" : "展开条件" }}</el-button>
                    </div>
                    <el-form v-show="reconciliationAdvancedVisible" :model="reconciliationForm" label-position="top" class="reconciliation-form">
                        <div class="reconciliation-form-grid reconciliation-form-grid--advanced">
                            <el-form-item v-if="userStore.isSuperAdmin" label="组织">
                                <el-select v-model="reconciliationForm.orgIds" multiple clearable collapse-tags collapse-tags-tooltip filterable placeholder="全部组织" style="width: 100%" @change="handleReconciliationOrgChange">
                                    <el-option v-for="org in orgOptions" :key="org.id" :label="org.name" :value="org.id" />
                                </el-select>
                            </el-form-item>
                            <el-form-item label="平台">
                                <el-select v-model="reconciliationForm.platforms" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="全部平台" style="width: 100%" @change="handleReconciliationPlatformChange">
                                    <el-option v-for="item in platformOptions" :key="item.value" :label="item.label" :value="item.value">
                                        <PlatformBadge :platform="item.value" />
                                    </el-option>
                                </el-select>
                            </el-form-item>
                            <el-form-item label="店铺">
                                <el-select v-model="reconciliationForm.shopIds" clearable filterable multiple collapse-tags collapse-tags-tooltip placeholder="全部店铺" :loading="reconciliationShopLoading" style="width: 100%">
                                    <el-option v-for="shop in reconciliationFilteredShopOptions" :key="shop.id" :label="shop.shop_name" :value="shop.id">
                                        <ShopBadge :label="shop.shop_name" :color="shop.shop_color" size="compact" />
                                    </el-option>
                                </el-select>
                            </el-form-item>
                            <el-form-item label="QIC仓">
                                <el-input v-model="reconciliationForm.qicWarehouse" clearable placeholder="全部QIC仓" />
                            </el-form-item>
                        </div>
                    </el-form>
                </section>

                <section class="reconciliation-preview">
                    <div class="reconciliation-preview-header">
                        <div class="reconciliation-panel-title">导出预览</div>
                        <div class="reconciliation-panel-note">导出包含汇总和统一明细两个 sheet，明细会额外带出店铺列。</div>
                    </div>
                    <div class="reconciliation-preview-grid">
                        <div class="reconciliation-preview-card">
                            <span class="reconciliation-preview-label">预计命中源数据</span>
                            <strong v-if="reconciliationPreviewLoading" class="reconciliation-preview-value">计算中...</strong>
                            <strong v-else class="reconciliation-preview-value">{{ reconciliationPreviewCountLabel }}</strong>
                        </div>
                        <div class="reconciliation-preview-card reconciliation-preview-card--wide">
                            <span class="reconciliation-preview-label">导出文件名</span>
                            <strong class="reconciliation-preview-filename">{{ reconciliationPreviewFilename }}</strong>
                        </div>
                    </div>
                    <el-alert v-if="reconciliationPreviewHint" :title="reconciliationPreviewHint" :type="reconciliationPreviewAlertType" :closable="false" show-icon />
                </section>
            </div>

            <template #footer>
                <div class="reconciliation-dialog-footer">
                    <el-button @click="handleReconciliationDialogReset">清空条件</el-button>
                    <el-button @click="reconciliationDialogVisible = false">取消</el-button>
                    <el-button type="primary" :loading="exportReconciliationLoading" :disabled="reconciliationExportDisabled" @click="handleReconciliationExport">导出汇总</el-button>
                </div>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
defineOptions({ name: "BicSummary" });

import { ElMessage, type TableInstance } from "element-plus";
import { useUserStore } from "@/stores/user";
import { getAllOrganizations, type Organization } from "@/api/organization";
import ActiveFilterTags from "@/components/ActiveFilterTags.vue";
import type { ActiveFilterTag } from "@/components/activeFilterTags";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { listBicDetails, listBicSourceRows, type BicDetail, type BicExportScope, type BicSourceRow } from "@/api/bicAccounting";
import BicSourceRowsTable from "./BicSourceRowsTable.vue";
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
import { formatAmount, formatMonth, monthRangeLabel, splitMonthRange } from "./common";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";

const loading = ref(false);
const tableRef = ref<TableInstance>();
const tableData = ref<BicDetail[]>([]);
const selectedRows = ref<BicDetail[]>([]);
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const userStore = useUserStore();
const orgOptions = ref<Organization[]>([]);
const shopOptions = ref<Shop[]>([]);
const platforms = ref<Platform[]>(getFallbackPlatforms());
const platformOptions = ref<PlatformOption[]>(toSourcePlatformOptions(platforms.value));
const shopLoading = ref(false);
const reconciliationShopLoading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const exportReconciliationLoading = ref(false);
const reconciliationDialogVisible = ref(false);
const reconciliationAdvancedVisible = ref(false);
const reconciliationPreviewLoading = ref(false);
const reconciliationPreviewTotal = ref<number | null>(null);
const reconciliationShopOptions = ref<Shop[]>([]);
const sourceDrawerVisible = ref(false);
const sourceLoading = ref(false);
const sourceDetail = ref<BicDetail | null>(null);
const sourceRows = ref<BicSourceRow[]>([]);
const sourcePagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const reconciliationForm = reactive({
    accountingMonth: "",
    orgIds: [] as number[],
    platforms: [] as string[],
    shopIds: [] as number[],
    serviceProvider: "",
    qicWarehouse: "",
});
const drawerSearchForm = reactive({
    monthRange: null as string[] | null,
    orgIds: [] as number[],
    platforms: [] as string[],
    shopIds: [] as number[],
    serviceProvider: "",
    qicWarehouse: "",
});
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

interface DetailFilterTag extends ActiveFilterTag {
    key: "monthRange" | "orgIds" | "platforms" | "shopIds" | "serviceProvider" | "qicWarehouse";
}

const activeFilterTags = computed<DetailFilterTag[]>(() => {
    const tags: DetailFilterTag[] = [];
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

const sourceDrawerTitle = computed(() => {
    const row = sourceDetail.value;
    if (!row) return "源数据";
    return `${formatMonth(row.accounting_year, row.accounting_month)} · ${row.shop_name || "-"} · ${row.service_provider || "-"} · ${row.qic_warehouse || "-"}`;
});

const reconciliationProviderOptions = computed(() => {
    const values = new Set<string>();
    tableData.value.forEach((row) => {
        const value = (row.service_provider || "").trim();
        if (value) values.add(value);
    });
    const currentProvider = singleProviderValue(reconciliationForm.serviceProvider);
    if (currentProvider) values.add(currentProvider);
    return Array.from(values).sort((left, right) => left.localeCompare(right, "zh-CN"));
});

const reconciliationSelectedOrgIdsParam = computed(() => reconciliationForm.orgIds.join(",") || undefined);
const reconciliationSelectedReportPlatformsParam = computed(() => {
    const values = new Set(reconciliationForm.platforms.map((platform) => getReportPlatformCode(platform, platforms.value)).filter(Boolean));
    return Array.from(values).join(",") || undefined;
});

const reconciliationFilteredShopOptions = computed(() => {
    if (!reconciliationForm.platforms.length) return reconciliationShopOptions.value;
    const reportPlatforms = new Set(reconciliationForm.platforms.map((platform) => getReportPlatformCode(platform, platforms.value)).filter(Boolean));
    return reconciliationShopOptions.value.filter((shop) => reportPlatforms.has(shop.platform_name));
});

const reconciliationSelectedMonth = computed(() => selectedMonthFromValue(reconciliationForm.accountingMonth));
const reconciliationSelectedProvider = computed(() => singleProviderValue(reconciliationForm.serviceProvider));
const reconciliationPreviewFilename = computed(() => buildExportFilename([
    reconciliationForm.accountingMonth || "待选月份",
    reconciliationSelectedProvider.value || "待选服务商",
    "BIC对账表",
]));
const reconciliationPreviewCountLabel = computed(() => {
    if (!reconciliationCanPreview()) return "待补齐条件";
    if (reconciliationPreviewTotal.value === null) return "待计算";
    return `${reconciliationPreviewTotal.value.toLocaleString("zh-CN")} 行`;
});
const reconciliationPreviewAlertType = computed(() => {
    if (!reconciliationCanPreview()) return "warning";
    if (reconciliationPreviewTotal.value === 0) return "info";
    return "success";
});
const reconciliationPreviewHint = computed(() => {
    if (!reconciliationCanPreview()) return "先选择单个月份和单个服务商，再预估本次导出范围。";
    if (reconciliationPreviewLoading.value) return "正在根据当前条件计算可导出的源数据范围。";
    if (reconciliationPreviewTotal.value === 0) return "当前条件会导出一个仅含表头的空白工作簿。";
    if (reconciliationPreviewTotal.value !== null) return `当前条件预计命中 ${reconciliationPreviewTotal.value.toLocaleString("zh-CN")} 行源数据，将提交到下载中心生成。`;
    return "";
});
const reconciliationExportDisabled = computed(() => {
    if (!reconciliationSelectedMonth.value || !reconciliationSelectedProvider.value) return true;
    return false;
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
        const data = await listBicDetails(queryParams());
        tableData.value = data.items;
        pagination.total = data.total;
    } finally {
        loading.value = false;
    }
}

const drawerSelectedReportPlatformsParam = computed(() => {
    const values = new Set(drawerSearchForm.platforms.map((platform) => getReportPlatformCode(platform, platforms.value)).filter(Boolean));
    return Array.from(values).join(",") || undefined;
});
const drawerSelectedOrgIdsParam = computed(() => drawerSearchForm.orgIds.join(",") || undefined);

async function fetchSourceRows() {
    if (!sourceDetail.value) return;
    sourceLoading.value = true;
    try {
        const data = await listBicSourceRows({
            detail_id: sourceDetail.value.id,
            page: sourcePagination.page,
            page_size: sourcePagination.pageSize,
            org_id: drawerSelectedOrgIdsParam.value,
            platform_code: drawerSelectedReportPlatformsParam.value,
            shop_ids: drawerSearchForm.shopIds.join(",") || undefined,
            service_provider: drawerSearchForm.serviceProvider || undefined,
            qic_warehouse: drawerSearchForm.qicWarehouse || undefined,
            ...splitMonthRange(drawerSearchForm.monthRange),
        });
        sourceRows.value = data.items;
        sourcePagination.total = data.total;
    } finally {
        sourceLoading.value = false;
    }
}

async function fetchPageShopOptions() {
    shopLoading.value = true;
    try {
        const res = await getShopList({ page: 1, page_size: 100, org_id: selectedOrgIdsParam.value, platform_name: selectedReportPlatformsParam.value });
        shopOptions.value = res.items || [];
    } finally {
        shopLoading.value = false;
    }
}

async function fetchReconciliationShopOptions() {
    reconciliationShopLoading.value = true;
    try {
        const res = await getShopList({ page: 1, page_size: 100, org_id: reconciliationSelectedOrgIdsParam.value, platform_name: reconciliationSelectedReportPlatformsParam.value });
        reconciliationShopOptions.value = res.items || [];
    } finally {
        reconciliationShopLoading.value = false;
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
    await fetchPageShopOptions();
    const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
    searchForm.shopIds = searchForm.shopIds.filter((id) => availableShopIds.has(id));
}

async function handleOrgChange() {
    await fetchPageShopOptions();
    const availableShopIds = new Set(filteredShopOptions.value.map((shop) => shop.id));
    searchForm.shopIds = searchForm.shopIds.filter((id) => availableShopIds.has(id));
}

function handleSearch() {
    pagination.page = 1;
    fetchData();
}

function handleReset() {
    searchForm.monthRange = null;
    searchForm.orgIds = [];
    searchForm.platforms = [];
    searchForm.shopIds = [];
    searchForm.serviceProvider = "";
    searchForm.qicWarehouse = "";
    fetchPageShopOptions();
    handleSearch();
}

async function removeFilterTag(tag: DetailFilterTag) {
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

function handleSelectionChange(rows: BicDetail[]) {
    selectedRows.value = rows;
}

function clearSelectedRows() {
    selectedRows.value = [];
    tableRef.value?.clearSelection();
}

function openSourceRows(row: BicDetail) {
    sourceDetail.value = row;
    sourcePagination.page = 1;
    sourceRows.value = [];
    drawerSearchForm.monthRange = [...searchForm.monthRange];
    drawerSearchForm.orgIds = [...searchForm.orgIds];
    drawerSearchForm.platforms = [...searchForm.platforms];
    drawerSearchForm.shopIds = [...searchForm.shopIds];
    drawerSearchForm.serviceProvider = searchForm.serviceProvider;
    drawerSearchForm.qicWarehouse = searchForm.qicWarehouse;
    sourceDrawerVisible.value = true;
    fetchSourceRows();
}

function selectedMonthFromRange(range: string[]) {
    const [start, end] = range;
    const month = start && (!end || start === end) ? start : "";
    if (!month) return null;
    return selectedMonthFromValue(month);
}

function selectedMonthFromValue(month: string) {
    if (!month) return null;
    const [year, monthNumber] = month.split("-").map(Number);
    if (!year || !monthNumber) return null;
    return { accounting_year: year, accounting_month: monthNumber };
}

function singleProviderValue(value: string) {
    const providerValues = value.split(/[,，]/).map((item) => item.trim()).filter(Boolean);
    return providerValues.length === 1 ? providerValues[0] : "";
}

function reconciliationCanPreview() {
    return Boolean(reconciliationSelectedMonth.value && reconciliationSelectedProvider.value);
}

async function syncReconciliationFormFromListFilters() {
    const currentMonth = selectedMonthFromRange(searchForm.monthRange);
    reconciliationForm.accountingMonth = currentMonth ? `${currentMonth.accounting_year}-${String(currentMonth.accounting_month).padStart(2, "0")}` : "";
    reconciliationForm.orgIds = [...searchForm.orgIds];
    reconciliationForm.platforms = [...searchForm.platforms];
    reconciliationForm.shopIds = [...searchForm.shopIds];
    reconciliationForm.serviceProvider = singleProviderValue(searchForm.serviceProvider);
    reconciliationForm.qicWarehouse = searchForm.qicWarehouse;
    reconciliationAdvancedVisible.value = Boolean(
        reconciliationForm.orgIds.length ||
        reconciliationForm.platforms.length ||
        reconciliationForm.shopIds.length ||
        reconciliationForm.qicWarehouse,
    );
    await fetchReconciliationShopOptions();
}

async function openReconciliationDialog() {
    await syncReconciliationFormFromListFilters();
    reconciliationDialogVisible.value = true;
    scheduleReconciliationPreview();
}

async function handleReconciliationPlatformChange() {
    await fetchReconciliationShopOptions();
    const availableShopIds = new Set(reconciliationFilteredShopOptions.value.map((shop) => shop.id));
    reconciliationForm.shopIds = reconciliationForm.shopIds.filter((id) => availableShopIds.has(id));
}

async function handleReconciliationOrgChange() {
    await fetchReconciliationShopOptions();
    const availableShopIds = new Set(reconciliationFilteredShopOptions.value.map((shop) => shop.id));
    reconciliationForm.shopIds = reconciliationForm.shopIds.filter((id) => availableShopIds.has(id));
}

async function handleReconciliationDialogReset() {
    reconciliationForm.accountingMonth = "";
    reconciliationForm.orgIds = [];
    reconciliationForm.platforms = [];
    reconciliationForm.shopIds = [];
    reconciliationForm.serviceProvider = "";
    reconciliationForm.qicWarehouse = "";
    reconciliationAdvancedVisible.value = false;
    reconciliationPreviewTotal.value = null;
    await fetchReconciliationShopOptions();
}

function handleDrawerSearch() {
    sourcePagination.page = 1;
    fetchSourceRows();
}

function handleDrawerReset() {
    drawerSearchForm.monthRange = [];
    drawerSearchForm.orgIds = [];
    drawerSearchForm.platforms = [];
    drawerSearchForm.shopIds = [];
    drawerSearchForm.serviceProvider = "";
    drawerSearchForm.qicWarehouse = "";
    handleDrawerSearch();
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
        const filename = normalizeExportFilename(buildExportFilename([
            monthRangeLabel(searchForm.monthRange) || "全部核算年月",
            `平台${summarizeFilenameValues(searchForm.platforms.map(getPlatformLabel), "全部")}`,
            `店铺${summarizeFilenameValues(searchForm.shopIds.map((id) => shopOptions.value.find((s) => s.id === id)?.shop_name || String(id)), "全部")}`,
            `服务商${searchForm.serviceProvider || "全部"}`,
            `QIC仓${searchForm.qicWarehouse || "全部"}`,
            "BIC汇总",
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中",
        ]));
        await submitExportJob({
            export_type: "bic.details",
            title: "BIC汇总导出",
            filename,
            params,
        });
    } finally {
        loadingRef.value = false;
    }
}

async function handleReconciliationExport() {
    const selectedMonth = reconciliationSelectedMonth.value;
    if (!selectedMonth) {
        ElMessage.warning("导出汇总需要选择单个核算月份");
        return;
    }
    const provider = reconciliationSelectedProvider.value;
    if (!provider) {
        ElMessage.warning("导出汇总需要填写单个服务商");
        return;
    }

    exportReconciliationLoading.value = true;
    try {
        const params = {
            ...selectedMonth,
            org_id: reconciliationSelectedOrgIdsParam.value,
            platform_code: reconciliationSelectedReportPlatformsParam.value,
            shop_ids: reconciliationForm.shopIds.join(",") || undefined,
            service_provider: provider,
            qic_warehouse: reconciliationForm.qicWarehouse || undefined,
        };
        const filename = normalizeExportFilename(buildExportFilename([
            formatMonth(selectedMonth.accounting_year, selectedMonth.accounting_month),
            provider,
            "BIC对账表",
        ]));
        await submitExportJob({
            export_type: "bic.reconciliation",
            title: "BIC对账表导出",
            filename,
            params,
        });
        reconciliationDialogVisible.value = false;
    } finally {
        exportReconciliationLoading.value = false;
    }
}

function summaryMethod({ columns, data }: { columns: any[]; data: BicDetail[] }) {
    return columns.map((column, index) => {
        if (index === 1) return "合计";
        if (column.property === "total_amount") return formatAmount(data.reduce((sum, item) => sum + Number(item.total_amount || 0), 0));
        return "";
    });
}

onMounted(async () => {
    await fetchOrgOptions();
    await fetchPlatformOptions();
    await fetchPageShopOptions();
    await fetchReconciliationShopOptions();
    fetchData();
});

usePageRefresh(async () => {
    await fetchPlatformOptions();
    await fetchPageShopOptions();
    await fetchReconciliationShopOptions();
    await fetchData();
});

let reconciliationPreviewTimer: ReturnType<typeof setTimeout> | null = null;
let reconciliationPreviewTicket = 0;

function scheduleReconciliationPreview() {
    if (reconciliationPreviewTimer) window.clearTimeout(reconciliationPreviewTimer);
    if (!reconciliationDialogVisible.value) return;
    reconciliationPreviewTimer = window.setTimeout(() => {
        void fetchReconciliationPreview();
    }, 220);
}

async function fetchReconciliationPreview() {
    if (!reconciliationDialogVisible.value) return;
    if (!reconciliationCanPreview()) {
        reconciliationPreviewTotal.value = null;
        reconciliationPreviewLoading.value = false;
        return;
    }
    const ticket = ++reconciliationPreviewTicket;
    reconciliationPreviewLoading.value = true;
    try {
        const data = await listBicSourceRows({
            page: 1,
            page_size: 1,
            org_id: reconciliationSelectedOrgIdsParam.value,
            platform_code: reconciliationSelectedReportPlatformsParam.value,
            shop_ids: reconciliationForm.shopIds.join(",") || undefined,
            service_provider: reconciliationSelectedProvider.value || undefined,
            qic_warehouse: reconciliationForm.qicWarehouse || undefined,
            accounting_year: reconciliationSelectedMonth.value?.accounting_year,
            accounting_month: reconciliationSelectedMonth.value?.accounting_month,
        });
        if (ticket !== reconciliationPreviewTicket) return;
        reconciliationPreviewTotal.value = data.total;
    } finally {
        if (ticket === reconciliationPreviewTicket) reconciliationPreviewLoading.value = false;
    }
}

watch(
    () => [
        reconciliationDialogVisible.value,
        reconciliationForm.accountingMonth,
        reconciliationForm.serviceProvider,
        reconciliationForm.qicWarehouse,
        reconciliationForm.shopIds.join(","),
        reconciliationSelectedOrgIdsParam.value || "",
        reconciliationSelectedReportPlatformsParam.value || "",
    ],
    () => {
        scheduleReconciliationPreview();
    },
);
</script>

<style scoped lang="scss">
@use "./transaction.scss";

:deep(.summary-table .summary-edge-column .cell),
:deep(.summary-table th.summary-edge-column .cell) {
    padding-right: 18px !important;
}

.drawer-filter-form {
    padding: 0 0 12px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    margin-bottom: 12px;
}

.reconciliation-dialog-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.reconciliation-dialog-kicker {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    letter-spacing: 0.04em;
}

.reconciliation-dialog-title {
    font-size: 20px;
    font-weight: 600;
    color: #0f172a;
    margin-top: 4px;
}

.reconciliation-dialog-subtitle {
    font-size: 13px;
    color: #64748b;
    margin-top: 6px;
}

.reconciliation-dialog-body {
    display: grid;
    gap: 14px;
}

.reconciliation-panel,
.reconciliation-preview {
    border: 1px solid #dbe4f0;
    border-radius: 10px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    padding: 16px;
}

.reconciliation-panel-header,
.reconciliation-preview-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
}

.reconciliation-panel-title {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
}

.reconciliation-panel-note {
    font-size: 12px;
    color: #64748b;
    margin-top: 4px;
}

.reconciliation-form :deep(.el-form-item) {
    margin-bottom: 0;
}

.reconciliation-form-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px 16px;
}

.reconciliation-form-grid--advanced {
    align-items: start;
}

.reconciliation-preview-grid {
    display: grid;
    grid-template-columns: minmax(0, 180px) minmax(0, 1fr);
    gap: 12px;
    margin-bottom: 12px;
}

.reconciliation-preview-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 14px;
    min-height: 78px;
}

.reconciliation-preview-card--wide {
    background: #fefefe;
}

.reconciliation-preview-label {
    display: block;
    font-size: 12px;
    color: #64748b;
    margin-bottom: 8px;
}

.reconciliation-preview-value {
    font-size: 24px;
    line-height: 1.2;
    color: #0f172a;
}

.reconciliation-preview-filename {
    display: block;
    font-size: 14px;
    line-height: 1.5;
    color: #0f172a;
    word-break: break-all;
}

.reconciliation-dialog-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
}

@media (max-width: 768px) {
    .reconciliation-dialog-header,
    .reconciliation-panel-header,
    .reconciliation-preview-header,
    .reconciliation-dialog-footer {
        flex-direction: column;
        align-items: stretch;
    }

    .reconciliation-form-grid,
    .reconciliation-preview-grid {
        grid-template-columns: minmax(0, 1fr);
    }
}
</style>
