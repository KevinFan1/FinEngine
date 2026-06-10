import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./index.ts", import.meta.url), "utf8");

test("auth public requests do not show global toast errors from the API interceptor", () => {
    assert.match(source, /isAuthPublicRequest\(config\.url\)/);
    assert.match(source, /const isPublicRequest = isAuthPublicRequest\(response\.config\.url\)/);
    assert.match(source, /else if \(!isPublicRequest\) \{\s*ElMessage\.error\(message\);/);
    assert.match(source, /const isPublicRequest = isAuthPublicRequest\(error\.config\?\.url\)/);
    assert.match(source, /else if \(!isPublicRequest\) \{\s*ElMessage\.error\(message\);/);
});
