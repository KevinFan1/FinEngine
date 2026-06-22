import type { Component } from "vue";

export type SidebarMenuIconName =
    | "Collection"
    | "CollectionTag"
    | "DataAnalysis"
    | "Document"
    | "Download"
    | "House"
    | "List"
    | "Money"
    | "OfficeBuilding"
    | "Setting"
    | "Shop"
    | "Upload"
    | "User"
    | "Wallet"
    | "Warning";

export interface SidebarMenuLinkItem {
    type?: "item";
    path: string;
    title: string;
    icon: SidebarMenuIconName;
    roles?: string[];
    internalOnly?: boolean;
    children?: SidebarMenuLinkItem[];
}

export interface SidebarMenuDividerItem {
    type: "divider";
    path: string;
}

export type SidebarMenuItem = SidebarMenuLinkItem | SidebarMenuDividerItem;

export interface ResolvedSidebarMenuItem extends Omit<
    SidebarMenuLinkItem,
    "icon" | "children"
> {
    icon: Component;
    children?: ResolvedSidebarMenuItem[];
}

const merchantReconciliationMenuEnabled = false;
const memberVisibleTopLevelPaths = new Set([
    "/upload",
    "/downloads",
    "/shops",
    "/order-accounting",
    "/transaction-accounting",
    "/bic-accounting",
]);

export const sidebarMenuItems: SidebarMenuItem[] = [
    {
        path: "/dashboard",
        title: "首页",
        icon: "House",
    },
    {
        path: "/reconciliation-checklist/upload",
        title: "底表上传",
        icon: "Upload",
    },
    {
        path: "/reconciliation-checklist/tasks",
        title: "任务中心",
        icon: "List",
    },
    {
        path: "/reconciliation-checklist/summary",
        title: "商家总表",
        icon: "DataAnalysis",
    },
    {
        path: "/reconciliation-checklist/merchant-details",
        title: "商家明细",
        icon: "Document",
    },
    {
        path: "/reconciliation-checklist/payable-balance-details",
        title: "余额明细",
        icon: "Document",
    },
    {
        path: "/reconciliation-checklist/invoice-edits",
        title: "发票修改",
        icon: "Document",
    },
    {
        path: "/reconciliation-checklist/merchant-edits",
        title: "商家修改",
        icon: "Document",
    },
    {
        path: "/downloads",
        title: "下载中心",
        icon: "Download",
    },
    {
        type: "divider",
        path: "/sidebar-primary-divider",
    },
    {
        path: "/upload",
        title: "核算上传中心",
        icon: "Upload",
        internalOnly: true,
    },
    {
        path: "/shops",
        title: "店铺管理",
        icon: "Shop",
        internalOnly: true,
    },
    {
        path: "/order-accounting",
        title: "动账核算",
        icon: "Money",
        internalOnly: true,
        children: [
            { path: "/tasks", title: "核算任务", icon: "List" },
            {
                path: "/summaries",
                title: "汇总明细",
                icon: "Document",
            },
            {
                path: "/summary-report",
                title: "汇总报表",
                icon: "DataAnalysis",
            },
        ],
    },
    {
        path: "/transaction-accounting",
        title: "动账资金核算",
        icon: "Wallet",
        internalOnly: true,
        children: [
            {
                path: "/transaction-tasks",
                title: "资金任务",
                icon: "List",
            },
            {
                path: "/transaction-summaries",
                title: "科目明细",
                icon: "Document",
            },
            {
                path: "/transaction-summary-report",
                title: "年度报表",
                icon: "DataAnalysis",
            },
        ],
    },
    {
        path: "/bic-accounting",
        title: "BIC核算",
        icon: "Wallet",
        internalOnly: true,
        children: [
            {
                path: "/bic-tasks",
                title: "BIC任务",
                icon: "List",
            },
            {
                path: "/bic-details",
                title: "BIC源明细",
                icon: "Document",
            },
            {
                path: "/bic-summary",
                title: "BIC汇总",
                icon: "Document",
            },
        ],
    },
    ...(merchantReconciliationMenuEnabled
        ? [
              {
                  path: "/merchant-reconciliation",
                  title: "商家对账",
                  icon: "Money" as const,
                  children: [
                      {
                          path: "/merchant-reconciliation/upload",
                          title: "上传中心",
                          icon: "Upload" as const,
                      },
                      {
                          path: "/merchant-reconciliation/tasks",
                          title: "对账任务",
                          icon: "List" as const,
                      },
                      {
                          path: "/merchant-reconciliation/unmatched",
                          title: "未匹配维护",
                          icon: "Warning" as const,
                      },
                      {
                          path: "/merchant-reconciliation/payments",
                          title: "货款明细",
                          icon: "Document" as const,
                      },
                      {
                          path: "/merchant-reconciliation/purchases",
                          title: "采购明细",
                          icon: "Document" as const,
                      },
                      {
                          path: "/merchant-reconciliation/bank-flows",
                          title: "银行流水",
                          icon: "Wallet" as const,
                      },
                      {
                          path: "/merchant-reconciliation/summary",
                          title: "汇总数据",
                          icon: "DataAnalysis" as const,
                      },
                      {
                          path: "/merchant-reconciliation/net-rates",
                          title: "净额比例",
                          icon: "Setting" as const,
                      },
                  ],
              },
          ]
        : []),
    {
        path: "/rule-config",
        title: "规则配置",
        icon: "Setting",
        children: [
            {
                path: "/category-dicts",
                title: "动账重分类字典",
                icon: "Collection",
                roles: ["superadmin"],
            },
            {
                path: "/file-specs",
                title: "文件规格配置",
                icon: "Setting",
                roles: ["superadmin"],
            },
            {
                path: "/transaction-major-categories",
                title: "资金大分类",
                icon: "CollectionTag",
                roles: ["superadmin"],
            },
            {
                path: "/transaction-rules",
                title: "资金重分类规则",
                icon: "Setting",
                roles: ["superadmin"],
            },
        ],
    },
    {
        path: "/system-management",
        title: "系统管理",
        icon: "OfficeBuilding",
        children: [
            {
                path: "/organizations",
                title: "组织管理",
                icon: "OfficeBuilding",
                roles: ["superadmin"],
            },
            {
                path: "/audit-logs",
                title: "操作日志",
                icon: "Document",
                roles: ["superadmin", "org_admin"],
            },
            {
                path: "/users",
                title: "用户管理",
                icon: "User",
                roles: ["superadmin", "org_admin"],
            },
        ],
    },
];

export function filterSidebarMenuByRole(
    items: SidebarMenuItem[],
    userRole: string,
    isInternalOrg = true,
): SidebarMenuItem[] {
    const isTopLevelMenu = items === sidebarMenuItems;
    return items.flatMap((item) => {
        if (item.type === "divider") {
            if (userRole === "member" && isTopLevelMenu) return [];
            return [item];
        }
        if (item.roles && !item.roles.includes(userRole)) return [];
        if (item.internalOnly && !isInternalOrg) return [];
        if (
            userRole === "member" &&
            isTopLevelMenu &&
            !memberVisibleTopLevelPaths.has(item.path)
        ) {
            return [];
        }
        if (!item.children?.length) return [item];

        const children = filterSidebarMenuByRole(
            item.children,
            userRole,
            isInternalOrg,
        );
        return children.length ? [{ ...item, children }] : [];
    });
}
