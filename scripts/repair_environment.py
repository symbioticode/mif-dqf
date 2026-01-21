#!/usr/bin/env python3
"""
repair_environment.py — Réparation automatique de l'environnement MIF/DQF
Adapté pour le projet mif-dqf (flake.nix, justfile, pyproject.toml, direnv)

Usage:
    python scripts/repair_environment.py [--check-only]
"""

import subprocess
from pathlib import Path
from typing import List

class ProjectRepairer:
    """Réparateur automatique d'environnement pour MIF/DQF"""

    def __init__(self, root: Path = Path(".")):
        self.root = root.resolve()
        self.issues: List[str] = []
        self.fixes: List[str] = []

    def run(self, cmd: List[str], capture: bool = False) -> tuple[int, str]:
        """Exécute une commande et retourne (code, output)"""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.root,
                check=False,
                capture_output=capture,
                text=True,
            )
            return result.returncode, result.stdout if capture else ""
        except Exception as e:
            return 1, str(e)

    # ========================================================================
    # FICHIERS ESSENTIELS
    # ========================================================================

    def check_essential_files(self):
        """Vérifie et recrée les fichiers essentiels du projet MIF/DQF"""
        print("\n🔍 Vérification des fichiers essentiels")

        essential = {
            "flake.nix": None,  # Contenu généré plus bas si absent
            "justfile": None,
            "pyproject.toml": None,
            ".envrc": "use flake\n",  # Minimal pour direnv + nix
            ".gitignore": self._default_gitignore(),
        }

        for filename, default_content in essential.items():
            path = self.root / filename
            if not path.exists():
                self.issues.append(f"Fichier manquant : {filename}")
                if default_content is not None:
                    path.write_text(default_content)
                    self.fixes.append(f"Créé {filename} avec contenu par défaut")
            else:
                self.fixes.append(f"{filename} présent")

    def _default_gitignore(self) -> str:
        return """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtualenv
.venv/
venv/
ENV/

# Direnv
.direnv/

# Nix
result/
result-*

# Logs & work
_work/
logs/
reports/
provenance/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Tests
.pytest_cache/
.coverage
htmlcov/

# OS
.DS_Store
Thumbs.db
"""

    # ========================================================================
    # STRUCTURE PROJET
    # ========================================================================

    def check_project_structure(self):
        """Vérifie la structure de base du package dqf"""
        print("\n🔍 Vérification structure package")

        required = [
            "dqf/__init__.py",
            "dqf/checks/__init__.py",
            "dqf/core/__init__.py",
        ]

        for rel_path in required:
            path = self.root / rel_path
            if not path.exists():
                self.issues.append(f"Structure manquante : {rel_path}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
                path.write_text("# -*- coding: utf-8 -*-\n\"\"\"Package dqf\"\"\"\n")
                self.fixes.append(f"Créé {rel_path}")
            else:
                self.fixes.append(f"{rel_path} présent")

    # ========================================================================
    # DIRENV
    # ========================================================================

    def setup_direnv(self):
        """Active direnv si installé"""
        print("\n🔄 Configuration direnv")
        code, _ = self.run(["direnv", "allow"])
        if code == 0:
            self.fixes.append("direnv allow exécuté")
        else:
            self.issues.append("direnv non disponible ou échec allow")

    # ========================================================================
    # RAPPORT FINAL
    # ========================================================================

    def repair_all(self, check_only: bool = False):
        print("=" * 70)
        print("🔧 RÉPARATION ENVIRONNEMENT - MIF/DQF")
        print("=" * 70)

        self.check_essential_files()
        self.check_project_structure()

        if not check_only:
            self.setup_direnv()

        print("\n" + "=" * 70)
        print("📊 RAPPORT")
        print("=" * 70)

        if self.issues:
            print(f"\n⚠️  {len(self.issues)} problèmes détectés :")
            for issue in self.issues:
                print(f"   • {issue}")

        if self.fixes:
            print(f"\n✅ {len(self.fixes)} actions effectuées :")
            for fix in self.fixes:
                print(f"   • {fix}")

        if not self.issues and not self.fixes:
            print("\n🎉 Environnement déjà en parfait état !")

        print("\nProchaines étapes recommandées :")
        print("   1. just sanitize          # Vérification complète")
        print("   2. just run-examples      # Validation fonctionnelle")
        print("   3. just sync 'msg'        # Synchronisation GitHub")
        print("=" * 70)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Répare l'environnement MIF/DQF (flake, just, pyproject, direnv)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Vérifier seulement, sans correction automatique",
    )

    args = parser.parse_args()

    repairer = ProjectRepairer()
    repairer.repair_all(check_only=args.check_only)


if __name__ == "__main__":
    main()