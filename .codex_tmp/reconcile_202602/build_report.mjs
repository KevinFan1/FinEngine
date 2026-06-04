import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "/Users/kevinfan/Desktop/projects/FinEngine/.codex_tmp/reconcile_202602/reconcile_data.json";
const outputDir = "/Users/kevinfan/Desktop/projects/FinEngine/outputs/reconcile_202602_20260603";
const outputPath = `${outputDir}/2026-02_商家对账差异分析报告.xlsx`;

const raw = await fs.readFile(inputPath, "utf8");
const data = JSON.parse(raw);

const workbook = Workbook.create();
workbook.setColorScheme({
  name: "Reconcile",
  themeColors: {
    accent1: "#164E63",
    accent2: "#B45309",
    accent3: "#15803D",
    accent4: "#B91C1C",
    accent5: "#475569",
    accent6: "#0F766E",
    dk1: "#111827",
    lt1: "#FFFFFF",
    lt2: "#E5E7EB",
    hlink: "#0369A1",
    folHlink: "#7C2D12",
  },
});

function colName(index) {
  let name = "";
  let n = index;
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function excelValue(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "number") return Number.isFinite(value) ? Math.round(value * 100) / 100 : null;
  if (typeof value === "boolean") return value;
  return String(value);
}

function setColWidths(sheet, headers, rows) {
  headers.forEach((header, idx) => {
    const sample = rows.slice(0, 500).map((row) => row[header]);
    const maxChars = Math.max(
      String(header).length,
      ...sample.map((value) => (value === null || value === undefined ? 0 : String(value).length)),
    );
    const width = Math.max(64, Math.min(180, maxChars * 6 + 14));
    sheet.getRange(`${colName(idx + 1)}:${colName(idx + 1)}`).format.columnWidth = width;
  });
}

function formatTable(sheet, headers, rows, opts = {}) {
  const rowCount = rows.length + 1;
  const colCount = headers.length;
  const end = `${colName(colCount)}${rowCount}`;
  const fullRange = sheet.getRange(`A1:${end}`);
  const headerRange = sheet.getRange(`A1:${colName(colCount)}1`);

  fullRange.format = {
    font: { name: "Aptos", size: 10, color: "#111827" },
    verticalAlignment: "center",
    wrapText: false,
  };
  headerRange.format = {
    fill: "#164E63",
    font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  fullRange.format.borders = { preset: "outside", style: "thin", color: "#CBD5E1" };
  sheet.freezePanes.freezeRows(1);
  setColWidths(sheet, headers, rows);

  for (let idx = 0; idx < headers.length; idx += 1) {
    const header = headers[idx];
    if (/金额|GMV|应付|差异|余额|流水|货款|借退|动账/.test(header) && rowCount > 1) {
      sheet.getRange(`${colName(idx + 1)}2:${colName(idx + 1)}${rowCount}`).format.numberFormat = "#,##0.00;[Red]-#,##0.00;0.00";
    }
    if (/行数|订单数|原始行号|手工行号|汇总行号/.test(header) && rowCount > 1) {
      sheet.getRange(`${colName(idx + 1)}2:${colName(idx + 1)}${rowCount}`).format.numberFormat = "0";
    }
  }

  if (opts.highlightDiffCol) {
    const diffIndex = headers.indexOf(opts.highlightDiffCol) + 1;
    if (diffIndex > 0 && rowCount > 1) {
      sheet.getRange(`${colName(diffIndex)}2:${colName(diffIndex)}${rowCount}`).conditionalFormats.addCellIs({
        operator: "notEqual",
        formula: 0,
        format: { fill: "#FEF3C7", font: { color: "#92400E", bold: true } },
      });
    }
  }
}

function addSheet(name, rows, opts = {}) {
  const sheet = workbook.worksheets.add(name);
  const headers = opts.headers || (rows.length ? Object.keys(rows[0]) : ["说明"]);
  const values = [headers, ...rows.map((row) => headers.map((header) => excelValue(row[header])))];
  const range = sheet.getRange(`A1:${colName(headers.length)}${values.length}`);
  range.values = values;
  formatTable(sheet, headers, rows, opts);
  return sheet;
}

function metricRows(metrics) {
  return Object.entries(metrics).map(([key, value]) => ({ 指标: key, 数值: excelValue(value) }));
}

const summarySheet = workbook.worksheets.add("结论摘要");
summarySheet.getRange("A1").values = [["2026-02 商家对账差异分析报告"]];
summarySheet.getRange("A1:E1").format = {
  fill: "#0F172A",
  font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" },
  verticalAlignment: "center",
};
summarySheet.getRange("A2").values = [[`生成时间：${data.metadata.generated_at}`]];
summarySheet.getRange("A2:E2").format = {
  fill: "#E0F2FE",
  font: { name: "Aptos", size: 10, color: "#0C4A6E" },
};

const conclusionHeaders = ["项目", "结论", "关键数字"];
summarySheet.getRange("A4:C4").values = [conclusionHeaders];
summarySheet.getRange(`A5:C${4 + data.findings.length}`).values = data.findings.map((row) =>
  conclusionHeaders.map((header) => excelValue(row[header])),
);
formatTable(summarySheet, conclusionHeaders, data.findings, {});
summarySheet.getRange("A1").values = [["2026-02 商家对账差异分析报告"]];
summarySheet.getRange("A1:E1").format = {
  fill: "#0F172A",
  font: { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" },
};
summarySheet.getRange("A2").values = [[`生成时间：${data.metadata.generated_at}`]];
summarySheet.getRange("A2:E2").format = {
  fill: "#E0F2FE",
  font: { name: "Aptos", size: 10, color: "#0C4A6E" },
};
summarySheet.getRange("A4:C4").format = {
  fill: "#164E63",
  font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  wrapText: true,
};
summarySheet.getRange(`A5:C${4 + data.findings.length}`).format = {
  font: { name: "Aptos", size: 10, color: "#111827" },
  verticalAlignment: "top",
  wrapText: true,
};
summarySheet.getRange("A:A").format.columnWidth = 150;
summarySheet.getRange("B:B").format.columnWidth = 360;
summarySheet.getRange("C:C").format.columnWidth = 260;
summarySheet.freezePanes.freezeRows(4);

const metricStartRow = 13;
const metrics = metricRows(data.summary_metrics);
summarySheet.getRange(`A${metricStartRow}:B${metricStartRow}`).values = [["指标", "数值"]];
summarySheet.getRange(`A${metricStartRow + 1}:B${metricStartRow + metrics.length}`).values = metrics.map((row) => [row.指标, row.数值]);
summarySheet.getRange(`A${metricStartRow}:B${metricStartRow}`).format = {
  fill: "#B45309",
  font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
};
summarySheet.getRange(`B${metricStartRow + 1}:B${metricStartRow + metrics.length}`).format.numberFormat = "#,##0.00;[Red]-#,##0.00;0.00";

const sourceStartRow = metricStartRow;
summarySheet.getRange(`D${sourceStartRow}:E${sourceStartRow}`).values = [["来源文件", "路径"]];
summarySheet.getRange(`D${sourceStartRow + 1}:E${sourceStartRow + 2}`).values = [
  ["原始数据", data.metadata.original_file],
  ["手工汇总文件", data.metadata.manual_file],
];
summarySheet.getRange(`D${sourceStartRow}:E${sourceStartRow}`).format = {
  fill: "#475569",
  font: { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" },
};
summarySheet.getRange("D:D").format.columnWidth = 120;
summarySheet.getRange("E:E").format.columnWidth = 420;

addSheet("收款商家归属差异", data.payee_mapping, {
  highlightDiffCol: "应付差异_手工减原始",
});
addSheet("大商家名称差异", data.big_merchant_mapping, {
  highlightDiffCol: "应付差异_手工减原始",
});
addSheet("明细vs汇总", data.summary_compare, {
  highlightDiffCol: "应付差异_明细减汇总",
});
addSheet("手工归属影响", data.reassignment_effect, {
  highlightDiffCol: "应付变化_手工归属减原始归属",
});
addSheet("红单货款vs汇总", data.red_goods_compare, {
  highlightDiffCol: "汇总应付减红单应付",
});
addSheet("疑似归错明细", data.merchant_mismatch_detail, {
  highlightDiffCol: "_应付差异_手工减原始",
});
addSheet("金额差异明细", data.amount_mismatch_detail, {
  highlightDiffCol: "_应付差异_手工减原始",
});
addSheet("原始区间被排除行", data.selected_span_excluded);
addSheet("同订单未选流水", data.extra_same_order.length ? data.extra_same_order : [{ 说明: "手工订单号在原始数据中没有额外未选流水" }]);

await fs.mkdir(outputDir, { recursive: true });

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const summaryInspect = await workbook.inspect({
  kind: "table",
  range: "结论摘要!A1:E30",
  include: "values,formulas",
  tableMaxRows: 30,
  tableMaxCols: 6,
});
console.log(summaryInspect.ndjson);

await workbook.render({ sheetName: "结论摘要", range: "A1:E30", scale: 1, format: "png" });
await workbook.render({ sheetName: "收款商家归属差异", range: "A1:H12", scale: 1, format: "png" });

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
