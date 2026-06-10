import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const uploadSource = fs.readFileSync(new URL("./upload.vue", import.meta.url), "utf8");

test("bottom table upload downloads source template directly", () => {
    assert.match(uploadSource, /@click="handleTemplateDownload"/);
    assert.match(uploadSource, /downloadChecklistTemplate\("source"\)/);
    assert.doesNotMatch(uploadSource, /templateDialogVisible/);
    assert.doesNotMatch(uploadSource, /发票更新模板/);
    assert.doesNotMatch(uploadSource, /商家更新模板/);
    assert.doesNotMatch(uploadSource, /选择模板类型/);
});
