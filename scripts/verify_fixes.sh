#!/bin/bash
# verify_fixes.sh - Vérification des corrections DQF v1.0.0

set -e

echo "🔍 VÉRIFICATION CORRECTIONS DQF v1.0.0"
echo "==========================================="
echo ""

ERRORS=0
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ==============================================================================
# CHECK 1: Imports dans base.py
# ==============================================================================
echo "1️⃣  Vérification imports base.py"

if grep -q "^from typing import Any, Dict, List, Optional" dqf/checks/base.py; then
    echo -e "${GREEN}✅ Imports typing corrects${NC}"
else
    echo -e "${RED}❌ Imports typing incorrects${NC}"
    echo "Attendu: from typing import Any, Dict, List, Optional"
    echo "Trouvé:"
    grep "^from typing import" dqf/checks/base.py
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ==============================================================================
# CHECK 2: Test import Python réel
# ==============================================================================
echo "2️⃣  Test import Python"

if python3 -c "from dqf.checks.base import BaseCheck, CheckResult, CheckIssue" 2>/dev/null; then
    echo -e "${GREEN}✅ Import Python fonctionne${NC}"
else
    echo -e "${RED}❌ Import Python échoue:${NC}"
    python3 -c "from dqf.checks.base import BaseCheck" 2>&1 || true
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ==============================================================================
# CHECK 3: Linting ruff (F821 seulement)
# ==============================================================================
echo "3️⃣  Vérification linting (F821 - undefined names)"

if ruff check dqf/checks/base.py --select F821 2>&1 | grep -q "All checks passed\|Found 0 errors"; then
    echo -e "${GREEN}✅ Aucune erreur F821${NC}"
else
    echo -e "${RED}❌ Erreurs F821 détectées:${NC}"
    ruff check dqf/checks/base.py --select F821 2>&1 || true
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ==============================================================================
# CHECK 4: Variable 'issues' dans _create_result
# ==============================================================================
echo "4️⃣  Vérification variable 'issues'"

if grep -q "issues=issues or \[\]" dqf/checks/base.py; then
    # Vérifier si paramètre défini
    if grep -B5 "issues=issues or \[\]" dqf/checks/base.py | grep -q "issues: Optional\[List\[CheckIssue\]\]"; then
        echo -e "${GREEN}✅ Variable 'issues' correctement définie comme paramètre${NC}"
    else
        echo -e "${RED}❌ Variable 'issues' utilisée mais non définie${NC}"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${GREEN}✅ Pas d'utilisation de 'issues' dans _create_result (OK)${NC}"
fi

echo ""

# ==============================================================================
# CHECK 5: Tests unitaires base_check
# ==============================================================================
echo "5️⃣  Tests unitaires test_base_check.py"

if pytest tests/unit/test_base_check.py -v --tb=short 2>&1 | grep -q "passed"; then
    PASSED=$(pytest tests/unit/test_base_check.py -v 2>&1 | grep -o "[0-9]* passed" | cut -d' ' -f1)
    echo -e "${GREEN}✅ Tests base_check: $PASSED passés${NC}"
else
    echo -e "${RED}❌ Tests base_check échouent${NC}"
    pytest tests/unit/test_base_check.py -v --tb=short 2>&1 | tail -30 || true
    ERRORS=$((ERRORS + 1))
fi

echo ""

# ==============================================================================
# CHECK 6: Examples fonctionnent
# ==============================================================================
echo "6️⃣  Vérification examples (import only)"

for example in examples/01_basic_validation.py examples/03_batch_processing.py examples/04_custom_check.py; do
    if python3 -c "import sys; sys.path.insert(0, '.'); exec(open('$example').read().split('if __name__')[0])" 2>/dev/null; then
        echo -e "${GREEN}✅ $example (imports OK)${NC}"
    else
        echo -e "${RED}❌ $example (imports échouent)${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""

# ==============================================================================
# CHECK 7: Build module disponible
# ==============================================================================
echo "7️⃣  Vérification module 'build'"

if python3 -c "import build; print('OK')" 2>/dev/null; then
    echo -e "${GREEN}✅ Module 'build' disponible${NC}"
else
    echo -e "${YELLOW}⚠️  Module 'build' non disponible${NC}"
    echo "   Relancer: nix develop (pour recharger flake.nix)"
fi

echo ""

# ==============================================================================
# RÉSUMÉ
# ==============================================================================
echo "==========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TOUTES LES VÉRIFICATIONS PASSÉES ($ERRORS erreurs)${NC}"
    echo ""
    echo "Prochaine étape recommandée:"
    echo "  just sanitize    # Vérification complète + tests"
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERREUR(S) DÉTECTÉE(S)${NC}"
    echo ""
    echo "Actions:"
    echo "  1. Relire logs ci-dessus"
    echo "  2. Relancer: ./fix_critical_issues_v2.sh"
    exit 1
fi
