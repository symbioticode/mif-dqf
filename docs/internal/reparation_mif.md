CONTEXTE GLOBAL (MIF / DQF)

Le dépôt MIF-DQF contient plusieurs branches divergentes :
- main : version v1.1 (DQFMode, MIF-Lite, PROD envelope, MPI engine, etc.)
- baseline-cleanup : nettoyage v1.0 + restauration de documents + corrections mineures
- claude/verify-github-access-0SyGI : branche triviale (1 commit)
- claude/review-project-architecture-IGcu0 : commit temporaire
- historique v1.0 et v1.1 mélangés dans plusieurs branches

Problème : baseline-cleanup est "8 commits ahead, 28 behind main".
Risque : merger baseline-cleanup → main écraserait du code v1.1.

Objectif : reconstruire une baseline propre, conforme à DQF_SPECIFICATION.md v1.1,
sans réintroduire les erreurs de v1.0.

------------------------------------------------------------
PLAN D’ACTION POUR CLAUDE CODE
------------------------------------------------------------

1. Mettre baseline-cleanup à jour avec main
   - Action : intégrer tous les commits v1.1 dans baseline-cleanup.
   - Commande : git merge origin/main (ou rebase)
   - Résolution : conserver le code v1.1, intégrer uniquement les corrections valides
     de baseline-cleanup (gitignore, déduplication tests, fix patterns).
   - Éliminer : restaurations v1.0 obsolètes, anciennes docs v1.0.

2. Fusionner la branche claude/verify-github-access-0SyGI dans baseline-cleanup
   - Branche triviale, pas de risque.
   - Commande : git merge origin/claude/verify-github-access-0SyGI

3. Vérifier la conformité v1.1
   - Exécuter tous les tests : pytest -q
   - Vérifier cohérence avec :
       - DQF_SPECIFICATION.md v1.1
       - ARCHITECTURE.md v1.1
       - API.md v1.1
   - S’assurer que :
       - DQFMode, DQFConfig, MPI engine, PROD envelope, MIF-Lite sont intacts
       - aucune régression v1.0 n’a été réintroduite

4. Préparer la PR baseline-cleanup → main
   - Une fois baseline-cleanup :
       - synchronisée avec main
       - nettoyée
       - conforme à la spec v1.1
       - testée
   - Pousser la branche et créer la PR.

------------------------------------------------------------
RAPPORT DES MODIFICATIONS (LANGAGE HUMAIN)
------------------------------------------------------------

Diagnostic initial :
- Le dépôt local était en désordre, empêchant toute analyse fiable.
- La branche main contenait une version v1.1 correcte mais mélangée avec des commits
  de maintenance et des merges successifs.
- baseline-cleanup contenait un mélange de :
    - nettoyages utiles
    - restaurations v1.0 obsolètes
    - corrections valides (tests, gitignore, patterns)
- Plusieurs branches secondaires contenaient des commits isolés ou temporaires.

Analyse de Claude Sonnet 4.6 :
- La v1.0 souffrait de surcomplexification (scripts, backups, tooling excessif).
- Le projet avait perdu le fil architectural (PROD envelope, MIF-UID, certification).
- Trop de documentation générée par rapport au code fonctionnel.
- La spécification DQF_SPECIFICATION.md v1.1 est nettement plus rigoureuse que la v1.0.

Éléments valides conservés :
- Corrections typing (base.py)
- Fix flake.nix
- Tests 104/104 OK
- Concept baseline réaliste vs irréaliste
- Nettoyage baseline (gitignore, déduplication tests)

Éléments obsolètes à éliminer :
- Restauration de documents v1.0
- Scripts de tooling superflus
- Backups et workflows redondants
- Toute logique v1.0 contredisant la spec v1.1

Objectif final :
- Obtenir une branche baseline-cleanup propre, synchronisée avec main,
  conforme à DQF_SPECIFICATION.md v1.1, prête pour une PR propre et sûre.

------------------------------------------------------------
ATTENTES POUR CLAUDE CODE
------------------------------------------------------------

1. Appliquer le merge main → baseline-cleanup.
2. Résoudre les conflits en respectant strictement la spec v1.1.
3. Intégrer verify-github-access.
4. Vérifier la cohérence fonctionnelle (tests + architecture).
5. Produire un rapport final de consolidation.
6. Préparer la PR baseline-cleanup → main.
