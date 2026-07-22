"""
Unit tests for deficiency utility functions.
"""
from datetime import date, datetime
from django.test import TestCase

from apps.deficiencies.utility import normalize_date
from .test_config import DeficiencyTestCase


class NormalizeDateTest(DeficiencyTestCase):
    """Test normalize_date utility function"""

    def test_normalize_date_with_none(self):
        """Test normalize_date returns None for None input"""
        result = normalize_date(None)
        self.assertIsNone(result)

    def test_normalize_date_with_empty_string(self):
        """Test normalize_date returns empty string for empty input"""
        result = normalize_date('')
        self.assertEqual(result, '')

    def test_normalize_date_with_whitespace_string(self):
        """Test normalize_date handles whitespace strings"""
        result = normalize_date('   ')
        self.assertEqual(result, '   ')

    def test_normalize_date_yyyy_mm_dd_format(self):
        """Test normalize_date with YYYY-MM-DD format (Django standard)"""
        result = normalize_date('2025-06-20')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_mm_dd_yyyy_format(self):
        """Test normalize_date with MM/DD/YYYY format (US format)"""
        result = normalize_date('06/20/2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_dd_mm_yyyy_format(self):
        """Test normalize_date with DD/MM/YYYY format (UK/Australian)"""
        result = normalize_date('20/06/2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_dd_mm_yyyy_dashes(self):
        """Test normalize_date with DD-MM-YYYY format (European)"""
        result = normalize_date('20-06-2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_dd_mmm_yyyy_format(self):
        """Test normalize_date with DD-MMM-YYYY format (Oracle legacy)"""
        result = normalize_date('20-JUN-2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_dd_mmm_yyyy_lowercase(self):
        """Test normalize_date with lowercase month abbreviation"""
        result = normalize_date('20-jun-2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_dd_mmm_yyyy_mixed_case(self):
        """Test normalize_date with mixed case month abbreviation"""
        result = normalize_date('20-Jun-2025')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_with_leading_zero(self):
        """Test normalize_date handles leading zeros correctly"""
        result = normalize_date('06/03/2025')
        self.assertEqual(result, date(2025, 6, 3))

    def test_normalize_date_with_year_2024(self):
        """Test normalize_date works with 2024 dates"""
        result = normalize_date('15/12/2024')
        self.assertEqual(result, date(2024, 12, 15))

    def test_normalize_date_with_year_2026(self):
        """Test normalize_date works with 2026 dates"""
        result = normalize_date('2026-01-31')
        self.assertEqual(result, date(2026, 1, 31))

    def test_normalize_date_all_months_abbreviations(self):
        """Test normalize_date handles all month abbreviations"""
        test_cases = [
            ('01-JAN-2025', date(2025, 1, 1)),
            ('01-FEB-2025', date(2025, 2, 1)),
            ('01-MAR-2025', date(2025, 3, 1)),
            ('01-APR-2025', date(2025, 4, 1)),
            ('01-MAY-2025', date(2025, 5, 1)),
            ('01-JUN-2025', date(2025, 6, 1)),
            ('01-JUL-2025', date(2025, 7, 1)),
            ('01-AUG-2025', date(2025, 8, 1)),
            ('01-SEP-2025', date(2025, 9, 1)),
            ('01-OCT-2025', date(2025, 10, 1)),
            ('01-NOV-2025', date(2025, 11, 1)),
            ('01-DEC-2025', date(2025, 12, 1)),
        ]
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = normalize_date(input_date)
                self.assertEqual(result, expected)

    def test_normalize_date_with_date_object(self):
        """Test normalize_date returns date portion for datetime object"""
        input_datetime = datetime(2025, 6, 20, 15, 30, 0)
        result = normalize_date(input_datetime)
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_with_date_object_input(self):
        """Test normalize_date returns same value for date object"""
        input_date = date(2025, 6, 20)
        result = normalize_date(input_date)
        self.assertEqual(result, input_date)

    def test_normalize_date_with_whitespace_yyyy_mm_dd(self):
        """Test normalize_date handles whitespace around YYYY-MM-DD"""
        result = normalize_date(' 2025-06-20 ')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_with_whitespace_dd_mm_yyyy(self):
        """Test normalize_date handles whitespace around DD/MM/YYYY"""
        result = normalize_date(' 20/06/2025 ')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_february_29_leap_year(self):
        """Test normalize_date handles leap year dates correctly"""
        result = normalize_date('29/02/2024')
        self.assertEqual(result, date(2024, 2, 29))

    def test_normalize_date_invalid_february_29_non_leap_year(self):
        """Test normalize_date returns input for invalid Feb 29 date"""
        # 2023 is not a leap year
        result = normalize_date('29/02/2023')
        # Should return the input since it can't parse
        self.assertEqual(result, '29/02/2023')

    def test_normalize_date_invalid_string(self):
        """Test normalize_date returns invalid string unchanged"""
        result = normalize_date('invalid-date-string')
        self.assertEqual(result, 'invalid-date-string')

    def test_normalize_date_partial_date(self):
        """Test normalize_date returns partial dates unchanged"""
        result = normalize_date('2025-06')
        self.assertEqual(result, '2025-06')

    def test_normalize_date_with_extra_characters(self):
        """Test normalize_date returns strings with extra characters unchanged"""
        result = normalize_date('20-JUN-2025T00:00:00')
        self.assertEqual(result, '20-JUN-2025T00:00:00')

    def test_normalize_date_us_vs_uk_format_ambiguous_date(self):
        """Test behavior with ambiguous dates (01/02/2025)"""
        # Should parse as MM/DD/YYYY (US format comes before UK in format list)
        result = normalize_date('01/02/2025')
        # This will be parsed as January 2nd (US format)
        self.assertEqual(result, date(2025, 1, 2))

    def test_normalize_date_single_digit_day_or_month(self):
        """Test normalize_date with single digit day/month"""
        result = normalize_date('1/6/2025')
        self.assertEqual(result, date(2025, 1, 6))

    def test_normalize_date_double_digit_day_and_month(self):
        """Test normalize_date with double digit day and month"""
        result = normalize_date('12/12/2025')
        self.assertEqual(result, date(2025, 12, 12))

    def test_normalize_date_year_2000(self):
        """Test normalize_date handles year 2000 correctly"""
        result = normalize_date('01/01/2000')
        self.assertEqual(result, date(2000, 1, 1))

    def test_normalize_date_year_2099(self):
        """Test normalize_date handles future years like 2099"""
        result = normalize_date('31/12/2099')
        self.assertEqual(result, date(2099, 12, 31))

    def test_normalize_date_preserves_date_object(self):
        """Test normalize_date doesn't modify original date objects"""
        original = date(2025, 6, 20)
        result = normalize_date(original)
        self.assertEqual(result, original)
        # Ensure it's the same type
        self.assertIsInstance(result, date)

    def test_normalize_date_format_priority(self):
        """Test that formats are tried in the correct priority order"""
        # YYYY-MM-DD should work first
        result1 = normalize_date('2025-06-20')
        self.assertEqual(result1, date(2025, 6, 20))

        # MM/DD/YYYY should work second
        result2 = normalize_date('06/20/2025')
        self.assertEqual(result2, date(2025, 6, 20))

        # DD/MM/YYYY should work third
        result3 = normalize_date('20/06/2025')
        self.assertEqual(result3, date(2025, 6, 20))

        # DD-MM-YYYY should work fourth
        result4 = normalize_date('20-06-2025')
        self.assertEqual(result4, date(2025, 6, 20))

        # DD-MMM-YYYY should work last
        result5 = normalize_date('20-JUN-2025')
        self.assertEqual(result5, date(2025, 6, 20))


class UtilityEdgeCasesTest(DeficiencyTestCase):
    """Test edge cases for utility functions"""

    def test_normalize_date_very_long_string(self):
        """Test normalize_date handles very long strings"""
        long_string = 'a' * 1000
        result = normalize_date(long_string)
        self.assertEqual(result, long_string)

    def test_normalize_date_special_characters(self):
        """Test normalize_date handles special characters"""
        result = normalize_date('@#$%^&*()')
        self.assertEqual(result, '@#$%^&*()')

    def test_normalize_date_with_newlines(self):
        """Test normalize_date handles strings with newlines"""
        result = normalize_date('2025-06-20\n')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_with_tabs(self):
        """Test normalize_date handles strings with tabs"""
        result = normalize_date('\t2025-06-20\t')
        self.assertEqual(result, date(2025, 6, 20))

    def test_normalize_date_unicode_characters(self):
        """Test normalize_date handles unicode in invalid strings"""
        result = normalize_date('🎂🎉')
        self.assertEqual(result, '🎂🎉')

    def test_normalize_date_zero_month_or_day(self):
        """Test normalize_date handles zero values appropriately"""
        # Zero month should fail to parse
        result = normalize_date('00/06/2025')
        self.assertEqual(result, '00/06/2025')

    def test_normalize_date_negative_numbers(self):
        """Test normalize_date handles negative numbers"""
        result = normalize_date('-1/-1/-2025')
        self.assertEqual(result, '-1/-1/-2025')
