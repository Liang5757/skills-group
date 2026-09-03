import unittest

from huijin_tracker.entities import match_entity
from huijin_tracker.models import Attribution


class EntityTests(unittest.TestCase):
    def test_exact_entities_and_named_plan(self):
        cases = {
            "中央汇金投资有限责任公司": Attribution.DIRECT,
            "Central Huijin Investment Ltd.": Attribution.DIRECT,
            "中央汇金资产管理有限责任公司": Attribution.ASSET_MGMT,
            "中国证券金融股份有限公司": Attribution.RELATED_CONTROLLED,
            "易方达基金-中央汇金资产管理有限责任公司-易方达基金-汇金资管单一资产管理计划": Attribution.NAMED_PLAN,
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(match_entity(name).attribution, expected)

    def test_ambiguous_short_name_is_not_matched(self):
        self.assertEqual(match_entity("汇金公司").attribution, Attribution.UNKNOWN)
        self.assertEqual(match_entity("北京汇金投资有限公司").attribution, Attribution.UNKNOWN)

    def test_different_named_plans_do_not_share_an_identity(self):
        first = match_entity(
            "易方达基金-中央汇金资产管理有限责任公司-易方达基金-汇金资管单一资产管理计划"
        )
        second = match_entity(
            "华夏基金-中央汇金资产管理有限责任公司-华夏基金-汇金资管单一资产管理计划"
        )
        self.assertNotEqual(first.canonical_key, second.canonical_key)
        self.assertTrue(first.canonical_key.startswith("huijin_named_plan:"))


if __name__ == "__main__":
    unittest.main()
