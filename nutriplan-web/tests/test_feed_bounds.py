"""Tests for ingredient inclusion bounds and fixed inclusions."""
import unittest

from services.native_ration import available_feeds, build_feed


class CatalogBoundsTests(unittest.TestCase):
    def test_catalog_exposes_numeric_bounds(self):
        feeds = available_feeds()
        self.assertTrue(feeds)
        for feed in feeds:
            self.assertIsInstance(feed['lower_limit'], float)
            self.assertIsInstance(feed['limit'], float)
            self.assertGreaterEqual(feed['limit'], feed['lower_limit'])


class BuildFeedBoundsTests(unittest.TestCase):
    def _item(self, **overrides):
        item = {
            'rufas_id': 51,
            'price_as_fed': 0.35,
            'minimum_kg_dm': 0,
            'maximum_kg_dm': 10,
        }
        item.update(overrides)
        return item

    def test_fixed_inclusion_keeps_equal_bounds(self):
        feed = build_feed(self._item(minimum_kg_dm=2.5, maximum_kg_dm=2.5))
        self.assertAlmostEqual(feed.lower_limit, 2.5)
        self.assertAlmostEqual(feed.limit, 2.5)

    def test_maximum_below_minimum_is_rejected(self):
        with self.assertRaises(ValueError):
            build_feed(self._item(minimum_kg_dm=5, maximum_kg_dm=2))

    def test_negative_bounds_are_rejected(self):
        with self.assertRaises(ValueError):
            build_feed(self._item(minimum_kg_dm=-1, maximum_kg_dm=10))


if __name__ == '__main__':
    unittest.main()
