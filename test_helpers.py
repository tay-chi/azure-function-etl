# Unit tests for helper functions
# Run with: pytest test_helpers.py -v

import pytest
from country_codes import get_country_code
from data_helpers import get_json_value, format_phone, format_date_to_iso, clean_text


# ============================================================
# TESTS FOR country_codes.py
# ============================================================

class TestGetCountryCode:
    """Tests for the get_country_code function"""
    
    def test_full_country_name_uppercase(self):
        """Should convert full country name to 2-letter code"""
        assert get_country_code("UNITED STATES") == "US"
        assert get_country_code("CANADA") == "CA"
        assert get_country_code("UNITED KINGDOM") == "GB"
    
    def test_full_country_name_lowercase(self):
        """Should handle lowercase input"""
        assert get_country_code("united states") == "US"
        assert get_country_code("canada") == "CA"
    
    def test_full_country_name_mixed_case(self):
        """Should handle mixed case input"""
        assert get_country_code("United States") == "US"
        assert get_country_code("Canada") == "CA"
    
    def test_empty_string_returns_default(self):
        """Should return 'US' for empty string"""
        assert get_country_code("") == "US"
    
    def test_none_returns_default(self):
        """Should return 'US' for None input"""
        assert get_country_code(None) == "US"
    
    def test_two_letter_code_passthrough(self):
        """Should pass through if already a 2-letter code"""
        assert get_country_code("US") == "US"
        assert get_country_code("CA") == "CA"
        assert get_country_code("GB") == "GB"
    
    def test_unknown_country_returns_default(self):
        """Should return 'US' for unknown country names"""
        assert get_country_code("MADE UP COUNTRY") == "US"
        assert get_country_code("XYZ") == "US"
    
    def test_usa_variations(self):
        """Should handle common USA variations"""
        assert get_country_code("USA") == "US"
        assert get_country_code("UNITED STATES OF AMERICA") == "US"


# ============================================================
# TESTS FOR data_helpers.py - get_json_value
# ============================================================

class TestGetJsonValue:
    """Tests for the get_json_value function"""
    
    def test_simple_path(self):
        """Should extract value from simple nested path"""
        data = {"level1": {"level2": "found_it"}}
        assert get_json_value(data, "level1", "level2") == "found_it"
    
    def test_deep_path(self):
        """Should extract value from deeply nested path"""
        data = {"a": {"b": {"c": {"d": "deep_value"}}}}
        assert get_json_value(data, "a", "b", "c", "d") == "deep_value"
    
    def test_missing_key_returns_empty_dict(self):
        """Should return empty dict when key doesn't exist"""
        data = {"level1": {"level2": "value"}}
        result = get_json_value(data, "level1", "missing_key")
        assert result == {}
    
    def test_none_data_returns_empty_string(self):
        """Should return empty string when data is None"""
        assert get_json_value(None, "any", "path") == ""
    
    def test_empty_dict_returns_empty_dict(self):
        """Should return empty dict for empty dict"""
        assert get_json_value({}, "any", "path") == {}


# ============================================================
# TESTS FOR data_helpers.py - format_phone
# ============================================================

class TestFormatPhone:
    """Tests for the format_phone function"""
    
    def test_normal_phone_number(self):
        """Should format area code and number correctly"""
        result = format_phone("555", "1234567")
        assert result == "555-1234567"
    
    def test_empty_area_code(self):
        """Should handle empty area code"""
        result = format_phone("", "1234567")
        assert result == "1234567"
    
    def test_empty_number(self):
        """Should handle empty number"""
        result = format_phone("555", "")
        assert result == "555"
    
    def test_both_empty(self):
        """Should handle both empty"""
        result = format_phone("", "")
        assert result == ""
    
    def test_none_values(self):
        """Should handle None values"""
        result = format_phone(None, None)
        assert result == ""


# ============================================================
# TESTS FOR data_helpers.py - format_date_to_iso
# ============================================================

class TestFormatDateToIso:
    """Tests for the format_date_to_iso function"""
    
    def test_valid_date_format(self):
        """Should convert valid date to ISO format"""
        result = format_date_to_iso("2025-01-15")
        assert result == "2025-01-15T00:00:00"
    
    def test_empty_string_returns_empty(self):
        """Should return empty string for empty input"""
        assert format_date_to_iso("") == ""
    
    def test_none_returns_empty(self):
        """Should return empty string for None input"""
        assert format_date_to_iso(None) == ""


# ============================================================
# TESTS FOR data_helpers.py - clean_text
# ============================================================

class TestCleanText:
    """Tests for the clean_text function"""
    
    def test_removes_leading_trailing_whitespace(self):
        """Should remove leading and trailing whitespace"""
        assert clean_text("  hello  ") == "hello"
    
    def test_removes_newlines(self):
        """Should remove or replace newline characters"""
        result = clean_text("hello\nworld")
        assert "\n" not in result
    
    def test_removes_carriage_returns(self):
        """Should remove or replace carriage return characters"""
        result = clean_text("hello\rworld")
        assert "\r" not in result
    
    def test_handles_tabs(self):
        """Should handle tab characters"""
        result = clean_text("hello\tworld")
        assert isinstance(result, str)
    
    def test_empty_string(self):
        """Should handle empty string"""
        assert clean_text("") == ""
    
    def test_none_returns_empty(self):
        """Should handle None input"""
        result = clean_text(None)
        assert result == "" or result is None
    
    def test_non_string_input(self):
        """Should handle non-string input like numbers"""
        result = clean_text(12345)
        assert result == "12345" or result == 12345


# ============================================================
# HOW TO RUN THESE TESTS
# ============================================================
# 
# 1. Make sure pytest is installed:
#    pip install pytest
#
# 2. Run all tests:
#    pytest test_helpers.py -v
#
# 3. Run a specific test class:
#    pytest test_helpers.py::TestGetCountryCode -v
#
# 4. Run a specific test:
#    pytest test_helpers.py::TestGetCountryCode::test_full_country_name_uppercase -v
#
# The -v flag means "verbose" - shows each test name and result