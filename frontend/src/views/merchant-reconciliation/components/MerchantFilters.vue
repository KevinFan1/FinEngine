<template>
    <el-card shadow="never" class="search-card">
        <el-form :model="model" inline class="filter-form">
            <el-form-item v-if="showMonth" label="数据年月">
                <el-date-picker
                    :model-value="model.month"
                    type="month"
                    clearable
                    value-format="YYYY-MM"
                    placeholder="选择月份"
                    style="width: 170px"
                    @update:model-value="updateField('month', $event)"
                />
            </el-form-item>
            <el-form-item v-if="showOrg" label="组织">
                <el-select
                    :model-value="model.orgId"
                    clearable
                    filterable
                    placeholder="组织"
                    style="width: 190px"
                    @update:model-value="handleOrgUpdate"
                >
                    <el-option v-for="org in orgs" :key="org.id" :label="org.name" :value="org.id" />
                </el-select>
            </el-form-item>
            <el-form-item v-if="showShop" label="店铺">
                <el-select
                    :model-value="model.shopId"
                    :multiple="multipleShops"
                    clearable
                    filterable
                    collapse-tags
                    collapse-tags-tooltip
                    :placeholder="multipleShops ? '选择抖音店铺' : '选择抖音店铺'"
                    :loading="shopLoading"
                    :style="{ width: multipleShops ? '260px' : '240px' }"
                    @update:model-value="updateField('shopId', $event)"
                >
                    <el-option
                        v-for="shop in shops"
                        :key="shop.id"
                        :label="shop.shop_name"
                        :value="shop.id"
                    >
                        <ShopBadge :label="shop.shop_name" :color="shop.shop_color" size="compact" />
                    </el-option>
                </el-select>
            </el-form-item>
            <el-form-item v-if="showMatchStatus" label="匹配状态">
                <el-select
                    :model-value="model.matchStatus"
                    clearable
                    placeholder="全部"
                    style="width: 130px"
                    @update:model-value="updateField('matchStatus', $event)"
                >
                    <el-option label="已匹配" value="matched" />
                    <el-option label="未匹配" value="unmatched" />
                </el-select>
            </el-form-item>
            <el-form-item v-if="showBankStatus" label="银行流水状态">
                <el-select
                    :model-value="model.bankStatus"
                    clearable
                    placeholder="全部"
                    style="width: 140px"
                    @update:model-value="updateField('bankStatus', $event)"
                >
                    <el-option label="待匹配" value="pending" />
                    <el-option label="已匹配" value="matched" />
                    <el-option label="有差异" value="diff" />
                </el-select>
            </el-form-item>
            <el-form-item v-if="showKeyword" label="搜索">
                <el-input
                    :model-value="model.keyword"
                    clearable
                    :placeholder="keywordPlaceholder"
                    style="width: 220px"
                    @update:model-value="updateField('keyword', $event)"
                    @keyup.enter="$emit('search')"
                />
            </el-form-item>
            <el-form-item v-if="showActions">
                <el-button type="primary" @click="$emit('search')">搜索</el-button>
                <el-button @click="$emit('reset')">重置</el-button>
            </el-form-item>
        </el-form>
    </el-card>
</template>

<script setup lang="ts">
import type { Organization } from "@/api/organization";
import type { Shop } from "@/api/shop";
import ShopBadge from "@/components/ShopBadge.vue";

interface MerchantFilterModel {
    month?: string;
    orgId?: number;
    shopId?: number | number[];
    matchStatus?: string;
    bankStatus?: string;
    keyword?: string;
}

const props = withDefaults(
    defineProps<{
        model: MerchantFilterModel;
        shops: Shop[];
        orgs: Organization[];
        showOrg?: boolean;
        shopLoading?: boolean;
        showMonth?: boolean;
        showShop?: boolean;
        showMatchStatus?: boolean;
        showBankStatus?: boolean;
        showKeyword?: boolean;
        showActions?: boolean;
        keywordPlaceholder?: string;
        multipleShops?: boolean;
    }>(),
    {
        showOrg: false,
        shopLoading: false,
        showMonth: true,
        showShop: true,
        showMatchStatus: false,
        showBankStatus: false,
        showKeyword: true,
        showActions: true,
        keywordPlaceholder: "搜索关键字",
        multipleShops: false,
    },
);

const emit = defineEmits<{
    (event: "update:model", value: MerchantFilterModel): void;
    (event: "org-change"): void;
    (event: "search"): void;
    (event: "reset"): void;
}>();

function updateField(field: keyof MerchantFilterModel, value: unknown) {
    emit("update:model", { ...props.model, [field]: value });
}

function handleOrgUpdate(value: unknown) {
    updateField("orgId", value);
    emit("org-change");
}

</script>
