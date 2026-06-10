import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const globalStylesFile = new URL("./global.scss", import.meta.url);

test("shared pagination keeps controls scrollable and resists flex compression", async () => {
    const source = await readFile(globalStylesFile, "utf8");
    const pageContainerBlock = nestedBlock(source, ".page-container");
    const paginationBlock = nestedBlock(pageContainerBlock, ".pagination-area");
    const elPaginationBlock = nestedBlock(paginationBlock, ".el-pagination");

    assert.match(paginationBlock, /min-width:\s*0;/);
    assert.match(paginationBlock, /flex-shrink:\s*0;/);
    assert.match(paginationBlock, /overflow-x:\s*auto;/);
    assert.match(paginationBlock, /overflow-y:\s*hidden;/);
    assert.match(elPaginationBlock, /flex-shrink:\s*0;/);
    assert.match(elPaginationBlock, /min-width:\s*max-content;/);
});

test("mobile shared pagination avoids centering wide controls into clipped overflow", async () => {
    const source = await readFile(globalStylesFile, "utf8");
    const pageContainerBlock = nestedBlock(source, ".page-container");
    const paginationBlock = nestedBlock(pageContainerBlock, ".pagination-area");

    assert.match(paginationBlock, /overflow-x:\s*auto;/);
    assert.doesNotMatch(source, /@media\s*\(max-width:\s*768px\)[\s\S]*\.pagination-area\s*{[\s\S]*justify-content:\s*center;/);
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
