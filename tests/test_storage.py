# -*- coding: utf-8 -*-
import unittest
import sys
import os

# Ensure src module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage import DatabaseManager

class TestStorage(unittest.TestCase):
    
    def test_parse_sniper_value(self):
        """Parse sniper point values."""
        
        # 1. Plain numeric values
        self.assertEqual(DatabaseManager._parse_sniper_value(100), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value(100.5), 100.5)
        self.assertEqual(DatabaseManager._parse_sniper_value("100"), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("100.5"), 100.5)
        
        # 2. KR/US price text with explicit currency markers
        self.assertEqual(DatabaseManager._parse_sniper_value("100원 부근 매수 고려"), 100.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("price: $100.5"), 100.5)
        
        # 3. Regression: MA indicator numbers must not be extracted
        text_bug = "MA5 데이터 회복 후 MA5 재돌파와 이격률 2% 미만 구간에서 100원 고려"
        self.assertEqual(DatabaseManager._parse_sniper_value(text_bug), 100.0)
        
        # 4. More noisy input cases
        text_complex = "MA10 is 20.5, consider buying near 30원"
        self.assertEqual(DatabaseManager._parse_sniper_value(text_complex), 30.0)
        
        self.assertEqual(DatabaseManager._parse_sniper_value("30원"), 30.0)
        
        # Multiple numbers before the currency marker should use the latest valid price.
        self.assertEqual(DatabaseManager._parse_sniper_value("MA5 10 20원"), 20.0)
        
        # 5. Fallback: no currency marker; extracts the last non-MA number.
        self.assertEqual(DatabaseManager._parse_sniper_value("102.10-103.00(MA5 near)"), 103.0)
        self.assertEqual(DatabaseManager._parse_sniper_value("97.62-98.50(MA10 near)"), 98.5)
        self.assertEqual(DatabaseManager._parse_sniper_value("93.40 below(MA20 support)"), 93.4)
        self.assertEqual(DatabaseManager._parse_sniper_value("108.00-110.00(previous resistance)"), 110.0)

        # 6. Invalid input
        self.assertIsNone(DatabaseManager._parse_sniper_value(None))
        self.assertIsNone(DatabaseManager._parse_sniper_value(""))
        self.assertIsNone(DatabaseManager._parse_sniper_value("no numbers"))
        self.assertIsNone(DatabaseManager._parse_sniper_value("MA5 without price"))

        # 7. Regression: technical indicator numbers inside parentheses are ignored.
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.52-1.53 (MA5/10 pullback area)"), 10.0)
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.55-1.56(MA5/M20 support)"), 20.0)
        self.assertNotEqual(DatabaseManager._parse_sniper_value("1.49-1.50(MA60 stabilization)"), 60.0)
        # Verify that the parsed value remains inside the price range.
        self.assertIn(DatabaseManager._parse_sniper_value("1.52-1.53 (MA5/10 pullback area)"), [1.52, 1.53])
        self.assertIn(DatabaseManager._parse_sniper_value("1.55-1.56(MA5/M20 support)"), [1.55, 1.56])
        self.assertIn(DatabaseManager._parse_sniper_value("1.49-1.50(MA60 stabilization)"), [1.49, 1.50])

if __name__ == '__main__':
    unittest.main()
