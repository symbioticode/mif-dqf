#!/usr/bin/env python3
"""
Diagnostic script pour tests pytest non collectes
"""

import ast
import sys


def analyze_test_file(filepath):
    """Analyse structure d'un fichier test pytest."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {filepath}")
    print(f"{'='*60}\n")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse AST
    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError as e:
        print(f"? SYNTAX ERROR: {e}")
        return False

    # Find classes and functions
    classes_found = []
    functions_found = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes_found.append(
                {
                    "name": node.name,
                    "lineno": node.lineno,
                    "methods": [
                        m.name for m in node.body if isinstance(m, ast.FunctionDef)
                    ],
                }
            )
        elif isinstance(node, ast.FunctionDef):
            # Top-level functions only
            if node.col_offset == 0:
                functions_found.append({"name": node.name, "lineno": node.lineno})

    # Print findings
    print(f"? Classes found: {len(classes_found)}")
    for cls in classes_found:
        marker = "?" if cls["name"].startswith("Test") else "?"
        print(f"  {marker} {cls['name']} (line {cls['lineno']})")
        print(f"     Methods: {len(cls['methods'])}")
        for method in cls["methods"]:
            m_marker = "?" if method.startswith("test_") else "?"
            print(f"       {m_marker} {method}")

    print(f"\n? Top-level functions: {len(functions_found)}")
    for func in functions_found:
        marker = "?" if func["name"].startswith("test_") else "?"
        print(f"  {marker} {func['name']} (line {func['lineno']})")

    # Validation
    valid_classes = [c for c in classes_found if c["name"].startswith("Test")]
    valid_tests = sum(
        len([m for m in c["methods"] if m.startswith("test_")]) for c in valid_classes
    )
    valid_tests += len([f for f in functions_found if f["name"].startswith("test_")])

    print(f"\n{'='*60}")
    print(f"? Valid test classes: {len(valid_classes)}")
    print(f"? Valid test methods/functions: {valid_tests}")
    print(f"{'='*60}\n")

    if valid_tests == 0:
        print("? NO VALID TESTS FOUND!")
        print("   Pytest requires:")
        print("   - Classes named Test*")
        print("   - Methods/functions named test_*")
        return False

    return True


if __name__ == "__main__":
    filepath = (
        sys.argv[1] if len(sys.argv) > 1 else "tests/unit/test_check_3_calendar.py"
    )
    success = analyze_test_file(filepath)
    sys.exit(0 if success else 1)
