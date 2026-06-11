import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sourceFile = new URL("./DouyinDongzhangDetailDrawer.vue", import.meta.url);

test("detail drawer reloads from a single open-or-context watcher", async () => {
    const source = await readFile(sourceFile, "utf8");

    assert.match(
        source,
        /watch\(\s*\[\s*\(\) => props\.modelValue,\s*detailContextKey\s*\],/s,
    );
    assert.match(
        source,
        /if \(pagination\.page !== 1\) {\s*pagination\.page = 1;\s*return;\s*}\s*void fetchData\(\);/s,
    );
    assert.doesNotMatch(source, /watch\(\s*\(\) => props\.context,\s*/s);
});

test("detail drawer deduplicates identical in-flight detail requests", async () => {
    const source = await readFile(sourceFile, "utf8");

    assert.match(source, /const inFlightFetchRequestKey = ref<string \| null>\(null\);/);
    assert.match(source, /let inFlightFetchPromise: Promise<void> \| null = null;/);
    assert.match(
        source,
        /if \(inFlightFetchRequestKey\.value === requestKey && inFlightFetchPromise\) {\s*return inFlightFetchPromise;\s*}/s,
    );
    assert.match(source, /let latestFetchSequence = 0;/);
});
