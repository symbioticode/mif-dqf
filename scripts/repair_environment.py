#!/usr/bin/env python3
"""
repair_environment.py — Réparation automatique de l'environnement MIF/DQF
Adapté pour DQF v1.0.0 avec nouveau flake.nix (build tools inclus)

Usage:
    python scripts/repair_environment.py [--check-only]
    python scripts/repair_environment.py --verify-build
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

class ProjectRepairer:
    """Réparateur automatique d'environnement pour MIF/DQF v1.0.0"""

    def __init__(self, root: Path = Path(".")):
        self.root = root.resolve()
        self.issues: List[str] = []
        self.fixes: List[str] = []
        self.warnings: List[str] = []

    def run(self, cmd: List[str], capture: bool = False) -> Tuple[int, str]:
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
    # VÉRIFICATIONS CRITIQUES (alignées avec corrections v1.0.0)
    # ========================================================================

    def check_python_version(self):
        """Vérifie version Python 3.12+"""
        print("\n🐍 Vérification version Python")
        
        code, output = self.run(["python", "--version"], capture=True)
        if code == 0:
            version = output.strip()
            if "3.12" in version:
                self.fixes.append(f"Python version OK: {version}")
            else:
                self.warnings.append(f"Python {version} (attendu: 3.12.x)")
        else:
            self.issues.append("Python non disponible")

    def check_nix_environment(self):
        """Vérifie environnement Nix avec nouveau flake.nix"""
        print("\n❄️  Vérification environnement Nix")
        
        # Vérifier flake.nix existe
        flake_path = self.root / "flake.nix"
        if not flake_path.exists():
            self.issues.append("flake.nix manquant")
            return
        
        # Vérifier que flake.nix contient les build tools
        content = flake_path.read_text()
        required_packages = ["build", "setuptools", "wheel", "twine", "pytest-cov"]
        
        for pkg in required_packages:
            if pkg in content:
                self.fixes.append(f"flake.nix contient '{pkg}'")
            else:
                self.issues.append(f"flake.nix manque '{pkg}' dans pythonEnv")

    def check_critical_imports(self):
        """Vérifie que base.py a les imports typing complets"""
        print("\n📦 Vérification imports critiques (base.py)")
        
        base_path = self.root / "dqf" / "checks" / "base.py"
        if not base_path.exists():
            self.issues.append("dqf/checks/base.py manquant")
            return
        
        content = base_path.read_text()
        
        # Vérifier import typing complet
        required_imports = ["Any", "Dict", "List", "Optional"]
        import_line = None
        
        for line in content.split('\n'):
            if line.startswith("from typing import"):
                import_line = line
                break
        
        if import_line:
            missing = [imp for imp in required_imports if imp not in import_line]
            if missing:
                self.issues.append(f"Imports typing manquants dans base.py: {missing}")
            else:
                self.fixes.append("Imports typing complets dans base.py")
        else:
            self.issues.append("Aucun import typing trouvé dans base.py")

    def check_python_modules(self):
        """Vérifie disponibilité des modules Python critiques"""
        print("\n🔍 Vérification modules Python critiques")
        
        critical_modules = {
            "pandas": "pandas>=2.2.0",
            "numpy": "numpy>=1.26.0",
            "pytest": "pytest>=7.0.0",
            "build": "build",
            "ruff": "ruff",
            "black": "black",
        }
        
        for module, desc in critical_modules.items():
            code, _ = self.run(["python", "-c", f"import {module}"], capture=True)
            if code == 0:
                # Obtenir version si possible
                code_ver, version = self.run(
                    ["python", "-c", f"import {module}; print(getattr({module}, '__version__', 'unknown'))"],
                    capture=True
                )
                version_str = version.strip() if code_ver == 0 else "unknown"
                self.fixes.append(f"Module '{module}' disponible (v{version_str})")
            else:
                self.issues.append(f"Module '{module}' manquant ({desc})")

    def verify_build_system(self):
        """Vérifie que le système de build fonctionne"""
        print("\n🏗️  Vérification système de build")
        
        # Test 1: python -m build existe
        code, output = self.run(["python", "-m", "build", "--help"], capture=True)
        if code == 0:
            self.fixes.append("Module 'build' fonctionnel")
        else:
            self.issues.append("Module 'build' non fonctionnel")
            return
        
        # Test 2: Vérifier pyproject.toml
        pyproject_path = self.root / "pyproject.toml"
        if not pyproject_path.exists():
            self.issues.append("pyproject.toml manquant")
            return
        
        # Test 3: Vérifier config ruff moderne
        content = pyproject_path.read_text()
        if "[tool.ruff.lint]" in content:
            self.fixes.append("Configuration ruff moderne ([tool.ruff.lint])")
        else:
            self.warnings.append("Configuration ruff possiblement obsolète")

    def check_test_structure(self):
        """Vérifie structure des tests"""
        print("\n🧪 Vérification structure tests")
        
        test_files = [
            "tests/conftest.py",
            "tests/unit/test_base_check.py",
            "tests/integration/test_validator.py",
        ]
        
        for test_file in test_files:
            path = self.root / test_file
            if path.exists():
                self.fixes.append(f"Test présent: {test_file}")
            else:
                self.warnings.append(f"Test manquant: {test_file}")

    # ========================================================================
    # FICHIERS ESSENTIELS
    # ========================================================================

    def check_essential_files(self):
        """Vérifie et recrée les fichiers essentiels du projet MIF/DQF"""
        print("\n📄 Vérification des fichiers essentiels")

        essential = {
            "flake.nix": None,  # Ne pas recréer automatiquement
            "justfile": None,
            "pyproject.toml": None,
            ".envrc": "use flake\n",  # Minimal pour direnv + nix
            ".gitignore": self._default_gitignore(),
            "pytest.ini": self._default_pytest_ini(),
        }

        for filename, default_content in essential.items():
            path = self.root / filename
            if not path.exists():
                if default_content is not None:
                    path.write_text(default_content)
                    self.fixes.append(f"Créé {filename} avec contenu par défaut")
                else:
                    self.issues.append(f"Fichier critique manquant: {filename}")
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
.env

# Virtualenv
.venv/
venv/
ENV/

# Direnv
.direnv/

# Nix
result/
result-*
.devenv/

# Logs & work
_work/
logs/
reports/
provenance/
baseline_report_*.txt

# IDE
.idea/
.vscode/
*.swp
*.swo

# Tests
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/

# OS
.DS_Store
Thumbs.db

# Backup
*.bak
*.backup
*_backup/
"""

    def _default_pytest_ini(self) -> str:
        return """[pytest]
minversion = 7.0
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --strict-markers
    --tb=short
    --disable-warnings
markers =
    slow: marks tests as slow (deselect with '-m \"not slow\"')
    integration: marks tests as integration tests
"""

    # ========================================================================
    # STRUCTURE PROJET
    # ========================================================================

    def check_project_structure(self):
        """Vérifie la structure de base du package dqf"""
        print("\n📁 Vérification structure package")

        required = [
            "dqf/__init__.py",
            "dqf/checks/__init__.py",
            "dqf/checks/base.py",
            "dqf/core/__init__.py",
            "dqf/core/report.py",
            "dqf/core/validator.py",
        ]

        for rel_path in required:
            path = self.root / rel_path
            if not path.exists():
                if "__init__.py" in rel_path:
                    # Créer __init__.py minimal
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                    path.write_text('"""\nDQF Module\n"""\n')
                    self.fixes.append(f"Créé {rel_path}")
                else:
                    self.issues.append(f"Fichier manquant: {rel_path}")
            else:
                self.fixes.append(f"{rel_path} présent")

    # ========================================================================
    # DIRENV
    # ========================================================================

    def setup_direnv(self):
        """Active direnv si installé"""
        print("\n🔄 Configuration direnv")
        code, _ = self.run(["which", "direnv"], capture=True)
        if code != 0:
            self.warnings.append("direnv non installé (optionnel)")
            return
        
        code, _ = self.run(["direnv", "allow"])
        if code == 0:
            self.fixes.append("direnv allow exécuté")
        else:
            self.warnings.append("direnv allow échoué (vérifier manuellement)")

    # ========================================================================
    # TESTS DE VALIDATION
    # ========================================================================

    def run_validation_tests(self):
        """Exécute tests de validation rapides"""
        print("\n✅ Tests de validation")
        
        # Test 1: Import base.py
        code, output = self.run(
            ["python", "-c", "from dqf.checks.base import BaseCheck, CheckResult; print('OK')"],
            capture=True
        )
        if code == 0 and "OK" in output:
            self.fixes.append("Import dqf.checks.base: OK")
        else:
            self.issues.append("Import dqf.checks.base échoue")
        
        # Test 2: Ruff check F821
        code, output = self.run(
            ["ruff", "check", "dqf/checks/base.py", "--select", "F821"],
            capture=True
        )
        if code == 0:
            self.fixes.append("Ruff F821 (undefined names): OK")
        else:
            self.issues.append("Erreurs linting F821 détectées")
        
        # Test 3: pytest rapide
        code, _ = self.run(
            ["pytest", "tests/unit/test_base_check.py", "-q"],
            capture=True
        )
        if code == 0:
            self.fixes.append("Tests base_check: OK")
        else:
            self.warnings.append("Tests base_check ont des échecs")

    # ========================================================================
    # RAPPORT FINAL
    # ========================================================================

    def repair_all(self, check_only: bool = False, verify_build: bool = False):
        print("=" * 70)
        print("🔧 RÉPARATION ENVIRONNEMENT - DQF v1.0.0")
        print("=" * 70)

        # Vérifications critiques (alignées avec corrections v1.0.0)
        self.check_python_version()
        self.check_nix_environment()
        self.check_critical_imports()
        self.check_python_modules()
        
        if verify_build:
            self.verify_build_system()
        
        # Vérifications structure
        self.check_essential_files()
        self.check_project_structure()
        self.check_test_structure()

        # Actions (si pas check-only)
        if not check_only:
            self.setup_direnv()
            self.run_validation_tests()

        # Rapport final
        print("\n" + "=" * 70)
        print("📊 RAPPORT")
        print("=" * 70)

        if self.issues:
            print(f"\n❌ {len(self.issues)} problème(s) critique(s) détecté(s):")
            for issue in self.issues:
                print(f"   • {issue}")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} avertissement(s):")
            for warn in self.warnings:
                print(f"   • {warn}")

        if self.fixes:
            print(f"\n✅ {len(self.fixes)} vérification(s) réussie(s):")
            for fix in self.fixes:
                print(f"   • {fix}")

        if not self.issues and not self.warnings:
            print("\n🎉 Environnement en parfait état !")

        # Recommandations
        print("\n📋 Prochaines étapes recommandées:")
        if self.issues:
            print("   1. Corriger les problèmes critiques ci-dessus")
            print("   2. Relancer: python scripts/repair_environment.py")
        else:
            print("   1. just sanitize          # Vérification complète")
            print("   2. just test              # Tous les tests")
            print("   3. python -m build        # Build package")
        
        print("=" * 70)
        
        # Code de sortie
        return 0 if not self.issues else 1


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Répare l'environnement DQF v1.0.0 (aligné avec nouveau flake.nix)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Vérifier seulement, sans correction automatique",
    )
    parser.add_argument(
        "--verify-build",
        action="store_true",
        help="Vérifier également le système de build",
    )

    args = parser.parse_args()

    repairer = ProjectRepairer()
    exit_code = repairer.repair_all(
        check_only=args.check_only,
        verify_build=args.verify_build
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()