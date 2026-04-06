#!/bin/bash
set -e

echo "🔧 Correction Problèmes Critiques DQF v1.0.0"
echo "=============================================="

# 1. Import Optional
echo "1️⃣  Ajout import typing dans base.py..."
if ! grep -q "from typing import" dqf/checks/base.py; then
    sed -i '4a from typing import Any, Dict, List, Optional' dqf/checks/base.py
    echo "   ✅ Import ajouté"
else
    echo "   ℹ️  Import déjà présent"
fi

# 2. Fix variable issues
echo "2️⃣  Vérification variable 'issues'..."
if grep -q "issues=issues or \[\]" dqf/checks/base.py; then
    # Vérifier si CheckResult a champ issues
    if ! grep -A10 "class CheckResult" dqf/checks/base.py | grep -q "issues:"; then
        echo "   🔧 Retrait paramètre 'issues' non défini..."
        sed -i '/issues=issues or \[\]/d' dqf/checks/base.py
        echo "   ✅ Corrigé"
    else
        echo "   ℹ️  CheckResult a champ issues, OK"
    fi
fi

# 3. Typing deprecated
echo "3️⃣  Vérification typing deprecated..."
if [ -f "dqf/checks/__init__.py" ]; then
    if grep -q "from typing import Any, Dict, List, Optional" dqf/checks/__init__.py; then
        echo "   🔧 Nettoyage __init__.py..."
        echo "# Check classes module" > dqf/checks/__init__.py
        echo "   ✅ Nettoyé"
    fi
fi

# 4. Install build
echo "4️⃣  Installation module 'build'..."
pip install build twine -q
echo "   ✅ Installé"

# 5. Références obsolètes
echo "5️⃣  Correction références obsolètes..."
find . -type f \( -name "*.md" -o -name "*.toml" \) \
    -exec sed -i 's/yourusername/symbioticode/g' {} \; 2>/dev/null || true
find . -type f \( -name "*.md" -o -name "*.toml" \) \
    -exec sed -i 's/your\.email@example\.com/corail.synergia@proton.me/g' {} \; 2>/dev/null || true
echo "   ✅ Références mises à jour"

# 6. Vérification
echo ""
echo "🧪 Vérification..."
python -c "from dqf.checks.base import BaseCheck; print('✅ Import base.py OK')"

echo ""
echo "✅ Corrections appliquées - Lancer 'just sanitize' puis 'python scripts/test_baseline_v1.0.0.py'"