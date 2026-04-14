Ce document fait la synthèse entre le besoin de légèreté opérationnelle et la rigueur normative de la **DQF Specification v1.1**.

Voici la version finalisée et amendée du document de décision ci-dessous, intégrant les résolutions des tensions identifiées (structure des checks, labels D-SIG et placeholders de provenance).

# 📄 Décision Architecturale : DQF-MIF v1.1 (Amendée)

**Statut** : Approuvé avec amendements (Phase 1)  
**Contexte** : Alignement final entre `DQF_SPECIFICATION.md`, `mif_file_formats_strategy_rag.md` et `D-SIG v0.5`.  
**Référence** : Résolution des Décisions 1 & 2.

---

## 🏗️ 1. Arbitrages Techniques

### Décision 1 : Alignement CORE/ADVISORY
Conformément à la spécification v1.1, nous abandonnons la chaîne binaire `steps_passed` (trop opaque). Le système doit explicitement distinguer ce qui est bloquant pour la certification de ce qui est indicatif.
* **Core Checks** : `PROD`, `C2` (OHLCV), `C3` (Calendar), `C5` (Traceability). Si l'un échoue → Status `VOID`.
* **Advisory Checks** : `C1` (Stream Integrity), `C4` (Interpolation). Si l'un échoue → Status `WARNING`.

### Décision 2 : Conformité D-SIG (Labels & Vitalité)
Pour assurer l'interopérabilité, nous adoptons les labels natifs de **D-SIG v0.5**. Le terme local "TRUSTED" est mappé sur le label standard **"EXCELLENT"** pour un succès total (6/6). Cela garantit que n'importe quel système compatible D-SIG peut interpréter le signal DQF sans dictionnaire de traduction supplémentaire.

---

## 💎 2. Le Manifeste Final : MIF-Lite v1.1

Ce format `.mif.json` devient l'artefact officiel de sortie du Layer 0.



```json
{
  "@context": "https://mif.dev/v1",
  "@type": "DataCertification",
  "mif_uid": "sha256:h4sh_v3rsion_dqf_plus_data",
  "status": {
    "overall": "CERTIFIED",
    "precondition_gate": 1.0,
    "purity_index": 0.95
  },
  "checks": {
    "core": {
      "PROD_envelope": "PASS",
      "C2_ohlcv_physics": "PASS",
      "C3_calendar_strict": "PASS",
      "C5_index_traceability": "PASS"
    },
    "advisory": {
      "C1_stream_integrity": "SKIP",
      "C4_forward_fill_limit": "WARN"
    }
  },
  "vitality_signal": {
    "score": 100,
    "label": "EXCELLENT",
    "trend": "STABLE"
  },
  "provenance": {
    "dqf_version": "1.1.0",
    "mode": "CERTIFICATION",
    "source_hash": "sha256:data_brute",
    "calendar": "NYSE",
    "cleaning_log_uri": null
  },
  "signature": {
    "type": "sha256_provisional",
    "value": "..."
  }
}
```

---

## 📉 3. Résolution des Tensions et Alignement

### Intégration de la Stratégie RAG
Le champ `cleaning_log_uri: null` est ajouté par anticipation. Conformément à `mif_file_formats_strategy_rag.md`, ce champ sera peuplé en Phase 2 par l'URI d'un fichier Parquet ou d'un log détaillé, permettant la "Navigation de Provenance" sans alourdir le manifeste actuel.

### Application du Precondition Gate
La décision 1 est ici totalement opérante :
* Si `checks.core` contient un `FAIL` → `precondition_gate = 0.0`.
* Si `checks.advisory` contient un `WARN` → `precondition_gate = 0.8` (dégradation de la confiance sans invalidation totale).

---

## 🏁 4. Conclusion : Pourquoi cette version est la bonne

1.  **Elle est sincère** : Elle avoue que certains checks sont ignorés (`SKIP`) ou provisoires (`sha256_provisional`).
2.  **Elle est structurée** : Elle sépare les responsabilités critiques (CORE) des métadonnées informatives (ADVISORY).
3.  **Elle est standardisée** : Elle parle le langage de D-SIG (EXCELLENT, STABLE) et prépare le terrain pour le RAG (placeholders).

**Action Suivante** : Mise à jour du moteur de validation Python pour générer ce dictionnaire `checks` au lieu de la chaîne binaire `steps_passed`. L'alignement est maintenant scellé entre la vision stratégique et l'implémentation technique.

----------------------------------

# 📄 Décision Architecturale : DQF-MIF Layer 0 Implementation

**Statut** : Approuvé  
**Contexte** : Migration de DQF v1.0.0 vers DQF Spec v1.1 (Standard MIF)  
**Objectif** : Transformer DQF d'un outil de diagnostic en un **système de certification de données**.

---

## 🏗️ 1. Résolution des Décisions Critiques

### Décision 1 : Alignement Structurel (Approuvée)
L'architecture de DQF est désormais officiellement scindée pour servir le standard MIF :
* **Modes Opérationnels** : Implémentation immédiate des modes `CERTIFICATION` (strict, non-bypassable) et `DIAGNOSTIC` (flexible).
* **Délimitation du Périmètre** : Le **Check 6 (Statistical Sanity)** est officiellement exclu de DQF. Il est migré vers le **MIF Layer 1** (Validation Statistique). DQF se concentre exclusivement sur les "Lois de la Physique" (OHLCV, Unicité, Calendrier).
* **Élévation PROD** : Le "Check 7" devient l'enveloppe **PROD (Provenance & Reliability Operational Data)**. Ce n'est plus un test, mais le sceau de sortie du framework.

### Décision 2 : Stratégie Cryptographique "Lean" (Approuvée)
Pour respecter la contrainte d'absence d'infrastructure de clés (PKI) tout en garantissant l'esprit de MIF :
* **MIF-UID Provisoire** : Utilisation exclusive du **SHA-256** pour le `source_sig`.
* **Flag de Confiance** : Marquage explicite dans le manifeste : `sig_type: "sha256_provisional"`.
* **Évolutivité** : Le format de sortie est conçu pour accueillir `Ed25519` sans rupture de schéma dès que les moyens techniques le permettront. Le hash actuel garantit l'immutabilité, à défaut de garantir l'identité de l'émetteur (ce qui suffit pour la Phase 1).

---

## 💎 2. Le Format de Sortie : Le "Certificat de Vitalité DQF"

Conformément à l'esprit de **D-SIG** et aux formats définis dans la stratégie MIF, le résultat d'un traitement DQF ne sera pas un fichier de données modifié, mais un **Manifeste de Certification** (`.mif.json`) léger.

### Structure du Manifeste (MIF-Lite)
```json
{
  "@context": "https://mif.dev/v1",
  "@type": "DataCertification",
  "mif_uid": "sha256:h4sh_v3rsion_dqf_plus_data",
  "status": {
    "overall": "CERTIFIED",
    "precondition_gate": 1.0,
    "purity_index": 0.95
  },
  "vitality_signal": {
    "score": 100,
    "label": "TRUSTED",
    "trend": "STABLE"
  },
  "provenance": {
    "dqf_version": "1.1.0",
    "mode": "CERTIFICATION",
    "source_hash": "sha256:data_brute",
    "calendar": "NYSE",
    "steps_passed": "11111"
  },
  "signature": {
    "type": "sha256_provisional",
    "value": "..."
  }
}
```

---

## 📈 3. Intégration D-SIG : De l'Audit à la Référence

Pour transformer ce bundle en un **Signal de Référence** (Phare Opérationnel), nous appliquons les principes de **D-SIG** :

1.  **La Triple-Réduction (D-SIG R1)** : Le succès de DQF (6/6) est immédiatement traduit en un score de vitalité (100). Un échec sur un check CORE produit un statut `VOID` (Score 0), rendant la donnée invisible pour les couches MIF supérieures.
2.  **L'Identité Immuable** : Le `MIF-UID` devient l'ancre de vérité. Toute métrique calculée ultérieurement devra citer cet UID. Si l'UID change (données différentes ou version DQF majeure), la certification de la métrique est automatiquement invalidée.
3.  **L'Analyse de Tendance** : DQF ne se contentera pas de valider un fichier. Il pourra comparer le `Purity Index` actuel aux précédents pour signaler une dégradation de la qualité du fournisseur (Signal de Vitalité du Flux).

[Image d'un flux de certification montrant la donnée brute entrant dans DQF, la génération du manifeste JSON-LD avec son score de vitalité, et son utilisation comme phare pour les métriques MIF]

---

## 🏁 4. Conclusion & Prochaine Action

Les formats de `mif_file_formats_strategy_rag.md` ne sont pas abandonnés, ils sont **distillés**. On conserve la structure `JSON-LD` (sémantique) et le `TOON` (résumé) pour la communication entre modules, mais on différe la complexité `Parquet` et `Ed25519`.

**Prochaine étape immédiate :**
Implémenter le `precondition_gate` dans le moteur de calcul. 
* *Logique* : `MIF_Score = f(Calcul) * DQF.status_multiplier`.
* *Impact* : Si DQF renvoie `FAIL` (0.2) ou `VOID` (0.0), la métrique est mathématiquement "éteinte", protégeant ainsi le système de décision contre toute corruption de donnée.

**L'alignement est désormais total : DQF est le gardien physique, MIF est le validateur logique, et D-SIG est le langage de communication de leur confiance combinée.**
