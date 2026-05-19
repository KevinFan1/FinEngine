import {
    createRouter,
    createWebHistory,
    type RouteRecordRaw,
} from "vue-router";
import { useUserStore } from "@/stores/user";

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
                path: "upload",
                name: "UploadCenter",
                component: () => import("@/views/upload/index.vue"),
                meta: { title: "上传中心", icon: "Upload" },
            },
            {
                path: "tasks",
                name: "Tasks",
                component: () => import("@/views/task/index.vue"),
                meta: { title: "任务列表", icon: "List" },
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
                component: () => import("@/views/transaction-placeholder/index.vue"),
                meta: { title: "动账上传中心", icon: "Upload" },
            },
            {
                path: "transaction-tasks",
                name: "TransactionTasks",
                component: () => import("@/views/transaction-placeholder/index.vue"),
                meta: { title: "动账任务列表", icon: "List" },
            },
            {
                path: "transaction-summaries",
                name: "TransactionSummaries",
                component: () => import("@/views/transaction-placeholder/index.vue"),
                meta: { title: "动账汇总明细", icon: "Document" },
            },
            {
                path: "transaction-summary-report",
                name: "TransactionSummaryReport",
                component: () => import("@/views/transaction-placeholder/index.vue"),
                meta: { title: "动账汇总报表", icon: "DataAnalysis" },
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
    const rawToken = localStorage.getItem("token");
    const token = rawToken && rawToken !== "undefined" ? rawToken : null;

    let userInfo: any = null;
    try {
        const raw = localStorage.getItem("userInfo");
        userInfo = raw && raw !== "undefined" ? JSON.parse(raw) : null;
    } catch {
        userInfo = null;
    }

    // Set page title
    const title = to.meta.title ? `${to.meta.title} - FinEngine 财务运营平台` : "FinEngine 财务运营平台";
    document.title = title as string;

    // Public routes (login page)
    if (to.meta.requiresAuth === false) {
        if (token) {
            // Already logged in, redirect to dashboard
            next("/dashboard");
        } else {
            next();
        }
        return;
    }

    // Protected routes - check authentication
    if (!token) {
        next("/login");
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
