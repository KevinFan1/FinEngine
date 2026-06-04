import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ORIG_PATH = Path("/Users/kevinfan/Documents/财务需求/对账单需求/原始数据.xlsx")
MANUAL_PATH = Path("/Users/kevinfan/Downloads/2026-02_店铺全部_商家对账汇总_附带明细_全部 (1).xlsx")
OUT_DIR = Path("/Users/kevinfan/Desktop/projects/FinEngine/.codex_tmp/reconcile_202602")
OUT_JSON = OUT_DIR / "reconcile_data.json"


def norm_id(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.startswith("'"):
        text = text[1:]
    text = text.strip()
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def norm_name(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", "", text)
    return text.replace("（", "(").replace("）", ")")


def display_text(value, blank="(空)"):
    if pd.isna(value):
        return blank
    text = str(value).strip()
    return text if text else blank


def money(series):
    return np.round(pd.to_numeric(series, errors="coerce").fillna(0).astype(float), 2)


def safe_records(df, columns):
    records = df.loc[:, columns].copy()
    records = records.replace({np.nan: None})
    output = []
    for item in records.to_dict("records"):
        cleaned = {}
        for key, value in item.items():
            if isinstance(value, (np.integer,)):
                cleaned[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                if math.isnan(value):
                    cleaned[key] = None
                else:
                    cleaned[key] = round(float(value), 2)
            else:
                cleaned[key] = value
        output.append(cleaned)
    return output


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    orig = pd.read_excel(ORIG_PATH, sheet_name="Sheet1", dtype=str)
    manual = pd.read_excel(MANUAL_PATH, sheet_name="动账明细", dtype=str)
    summary = pd.read_excel(MANUAL_PATH, sheet_name="商家对账汇总", dtype=str)
    red_goods = pd.read_excel(MANUAL_PATH, sheet_name="红单货款", dtype=str)

    for df in (orig, manual, summary, red_goods):
        df.columns = [str(col).strip() for col in df.columns]

    orig["_原始行号"] = np.arange(2, len(orig) + 2)
    manual["_手工行号"] = np.arange(2, len(manual) + 2)
    summary["_汇总行号"] = np.arange(2, len(summary) + 2)

    orig["_流水号"] = orig["动帐流水号"].map(norm_id)
    manual["_流水号"] = manual["动账流水号"].map(norm_id)
    orig["_订单号_norm"] = orig["订单号"].map(norm_id)
    manual["_订单号_norm"] = manual["订单号"].map(norm_id)

    matched = manual.merge(orig, on="_流水号", how="left", suffixes=("_手工", "_原始"), indicator=True)
    matched["_订单号_match"] = matched["_订单号_norm_手工"]
    matched["_大商家_手工_norm"] = matched["大商家名称"].map(norm_name)
    matched["_大商家_原始_norm"] = matched["商家名（红单）"].map(norm_name)
    matched["_收款_手工_norm"] = matched["收款商家"].map(norm_name)
    matched["_收款_原始_norm"] = matched["调商家主体"].map(norm_name)

    matched["_手工GMV"] = money(matched["实收GMV_手工"])
    matched["_原始GMV"] = money(matched["实收GMV_原始"])
    matched["_手工应付"] = money(matched["直播款"])
    matched["_原始应付"] = money(matched["调-应付商家金额"])
    matched["_手工动账金额"] = money(matched["动账金额_手工"])
    matched["_原始动账金额"] = money(matched["动账金额_原始"])
    matched["_GMV差异_手工减原始"] = matched["_手工GMV"] - matched["_原始GMV"]
    matched["_应付差异_手工减原始"] = matched["_手工应付"] - matched["_原始应付"]
    matched["_动账金额差异_手工减原始"] = matched["_手工动账金额"] - matched["_原始动账金额"]
    matched["_收款商家是否不同"] = matched["_收款_手工_norm"] != matched["_收款_原始_norm"]
    matched["_大商家是否不同"] = matched["_大商家_手工_norm"] != matched["_大商家_原始_norm"]
    matched["_金额是否不同"] = (
        matched["_GMV差异_手工减原始"].abs().gt(0.005)
        | matched["_应付差异_手工减原始"].abs().gt(0.005)
        | matched["_动账金额差异_手工减原始"].abs().gt(0.005)
    )

    missing_orig = matched[matched["_merge"] != "both"].copy()
    merchant_mismatch = matched[matched["_收款商家是否不同"] | matched["_大商家是否不同"]].copy()
    amount_mismatch = matched[matched["_金额是否不同"]].copy()

    payee_map = (
        matched[matched["_收款商家是否不同"]]
        .assign(
            手工收款商家=lambda d: d["收款商家"].map(display_text),
            原始调商家主体=lambda d: d["调商家主体"].map(display_text),
            手工大商家=lambda d: d["大商家名称"].map(display_text),
            原始红单商家=lambda d: d["商家名（红单）"].map(display_text),
        )
        .groupby(["手工收款商家", "原始调商家主体"], dropna=False)
        .agg(
            差异行数=("_流水号", "size"),
            订单数=("_订单号_match", "nunique"),
            手工GMV=("_手工GMV", "sum"),
            原始GMV=("_原始GMV", "sum"),
            手工应付=("_手工应付", "sum"),
            原始应付=("_原始应付", "sum"),
            应付差异_手工减原始=("_应付差异_手工减原始", "sum"),
            示例手工大商家=("手工大商家", lambda s: " / ".join(pd.Series(s).dropna().astype(str).unique()[:3])),
            示例原始红单商家=("原始红单商家", lambda s: " / ".join(pd.Series(s).dropna().astype(str).unique()[:3])),
        )
        .reset_index()
    )
    payee_map["GMV差异_手工减原始"] = payee_map["手工GMV"] - payee_map["原始GMV"]
    payee_map = payee_map.sort_values(["手工应付", "差异行数"], ascending=[False, False])

    big_map = (
        matched[matched["_大商家是否不同"]]
        .assign(
            手工大商家=lambda d: d["大商家名称"].map(display_text),
            原始红单商家=lambda d: d["商家名（红单）"].map(display_text),
            手工收款商家=lambda d: d["收款商家"].map(display_text),
            原始调商家主体=lambda d: d["调商家主体"].map(display_text),
        )
        .groupby(["手工大商家", "原始红单商家"], dropna=False)
        .agg(
            差异行数=("_流水号", "size"),
            订单数=("_订单号_match", "nunique"),
            手工应付=("_手工应付", "sum"),
            原始应付=("_原始应付", "sum"),
            应付差异_手工减原始=("_应付差异_手工减原始", "sum"),
            示例手工收款商家=("手工收款商家", lambda s: " / ".join(pd.Series(s).dropna().astype(str).unique()[:3])),
            示例原始调商家主体=("原始调商家主体", lambda s: " / ".join(pd.Series(s).dropna().astype(str).unique()[:3])),
        )
        .reset_index()
        .sort_values(["手工应付", "差异行数"], ascending=[False, False])
    )

    manual_group = (
        manual.assign(
            收款商家_norm=manual["收款商家"].map(norm_name),
            收款商家显示=manual["收款商家"].map(display_text),
            明细GMV=money(manual["实收GMV"]),
            明细应付=money(manual["直播款"]),
        )
        .groupby(["收款商家_norm", "收款商家显示"], dropna=False)
        .agg(明细行数=("_流水号", "size"), 明细GMV=("明细GMV", "sum"), 明细应付=("明细应付", "sum"))
        .reset_index()
    )
    summary_group = (
        summary.assign(
            收款商家_norm=summary["商家收款主体"].map(norm_name),
            收款商家显示=summary["商家收款主体"].map(display_text),
            汇总GMV=money(summary["实收GMV"]),
            汇总应付=money(summary["应付商家净额"]),
        )
        .groupby(["收款商家_norm", "收款商家显示"], dropna=False)
        .agg(汇总行数=("_汇总行号", "size"), 汇总GMV=("汇总GMV", "sum"), 汇总应付=("汇总应付", "sum"))
        .reset_index()
    )
    summary_compare = manual_group.merge(summary_group, on="收款商家_norm", how="outer", suffixes=("_明细", "_汇总"))
    summary_compare["收款商家"] = summary_compare["收款商家显示_明细"].fillna(summary_compare["收款商家显示_汇总"])
    for col in ("明细行数", "明细GMV", "明细应付", "汇总行数", "汇总GMV", "汇总应付"):
        summary_compare[col] = summary_compare[col].fillna(0)
    summary_compare["GMV差异_明细减汇总"] = summary_compare["明细GMV"] - summary_compare["汇总GMV"]
    summary_compare["应付差异_明细减汇总"] = summary_compare["明细应付"] - summary_compare["汇总应付"]
    summary_compare = summary_compare.sort_values("应付差异_明细减汇总", key=lambda s: s.abs(), ascending=False)

    original_payee_group = (
        matched.assign(
            原始收款商家_norm=matched["调商家主体"].map(norm_name),
            原始收款商家显示=matched["调商家主体"].map(display_text),
        )
        .groupby(["原始收款商家_norm", "原始收款商家显示"], dropna=False)
        .agg(原始归属行数=("_流水号", "size"), 原始归属GMV=("_原始GMV", "sum"), 原始归属应付=("_原始应付", "sum"))
        .reset_index()
    )
    reassignment_effect = manual_group.merge(
        original_payee_group,
        left_on="收款商家_norm",
        right_on="原始收款商家_norm",
        how="outer",
    )
    reassignment_effect["商家"] = reassignment_effect["收款商家显示"].fillna(reassignment_effect["原始收款商家显示"])
    for col in ("明细行数", "明细GMV", "明细应付", "原始归属行数", "原始归属GMV", "原始归属应付"):
        reassignment_effect[col] = reassignment_effect[col].fillna(0)
    reassignment_effect["GMV变化_手工归属减原始归属"] = reassignment_effect["明细GMV"] - reassignment_effect["原始归属GMV"]
    reassignment_effect["应付变化_手工归属减原始归属"] = reassignment_effect["明细应付"] - reassignment_effect["原始归属应付"]
    reassignment_effect = reassignment_effect.sort_values("应付变化_手工归属减原始归属", key=lambda s: s.abs(), ascending=False)

    manual_flows = set(manual["_流水号"])
    selected_orig = orig[orig["_流水号"].isin(manual_flows)].copy()
    if selected_orig.empty:
        selected_span_missing = pd.DataFrame()
        selected_span = {"min_row": None, "max_row": None, "span_rows": 0, "selected_rows": 0, "excluded_rows_in_span": 0}
    else:
        min_row = int(selected_orig["_原始行号"].min())
        max_row = int(selected_orig["_原始行号"].max())
        selected_rows = set(selected_orig["_原始行号"])
        excluded = orig[
            orig["_原始行号"].between(min_row, max_row)
            & ~orig["_原始行号"].isin(selected_rows)
        ].copy()
        selected_span_missing = excluded.copy()
        selected_span = {
            "min_row": min_row,
            "max_row": max_row,
            "span_rows": max_row - min_row + 1,
            "selected_rows": int(len(selected_orig)),
            "excluded_rows_in_span": int(len(excluded)),
        }

    original_order_rows = orig[orig["_订单号_norm"].isin(set(manual["_订单号_norm"]) - {""})].copy()
    extra_same_order = original_order_rows[~original_order_rows["_流水号"].isin(manual_flows)].copy()

    red_goods_group = (
        red_goods.assign(
            收款商家_norm=red_goods["收款商家"].map(norm_name),
            收款商家显示=red_goods["收款商家"].map(display_text),
            红单应付=money(red_goods["应付货款金额"]),
            红单借退=money(red_goods["借-退"]),
        )
        .groupby(["收款商家_norm", "收款商家显示"], dropna=False)
        .agg(红单行数=("收款商家", "size"), 红单应付=("红单应付", "sum"), 红单借退=("红单借退", "sum"))
        .reset_index()
    )
    red_compare = summary_group.merge(red_goods_group, on="收款商家_norm", how="outer")
    red_compare["收款商家"] = red_compare["收款商家显示_x"].fillna(red_compare["收款商家显示_y"])
    for col in ("汇总应付", "汇总GMV", "红单应付", "红单借退", "汇总行数", "红单行数"):
        red_compare[col] = red_compare[col].fillna(0)
    red_compare["汇总应付减红单应付"] = red_compare["汇总应付"] - red_compare["红单应付"]
    red_compare = red_compare.sort_values("汇总应付减红单应付", key=lambda s: s.abs(), ascending=False)

    total_manual_detail_pay = float(money(manual["直播款"]).sum())
    total_summary_pay = float(money(summary["应付商家净额"]).sum())
    total_original_matched_pay = float(matched["_原始应付"].sum())
    total_manual_gmv = float(money(manual["实收GMV"]).sum())
    total_summary_gmv = float(money(summary["实收GMV"]).sum())
    total_original_matched_gmv = float(matched["_原始GMV"].sum())

    findings = [
        {
            "项目": "手工动账明细匹配原始数据",
            "结论": "9009 行动账明细按动账流水号全部在原始数据中找到；不是明细缺失导致。",
            "关键数字": f"手工明细 {len(manual)} 行；原始匹配缺失 {len(missing_orig)} 行。",
        },
        {
            "项目": "按订单号匹配风险",
            "结论": "手工明细的 8903 个订单在原始数据中没有额外未选流水；按订单号不会多带行，但订单号列在两表显示格式不同，需规范化。",
            "关键数字": f"同订单未选流水 {len(extra_same_order)} 行。",
        },
        {
            "项目": "主要差异来源",
            "结论": "手工明细中 4741 行收款商家不同于原始数据调商家主体，属于收款主体重归属/改写。",
            "关键数字": f"涉及手工应付 {float(merchant_mismatch['_手工应付'].sum()):,.2f}；其中收款主体不同 {int(matched['_收款商家是否不同'].sum())} 行。",
        },
        {
            "项目": "金额口径差异",
            "结论": "同一流水下动账金额一致；GMV 仅 1 行差 1.81；应付/直播款有 387 行小额差异，合计手工比原始少 6.28，多数为分行四舍五入口径差。",
            "关键数字": f"手工明细应付 {total_manual_detail_pay:,.2f}；原始匹配应付 {total_original_matched_pay:,.2f}；差 {total_manual_detail_pay - total_original_matched_pay:,.2f}。",
        },
        {
            "项目": "汇总表与动账明细",
            "结论": "汇总表 GMV 与动账明细完全一致；汇总表应付商家净额比动账明细直播款多 4.90，且源文件中这两张表均为硬填数值，无公式。",
            "关键数字": f"明细应付 {total_manual_detail_pay:,.2f}；汇总应付 {total_summary_pay:,.2f}；差 {total_manual_detail_pay - total_summary_pay:,.2f}。",
        },
        {
            "项目": "原始数据全表/区间筛选",
            "结论": "手工明细取自原始数据后段范围，但中间排除了 84 行，因此直接用原始数据全表或连续区间汇总会对不上。",
            "关键数字": f"原始行号 {selected_span['min_row']} 至 {selected_span['max_row']}，跨度 {selected_span['span_rows']} 行，排除 {selected_span['excluded_rows_in_span']} 行。",
        },
    ]

    data = {
        "metadata": {
            "original_file": str(ORIG_PATH),
            "manual_file": str(MANUAL_PATH),
            "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary_metrics": {
            "原始数据行数": int(len(orig)),
            "手工动账明细行数": int(len(manual)),
            "商家对账汇总行数": int(len(summary)),
            "手工订单数": int((manual["_订单号_norm"] != "").sum()),
            "手工唯一订单数": int(manual["_订单号_norm"].nunique()),
            "流水号匹配缺失行数": int(len(missing_orig)),
            "收款商家不同明细行数": int(matched["_收款商家是否不同"].sum()),
            "大商家不同明细行数": int(matched["_大商家是否不同"].sum()),
            "金额不同明细行数": int(amount_mismatch.shape[0]),
            "手工明细GMV": total_manual_gmv,
            "汇总表GMV": total_summary_gmv,
            "原始匹配GMV": total_original_matched_gmv,
            "手工明细应付": total_manual_detail_pay,
            "汇总表应付": total_summary_pay,
            "原始匹配应付": total_original_matched_pay,
            "明细应付减汇总应付": total_manual_detail_pay - total_summary_pay,
            "明细应付减原始匹配应付": total_manual_detail_pay - total_original_matched_pay,
            "明细GMV减汇总GMV": total_manual_gmv - total_summary_gmv,
            "明细GMV减原始匹配GMV": total_manual_gmv - total_original_matched_gmv,
            **selected_span,
            "同订单未选原始流水行数": int(len(extra_same_order)),
        },
        "findings": findings,
        "payee_mapping": safe_records(
            payee_map,
            [
                "手工收款商家",
                "原始调商家主体",
                "差异行数",
                "订单数",
                "手工GMV",
                "原始GMV",
                "GMV差异_手工减原始",
                "手工应付",
                "原始应付",
                "应付差异_手工减原始",
                "示例手工大商家",
                "示例原始红单商家",
            ],
        ),
        "big_merchant_mapping": safe_records(
            big_map,
            [
                "手工大商家",
                "原始红单商家",
                "差异行数",
                "订单数",
                "手工应付",
                "原始应付",
                "应付差异_手工减原始",
                "示例手工收款商家",
                "示例原始调商家主体",
            ],
        ),
        "summary_compare": safe_records(
            summary_compare,
            [
                "收款商家",
                "明细行数",
                "汇总行数",
                "明细GMV",
                "汇总GMV",
                "GMV差异_明细减汇总",
                "明细应付",
                "汇总应付",
                "应付差异_明细减汇总",
            ],
        ),
        "reassignment_effect": safe_records(
            reassignment_effect[
                reassignment_effect["应付变化_手工归属减原始归属"].abs().gt(0.005)
                | reassignment_effect["GMV变化_手工归属减原始归属"].abs().gt(0.005)
            ],
            [
                "商家",
                "明细行数",
                "原始归属行数",
                "明细GMV",
                "原始归属GMV",
                "GMV变化_手工归属减原始归属",
                "明细应付",
                "原始归属应付",
                "应付变化_手工归属减原始归属",
            ],
        ),
        "red_goods_compare": safe_records(
            red_compare,
            [
                "收款商家",
                "汇总行数",
                "红单行数",
                "汇总GMV",
                "汇总应付",
                "红单应付",
                "汇总应付减红单应付",
                "红单借退",
            ],
        ),
        "merchant_mismatch_detail": safe_records(
            merchant_mismatch.sort_values(["_收款商家是否不同", "_手工应付"], ascending=[False, False]),
            [
                "_手工行号",
                "_原始行号",
                "订单号_手工",
                "子订单号_手工",
                "动账流水号",
                "动账场景_手工",
                "动账方向_手工",
                "_手工动账金额",
                "_手工GMV",
                "_原始GMV",
                "_手工应付",
                "_原始应付",
                "_应付差异_手工减原始",
                "大商家名称",
                "商家名（红单）",
                "收款商家",
                "调商家主体",
                "商品编码_手工",
                "商品名称_手工",
                "直播间",
                "直播日期",
            ],
        ),
        "amount_mismatch_detail": safe_records(
            amount_mismatch.sort_values("_应付差异_手工减原始", key=lambda s: s.abs(), ascending=False),
            [
                "_手工行号",
                "_原始行号",
                "订单号_手工",
                "动账流水号",
                "动账场景_手工",
                "动账方向_手工",
                "_手工动账金额",
                "_原始动账金额",
                "_动账金额差异_手工减原始",
                "_手工GMV",
                "_原始GMV",
                "_GMV差异_手工减原始",
                "_手工应付",
                "_原始应付",
                "_应付差异_手工减原始",
                "大商家名称",
                "商家名（红单）",
                "收款商家",
                "调商家主体",
                "商品编码_手工",
                "商品名称_手工",
            ],
        ),
        "selected_span_excluded": safe_records(
            selected_span_missing,
            [
                "_原始行号",
                "订单号",
                "动帐流水号",
                "动账场景",
                "动账方向",
                "动账金额",
                "实收GMV",
                "调-应付商家金额",
                "商家名（红单）",
                "调商家主体",
                "商品编码",
                "商品名称",
                "备注",
            ],
        ),
        "extra_same_order": safe_records(
            extra_same_order,
            [
                "_原始行号",
                "订单号",
                "动帐流水号",
                "动账场景",
                "动账方向",
                "动账金额",
                "实收GMV",
                "调-应付商家金额",
                "商家名（红单）",
                "调商家主体",
                "商品编码",
                "商品名称",
                "备注",
            ],
        ),
    }

    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUT_JSON)


if __name__ == "__main__":
    main()
