import pathlib
import sys

print("🩺 DOCTOR CHECK...")

problems = []

# Check ASCII
for root in ["dqf", "tests"]:
    for f in pathlib.Path(root).rglob("*.py"):
        if any(b > 127 for b in f.read_bytes()):
            problems.append(f"Non-ASCII: {f}")

# Check empty files
for f in pathlib.Path("dqf").rglob("*.py"):
    if f.read_text().strip() == "":
        problems.append(f"Empty file: {f}")

if problems:
    print("❌ Issues found:")
    for p in problems:
        print(" -", p)
    sys.exit(1)

print("✔ All good")
sys.exit(0)
