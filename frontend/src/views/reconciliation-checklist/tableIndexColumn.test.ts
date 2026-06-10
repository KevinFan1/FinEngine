import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const REQUIRED_INDEX_TABLES = [
    {
        label: "对账清单任务中心",
        file: new URL("./tasks.vue", import.meta.url),
        tableCount: 1,
        firstColumn: "selection",
    },
    {
        label: "对账清单汇总页",
        file: new URL("./summary.vue", import.meta.url),
        tableCount: 3,
        firstColumn: "selection",
    },
    {
        label: "下载中心",
        file: new URL("../download/index.vue", import.meta.url),
        tableCount: 1,
        firstColumn: "index",
    },
];

test("keeps required tables with the correct leading columns", () => {
    for (const requirement of REQUIRED_INDEX_TABLES) {
        const source = fs.readFileSync(requirement.file, "utf8");
        const leadingColumns = leadingTableColumns(source, 2);

        assert.equal(
            leadingColumns.length,
            requirement.tableCount,
            `${requirement.label} should have ${requirement.tableCount} checked table(s)`,
        );

        leadingColumns.forEach((columns, index) => {
            const tableLabel =
                requirement.tableCount === 1
                    ? requirement.label
                    : `${requirement.label}第 ${index + 1} 个表格`;

            if (requirement.firstColumn === "selection") {
                assert.match(
                    columns[0] || "",
                    /\btype="selection"/,
                    `${tableLabel} first column must be selection`,
                );
                assert.match(
                    columns[1] || "",
                    /\blabel="序号"/,
                    `${tableLabel} second column must be 序号`,
                );
                assert.doesNotMatch(
                    columns[1] || "",
                    /\bv-if=/,
                    `${tableLabel} sequence column must always be visible`,
                );
                return;
            }

            assert.match(
                columns[0] || "",
                /\blabel="序号"/,
                `${tableLabel} first column must be 序号`,
            );
            assert.doesNotMatch(
                columns[0] || "",
                /\bv-if=/,
                `${tableLabel} sequence column must always be visible`,
            );
        });
    }
});

test("summary tables do not append trailing spacer columns", () => {
    const source = fs.readFileSync(new URL("./summary.vue", import.meta.url), "utf8");
    const tableBlocks = extractTableBlocks(source);

    assert.equal(tableBlocks.length, 3, "对账清单汇总页 should keep 3 summary tables");

    tableBlocks.forEach((tableBlock, index) => {
        const columns = extractAllColumns(tableBlock);
        const lastColumn = columns.at(-1) || "";

        assert.ok(lastColumn, `对账清单汇总页第 ${index + 1} 个表格 should have a trailing column`);
        assert.doesNotMatch(
            lastColumn,
            /\blabel=""|\bmin-width="12"/,
            `对账清单汇总页第 ${index + 1} 个表格 should not use an empty spacer column`,
        );
    });
});

test("summary tables keep stretch-to-card fit behavior", () => {
    const source = fs.readFileSync(new URL("./summary.vue", import.meta.url), "utf8");
    const tableBlocks = extractTableBlocks(source);

    assert.equal(tableBlocks.length, 3, "对账清单汇总页 should keep 3 summary tables");

    tableBlocks.forEach((tableBlock, index) => {
        assert.doesNotMatch(
            tableBlock,
            /:fit="false"|\bfit="false"/,
            `对账清单汇总页第 ${index + 1} 个表格 should stretch to the card width`,
        );
    });
});

test("summary page keeps tables flush with the list area", () => {
    const source = fs.readFileSync(new URL("./summary.vue", import.meta.url), "utf8");

    assert.doesNotMatch(
        source,
        /class="summary-table-shell"/,
        "对账清单汇总页 should not wrap tables in a shell that prevents full-width layout",
    );
    assert.doesNotMatch(
        source,
        /\.summary-table-shell\s*\{[\s\S]*padding-right:/,
        "对账清单汇总页 should not reserve a right gutter beside the list",
    );
});

test("summary page keeps the trailing column aligned with card header padding", () => {
    const source = fs.readFileSync(new URL("./summary.vue", import.meta.url), "utf8");
    const tableBlocks = extractTableBlocks(source);

    assert.equal(tableBlocks.length, 3, "对账清单汇总页 should keep 3 summary tables");

    tableBlocks.forEach((tableBlock, index) => {
        const columns = extractAllColumns(tableBlock);
        const lastColumn = columns.at(-1) || "";

        assert.match(
            lastColumn,
            /\bclass-name="[^"]*summary-edge-column[^"]*"/,
            `对账清单汇总页第 ${index + 1} 个表格最后一列 should mark trailing cells with summary-edge-column`,
        );
        assert.match(
            lastColumn,
            /\bheader-class-name="[^"]*summary-edge-column[^"]*"/,
            `对账清单汇总页第 ${index + 1} 个表格最后一列表头 should mark trailing cells with summary-edge-column`,
        );
    });

    assert.match(
        source,
        /:deep\(\.summary-table \.summary-edge-column \.cell\),[\s\S]*padding-right:\s*18px\s*!important;/,
        "对账清单汇总页 should keep 18px trailing cell padding to align with card header actions",
    );
});

function leadingTableColumns(source: string, count: number): string[][] {
    return extractTableBlocks(source).map((tableBlock) => extractLeadingColumns(tableBlock, count));
}

function extractLeadingColumns(source: string, count: number): string[] {
    return extractAllColumns(source).slice(0, count);
}

function extractAllColumns(source: string): string[] {
    const columns: string[] = [];
    const columnPattern = /<el-table-column\b[\s\S]*?(?:\/>|>)/g;
    let match: RegExpExecArray | null;

    while ((match = columnPattern.exec(source))) {
        columns.push(match[0]);
    }

    return columns;
}

function extractTableBlocks(source: string): string[] {
    const tableBlocks: string[] = [];
    const tablePattern = /<el-table(?=[\s>])[\s\S]*?<\/el-table>/g;
    let tableMatch: RegExpExecArray | null;

    while ((tableMatch = tablePattern.exec(source))) {
        tableBlocks.push(tableMatch[0]);
    }

    return tableBlocks;
}
