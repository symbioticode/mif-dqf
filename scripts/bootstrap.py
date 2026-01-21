import subprocess
import sys
import os

print("🚀 BOOTSTRAP...")

subprocess.run(["pip", "install", "-r", "requirements.txt"], check=False)
subprocess.run(["pip", "install", "black", "ruff", "pytest", "coverage"], check=False)

os.makedirs(".githooks", exist_ok=True)

print("✔ Bootstrap complete")
