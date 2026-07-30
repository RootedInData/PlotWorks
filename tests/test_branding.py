from __future__ import annotations

import unittest
from pathlib import Path


class BrandingTests(unittest.TestCase):
    def test_legacy_brand_name_is_absent_from_text_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        forbidden = ("Data" + " Analysis" + " Agency", "Data" + "_analysis" + "_agency", "data" + "_analysis" + "_agency")
        hits: list[str] = []
        for path in root.rglob("*"):
            if path.resolve() == Path(__file__).resolve():
                continue
            if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".gif", ".pdf", ".db", ".pyc"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for term in forbidden:
                if term in text:
                    hits.append(f"{path.relative_to(root)}: {term}")
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
