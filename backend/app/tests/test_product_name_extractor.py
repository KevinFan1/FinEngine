import re
from pathlib import Path

import pandas as pd

SOURCE_DIR = "/Users/kevinfan/Documents/04财务数据/26年4月动账资金/2026-04动账原数据"
OUTPUT_FILE = "./result/合并结果.xlsx"


def extract_sku(name):
    if pd.isna(name):
        return ""

    name = str(name).upper()

    # CAN + T 货号（支持 + 连接）
    pattern = r"(?:CAN\d+(?:\+CAN\d+)*|T\d{4,})"

    skus = re.findall(pattern, name)

    return ",".join(skus)


def load_all_files(source_dir: Path):
    files = list(source_dir.glob("*.xlsx")) + list(source_dir.glob("*.xls"))

    print(f"发现 {len(files)} 个Excel文件")

    all_data = []

    for file in files:
        print(f"处理: {file.name}")

        try:
            df = pd.read_excel(file)

            df.columns = df.columns.astype(str).str.strip()

            if "商品名称" not in df.columns:
                print("  ❌ 跳过：无【商品名称】列")
                continue

            tmp = pd.DataFrame({"商品名称": df["商品名称"], "货号": df["商品名称"].apply(extract_sku)})

            all_data.append(tmp)

            print(f"  ✅ 完成: {file.name}")

        except Exception as e:
            print(f"  ❌ 失败: {file.name} -> {e}")

    if not all_data:
        return pd.DataFrame(columns=["商品名称", "货号"])

    return pd.concat(all_data, ignore_index=True)


def main():
    source_dir = Path(SOURCE_DIR)
    output_path = Path(OUTPUT_FILE)

    output_path.parent.mkdir(exist_ok=True)

    result = load_all_files(source_dir)

    print(f"总数据量: {len(result)}")

    # 输出合并Excel
    result.to_excel(output_path, index=False)

    print(f"✅ 合并完成: {output_path}")


if __name__ == "__main__":
    main()
