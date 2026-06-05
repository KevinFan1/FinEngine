import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const dashboardFile = new URL("./index.vue", import.meta.url);

test("dashboard page opts out of fixed-height flex compression", async () => {
    const source = await readFile(dashboardFile, "utf8");
    const dashboardPageBlock = ruleBlock(source, ".dashboard-page");

    assert.match(dashboardPageBlock, /display:\s*block;/);
    assert.match(dashboardPageBlock, /height:\s*auto;/);
    assert.match(dashboardPageBlock, /min-height:\s*100%;/);
});

test("dashboard hero stacks before tablet-width copy collides with metadata", async () => {
    const source = await readFile(dashboardFile, "utf8");
    const tabletMedia = mediaBlock(source, 1120);
    const heroBlock = ruleBlock(tabletMedia, ".dashboard-hero");
    const heroMetaBlock = ruleBlock(tabletMedia, ".hero-meta");

    assert.match(heroBlock, /flex-direction:\s*column;/);
    assert.match(heroBlock, /align-items:\s*flex-start;/);
    assert.match(heroBlock, /overflow:\s*visible;/);
    assert.match(heroMetaBlock, /justify-content:\s*flex-start;/);
    assert.match(heroMetaBlock, /width:\s*100%;/);
});

function mediaBlock(source: string, maxWidth: number) {
    return nestedBlock(source, `@media (max-width: ${maxWidth}px)`);
}

function ruleBlock(source: string, selector: string) {
    return nestedBlock(source, selector);
}

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
