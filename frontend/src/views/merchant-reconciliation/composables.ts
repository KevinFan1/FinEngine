import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { getAllOrganizations, type Organization } from "@/api/organization";
import { getShopList, type Shop } from "@/api/shop";
import { useUserStore } from "@/stores/user";
import { isDouyinShop, selectedMonthParts } from "./common";

export interface MerchantFilterState {
    month: string;
    orgId?: number;
    shopId?: number | number[];
    matchStatus?: string;
    bankStatus?: string;
    keyword: string;
}

export function useMerchantReconciliationFilters(options: { multipleShops?: boolean; autoSelectFirstShop?: boolean } = {}) {
    const userStore = useUserStore();
    const shopLoading = ref(false);
    const shops = ref<Shop[]>([]);
    const orgOptions = ref<Organization[]>([]);
    const searchForm = reactive<MerchantFilterState>({
        month: "",
        orgId: undefined,
        shopId: options.multipleShops ? [] : undefined,
        matchStatus: "",
        bankStatus: "",
        keyword: "",
    });
    const douyinShops = computed(() => shops.value.filter(isDouyinShop));

    async function fetchOrgs() {
        if (!userStore.isSuperAdmin) return;
        orgOptions.value = await getAllOrganizations();
    }

    async function fetchShops() {
        shopLoading.value = true;
        try {
            const result = await getShopList({
                page: 1,
                page_size: 1000,
                org_id: searchForm.orgId,
                platform_name: "抖音",
            });
            shops.value = result.items || [];
            if (options.autoSelectFirstShop !== false && !options.multipleShops && !searchForm.shopId && douyinShops.value.length) {
                searchForm.shopId = douyinShops.value[0].id;
            }
        } finally {
            shopLoading.value = false;
        }
    }

    async function handleOrgChange() {
        searchForm.shopId = options.multipleShops ? [] : undefined;
        await fetchShops();
    }

    function resetFilters() {
        searchForm.month = "";
        searchForm.orgId = undefined;
        searchForm.shopId = options.multipleShops ? [] : undefined;
        searchForm.matchStatus = "";
        searchForm.bankStatus = "";
        searchForm.keyword = "";
    }

    function requireMonth(showMessage = true) {
        const parts = selectedMonthParts(searchForm.month);
        if (!parts.accounting_year || !parts.accounting_month) {
            if (showMessage) {
                ElMessage.warning("请选择业务年月");
            }
            return null;
        }
        return parts;
    }

    function requireSingleShop(showMessage = true) {
        const month = requireMonth(showMessage);
        const shopId = Number(searchForm.shopId || 0);
        if (!month) return null;
        if (!shopId) {
            if (showMessage) {
                ElMessage.warning("请选择店铺");
            }
            return null;
        }
        return { ...month, shop_id: shopId };
    }

    function redSheetParams() {
        const month = selectedMonthParts(searchForm.month);
        const shopIds = Array.isArray(searchForm.shopId)
            ? searchForm.shopId.join(",")
            : searchForm.shopId
              ? String(searchForm.shopId)
              : undefined;
        const params: {
            accounting_year?: number;
            accounting_month?: number;
            org_id?: number;
            shop_ids?: string;
            keyword?: string;
        } = {
            org_id: searchForm.orgId,
            shop_ids: shopIds,
            keyword: searchForm.keyword || undefined,
        };
        if (month.accounting_year && month.accounting_month) {
            params.accounting_year = month.accounting_year;
            params.accounting_month = month.accounting_month;
        }
        return params;
    }

    return {
        userStore,
        searchForm,
        shops,
        douyinShops,
        orgOptions,
        shopLoading,
        fetchOrgs,
        fetchShops,
        handleOrgChange,
        resetFilters,
        requireMonth,
        requireSingleShop,
        redSheetParams,
    };
}
