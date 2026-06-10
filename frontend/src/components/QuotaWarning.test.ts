import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./QuotaWarning.vue", import.meta.url), "utf8");

test("quota chip stays compact in the top header", () => {
    assert.match(source, /\.quota-chip\s*{[\s\S]*?height:\s*32px;/);
    assert.doesNotMatch(source, /\.quota-chip\s*{[\s\S]*?min-height:\s*38px;/);
    assert.match(source, /grid-template-rows:\s*1fr 2px/);
    assert.match(source, /\.quota-chip-bar\s*{[\s\S]*?height:\s*2px;/);
});
