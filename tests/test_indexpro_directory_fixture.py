import unittest

from app.indexpro_directory import load_directory_fixture
from app.settings import INDEXPRO_DIRECTORY_FIXTURE_PATH


class IndexProDirectoryFixtureTests(unittest.TestCase):
    def test_directory_fixture_has_expected_sections(self) -> None:
        result = load_directory_fixture(INDEXPRO_DIRECTORY_FIXTURE_PATH)
        self.assertGreaterEqual(len(result.manufacturers), 1)
        self.assertGreaterEqual(len(result.distributors), 1)
        self.assertGreaterEqual(len(result.handlings), 1)
        self.assertGreaterEqual(len(result.relations), 1)
        self.assertEqual(result.manufacturers[0].mcid, "1593")
        self.assertEqual(
            result.distributors[0].location_url,
            "https://www.indexpro.co.jp/distributor/location?did=774",
        )
        self.assertEqual(
            result.distributors[0].online_sales_url,
            "https://www.indexpro.co.jp/distributor/onlinesales?did=774",
        )
        self.assertEqual(result.distributors[0].source_category, "オンライン販売")
        self.assertEqual(result.relations[0].relation_category, "オンライン販売")


if __name__ == "__main__":
    unittest.main()
