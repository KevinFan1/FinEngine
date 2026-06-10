import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./index.vue", import.meta.url), "utf8");

test("labels the export task title column as module in the download center list", () => {
    assert.match(
        source,
        /<el-table-column prop="title" label="模块" min-width="240" show-overflow-tooltip \/>/,
    );
    assert.doesNotMatch(
        source,
        /<el-table-column prop="title" label="名称"/,
    );
    assert.match(source, /<el-table-column prop="module" label="所属模块" width="150">/);
});
