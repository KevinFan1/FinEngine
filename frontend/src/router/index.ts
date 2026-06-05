import {
    createRouter,
    createWebHistory,
    type RouteRecordRaw,
} from "vue-router";
import { useUserStore } from "@/stores/user";
import { forceLogout } from "@/utils/authSession";
import { getStoredAuthToken, isAuthTokenExpired } from "@/utils/authToken";

const routes: RouteRecordRaw[] = [
    {
        path: "/login",
        name: "Login",
        component: () => import("@/views/login/index.vue"),
        meta: { requiresAuth: false, title: "登录" },
    },
    {
        path: "/",
        component: () => import("@/layouts/DefaultLayout.vue"),
        redirect: "/dashboard",
        meta: { requiresAuth: true },
        children: [
            {
                path: "dashboard",
                name: "Dashboard",
                component: () => import("@/views/dashboard/index.vue"),
                meta: { title: "首页", icon: "House" },
            },
            {
                path: "profile",
                name: "ProfileCenter",
                component: () => import("@/views/profile/index.vue"),
                meta: { title: "个人中心", icon: "User" },
            },
            {
                path: "organizations",
                name: "Organizations",
                component: () => import("@/views/organization/index.vue"),
                meta: {
                    title: "组织管理",
                    icon: "OfficeBuilding",
                    roles: ["superadmin"],
                },
            },
            {
                path: "users",
                name: "Users",
                component: () => import("@/views/user/index.vue"),
                meta: {
                    title: "用户管理",
                    icon: "User",
                    roles: ["superadmin", "org_admin"],
                },
            },
            {
                path: "shops",
                name: "Shops",
                component: () => import("@/views/shop/index.vue"),
                meta: { title: "店铺管理", icon: "Shop" },
            },
            {
                path: "category-dicts",
                name: "CategoryDicts",
                component: () => import("@/views/category-dict/index.vue"),
                meta: {
                    title: "动账重分类字典",
                    icon: "Collection",
                    roles: ["superadmin"],
                },
            },
            {
                path: "file-specs",
                name: "FileSpecs",
                component: () => import("@/views/file-specs/index.vue"),
                meta: {
                    title: "文件规格配置",
                    icon: "Setting",
                    roles: ["superadmin"],
                },
            },
            {
                path: "upload",
                name: "UploadCenter",
                component: () => import("@/views/upload/index.vue"),
                meta: { title: "上传中心", icon: "Upload" },
            },
            {
                path: "downloads",
                name: "DownloadCenter",
                component: () => import("@/views/download/index.vue"),
                meta: { title: "下载中心", icon: "Download" },
            },
            {
                path: "tasks",
                name: "Tasks",
                component: () => import("@/views/task/index.vue"),
                meta: { title: "核算任务", icon: "List" },
            },
            {
                path: "summaries",
                name: "Summaries",
                component: () => import("@/views/summary/index.vue"),
                meta: { title: "汇总明细", icon: "Document" },
            },
            {
                path: "summary-report",
                name: "SummaryReport",
                component: () => import("@/views/summary-report/index.vue"),
                meta: { title: "汇总报表", icon: "DataAnalysis" },
            },
            {
                path: "transaction-upload",
                name: "TransactionUploadCenter",
                redirect: "/upload",
                meta: { title: "上传中心", icon: "Upload" },
            },
            {
                path: "transaction-tasks",
                name: "TransactionTasks",
                component: () =>
                    import("@/views/transaction-accounting/tasks.vue"),
                meta: { title: "资金任务", icon: "List" },
            },
            {
                path: "transaction-major-categories",
                name: "TransactionMajorCategories",
                component: () =>
                    import("@/views/transaction-accounting/major-categories.vue"),
                meta: {
                    title: "资金大分类",
                    icon: "CollectionTag",
                    roles: ["superadmin"],
                },
            },
            {
                path: "transaction-rules",
                name: "TransactionRules",
                component: () =>
                    import("@/views/transaction-accounting/rules.vue"),
                meta: {
                    title: "资金重分类规则",
                    icon: "Setting",
                    roles: ["superadmin"],
                },
            },
            {
                path: "transaction-summaries",
                name: "TransactionSummaries",
                component: () =>
                    import("@/views/transaction-accounting/details.vue"),
                meta: { title: "科目明细", icon: "Document" },
            },
            {
                path: "transaction-summary-report",
                name: "TransactionSummaryReport",
                component: () =>
                    import("@/views/transaction-accounting/report.vue"),
                meta: { title: "年度报表", icon: "DataAnalysis" },
            },
            {
                path: "bic-tasks",
                name: "BicTasks",
                component: () => import("@/views/bic-accounting/tasks.vue"),
                meta: { title: "BIC任务", icon: "List" },
            },
            {
                path: "bic-summary",
                name: "BicSummary",
                component: () => import("@/views/bic-accounting/details.vue"),
                meta: { title: "BIC汇总", icon: "Document" },
            },
            {
                path: "bic-details",
                name: "BicDetails",
                component: () => import("@/views/bic-accounting/source.vue"),
                meta: { title: "BIC源明细", icon: "Document" },
            },
            {
                path: "reconciliation-checklist",
                name: "ReconciliationChecklist",
                redirect: "/reconciliation-checklist/summary",
                meta: { title: "对账清单", icon: "DataAnalysis" },
            },
            {
                path: "reconciliation-checklist/upload",
                name: "ReconciliationChecklistUpload",
                component: () => import("@/views/reconciliation-checklist/upload.vue"),
                meta: { title: "对账清单上传", icon: "Upload" },
            },
            {
                path: "reconciliation-checklist/tasks",
                name: "ReconciliationChecklistTasks",
                component: () => import("@/views/reconciliation-checklist/tasks.vue"),
                meta: { title: "对账清单任务", icon: "List" },
            },
            {
                path: "reconciliation-checklist/summary",
                name: "ReconciliationChecklistSummary",
                component: () => import("@/views/reconciliation-checklist/summary.vue"),
                meta: { title: "对账清单汇总", icon: "DataAnalysis" },
            },
            {
                path: "merchant-reconciliation",
                name: "MerchantReconciliation",
                redirect: "/merchant-reconciliation/tasks",
                meta: { title: "商家对账", icon: "Money" },
            },
            {
                path: "merchant-reconciliation/upload",
                name: "MerchantReconciliationUpload",
                component: () => import("@/views/merchant-reconciliation/upload.vue"),
                meta: { title: "上传中心", icon: "Upload" },
            },
            {
                path: "merchant-reconciliation/tasks",
                name: "MerchantReconciliationTasks",
                component: () => import("@/views/merchant-reconciliation/tasks.vue"),
                meta: { title: "对账任务", icon: "List" },
            },
            {
                path: "merchant-reconciliation/unmatched",
                name: "MerchantReconciliationUnmatched",
                component: () => import("@/views/merchant-reconciliation/unmatched.vue"),
                meta: { title: "未匹配维护", icon: "Warning" },
            },
            {
                path: "merchant-reconciliation/payments",
                name: "MerchantReconciliationPayments",
                component: () => import("@/views/merchant-reconciliation/payments.vue"),
                meta: { title: "货款明细", icon: "Document" },
            },
            {
                path: "merchant-reconciliation/purchases",
                name: "MerchantReconciliationPurchases",
                component: () => import("@/views/merchant-reconciliation/purchases.vue"),
                meta: { title: "采购明细", icon: "Document" },
            },
            {
                path: "merchant-reconciliation/bank-flows",
                name: "MerchantReconciliationBankFlows",
                component: () => import("@/views/merchant-reconciliation/bank-flows.vue"),
                meta: { title: "银行流水", icon: "Wallet" },
            },
            {
                path: "merchant-reconciliation/summary",
                name: "MerchantReconciliationSummary",
                component: () => import("@/views/merchant-reconciliation/summary.vue"),
                meta: { title: "汇总数据", icon: "DataAnalysis" },
            },
            {
                path: "merchant-reconciliation/net-rates",
                name: "MerchantReconciliationNetRates",
                component: () => import("@/views/merchant-reconciliation/net-rates.vue"),
                meta: { title: "净额比例", icon: "Setting" },
            },
            {
                path: "audit-logs",
                name: "AuditLogs",
                component: () => import("@/views/audit/index.vue"),
                meta: {
                    title: "操作日志",
                    icon: "Document",
                    roles: ["superadmin", "org_admin"],
                },
            },
        ],
    },
    {
        path: "/:pathMatch(.*)*",
        redirect: "/dashboard",
    },
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

// Navigation guards
router.beforeEach((to, _from, next) => {
    const token = getStoredAuthToken();
    const tokenExpired = Boolean(token && isAuthTokenExpired(token));

    let userInfo: any = null;
    try {
        const raw = localStorage.getItem("userInfo");
        userInfo = raw && raw !== "undefined" ? JSON.parse(raw) : null;
    } catch {
        userInfo = null;
    }

    // Set page title
    const title = to.meta.title
        ? `${to.meta.title} - FinEngine 财务核算平台`
        : "FinEngine 财务核算平台";
    document.title = title as string;

    // Public routes (login page)
    if (to.meta.requiresAuth === false) {
        if (token && !tokenExpired) {
            // Already logged in, redirect to dashboard
            next("/dashboard");
        } else {
            if (tokenExpired) {
                forceLogout({ redirect: false, notify: false, broadcast: false });
            }
            next();
        }
        return;
    }

    // Protected routes - check authentication
    if (!token) {
        next({ path: "/login", query: { redirect: to.fullPath } });
        return;
    }

    if (tokenExpired) {
        forceLogout({ redirect: false, notify: false, broadcast: true });
        next({ path: "/login", query: { redirect: to.fullPath } });
        return;
    }

    // Check role-based access
    const requiredRoles = to.meta.roles as string[] | undefined;
    if (requiredRoles && requiredRoles.length > 0) {
        const userRole = userInfo?.role || "";
        if (!requiredRoles.includes(userRole)) {
            // No permission, redirect to dashboard
            next("/dashboard");
            return;
        }
    }

    next();
});

export default router;
