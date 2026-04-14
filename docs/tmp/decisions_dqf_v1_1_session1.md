# Décisions DQF v1.1 — Session 1

**Statut** : Baseline pré-session 2  
**Date** : 2026-04-14  
**Auteurs** : dravitch, Claude (Anthropic)

---

## Contexte

Ce document capture les décisions architecturales prises lors de la session 1
de développement DQF v1.1. Il complète `docs/DQF_SPECIFICATION.md` (spec
canonique) en documentant le *pourquoi* de chaque choix.

---

## D-01 : Modes CERTIFICATION / DIAGNOSTIC — pas de défaut

**Décision** : Le mode doit être déclaré explicitement par l'appelant.
Aucune valeur par défaut dans `DQFConfig`.

**Raison** : Un défaut silencieux masquerait l'intention. Un data scientist
qui oublie de déclarer le mode ne devrait pas obtenir une certification
inattendue ou un diagnostic non-voulu.

**Implémentation** : `DQFConfig.__post_init__` lève `TypeError` si `mode`
n'est pas un `DQFMode`.

---

## D-02 : CORE / ADVISORY — classification des checks

**Décision** : Deux niveaux de sévérité :

| Niveau | Effet sur le gate | Checks |
|--------|------------------|--------|
| CORE   | FAIL → `gate = 0.0`, statut `VOID` | PROD, C2, C3, C5 |
| ADVISORY | WARN → `gate ≤ 0.8`, statut `WARNING` | C1, C4 |

**Raison** : Distinguer les violations physiques (indépassables) des
avertissements de qualité (non-bloquants).

---

## D-03 : MIF Purity Index (MPI) — échelle 0–100

**Décision** : Le MPI est exprimé sur une échelle **0–100** (entier ou
flottant), jamais 0–1.

**Raison** : Cohérence avec les conventions de scoring financier (BPS,
pourcentages). Le champ `purity_index` dans le manifest JSON reflète
directement le score, sans conversion.

**Formule** :
```
MPI = 100 × (1 − Σ(interventions_i × gravity_i) / N_total_points)
```

Un MPI de 100.0 signifie : zéro intervention — données canoniques dès l'origine.

---

## D-04 : PROD Envelope — sceau de confiance (pas un check de données)

**Décision** : Le composant PROD n'est pas un check de données. Il est le
mécanisme de confiance du format de sortie. Il est appelé par `DQFValidator`
uniquement quand le pipeline s'achève sans exception non gérée.

**Phase 1** : signature `sha256_provisional` (hash SHA-256 du MIF-UID).
**Phase 2** : remplacement par Ed25519 — le schéma reste identique.

---

## D-05 : Défaut transitoire `DQFMode.DIAGNOSTIC` dans C3

**Décision** : `CalendarAlignmentCheck.run()` accepte un `kwargs["mode"]`
avec défaut `DQFMode.DIAGNOSTIC` pour rester utilisable en test unitaire
sans passer `config` complet.

**Avertissement** : Ce défaut est transitoire. En production, le mode est
toujours fourni par `DQFValidator`. Ne pas promouvoir ce pattern dans les
nouveaux checks.

---

## D-06 : Suppression C6 et C7

**C6** (Sanity Tests statistiques) → migré vers MIF Layer 1.
**C7** (Logging) → remplacé par PROD Envelope.

**Raison** : Les tests statistiques relèvent de la probabilité de marché,
pas des lois physiques OHLCV. DQF se limite aux lois physiques.

---

## Manifeste Final : MIF-Lite v1.1

Exemple de manifest `.mif.json` produit par `PRODEnvelope.build()` pour
un dataset NYSE certifié avec MPI 95 :

```json
{
  "@context": "https://mif.dev/v1",
  "@type": "DataCertification",
  "mif_uid": "sha256:a3f9c4d2e1b8f7a6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2",
  "status": {
    "overall": "CERTIFIED",
    "precondition_gate": 1.0,
    "purity_index": 95.0
  },
  "checks": {
    "core": {
      "PROD": "PASS",
      "C2": "PASS",
      "C3": "PASS",
      "C5": "PASS"
    },
    "advisory": {
      "C1": "SKIP",
      "C4": "PASS"
    }
  },
  "vitality_signal": {
    "score": 95,
    "label": "EXCELLENT",
    "trend": "STABLE"
  },
  "provenance": {
    "dqf_version": "1.1.0",
    "mode": "CERTIFICATION",
    "source_hash": "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b",
    "calendar": "NYSE",
    "cleaning_log_uri": null
  },
  "signature": {
    "type": "sha256_provisional",
    "value": "b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3"
  }
}
```

**Note** : `purity_index` est sur l'échelle **0–100** (spec §5, `mpi.py`).
Une valeur de `95.0` signifie 5 % d'interventions pondérées sur l'ensemble
des points OHLCV.

---

*Document vivant — mis à jour à chaque session.*
