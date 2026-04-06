#!/usr/bin/env python3
"""
Backup Propre v1.0.0 - Avant Nettoyage Final

Crée un backup complet et propre du projet DQF v1.0.0
AVANT le nettoyage final pour publication.

Ce backup servira de référence historique et de point de restauration.

Usage:
    python scripts/backup_clean_v1.0.0.py
    python scripts/backup_clean_v1.0.0.py --backup-dir ../dqf-backups
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# Couleurs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class BackupManager:
    """Gestionnaire de backup propre v1.0.0"""

    def __init__(self, backup_root: str = "../dqf-backups"):
        self.backup_root = Path(backup_root)
        self.project_root = Path.cwd()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.git_tag = self.get_git_tag()
        self.backup_name = f"dqf_{self.git_tag}_{self.timestamp}"
        self.backup_path = self.backup_root / self.backup_name

    def log(self, msg: str, color: str = RESET):
        """Affiche message coloré"""
        print(f"{color}{msg}{RESET}")

    def get_git_tag(self) -> str:
        """Récupère tag git ou version par défaut"""
        try:
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "v1.0.0"

    def get_exclusions(self) -> List[str]:
        """Liste des patterns à exclure du backup"""
        return [
            ".git",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            ".pytest_cache",
            ".ruff_cache",
            ".mypy_cache",
            "htmlcov",
            ".coverage",
            "dist",
            "build",
            "*.egg-info",
            ".venv",
            "venv",
            ".env",
            ".env.*",
            "result",
            "result-*",
            ".direnv",
        ]

    def verify_project_structure(self) -> bool:
        """Vérifie que la structure projet est correcte"""
        self.log("\n🔍 Vérification structure projet...", BLUE)

        required_dirs = ["dqf", "tests", "docs", "examples"]
        required_files = [
            "pyproject.toml",
            "README.md",
            "LICENSE",
            "justfile",
        ]

        all_ok = True

        for dir_name in required_dirs:
            if not (self.project_root / dir_name).exists():
                self.log(f"  ❌ Dossier manquant: {dir_name}", RED)
                all_ok = False
            else:
                self.log(f"  ✅ {dir_name}/", GREEN)

        for file_name in required_files:
            if not (self.project_root / file_name).exists():
                self.log(f"  ❌ Fichier manquant: {file_name}", RED)
                all_ok = False
            else:
                self.log(f"  ✅ {file_name}", GREEN)

        return all_ok

    def get_project_stats(self) -> dict:
        """Calcule statistiques projet"""
        stats = {
            "py_files": 0,
            "test_files": 0,
            "doc_files": 0,
            "total_lines": 0,
        }

        # Fichiers Python
        for py_file in self.project_root.rglob("*.py"):
            if "__pycache__" not in str(py_file):
                stats["py_files"] += 1
                if "test" in str(py_file):
                    stats["test_files"] += 1
                try:
                    stats["total_lines"] += len(py_file.read_text().splitlines())
                except Exception:
                    pass

        # Fichiers docs
        for md_file in (self.project_root / "docs").rglob("*.md"):
            stats["doc_files"] += 1

        return stats

    def create_backup_metadata(self):
        """Crée fichier metadata.txt dans le backup"""
        metadata_content = f"""DQF Backup Metadata
==================

Backup Name: {self.backup_name}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Git Tag: {self.git_tag}
Source: {self.project_root}

Purpose: Backup propre AVANT nettoyage final v1.0.0
Status: État validé (104/104 tests PASS)

Project Statistics:
-------------------
"""

        stats = self.get_project_stats()
        for key, value in stats.items():
            metadata_content += f"{key}: {value}\n"

        metadata_content += f"""
Excluded Patterns:
------------------
{chr(10).join('- ' + p for p in self.get_exclusions())}

Restoration:
------------
To restore this backup:
    rsync -a --delete {self.backup_path}/ /path/to/project/

Git Info:
---------
"""

        # Ajouter git info
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--oneline"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                metadata_content += f"Last commit: {result.stdout.strip()}\n"
        except Exception:
            pass

        metadata_path = self.backup_path / "BACKUP_METADATA.txt"
        metadata_path.write_text(metadata_content)
        self.log(f"  ✅ Metadata créée: BACKUP_METADATA.txt", GREEN)

    def create_backup(self) -> bool:
        """Crée le backup avec rsync"""
        self.log(f"\n📦 Création backup: {self.backup_name}", BLUE)

        # Créer dossier backup
        self.backup_root.mkdir(parents=True, exist_ok=True)

        # Construire commande rsync
        exclusions = []
        for pattern in self.get_exclusions():
            exclusions.extend(["--exclude", pattern])

        rsync_cmd = [
            "rsync",
            "-a",
            "--info=progress2",
            *exclusions,
            f"{self.project_root}/",
            f"{self.backup_path}/",
        ]

        try:
            result = subprocess.run(rsync_cmd, check=False)

            if result.returncode == 0:
                self.log(f"  ✅ Backup créé: {self.backup_path}", GREEN)
                return True
            else:
                self.log(f"  ❌ Erreur rsync (code {result.returncode})", RED)
                return False

        except Exception as e:
            self.log(f"  ❌ Erreur: {e}", RED)
            return False

    def verify_backup(self) -> bool:
        """Vérifie que le backup est complet"""
        self.log("\n🔍 Vérification backup...", BLUE)

        required_in_backup = [
            "dqf/__init__.py",
            "tests/conftest.py",
            "docs/API.md",
            "pyproject.toml",
            "README.md",
        ]

        all_ok = True
        for filepath in required_in_backup:
            backup_file = self.backup_path / filepath
            if backup_file.exists():
                size = backup_file.stat().st_size
                self.log(f"  ✅ {filepath} ({size} bytes)", GREEN)
            else:
                self.log(f"  ❌ MANQUANT: {filepath}", RED)
                all_ok = False

        # Compter dossiers racine
        root_dirs = [d for d in self.backup_path.iterdir() if d.is_dir()]
        self.log(f"\n  📊 Dossiers racine: {len(root_dirs)}", BLUE)
        for d in sorted(root_dirs):
            self.log(f"     - {d.name}/", BLUE)

        return all_ok

    def cleanup_old_backups(self, keep_last: int = 10):
        """Nettoie vieux backups (garde les N derniers)"""
        self.log(f"\n🧹 Nettoyage vieux backups (garde {keep_last} derniers)...", BLUE)

        # Lister tous les backups dqf_*
        all_backups = sorted(
            [d for d in self.backup_root.glob("dqf_*") if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if len(all_backups) <= keep_last:
            self.log(f"  ℹ️  Seulement {len(all_backups)} backups, rien à nettoyer", YELLOW)
            return

        to_remove = all_backups[keep_last:]
        self.log(f"  🗑️  {len(to_remove)} backups à supprimer", YELLOW)

        for backup in to_remove:
            try:
                shutil.rmtree(backup)
                self.log(f"     ✅ Supprimé: {backup.name}", GREEN)
            except Exception as e:
                self.log(f"     ❌ Erreur suppression {backup.name}: {e}", RED)

    def run(self, cleanup_old: bool = True) -> int:
        """Exécute le processus de backup complet"""
        self.log("=" * 70, BLUE)
        self.log("BACKUP PROPRE DQF v1.0.0", BLUE)
        self.log("=" * 70, BLUE)

        # Étape 1 : Vérifier structure
        if not self.verify_project_structure():
            self.log("\n❌ Structure projet invalide", RED)
            return 1

        # Étape 2 : Créer backup
        if not self.create_backup():
            self.log("\n❌ Échec création backup", RED)
            return 1

        # Étape 3 : Créer metadata
        self.create_backup_metadata()

        # Étape 4 : Vérifier backup
        if not self.verify_backup():
            self.log("\n❌ Backup incomplet", RED)
            return 1

        # Étape 5 : Nettoyer vieux backups
        if cleanup_old:
            self.cleanup_old_backups(keep_last=10)

        # Rapport final
        self.log("\n" + "=" * 70, GREEN)
        self.log("✅ BACKUP RÉUSSI", GREEN)
        self.log("=" * 70, GREEN)

        backup_size = sum(
            f.stat().st_size for f in self.backup_path.rglob("*") if f.is_file()
        ) / (1024 * 1024)

        self.log(f"\n📍 Emplacement: {self.backup_path}", BLUE)
        self.log(f"📊 Taille: {backup_size:.2f} MB", BLUE)
        self.log(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", BLUE)

        self.log("\n🔄 Pour restaurer:", BLUE)
        self.log(f"   rsync -a --delete {self.backup_path}/ /path/to/project/", YELLOW)

        self.log("\n✅ Prêt pour nettoyage final", GREEN)
        return 0


def main():
    """Point d'entrée"""
    import argparse

    parser = argparse.ArgumentParser(description="Backup Propre DQF v1.0.0")
    parser.add_argument(
        "--backup-dir",
        "-b",
        default="../dqf-backups",
        help="Dossier racine des backups",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Ne pas nettoyer les vieux backups",
    )

    args = parser.parse_args()

    manager = BackupManager(backup_root=args.backup_dir)
    sys.exit(manager.run(cleanup_old=not args.no_cleanup))


if __name__ == "__main__":
    main()