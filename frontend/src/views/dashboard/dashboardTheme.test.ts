import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const dashboardFile = new URL("./index.vue", import.meta.url);
const themeFile = new URL("../../styles/theme.css", import.meta.url);

test("dashboard uses restrained finance color tokens", async () => {
    const source = await readFile(dashboardFile, "utf8");

    assert.match(source, /--dashboard-primary:\s*#2563EB;/);
    assert.match(source, /--dashboard-bg:\s*#F8FAFC;/);
    assert.match(source, /--dashboard-surface:\s*#FFFFFF;/);
    assert.match(source, /--dashboard-border:\s*#E2E8F0;/);
    assert.match(source, /--dashboard-text:\s*#1E293B;/);
    assert.match(source, /--dashboard-muted:\s*#64748B;/);
    assert.equal(source.includes("--metric-accent"), false);
    assert.equal(source.includes("radial-gradient"), false);
    assert.equal(source.includes("linear-gradient(135deg"), false);
});

test("dashboard reserves semantic colors for recent task status only", async () => {
    const source = await readFile(dashboardFile, "utf8");

    assert.match(source, /--dashboard-success:\s*#10B981;/);
    assert.match(source, /--dashboard-warning:\s*#F59E0B;/);
    assert.equal(countMatches(source, /var\(--dashboard-success\)/g), 1);
    assert.equal(countMatches(source, /var\(--dashboard-warning\)/g), 1);
    assert.equal(countMatches(source, /#F59E0B|#f59e0b|#10B981|#10b981/g), 2);
});

test("global page background is flat finance gray", async () => {
    const source = await readFile(themeFile, "utf8");

    assert.match(source, /--page-bg-gradient:\s*#F8FAFC;/);
});

function countMatches(source: string, pattern: RegExp) {
    return source.match(pattern)?.length ?? 0;
}
