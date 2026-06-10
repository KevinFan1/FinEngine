import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./exportJobs.ts", import.meta.url), "utf8");

test("export submission uses a lightweight success message instead of a confirm dialog", () => {
    assert.match(source, /ElMessage\.success/);
    assert.doesNotMatch(source, /ElMessageBox\.confirm/);
    assert.doesNotMatch(source, /confirmButtonText:\s*"去下载中心"/);
});
