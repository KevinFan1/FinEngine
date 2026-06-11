<template>
    <el-drawer
        :model-value="modelValue"
        title="抖音动账源明细"
        size="92%"
        append-to-body
        destroy-on-close
        class="douyin-detail-drawer"
        :close-on-click-modal="false"
        @update:model-value="emit('update:modelValue', $event)"
    >
        <div class="detail-drawer">
            <div class="detail-toolbar">
                <div class="detail-toolbar-copy">
                    <p class="detail-toolbar-kicker">源明细抽屉</p>
                    <div class="detail-context">
                        <span class="context-item">核算年月：{{ context?.sourceDate || "-" }}</span>
                        <span class="context-item">业务年月：{{ context?.summaryDate || "-" }}</span>
                        <span class="context-item">
                            来源平台：
                            <PlatformBadge v-if="context?.platform" :platform="context.platform" />
                            <template v-else>-</template>
                        </span>
                        <span class="context-item">
                            店铺：
                            <ShopBadge :label="context?.shopName || '-'" :color="context?.shopColor" size="table" />
                        </span>
                        <span class="context-item">总行数：{{ pagination.total }}</span>
                    </div>
                </div>
                <div class="detail-actions">
                    <el-checkbox v-model="includeInSummaryExport">汇总导出附带明细</el-checkbox>

                    <el-popover
                        placement="bottom-end"
                        :width="340"
                        trigger="click"
                        popper-class="detail-column-popover"
                    >
                        <template #reference>
                            <el-button plain>
                                <el-icon><Setting /></el-icon>
                                字段
                                <span class="column-button-count">{{ visibleBusinessColumns.length }}/{{ BUSINESS_COLUMN_DEFS.length }}</span>
                            </el-button>
                        </template>

                        <div class="column-panel">
                            <div class="column-panel-head">
                                <div>
                                    <p class="column-panel-title">字段显示</p>
                                    <p class="column-panel-subtitle">保存到当前登录用户配置，下次登录后自动恢复</p>
                                </div>
                                <el-button link type="primary" @click="resetVisibleColumns">恢复默认</el-button>
                            </div>
                            <el-scrollbar max-height="320px">
                                <el-checkbox-group
                                    v-model="visibleColumnKeys"
                                    class="column-checkbox-group"
                                    @change="handleVisibleColumnsChange"
                                >
                                    <el-checkbox
                                        v-for="column in BUSINESS_COLUMN_DEFS"
                                        :key="column.key"
                                        :value="column.key"
                                        :disabled="isColumnLocked(column.key)"
                                    >
                                        {{ column.label }}
                                    </el-checkbox>
                                </el-checkbox-group>
                            </el-scrollbar>
                        </div>
                    </el-popover>

                    <el-button :loading="exportCurrentPageLoading" @click="handleExport('current_page')">
                        <el-icon><Download /></el-icon> 导出当前页
                    </el-button>
                    <el-button :loading="exportSelectedLoading" :disabled="selectedCount === 0" @click="handleExport('selected')">
                        <el-icon><Download /></el-icon> 导出选中
                    </el-button>
                    <el-button type="success" :loading="exportAllLoading" @click="handleExport('all')">
                        <el-icon><Download /></el-icon> 导出全部
                    </el-button>
                </div>
            </div>

            <el-table
                ref="detailTableRef"
                class="summary-table summary-detail-table fill-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                :fit="false"
                style="width: 100%"
                height="100%"
                row-key="id"
                @selection-change="handleSelectionChange"
            >
                <el-table-column type="selection" width="48" fixed="left" :reserve-selection="true" />
                <el-table-column label="序号" width="72" align="center" fixed="left">
                    <template #default="{ $index }">
                        {{ (pagination.page - 1) * pagination.pageSize + $index + 1 }}
                    </template>
                </el-table-column>

                <template v-for="column in visibleBusinessColumns" :key="column.key">
                    <el-table-column
                        v-if="column.kind === 'platform'"
                        :label="column.label"
                        :width="column.width"
                        :fixed="column.fixed"
                        :show-overflow-tooltip="column.tooltip"
                    >
                        <template #default="{ row }">
                            <PlatformBadge :platform="row.platform" />
                        </template>
                    </el-table-column>

                    <el-table-column
                        v-else-if="column.kind === 'shop'"
                        :label="column.label"
                        :width="column.width"
                        :fixed="column.fixed"
                        :show-overflow-tooltip="column.tooltip"
                    >
                        <template #default="{ row }">
                            <ShopBadge :label="row.shop_name" :color="row.shop_color" size="compact" />
                        </template>
                    </el-table-column>

                    <el-table-column
                        v-else-if="column.kind === 'money'"
                        :prop="column.prop"
                        :label="column.label"
                        :width="column.width"
                        :min-width="column.minWidth"
                        :fixed="column.fixed"
                        :show-overflow-tooltip="column.tooltip"
                        align="right"
                        header-align="right"
                    >
                        <template #default="{ row }">
                            <span class="font-mono money-cell">{{ formatMoney(row[column.prop]) }}</span>
                        </template>
                    </el-table-column>

                    <el-table-column
                        v-else
                        :prop="column.prop"
                        :label="column.label"
                        :width="column.width"
                        :min-width="column.minWidth"
                        :fixed="column.fixed"
                        :show-overflow-tooltip="column.tooltip"
                    />
                </template>

                <template #empty>
                    <el-empty description="暂无源明细数据" :image-size="80" />
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
        </div>
    </el-drawer>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue";
import { Download, Setting } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import { getMyPreference, updateMyPreference } from "@/api/auth";
import { type SummaryDongzhangDetailRecord, getSummaryDongzhangDetailList } from "@/api/summary";
import { useUserStore } from "@/stores/user";
import { formatMoney } from "@/utils/format";
import { PAGE_SIZE_OPTIONS, PAGINATION_LAYOUT } from "@/utils/pagination";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";

type DetailColumnKind = "text" | "money" | "platform" | "shop";

interface DetailColumnDef {
    key: string;
    label: string;
    kind: DetailColumnKind;
    prop: keyof SummaryDongzhangDetailRecord | "";
    width?: number;
    minWidth?: number;
    tooltip?: boolean;
    fixed?: "left";
    defaultVisible?: boolean;
    alwaysVisible?: boolean;
}

export interface DouyinDongzhangDetailContext {
    summaryId: number;
    orgId?: number;
    sourceDate?: string;
    summaryDate?: string;
    platform?: string;
    shopName?: string;
    shopColor?: string | null;
}

const BUSINESS_COLUMN_DEFS: DetailColumnDef[] = [
    { key: "platform", label: "平台", kind: "platform", prop: "", width: 110, fixed: "left", defaultVisible: true, alwaysVisible: true },
    { key: "shop_name", label: "店铺", kind: "shop", prop: "shop_name", width: 220, fixed: "left", tooltip: true, defaultVisible: true, alwaysVisible: true },
    { key: "transaction_time", label: "动账时间", kind: "text", prop: "transaction_time", width: 170, defaultVisible: true },
    { key: "transaction_flow_no", label: "动帐流水号", kind: "text", prop: "transaction_flow_no", width: 180, tooltip: true, defaultVisible: true },
    { key: "transaction_direction", label: "动账方向", kind: "text", prop: "transaction_direction", width: 100, defaultVisible: true },
    { key: "transaction_amount", label: "动账金额", kind: "money", prop: "transaction_amount", width: 120, defaultVisible: true },
    { key: "transaction_account", label: "动账账户", kind: "text", prop: "transaction_account", width: 140, tooltip: true, defaultVisible: true },
    { key: "transaction_scene", label: "动账场景", kind: "text", prop: "transaction_scene", width: 180, tooltip: true, defaultVisible: true },
    { key: "billing_type", label: "计费类型", kind: "text", prop: "billing_type", width: 140, tooltip: true, defaultVisible: true },
    { key: "sub_order_no", label: "子订单号", kind: "text", prop: "sub_order_no", width: 150, tooltip: true, defaultVisible: true },
    { key: "order_no", label: "订单号", kind: "text", prop: "order_no", width: 150, tooltip: true, defaultVisible: true },
    { key: "after_sale_no", label: "售后编号", kind: "text", prop: "after_sale_no", width: 150, tooltip: true, defaultVisible: true },
    { key: "order_time", label: "下单时间", kind: "text", prop: "order_time", width: 170, defaultVisible: true },
    { key: "summary_date", label: "调年月(系统的业务年月)", kind: "text", prop: "summary_date", width: 170, defaultVisible: true },
    { key: "product_id", label: "商品ID", kind: "text", prop: "product_id", width: 120, tooltip: true, defaultVisible: true },
    { key: "product_code", label: "商品编码", kind: "text", prop: "product_code", width: 140, tooltip: true, defaultVisible: true },
    { key: "product_name", label: "商品名称", kind: "text", prop: "product_name", width: 240, tooltip: true, defaultVisible: true },
    { key: "author_id", label: "达人ID", kind: "text", prop: "author_id", width: 120, tooltip: true, defaultVisible: true },
    { key: "author_name", label: "达人名称", kind: "text", prop: "author_name", width: 150, tooltip: true, defaultVisible: true },
    { key: "order_type", label: "订单类型", kind: "text", prop: "order_type", width: 120, tooltip: true, defaultVisible: true },
    { key: "order_paid_amount_raw", label: "订单实付应结", kind: "money", prop: "order_paid_amount_raw", width: 130, defaultVisible: true },
    { key: "shipping_fee", label: "运费实付", kind: "money", prop: "shipping_fee", width: 120, defaultVisible: true },
    { key: "platform_subsidy_shipping", label: "实际平台补贴_运费", kind: "money", prop: "platform_subsidy_shipping", width: 160, defaultVisible: true },
    { key: "platform_subsidy", label: "实际平台补贴", kind: "money", prop: "platform_subsidy", width: 130, defaultVisible: true },
    { key: "other_platform_subsidy", label: "其他平台补贴", kind: "money", prop: "other_platform_subsidy", width: 130, defaultVisible: true },
    { key: "trade_in_deduction", label: "以旧换新抵扣", kind: "money", prop: "trade_in_deduction", width: 140, defaultVisible: true },
    { key: "gov_subsidy_platform", label: "政府补贴平台垫资", kind: "money", prop: "gov_subsidy_platform", width: 160, defaultVisible: true },
    { key: "author_subsidy", label: "实际达人补贴", kind: "money", prop: "author_subsidy", width: 130, defaultVisible: true },
    { key: "douyin_pay_subsidy", label: "实际抖音支付补贴", kind: "money", prop: "douyin_pay_subsidy", width: 160, defaultVisible: true },
    { key: "douyin_monthly_subsidy", label: "实际抖音月付营销补贴", kind: "money", prop: "douyin_monthly_subsidy", width: 180, defaultVisible: true },
    { key: "bank_subsidy", label: "银行补贴", kind: "money", prop: "bank_subsidy", width: 120, defaultVisible: true },
    { key: "order_refund_raw", label: "订单退款", kind: "money", prop: "order_refund_raw", width: 120, defaultVisible: true },
    { key: "platform_fee_raw", label: "平台服务费", kind: "money", prop: "platform_fee_raw", width: 140, defaultVisible: true },
    { key: "commission_raw", label: "佣金", kind: "money", prop: "commission_raw", width: 120, defaultVisible: true },
    { key: "provider_commission_raw", label: "服务商佣金", kind: "money", prop: "provider_commission_raw", width: 150, defaultVisible: true },
    { key: "channel_share", label: "渠道分成", kind: "money", prop: "channel_share", width: 120, defaultVisible: true },
    { key: "merchant_fee_raw", label: "招商服务费", kind: "money", prop: "merchant_fee_raw", width: 140, defaultVisible: true },
    { key: "promotion_fee_raw", label: "站外推广费", kind: "money", prop: "promotion_fee_raw", width: 150, defaultVisible: true },
    { key: "other_share", label: "其他分成", kind: "money", prop: "other_share", width: 120, defaultVisible: true },
    { key: "is_commission_free", label: "是否免佣", kind: "text", prop: "is_commission_free", width: 100, defaultVisible: true },
    { key: "commission_free_amount", label: "免佣金额", kind: "money", prop: "commission_free_amount", width: 120, defaultVisible: true },
    { key: "merchant_name", label: "商户主体名称", kind: "text", prop: "merchant_name", width: 220, tooltip: true, defaultVisible: true },
    { key: "remark", label: "备注", kind: "text", prop: "remark", minWidth: 260, tooltip: true, defaultVisible: true },
    { key: "matched_compensation", label: "匹配赔付", kind: "text", prop: "matched_compensation", width: 140, tooltip: true, defaultVisible: true },
    { key: "refund_to_compensation", label: "退款转赔付", kind: "money", prop: "refund_to_compensation", width: 130, defaultVisible: true },
    { key: "cashback", label: "返现", kind: "money", prop: "cashback", width: 120, defaultVisible: true },
    { key: "order_paid", label: "收", kind: "money", prop: "order_paid", width: 120, defaultVisible: true },
    { key: "refund_amount", label: "退", kind: "money", prop: "refund_amount", width: 120, defaultVisible: true },
    { key: "gmv", label: "实收GMV", kind: "money", prop: "gmv", width: 130, defaultVisible: true },
    { key: "platform_income", label: "平台其他收入", kind: "money", prop: "platform_income", width: 140, defaultVisible: true },
    { key: "platform_fee_positive", label: "平台服务费（修改正数）", kind: "money", prop: "platform_fee_positive", width: 170, defaultVisible: true },
    { key: "return_cost", label: "退货及其他费用", kind: "money", prop: "return_cost", width: 150, defaultVisible: true },
    { key: "commission_derived", label: "达人佣金", kind: "money", prop: "commission_derived", width: 130, defaultVisible: true },
    { key: "bic", label: "BIC", kind: "money", prop: "bic", width: 110, defaultVisible: true },
    { key: "insurance_fee", label: "运费险", kind: "money", prop: "insurance_fee", width: 110, defaultVisible: true },
    { key: "major_merchant_name", label: "大商家名称", kind: "text", prop: "major_merchant_name", width: 160, tooltip: true, defaultVisible: true },
    { key: "receipt_merchant", label: "收款商家", kind: "text", prop: "receipt_merchant", width: 160, tooltip: true, defaultVisible: true },
    { key: "allocated_bic", label: "分摊BIC", kind: "money", prop: "allocated_bic", width: 120, defaultVisible: true },
    { key: "allocated_insurance_fee", label: "分摊运费险", kind: "money", prop: "allocated_insurance_fee", width: 130, defaultVisible: true },
    { key: "live_amount", label: "直播款", kind: "money", prop: "live_amount", width: 130, defaultVisible: true },
    { key: "merchant_match_status", label: "商家匹配状态", kind: "text", prop: "merchant_match_status", width: 130, defaultVisible: true },
    { key: "merchant_match_error", label: "商家匹配失败原因", kind: "text", prop: "merchant_match_error", minWidth: 220, tooltip: true, defaultVisible: true },
];

const DEFAULT_VISIBLE_COLUMN_KEYS = BUSINESS_COLUMN_DEFS.filter((column) => column.defaultVisible).map((column) => column.key);
const ALWAYS_VISIBLE_COLUMN_KEYS = BUSINESS_COLUMN_DEFS.filter((column) => column.alwaysVisible).map((column) => column.key);
const COLUMN_PREFERENCE_KEY = "douyin_dongzhang_detail_visible_columns";
const DETAIL_DEFAULT_PAGE_SIZE = 50;

const props = defineProps<{
    modelValue: boolean;
    context: DouyinDongzhangDetailContext | null;
    selectedOrgIds?: number[];
    includeInSummaryExport?: boolean;
}>();

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
    "update:includeInSummaryExport": [value: boolean];
}>();

const userStore = useUserStore();
const loading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const exportSelectedLoading = ref(false);
const tableData = ref<SummaryDongzhangDetailRecord[]>([]);
const selectedRows = ref<SummaryDongzhangDetailRecord[]>([]);
const includeInSummaryExport = ref(false);
const detailTableRef = ref<{ doLayout: () => void }>();
const visibleColumnKeys = ref<string[]>([...DEFAULT_VISIBLE_COLUMN_KEYS]);
const savingVisibleColumns = ref(false);
const inFlightFetchRequestKey = ref<string | null>(null);
let inFlightFetchPromise: Promise<void> | null = null;
let latestFetchSequence = 0;

const pagination = reactive({
    page: 1,
    pageSize: DETAIL_DEFAULT_PAGE_SIZE,
    total: 0,
});

const selectedCount = computed(() => selectedRows.value.length);
const visibleBusinessColumns = computed(() => {
    const visibleSet = new Set(visibleColumnKeys.value);
    return BUSINESS_COLUMN_DEFS.filter((column) => visibleSet.has(column.key));
});
const detailContextKey = computed(() => {
    const context = props.context;
    if (!context?.summaryId) return "";
    const orgId =
        context.orgId ||
        (props.selectedOrgIds?.length ? props.selectedOrgIds.join(",") : "");
    return [
        context.summaryId,
        orgId,
        context.sourceDate || "",
        context.summaryDate || "",
        context.platform || "",
        context.shopName || "",
        context.shopColor || "",
    ].join("|");
});

watch(
    () => props.includeInSummaryExport,
    (value) => {
        const nextValue = Boolean(value);
        if (includeInSummaryExport.value !== nextValue) {
            includeInSummaryExport.value = nextValue;
        }
    },
    { immediate: true },
);

watch(includeInSummaryExport, (value) => {
    if (value !== Boolean(props.includeInSummaryExport)) {
        emit("update:includeInSummaryExport", value);
    }
});

watch(
    () => userStore.userInfo?.id,
    () => {
        restoreVisibleColumns();
    },
    { immediate: true },
);

watch([() => props.modelValue, detailContextKey], ([visible, currentContextKey]) => {
    selectedRows.value = [];
    if (!visible || !currentContextKey) return;
    if (pagination.page !== 1) {
        pagination.page = 1;
        return;
    }
    void fetchData();
});

function isColumnLocked(key: string) {
    return ALWAYS_VISIBLE_COLUMN_KEYS.includes(key);
}

function areColumnKeysEqual(left: string[], right: string[]) {
    return left.length === right.length && left.every((key, index) => key === right[index]);
}

function normalizeVisibleColumnKeys(keys: string[]) {
    const allowed = new Set(BUSINESS_COLUMN_DEFS.map((column) => column.key));
    const normalized = Array.from(new Set([...ALWAYS_VISIBLE_COLUMN_KEYS, ...keys])).filter((key) => allowed.has(key));
    const orderedSet = new Set(normalized);
    return BUSINESS_COLUMN_DEFS.map((column) => column.key).filter((key) => orderedSet.has(key));
}

async function applyVisibleColumns(keys: string[], options?: { persist?: boolean }) {
    const nextKeys = normalizeVisibleColumnKeys(keys);
    const changed = !areColumnKeysEqual(visibleColumnKeys.value, nextKeys);
    if (changed) {
        visibleColumnKeys.value = nextKeys;
    }
    if (options?.persist) {
        await persistVisibleColumns();
    }
    if (changed) {
        await nextTick();
        detailTableRef.value?.doLayout();
    }
}

function restoreVisibleColumns() {
    void restoreVisibleColumnsFromServer();
}

async function restoreVisibleColumnsFromServer() {
    if (!userStore.userInfo?.id) {
        await applyVisibleColumns(DEFAULT_VISIBLE_COLUMN_KEYS);
        return;
    }
    try {
        const preference = await getMyPreference<string[]>(COLUMN_PREFERENCE_KEY);
        const nextKeys = Array.isArray(preference?.preference_value) ? preference.preference_value : DEFAULT_VISIBLE_COLUMN_KEYS;
        await applyVisibleColumns(nextKeys);
    } catch {
        await applyVisibleColumns(DEFAULT_VISIBLE_COLUMN_KEYS);
    }
}

async function persistVisibleColumns() {
    if (!userStore.userInfo?.id || savingVisibleColumns.value) return;
    savingVisibleColumns.value = true;
    try {
        await updateMyPreference(COLUMN_PREFERENCE_KEY, visibleColumnKeys.value);
    } finally {
        savingVisibleColumns.value = false;
    }
}

function resetVisibleColumns() {
    void applyVisibleColumns(DEFAULT_VISIBLE_COLUMN_KEYS, { persist: true });
    ElMessage.success("已恢复默认字段显示");
}

function handleVisibleColumnsChange(keys: string[]) {
    void applyVisibleColumns(keys, { persist: true });
}

function handleSelectionChange(rows: SummaryDongzhangDetailRecord[]) {
    selectedRows.value = rows;
}

async function fetchData() {
    if (!props.context?.summaryId) return;
    const requestKey = [
        props.context.summaryId,
        pagination.page,
        pagination.pageSize,
        props.context.orgId ||
            (props.selectedOrgIds?.length ? props.selectedOrgIds.join(",") : ""),
    ].join("|");
    if (inFlightFetchRequestKey.value === requestKey && inFlightFetchPromise) {
        return inFlightFetchPromise;
    }
    const fetchSequence = ++latestFetchSequence;
    inFlightFetchRequestKey.value = requestKey;
    const requestPromise = (async () => {
        loading.value = true;
        try {
            const res = await getSummaryDongzhangDetailList(props.context!.summaryId, {
                page: pagination.page,
                page_size: pagination.pageSize,
                org_id:
                    props.context!.orgId ||
                    (props.selectedOrgIds?.length ? props.selectedOrgIds.join(",") : undefined),
            });
            if (fetchSequence !== latestFetchSequence) return;
            tableData.value = res.items || [];
            pagination.total = res.total || 0;
        } finally {
            if (fetchSequence === latestFetchSequence) {
                loading.value = false;
                await nextTick();
                detailTableRef.value?.doLayout();
            }
            if (inFlightFetchPromise === requestPromise) {
                inFlightFetchPromise = null;
                inFlightFetchRequestKey.value = null;
            }
        }
    })();
    inFlightFetchPromise = requestPromise;
    return requestPromise;
}

async function handleExport(scope: "all" | "current_page" | "selected") {
    if (!props.context?.summaryId) return;
    if (scope === "current_page" && tableData.value.length === 0) {
        ElMessage.warning("当前页暂无可导出的源明细");
        return;
    }
    if (scope === "selected" && selectedCount.value === 0) {
        ElMessage.warning("请先选择要导出的源明细");
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
            summary_id: props.context.summaryId,
            org_id:
                props.context.orgId ||
                (props.selectedOrgIds?.length ? props.selectedOrgIds.join(",") : undefined),
            scope,
            ids: scope === "selected" ? selectedRows.value.map((row) => row.id).join(",") : undefined,
            page: scope === "current_page" ? pagination.page : undefined,
            page_size: scope === "current_page" ? pagination.pageSize : undefined,
        };
        const scopeLabel = scope === "all" ? "全部" : scope === "current_page" ? `第${pagination.page}页` : "选中";
        await submitExportJob({
            export_type: "summary.dongzhang_details",
            title: "抖音动账源明细导出",
            filename: normalizeExportFilename(`抖音动账源明细_${props.context.sourceDate || "全部核算年月"}_${props.context.shopName || "全部店铺"}_${scopeLabel}.xlsx`),
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
</script>

<style scoped lang="scss">
.detail-drawer {
    display: flex;
    flex-direction: column;
    gap: 14px;
    height: 100%;
    min-height: 0;
}

.detail-toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
}

.detail-toolbar-copy {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-width: 0;
}

.detail-toolbar-kicker {
    margin: 0;
    color: var(--el-color-primary);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.08em;
}

.detail-context {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    min-width: 0;
}

.context-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    min-height: 26px;
    color: var(--text-secondary);
    font-size: 13px;
}

.detail-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.column-button-count {
    margin-left: 2px;
    color: var(--text-tertiary);
    font-size: 12px;
}

.column-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.column-panel-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
}

.column-panel-title {
    margin: 0;
    color: var(--text-primary);
    font-size: 14px;
    font-weight: 600;
}

.column-panel-subtitle {
    margin: 4px 0 0;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;
}

.column-checkbox-group {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px 14px;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
}

:deep(.summary-detail-table) {
    border-top: 1px solid var(--border-light);
}

:global(.douyin-detail-drawer .el-drawer__header) {
    display: flex;
    align-items: center;
    min-height: 58px;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}

.fill-table {
    flex: 1;
    min-height: 0;
    height: 100% !important;
    overflow: hidden;

    :deep(.el-table__inner-wrapper) {
        display: flex;
        flex-direction: column;
    }

    :deep(.el-table__body-wrapper) {
        flex: 1;
        min-height: 0;
        overflow: auto;
    }
}

:deep(.column-checkbox-group .el-checkbox) {
    margin-right: 0;
    min-width: 0;
}

:deep(.el-drawer__body) {
    padding: 12px 14px 14px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

@media (max-width: 768px) {
    .detail-toolbar {
        flex-direction: column;
    }

    .detail-actions {
        justify-content: flex-start;
    }

    .column-checkbox-group {
        grid-template-columns: 1fr;
    }
}
</style>
