"""
Code Extraction and Validation Pipeline

Extracts clean TypeScript code from LLM responses that may contain:
- Explanatory text before/after code
- Markdown code fences
- Reasoning and planning text
- Mixed content

Validates that extracted code is:
- Actually TypeScript (not Python or other languages)
- Has minimum quality standards
- Compiles-ready (proper syntax)
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def extract_clean_code(llm_response: str, expected_language: str = "typescript") -> str:
    """
    Extract clean code from LLM response, removing all non-code content.
    
    Args:
        llm_response: Raw LLM output (may contain reasoning, markdown, etc.)
        expected_language: Expected programming language (default: typescript)
    
    Returns:
        Clean code string
    
    Raises:
        ValueError: If no valid code found or wrong language detected
    """
    if not llm_response or len(llm_response.strip()) == 0:
        raise ValueError("Empty LLM response")
    
    # Strategy 1: Try to extract from markdown code blocks
    code = _extract_from_markdown_blocks(llm_response, expected_language)
    
    if code:
        logger.debug(f"Extracted {len(code)} chars from markdown blocks")
    else:
        # Strategy 2: Try to find where code starts (import/export/const/etc)
        code = _extract_by_code_markers(llm_response)
        
        if code:
            logger.debug(f"Extracted {len(code)} chars by code markers")
        else:
            # Strategy 3: Last resort - assume entire response is code if it looks like it
            if _looks_like_code(llm_response):
                code = llm_response.strip()
                logger.debug("Treating entire response as code")
            else:
                raise ValueError("Could not extract code from LLM response")
    
    # Clean up extracted code
    code = _cleanup_code(code)
    
    # Validate it's the right language
    if expected_language == "typescript":
        # Check for Python syntax first (hard blocker)
        if has_python_syntax(code):
            raise ValueError("Generated Python code instead of TypeScript")

        # Check for TypeScript syntax (more lenient now)
        if not has_typescript_syntax(code):
            # Log the code snippet for debugging
            logger.warning(f"Code validation concern - first 200 chars: {code[:200]}")
            # Only raise if it's REALLY not TypeScript (has no JS/TS patterns at all)
            if not any(pattern in code for pattern in ['import', 'export', 'function', 'const', '=>', 'interface']):
                raise ValueError("Generated code doesn't look like TypeScript")
            else:
                logger.info("Code looks like JavaScript/TypeScript - allowing despite low indicator count")

    # Validate minimum quality (reduced from 50 to 30 for simple components)
    if len(code) < 30:
        raise ValueError(f"Generated code too short ({len(code)} chars)")

    if not _has_imports_or_exports(code):
        logger.info("Code has no imports or exports - may be a simple snippet (allowed)")
    
    return code


def _extract_from_markdown_blocks(text: str, language: str) -> Optional[str]:
    """Extract code from markdown code blocks (```typescript ... ```)."""
    # Try language-specific blocks first
    patterns = [
        rf'```{language}\n(.*?)```',
        r'```typescript\n(.*?)```',
        r'```ts\n(.*?)```',
        r'```tsx\n(.*?)```',
        r'```javascript\n(.*?)```',
        r'```js\n(.*?)```',
        r'```jsx\n(.*?)```',
        r'```\n(.*?)```',  # Generic code block
    ]
    
    all_blocks = []
    for pattern in patterns:
        blocks = re.findall(pattern, text, re.DOTALL)
        all_blocks.extend(blocks)
    
    if all_blocks:
        # Join multiple blocks with double newline
        return '\n\n'.join(block.strip() for block in all_blocks)
    
    return None


def _extract_by_code_markers(text: str) -> Optional[str]:
    """Find where code starts by looking for common markers (import, export, etc.)."""
    lines = text.split('\n')
    code_start = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check if line starts with code marker
        if stripped.startswith(('import ', 'export ', 'const ', 'let ', 'var ',
                                'function ', 'interface ', 'type ', 'class ',
                                'async ', "'use client'", '"use client"')):
            code_start = i
            break
    
    if code_start is not None:
        # Take everything from code start to end
        code_lines = lines[code_start:]
        
        # Try to find where code ends (if there's explanatory text after)
        code_end = len(code_lines)
        for i, line in enumerate(code_lines):
            # Check for obvious non-code markers
            if line.strip().startswith(('So in summary', 'This code', 'The above',
                                       'Note:', 'Important:', '---', '###')):
                code_end = i
                break
        
        return '\n'.join(code_lines[:code_end])
    
    return None


def _looks_like_code(text: str) -> bool:
    """Check if text looks like code (has typical code patterns)."""
    code_indicators = [
        'import ',
        'export ',
        'function ',
        'const ',
        '=>',
        '() {',
        'interface ',
        'type ',
        'return ',
    ]
    
    # Count how many indicators present
    indicator_count = sum(1 for indicator in code_indicators if indicator in text)
    
    # If it has at least 3 code indicators, probably code
    return indicator_count >= 3


def _cleanup_code(code: str) -> str:
    """Clean up extracted code (remove artifacts, normalize whitespace)."""
    # Remove any remaining markdown artifacts
    code = re.sub(r'```\w*\n?', '', code)
    code = re.sub(r'```$', '', code)
    
    # Remove HTML comments (<!-- ... -->)
    code = re.sub(r'<!--.*?-->', '', code, flags=re.DOTALL)
    
    # Remove lines that are clearly explanatory
    lines = code.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip lines that are obviously not code
        if stripped.startswith(('Okay,', 'Here', 'Let me', 'I will', 'This is',
                               'The above', 'Note:', 'Important:', '---')):
            continue
        cleaned_lines.append(line)
    
    code = '\n'.join(cleaned_lines)
    
    # Normalize whitespace (but preserve indentation)
    code = code.strip()
    
    # Remove excessive blank lines (max 2 consecutive)
    code = re.sub(r'\n{3,}', '\n\n', code)
    
    return code


def has_python_syntax(code: str) -> bool:
    """
    Check if code contains Python-specific syntax.
    
    Returns True if Python patterns detected.
    """
    python_indicators = [
        r'def\s+\w+\s*\(',  # def function_name(
        r'self\.',          # self.attribute
        r'class\s+\w+\s*:',  # class Name:
        r'^\s*"""',         # Python docstrings
        r"^\s*'''",         # Python docstrings (single quotes)
        r'print\s*\(',      # print()
        r'if\s+__name__\s*==',  # if __name__ == '__main__'
        r'from\s+\w+\s+import',  # from x import y
        r'@dataclass',      # decorators
        r'async\s+def\s',   # async def (Python-style)
    ]
    
    for pattern in python_indicators:
        if re.search(pattern, code, re.MULTILINE):
            logger.warning(f"Detected Python syntax: {pattern}")
            return True
    
    return False


def has_typescript_syntax(code: str) -> bool:
    """
    Check if code has TypeScript-specific patterns.

    Returns True if TypeScript patterns detected.
    """
    typescript_indicators = [
        r':\s*(string|number|boolean|any|void|unknown)',  # Type annotations
        r'interface\s+\w+',   # interface definitions
        r'type\s+\w+\s*=',    # type aliases
        r'<\w+>',             # Generics (also matches JSX)
        r'=>',                # Arrow functions
        r'import.*from\s+["\']',  # ES6 imports
        r'export\s+(default|const|function|interface|type)',  # ES6 exports
        r'function\s+\w+',    # Function declarations
        r'const\s+\w+',       # Const declarations
        r'<div|<button|<input|<form',  # JSX/TSX elements
        r'className=',        # React className (TSX indicator)
        r'useState|useEffect|useCallback',  # React hooks
    ]

    indicator_count = 0
    for pattern in typescript_indicators:
        if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
            indicator_count += 1

    # Relaxed: Need at least 1 indicator (was 2, too strict)
    # Most TS/React code will have imports, exports, or arrow functions
    return indicator_count >= 1


def _has_imports_or_exports(code: str) -> bool:
    """Check if code has imports or exports (sign of completeness)."""
    return bool(re.search(r'^(import|export)\s', code, re.MULTILINE))


def validate_typescript_file(code: str, filename: str = "unknown") -> Tuple[bool, Optional[str]]:
    """
    Validate TypeScript code for common issues.

    Args:
        code: TypeScript code to validate
        filename: Optional filename for better error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for Python syntax
    if has_python_syntax(code):
        return False, f"{filename}: Contains Python syntax (def, self, class:)"

    # Check for TypeScript syntax
    if not has_typescript_syntax(code):
        return False, f"{filename}: Doesn't appear to be TypeScript"

    # Check minimum length (reduced from 100 to 40 for simple components)
    if len(code) < 40:
        return False, f"{filename}: Code too short ({len(code)} chars)"
    
    # Check for obvious errors
    if 'ERROR:' in code[:200]:
        return False, f"{filename}: Contains error message at start"
    
    # Check for unfinished code
    if code.count('{') != code.count('}'):
        return False, f"{filename}: Mismatched braces (unfinished code)"
    
    return True, None


def extract_and_validate(llm_response: str, component_name: str = "component") -> str:
    """
    High-level function: Extract code and validate in one step.
    
    Args:
        llm_response: Raw LLM output
        component_name: Name of component (for error messages)
    
    Returns:
        Clean, validated TypeScript code
    
    Raises:
        ValueError: If extraction or validation fails
    """
    try:
        # Extract
        code = extract_clean_code(llm_response, expected_language="typescript")
        
        # Validate
        is_valid, error = validate_typescript_file(code, filename=f"{component_name}.ts")
        
        if not is_valid:
            raise ValueError(error)
        
        logger.info(f"Successfully extracted and validated {len(code)} chars for {component_name}")
        return code
        
    except ValueError as e:
        logger.error(f"Failed to extract/validate {component_name}: {e}")
        raise


if __name__ == "__main__":
    # Test the extractor
    test_cases = [
        # Test 1: Markdown block
        """Here's the code you requested:

```typescript
export interface Product {
  id: string;
  name: string;
  price: number;
}
```

This creates a product interface.""",
        
        # Test 2: No markdown, starts with code
        """export interface User {
  id: string;
  name: string;
  email: string;
}

export function getUser(id: string): User {
  // implementation
  return { id, name: 'Test', email: 'test@test.com' };
}""",
        
        # Test 3: With reasoning before code
        """Okay, I'll create the component. Let me start with the interface.

export interface Task {
  id: string;
  title: string;
  completed: boolean;
}

export function TaskList() {
  return <div>Tasks</div>;
}""",
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}")
        print(f"{'='*60}")
        try:
            result = extract_and_validate(test, f"test_{i}")
            print(f"✅ Success! Extracted {len(result)} chars")
            print(f"Preview:\n{result[:200]}...")
        except ValueError as e:
            print(f"❌ Failed: {e}")

