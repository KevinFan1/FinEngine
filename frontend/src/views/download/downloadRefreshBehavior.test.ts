import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sourceFile = new URL("./index.vue", import.meta.url);

test("download center refreshes when the cached page is re-activated", async () => {
    const source = await readFile(sourceFile, "utf8");

    assert.match(
        source,
        /onActivated\(\(\)\s*=>\s*\{\s*fetchData\(\);/s,
        "下载中心从 keep-alive 缓存切回时应重新请求列表接口",
    );
    assert.match(
        source,
        /usePageRefresh\(fetchData\)/,
        "下载中心应注册页面级刷新能力，供全局入口复用",
    );
});
