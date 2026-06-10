import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./DefaultLayout.vue", import.meta.url), "utf8");

test("keeps a dedicated download center entry in the top-right header", () => {
    assert.match(source, /class="download-center-entry"/);
    assert.match(source, /download-center-popover/);
    assert.match(source, /最近导出任务/);
    assert.match(source, /<span class="download-center-panel__eyebrow">下载中心<\/span>/);
    assert.match(source, /查看全部/);
    assert.match(source, /openDownloadCenterEntry/);
    assert.match(source, /navigateToDownloadCenter/);
});

test("removes the top-right global refresh button", () => {
    const headerRightBlock = source.match(
        /<div class="header-right">[\s\S]*?<\/div>\s*<\/header>/,
    )?.[0];

    assert.ok(headerRightBlock, "header-right block should exist");
    assert.doesNotMatch(headerRightBlock || "", /class="refresh-btn"/);
    assert.doesNotMatch(
        headerRightBlock || "",
        /isRefreshingCurrentPage/,
    );
});

test("counts queued and running jobs for the header activity badge", () => {
    assert.match(source, /headerActiveJobCount/);
    assert.match(source, /job\.status === "queued" \|\| job\.status === "running"/);
    assert.match(source, /个任务处理中/);
});

test("allows direct download from the header panel", () => {
    assert.match(source, /downloadHeaderJob/);
    assert.match(source, /downloadExportJobFile/);
    assert.match(source, /下载中/);
});

test("header download panel fetches only after opening and offers manual refresh", () => {
    assert.match(source, /@show="handleDownloadCenterShow"/);
    assert.doesNotMatch(source, /onMounted\(\(\) => \{\s*startDownloadJobPolling\(\)/);
    assert.doesNotMatch(source, /setInterval\(/);
    assert.match(source, /fetchHeaderDownloadJobs\(\)/);
    assert.match(source, /mine_only:\s*true/);
    assert.match(source, /download-center-panel__refresh/);
    assert.match(source, /RefreshRight/);
});

test("header panel keeps only file name, status, and download action for each job", () => {
    assert.match(source, /downloadJobFilenameLabel/);
    assert.match(source, /download-center-panel__column-title">\s*文件名称/);
    assert.match(source, /download-center-panel__column-title">\s*状态/);
    assert.match(source, /download-center-panel__column-title">\s*按钮/);
    assert.match(source, /download-center-job__filename/);
    assert.match(source, /download-center-job__status/);
    assert.match(source, /download-center-job__action-cell/);
    assert.doesNotMatch(source, /download-center-job__label/);
    assert.doesNotMatch(source, /download-center-job__meta/);
    assert.doesNotMatch(source, /download-center-job__icon/);
    assert.match(source, /downloadCenterPopoverVisible/);
});

test("header download panel uses polished compact table styling", () => {
    assert.match(source, /class="download-center-panel__body"/);
    assert.match(source, /class="download-center-job__status-dot"/);
    assert.match(source, /download-center-panel__link-icon/);
    assert.match(source, /:global\(\.download-center-popover\)/);
    assert.match(source, /:global\(\.download-center-popover \.download-center-panel__body\)/);
    assert.match(source, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+32px\s+64px/);
    assert.match(source, /box-shadow:\s*0 24px 54px rgba\(15,\s*23,\s*42,\s*0\.16\)/);
    assert.match(source, /backdrop-filter:\s*blur\(14px\)/);
});

test("header download panel prioritizes long file names with color-only status", () => {
    assert.match(source, /:width="520"/);
    assert.match(source, /aria-label="\`状态：\$\{downloadJobStatusLabel\(job\.status\)\}\`"/);
    assert.doesNotMatch(source, /{{\s*downloadJobStatusLabel\(job\.status\)\s*}}/);
    assert.match(source, /grid-template-columns:\s*minmax\(0,\s*1fr\)\s+32px\s+64px/);
    assert.match(source, /width:\s*14px;\s*height:\s*14px;/);
});
