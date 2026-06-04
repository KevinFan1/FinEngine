<template>
    <div class="page-container transaction-page">
        <MerchantFilters
            :model="searchForm"
            :shops="douyinShops"
            :orgs="orgOptions"
            :show-org="userStore.isSuperAdmin"
            :show-shop="false"
            :show-keyword="false"
            :shop-loading="shopLoading"
            @update:model="Object.assign(searchForm, $event)"
            @org-change="handleOrgChange"
            @search="handleSearch"
            @reset="handleReset"
        />

        <el-card shadow="never" class="table-card">
            <template #header>
                <div class="card-header">
                    <div class="summary-title-group">
                        <span class="card-header-title">净额比例</span>
                        <span class="summary-count">{{ footerText }}</span>
                    </div>
                    <div class="card-header-actions">
                        <el-button :disabled="!hasMonth" :loading="loading" @click="fetchData">
                            <el-icon><Refresh /></el-icon>
                            刷新
                        </el-button>
                        <el-button type="primary" :disabled="changedRows.length === 0" :loading="saving" @click="saveRows">
                            <el-icon><Check /></el-icon>
                            保存
                        </el-button>
                    </div>
                </div>
            </template>

            <el-table class="summary-table roomy-table" :data="tableData" v-loading="loading" stripe border>
                <el-table-column v-if="userStore.isSuperAdmin" prop="org_name" label="组织" min-width="220" show-overflow-tooltip />
                <el-table-column label="业务年月" width="110">
                    <template #default="{ row }">{{ formatMonth(row.accounting_year, row.accounting_month) }}</template>
                </el-table-column>
                <el-table-column label="平台" width="100">
                    <template #default>抖音</template>
                </el-table-column>
                <el-table-column label="净额比例" width="200" align="right">
                    <template #default="{ row }">
                        <el-input-number
                            v-model="row.editing_percent"
                            :min="0"
                            :max="100"
                            :precision="2"
                            :step="1"
                            controls-position="right"
                            class="rate-input"
                        />
                    </template>
                </el-table-column>
                <el-table-column label="状态" width="110" align="center">
                    <template #default="{ row }">
                        <el-tag :type="row.is_default ? 'info' : 'success'" effect="plain" size="small">
                            {{ row.is_default ? "默认70%" : "已维护" }}
                        </el-tag>
                    </template>
                </el-table-column>
                <el-table-column label="备注" min-width="240">
                    <template #default="{ row }">
                        <el-input v-model="row.remark" clearable placeholder="备注" />
                    </template>
                </el-table-column>
                <el-table-column prop="updated_at" label="更新时间" width="180" />
            </el-table>
        </el-card>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { Check, Refresh } from "@element-plus/icons-vue";
import {
    listMerchantNetRateSettings,
    upsertMerchantNetRateSettings,
    type MerchantNetRateSetting,
} from "@/api/merchantReconciliation";
import MerchantFilters from "./components/MerchantFilters.vue";
import { formatMonth, selectedMonthParts } from "./common";
import { useMerchantReconciliationFilters } from "./composables";

defineOptions({ name: "MerchantReconciliationNetRates" });

type RateRow = MerchantNetRateSetting & {
    editing_percent: number;
    original_percent: number;
    original_remark: string;
};

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
const saving = ref(false);
const tableData = ref<RateRow[]>([]);
const hasMonth = computed(() => Boolean(searchForm.month));
const changedRows = computed(() =>
    tableData.value.filter((row) =>
        Number(row.editing_percent || 0).toFixed(2) !== Number(row.original_percent || 0).toFixed(2)
        || String(row.remark || "") !== String(row.original_remark || ""),
    ),
);
const footerText = computed(() => {
    if (!hasMonth.value) return "请选择数据年月";
    return `共 ${tableData.value.length} 个组织 · 已修改 ${changedRows.value.length} 条`;
});

function queryParams(showMessage = true) {
    const month = selectedMonthParts(searchForm.month);
    if (!month.accounting_year || !month.accounting_month) {
        if (showMessage) ElMessage.warning("请选择数据年月");
        return null;
    }
    return {
        accounting_year: month.accounting_year,
        accounting_month: month.accounting_month,
        org_id: searchForm.orgId,
        platform_code: "douyin",
    };
}

async function fetchData() {
    const params = queryParams(true);
    if (!params) return;
    loading.value = true;
    try {
        const rows = await listMerchantNetRateSettings(params);
        tableData.value = (rows || []).map((row) => {
            const percent = Number(row.net_rate_percent || 70);
            return {
                ...row,
                editing_percent: percent,
                original_percent: percent,
                original_remark: row.remark || "",
            };
        });
    } finally {
        loading.value = false;
    }
}

async function saveRows() {
    const params = queryParams(true);
    if (!params) return;
    const rows = changedRows.value;
    if (rows.length === 0) {
        ElMessage.info("没有需要保存的比例");
        return;
    }
    saving.value = true;
    try {
        const result = await upsertMerchantNetRateSettings({
            accounting_year: params.accounting_year,
            accounting_month: params.accounting_month,
            platform_code: "douyin",
            items: rows.map((row) => ({
                org_id: row.org_id,
                net_rate_percent: row.editing_percent,
                remark: row.remark || "",
            })),
        });
        ElMessage.success(`已保存 ${result.total_count || rows.length} 条净额比例`);
        await fetchData();
    } finally {
        saving.value = false;
    }
}

async function handleSearch() {
    await fetchData();
}

async function handleReset() {
    resetFilters();
    await fetchShops();
    tableData.value = [];
}

onMounted(async () => {
    await fetchOrgs();
    await fetchShops();
});
</script>

<style scoped lang="scss">
@use "../transaction-accounting/transaction.scss";

.rate-input {
    width: 150px;
}
</style>
