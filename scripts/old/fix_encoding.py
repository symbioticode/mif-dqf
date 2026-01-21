import sys
import pathlib

def fix_file(path):
    content = path.read_text(encoding="utf-8", errors="ignore")
    ascii_content = content.encode("ascii", errors="ignore").decode("ascii")
    if content != ascii_content:
        path.write_text(ascii_content, encoding="ascii")
        return True
    return False

fixed = []

for root in ["dqf", "tests"]:
    for f in pathlib.Path(root).rglob("*.py"):
        if fix_file(f):
            fixed.append(str(f))

if fixed:
    print("🧹 Fixed non-ASCII in:")
    for f in fixed:
        print("  -", f)
else:
    print("✨ No non-ASCII characters found")

# Also sanitize justfile
jf = pathlib.Path("justfile")
if jf.exists():
    if fix_file(jf):
        fixed.append("justfile")

sys.exit(0)
