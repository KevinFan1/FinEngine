import test from "node:test";
import assert from "node:assert/strict";
import {
    formatResultSummaryValue,
    resultSummaryItems,
} from "./resultSummary.ts";

test("resultSummaryItems keeps Chinese summary keys readable", () => {
    const items = resultSummaryItems({
        文件类型: "红单",
        错误明细: ["第 2 行金额为空", "第 3 行订单号为空"],
        依赖数据: "order_index",
    });

    assert.deepEqual(items, [
        { key: "文件类型", label: "文件类型", value: "红单" },
        {
            key: "错误明细",
            label: "错误明细",
            value: "第 2 行金额为空；第 3 行订单号为空",
        },
        { key: "依赖数据", label: "依赖数据", value: "订单索引" },
    ]);
});

test("resultSummaryItems translates legacy English keys to Chinese labels", () => {
    const items = resultSummaryItems({
        total_rows: 10,
        success_rows: 8,
        failed_rows: 2,
        summary_ids: [12, 13],
        fallback_time_count: 3,
    });

    assert.deepEqual(items, [
        { key: "total_rows", label: "总行数", value: "10" },
        { key: "success_rows", label: "成功行数", value: "8" },
        { key: "failed_rows", label: "失败行数", value: "2" },
        { key: "summary_ids", label: "汇总记录ID", value: "12、13" },
        { key: "fallback_time_count", label: "兜底归属年月行数", value: "3" },
    ]);
});

test("resultSummaryItems can omit summary keys that are shown elsewhere", () => {
    const items = resultSummaryItems(
        {
            总行数: 10,
            错误明细: ["第 2 行金额为空"],
            errors: ["legacy error"],
            解析耗时秒: 0.23,
        },
        { excludeKeys: ["错误明细", "errors"] },
    );

    assert.deepEqual(items, [
        { key: "总行数", label: "总行数", value: "10" },
        { key: "解析耗时秒", label: "解析耗时秒", value: "0.23" },
    ]);
});

test("resultSummaryItems hides performance metrics when not allowed", () => {
    const summary = {
        总行数: 10,
        文件下载耗时秒: 1.23,
        解析耗时秒: 2.34,
        明细入库耗时秒: 3.45,
        汇总重建耗时秒: 4.56,
        parse_seconds: 5.67,
    };

    assert.deepEqual(resultSummaryItems(summary, { showPerformanceMetrics: false }), [
        { key: "总行数", label: "总行数", value: "10" },
    ]);

    assert.deepEqual(
        resultSummaryItems(summary, { showPerformanceMetrics: true }).map(
            (item) => item.key,
        ),
        [
            "总行数",
            "文件下载耗时秒",
            "解析耗时秒",
            "明细入库耗时秒",
            "汇总重建耗时秒",
            "parse_seconds",
        ],
    );
});

test("formatResultSummaryValue formats empty and complex values", () => {
    assert.equal(formatResultSummaryValue("涉及年月", []), "无");
    assert.equal(formatResultSummaryValue("处理提示", null), "-");
    assert.equal(
        formatResultSummaryValue("耗时", { parse: 1.2, rebuild: 0.3 }),
        '{\n  "parse": 1.2,\n  "rebuild": 0.3\n}',
    );
});
