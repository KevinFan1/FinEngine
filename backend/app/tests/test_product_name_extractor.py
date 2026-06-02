import argparse
import re
import unicodedata
from pathlib import Path

import pandas as pd


PRODUCT_NAME_COLUMN = "商品名称"
SKU_COLUMN = "货号"

SOURCE_DIR = Path("/Users/kevinfan/Documents/04财务数据/26年4月动账资金/2026-04动账原数据")
RESULT_DIR = Path(__file__).resolve().parent / "result"
DEFAULT_MERGED_OUTPUT = RESULT_DIR / "合并结果.xlsx"

# 商品编码：字母前缀 + 至少 3 位数字。
# 支持：
#   CAN1400766+CAN1400842
#   V33535-F / V61416-M
#   约33*13mmCAN3110492 这种贴在尺寸单位后的货号
SKU_TOKEN_PATTERN = r"[A-Z]{1,16}\d{3,16}(?:-[FM](?![A-Z0-9]))?"
SKU_GROUP_PATTERN = rf"{SKU_TOKEN_PATTERN}(?:\s*\+\s*{SKU_TOKEN_PATTERN})*"
SKU_PATTERN = re.compile(
    rf"(?<![A-Z0-9])({SKU_GROUP_PATTERN})(?![A-Z0-9])"
    rf"|(?:MM|CM)({SKU_GROUP_PATTERN})(?![A-Z0-9])"
)

MATERIAL_BLACKLIST = {
    "S925",
    "S990",
    "S999",
    "AG925",
    "AG990",
    "AG999",
    "AU750",
    "AU916",
    "AU999",
    "G750",
    "G999",
    "PT900",
    "PT950",
    "PT990",
    "PT999",
    "PD950",
    "PD990",
    "PD999",
    "K9",
    "K10",
    "K14",
    "K18",
    "K22",
    "K24",
}


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""

    return unicodedata.normalize("NFKC", str(value)).upper()


def is_valid_sku_token(sku: str) -> bool:
    base_sku = sku.split("-", 1)[0]
    if base_sku in MATERIAL_BLACKLIST:
        return False

    return sum(char.isdigit() for char in base_sku) >= 3


def normalize_sku_group(group: str) -> str:
    sku_parts = re.sub(r"\s*\+\s*", "+", group).split("+")
    valid_parts = [sku for sku in sku_parts if is_valid_sku_token(sku)]
    return "+".join(valid_parts)


def extract_sku(name: object) -> str:
    """从商品名称提取货号；多个独立货号用逗号分隔，组合货号保留 +。"""
    normalized_name = normalize_text(name)
    if not normalized_name:
        return ""

    skus = []
    seen = set()

    for match in SKU_PATTERN.finditer(normalized_name):
        sku = normalize_sku_group(match.group(1) or match.group(2))
        if not sku or sku in seen:
            continue

        seen.add(sku)
        skus.append(sku)

    return ",".join(skus)


def excel_files(source_dir: Path) -> list[Path]:
    return sorted(
        file
        for file in [*source_dir.glob("*.xlsx"), *source_dir.glob("*.xls")]
        if not file.name.startswith("~$")
    )


def merge_source_files(source_dir: Path = SOURCE_DIR, output_path: Path = DEFAULT_MERGED_OUTPUT) -> pd.DataFrame:
    files = excel_files(source_dir)
    print(f"发现 {len(files)} 个 Excel 文件")

    all_data = []
    for file in files:
        print(f"处理: {file.name}")

        try:
            df = pd.read_excel(file)
            df.columns = df.columns.astype(str).str.strip()

            if PRODUCT_NAME_COLUMN not in df.columns:
                print("  跳过：无【商品名称】列")
                continue

            tmp = pd.DataFrame(
                {
                    PRODUCT_NAME_COLUMN: df[PRODUCT_NAME_COLUMN],
                    SKU_COLUMN: df[PRODUCT_NAME_COLUMN].map(extract_sku),
                }
            )
            all_data.append(tmp)
            print(f"  完成: {file.name}")
        except Exception as exc:
            print(f"  失败: {file.name} -> {exc}")

    result = (
        pd.concat(all_data, ignore_index=True)
        if all_data
        else pd.DataFrame(columns=[PRODUCT_NAME_COLUMN, SKU_COLUMN])
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_excel(output_path, index=False)
    print(f"总数据量: {len(result)}")
    print(f"已写入: {output_path}")

    return result


def default_extracted_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}_提取货号{input_path.suffix}")


def fill_sku_column(input_path: Path, output_path: Path | None = None) -> dict[str, int]:
    output_path = output_path or default_extracted_output_path(input_path)
    sheets = pd.read_excel(input_path, sheet_name=None)
    stats = {}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, sheet_data in sheets.items():
            sheet_data.columns = sheet_data.columns.astype(str).str.strip()

            if PRODUCT_NAME_COLUMN not in sheet_data.columns:
                sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)
                stats[sheet_name] = 0
                continue

            sheet_data[SKU_COLUMN] = sheet_data[PRODUCT_NAME_COLUMN].map(extract_sku)
            stats[sheet_name] = int(sheet_data[SKU_COLUMN].astype(bool).sum())
            sheet_data.to_excel(writer, sheet_name=sheet_name, index=False)

    for sheet_name, count in stats.items():
        print(f"{sheet_name}: 提取 {count} 行货号")
    print(f"已写入: {output_path}")

    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="解析商品名称中的货号")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR, help="原始 Excel 目录")
    parser.add_argument("--input", type=Path, default=None, help="已有 Excel 文件，填充/重算货号列")
    parser.add_argument("--output", type=Path, default=None, help="输出 Excel 文件")
    parser.add_argument(
        "--merge-source",
        action="store_true",
        help="合并 source-dir 下所有 Excel，并输出商品名称/货号两列",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.input:
        fill_sku_column(args.input.resolve(), args.output.resolve() if args.output else None)
        return

    output_path = args.output.resolve() if args.output else DEFAULT_MERGED_OUTPUT
    merge_source_files(args.source_dir.resolve(), output_path)


def test_extract_sku_from_common_product_names() -> None:
    assert extract_sku("沉香【佳哥专属】26 G16591-沉香鼓珠手串-11mm") == "G16591"
    assert extract_sku("【云上叙】手机贴-发六件-随形-V94970-13（东哥）") == "V94970"
    assert extract_sku("【玉总珠宝】崖柏斜挎-约7-8mm 多样性发一 CAN1400899") == "CAN1400899"
    assert extract_sku("【子楚专属】3 ZC00100027 S925银镶嵌和田玉戒指-多样性发一件") == "ZC00100027"
    assert extract_sku("【云上珠宝】小叶紫檀108佛珠多圈圆珠手串H200-6mm") == "H200"
    assert extract_sku("【云上叙】XP002-18K金淡水珍珠小米珠项链3mm（商城）") == "XP002"
    assert extract_sku("约33*13mmCAN3110492") == "CAN3110492"


def test_extract_sku_filters_material_and_size_names() -> None:
    assert extract_sku("S925银镶青金石耳钉-11.5*2mm") == ""
    assert extract_sku("18K金镶嵌极光吊坠-15mm") == ""
    assert extract_sku("老山檀手镯-多样性发一件-7x7mm") == ""
    assert extract_sku("AU750金项链 PT950铂金戒指 S999足银手链") == ""
    assert extract_sku("【云上雅岚】流萤丨18K绿松手链-多样性发一件-XYGD3089540-B") == "XYGD3089540"
    assert extract_sku("【云上雅岚】清浅丨18K蜜蜡耳钩-多样性发一件-XYGD343005-D") == "XYGD343005"


def test_extract_sku_keeps_plus_groups_and_removes_duplicates() -> None:
    assert extract_sku("V12452-S925银玛瑙吊坠 V12452-15（东哥）") == "V12452"
    assert extract_sku("组合 A1234+B5678 多样性发一件") == "A1234+B5678"
    assert extract_sku("组合 A1234 + B5678 多样性发一件") == "A1234+B5678"
    assert extract_sku("组合 A1234＋B5678 多样性发一件") == "A1234+B5678"


def test_extract_sku_keeps_letter_suffixes() -> None:
    assert extract_sku("【云上叙】淡水珍珠项链-多样性发一件-2.5mm V33535-F（商城）") == "V33535-F"
    assert extract_sku("【云上叙】S925银淡水珍珠项链-多样性发一件-3mm-V61416-M（甄选）") == "V61416-M"
    assert extract_sku("【云上叙】V2378-F-S925银淡水珍珠耳钩-多样性发一件-7mm") == "V2378-F"
    assert extract_sku("【小宝珠宝】27 T44378-S925银镶青金石耳钉-11.5*2mm") == "T44378"


if __name__ == "__main__":
    main()
