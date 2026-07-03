from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = APP_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from star_manager.core.card_parser import (  # noqa: E402
    extract_auto_resolver_records_from_card,
    is_ais_card,
)


DEFAULT_INPUT = Path("test/hs2/UserData/chara")
KIND_LABELS = {
    "8": "身体彩绘布局",
    "110": "男性脸模",
    "111": "男性脸部肌肤",
    "112": "男性脸部细节",
    "121": "胡子",
    "131": "男性身体肌肤",
    "132": "男性身体细节",
    "133": "男性身体晒痕",
    "140": "男 mod / 上衣",
    "141": "男 mod / 下衣",
    "144": "男 mod / 手套",
    "147": "男 mod / 鞋子",
    "210": "脸模",
    "211": "脸部肌肤",
    "212": "脸部皱纹 / 脸部细节",
    "231": "身体肌肤",
    "232": "肉感",
    "233": "女性身体晒痕",
    "240": "女 mod / 上衣",
    "241": "女 mod / 下衣",
    "242": "女 mod / 内衣",
    "243": "女 mod / 内裤",
    "244": "女 mod / 手套",
    "245": "女 mod / 裤袜",
    "246": "女 mod / 袜子",
    "247": "女 mod / 鞋子",
    "300": "头发 / 后发",
    "301": "头发 / 前发",
    "302": "头发 / 鬓发",
    "303": "头发 / 侧发",
    "313": "人体彩绘",
    "314": "眉毛",
    "315": "睫毛",
    "316": "眼影",
    "317": "美瞳 / 眼睛种类",
    "319": "眼睛高光",
    "318": "瞳孔 / 黑眼",
    "320": "腮红",
    "322": "口红",
    "323": "痣 / 雀斑",
    "334": "乳头",
    "335": "阴毛",
    "348": "图案",
    "351": "饰品 mod / 头部",
    "352": "饰品 mod / 耳朵",
    "353": "饰品 mod / 眼镜",
    "354": "饰品 mod / 脸部",
    "355": "饰品 mod / 脖子",
    "356": "饰品 mod / 肩部",
    "357": "饰品 mod / 胸部",
    "358": "饰品 mod / 腰部",
    "359": "饰品 mod / 后背",
    "360": "饰品 mod / 胳膊",
    "361": "饰品 mod / 手部",
    "362": "饰品 mod / 脚",
    "363": "饰品 mod / 腹部下",
}


def collect_png_paths(inputs: list[Path], recursive: bool) -> list[Path]:
    paths: list[Path] = []
    for path in inputs:
        resolved = path.resolve()
        if resolved.is_file() and resolved.suffix.lower() == ".png":
            paths.append(resolved)
        elif resolved.is_dir():
            pattern = "**/*.png" if recursive else "*.png"
            paths.extend(item.resolve() for item in resolved.glob(pattern) if item.is_file())
    return sorted(set(paths))


def summarize(paths: list[Path], limit: int) -> dict[str, Any]:
    scanned = 0
    ais_cards = 0
    failed_cards: list[dict[str, str]] = []
    categories: dict[str, dict[str, Any]] = {}
    property_pairs: dict[tuple[str, str], dict[str, Any]] = {}

    selected_paths = paths[:limit] if limit > 0 else paths
    for path in selected_paths:
        scanned += 1
        try:
            if not is_ais_card(str(path)):
                continue
            ais_cards += 1
            records = extract_auto_resolver_records_from_card(str(path))
        except Exception as exc:  # noqa: BLE001
            failed_cards.append({"path": str(path), "error": str(exc)})
            continue

        for record in records:
            category = str(record.get("CategoryNo") or "").strip()
            if not category:
                continue
            prop = str(record.get("Property") or "").strip()
            slot = str(record.get("Slot") or "").strip()
            local_slot = str(record.get("LocalSlot") or "").strip()
            mod_id = str(record.get("ModID") or "").strip()
            name = str(record.get("Name") or "").strip()

            category_row = categories.setdefault(
                category,
                {
                    "category_no": category,
                    "label": KIND_LABELS.get(category, "未知"),
                    "record_count": 0,
                    "card_count": 0,
                    "cards": set(),
                    "properties": set(),
                    "examples": [],
                },
            )
            category_row["record_count"] += 1
            category_row["cards"].add(str(path))
            category_row["properties"].add(prop)
            if len(category_row["examples"]) < 5:
                category_row["examples"].append(
                    {
                        "card": str(path),
                        "property": prop,
                        "slot": slot,
                        "local_slot": local_slot,
                        "mod_id": mod_id,
                        "name": name,
                    }
                )

            pair_key = (category, prop)
            pair_row = property_pairs.setdefault(
                pair_key,
                {
                    "category_no": category,
                    "property": prop,
                    "label": KIND_LABELS.get(category, "未知"),
                    "record_count": 0,
                    "card_count": 0,
                    "cards": set(),
                    "examples": [],
                },
            )
            pair_row["record_count"] += 1
            pair_row["cards"].add(str(path))
            if len(pair_row["examples"]) < 5:
                pair_row["examples"].append(
                    {
                        "card": str(path),
                        "slot": slot,
                        "local_slot": local_slot,
                        "mod_id": mod_id,
                        "name": name,
                    }
                )

    category_rows = []
    for row in categories.values():
        cards = sorted(row.pop("cards"))
        properties = sorted(item for item in row.pop("properties") if item)
        row["card_count"] = len(cards)
        row["cards"] = cards
        row["properties"] = properties
        category_rows.append(row)

    pair_rows = []
    for row in property_pairs.values():
        cards = sorted(row.pop("cards"))
        row["card_count"] = len(cards)
        row["cards"] = cards
        pair_rows.append(row)

    category_rows.sort(key=lambda item: numeric_key(item["category_no"]))
    pair_rows.sort(key=lambda item: (numeric_key(item["category_no"]), item["property"]))

    return {
        "files_scanned": scanned,
        "ais_cards": ais_cards,
        "failed_cards": failed_cards,
        "category_count": len(category_rows),
        "property_pair_count": len(pair_rows),
        "categories": category_rows,
        "property_pairs": pair_rows,
    }


def numeric_key(value: str) -> tuple[int, str]:
    try:
        return int(value), value
    except ValueError:
        return 10**9, value


def print_markdown(summary: dict[str, Any]) -> None:
    print(f"files_scanned: {summary['files_scanned']}")
    print(f"ais_cards: {summary['ais_cards']}")
    print(f"category_count: {summary['category_count']}")
    print(f"property_pair_count: {summary['property_pair_count']}")
    if summary["failed_cards"]:
        print(f"failed_cards: {len(summary['failed_cards'])}")
    print()

    print("## CategoryNo 汇总")
    print()
    print("| CategoryNo | 部位/类别 | 记录数 | 卡片数 | Property | 示例 |")
    print("| ---: | --- | ---: | ---: | --- | --- |")
    for row in summary["categories"]:
        props = "<br>".join(f"`{item}`" for item in row["properties"]) or "-"
        example = row["examples"][0] if row["examples"] else {}
        example_text = format_example(example)
        print(
            f"| {row['category_no']} | {row['label']} | {row['record_count']} | "
            f"{row['card_count']} | {props} | {example_text} |"
        )

    print()
    print("## CategoryNo + Property 一一对应")
    print()
    print("| CategoryNo | Property | 部位/类别 | 记录数 | 卡片数 | 示例 |")
    print("| ---: | --- | --- | ---: | ---: | --- |")
    for row in summary["property_pairs"]:
        example = row["examples"][0] if row["examples"] else {}
        print(
            f"| {row['category_no']} | `{row['property']}` | {row['label']} | "
            f"{row['record_count']} | {row['card_count']} | {format_example(example)} |"
        )


def format_example(example: dict[str, Any]) -> str:
    if not example:
        return "-"
    card = Path(str(example.get("card") or "")).name
    mod_id = example.get("mod_id") or "-"
    name = example.get("name") or "-"
    slot = example.get("slot") or "-"
    return f"{card}<br>`{mod_id}`<br>{name}<br>slot={slot}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize HS2/AIS character-card CategoryNo and Property mappings."
    )
    parser.add_argument("paths", nargs="*", type=Path, help="PNG files or directories.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum PNG files to scan. 0 means no limit.")
    parser.add_argument("--no-recursive", dest="recursive", action="store_false")
    parser.add_argument("--json", type=Path, help="Write JSON summary to this path.")
    args = parser.parse_args()

    inputs = args.paths or [DEFAULT_INPUT]
    paths = collect_png_paths(inputs, args.recursive)
    summary = summarize(paths, args.limit)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print_markdown(summary)
    if args.json:
        print()
        print(f"JSON written to: {args.json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
