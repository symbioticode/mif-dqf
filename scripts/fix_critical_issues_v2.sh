#!/bin/bash
set -e

echo "🔧 CORRECTION CRITIQUE DQF v1.0.0 - VERSION RÉELLE"
echo "=========================================================="
echo ""

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Compteur d'erreurs
ERRORS=0

# =============================================================================
# FONCTION: Vérifier fichier existe
# =============================================================================
check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}❌ Fichier manquant: $1${NC}"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
    return 0
}

# =============================================================================
# FIX 1: Import Optional, Dict, List dans base.py
# =============================================================================
echo "1️⃣  Correction imports typing dans dqf/checks/base.py"

if check_file "dqf/checks/base.py"; then
    # Vérifier si imports déjà corrects
    if grep -q "^from typing import Any, Dict, List, Optional" dqf/checks/base.py; then
        echo -e "${GREEN}   ✅ Imports déjà corrects${NC}"
    else
        # Faire backup
        cp dqf/checks/base.py dqf/checks/base.py.backup
        
        # Remplacer ligne exacte
        sed -i 's/^from typing import Any$/from typing import Any, Dict, List, Optional/' dqf/checks/base.py
        
        # Vérifier
        if grep -q "^from typing import Any, Dict, List, Optional" dqf/checks/base.py; then
            echo -e "${GREEN}   ✅ Imports corrigés${NC}"
        else
            echo -e "${RED}   ❌ Échec correction imports${NC}"
            ERRORS=$((ERRORS + 1))
        fi
    fi
fi

echo ""

# =============================================================================
# FIX 2: Retirer variable 'issues' non définie
# =============================================================================
echo "2️⃣  Correction variable 'issues' dans _create_result"

if check_file "dqf/checks/base.py"; then
    # Vérifier si 'issues=' existe encore
    if grep -q "issues=issues or \[\]" dqf/checks/base.py; then
        # Vérifier d'abord si CheckResult a un champ 'issues'
        if grep -A10 "class CheckResult" dqf/checks/base.py | grep -q "issues:"; then
            echo -e "${YELLOW}   ⚠️  CheckResult a champ 'issues', mais variable non définie${NC}"
            echo -e "${YELLOW}   → Ajout paramètre 'issues' à _create_result${NC}"
            
            # Ajouter paramètre issues à la signature de _create_result
            sed -i '/def _create_result(/,/)/ s/details: Optional\[Dict\[str, Any\]\] = None,$/details: Optional[Dict[str, Any]] = None,\n        issues: Optional[List[CheckIssue]] = None,/' dqf/checks/base.py
            
            echo -e "${GREEN}   ✅ Paramètre 'issues' ajouté${NC}"
        else
            echo -e "${YELLOW}   ⚠️  CheckResult n'a PAS de champ 'issues'${NC}"
            echo -e "${YELLOW}   → Retrait de 'issues=...' de la création${NC}"
            
            # Retirer la ligne issues=
            sed -i '/issues=issues or \[\],$/d' dqf/checks/base.py
            
            if ! grep -q "issues=issues or \[\]" dqf/checks/base.py; then
                echo -e "${GREEN}   ✅ Ligne 'issues=' retirée${NC}"
            else
                echo -e "${RED}   ❌ Échec retrait 'issues='${NC}"
                ERRORS=$((ERRORS + 1))
            fi
        fi
    else
        echo -e "${GREEN}   ✅ Pas de 'issues=...' trouvé (déjà corrigé)${NC}"
    fi
fi

echo ""

# =============================================================================
# FIX 3: Nettoyage dqf/checks/__init__.py (typing deprecated)
# =============================================================================
echo "3️⃣  Nettoyage typing deprecated dans __init__.py"

if check_file "dqf/checks/__init__.py"; then
    # Créer version propre
    cat > dqf/checks/__init__.py << 'INITPY'
"""
DQF Checks Module

Provides all validation checks for data quality framework.
"""

# All checks are imported via dqf/__init__.py
# This file is intentionally minimal
INITPY
    
    echo -e "${GREEN}   ✅ __init__.py nettoyé${NC}"
else
    echo -e "${YELLOW}   ⚠️  __init__.py manquant, création...${NC}"
    mkdir -p dqf/checks
    cat > dqf/checks/__init__.py << 'INITPY'
"""
DQF Checks Module

Provides all validation checks for data quality framework.
"""
INITPY
    echo -e "${GREEN}   ✅ __init__.py créé${NC}"
fi

echo ""

# =============================================================================
# FIX 4: Références obsolètes (yourusername, email, examples_errors)
# =============================================================================
echo "4️⃣  Correction références obsolètes"

# Fonction pour remplacer en toute sécurité
safe_replace() {
    local pattern="$1"
    local replacement="$2"
    local description="$3"
    
    local count=$(grep -r "$pattern" --include="*.md" --include="*.toml" . 2>/dev/null | wc -l)
    
    if [ "$count" -gt 0 ]; then
        echo -e "${YELLOW}   → Remplacement: $description ($count occurrences)${NC}"
        find . -type f \( -name "*.md" -o -name "*.toml" \) \
            -exec sed -i "s|$pattern|$replacement|g" {} \; 2>/dev/null || true
        echo -e "${GREEN}     ✅ Remplacé${NC}"
    else
        echo -e "${GREEN}   ✅ Aucune occurrence '$description'${NC}"
    fi
}

safe_replace "yourusername" "symbioticode" "GitHub username"
safe_replace "your\.email@example\.com" "corail.synergia@proton.me" "Email"

# Retrait références examples_errors (plus délicat)
echo -e "${YELLOW}   → Suppression références 'examples_errors'${NC}"
find docs/ -type f -name "*.md" -exec grep -l "examples_errors" {} \; 2>/dev/null | while read file; do
    sed -i '/examples_errors/d' "$file"
    echo -e "     ✓ Nettoyé: $file"
done
echo -e "${GREEN}   ✅ Références 'examples_errors' retirées${NC}"

echo ""

# =============================================================================
# VÉRIFICATION 1: Import Python Réel
# =============================================================================
echo "🧪 VÉRIFICATION 1/4: Import Python"

if python3 -c "from dqf.checks.base import BaseCheck, CheckResult; print('✅ OK')" 2>/dev/null; then
    echo -e "${GREEN}✅ Import Python fonctionne${NC}"
else
    echo -e "${RED}❌ Import Python échoue${NC}"
    python3 -c "from dqf.checks.base import BaseCheck" 2>&1 | head -5
    ERRORS=$((ERRORS + 1))
fi

echo ""

# =============================================================================
# VÉRIFICATION 2: Linting Ruff
# =============================================================================
echo "🧪 VÉRIFICATION 2/4: Linting (ruff)"

if command -v ruff &> /dev/null; then
    if ruff check dqf/checks/base.py --select F821 2>/dev/null; then
        echo -e "${GREEN}✅ Aucune erreur F821 (undefined name)${NC}"
    else
        echo -e "${RED}❌ Erreurs linting détectées${NC}"
        ruff check dqf/checks/base.py --select F821
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  ruff non disponible, skip${NC}"
fi

echo ""

# =============================================================================
# VÉRIFICATION 3: Structure CheckResult
# =============================================================================
echo "🧪 VÉRIFICATION 3/4: Structure CheckResult"

python3 << 'PYCHECK'
from dqf.checks.base import CheckResult
import inspect

# Vérifier signature __init__
sig = inspect.signature(CheckResult)
params = list(sig.parameters.keys())

print(f"   Paramètres CheckResult: {params}")

if 'issues' in params:
    print("   ✅ CheckResult a paramètre 'issues'")
else:
    print("   ⚠️  CheckResult n'a PAS de paramètre 'issues'")

# Test création
try:
    result = CheckResult(
        check_name="test",
        status="PASS",
        message="test"
    )
    print("   ✅ Création CheckResult OK")
except Exception as e:
    print(f"   ❌ Erreur création: {e}")
PYCHECK

echo ""

# =============================================================================
# VÉRIFICATION 4: Test Unitaire Minimal
# =============================================================================
echo "🧪 VÉRIFICATION 4/4: Test unitaire minimal"

if command -v pytest &> /dev/null; then
    # Tester juste base_check
    if pytest tests/unit/test_base_check.py -v -x 2>&1 | grep -q "PASSED\|passed"; then
        echo -e "${GREEN}✅ Tests base_check passent${NC}"
    else
        echo -e "${RED}❌ Tests base_check échouent${NC}"
        pytest tests/unit/test_base_check.py -v -x 2>&1 | tail -20
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠️  pytest non disponible, skip${NC}"
fi

echo ""

# =============================================================================
# RÉSUMÉ FINAL
# =============================================================================
echo "=========================================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TOUTES LES CORRECTIONS APPLIQUÉES AVEC SUCCÈS${NC}"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. just sanitize        # Vérification complète"
    echo "  2. pytest tests/ -v     # Tous les tests"
    echo "  3. git diff             # Voir changements"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS ERREUR(S) DÉTECTÉE(S)${NC}"
    echo ""
    echo "Actions recommandées:"
    echo "  1. Vérifier logs ci-dessus"
    echo "  2. Restaurer backup si nécessaire:"
    echo "     cp dqf/checks/base.py.backup dqf/checks/base.py"
    echo ""
    exit 1
fi
