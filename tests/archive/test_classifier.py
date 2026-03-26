from datetime import datetime
import unittest

from app.classifier import classify_region, extract_companies
from app.models import RawPage


class ClassifierTests(unittest.TestCase):
    def test_extract_companies_detects_distributor(self) -> None:
        page = RawPage(
            manufacturer_name="オムロン",
            url="https://example.com",
            title="オムロン 公式代理店一覧",
            body="オムロン株式会社の代理店として高信頼代理店株式会社を掲載しています。",
            domain="omron.example",
            fetched_at=datetime.now(),
        )
        items = extract_companies([page])
        self.assertTrue(items)
        self.assertEqual(items[0].company_name, "高信頼代理店株式会社")
        self.assertEqual(items[0].estimated_stage, "一次代理店")

    def test_classify_region_prefers_kanto(self) -> None:
        self.assertEqual(classify_region("東京都に営業所があります。", "東京本社"), "関東")


if __name__ == "__main__":
    unittest.main()
