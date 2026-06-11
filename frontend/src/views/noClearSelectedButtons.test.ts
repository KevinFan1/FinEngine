import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const pages = [
    "views/reconciliation-checklist/summary.vue",
    "views/merchant-reconciliation/summary.vue",
    "views/summary/index.vue",
    "views/summary-report/index.vue",
    "views/bic-accounting/source.vue",
    "views/bic-accounting/details.vue",
    "views/transaction-accounting/details.vue",
    "views/upload/index.vue",
];

const workspaceRoot = new URL("../", import.meta.url);

test("selection pages no longer render dedicated clear-selected buttons", async () => {
    for (const relativePath of pages) {
        const source = await readFile(new URL(relativePath, workspaceRoot), "utf8");
        assert.doesNotMatch(
            source,
            />\s*清空选中(?:\s*\{\{[\s\S]*?\}\})?\s*<\/el-button>/,
            `${relativePath} should not render a 清空选中 button`,
        );
    }
});
