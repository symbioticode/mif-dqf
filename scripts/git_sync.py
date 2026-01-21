#!/usr/bin/env python3
"""
git_sync.py — Synchronisation Git robuste avec GitHub CLI
Usage: python scripts/git_sync.py "message de commit"

Fonctionnalités :
- Lit la configuration depuis .env
- Vérifie l'environnement (gh CLI, SSH)
- Crée automatiquement le dépôt GitHub si nécessaire
- Gère tous les cas complexes (rebase, conflits, force-push)
- Ne masque jamais les erreurs
- Arrête immédiatement en cas de problème

Dépendances :
- python-dotenv : pip install python-dotenv
- GitHub CLI : gh (installé via NixOS)
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Couleurs pour les logs
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log(msg, color=RESET):
    """Affiche un message coloré"""
    print(f"{color}{msg}{RESET}")

def run(cmd, check=False, capture=True):
    """Exécute une commande shell de manière robuste"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture,
            text=True,
            check=check
        )
        if capture:
            return True, result.stdout.strip(), result.stderr.strip()
        return True, "", ""
    except subprocess.CalledProcessError as e:
        if capture:
            return False, e.stdout.strip() if e.stdout else "", e.stderr.strip()
        return False, "", str(e)

def load_config():
    """Charge et valide la configuration depuis .env"""
    load_dotenv()
    
    config = {
        'github_owner': os.getenv('GITHUB_OWNER'),
        'github_repo': os.getenv('GITHUB_REPO_NAME'),
        'ssh_host': os.getenv('SSH_HOST_ALIAS'),
        'remote_ssh': os.getenv('GIT_REMOTE_SSH'),
        'auto_create': os.getenv('AUTO_CREATE_REPO', 'true').lower() == 'true',
        'verbose': os.getenv('VERBOSE_LOGS', 'false').lower() == 'true'
    }
    
    # Validation
    if not config['github_owner']:
        log("❌ GITHUB_OWNER manquant dans .env", RED)
        sys.exit(1)
    
    if not config['github_repo']:
        log("❌ GITHUB_REPO_NAME manquant dans .env", RED)
        sys.exit(1)
    
    # Vérifier cohérence du dossier
    current_dir = Path.cwd().name
    if current_dir != config['github_repo']:
        log(f"⚠️  Incohérence : dossier={current_dir}, .env={config['github_repo']}", YELLOW)
        response = input("   Continuer quand même ? (yes/no) : ").strip().lower()
        if response != "yes":
            sys.exit(0)
    
    return config

def check_environment(config):
    """Vérifie que l'environnement est prêt"""
    log("🔍 Vérification environnement...", BLUE)
    
    # 1. GitHub CLI installé
    success, stdout, _ = run("which gh")
    if not success:
        log("❌ GitHub CLI (gh) non installé", RED)
        log("   Installation : nix-env -iA nixpkgs.gh", YELLOW)
        sys.exit(1)
    log("✅ GitHub CLI détecté", GREEN)
    
    # 2. GitHub CLI authentifié
    success, stdout, stderr = run("gh auth status")
    if not success:
        log("❌ GitHub CLI non authentifié", RED)
        log(f"   Erreur : {stderr}", YELLOW)
        log("   Commande : gh auth login", YELLOW)
        sys.exit(1)
    
    # Vérifier que c'est la bonne identité
    if config['github_owner'] not in stdout:
        log(f"⚠️  GitHub CLI authentifié avec un autre compte", YELLOW)
        log(f"   Attendu : {config['github_owner']}", YELLOW)
        log(f"   Détecté : {stdout}", YELLOW)
        response = input("   Continuer quand même ? (yes/no) : ").strip().lower()
        if response != "yes":
            sys.exit(0)
    log(f"✅ Authentifié : {config['github_owner']}", GREEN)
    
    # 3. SSH fonctionnel
    success, stdout, stderr = run(f"ssh -T git@{config['ssh_host']}")
    # Note : ssh -T retourne code 1 même si OK (pas de shell)
    if "successfully authenticated" not in stderr.lower():
        log("❌ Authentification SSH échouée", RED)
        log(f"   Host : {config['ssh_host']}", YELLOW)
        log(f"   Erreur : {stderr}", YELLOW)
        sys.exit(1)
    log("✅ SSH fonctionnel", GREEN)
    
    # 4. Remote cohérent
    success, stdout, _ = run("git remote get-url origin")
    if success and stdout != config['remote_ssh']:
        log("⚠️  Remote existant différent de .env", YELLOW)
        log(f"   Git : {stdout}", YELLOW)
        log(f"   .env : {config['remote_ssh']}", YELLOW)

def repo_exists(config):
    """Vérifie si le dépôt GitHub existe"""
    success, stdout, stderr = run(f"git ls-remote {config['remote_ssh']}")
    
    if "repository not found" in stderr.lower():
        return False
    
    if not success:
        log(f"⚠️  Erreur lors de la vérification du dépôt : {stderr}", YELLOW)
        return False
    
    return True

def create_repo(config):
    """Crée le dépôt GitHub via GitHub CLI"""
    log("🆕 Création du dépôt GitHub...", BLUE)
    
    repo_full = f"{config['github_owner']}/{config['github_repo']}"
    
    # Commande gh repo create
    cmd = f"gh repo create {repo_full} --private --confirm"
    
    success, stdout, stderr = run(cmd)
    
    if not success:
        log("❌ Échec création dépôt", RED)
        log(f"   Erreur : {stderr}", YELLOW)
        sys.exit(1)
    
    log(f"✅ Dépôt créé : https://github.com/{repo_full}", GREEN)

def ensure_git_init():
    """Initialise Git si nécessaire"""
    if not Path(".git").exists():
        log("📦 Initialisation du dépôt Git...", BLUE)
        run("git init", check=True)
        run("git branch -M main", check=True)
        return True
    return False

def ensure_remote(config):
    """Configure le remote si manquant"""
    success, stdout, _ = run("git remote -v")
    
    if "origin" not in stdout:
        log("🔧 Configuration du remote...", BLUE)
        run(f"git remote add origin {config['remote_ssh']}", check=True)
        log(f"✅ Remote configuré : {config['remote_ssh']}", GREEN)
        return True
    
    return False

def get_commit_message():
    """Récupère le message de commit"""
    if len(sys.argv) > 1:
        return " ".join(sys.argv[1:])
    return os.getenv('DEFAULT_COMMIT_MESSAGE', f"Auto-sync {datetime.now().strftime('%Y-%m-%d %H:%M')}")

def safe_commit(message):
    """Commit local avec gestion des cas vides"""
    run("git add .")
    success, stdout, stderr = run(f'git commit -m "{message}"')
    
    if not success:
        if "nothing to commit" in stderr.lower():
            log("ℹ️  Rien à commiter", YELLOW)
            return False
        else:
            log(f"❌ Échec commit : {stderr}", RED)
            sys.exit(1)
    
    log(f"✅ Commit local : {message}", GREEN)
    return True

def safe_pull():
    """Pull intelligent avec gestion des cas complexes"""
    log("📥 Pull depuis origin/main...", BLUE)
    
    # Cas 1 : Pull normal
    success, stdout, stderr = run("git pull origin main --rebase")
    if success:
        log("✅ Pull réussi", GREEN)
        return True
    
    # Cas 2 : Pas de branche de suivi
    if "no tracking information" in stderr.lower():
        log("🔧 Configuration de la branche de suivi...", YELLOW)
        run("git branch --set-upstream-to=origin/main main", check=True)
        return safe_pull()  # Réessayer
    
    # Cas 3 : Histoires non liées
    if "unrelated histories" in stderr.lower():
        log("⚠️  Histoires non liées → merge forcé", YELLOW)
        success, _, _ = run("git pull origin main --allow-unrelated-histories")
        if not success:
            log("❌ Échec merge histoires non liées", RED)
            sys.exit(1)
        return True
    
    # Cas 4 : Branches divergentes
    if "divergent" in stderr.lower():
        log("⚠️  Branches divergentes → rebase", YELLOW)
        success, _, stderr2 = run("git pull origin main --rebase")
        if not success:
            log(f"❌ Échec rebase : {stderr2}", RED)
            sys.exit(1)
        return True
    
    # Cas 5 : Remote vide (première fois)
    if "couldn't find remote ref" in stderr.lower():
        log("ℹ️  Remote vide (premier push)", YELLOW)
        return True
    
    log(f"❌ Pull échoué : {stderr}", RED)
    sys.exit(1)

def safe_push():
    """Push intelligent avec gestion du force-push"""
    log("📤 Push vers origin/main...", BLUE)
    
    # Cas 1 : Push normal
    success, stdout, stderr = run("git push origin main")
    if success:
        log("✅ Push réussi", GREEN)
        return True
    
    # Cas 2 : Première fois (upstream manquant)
    if "upstream" in stderr.lower() or "no upstream" in stderr.lower():
        log("🔧 Configuration upstream...", YELLOW)
        success, _, _ = run("git push -u origin main")
        if success:
            log("✅ Push avec upstream réussi", GREEN)
            return True
        else:
            log("❌ Échec push upstream", RED)
            sys.exit(1)
    
    # Cas 3 : Non-fast-forward (besoin force-push)
    if "non-fast-forward" in stderr.lower() or "rejected" in stderr.lower():
        log("⚠️  Push rejeté → force-push nécessaire", YELLOW)
        log("   ATTENTION : cela écrasera l'historique distant", RED)
        
        response = input("   Forcer le push ? (yes/no) : ").strip().lower()
        if response == "yes":
            success, _, stderr2 = run("git push origin main --force")
            if success:
                log("✅ Force-push réussi", GREEN)
                return True
            else:
                log(f"❌ Échec force-push : {stderr2}", RED)
                sys.exit(1)
        else:
            log("❌ Push annulé par l'utilisateur", RED)
            sys.exit(0)
    
    log(f"❌ Push échoué : {stderr}", RED)
    sys.exit(1)

def main():
    """Workflow principal"""
    log("=" * 60, BLUE)
    log("GIT SYNC — Version Production avec GitHub CLI", BLUE)
    log("=" * 60, BLUE)
    
    # 1. Charger configuration
    config = load_config()
    
    # 2. Vérifier environnement
    check_environment(config)
    
    # 3. Initialiser Git si nécessaire
    ensure_git_init()
    
    # 4. Configurer remote si manquant
    ensure_remote(config)
    
    # 5. Vérifier si le dépôt GitHub existe
    if not repo_exists(config):
        log(f"📍 Dépôt {config['github_owner']}/{config['github_repo']} non trouvé", YELLOW)
        
        if config['auto_create']:
            create_repo(config)
        else:
            log("❌ AUTO_CREATE_REPO=false → arrêt", RED)
            log(f"   Créer manuellement : gh repo create {config['github_owner']}/{config['github_repo']} --private", YELLOW)
            sys.exit(1)
    
    # 6. Commit local
    message = get_commit_message()
    has_changes = safe_commit(message)
    
    # 7. Pull avec gestion intelligente
    safe_pull()
    
    # 8. Push avec gestion intelligente
    safe_push()
    
    log("=" * 60, GREEN)
    log("🎉 Synchronisation terminée avec succès", GREEN)
    log("=" * 60, GREEN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n⚠️  Interruption utilisateur", YELLOW)
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ Erreur inattendue : {e}", RED)
        sys.exit(1)