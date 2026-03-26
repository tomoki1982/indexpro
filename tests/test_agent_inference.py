import unittest

import pandas as pd

from app.agent_inference import (
    AGENT_TYPE,
    RETAILER_TYPE,
    get_candidate_agents_by_manufacturer_and_retailer,
)


class AgentInferenceTests(unittest.TestCase):
    def test_get_candidate_agents_by_manufacturer_and_retailer_returns_ranked_agents(self) -> None:
        relations = pd.DataFrame(
            [
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店X", "relation_category": AGENT_TYPE},
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店Y", "relation_category": AGENT_TYPE},
                {"manufacturer_name": "メーカーA", "distributor_name": "取扱店P", "relation_category": RETAILER_TYPE},
                {"manufacturer_name": "メーカーB", "distributor_name": "代理店Y", "relation_category": AGENT_TYPE},
                {"manufacturer_name": "メーカーB", "distributor_name": "取扱店P", "relation_category": RETAILER_TYPE},
                {"manufacturer_name": "メーカーC", "distributor_name": "代理店X", "relation_category": AGENT_TYPE},
                {"manufacturer_name": "メーカーC", "distributor_name": "取扱店P", "relation_category": RETAILER_TYPE},
            ]
        )
        handlings = pd.DataFrame(
            [
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーC"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーA"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーB"},
                {"distributor_name": "代理店Y", "handling_manufacturer_name": "メーカーD"},
            ]
        )

        results = get_candidate_agents_by_manufacturer_and_retailer(
            " メーカーA ",
            "取扱店P",
            relations,
            handlings,
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].rank, 1)
        self.assertEqual(results[0].agent_name, "代理店X")
        self.assertAlmostEqual(results[0].score, 2 / 3)
        self.assertEqual(results[0].matched_related_manufacturer_count, 2)
        self.assertEqual(results[0].retailer_related_manufacturer_count, 3)
        self.assertEqual(results[0].agent_total_handling_count, 2)
        self.assertEqual(results[0].evidence_manufacturers, ["メーカーA", "メーカーC"])

        self.assertEqual(results[1].rank, 2)
        self.assertEqual(results[1].agent_name, "代理店Y")
        self.assertAlmostEqual(results[1].score, 2 / 3)
        self.assertEqual(results[1].agent_total_handling_count, 3)

    def test_get_candidate_agents_by_manufacturer_and_retailer_returns_empty_when_no_match(self) -> None:
        relations = pd.DataFrame(
            [
                {"manufacturer_name": "メーカーA", "distributor_name": "代理店X", "relation_category": AGENT_TYPE},
                {"manufacturer_name": "メーカーA", "distributor_name": "取扱店P", "relation_category": RETAILER_TYPE},
            ]
        )
        handlings = pd.DataFrame(
            [{"distributor_name": "代理店X", "handling_manufacturer_name": "メーカーA"}]
        )

        results = get_candidate_agents_by_manufacturer_and_retailer(
            "メーカーA",
            "存在しない取扱店",
            relations,
            handlings,
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
