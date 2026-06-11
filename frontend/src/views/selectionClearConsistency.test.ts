import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const pages = [
    {
        label: "对账清单汇总页",
        file: new URL("./reconciliation-checklist/summary.vue", import.meta.url),
        clearFn: "clearSelectedRows",
        tableRef: "summaryTableRef",
    },
    {
        label: "商家对账汇总页",
        file: new URL("./merchant-reconciliation/summary.vue", import.meta.url),
        clearFn: "clearSelectedRows",
        tableRef: "summaryTableRef",
    },
    {
        label: "动账汇总页",
        file: new URL("./summary/index.vue", import.meta.url),
        clearFn: "clearSelectedRows",
        tableRef: "summaryTableRef",
    },
];

test("cross-page selection pages clear both data state and table checkbox state", async () => {
    for (const page of pages) {
        const source = await readFile(page.file, "utf8");
        const clearFnBlock = extractFunctionBlock(source, page.clearFn);

        assert.match(
            source,
            new RegExp(`ref="${page.tableRef}"`),
            `${page.label} should bind ${page.tableRef} on the table`,
        );
        assert.match(
            clearFnBlock,
            /new Map\(\)/,
            `${page.label} should clear the persisted selected map`,
        );
        assert.match(
            clearFnBlock,
            new RegExp(`${page.tableRef}\\.value\\?\\.clearSelection\\(\\)|${page.tableRef}\\.value\\.clearSelection\\(\\)`),
            `${page.label} should clear the table checkbox UI state`,
        );
    }
});

function extractFunctionBlock(source: string, functionName: string) {
    const marker = `function ${functionName}`;
    const markerIndex = source.indexOf(marker);
    assert.notEqual(markerIndex, -1, `Expected to find ${functionName}`);

    const blockStart = source.indexOf("{", markerIndex);
    assert.notEqual(blockStart, -1, `Expected ${functionName} to open a block`);

    let depth = 0;
    for (let index = blockStart; index < source.length; index += 1) {
        const char = source[index];
        if (char === "{") depth += 1;
        if (char === "}") depth -= 1;
        if (depth === 0) return source.slice(blockStart + 1, index);
    }

    assert.fail(`Expected ${functionName} block to close`);
}
