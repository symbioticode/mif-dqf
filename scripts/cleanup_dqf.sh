#!/usr/bin/env bash
# cleanup_dqf.sh
# Script de nettoyage final du projet DQF v1.0.0
# Supprime les fichiers temporaires, fake code, logs debug, backups et caches
# Auteur : Andrei
# Date   : 18 janvier 2026

set -euo pipefail  # Sécurité : arrêt sur erreur, variables non définies, pipe fail

echo "🧹 Début du nettoyage DQF - tout sera supprimé selon la liste validée"
echo "========================================================================"

# === 1. Scripts Temporaires ===
echo "1. Suppression des scripts temporaires et fake code..."
rm -f \
  add_enum_imports.py \
  analyze_failures.py \
  debug_config.py \
  debug_imports.py \
  debug_validation.py \
  fix_tests_progressive.py \
  migrate_tests.py \
  bootstrap_dqf_nix.sh \
  bootstrap.py \
  check_github_account.sh \
  cleanup.sh

# === 2. Logs Debug ===
echo "2. Suppression des logs et artifacts debug..."
rm -f diagnostic.txt failure_analysis.txt
rm -f docs/examples_errors_*.txt
rm -f docs/dqf_project_final.md  # gardé uniquement dans DQF_PROJECT.md

# === 3. Backups et Checkpoints ===
echo "3. Suppression des backups et checkpoints..."
rm -rf tests.backup/ tests.checkpoints/ 2>/dev/null || true

# === 4. Cache Python ===
echo "4. Suppression des caches Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# === 5. Work Directory - Provenance temporaire ===
echo "5. Suppression des provenance temporaires..."
rm -rf _work/dqf/provenance/ 2>/dev/null || true

# === 6. Divers ===
echo "6. Suppression des dossiers vides ou obsolètes..."
rm -rf scripts/old/ scripts/utils/ src/ 2>/dev/null || true
rm -f dqf/core/validator.py.txt 2>/dev/null || true

echo "========================================================================"
echo "✅ Nettoyage terminé avec succès"
echo "   - Scripts temporaires supprimés"
echo "   - Logs et artifacts debug effacés"
echo "   - Backups et caches nettoyés"
echo "   - Dossiers obsolètes vidés"
echo ""
echo "Projet DQF maintenant propre et prêt pour la version stable 1.0.0"
