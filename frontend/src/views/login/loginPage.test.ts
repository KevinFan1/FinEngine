import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./index.vue", import.meta.url), "utf8");

test("login page keeps API/login errors inside the inline alert instead of duplicating toast errors", () => {
    assert.match(source, /<el-alert[\s\S]*v-if="loginError"/);
    assert.doesNotMatch(source, /ElMessage\.error\(message\)/);
    assert.doesNotMatch(source, /if \(!isApiMessageShown\(error\)\) \{\s*ElMessage\.error\(message\)/);
});

test("login page does not locally pre-judge captcha correctness before submitting", () => {
    assert.doesNotMatch(source, /captchaExpectedCode/);
    assert.doesNotMatch(source, /extractCaptchaCode/);
    assert.doesNotMatch(source, /验证码不正确/);
});

test("login page guards against duplicate submissions while a login request is in flight", () => {
    assert.match(source, /if \(loading\.value\) return;/);
});
