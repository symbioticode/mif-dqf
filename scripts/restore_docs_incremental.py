#!/usr/bin/env python3
"""
Restauration Incrémentale Documentation v1.0.0

Restaure les fichiers de documentation depuis le backup pre_restore_20260125_232052
UN PAR UN, en testant la non-régression après chaque fichier.

Usage:
    python scripts/restore_docs_incremental.py
    python scripts/restore_docs_incremental.py --dry-run
    python scripts/restore_docs_incremental.py --file README.md
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Couleurs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class IncrementalRestore:
    """Gestionnaire de restauration incrémentale"""

    def __init__(
        self,
        backup_path: str = "/home/andrei/Projects/09_MIF/01-DQF/dqf-backups/pre_restore_20260125_232052",
        dry_run: bool = False,
    ):
        self.backup_path = Path(backup_path)
        self.project_root = Path.cwd()
        self.dry_run = dry_run

        # Liste ordonnée des fichiers à restaurer (du moins au plus risqué)
        self.files_to_restore = [
            # Niveau 1 : Aucun impact code (safe)
            ".gitignore",
            "LICENSE",
            "docs/CHANGELOG.md",
            "CONTRIBUTING.md",
            "docs/DQF_PROJECT.md",
            
            # Niveau 2 : Documentation pure (safe)
            "README.md",
            "docs/TROUBLESHOOTING.md",
            
            # Niveau 3 : Documentation technique (vérifier références)
            "docs/ARCHITECTURE.md",
            "docs/API.md",
            
            # Niveau 4 : Configuration critique (ATTENTION)
            "pyproject.toml",
        ]

    def log(self, msg: str, color: str = RESET):
        """Affiche message coloré"""
        print(f"{color}{msg}{RESET}")

    def run_cmd(
        self, cmd: List[str], capture: bool = True
    ) -> Tuple[int, str, str]:
        """Exécute commande"""
        try:
            result = subprocess.run(
                cmd, capture_output=capture, text=True, check=False
            )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def verify_backup_exists(self) -> bool:
        """Vérifie que le backup source existe"""
        self.log("\n🔍 Vérification backup source...", BLUE)

        if not self.backup_path.exists():
            self.log(f"  ❌ Backup non trouvé: {self.backup_path}", RED)
            return False

        self.log(f"  ✅ Backup trouvé: {self.backup_path}", GREEN)

        # Vérifier fichiers présents
        missing = []
        for filepath in self.files_to_restore:
            if not (self.backup_path / filepath).exists():
                missing.append(filepath)

        if missing:
            self.log(f"  ⚠️  Fichiers manquants dans backup:", YELLOW)
            for f in missing:
                self.log(f"     - {f}", YELLOW)

        return True

    def create_safety_backup(self) -> bool:
        """Crée backup de sécurité avant modification"""
        if self.dry_run:
            self.log("  [DRY-RUN] Backup sécurité simulé", YELLOW)
            return True

        self.log("\n📦 Backup de sécurité...", BLUE)

        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup = self.project_root.parent / f"safety_backup_{timestamp}"

        rsync_cmd = [
            "rsync",
            "-a",
            "--exclude",
            ".git",
            "--exclude",
            "__pycache__",
            f"{self.project_root}/",
            f"{safety_backup}/",
        ]

        code, _, stderr = self.run_cmd(rsync_cmd)

        if code == 0:
            self.log(f"  ✅ Backup créé: {safety_backup}", GREEN)
            return True
        else:
            self.log(f"  ❌ Erreur: {stderr[:200]}", RED)
            return False

    def run_baseline_tests(self) -> bool:
        """Exécute tests baseline (104/104 expected)"""
        self.log("\n🧪 Tests baseline...", BLUE)

        # Utiliser sys.executable pour garantir bon Python
        import sys
        python_exe = sys.executable

        code, stdout, stderr = self.run_cmd(
            [python_exe, "-m", "pytest", "tests/", "-v", "--tb=short", "-q"]
        )

        if code == 0:
            # Extraire nombre tests
            for line in stdout.split("\n"):
                if "passed" in line.lower():
                    self.log(f"  ✅ {line.strip()}", GREEN)
                    break
            return True
        else:
            self.log(f"  ❌ Tests échoués", RED)
            # Afficher dernières lignes stderr
            stderr_lines = stderr.split("\n")[-10:]
            for line in stderr_lines:
                if line.strip():
                    self.log(f"     {line}", YELLOW)
            return False

    def run_example_test(self) -> bool:
        """Teste example basique"""
        self.log("\n📝 Test example basique...", BLUE)

        import sys
        python_exe = sys.executable

        code, stdout, stderr = self.run_cmd(
            [python_exe, "examples/01_basic_validation.py"]
        )

        if code == 0:
            self.log("  ✅ Example fonctionne", GREEN)
            return True
        else:
            self.log(f"  ❌ Example échoué", RED)
            self.log(f"  Stderr: {stderr[:300]}", YELLOW)
            return False

    def run_linting(self) -> bool:
        """Vérifie linting (avec auto-fix)"""
        self.log("\n🔍 Linting (auto-fix)...", BLUE)

        # Auto-fix
        self.run_cmd(["ruff", "check", "--fix", "dqf", "tests", "examples"])
        self.run_cmd(["black", "dqf", "tests", "examples"])

        # Vérifier
        code, stdout, _ = self.run_cmd(["ruff", "check", "dqf", "tests", "examples"])

        if code == 0 or not stdout.strip():
            self.log("  ✅ Linting OK", GREEN)
            return True
        else:
            # Ne pas bloquer pour warnings mineurs
            self.log(f"  ⚠️  Quelques warnings (non bloquant)", YELLOW)
            return True

    def verify_no_regression(self) -> bool:
        """Vérifie non-régression complète"""
        self.log("\n" + "=" * 70, BLUE)
        self.log("VÉRIFICATION NON-RÉGRESSION", BLUE)
        self.log("=" * 70, BLUE)

        all_ok = True

        # 1. Tests
        if not self.run_baseline_tests():
            all_ok = False

        # 2. Example
        if not self.run_example_test():
            all_ok = False

        # 3. Linting (non bloquant si warnings mineurs)
        self.run_linting()

        return all_ok

    def restore_file(self, filepath: str) -> bool:
        """Restaure un fichier depuis backup"""
        src = self.backup_path / filepath
        dst = self.project_root / filepath

        if not src.exists():
            self.log(f"  ⚠️  Fichier absent du backup: {filepath}", YELLOW)
            return False

        if self.dry_run:
            self.log(f"  [DRY-RUN] Restaurerait: {filepath}", YELLOW)
            return True

        # Créer dossier parent si nécessaire
        dst.parent.mkdir(parents=True, exist_ok=True)

        # Backup ancien fichier
        if dst.exists():
            backup_old = dst.with_suffix(dst.suffix + ".old")
            shutil.copy2(dst, backup_old)

        # Copier nouveau fichier
        shutil.copy2(src, dst)

        self.log(f"  ✅ Restauré: {filepath}", GREEN)
        return True

    def restore_single_file(self, filepath: str) -> int:
        """Restaure un fichier unique et teste"""
        self.log("=" * 70, BLUE)
        self.log(f"RESTAURATION: {filepath}", BLUE)
        self.log("=" * 70, BLUE)

        # 1. Restaurer fichier
        if not self.restore_file(filepath):
            return 1

        if self.dry_run:
            self.log("\n[DRY-RUN] Tests non-régression simulés", YELLOW)
            return 0

        # 2. Vérifier non-régression
        if not self.verify_no_regression():
            self.log(f"\n❌ RÉGRESSION DÉTECTÉE après {filepath}", RED)
            self.log("\n🔧 Actions:", YELLOW)
            self.log(f"   1. Restaurer ancien: mv {filepath}.old {filepath}", YELLOW)
            self.log("   2. Analyser différences", YELLOW)
            self.log("   3. Corriger fichier manuellement", YELLOW)
            return 1

        # 3. Commit (optionnel)
        self.log(f"\n✅ {filepath} OK - Pas de régression", GREEN)

        response = input("\n❓ Commiter ce fichier ? (yes/no/skip): ").strip().lower()

        if response == "yes":
            self.run_cmd(["git", "add", filepath])
            self.run_cmd(
                ["git", "commit", "-m", f"docs: restore verified {filepath}"]
            )
            self.log("  ✅ Commit effectué", GREEN)
        elif response == "skip":
            self.log("  ⏭️  Commit ignoré (fichier restauré mais non commité)", YELLOW)
        else:
            self.log("  ℹ️  Commit annulé", YELLOW)

        return 0

    def restore_all_incremental(self) -> int:
        """Restaure tous les fichiers un par un"""
        self.log("=" * 70, BLUE)
        self.log("RESTAURATION INCRÉMENTALE DOCUMENTATION v1.0.0", BLUE)
        self.log("=" * 70, BLUE)

        # Vérifier backup existe
        if not self.verify_backup_exists():
            return 1

        # Backup sécurité
        if not self.create_safety_backup():
            self.log("\n⚠️  Pas de backup sécurité (continuer ?)", YELLOW)
            response = input("   yes/no: ").strip().lower()
            if response != "yes":
                return 0

        # Vérifier baseline initiale
        self.log("\n" + "=" * 70, BLUE)
        self.log("BASELINE INITIALE (avant restauration)", BLUE)
        self.log("=" * 70, BLUE)

        if not self.verify_no_regression():
            self.log("\n❌ Baseline initiale invalide", RED)
            self.log("   Corriger d'abord l'état actuel", YELLOW)
            return 1

        self.log("\n✅ Baseline initiale OK - Début restauration...", GREEN)

        # Restaurer fichiers un par un
        restored = []
        failed = []

        for i, filepath in enumerate(self.files_to_restore, 1):
            self.log(f"\n{'=' * 70}", BLUE)
            self.log(f"[{i}/{len(self.files_to_restore)}] {filepath}", BLUE)
            self.log(f"{'=' * 70}", BLUE)

            result = self.restore_single_file(filepath)

            if result == 0:
                restored.append(filepath)
            else:
                failed.append(filepath)
                self.log(f"\n❌ Échec restauration: {filepath}", RED)

                response = input(
                    "\n❓ Continuer malgré l'échec ? (yes/abort): "
                ).strip().lower()

                if response != "yes":
                    break

        # Rapport final
        self.log("\n" + "=" * 70, GREEN if not failed else RED)
        self.log("RAPPORT FINAL RESTAURATION", GREEN if not failed else RED)
        self.log("=" * 70, GREEN if not failed else RED)

        self.log(f"\n📊 Fichiers restaurés: {len(restored)}/{len(self.files_to_restore)}", BLUE)
        for f in restored:
            self.log(f"  ✅ {f}", GREEN)

        if failed:
            self.log(f"\n❌ Fichiers échoués: {len(failed)}", RED)
            for f in failed:
                self.log(f"  ❌ {f}", RED)

        if not failed:
            self.log("\n🎉 RESTAURATION COMPLÈTE RÉUSSIE", GREEN)
            return 0
        else:
            self.log("\n⚠️  RESTAURATION PARTIELLE", YELLOW)
            return 1


def main():
    """Point d'entrée"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Restauration Incrémentale Documentation v1.0.0"
    )
    parser.add_argument(
        "--backup-path",
        "-b",
        default="/home/andrei/Projects/09_MIF/01-DQF/dqf-backups/pre_restore_20260125_232052",
        help="Chemin backup source",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Restaurer un fichier spécifique uniquement",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulation (ne restaure rien)",
    )

    args = parser.parse_args()

    restorer = IncrementalRestore(
        backup_path=args.backup_path, dry_run=args.dry_run
    )

    if args.file:
        # Restaurer fichier unique
        sys.exit(restorer.restore_single_file(args.file))
    else:
        # Restaurer tous
        sys.exit(restorer.restore_all_incremental())


if __name__ == "__main__":
    main()
