"""
Comprehensive Test Suite for eval() RCE Patches
================================================

Security Agent: Sentinel
Date: October 30, 2025
CVSS Score: 8.6 (HIGH)
Vulnerability: Remote Code Execution via unsafe eval()

This test suite validates all patches for eval() vulnerabilities:
1. deepseek_ocr_compressor.py - HIGH risk (external OCR input)
2. tool_test.py - MEDIUM risk (regex-validated math)
3. security_utils.safe_eval() - Helper function

Test Coverage:
- Safe literal parsing (lists, dicts, tuples, numbers)
- RCE attack blocking (__import__, os.system, exec, etc.)
- DoS prevention (input length limits)
- Pattern detection (dangerous keywords)
- Bypass attempt detection
- Integration with existing code
"""

import pytest
import ast
import sys
from pathlib import Path

# Add infrastructure to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.security_utils import safe_eval


class TestSafeEvalBasics:
    """Test safe_eval() with valid inputs"""

    def test_safe_eval_integer(self):
        """Test integer parsing"""
        assert safe_eval("42") == 42
        assert safe_eval("-123") == -123
        assert safe_eval("0") == 0

    def test_safe_eval_float(self):
        """Test float parsing"""
        assert safe_eval("3.14159") == 3.14159
        assert safe_eval("-0.5") == -0.5

    def test_safe_eval_string(self):
        """Test string parsing"""
        assert safe_eval("'hello'") == "hello"
        assert safe_eval('"world"') == "world"

    def test_safe_eval_list(self):
        """Test list parsing"""
        assert safe_eval("[1, 2, 3]") == [1, 2, 3]
        assert safe_eval("['a', 'b', 'c']") == ['a', 'b', 'c']
        assert safe_eval("[[1, 2], [3, 4]]") == [[1, 2], [3, 4]]

    def test_safe_eval_dict(self):
        """Test dict parsing"""
        assert safe_eval("{'a': 1}") == {'a': 1}
        assert safe_eval("{'key': 'value', 'num': 42}") == {'key': 'value', 'num': 42}

    def test_safe_eval_tuple(self):
        """Test tuple parsing"""
        assert safe_eval("(1, 2, 3)") == (1, 2, 3)
        assert safe_eval("('x', 'y')") == ('x', 'y')

    def test_safe_eval_set(self):
        """Test set parsing"""
        assert safe_eval("{1, 2, 3}") == {1, 2, 3}

    def test_safe_eval_boolean(self):
        """Test boolean parsing"""
        assert safe_eval("True") is True
        assert safe_eval("False") is False

    def test_safe_eval_none(self):
        """Test None parsing"""
        assert safe_eval("None") is None

    def test_safe_eval_nested_structures(self):
        """Test complex nested data structures"""
        result = safe_eval("{'coords': [[10, 20], [30, 40]], 'label': 'box1'}")
        assert result == {'coords': [[10, 20], [30, 40]], 'label': 'box1'}


class TestSafeEvalRCEBlocking:
    """Test that RCE attack vectors are blocked"""

    def test_blocks_import(self):
        """Test __import__ is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("__import__('os').system('ls')")

    def test_blocks_os_system(self):
        """Test os.system is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("os.system('rm -rf /')")

    def test_blocks_subprocess(self):
        """Test subprocess is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("subprocess.run(['ls'])")

    def test_blocks_exec(self):
        """Test exec() is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("exec('print(1)')")

    def test_blocks_eval(self):
        """Test eval() is blocked (recursion)"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("eval('1+1')")

    def test_blocks_compile(self):
        """Test compile() is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("compile('print(1)', '<string>', 'exec')")

    def test_blocks_open(self):
        """Test open() is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("open('/etc/passwd')")

    def test_blocks_builtins_access(self):
        """Test __builtins__ access is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("__builtins__['eval']('1+1')")

    def test_blocks_class_access(self):
        """Test __class__ attribute access is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("''.__class__.__bases__")

    def test_blocks_globals_access(self):
        """Test globals() is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("globals()['__builtins__']")

    def test_blocks_lambda(self):
        """Test lambda is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("lambda x: x+1")

    def test_blocks_getattr(self):
        """Test getattr is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("getattr(__builtins__, 'eval')")


class TestSafeEvalDoSPrevention:
    """Test DoS prevention measures"""

    def test_blocks_long_input(self):
        """Test input length limit (default 10KB)"""
        long_input = "[" + "1," * 10000 + "]"  # ~30KB
        with pytest.raises(ValueError, match="Input too long"):
            safe_eval(long_input)

    def test_allows_input_under_limit(self):
        """Test input under limit is allowed"""
        # ~5KB input (within 10KB limit)
        medium_input = "[" + ", ".join([str(i) for i in range(500)]) + "]"
        result = safe_eval(medium_input)
        assert len(result) == 500

    def test_custom_length_limit(self):
        """Test custom max_length parameter"""
        with pytest.raises(ValueError, match="Input too long"):
            safe_eval("[1, 2, 3]", max_length=5)  # String "[1, 2, 3]" is 9 chars


class TestSafeEvalErrorHandling:
    """Test error handling for invalid inputs"""

    def test_invalid_syntax(self):
        """Test invalid Python syntax"""
        with pytest.raises(ValueError, match="Invalid literal"):
            safe_eval("[1, 2,")  # Unclosed bracket

    def test_invalid_type_input(self):
        """Test non-string input"""
        with pytest.raises(ValueError, match="Input must be string"):
            safe_eval(123)  # type: ignore

    def test_invalid_literal(self):
        """Test invalid literal (function call)"""
        # This should be caught by pattern detection first
        with pytest.raises(ValueError):
            safe_eval("print('hello')")


class TestDeepSeekOCRPatch:
    """Test deepseek_ocr_compressor.py patch"""

    def test_valid_grounding_box_coords(self):
        """Test that valid grounding box coords are parsed safely"""
        # Simulate what _extract_grounding_boxes would parse
        coords_str = "[[10, 20, 30, 40], [50, 60, 70, 80]]"
        result = safe_eval(coords_str)
        assert result == [[10, 20, 30, 40], [50, 60, 70, 80]]

    def test_malicious_grounding_box_blocked(self):
        """Test that malicious OCR output is blocked"""
        # Simulated malicious OCR model output
        malicious_coords = "__import__('os').system('rm -rf /')"
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval(malicious_coords)

    def test_normalized_coords_parsing(self):
        """Test parsing of normalized coordinates (0-999)"""
        coords_str = "[[0, 0, 999, 999], [100, 100, 200, 200]]"
        result = safe_eval(coords_str)
        assert result == [[0, 0, 999, 999], [100, 100, 200, 200]]


class TestToolTestMathEvalPatch:
    """Test tool_test.py math_eval() patch"""

    def test_math_eval_integration(self):
        """Test that patched math_eval works correctly"""
        # Import the patched math_eval function
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tool_test",
            Path(__file__).parent.parent / "tool_test.py"
        )
        if spec and spec.loader:
            tool_test = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_test)

            # Test valid math expressions
            assert tool_test.math_eval("1 + 1") == "2"
            assert tool_test.math_eval("10 * 5") == "50"
            assert tool_test.math_eval("(12 / 3) + 5") == "9.0"

    def test_math_eval_blocks_malicious_input(self):
        """Test that math_eval blocks non-math expressions"""
        # Import the patched math_eval function
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tool_test",
            Path(__file__).parent.parent / "tool_test.py"
        )
        if spec and spec.loader:
            tool_test = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tool_test)

            # Test malicious input is rejected
            result = tool_test.math_eval("__import__('os').system('ls')")
            assert "Error" in result  # Should return error, not execute


class TestBypassAttempts:
    """Test common bypass techniques are blocked"""

    def test_unicode_encoding_bypass(self):
        """Test Unicode-encoded malicious input is blocked"""
        # Attempt to bypass with Unicode encoding
        with pytest.raises(ValueError):
            safe_eval("\\u005f\\u005fimport\\u005f\\u005f('os')")

    def test_string_concatenation_bypass(self):
        """Test string concatenation bypass is blocked"""
        # ast.literal_eval doesn't support expressions, so this fails
        with pytest.raises(ValueError):
            safe_eval("'__import' + '__'")

    def test_nested_eval_bypass(self):
        """Test nested eval bypass is blocked"""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            safe_eval("eval(eval('1+1'))")

    def test_base64_bypass(self):
        """Test base64-encoded payload is blocked"""
        # Even if base64 module was available, pattern detection blocks it
        with pytest.raises(ValueError):
            safe_eval("__import__('base64').b64decode('...')")


class TestProductionIntegration:
    """Test integration with production code"""

    def test_no_unsafe_eval_in_deepseek_ocr(self):
        """Verify deepseek_ocr_compressor.py no longer uses unsafe eval()"""
        ocr_file = Path(__file__).parent.parent / "infrastructure/deepseek_ocr_compressor.py"
        content = ocr_file.read_text()

        # Should NOT contain unsafe eval()
        # Pattern: eval( followed by non-literal-eval context
        import re
        unsafe_eval_pattern = r'\beval\s*\(\s*[^)]'
        matches = re.findall(unsafe_eval_pattern, content)

        # Filter out false positives (model.eval())
        unsafe_matches = [m for m in matches if "model.eval" not in m and ".eval()" not in m]

        assert len(unsafe_matches) == 0, f"Found unsafe eval() calls: {unsafe_matches}"

        # Should contain ast.literal_eval()
        assert "ast.literal_eval" in content, "ast.literal_eval not found in patched file"

    def test_no_unsafe_eval_in_tool_test(self):
        """Verify tool_test.py no longer uses unsafe eval()"""
        tool_test_file = Path(__file__).parent.parent / "tool_test.py"
        content = tool_test_file.read_text()

        # Should NOT contain eval() with restricted globals (old pattern)
        assert 'eval(expression, {"__builtins__": {}}' not in content

        # Should contain AST-based evaluation
        assert "ast.parse" in content or "ast.Num" in content or "ast.BinOp" in content


class TestRegressionPrevention:
    """Test that patches don't break existing functionality"""

    def test_safe_eval_preserves_json_compatibility(self):
        """Test that safe_eval handles JSON-like structures"""
        json_str = '{"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}'
        result = safe_eval(json_str)
        assert result == {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}

    def test_safe_eval_handles_coordinates(self):
        """Test grounding box coordinate format"""
        coords = "[[10, 20, 30, 40]]"
        result = safe_eval(coords)
        assert result == [[10, 20, 30, 40]]

    def test_safe_eval_handles_empty_structures(self):
        """Test empty lists/dicts"""
        assert safe_eval("[]") == []
        assert safe_eval("{}") == {}
        assert safe_eval("()") == ()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
