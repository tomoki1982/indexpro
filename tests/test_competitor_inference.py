import unittest

import pandas as pd

from app.competitor_inference import get_competitor_candidates


class CompetitorInferenceTests(unittest.TestCase):
    def test_get_competitor_candidates_returns_ranked_results(self) -> None:
        relations = pd.DataFrame(
            [
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店X", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店Y", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店Z", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーB", "distributor_name": "代理店X", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーB", "distributor_name": "代理店Y", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーC", "distributor_name": "代理店Y", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーD", "distributor_name": "代理店Q", "relation_category": "代理店"},
            ]
        )
        handlings = pd.DataFrame(
            [
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーB"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーB"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーC"},
                {"distributor_name": "代理店Z", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店Q", "handling_manufacturer_name": "メーカーD"},
            ]
        )

        results = get_competitor_candidates(" メーカーA ", relations, handlings)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].rank, 1)
        self.assertEqual(results[0].candidate_manufacturer_name, "メーカーB")
        self.assertEqual(results[0].common_distributor_count, 2)
        self.assertEqual(results[0].base_manufacturer_distributor_count, 3)
        self.assertEqual(results[0].candidate_manufacturer_distributor_count, 2)
        self.assertAlmostEqual(results[0].basic_score, 2 / 3)
        self.assertAlmostEqual(results[0].similarity_score, 2 / 3)
        self.assertEqual(results[0].common_distributors, ["代理店X", "代理店Y"])

        self.assertEqual(results[1].rank, 2)
        self.assertEqual(results[1].candidate_manufacturer_name, "メーカーC")
        self.assertEqual(results[1].common_distributor_count, 1)
        self.assertAlmostEqual(results[1].basic_score, 1 / 3)

    def test_get_competitor_candidates_excludes_large_distributors(self) -> None:
        relations = pd.DataFrame(
            [
                {"manufacturer_name": "メーカーA", "distributor_name": "大型代理店", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店X", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーB", "distributor_name": "大型代理店", "relation_category": "代理店"},
                {"manufacturer_name": "メーカーB", "distributor_name": "代理店X", "relation_category": "代理店"},
            ]
        )
        handlings = pd.DataFrame(
            [
                {"distributor_name": "大型代理店", "handling_manufacturer_name": f"メーカー{i}"}
                for i in range(40)
            ]
            + [
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーB"},
            ]
        )

        results = get_competitor_candidates(
            "メーカーA",
            relations,
            handlings,
            max_handling_count=30,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].candidate_manufacturer_name, "メーカーB")
        self.assertEqual(results[0].common_distributor_count, 1)
        self.assertEqual(results[0].common_distributors, ["代理店X"])


if __name__ == "__main__":
    unittest.main()
