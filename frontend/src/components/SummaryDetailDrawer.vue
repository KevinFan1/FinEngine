<template>
    <el-drawer
        :model-value="modelValue"
        title="动账明细"
        size="86%"
        append-to-body
        destroy-on-close
        :close-on-click-modal="false"
        @update:model-value="emit('update:modelValue', $event)"
    >
        <div class="detail-drawer">
            <div class="detail-toolbar">
                <div class="detail-toolbar-copy">
                    <p class="detail-toolbar-kicker">动账明细抽屉</p>
                    <div class="detail-context">
                        <span class="context-item"
                            >核算年月：{{ context?.sourceDate || "-" }}</span
                        >
                        <span class="context-item">
                            归集平台：
                            <PlatformBadge
                                v-if="
                                    context?.reportPlatform || context?.platform
                                "
                                :platform="
                                    context.reportPlatform || context.platform
                                "
                            />
                            <template v-else>-</template>
                        </span>
                        <span class="context-item">
                            店铺：
                            <ShopBadge
                                :label="context?.shopName || '-'"
                                :color="context?.shopColor"
                                size="table"
                            />
                        </span>
                        <span class="context-item"
                            >汇总行数：{{ context?.summaryCount || 0 }}</span
                        >
                    </div>
                </div>
                <div class="detail-actions">
                    <el-button
                        :loading="exportCurrentPageLoading"
                        @click="handleExport('current_page')"
                    >
                        <el-icon><Download /></el-icon> 导出当前页
                    </el-button>
                    <el-button
                        type="success"
                        :loading="exportAllLoading"
                        @click="handleExport('all')"
                    >
                        <el-icon><Download /></el-icon> 导出全部
                    </el-button>
                </div>
            </div>

            <el-table
                ref="detailTableRef"
                class="summary-table summary-detail-table"
                :data="tableData"
                v-loading="loading"
                stripe
                border
                show-summary
                :summary-method="getSummary"
                :fit="false"
                style="width: 100%"
                height="calc(100vh - 238px)"
                row-key="id"
            >
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
                    v-if="props.context?.orgId || (props.selectedOrgIds?.length || 0) > 0"
                    prop="org_name"
                    label="组织"
                    width="170"
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
                        <PlatformBadge :platform="row.platform" />
                    </template>
                </el-table-column>
                <el-table-column
                    prop="report_platform"
                    label="归集平台"
                    width="112"
                >
                    <template #default="{ row }">
                        <PlatformBadge :platform="row.report_platform" />
                    </template>
                </el-table-column>
                <el-table-column
                    prop="shop_name"
                    label="店铺"
                    width="220"
                    show-overflow-tooltip
                >
                    <template #default="{ row }">
                        <ShopBadge
                            :label="row.shop_name || '-'"
                            :color="row.shop_color"
                            size="table"
                        />
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
                    class-name="money-column"
                >
                    <template #default="{ row }">
                        <span class="font-mono money-cell">{{
                            formatMoney(row.bic)
                        }}</span>
                    </template>
                </el-table-column>

                <template #empty>
                    <el-empty description="暂无明细数据" :image-size="80" />
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
import { reactive, ref, watch, nextTick } from "vue";
import { Download } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus/es/components/message/index.mjs";
import type { TableColumnCtx } from "element-plus/es/components/table/index.mjs";
import { getSummaryList, type SummaryRecord } from "@/api/summary";
import { formatMoney } from "@/utils/format";
import {
    DEFAULT_PAGE_SIZE,
    PAGE_SIZE_OPTIONS,
    PAGINATION_LAYOUT,
} from "@/utils/pagination";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import { normalizeExportFilename, submitExportJob } from "@/utils/exportJobs";

export interface SummaryDetailContext {
    sourceYear?: number;
    sourceMonth?: number;
    sourceDate?: string;
    orgId?: number;
    orgName?: string | null;
    platform?: string;
    reportPlatform?: string;
    shopName?: string;
    shopColor?: string | null;
    summaryCount?: number;
}

const props = defineProps<{
    modelValue: boolean;
    context: SummaryDetailContext | null;
    selectedOrgIds?: number[];
}>();

const emit = defineEmits<{
    "update:modelValue": [value: boolean];
}>();

const loading = ref(false);
const exportAllLoading = ref(false);
const exportCurrentPageLoading = ref(false);
const tableData = ref<SummaryRecord[]>([]);
const detailTableRef = ref<{ doLayout: () => void }>();

const pagination = reactive({
    page: 1,
    pageSize: DEFAULT_PAGE_SIZE,
    total: 0,
});

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

watch(
    () => props.modelValue,
    (visible) => {
        if (visible) {
            pagination.page = 1;
            fetchData();
        }
    },
);

watch(
    () => props.context,
    () => {
        if (props.modelValue) {
            pagination.page = 1;
            fetchData();
        }
    },
);

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

async function fetchData() {
    if (!props.context) return;
    loading.value = true;
    try {
        const res = await getSummaryList({
            page: pagination.page,
            page_size: pagination.pageSize,
            org_id:
                props.context.orgId ||
                (props.selectedOrgIds?.length
                    ? props.selectedOrgIds.join(",")
                    : undefined),
            source_year: props.context.sourceYear,
            source_month: props.context.sourceMonth,
            platform_name: props.context.platform || undefined,
            report_platform_name: props.context.reportPlatform || undefined,
            shop_name: props.context.shopName || undefined,
        });
        tableData.value = res.items || [];
        pagination.total = res.total || 0;
    } catch {
        // Error handled by interceptor
    } finally {
        loading.value = false;
        await nextTick();
        detailTableRef.value?.doLayout();
    }
}

async function handleExport(scope: "all" | "current_page") {
    if (!props.context) return;
    if (scope === "current_page" && tableData.value.length === 0) {
        ElMessage.warning("当前页暂无可导出的明细数据");
        return;
    }

    const loadingRef =
        scope === "all" ? exportAllLoading : exportCurrentPageLoading;
    loadingRef.value = true;
    try {
        const params = {
            org_id:
                props.context.orgId ||
                (props.selectedOrgIds?.length
                    ? props.selectedOrgIds.join(",")
                    : undefined),
            source_year: props.context.sourceYear,
            source_month: props.context.sourceMonth,
            platform_name: props.context.platform || undefined,
            report_platform_name: props.context.reportPlatform || undefined,
            shop_name: props.context.shopName || undefined,
            scope,
            page: scope === "current_page" ? pagination.page : undefined,
            page_size:
                scope === "current_page" ? pagination.pageSize : undefined,
        };
        const scopeLabel = scope === "all" ? "全部" : `第${pagination.page}页`;
        await submitExportJob({
            export_type: "summary.detail",
            title: "汇总明细导出",
            filename: normalizeExportFilename(`汇总明细_${props.context.sourceDate || "全部核算年月"}_${props.context.shopName || "全部店铺"}_${scopeLabel}.xlsx`),
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
    flex-shrink: 0;
}

.pagination-area {
    display: flex;
    justify-content: flex-end;
}

:deep(.summary-detail-table) {
    border-top: 1px solid var(--border-light);
}

@media (max-width: 768px) {
    .detail-toolbar {
        flex-direction: column;
    }
}
</style>
