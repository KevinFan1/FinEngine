<template>
    <div class="page-container transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :shop-loading="shopLoading"
            show-bank-status
            keyword-placeholder="我方主体/收款商家"
            @update:model="handleFilterUpdate"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">汇总数据</span>
                        <span class="summary-count">{{ tableSummaryText }}</span>
                    </div>
                    <div class="card-header-actions">
                        <el-checkbox v-model="includeRelatedDetailsInExport" :disabled="!hasSelectedMonth">
                            导出附带明细
                        </el-checkbox>
                        <el-button :disabled="!hasSelectedMonth || selectedCount === 0" @click="clearSelectedRows">
                            清空选中
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth || selectedCount === 0" :loading="exportSelectedLoading" @click="handleExport('selected')">
                            <el-icon><Download /></el-icon>
                            导出选中
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth || tableData.length === 0" :loading="exportCurrentPageLoading" @click="handleExport('current_page')">
                            <el-icon><Download /></el-icon>
                            导出当前页
                        </el-button>
                        <el-button type="primary" :disabled="!hasSelectedMonth" :loading="exportAllLoading" @click="handleExport('all')">
                            <el-icon><Download /></el-icon>
                            导出全部
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth" :loading="openingDrawerLoading" @click="openOpeningDrawer">
                            <el-icon><EditPen /></el-icon>
                            维护期初金额
                        </el-button>
                        <el-button :disabled="!hasSelectedMonth" @click="fetchData(true)">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                    </div>
                </div>
            </template>

            <div v-if="!hasSelectedMonth" class="summary-empty-guide">
                <div class="summary-empty-icon">
                    <el-icon><Calendar /></el-icon>
                </div>
                <div class="summary-empty-content">
                    <p class="summary-empty-kicker">需要先确定数据年月</p>
                    <h2>选择数据年月后生成商家应付、冲减和未付流水汇总</h2>
                    <p>汇总会按我方主体与收款商家聚合，适合导出给财务复核。当前不是 0 条数据，而是还没有选定查询口径。</p>
                    <div class="summary-empty-actions">
                        <el-button type="primary" @click="selectCurrentMonth">
                            <el-icon><Calendar /></el-icon>
                            查看本月
                        </el-button>
                        <el-button @click="handleReset">清空筛选</el-button>
                    </div>
                </div>
                <div class="summary-empty-preview" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                </div>
            </div>

            <el-table
                ref="summaryTableRef"
                v-else
                class="summary-table roomy-table merchant-summary-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                show-summary
                :summary-method="summaryMethod"
                row-key="key"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="48" fixed="left" />
                <el-table-column label="序号" width="70" align="center" fixed="left">
                    <template #default="{ $index }">{{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}</template>
                </el-table-column>
                <el-table-column label="数据年月" width="110" fixed="left">
                    <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="160" show-overflow-tooltip />
                <el-table-column prop="our_subject" label="我方主体" width="180" show-overflow-tooltip />
                <el-table-column prop="merchant_receipt_subject" label="商家收款主体" min-width="320" show-overflow-tooltip />
                <el-table-column prop="gmv" label="实收GMV" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.gmv) }}</template>
                </el-table-column>
                <el-table-column prop="merchant_payable_net_amount" label="应付商家净额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.merchant_payable_net_amount) }}</template>
                </el-table-column>
                <el-table-column prop="opening_balance" label="期初余额" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.opening_balance) }}</template>
                </el-table-column>
                <el-table-column prop="business_fee_deduction" label="冲减业务费用" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.business_fee_deduction) }}</template>
                </el-table-column>
                <el-table-column prop="other_deduction_amount" label="其他冲减金额" width="140" align="right">
                    <template #default="{ row }">{{ formatAmount(row.other_deduction_amount) }}</template>
                </el-table-column>
                <el-table-column prop="payable_goods_balance" label="应付货款余额" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.payable_goods_balance) }}</template>
                </el-table-column>
                <el-table-column prop="paid_flow_amount" label="已付流水" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.paid_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="unpaid_flow_amount" label="未付流水" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.unpaid_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="bank_flow_amount" label="银行流水汇总" width="150" align="right">
                    <template #default="{ row }">{{ formatAmount(row.bank_flow_amount) }}</template>
                </el-table-column>
                <el-table-column prop="bank_payment_diff" label="银行付款差" width="130" align="right">
                    <template #default="{ row }">{{ formatAmount(row.bank_payment_diff) }}</template>
                </el-table-column>
                <el-table-column prop="bank_status" label="银行流水状态" width="130" align="center">
                    <template #default="{ row }">
                        <el-tag :type="bankStatusMeta(row.bank_status).type" size="small">{{ bankStatusMeta(row.bank_status).label }}</el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="操作" width="100" align="center" fixed="right">
                    <template #default="{ row }">
                        <el-button type="primary" link @click="openDrilldownDrawer(row)">
                            <el-icon><View /></el-icon>
                            查看
                        </el-button>
                    </template>
                </el-table-column>
            </el-table>

            <div v-if="hasSelectedMonth" class="pagination-area">
                <el-pagination
                    v-model:current-page="pagination.page"
                    v-model:page-size="pagination.pageSize"
                    :page-sizes="PAGE_SIZE_OPTIONS"
                    :layout="PAGINATION_LAYOUT"
                    :total="pagination.total"
                    background
                    @size-change="handleSizeChange"
                    @current-change="handlePageChange"
                />
            </div>
        </el-card>

        <el-drawer
            v-model="openingDrawerVisible"
            title="维护期初金额"
            size="760px"
            class="opening-balance-drawer"
        >
            <div class="opening-toolbar">
                <el-input
                    v-model="openingKeyword"
                    clearable
                    placeholder="搜索我方主体/收款商家"
                >
                    <template #prefix>
                        <el-icon><Search /></el-icon>
                    </template>
                </el-input>
                <el-button :loading="openingDrawerLoading" @click="fetchOpeningBalances">
                    <el-icon><Refresh /></el-icon>
                    刷新
                </el-button>
            </div>

            <el-table
                class="summary-table roomy-table opening-balance-table"
                :data="filteredOpeningRows"
                v-loading="openingDrawerLoading"
                stripe
                border
            >
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" width="140" show-overflow-tooltip />
                <el-table-column prop="our_subject" label="我方主体" min-width="180" show-overflow-tooltip />
                <el-table-column prop="receipt_merchant" label="收款商家" min-width="220" show-overflow-tooltip />
                <el-table-column prop="opening_balance" label="期初金额" width="180" align="right">
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.editing_balance"
                            :precision="2"
                            :step="100"
                            controls-position="right"
                            class="opening-balance-input"
                        />
                    </template>
                </el-table-column>
            </el-table>

            <template #footer>
                <div class="opening-drawer-footer">
                    <span>{{ openingFooterText }}</span>
                    <div>
                        <el-button @click="openingDrawerVisible = false">取消</el-button>
                        <el-button type="primary" :loading="openingSaving" :disabled="openingChangedRows.length === 0" @click="saveOpeningBalances">
                            保存
                        </el-button>
                    </div>
                </div>
            </template>
        </el-drawer>

        <el-drawer
            v-model="drilldownDrawerVisible"
            :title="drilldownTitle"
            size="92%"
            class="summary-drilldown-drawer"
        >
            <div v-if="drilldownRow" class="drilldown-overview">
                <div class="drilldown-identity">
                    <span class="drilldown-kicker">汇总行明细</span>
                    <div class="drilldown-subject-line">
                        <span class="drilldown-label">我方主体：</span>
                        <strong>{{ drilldownRow.our_subject || "-" }}</strong>
                    </div>
                    <div class="drilldown-subject-line">
                        <span class="drilldown-label">收款商家：</span>
                        <strong>{{ drilldownRow.merchant_receipt_subject || "-" }}</strong>
                    </div>
                </div>
                <div class="drilldown-metrics">
                    <span v-for="metric in drilldownMetricItems" :key="metric.label">
                        <em>{{ metric.label }}</em>
                        <strong>{{ metric.value }}</strong>
                    </span>
                </div>
            </div>

            <el-tabs v-model="drilldownActiveTab" @tab-change="handleDrilldownTabChange">
                <el-tab-pane :label="`动账明细 ${drilldownDetails.total}`" name="details">
                    <el-table class="summary-table roomy-table drilldown-table" :data="drilldownDetails.items" v-loading="drilldownDetails.loading" stripe border>
                        <el-table-column prop="source_row_number" label="源行号" width="90" />
                        <el-table-column prop="shop_name" label="店铺" width="160" show-overflow-tooltip />
                        <el-table-column prop="product_code" label="商品编码" width="130" show-overflow-tooltip />
                        <el-table-column prop="product_name" label="商品名称" min-width="220" show-overflow-tooltip />
                        <el-table-column prop="gmv" label="实收GMV" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.gmv) }}</template>
                        </el-table-column>
                        <el-table-column prop="live_amount" label="直播款" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.live_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="major_merchant_name" label="大商家" width="150" show-overflow-tooltip />
                        <el-table-column prop="receipt_merchant" label="收款商家" width="170" show-overflow-tooltip />
                        <el-table-column prop="live_room" label="直播间" width="140" show-overflow-tooltip />
                        <el-table-column prop="live_date" label="直播日期" width="120">
                            <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                        </el-table-column>
                        <el-table-column prop="transaction_flow_no" label="动账流水号" min-width="180" show-overflow-tooltip />
                    </el-table>
                    <div class="pagination-area">
                        <el-pagination
                            v-model:current-page="drilldownDetails.page"
                            v-model:page-size="drilldownDetails.pageSize"
                            :page-sizes="PAGE_SIZE_OPTIONS"
                            :layout="PAGINATION_LAYOUT"
                            :total="drilldownDetails.total"
                            background
                            @size-change="(size: number) => handleDrilldownSizeChange('details', size)"
                            @current-change="(page: number) => handleDrilldownPageChange('details', page)"
                        />
                    </div>
                </el-tab-pane>

                <el-tab-pane :label="`货款明细 ${drilldownPayments.total}`" name="payments">
                    <el-table class="summary-table roomy-table drilldown-table" :data="drilldownPayments.items" v-loading="drilldownPayments.loading" stripe border>
                        <el-table-column prop="source_row_number" label="源行号" width="90" />
                        <el-table-column prop="shop_name" label="店铺" width="160" show-overflow-tooltip />
                        <el-table-column prop="live_room" label="直播间" width="140" show-overflow-tooltip />
                        <el-table-column prop="live_date" label="直播日期" width="120">
                            <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                        </el-table-column>
                        <el-table-column prop="merchant" label="商家" width="150" show-overflow-tooltip />
                        <el-table-column prop="settlement_subject" label="结算主体" width="170" show-overflow-tooltip />
                        <el-table-column prop="receipt_merchant" label="收款商家" width="170" show-overflow-tooltip />
                        <el-table-column prop="payable_goods_amount" label="应付货款" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.payable_goods_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="business_fee_deduction" label="业务费用" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.business_fee_deduction) }}</template>
                        </el-table-column>
                        <el-table-column prop="deduction_amount" label="冲减金额" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.deduction_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="paid_amount" label="已付" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.paid_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="settlement_status" label="结算状态" min-width="120" show-overflow-tooltip />
                    </el-table>
                    <div class="pagination-area">
                        <el-pagination
                            v-model:current-page="drilldownPayments.page"
                            v-model:page-size="drilldownPayments.pageSize"
                            :page-sizes="PAGE_SIZE_OPTIONS"
                            :layout="PAGINATION_LAYOUT"
                            :total="drilldownPayments.total"
                            background
                            @size-change="(size: number) => handleDrilldownSizeChange('payments', size)"
                            @current-change="(page: number) => handleDrilldownPageChange('payments', page)"
                        />
                    </div>
                </el-tab-pane>

                <el-tab-pane :label="`采购明细 ${drilldownPurchases.total}`" name="purchases">
                    <el-table class="summary-table roomy-table drilldown-table" :data="drilldownPurchases.items" v-loading="drilldownPurchases.loading" stripe border>
                        <el-table-column prop="source_row_number" label="源行号" width="90" />
                        <el-table-column prop="shop_name" label="店铺" width="160" show-overflow-tooltip />
                        <el-table-column prop="live_room" label="直播间" width="140" show-overflow-tooltip />
                        <el-table-column prop="live_date" label="直播日期" width="120">
                            <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                        </el-table-column>
                        <el-table-column prop="merchant" label="商家" width="150" show-overflow-tooltip />
                        <el-table-column prop="live_code" label="直播编号" width="150" show-overflow-tooltip />
                        <el-table-column prop="product_name" label="货品名称" min-width="240" show-overflow-tooltip />
                        <el-table-column prop="borrow_amount" label="借货金额" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.borrow_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="return_amount" label="退货金额" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.return_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
                    </el-table>
                    <div class="pagination-area">
                        <el-pagination
                            v-model:current-page="drilldownPurchases.page"
                            v-model:page-size="drilldownPurchases.pageSize"
                            :page-sizes="PAGE_SIZE_OPTIONS"
                            :layout="PAGINATION_LAYOUT"
                            :total="drilldownPurchases.total"
                            background
                            @size-change="(size: number) => handleDrilldownSizeChange('purchases', size)"
                            @current-change="(page: number) => handleDrilldownPageChange('purchases', page)"
                        />
                    </div>
                </el-tab-pane>

                <el-tab-pane :label="`银行流水 ${drilldownBankFlows.total}`" name="bank_flows">
                    <el-table class="summary-table roomy-table drilldown-table" :data="drilldownBankFlows.items" v-loading="drilldownBankFlows.loading" stripe border>
                        <el-table-column prop="source_row_number" label="源行号" width="90" />
                        <el-table-column prop="bank_name" label="银行" width="110" show-overflow-tooltip />
                        <el-table-column prop="account_name" label="账户名称" width="210" show-overflow-tooltip />
                        <el-table-column prop="transaction_time" label="交易时间" width="170">
                            <template #default="{ row }">{{ formatRawDateTime(row.transaction_time) }}</template>
                        </el-table-column>
                        <el-table-column prop="counterparty_name" label="对方户名" width="220" show-overflow-tooltip />
                        <el-table-column prop="flow_amount" label="流水净额" width="120" align="right">
                            <template #default="{ row }">{{ formatAmount(row.flow_amount) }}</template>
                        </el-table-column>
                        <el-table-column prop="live_date" label="直播日期" width="130">
                            <template #default="{ row }">{{ formatRawDate(row.live_date) }}</template>
                        </el-table-column>
                        <el-table-column prop="purpose" label="用途/备注" min-width="240" show-overflow-tooltip />
                        <el-table-column prop="transaction_flow_no" label="流水号" min-width="180" show-overflow-tooltip />
                    </el-table>
                    <div class="pagination-area">
                        <el-pagination
                            v-model:current-page="drilldownBankFlows.page"
                            v-model:page-size="drilldownBankFlows.pageSize"
                            :page-sizes="PAGE_SIZE_OPTIONS"
                            :layout="PAGINATION_LAYOUT"
                            :total="drilldownBankFlows.total"
                            background
                            @size-change="(size: number) => handleDrilldownSizeChange('bank_flows', size)"
                            @current-change="(page: number) => handleDrilldownPageChange('bank_flows', page)"
                        />
                    </div>
                </el-tab-pane>
            </el-tabs>
        </el-drawer>
    </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Calendar, Download, EditPen, Refresh, Search, View } from "@element-plus/icons-vue";
import {
    listMerchantReconciliationSummaryBankFlows,
    listMerchantReconciliationSummaryDetails,
    listMerchantReconciliationSummaryPayments,
    listMerchantReconciliationSummaryPurchases,
    listMerchantOpeningBalances,
    listMerchantReconciliationSummary,
    upsertMerchantOpeningBalances,
    type MerchantBankFlowRow,
    type MerchantReconciliationDetail,
    type MerchantOpeningBalance,
    type MerchantReconciliationSummary,
    type MerchantRedSheetPayment,
    type MerchantRedSheetPurchase,
} from "@/api/merchantReconciliation";
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import { buildExportFilename, formatRawDate, formatRawDateTime, summarizeFilenameValues } from "@/utils/format";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatAmount, formatMonth, hasMonthSelectionChanged } from "./common";
import { useMerchantReconciliationFilters, type MerchantFilterState } from "./composables";

defineOptions({ name: "MerchantReconciliationSummary" });

const {
    userStore,
    searchForm,
    douyinShops,
    orgOptions,
    shopLoading,
    fetchOrgs,
    fetchShops,
    handleOrgChange,
    resetFilters,
} = useMerchantReconciliationFilters({ autoSelectFirstShop: false });

const loading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const openingDrawerVisible = ref(false);
const openingDrawerLoading = ref(false);
const openingSaving = ref(false);
const openingKeyword = ref("");
const tableData = ref<MerchantReconciliationSummary[]>([]);
const selectedRowMap = ref(new Map<string, MerchantReconciliationSummary>());
const restoringSelection = ref(false);
const summaryTableRef = ref<{
    clearSelection: () => void;
    toggleRowSelection: (row: MerchantReconciliationSummary, selected?: boolean) => void;
} | null>(null);
const includeRelatedDetailsInExport = ref(true);
type DrilldownTab = "details" | "payments" | "purchases" | "bank_flows";
type DrilldownState<T> = {
    items: T[];
    loading: boolean;
    loaded: boolean;
    page: number;
    pageSize: number;
    total: number;
};
type OpeningBalanceRow = MerchantOpeningBalance & {
    editing_balance: number;
    original_balance: number;
};
const openingRows = ref<OpeningBalanceRow[]>([]);
const drilldownDrawerVisible = ref(false);
const drilldownActiveTab = ref<DrilldownTab>("details");
const drilldownRow = ref<MerchantReconciliationSummary | null>(null);
const drilldownDetails = reactive<DrilldownState<MerchantReconciliationDetail>>({
    items: [],
    loading: false,
    loaded: false,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});
const drilldownPayments = reactive<DrilldownState<MerchantRedSheetPayment>>({
    items: [],
    loading: false,
    loaded: false,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});
const drilldownPurchases = reactive<DrilldownState<MerchantRedSheetPurchase>>({
    items: [],
    loading: false,
    loaded: false,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});
const drilldownBankFlows = reactive<DrilldownState<MerchantBankFlowRow>>({
    items: [],
    loading: false,
    loaded: false,
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});
const pagination = reactive({ page: 1, pageSize: DEFAULT_PAGE_SIZE, total: 0 });
const hasSelectedMonth = computed(() => Boolean(searchForm.month));
const selectedRows = computed(() => Array.from(selectedRowMap.value.values()));
const selectedCount = computed(() => selectedRowMap.value.size);
const tableSummaryText = computed(() => {
    if (!hasSelectedMonth.value) return "待选择数据年月";
    return `共 ${pagination.total} 条 · 已选 ${selectedCount.value} 条`;
});
const drilldownTitle = computed(() => {
    const row = drilldownRow.value;
    if (!row) return "查看明细";
    return `${formatMonth(row.accounting_year, row.accounting_month)} ${row.our_subject || "-"} / ${row.merchant_receipt_subject || "-"}`;
});
const drilldownMetricItems = computed(() => {
    const row = drilldownRow.value;
    if (!row) return [];
    return [
        { label: "实收GMV", value: formatAmount(row.gmv) },
        { label: "应付商家净额", value: formatAmount(row.merchant_payable_net_amount) },
        { label: "期初余额", value: formatAmount(row.opening_balance) },
        { label: "冲减业务费用", value: formatAmount(row.business_fee_deduction) },
        { label: "其他冲减金额", value: formatAmount(row.other_deduction_amount) },
        { label: "应付货款余额", value: formatAmount(row.payable_goods_balance) },
        { label: "已付流水", value: formatAmount(row.paid_flow_amount) },
        { label: "未付流水", value: formatAmount(row.unpaid_flow_amount) },
        { label: "银行流水汇总", value: formatAmount(row.bank_flow_amount) },
        { label: "银行付款差", value: formatAmount(row.bank_payment_diff) },
    ];
});

function currentMonthValue() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function queryParams(showMessage = true) {
    const [year, month] = String(searchForm.month || "").split("-").map(Number);
    if (!year || !month) {
        if (showMessage) {
            ElMessage.warning("请选择数据年月");
        }
        return null;
    }
    return {
        accounting_year: year,
        accounting_month: month,
        shop_id: typeof searchForm.shopId === "number" ? searchForm.shopId : undefined,
        org_id: searchForm.orgId,
        keyword: searchForm.keyword || undefined,
        bank_status: searchForm.bankStatus || undefined,
        page: pagination.page,
        page_size: pagination.pageSize,
    };
}

function bankStatusMeta(status: string) {
    const map: Record<string, { label: string; type: "success" | "warning" | "danger" | "info" }> = {
        matched: { label: "已匹配", type: "success" },
        diff: { label: "有差异", type: "danger" },
        pending: { label: "待匹配", type: "info" },
    };
    return map[status] || map.pending;
}

async function fetchData(showMessage = true) {
    const params = queryParams(showMessage);
    if (!params) {
        tableData.value = [];
        clearSelectedRows(false);
        pagination.total = 0;
        return;
    }
    loading.value = true;
    try {
        const result = await listMerchantReconciliationSummary(params);
        tableData.value = result.items || [];
        pagination.total = result.total || 0;
    } finally {
        loading.value = false;
        await nextTick();
        await restoreSelection();
    }
}

async function selectCurrentMonth() {
    searchForm.month = currentMonthValue();
    pagination.page = 1;
    await fetchData(false);
}

type ExportScope = "all" | "current_page" | "selected";

function handleSelectionChange(rows: MerchantReconciliationSummary[]) {
    if (restoringSelection.value) return;
    const currentPageKeys = new Set(tableData.value.map((row) => row.key));
    const nextMap = new Map(selectedRowMap.value);

    currentPageKeys.forEach((key) => {
        nextMap.delete(key);
    });
    rows.forEach((row) => {
        nextMap.set(row.key, row);
    });

    selectedRowMap.value = nextMap;
}

async function restoreSelection() {
    if (!summaryTableRef.value) return;
    restoringSelection.value = true;
    summaryTableRef.value.clearSelection();
    tableData.value.forEach((row) => {
        if (selectedRowMap.value.has(row.key)) {
            summaryTableRef.value?.toggleRowSelection(row, true);
        }
    });
    await nextTick();
    restoringSelection.value = false;
}

function clearSelectedRows(clearTable = true) {
    selectedRowMap.value = new Map();
    if (clearTable) {
        summaryTableRef.value?.clearSelection();
    }
}

async function handleExport(scope: ExportScope) {
    const params = queryParams(true);
    if (!params) return;
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
        const { page, page_size, ...baseParams } = params;
        const selectedShop = douyinShops.value.find((shop) => shop.id === Number(searchForm.shopId || 0));
        const scopeLabel =
            scope === "all"
                ? "全部"
                : scope === "current_page"
                  ? `第${pagination.page}页`
                  : "选中";
        await submitExportJob({
            export_type: "merchant_reconciliation.summary",
            title: "商家对账汇总导出",
            filename: normalizeExportFilename(buildExportFilename([
                searchForm.month || "全部数据年月",
                `店铺${summarizeFilenameValues([selectedShop?.shop_name || ""], "全部")}`,
                "商家对账汇总",
                includeRelatedDetailsInExport.value ? "附带明细" : null,
                scopeLabel,
            ])),
            params: {
                ...baseParams,
                scope,
                ids: scope === "selected" ? selectedRows.value.map((row) => row.key) : undefined,
                page: scope === "current_page" ? page : undefined,
                page_size: scope === "current_page" ? page_size : undefined,
                include_related_details: includeRelatedDetailsInExport.value,
            },
        });
    } finally {
        loadingRef.value = false;
    }
}

function resetDrilldownState<T>(state: DrilldownState<T>) {
    state.items = [];
    state.loading = false;
    state.loaded = false;
    state.page = 1;
    state.pageSize = DEFAULT_PAGE_SIZE;
    state.total = 0;
}

function drilldownParams(state: DrilldownState<unknown>) {
    const row = drilldownRow.value;
    if (!row) return null;
    return {
        accounting_year: row.accounting_year,
        accounting_month: row.accounting_month,
        shop_id: typeof searchForm.shopId === "number" ? searchForm.shopId : undefined,
        org_id: searchForm.orgId,
        summary_org_id: row.org_id || undefined,
        our_subject: row.our_subject,
        merchant_receipt_subject: row.merchant_receipt_subject,
        page: state.page,
        page_size: state.pageSize,
    };
}

async function fetchDrilldownTab(tab: DrilldownTab, force = false) {
    const loaders = {
        details: { state: drilldownDetails, request: listMerchantReconciliationSummaryDetails },
        payments: { state: drilldownPayments, request: listMerchantReconciliationSummaryPayments },
        purchases: { state: drilldownPurchases, request: listMerchantReconciliationSummaryPurchases },
        bank_flows: { state: drilldownBankFlows, request: listMerchantReconciliationSummaryBankFlows },
    };
    const { state, request } = loaders[tab];
    if (state.loaded && !force) return;
    const params = drilldownParams(state);
    if (!params) return;
    state.loading = true;
    try {
        const result = await request(params);
        state.items = result.items || [];
        state.total = result.total || 0;
        state.loaded = true;
    } finally {
        state.loading = false;
    }
}

async function openDrilldownDrawer(row: MerchantReconciliationSummary) {
    drilldownRow.value = row;
    drilldownActiveTab.value = "details";
    resetDrilldownState(drilldownDetails);
    resetDrilldownState(drilldownPayments);
    resetDrilldownState(drilldownPurchases);
    resetDrilldownState(drilldownBankFlows);
    drilldownDrawerVisible.value = true;
    await fetchDrilldownTab("details", true);
}

async function handleDrilldownTabChange(tabName: string | number) {
    await fetchDrilldownTab(String(tabName) as DrilldownTab);
}

async function handleDrilldownSizeChange(tab: DrilldownTab, size: number) {
    const state = drilldownStateByTab(tab);
    state.pageSize = size;
    state.page = 1;
    state.loaded = false;
    await fetchDrilldownTab(tab, true);
}

async function handleDrilldownPageChange(tab: DrilldownTab, page: number) {
    const state = drilldownStateByTab(tab);
    state.page = page;
    state.loaded = false;
    await fetchDrilldownTab(tab, true);
}

function drilldownStateByTab(tab: DrilldownTab) {
    const map = {
        details: drilldownDetails,
        payments: drilldownPayments,
        purchases: drilldownPurchases,
        bank_flows: drilldownBankFlows,
    };
    return map[tab];
}

function openingQueryParams(showMessage = true) {
    const params = queryParams(showMessage);
    if (!params) return null;
    return {
        accounting_year: params.accounting_year,
        accounting_month: params.accounting_month,
        shop_id: params.shop_id,
        org_id: params.org_id,
    };
}

const openingChangedRows = computed(() =>
    openingRows.value.filter((row) => Number(row.editing_balance || 0).toFixed(2) !== Number(row.original_balance || 0).toFixed(2)),
);

const filteredOpeningRows = computed(() => {
    const keyword = openingKeyword.value.trim().toLowerCase();
    if (!keyword) return openingRows.value;
    return openingRows.value.filter((row) =>
        String(row.our_subject || "").toLowerCase().includes(keyword)
        || String(row.receipt_merchant || "").toLowerCase().includes(keyword),
    );
});

const openingFooterText = computed(() => {
    if (openingRows.value.length === 0) return "暂无可维护数据";
    return `当前显示 ${filteredOpeningRows.value.length} 条，已修改 ${openingChangedRows.value.length} 条`;
});

async function openOpeningDrawer() {
    if (!openingQueryParams(true)) return;
    openingDrawerVisible.value = true;
    await fetchOpeningBalances();
}

async function fetchOpeningBalances() {
    const params = openingQueryParams(true);
    if (!params) return;
    openingDrawerLoading.value = true;
    try {
        const rows = await listMerchantOpeningBalances(params);
        openingRows.value = (rows || []).map((row) => {
            const balance = Number(row.opening_balance || 0);
            return {
                ...row,
                editing_balance: balance,
                original_balance: balance,
            };
        });
    } finally {
        openingDrawerLoading.value = false;
    }
}

async function saveOpeningBalances() {
    const params = queryParams(true);
    if (!params) return;
    const rows = openingChangedRows.value;
    if (rows.length === 0) {
        ElMessage.info("没有需要保存的期初金额");
        return;
    }
    openingSaving.value = true;
    try {
        const result = await upsertMerchantOpeningBalances({
            accounting_year: params.accounting_year,
            accounting_month: params.accounting_month,
            platform_code: "douyin",
            items: rows.map((row) => ({
                org_id: row.org_id,
                our_subject: row.our_subject,
                receipt_merchant: row.receipt_merchant,
                opening_balance: row.editing_balance || 0,
                remark: row.remark || "",
            })),
        });
        ElMessage.success(`已保存 ${result.total_count || rows.length} 条期初金额`);
        openingRows.value = openingRows.value.map((row) => ({
            ...row,
            original_balance: Number(row.editing_balance || 0),
        }));
        await fetchData(false);
    } finally {
        openingSaving.value = false;
    }
}

async function handleSearch() {
    pagination.page = 1;
    clearSelectedRows(false);
    await fetchData(true);
}

async function handleFilterUpdate(nextModel: Partial<MerchantFilterState> & { month?: string | null }) {
    const previousMonth = searchForm.month || "";
    const nextMonth = nextModel.month || "";
    clearSelectedRows();
    Object.assign(searchForm, {
        ...nextModel,
        month: nextMonth,
    });
    if (hasMonthSelectionChanged(previousMonth, nextMonth)) {
        pagination.page = 1;
        clearSelectedRows(false);
        await fetchData(false);
    }
}

async function handleReset() {
    resetFilters();
    await fetchShops();
    pagination.page = 1;
    clearSelectedRows(false);
    await fetchData(false);
}

async function handleSizeChange(size: number) {
    pagination.pageSize = size;
    pagination.page = 1;
    await fetchData(false);
}

async function handlePageChange(page: number) {
    pagination.page = page;
    await fetchData(false);
}

function summaryMethod({ columns, data }: { columns: any[]; data: MerchantReconciliationSummary[] }) {
    const moneyProps = new Set(["gmv", "merchant_payable_net_amount", "opening_balance", "business_fee_deduction", "other_deduction_amount", "payable_goods_balance", "paid_flow_amount", "unpaid_flow_amount", "bank_flow_amount", "bank_payment_diff"]);
    return columns.map((column, index) => {
        if (index === 0) return "合计";
        if (!moneyProps.has(column.property)) return "";
        return formatAmount(data.reduce((total, row) => total + Number((row as any)[column.property] || 0), 0));
    });
}

onMounted(async () => {
    await fetchOrgs();
    await fetchShops();
    await fetchData(false);
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";

.summary-note {
    margin-bottom: 12px;
}

.opening-toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
}

.opening-toolbar .el-input {
    max-width: 320px;
}

.opening-balance-table {
    width: 100%;
}

.opening-balance-input {
    width: 150px;
}

.opening-drawer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    width: 100%;
    color: var(--text-secondary);
}

.summary-drilldown-drawer {
    :deep(.el-drawer__body) {
        display: flex;
        flex-direction: column;
        gap: 14px;
        overflow: hidden;
    }

    :deep(.el-tabs) {
        min-height: 0;
    }

    :deep(.el-tab-pane) {
        min-height: 0;
    }
}

.drilldown-overview {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
    padding: 14px 16px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
}

.drilldown-identity {
    display: grid;
    gap: 8px;
    min-width: 0;
    max-width: 420px;

    strong,
    span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    strong {
        color: var(--text-primary);
        font-size: 15px;
    }
}

.drilldown-subject-line {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: baseline;
    min-width: 0;
}

.drilldown-label {
    color: var(--text-secondary);
    font-size: 13px;
}

.drilldown-kicker {
    color: var(--primary);
    font-size: 12px;
    font-weight: 700;
}

.drilldown-metrics {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;

    span {
        display: grid;
        gap: 2px;
        min-width: 116px;
        padding: 6px 10px;
        border: 1px solid var(--border-color-light);
        border-radius: 10px;
        background: var(--bg-card);
        color: var(--text-secondary);
        white-space: nowrap;
    }

    em {
        color: var(--text-tertiary);
        font-size: 11px;
        font-style: normal;
    }

    strong {
        color: var(--text-primary);
        font-size: 13px;
        font-weight: 700;
    }
}

.drilldown-table {
    width: 100%;
}

.merchant-summary-table {
    width: 100%;

    :deep(.el-table__header),
    :deep(.el-table__body),
    :deep(.el-table__footer) {
        table-layout: auto !important;
    }

    :deep(.el-table__header colgroup col[width="320"]),
    :deep(.el-table__body colgroup col[width="320"]),
    :deep(.el-table__footer colgroup col[width="320"]) {
        width: auto !important;
    }

    :deep(.el-table__empty-block) {
        min-height: 220px;
    }
}

.summary-empty-guide {
    position: relative;
    display: grid;
    grid-template-columns: 54px minmax(0, 1fr) 220px;
    gap: 18px;
    align-items: center;
    min-height: 230px;
    padding: 26px;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius-card);
    background: linear-gradient(135deg, var(--bg-elevated), var(--bg-card));
    overflow: hidden;
}

.summary-empty-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 54px;
    height: 54px;
    border: 1px solid var(--primary-light-7);
    border-radius: var(--radius-card);
    background: var(--primary-light-9);
    color: var(--primary);
    font-size: 26px;
}

.summary-empty-content {
    min-width: 0;

    h2 {
        margin: 0 0 8px;
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 700;
        line-height: 1.35;
        letter-spacing: 0;
    }

    p {
        max-width: 660px;
        margin: 0;
        color: var(--text-secondary);
        font-size: 13px;
        line-height: 1.65;
    }
}

.summary-empty-kicker {
    margin-bottom: 5px !important;
    color: var(--primary) !important;
    font-size: 12px !important;
    font-weight: 700;
}

.summary-empty-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 16px;
}

.summary-empty-preview {
    display: grid;
    gap: 10px;
    padding: 16px;
    border: 1px solid var(--border-color-light);
    border-radius: var(--radius-card);
    background: var(--bg-card);

    span {
        display: block;
        height: 20px;
        border-radius: 4px;
        background: linear-gradient(90deg, var(--primary-light-9), var(--bg-hover));

        &:nth-child(2) {
            width: 82%;
        }

        &:nth-child(3) {
            width: 64%;
        }
    }
}

@media (max-width: 920px) {
    .table-card :deep(.card-header) {
        align-items: stretch;
        flex-direction: column;
    }

    .table-card :deep(.card-header-actions) {
        justify-content: flex-start;
    }

    .summary-empty-guide {
        grid-template-columns: 54px minmax(0, 1fr);
    }

    .summary-empty-preview {
        display: none;
    }

    .drilldown-overview {
        align-items: flex-start;
        flex-direction: column;
    }

    .drilldown-metrics {
        justify-content: flex-start;
    }
}

@media (max-width: 640px) {
    .summary-empty-guide {
        grid-template-columns: 1fr;
        padding: 18px;
    }

    .summary-empty-content h2 {
        font-size: 16px;
    }
}
</style>
