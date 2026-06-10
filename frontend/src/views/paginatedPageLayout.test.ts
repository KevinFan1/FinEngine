import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const workspaceRoot = new URL("../", import.meta.url);
const globalStylesFile = new URL("../styles/global.scss", import.meta.url);

const paginatedPageFiles = [
    "views/audit/index.vue",
    "views/bic-accounting/details.vue",
    "views/bic-accounting/source.vue",
    "views/bic-accounting/tasks.vue",
    "views/category-dict/index.vue",
    "views/download/index.vue",
    "views/file-specs/index.vue",
    "views/merchant-reconciliation/bank-flows.vue",
    "views/merchant-reconciliation/payments.vue",
    "views/merchant-reconciliation/purchases.vue",
    "views/merchant-reconciliation/summary.vue",
    "views/merchant-reconciliation/tasks.vue",
    "views/merchant-reconciliation/unmatched.vue",
    "views/organization/index.vue",
    "views/reconciliation-checklist/summary.vue",
    "views/reconciliation-checklist/tasks.vue",
    "views/shop/index.vue",
    "views/summary/index.vue",
    "views/summary-report/index.vue",
    "views/task/index.vue",
    "views/transaction-accounting/details.vue",
    "views/transaction-accounting/tasks.vue",
    "views/user/index.vue",
];

test("shared flow utility keeps paginated pages in natural document scroll", async () => {
    const source = await readFile(globalStylesFile, "utf8");
    const flowBlock = nestedBlock(source, ".page-container--flow");

    assert.match(flowBlock, /display:\s*block;/);
    assert.match(flowBlock, /height:\s*auto;/);
    assert.match(flowBlock, /min-height:\s*100%;/);
});

test("paginated pages opt into the natural page scroll container", async () => {
    for (const relativePath of paginatedPageFiles) {
        const file = new URL(relativePath, workspaceRoot);
        const source = await readFile(file, "utf8");
        assert.match(
            source,
            /<div class="page-container[^"]*page-container--flow[^"]*">/,
            `${relativePath} should opt into page-container--flow`,
        );
    }
});

test("checklist summary stops using fixed-height flex compression for long tables", async () => {
    const source = await readFile(
        new URL("views/reconciliation-checklist/summary.vue", workspaceRoot),
        "utf8",
    );
    const checklistPageBlock = nestedBlock(source, ".checklist-page");
    const filterCardBlock = nestedBlock(source, ".checklist-filter-card");

    assert.match(checklistPageBlock, /display:\s*block;/);
    assert.match(checklistPageBlock, /height:\s*auto;/);
    assert.match(checklistPageBlock, /min-height:\s*100%;/);
    assert.match(filterCardBlock, /margin-bottom:\s*14px;/);
});

function nestedBlock(source: string, marker: string) {
    const markerIndex = source.indexOf(marker);
    assert.notEqual(markerIndex, -1, `Expected to find ${marker}`);

    const blockStart = source.indexOf("{", markerIndex);
    assert.notEqual(blockStart, -1, `Expected ${marker} to open a block`);

    let depth = 0;
    for (let index = blockStart; index < source.length; index += 1) {
        const char = source[index];
        if (char === "{") depth += 1;
        if (char === "}") depth -= 1;
        if (depth === 0) return source.slice(blockStart + 1, index);
    }

    assert.fail(`Expected ${marker} block to close`);
}
