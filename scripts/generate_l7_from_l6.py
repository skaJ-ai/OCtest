#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

SRC = Path("docs/hr_l6_apqc_master_library_v2.1_custom.json")

def main() -> None:
    obj = json.loads(SRC.read_text(encoding="utf-8"))
    library = obj.get("library", [])

    # stable order by l6_id numeric
    def l6num(item: dict) -> int:
        try:
            return int(str(item.get("l6_id", "")).split("-")[-1])
        except Exception:
            return 10**9

    library.sort(key=l6num)

    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for item in library:
        groups[(item.get("l3", ""), item.get("l4", ""), item.get("l5", ""))].append(item)

    for _, items in groups.items():
        for i, item in enumerate(items):
            pred = [items[i - 1]["l6_id"]] if i > 0 else []
            succ = [items[i + 1]["l6_id"]] if i < len(items) - 1 else []
            item["predecessors"] = pred
            item["successors"] = succ
            item["entry_condition"] = "" if i == 0 else "선행 L6 완료"

    obj["library"] = library
    obj["graph_enriched"] = True
    SRC.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"enriched={len(library)}")

if __name__ == "__main__":
    main()
