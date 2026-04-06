#!/usr/bin/env python3
"""
Restauration Backup Propre v1.0.0

Restaure le dernier backup validé (104/104 tests PASS)
et vérifie immédiatement la baseline.

Usage:
    python scripts/restore_clean_backup.py
    python scripts/restore_clean_backup.py --backup dqf_v1.0.0_20260125_230457
    python scripts/restore_clean_backup.py --verify-only
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Couleurs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class RestoreManager:
    """Gestionnaire de restauration propre"""

    def __init__(self, backup_dir: str = "../dqf-backups"):
        self.backup_dir = Path(backup_dir)
        self.project_root = Path.cwd()

    def log(self, msg: str, color: str = RESET):
        """Affiche message coloré"""
        print(f"{color}{msg}{RESET}")

    def run_cmd(self, cmd: List[str], capture: bool = True) -> Tuple[int, str, str]:
        """Exécute commande"""
        try:
            result = subprocess.run(
                cmd, capture_output=capture, text=True, check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def list_backups(self) -> List[Path]:
        """Liste backups disponibles (triés par date)"""
        if not self.backup_dir.exists():
            return []

        backups = sorted(
            [d for d in self.backup_dir.glob("dqf_*") if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        return backups

    def get_recommended_backup(self) -> Path:
        """Retourne le backup recommandé (dernier v1.0.0)"""
        backups = self.list_backups()

        # Chercher dernier v1.0.0
        for backup in backups:
            if "v1.0.0" in backup.name:
                return backup

        # Sinon, retourner le plus récent
        return backups[0] if backups else None

    def verify_backup_structure(self, backup_path: Path) -> bool:
        """Vérifie structure du backup"""
        self.log(f"\n🔍 Vérification structure backup: {backup_path.name}", BLUE)

        required = [
            "dqf/__init__.py",
            "tests/conftest.py",
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "justfile",
        ]

        all_ok = True
        for filepath in required:
            if (backup_path / filepath).exists():
                self.log(f"  ✅ {filepath}", GREEN)
            else:
                self.log(f"  ❌ MANQUANT: {filepath}", RED)
                all_ok = False

        # Compter dossiers racine
        root_dirs = [d for d in backup_path.iterdir() if d.is_dir()]
        self.log(f"\n  📊 Dossiers racine: {len(root_dirs)}", BLUE)

        if len(root_dirs) < 8:
            self.log(
                f"  ⚠️  Backup potentiellement incomplet ({len(root_dirs)} dossiers)",
                YELLOW,
            )
            self.log("      Attendu: dqf, tests, docs, examples, scripts, config, _work, .github", YELLOW)

        return all_ok

    def create_pre_restore_backup(self) -> bool:
        """Crée backup pré-restauration"""
        self.log("\n📦 Backup pré-restauration...", BLUE)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_restore = self.backup_dir / f"pre_restore_{timestamp}"

        rsync_cmd = [
            "rsync",
            "-a",
            "--exclude",
            ".git",
            "--exclude",
            "__pycache__",
            "--exclude",
            ".pytest_cache",
            f"{self.project_root}/",
            f"{pre_restore}/",
        ]

        code, _, stderr = self.run_cmd(rsync_cmd)

        if code == 0:
            self.log(f"  ✅ Backup créé: {pre_restore.name}", GREEN)
            return True
        else:
            self.log(f"  ❌ Erreur: {stderr[:200]}", RED)
            return False

    def restore_backup(self, backup_path: Path) -> bool:
        """Restaure le backup"""
        self.log(f"\n🔄 Restauration depuis: {backup_path.name}", BLUE)

        rsync_cmd = [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            ".git",
            "--exclude",
            ".env",
            "--exclude",
            ".venv",
            f"{backup_path}/",
            f"{self.project_root}/",
        ]

        code, stdout, stderr = self.run_cmd(rsync_cmd)

        if code == 0:
            self.log("  ✅ Restauration réussie", GREEN)
            return True
        else:
            self.log(f"  ❌ Erreur: {stderr[:200]}", RED)
            return False

    def verify_dependencies(self) -> bool:
        """Vérifie et installe dépendances si nécessaire"""
        self.log("\n🔍 Vérification dépendances...", BLUE)

        # Vérifier si pandas est installé
        code, _, _ = self.run_cmd(["python", "-c", "import pandas"])

        if code != 0:
            self.log("  ⚠️  pandas non installé", YELLOW)
            self.log("  📦 Installation dépendances...", BLUE)

            code, _, stderr = self.run_cmd(["pip", "install", "-e", ".[dev]"])

            if code == 0:
                self.log("  ✅ Dépendances installées", GREEN)
                return True
            else:
                self.log(f"  ❌ Échec installation: {stderr[:200]}", RED)
                return False
        else:
            self.log("  ✅ Dépendances OK", GREEN)
            return True

    def verify_baseline(self) -> bool:
        """Vérifie baseline après restauration"""
        self.log("\n" + "=" * 70, BLUE)
        self.log("VÉRIFICATION BASELINE POST-RESTAURATION", BLUE)
        self.log("=" * 70, BLUE)

        all_ok = True

        # 1. Tests
        self.log("\n1️⃣  Tests pytest...", BLUE)
        code, stdout, stderr = self.run_cmd(
            ["pytest", "tests/", "-v", "--tb=short", "-q"]
        )

        if code == 0:
            # Extraire résultat
            for line in stdout.split("\n"):
                if "passed" in line.lower():
                    self.log(f"  ✅ {line.strip()}", GREEN)
                    break
        else:
            self.log(f"  ❌ Tests échoués", RED)
            self.log(f"  Stderr: {stderr[:300]}", YELLOW)
            all_ok = False

        # 2. Example basique
        self.log("\n2️⃣  Example basique...", BLUE)
        code, _, stderr = self.run_cmd(["python", "examples/01_basic_validation.py"])

        if code == 0:
            self.log("  ✅ Example fonctionne", GREEN)
        else:
            self.log(f"  ❌ Example échoué", RED)
            self.log(f"  Stderr: {stderr[:300]}", YELLOW)
            all_ok = False

        # 3. Linting (avec auto-fix)
        self.log("\n3️⃣  Linting (auto-fix)...", BLUE)
        
        # Auto-fix ruff
        code, _, _ = self.run_cmd(["ruff", "check", "--fix", "dqf", "tests", "examples"])
        
        # Format black
        code, _, _ = self.run_cmd(["black", "dqf", "tests", "examples"])
        
        # Vérifier après fix
        code, stdout, _ = self.run_cmd(["ruff", "check", "dqf", "tests", "examples"])

        if code == 0 or not stdout.strip():
            self.log("  ✅ Linting OK (après auto-fix)", GREEN)
        else:
            self.log(f"  ⚠️  Quelques warnings restants", YELLOW)
            # Ne pas bloquer pour warnings

        return all_ok

    def run(self, backup_name: str = None, verify_only: bool = False) -> int:
        """Exécute restauration complète"""
        self.log("=" * 70, BLUE)
        self.log("RESTAURATION BACKUP PROPRE v1.0.0", BLUE)
        self.log("=" * 70, BLUE)

        # Liste backups
        backups = self.list_backups()

        if not backups:
            self.log("\n❌ Aucun backup trouvé", RED)
            return 1

        # Sélectionner backup
        if backup_name:
            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                self.log(f"\n❌ Backup non trouvé: {backup_name}", RED)
                return 1
        else:
            backup_path = self.get_recommended_backup()

        self.log(f"\n📋 Backups disponibles:", BLUE)
        for i, backup in enumerate(backups[:10], 1):
            marker = "👉" if backup == backup_path else "  "
            self.log(f"  {marker} {i}. {backup.name}", BLUE)

        # Vérifier structure backup
        if not self.verify_backup_structure(backup_path):
            self.log("\n⚠️  Backup potentiellement incomplet", YELLOW)
            response = input("   Continuer quand même ? (yes/no): ").strip().lower()
            if response != "yes":
                return 0

        if verify_only:
            self.log("\n✅ Vérification terminée (--verify-only)", GREEN)
            return 0

        # Confirmation
        self.log(f"\n❓ Restaurer depuis: {backup_path.name} ?", YELLOW)
        self.log("   ATTENTION: Écrasera l'état actuel du projet", YELLOW)
        response = input("   Taper 'yes' pour confirmer: ").strip().lower()

        if response != "yes":
            self.log("  ℹ️  Restauration annulée", YELLOW)
            return 0

        # Backup pré-restauration
        if not self.create_pre_restore_backup():
            self.log("\n❌ Échec backup pré-restauration", RED)
            return 1

        # Restauration
        if not self.restore_backup(backup_path):
            self.log("\n❌ Échec restauration", RED)
            return 1

        # Vérifier dépendances
        if not self.verify_dependencies():
            self.log("\n⚠️  Problème dépendances (continuer...)", YELLOW)

        # Vérifier baseline
        if not self.verify_baseline():
            self.log("\n❌ Baseline invalide après restauration", RED)
            self.log("\n🔧 Actions correctives:", YELLOW)
            self.log("   1. Vérifier environnement Python", YELLOW)
            self.log("   2. Réinstaller: pip install -e '.[dev]'", YELLOW)
            self.log("   3. Relancer tests: pytest tests/ -v", YELLOW)
            return 1

        # Succès
        self.log("\n" + "=" * 70, GREEN)
        self.log("✅ RESTAURATION RÉUSSIE", GREEN)
        self.log("=" * 70, GREEN)

        self.log("\n🎯 Prochaines étapes:", BLUE)
        self.log("   1. Vérifier: git status", YELLOW)
        self.log("   2. Tester: pytest tests/ -v", YELLOW)
        self.log("   3. Tester: python examples/01_basic_validation.py", YELLOW)
        self.log("   4. Si OK → Restaurer docs un par un", YELLOW)

        return 0


def main():
    """Point d'entrée"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Restauration Backup Propre v1.0.0"
    )
    parser.add_argument(
        "--backup",
        "-b",
        help="Nom du backup à restaurer (ex: dqf_v1.0.0_20260125_230457)",
    )
    parser.add_argument(
        "--backup-dir",
        default="../dqf-backups",
        help="Dossier backups (défaut: ../dqf-backups)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Vérifier structure sans restaurer",
    )

    args = parser.parse_args()

    manager = RestoreManager(backup_dir=args.backup_dir)
    sys.exit(manager.run(backup_name=args.backup, verify_only=args.verify_only))


if __name__ == "__main__":
    main()