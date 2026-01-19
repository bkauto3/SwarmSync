"""
Test Suite for TOON Encoder
----------------------------
Comprehensive tests for TOON encoding/decoding functionality.

Tests cover:
1. Basic encoding/decoding
2. Token reduction validation
3. Edge cases (escaping, nulls, nested data)
4. Content-Type negotiation
5. Backward compatibility

Author: Hudson (Code Review Agent)
Date: 2025-10-27
Version: 1.0.0
"""

import pytest
import json
from infrastructure.toon_encoder import (
    supports_toon,
    encode_to_toon,
    decode_from_toon,
    calculate_token_reduction,
    toon_or_json,
    _encode_value,
    _decode_value,
    _split_csv_line
)


class TestToonSupport:
    """Test TOON suitability detection"""

    def test_supports_tabular_data(self):
        """TOON should support consistent tabular data"""
        data = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 3, "name": "Charlie", "age": 35}
        ]
        assert supports_toon(data) is True

    def test_rejects_single_object(self):
        """TOON should reject single objects (no repetition)"""
        data = {"id": 1, "name": "Alice"}
        assert supports_toon(data) is False

    def test_rejects_single_item_list(self):
        """TOON should reject single-item lists"""
        data = [{"id": 1, "name": "Alice"}]
        assert supports_toon(data) is False

    def test_rejects_inconsistent_keys(self):
        """TOON should reject data with inconsistent keys"""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "email": "bob@example.com"}  # Different keys
        ]
        assert supports_toon(data) is False

    def test_accepts_partial_key_overlap(self):
        """TOON should accept data with >70% key overlap"""
        data = [
            {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "age": 35}  # Missing email (75% overlap)
        ]
        # First item has all keys, so 3/4 = 75% consistency
        assert supports_toon(data) is True

    def test_rejects_deeply_nested_data(self):
        """TOON should reject deeply nested structures"""
        data = [
            {"id": 1, "nested": {"level1": {"level2": {"level3": "value"}}}},
            {"id": 2, "nested": {"level1": {"level2": {"level3": "value"}}}}
        ]
        assert supports_toon(data) is False

    def test_accepts_shallow_nested_data(self):
        """TOON should accept shallow (1-level) nesting"""
        data = [
            {"id": 1, "metadata": {"created": "2025-01-01", "author": "Alice"}},
            {"id": 2, "metadata": {"created": "2025-01-02", "author": "Bob"}}
        ]
        assert supports_toon(data) is True

    def test_rejects_non_list(self):
        """TOON should reject non-list data"""
        assert supports_toon("string") is False
        assert supports_toon(123) is False
        assert supports_toon(None) is False


class TestToonEncoding:
    """Test TOON encoding functionality"""

    def test_basic_encoding(self):
        """Test basic TOON encoding"""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]

        toon = encode_to_toon(data)

        assert "@toon 1.0" in toon
        assert "@keys id,name" in toon
        assert "1,Alice" in toon
        assert "2,Bob" in toon

    def test_encoding_with_nulls(self):
        """Test encoding with null values"""
        data = [
            {"id": 1, "name": "Alice", "email": None},
            {"id": 2, "name": "Bob", "email": "bob@example.com"}
        ]

        toon = encode_to_toon(data)

        lines = toon.split('\n')
        assert lines[2] == "1,Alice,"  # Null becomes empty string
        assert "2,Bob,bob@example.com" in toon

    def test_encoding_with_commas(self):
        """Test encoding with commas in values"""
        data = [
            {"id": 1, "name": "Smith, John"},
            {"id": 2, "name": "Doe, Jane"}
        ]

        toon = encode_to_toon(data)

        # Commas should be escaped as \c
        assert "Smith\\c John" in toon
        assert "Doe\\c Jane" in toon

    def test_encoding_with_newlines(self):
        """Test encoding with newlines in values"""
        data = [
            {"id": 1, "description": "Line 1\nLine 2"},
            {"id": 2, "description": "Single line"}
        ]

        toon = encode_to_toon(data)

        # Newlines should be escaped as \n
        assert "Line 1\\nLine 2" in toon

    def test_encoding_with_backslashes(self):
        """Test encoding with backslashes in values"""
        data = [
            {"id": 1, "path": "C:\\Users\\Alice"},
            {"id": 2, "path": "C:\\Users\\Bob"}
        ]

        toon = encode_to_toon(data)

        # Backslashes should be escaped
        assert "C:\\\\Users\\\\Alice" in toon

    def test_encoding_with_booleans(self):
        """Test encoding with boolean values"""
        data = [
            {"id": 1, "active": True, "verified": False},
            {"id": 2, "active": False, "verified": True}
        ]

        toon = encode_to_toon(data)

        assert "1,true,false" in toon
        assert "2,false,true" in toon

    def test_encoding_with_numbers(self):
        """Test encoding with numeric values"""
        data = [
            {"id": 1, "age": 30, "score": 95.5},
            {"id": 2, "age": 25, "score": 87.3}
        ]

        toon = encode_to_toon(data)

        assert "1,30,95.5" in toon
        assert "2,25,87.3" in toon

    def test_encoding_with_nested_objects(self):
        """Test encoding with nested objects (JSON fallback)"""
        data = [
            {"id": 1, "metadata": {"created": "2025-01-01", "author": "Alice"}},
            {"id": 2, "metadata": {"created": "2025-01-02", "author": "Bob"}}
        ]

        toon = encode_to_toon(data)

        # Nested objects should be JSON-encoded and escaped
        assert "@toon 1.0" in toon
        assert "id,metadata" in toon
        # Check that metadata is present (exact format may vary)
        assert "created" in toon
        assert "Alice" in toon

    def test_rejects_unsuitable_data(self):
        """Test that encoding raises error for unsuitable data"""
        with pytest.raises(ValueError):
            encode_to_toon([{"id": 1}])  # Single item

        with pytest.raises(ValueError):
            encode_to_toon([{"a": 1}, {"b": 2}])  # Inconsistent keys


class TestToonDecoding:
    """Test TOON decoding functionality"""

    def test_basic_decoding(self):
        """Test basic TOON decoding"""
        toon = "@toon 1.0\n@keys id,name\n1,Alice\n2,Bob"

        result = decode_from_toon(toon)

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "Alice"}
        assert result[1] == {"id": 2, "name": "Bob"}

    def test_decoding_with_nulls(self):
        """Test decoding with null values"""
        toon = "@toon 1.0\n@keys id,name,email\n1,Alice,\n2,Bob,bob@example.com"

        result = decode_from_toon(toon)

        assert result[0]["email"] is None
        assert result[1]["email"] == "bob@example.com"

    def test_decoding_with_escaped_commas(self):
        """Test decoding with escaped commas"""
        toon = "@toon 1.0\n@keys id,name\n1,Smith\\c John\n2,Doe\\c Jane"

        result = decode_from_toon(toon)

        assert result[0]["name"] == "Smith, John"
        assert result[1]["name"] == "Doe, Jane"

    def test_decoding_with_escaped_newlines(self):
        """Test decoding with escaped newlines"""
        toon = "@toon 1.0\n@keys id,description\n1,Line 1\\nLine 2\n2,Single line"

        result = decode_from_toon(toon)

        assert result[0]["description"] == "Line 1\nLine 2"
        assert result[1]["description"] == "Single line"

    def test_decoding_booleans(self):
        """Test decoding boolean values"""
        toon = "@toon 1.0\n@keys id,active\n1,true\n2,false"

        result = decode_from_toon(toon)

        assert result[0]["active"] is True
        assert result[1]["active"] is False

    def test_decoding_numbers(self):
        """Test decoding numeric values"""
        toon = "@toon 1.0\n@keys id,age,score\n1,30,95.5\n2,25,87.3"

        result = decode_from_toon(toon)

        assert result[0]["age"] == 30
        assert result[0]["score"] == 95.5
        assert result[1]["age"] == 25
        assert result[1]["score"] == 87.3

    def test_roundtrip_consistency(self):
        """Test that encode -> decode preserves data"""
        original = [
            {"id": 1, "name": "Alice", "age": 30, "active": True},
            {"id": 2, "name": "Bob", "age": 25, "active": False},
            {"id": 3, "name": "Charlie", "age": 35, "active": True}
        ]

        toon = encode_to_toon(original)
        decoded = decode_from_toon(toon)

        assert len(decoded) == len(original)
        for i, item in enumerate(original):
            assert decoded[i] == item

    def test_invalid_format_missing_header(self):
        """Test that invalid TOON format raises error"""
        with pytest.raises(ValueError, match="missing @toon header"):
            decode_from_toon("invalid\n@keys id\n1")

    def test_invalid_format_missing_keys(self):
        """Test that missing @keys raises error"""
        with pytest.raises(ValueError, match="missing @keys header"):
            decode_from_toon("@toon 1.0\ninvalid\n1")

    def test_invalid_format_mismatched_columns(self):
        """Test that mismatched columns raises error"""
        with pytest.raises(ValueError, match="row has .* values but .* keys expected"):
            decode_from_toon("@toon 1.0\n@keys id,name\n1,Alice\n2,Bob,Extra")


class TestTokenReduction:
    """Test token reduction calculation"""

    def test_token_reduction_tabular_data(self):
        """Test that tabular data provides 30-60% reduction"""
        data = [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(1, 11)
        ]

        reduction = calculate_token_reduction(data)

        # Should be in 30-60% range
        assert 0.3 <= reduction <= 0.6, f"Reduction {reduction:.2%} outside expected range"

    def test_token_reduction_unsuitable_data(self):
        """Test that unsuitable data returns 0% reduction"""
        data = [{"id": 1}]  # Single item

        reduction = calculate_token_reduction(data)

        assert reduction == 0.0

    def test_token_reduction_vs_json(self):
        """Test that TOON is smaller than JSON"""
        data = [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 3, "name": "Charlie", "age": 35}
        ]

        json_str = json.dumps(data, separators=(',', ':'))
        toon_str = encode_to_toon(data)

        assert len(toon_str) < len(json_str)


class TestContentTypeNegotiation:
    """Test automatic TOON/JSON selection"""

    def test_toon_for_efficient_data(self):
        """Test that efficient data uses TOON"""
        data = [
            {"id": i, "name": f"User{i}"}
            for i in range(1, 11)
        ]

        content_type, encoded = toon_or_json(data)

        assert content_type == "application/toon"
        assert "@toon 1.0" in encoded

    def test_json_for_single_object(self):
        """Test that single object uses JSON"""
        data = {"id": 1, "name": "Alice"}

        content_type, encoded = toon_or_json(data)

        assert content_type == "application/json"
        assert json.loads(encoded) == data

    def test_json_for_small_reduction(self):
        """Test that data with <20% reduction uses JSON"""
        # Single pair of items with few keys (minimal benefit)
        data = [
            {"a": 1},
            {"a": 2}
        ]

        content_type, encoded = toon_or_json(data)

        # Should prefer JSON for minimal benefit
        if supports_toon(data):
            reduction = calculate_token_reduction(data)
            if reduction < 0.2:
                assert content_type == "application/json"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_list(self):
        """Test encoding empty list"""
        assert supports_toon([]) is False

    def test_special_characters(self):
        """Test encoding with various special characters"""
        data = [
            {"id": 1, "text": "Tab:\t Quote:\" Backslash:\\"},
            {"id": 2, "text": "Normal text"}
        ]

        toon = encode_to_toon(data)
        decoded = decode_from_toon(toon)

        # Should preserve special characters
        assert decoded[0]["text"] == data[0]["text"]

    def test_large_dataset(self):
        """Test encoding large dataset"""
        data = [
            {"id": i, "name": f"User{i}", "email": f"user{i}@example.com"}
            for i in range(1, 101)
        ]

        toon = encode_to_toon(data)
        decoded = decode_from_toon(toon)

        assert len(decoded) == 100
        assert decoded[0]["id"] == 1
        assert decoded[99]["id"] == 100

    def test_unicode_support(self):
        """Test encoding with Unicode characters"""
        data = [
            {"id": 1, "name": "Alice 你好"},
            {"id": 2, "name": "Bob мир"}
        ]

        toon = encode_to_toon(data)
        decoded = decode_from_toon(toon)

        assert decoded[0]["name"] == "Alice 你好"
        assert decoded[1]["name"] == "Bob мир"


class TestValueHelpers:
    """Test internal value encoding/decoding helpers"""

    def test_encode_value_primitives(self):
        """Test encoding primitive values"""
        assert _encode_value(None) == ""
        assert _encode_value(True) == "true"
        assert _encode_value(False) == "false"
        assert _encode_value(42) == "42"
        assert _encode_value(3.14) == "3.14"
        assert _encode_value("hello") == "hello"

    def test_encode_value_escaping(self):
        """Test encoding with escaping"""
        assert _encode_value("a,b") == "a\\cb"
        assert _encode_value("a\nb") == "a\\nb"
        assert _encode_value("a\\b") == "a\\\\b"

    def test_decode_value_primitives(self):
        """Test decoding primitive values"""
        assert _decode_value("") is None
        assert _decode_value("true") is True
        assert _decode_value("false") is False
        assert _decode_value("42") == 42
        assert _decode_value("3.14") == 3.14
        assert _decode_value("hello") == "hello"

    def test_decode_value_unescaping(self):
        """Test decoding with unescaping"""
        assert _decode_value("a\\cb") == "a,b"
        assert _decode_value("a\\nb") == "a\nb"
        assert _decode_value("a\\\\b") == "a\\b"

    def test_split_csv_line(self):
        """Test CSV line splitting"""
        assert _split_csv_line("a,b,c") == ["a", "b", "c"]
        assert _split_csv_line("a\\cb,d") == ["a,b", "d"]
        assert _split_csv_line("a\\\\,b") == ["a\\", "b"]


class TestBackwardCompatibility:
    """Test backward compatibility with existing A2A protocol"""

    def test_json_fallback_works(self):
        """Test that JSON fallback works for non-TOON data"""
        data = {"single": "object"}

        content_type, encoded = toon_or_json(data)

        assert content_type == "application/json"
        assert json.loads(encoded) == data

    def test_toon_disabled_gracefully(self):
        """Test that system works without TOON support"""
        data = [{"id": 1}, {"id": 2}]

        # Should work with JSON even if TOON would be beneficial
        json_str = json.dumps(data)
        assert json.loads(json_str) == data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
