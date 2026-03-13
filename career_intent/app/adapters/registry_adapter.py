from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List


class FunctionRegistryAdapter:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)

    def load(self) -> List[Dict[str, str]]:
        if not self.registry_path.exists():
            return []
        with self.registry_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return [dict(row) for row in reader]

    def search(self, keyword: str) -> List[Dict[str, str]]:
        needle = keyword.strip().lower()
        rows = self.load()
        if not needle:
            return rows
        out: List[Dict[str, str]] = []
        for row in rows:
            blob = " ".join(str(value) for value in row.values()).lower()
            if needle in blob:
                out.append(row)
        return out

    def print_available(self, keyword: str = "") -> List[str]:
        matches = self.search(keyword)
        names = sorted({row.get("qualified_name", "") for row in matches if row.get("qualified_name")})
        for name in names:
            print(name)
        return names
