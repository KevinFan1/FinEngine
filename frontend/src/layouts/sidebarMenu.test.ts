import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { filterSidebarMenuByRole, sidebarMenuItems } from "./sidebarMenu.ts";

test("puts daily reconciliation upload first without removing other modules", () => {
    const [dailyMenu, moreMenu] = sidebarMenuItems;

    assert.equal(dailyMenu.title, "常用功能");
    assert.deepEqual(
        dailyMenu.children?.map((item) => item.title),
        [
            "对账清单上传",
            "对账清单任务",
            "对账清单汇总",
            "下载中心",
            "店铺管理",
            "用户管理",
        ],
    );
    assert.equal(dailyMenu.children?.[0]?.path, "/reconciliation-checklist/upload");
    assert.equal(
        countMenuItemsByPath(sidebarMenuItems, "/downloads"),
        1,
        "download center should only appear in daily work",
    );

    assert.equal(moreMenu.title, "更多功能");
    assert.ok(
        moreMenu.children?.some((item) => item.title === "动账核算"),
        "legacy accounting menu should remain available under more features",
    );
    assert.ok(
        moreMenu.children?.some((item) => item.title === "BIC核算"),
        "BIC menu should remain available under more features",
    );
});

test("keeps user management visible only for admin roles after promotion", () => {
    const orgAdminDailyMenu = filterSidebarMenuByRole(
        sidebarMenuItems,
        "org_admin",
    )[0];
    const regularDailyMenu = filterSidebarMenuByRole(
        sidebarMenuItems,
        "operator",
    )[0];

    assert.ok(
        orgAdminDailyMenu.children?.some((item) => item.title === "用户管理"),
    );
    assert.equal(
        regularDailyMenu.children?.some((item) => item.title === "用户管理"),
        false,
    );
});

test("indents third-level sidebar items deeper than second-level groups", async () => {
    const layoutSource = await readFile(
        new URL("./DefaultLayout.vue", import.meta.url),
        "utf8",
    );

    const secondLevelIndent = extractLeftMargin(
        layoutSource,
        ":deep(.el-sub-menu .el-menu-item)",
    );
    const thirdLevelIndent = extractLeftMargin(
        layoutSource,
        ":deep(.el-sub-menu .el-sub-menu .el-menu-item)",
    );

    assert.ok(
        thirdLevelIndent > secondLevelIndent,
        "third-level menu items should be visually nested under their parent group",
    );
});

function extractLeftMargin(source: string, selector: string) {
    const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const rule = source.match(new RegExp(`${escapedSelector}\\s*\\{([\\s\\S]*?)\\n\\s*\\}`));
    assert.ok(rule, `${selector} rule should exist`);

    const margin = rule[1].match(/margin:\s*\d+px\s+\d+px\s+\d+px\s+(\d+)px;/);
    assert.ok(margin, `${selector} should use four-value pixel margin`);
    return Number(margin[1]);
}

function countMenuItemsByPath(items: Array<{ path: string; children?: unknown[] }>, path: string): number {
    return items.reduce((count, item) => {
        const childCount = item.children
            ? countMenuItemsByPath(
                  item.children as Array<{ path: string; children?: unknown[] }>,
                  path,
              )
            : 0;
        return count + (item.path === path ? 1 : 0) + childCount;
    }, 0);
}
