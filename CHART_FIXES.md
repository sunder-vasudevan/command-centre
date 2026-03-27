# Command Centre Chart Fixes — 2026-03-27

## Problem
Command Centre charts were missing/not rendering after wrap updates. Charts would fail to load silently, leaving blank spaces where graphs should be.

## Root Cause
The `wrap_update.py` script's `sessions_to_js()` function was converting session labels incorrectly:
1. JSON stores labels as `"label": "Mar 27\\nMeta"` (with escaped backslash-n)
2. Python's `json.load()` converts this to the Python string `"Mar 27\nMeta"` (with actual newline character)
3. When writing to JavaScript via f-string, the newline was being written as a literal line break
4. This broke the JavaScript object syntax: `{label:'Mar 27` (line break) `Meta',project...}` ❌

## Solution

### Fix 1: Proper String Escaping (wrap_update.py)
```python
# OLD (broken):
label = s["label"].replace("\\n", "\n").replace("\n", "\\n")

# NEW (correct):
label = s["label"]
line = f"{{label:'{repr(label)[1:-1]}',project:'{s['project']}',mins:{s['mins']},tokens:{tokens}}},"
```

Using `repr()` ensures Python properly escapes the backslash for JavaScript.

### Fix 2: Validation Function (wrap_update.py)
Added `validate_js_syntax()` that checks generated sessions JS for syntax errors before patching HTML.
- Runs automatically on every `wrap_update.py sync` call
- Aborts sync if errors detected, preventing broken deployments
- Prevents future chart rendering regressions

## Testing
✅ Charts now render correctly on Command Centre
✅ All sessions display with proper newlines (not line breaks)
✅ Validation catches any future escaping issues at sync time

## Prevention
- Use `python3 wrap_update.py sync` to auto-validate before deploying
- Validation will catch newline escaping errors immediately
- No more silent chart failures — explicit error message if sync detects syntax errors
