#!/bin/bash

echo "🔧 Fixing type hints..."

# 1. Installer types-PyYAML
pip install types-PyYAML

# 2. Ajouter -> None aux __init__
echo "  Adding -> None to __init__..."
find dqf -name "*.py" -exec sed -i 's/\(def __init__(self[^)]*)\):/\1 -> None:/' {} \;

# 3. Ajouter imports nécessaires si manquants
echo "  Ensuring imports..."
for file in dqf/checks/*.py; do
    if ! grep -q "from typing import" "$file"; then
        sed -i '1i from typing import Any, Dict, List, Optional' "$file"
    fi
done

# 4. Vérifier
echo "  Verifying..."
mypy dqf --no-error-summary | head -20

echo "✅ Type hints fixes applied"
echo "📝 Manual fixes still needed for complex cases"