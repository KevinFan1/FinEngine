import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const summaryFile = new URL("./summary.vue", import.meta.url);

test("checklist summary clearSelectedRows clears the visible table selection state", async () => {
    const source = await readFile(summaryFile, "utf8");

    assert.doesNotMatch(
        source,
        />\s*清空选中\s*<\/el-button>/,
        "对账清单汇总页不再展示单独的清空选中按钮",
    );

    assert.match(
        source,
        /ref="summaryTableRef"/,
        "对账清单汇总页应给当前表格绑定 summaryTableRef，方便统一清空勾选状态",
    );

    const clearSelectedRowsBlock = extractFunctionBlock(source, "clearSelectedRows");

    assert.match(
        clearSelectedRowsBlock,
        /selectedRowMap\.value\s*=\s*new Map\(\)/,
        "clearSelectedRows 应先清空业务侧已选映射",
    );
    assert.match(
        clearSelectedRowsBlock,
        /summaryTableRef\.value\?\.clearSelection\(\)/,
        "clearSelectedRows 应同步清空表格组件内部的勾选状态",
    );
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
