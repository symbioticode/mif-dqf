#!/bin/bash
# fix_remaining_issues.sh - Correction des 3 problèmes restants du baseline

set -e

echo "🔧 CORRECTION PROBLÈMES RESTANTS - DQF v1.0.0"
echo "============================================================"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ERRORS=0

# =============================================================================
# FIX 1: Corriger test_baseline_v1.0.0.py (--quiet non supporté)
# =============================================================================
echo "1️⃣  Correction argument --quiet dans test_baseline_v1.0.0.py"

if [ -f "scripts/test_baseline_v1.0.0.py" ]; then
    # Retirer --quiet de la commande build
    if grep -q "python -m build --quiet" scripts/test_baseline_v1.0.0.py; then
        sed -i 's/python -m build --quiet/python -m build/' scripts/test_baseline_v1.0.0.py
        echo -e "${GREEN}   ✅ Retiré '--quiet' de la commande build${NC}"
    else
        echo -e "${GREEN}   ✅ Argument '--quiet' déjà absent${NC}"
    fi
else
    echo -e "${RED}   ❌ scripts/test_baseline_v1.0.0.py non trouvé${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# =============================================================================
# FIX 2: Corriger examples/03_batch_processing.py
# =============================================================================
echo "2️⃣  Vérification examples/03_batch_processing.py"

if [ -f "examples/03_batch_processing.py" ]; then
    # Tester l'example
    if python examples/03_batch_processing.py 2>&1 | grep -q "Error\|Traceback"; then
        echo -e "${YELLOW}   ⚠️  Example 03_batch_processing.py a des erreurs${NC}"
        echo "      Analyse détaillée:"
        
        # Essayer de comprendre l'erreur
        python examples/03_batch_processing.py 2>&1 | tail -20 | head -10
        
        echo ""
        echo "   Action recommandée: Vérifier le fichier manuellement"
        echo "   Commande: python examples/03_batch_processing.py"
        ERRORS=$((ERRORS + 1))
    else
        echo -e "${GREEN}   ✅ Example fonctionne${NC}"
    fi
else
    echo -e "${RED}   ❌ examples/03_batch_processing.py non trouvé${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# =============================================================================
# FIX 3: Références obsolètes (yourusername, email, examples_errors)
# =============================================================================
echo "3️⃣  Correction références obsolètes"

# Liste des remplacements
declare -A REPLACEMENTS=(
    ["yourusername"]="symbioticode"
    ["your\.email@example\.com"]="corail.synergia@proton.me"
    ["your-email@example\.com"]="corail.synergia@proton.me"
)

for pattern in "${!REPLACEMENTS[@]}"; do
    replacement="${REPLACEMENTS[$pattern]}"
    
    # Compter occurrences
    count=$(grep -r "$pattern" --include="*.md" --include="*.toml" --include="*.py" . 2>/dev/null | wc -l || echo 0)
    
    if [ "$count" -gt 0 ]; then
        echo -e "${YELLOW}   → Remplacement: $pattern → $replacement ($count occurrences)${NC}"
        
        # Faire remplacement
        find . -type f \( -name "*.md" -o -name "*.toml" -o -name "*.py" \) \
            -exec sed -i "s|$pattern|$replacement|g" {} \; 2>/dev/null || true
        
        echo -e "${GREEN}     ✅ Remplacé${NC}"
    else
        echo -e "${GREEN}   ✅ Aucune occurrence '$pattern'${NC}"
    fi
done

echo ""

# Retrait références examples_errors
echo "   → Retrait références 'examples_errors'"

examples_errors_count=$(grep -r "examples_errors" --include="*.md" --include="*.py" . 2>/dev/null | wc -l || echo 0)

if [ "$examples_errors_count" -gt 0 ]; then
    echo -e "${YELLOW}     Trouvé $examples_errors_count occurrence(s)${NC}"
    
    # Supprimer lignes contenant examples_errors
    find . -type f \( -name "*.md" -o -name "*.py" \) -exec grep -l "examples_errors" {} \; 2>/dev/null | while read file; do
        sed -i '/examples_errors/d' "$file"
        echo -e "     ✓ Nettoyé: $file"
    done
    
    echo -e "${GREEN}     ✅ Références retirées${NC}"
else
    echo -e "${GREEN}     ✅ Aucune référence 'examples_errors'${NC}"
fi

echo ""

# =============================================================================
# VÉRIFICATION FINALE
# =============================================================================
echo "============================================================"
echo "🧪 VÉRIFICATION FINALE"
echo "============================================================"
echo ""

# Test 1: Build sans --quiet
echo "Test 1: Build package"
if python -m build --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Module build disponible${NC}"
else
    echo -e "${RED}❌ Module build non disponible${NC}"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# Test 2: Références obsolètes
echo "Test 2: Vérification références obsolètes"

remaining_issues=0

if grep -r "yourusername" --include="*.md" --include="*.toml" . 2>/dev/null | grep -v ".git" > /dev/null; then
    echo -e "${RED}❌ Encore des références 'yourusername'${NC}"
    remaining_issues=$((remaining_issues + 1))
else
    echo -e "${GREEN}✅ Aucune référence 'yourusername'${NC}"
fi

if grep -r "your.*email@example\.com" --include="*.md" --include="*.toml" . 2>/dev/null | grep -v ".git" > /dev/null; then
    echo -e "${RED}❌ Encore des références 'your.email@example.com'${NC}"
    remaining_issues=$((remaining_issues + 1))
else
    echo -e "${GREEN}✅ Aucune référence 'your.email@example.com'${NC}"
fi

if grep -r "examples_errors" --include="*.md" --include="*.py" . 2>/dev/null | grep -v ".git" > /dev/null; then
    echo -e "${RED}❌ Encore des références 'examples_errors'${NC}"
    remaining_issues=$((remaining_issues + 1))
else
    echo -e "${GREEN}✅ Aucune référence 'examples_errors'${NC}"
fi

ERRORS=$((ERRORS + remaining_issues))

echo ""

# =============================================================================
# RÉSUMÉ
# =============================================================================
echo "============================================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ TOUTES LES CORRECTIONS APPLIQUÉES${NC}"
    echo ""
    echo "Prochaine étape:"
    echo "  python scripts/test_baseline_v1.0.0.py"
    echo ""
    exit 0
else
    echo -e "${RED}❌ $ERRORS PROBLÈME(S) RESTANT(S)${NC}"
    echo ""
    echo "Vérifier logs ci-dessus pour détails"
    exit 1
fi