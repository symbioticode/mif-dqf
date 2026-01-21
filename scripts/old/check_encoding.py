import sys
import pathlib

issues = []

def scan(path):
    for f in pathlib.Path(path).rglob("*.py"):
        content = f.read_bytes()
        if any(b > 127 for b in content):
            issues.append(str(f))

scan("dqf")
scan("tests")

if issues:
    print(f"❌ Non-ASCII in: {issues}")
    sys.exit(1)
else:
    print("✅ All files ASCII-only")

jf = pathlib.Path("justfile")
if jf.exists():
    content = jf.read_bytes()
    if any(b > 127 for b in content):
        issues.append("justfile")

    sys.exit(0)