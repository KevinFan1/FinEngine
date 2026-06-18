import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { filterSidebarMenuByRole, sidebarMenuItems } from "./sidebarMenu.ts";

test("flattens common functions above the sidebar divider", () => {
    const dividerIndex = sidebarMenuItems.findIndex(
        (item) => item.type === "divider",
    );
    const primaryMenus = sidebarMenuItems.slice(0, dividerIndex);
    const dividerMenu = sidebarMenuItems[dividerIndex];

    assert.equal(dividerMenu.type, "divider");
    assert.deepEqual(
        primaryMenus.map((item) => item.title),
        [
            "首页",
            "底表上传",
            "任务中心",
            "商家总表",
            "商家明细",
            "余额明细",
            "发票修改",
            "商家修改",
            "下载中心",
        ],
    );
    assert.equal(primaryMenus[0]?.path, "/dashboard");
    assert.equal(primaryMenus[1]?.path, "/reconciliation-checklist/upload");
    assert.ok(
        sidebarMenuItems.some(
            (item) =>
                item.type !== "divider" &&
                item.path === "/reconciliation-checklist/invoice-edits" &&
                item.title === "发票修改",
        ),
    );
    assert.ok(
        sidebarMenuItems.some(
            (item) =>
                item.type !== "divider" &&
                item.path === "/reconciliation-checklist/merchant-edits" &&
                item.title === "商家修改",
        ),
    );
    assert.equal(
        countMenuItemsByPath(sidebarMenuItems, "/downloads"),
        1,
        "download center should only appear once in the flattened primary area",
    );
    assert.equal(
        sidebarMenuItems.some((item) => item.title === "常用功能"),
        false,
    );

    assert.ok(
        sidebarMenuItems.some((item) => item.title === "动账核算"),
        "legacy accounting menu should remain available as a top-level group",
    );
    assert.ok(
        sidebarMenuItems.some((item) => item.title === "BIC核算"),
        "BIC menu should remain available as a top-level group",
    );
});

test("promotes accounting upload center to a top-level menu item", () => {
    assert.equal(
        sidebarMenuItems.some((item) => item.title === "工作台"),
        false,
    );
    assert.ok(
        sidebarMenuItems.some(
            (item) =>
                item.path === "/upload" &&
                item.title === "核算上传中心" &&
                !item.children?.length,
        ),
    );
    const uploadIndex = sidebarMenuItems.findIndex(
        (item) => item.path === "/upload",
    );
    const shopsIndex = sidebarMenuItems.findIndex(
        (item) => item.path === "/shops",
    );
    assert.ok(uploadIndex >= 0);
    assert.equal(shopsIndex, uploadIndex + 1);
});

test("keeps user management under system management and only visible for admin roles", () => {
    const orgAdminMenus = filterSidebarMenuByRole(
        sidebarMenuItems,
        "org_admin",
    );
    const regularMenus = filterSidebarMenuByRole(sidebarMenuItems, "operator");
    const orgSystemManagement = orgAdminMenus.find(
        (item) => item.type !== "divider" && item.title === "系统管理",
    );
    const regularSystemManagement = regularMenus.find(
        (item) => item.type !== "divider" && item.title === "系统管理",
    );

    assert.ok(
        orgSystemManagement &&
            "children" in orgSystemManagement &&
            orgSystemManagement.children?.some(
                (item) => item.title === "用户管理",
            ),
    );
    assert.equal(
        regularMenus.some((item) => item.title === "用户管理"),
        false,
    );
    assert.equal(
        Boolean(
            regularSystemManagement &&
            "children" in regularSystemManagement &&
            regularSystemManagement.children?.some(
                (item) => item.title === "用户管理",
            ),
        ),
        false,
    );
});

test("limits organization members to the designated accounting and shop menus", () => {
    const memberMenus = filterSidebarMenuByRole(sidebarMenuItems, "member");

    assert.deepEqual(
        memberMenus
            .filter((item) => item.type !== "divider")
            .map((item) => item.title),
        [
            "核算上传中心",
            "下载中心",
            "店铺管理",
            "动账核算",
            "动账资金核算",
            "BIC核算",
        ],
    );
    assert.equal(
        memberMenus.some(
            (item) => item.type !== "divider" && item.title === "规则配置",
        ),
        false,
    );
    assert.equal(
        memberMenus.some(
            (item) => item.type !== "divider" && item.title === "系统管理",
        ),
        false,
    );
});

test("keeps download center visible for external organization members", () => {
    const memberMenus = filterSidebarMenuByRole(
        sidebarMenuItems,
        "member",
        false,
    );

    assert.deepEqual(
        memberMenus
            .filter((item) => item.type !== "divider")
            .map((item) => item.title),
        ["下载中心"],
    );
});

test("keeps sidebar menu to two levels", () => {
    assert.equal(hasNestedChildren(sidebarMenuItems), false);
});

test("keeps leaf menu titles aligned with route tab titles", () => {
    const routerSource = fs.readFileSync(
        new URL("../router/index.ts", import.meta.url),
        "utf8",
    );
    const routeTitleMap = extractRouteTitleMap(routerSource);

    for (const item of flattenLeafMenuItems(sidebarMenuItems)) {
        const routeTitle = routeTitleMap.get(item.path);
        if (!routeTitle) continue;
        assert.equal(
            routeTitle,
            item.title,
            `route title mismatch for ${item.path}`,
        );
    }
});

function countMenuItemsByPath(
    items: Array<{ path: string; children?: unknown[] }>,
    path: string,
): number {
    return items.reduce((count, item) => {
        const childCount = item.children
            ? countMenuItemsByPath(
                  item.children as Array<{
                      path: string;
                      children?: unknown[];
                  }>,
                  path,
              )
            : 0;
        return count + (item.path === path ? 1 : 0) + childCount;
    }, 0);
}

function hasNestedChildren(items: Array<{ children?: unknown[] }>): boolean {
    return items.some((item) =>
        Boolean(
            item.children?.some((child) =>
                Boolean((child as { children?: unknown[] }).children?.length),
            ),
        ),
    );
}

function flattenLeafMenuItems(
    items: Array<{
        type?: string;
        path: string;
        title?: string;
        children?: unknown[];
    }>,
): Array<{ path: string; title: string }> {
    return items.flatMap((item) => {
        if (item.type === "divider") return [];
        if (item.children?.length) {
            return flattenLeafMenuItems(
                item.children as Array<{
                    type?: string;
                    path: string;
                    title?: string;
                    children?: unknown[];
                }>,
            );
        }
        return item.title ? [{ path: item.path, title: item.title }] : [];
    });
}

function extractRouteTitleMap(source: string): Map<string, string> {
    const map = new Map<string, string>();
    const lines = source.split("\n");
    let currentPath: string | null = null;

    for (const line of lines) {
        const pathMatch = line.match(/path:\s*"([^"]+)"/);
        if (pathMatch) {
            const rawPath = pathMatch[1];
            currentPath = rawPath.startsWith("/") ? rawPath : `/${rawPath}`;
        }

        const titleMatch = line.match(/title:\s*"([^"]+)"/);
        if (currentPath && titleMatch) {
            map.set(currentPath, titleMatch[1]);
            currentPath = null;
        }
    }

    return map;
}
