<template>
    <el-table
        ref="tableRef"
        class="summary-table roomy-table source-table bic-source-table"
        :data="rows"
        v-loading="loading"
        stripe
        border
        :height="height"
        row-key="id"
        @selection-change="handleSelectionChange"
    >
        <el-table-column v-if="selectable" type="selection" width="48" fixed="left" :reserve-selection="true" />
        <el-table-column label="序号" width="78" fixed="left" align="center">
            <template #default="{ $index }">{{ offset + $index + 1 }}</template>
        </el-table-column>
        <el-table-column prop="accounting_year" label="核算年月" width="112" align="center">
            <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
        </el-table-column>
        <el-table-column prop="platform_code" label="平台" width="110">
            <template #default="{ row }"><PlatformBadge :platform="row.platform_code" /></template>
        </el-table-column>
        <el-table-column v-if="showOrg" label="组织" width="170" show-overflow-tooltip>
            <template #default="{ row }">{{ row.org_name || `组织#${row.org_id}` }}</template>
        </el-table-column>
        <el-table-column prop="store_short_id" label="店铺id" width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.store_short_id || "-" }}</template>
        </el-table-column>
        <el-table-column prop="shop_name" label="店铺名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }"><ShopBadge :label="row.shop_name || '-'" :color="shopColorByName?.get(row.shop_name || '')" size="table" /></template>
        </el-table-column>
        <el-table-column prop="service_provider" label="服务商" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.service_provider || "-" }}</template>
        </el-table-column>
        <el-table-column prop="qic_warehouse" label="QIC仓" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.qic_warehouse || "-" }}</template>
        </el-table-column>
        <el-table-column prop="settlement_no" label="结算单号" min-width="220" show-overflow-tooltip />
        <el-table-column prop="order_code" label="订单码" min-width="120" show-overflow-tooltip />
        <el-table-column prop="related_order_no" label="关联订单号" min-width="160" show-overflow-tooltip />
        <el-table-column prop="related_waybill_no" label="关联运单号" min-width="160" show-overflow-tooltip />
        <el-table-column prop="fee_item" label="费用项" min-width="130" show-overflow-tooltip />
        <el-table-column prop="settlement_amount" label="结算金额" min-width="120" align="right" header-align="right">
            <template #default="{ row }"><span class="font-mono money-cell">{{ formatAmount(row.settlement_amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="billing_params" label="计费参数" min-width="260" show-overflow-tooltip />
        <el-table-column prop="billing_completed_time" label="计费完成时间" min-width="170" show-overflow-tooltip />
        <el-table-column prop="business_node" label="业务节点" min-width="120" show-overflow-tooltip />
        <el-table-column prop="business_occurred_time" label="业务发生时间" min-width="170" show-overflow-tooltip />
        <el-table-column prop="settled_at" label="结算时间" min-width="170" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" min-width="110" show-overflow-tooltip />
        <el-table-column prop="transaction_account" label="动账账户" min-width="120" show-overflow-tooltip />
        <el-table-column prop="transaction_flow_no" label="动账流水号" min-width="230" show-overflow-tooltip />
        <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
        <el-table-column prop="is_mudaibao" label="是否木带宝" width="120" show-overflow-tooltip />
        <el-table-column prop="is_child_order" label="是否子单" width="110" show-overflow-tooltip />
    </el-table>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { TableInstance } from "element-plus";
import PlatformBadge from "@/components/PlatformBadge.vue";
import ShopBadge from "@/components/ShopBadge.vue";
import type { BicSourceRow } from "@/api/bicAccounting";
import { formatAmount, formatMonth } from "./common";

withDefaults(defineProps<{
    rows: BicSourceRow[];
    loading?: boolean;
    height?: string;
    offset?: number;
    showOrg?: boolean;
    selectable?: boolean;
    shopColorByName?: Map<string, string | undefined>;
}>(), {
    loading: false,
    offset: 0,
    showOrg: false,
    selectable: false,
});

const emit = defineEmits<{
    (event: "selection-change", rows: BicSourceRow[]): void;
}>();

const tableRef = ref<TableInstance>();

function handleSelectionChange(rows: BicSourceRow[]) {
    emit("selection-change", rows);
}

defineExpose({
    clearSelection: () => tableRef.value?.clearSelection(),
});
</script>

<style scoped lang="scss">
:deep(.bic-source-table .cell) {
    white-space: nowrap;
}
</style>
