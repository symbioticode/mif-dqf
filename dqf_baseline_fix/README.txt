# DQF v1.0.0 - CORRECTIONS CRITIQUES
# Date: 3 février 2026

## Contenu de ce dossier:

### Fichiers Corrigés (à copier dans votre repo)
1. base.py              → dqf/checks/base.py
2. flake.nix            → flake.nix (racine)
3. pyproject.toml       → pyproject.toml (racine)

### Scripts de Correction (à copier dans scripts/)
4. fix_critical_issues_v2.sh  → scripts/
5. verify_fixes.sh            → scripts/

### Documentation
6. GUIDE_CORRECTION_COMPLETE.md  → Guide complet étape par étape
7. justfile_critical_fixes.txt   → Targets à ajouter dans justfile

## PROCÉDURE RAPIDE:

Dans votre repo mif-dqf:

1. Copier fichiers corrigés:
   cp base.py dqf/checks/base.py
   cp flake.nix flake.nix
   cp pyproject.toml pyproject.toml
   cp fix_critical_issues_v2.sh scripts/
   cp verify_fixes.sh scripts/
   chmod +x scripts/*.sh

2. Relancer environnement Nix:
   exit
   nix develop

3. Exécuter corrections:
   ./scripts/fix_critical_issues_v2.sh

4. Vérifier:
   ./scripts/verify_fixes.sh

5. Baseline complète:
   just sanitize
   python scripts/test_baseline_v1.0.0.py

RÉSULTAT ATTENDU: 5/5 checks ✅ PASS

Lire GUIDE_CORRECTION_COMPLETE.md pour détails complets.
