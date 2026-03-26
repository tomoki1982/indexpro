import unittest

from app.indexpro import load_indexpro_fixture
from app.settings import INDEXPRO_FIXTURE_PATH


class IndexProFixtureTests(unittest.TestCase):
    def test_fixture_contains_products_and_distributors(self) -> None:
        result = load_indexpro_fixture(INDEXPRO_FIXTURE_PATH, "オムロン")
        self.assertEqual(len(result.manufacturers), 1)
        self.assertGreaterEqual(len(result.products), 1)
        self.assertGreaterEqual(len(result.distributors), 1)
        self.assertIn(
            "オムロン 制御機器・FAシステム",
            result.distributors[0].handling_manufacturers,
        )


if __name__ == "__main__":
    unittest.main()
