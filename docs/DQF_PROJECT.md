# DQF - Data Quality Framework  
**Version** : 1.0.0 — **(document historique — voir v1.1 dans README.md)**  
**Date** : 20 janvier 2026  
**Statut** : ✅ Production Ready (104/104 tests passing à l'époque)  
**Licence** : MIT  

> ⚠️ **Ce document décrit DQF v1.0.0** (release de janvier 2026). La version courante est **v1.1.0**.
> Pour la documentation à jour, voir :
> - [`README.md`](../README.md) — Quick Start v1.1
> - [`docs/API.md`](./API.md) — Référence API v1.1
> - [`docs/DQF_SPECIFICATION.md`](./DQF_SPECIFICATION.md) — Spec canonique v1.1

---

## 📋 Vue d’Ensemble

DQF (Data Quality Framework) est un framework **autonome** de validation de qualité pour données financières OHLCV (Open, High, Low, Close, Volume). Il détecte et signale les anomalies dans les données de marché avant leur utilisation dans des stratégies de trading ou des analyses quantitatives.

### Objectifs

- **Autonome** : Fonctionne indépendamment (pas de dépendance MIF)  
- **Domain-specific** : Conçu pour données financières OHLCV  
- **Reproductible** : Mêmes données → mêmes résultats  
- **Transparent** : Provenance tracking complet  

### Positionnement dans l’écosystème

```
DQF (Layer -1) = Validation qualité données
    ↓
DAL (Layer 0)  = Abstraction sources multiples  [À VENIR]
    ↓
MIF (Layers 1-5) = Certification métriques
```

---

## 🎯 Fonctionnalités

### Les 7 Checks de Validation (v1.0.0 — historique)

| Check | Nom | Description | Statut v1.0 | Statut v1.1 |
|-------|-----|-------------|-------------|-------------|
| 1 | Source Uniqueness | Validation source unique + métadonnées | ✅ | ADVISORY (SKIP Phase 1) |
| 2 | OHLCV Integrity | Lois physiques marché (H≥L, H≥O/C, etc.) | ✅ | CORE (C2) |
| 3 | Calendar Alignment | Détection auto calendar + weekends/holidays | ✅ | CORE (C3) |
| 4 | Forward-Fill Limits | Détection interpolation excessive | ✅ | ADVISORY (C4) |
| 5 | Index Traceability | Index unique, chronologique, timezone | ✅ | CORE (C5) |
| 6 | Sanity Tests | Anomalies statistiques (returns, volume, volatility) | ✅ | **Supprimé → MIF Layer 1** |
| 7 | Comprehensive Logging | Provenance tracking complet + export JSON | ✅ | **Supprimé → PROD Envelope** |

### Composants Core

- **DQFValidator** : Orchestrateur principal  
- **DQFReport** : Rapport consolidé + exports YAML/JSON  
- **DQFConfig** : Configuration YAML/kwargs  
- **BaseCheck** : Classe abstraite enrichie  
- **Calendar Utils** : Détection NYSE/CRYPTO/FOREX  
- **Provenance Tracking** : Chaîne complète des opérations  

---

## 🚀 Installation

### Prérequis

- Python 3.10+  
- pandas ≥ 2.0.0  
- PyYAML ≥ 6.0  

### Installation depuis source

```bash
git clone https://github.com/symbioticode/mif-dqf.git
cd mif-dqf
pip install -e .
```

---

## 📖 Usage

### Validation simple

```python
import pandas as pd
from dqf import DQFValidator, DQFConfig

dates = pd.date_range("2024-01-01", periods=100, freq="D", tz="UTC")
data = pd.DataFrame({...}, index=dates)

# v1.0.0 (historique — ne pas utiliser)
# validator = DQFValidator(DQFConfig())
# report = validator.validate(data, symbol="BTC-USD", source="yahoo")

# v1.1.0 (courant)
from dqf import DQFValidator, DQFConfig, DQFMode
from pathlib import Path

validator = DQFValidator(DQFConfig(mode=DQFMode.CERTIFICATION))
report = validator.validate(data, calendar="NYSE")

print(report.overall_status)          # CERTIFIED / WARNING / VOID
print(f"MPI: {report.purity_index}")
Path("report.yaml").write_text(report.to_yaml())
```

### Configuration personnalisée

```yaml
checks:
  check_2_integrity:
    enabled: true
    max_violation_rate: 0.01
```

---

## 🏗️ Architecture

### Structure du projet

```
dqf/
├── dqf/
│   ├── checks/
│   ├── core/
│   ├── utils/
│   └── __init__.py
├── tests/
│   ├── unit/
│   └── integration/
├── examples/
└── docs/
```

### Workflow de validation

```
DataFrame → DQFConfig → DQFValidator → Checks → DQFReport → Exports
```

---

## 📊 Métriques Qualité

### Tests v1.0.0 (historique)

```
Total Tests:     104 (100%)  — janvier 2026
  - Unit:        96 tests
  - Integration: 8 tests
```

### Tests v1.1.0 (courant)

```
Total Tests:     189 (100%)  — avril 2026
  - Unit:        164 tests
  - Integration: 25 tests
Status:          ✅ 189/189 PASSING
```

### Code

```
Production:      ~1,350 lines
Tests:           ~1,200 lines
Examples:        ~450 lines
Docs:            ~2,100 lines
Ratio Test/Prod: 0.89x
```

---

## 📝 Corrections Finales (20 janvier 2026)

- Uniformisation message d’erreur `_validate_dataframe()` :  
  `"Expected pd.DataFrame, got {type}"`
- Alignement tests unitaires/intégration  
- Nettoyage imports + linting  
- Documentation API clarifiée  
- Provenance tracking stabilisé  

---

## ⚠️ Limitations Connues v1.0.0 (toutes résolues en v1.1.0)

| Limitation v1.0.0 | Résolution v1.1.0 |
|-------------------|-------------------|
| `datetime.utcnow()` dans check_7_logging.py | Supprimé (C7 removed) |
| Example 03 crash `report.timestamp.isoformat()` | Entièrement réécrit |
| `DQFConfig()` sans mode (pas de validation) | Mode obligatoire + TypeError |
| `report.checks_passed` / `total_checks` | Remplacé par `purity_index` + `precondition_gate` |

---

## 📘 Documentation API (extraits pertinents)

### BaseCheck._validate_dataframe()

```python
Raises:
    TypeError: If df is not a pandas DataFrame
        Message format: "Expected pd.DataFrame, got {actual_type}"
    ValueError: If DataFrame is empty
```

### DQFReport.timestamp

```
timestamp: str  # ISO 8601 string, not datetime
```

---

## 🗺️ Roadmap

### v1.1.0 ✅ (courant — avril 2026)

- Modes CERTIFICATION / DIAGNOSTIC  
- Classification CORE / ADVISORY  
- PROD Envelope → MIF-Lite manifest (.mif.json)  
- MIF Purity Index (MPI) : 0–100  
- MIF-UID : SHA-256 déterministe  
- C6 migré vers MIF Layer 1 ; C7 remplacé par PROD Envelope  
- 189/189 tests passing  

### v1.2.0 (prévu)

- Active cleaning optionnel en mode CERTIFICATION  
- Rapports diff avant/après  

### v2.0.0 (prévu)

- Intégration DAL (`get_certified_data()`)  
- C1 activé — handoff DAL  
- Provenance DAL-compatible  

---

## 📝 Leçons Apprises

- Ground Truth First : code → tests → docs  
- One Source of Truth : API.md reflète le code réel  
- Explainability First : messages d’erreur simples et cohérents  
- Tests d’intégration = API publique  
- Tests unitaires = API interne  

---

## 🔧 Maintenance

### NixOS (recommandé)

```bash
direnv allow
just test
just lint
just format
just coverage
```

### Autres OS

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 📄 Licence

MIT

---

## 👥 Auteurs

- **Andrei** — Lead Developer  
- **Claude (Anthropic)** — Architecture & Implementation Assistant  
- **Grok (xAI)** — Workflow Analysis  

---

## 🙏 Remerciements

- Communauté NixOS  
- Projet MIF  
- pandas, pytest, PyYAML  
- Anthropic pour Claude  

---

**Fin DQF_PROJECT.md v1.0.0 — Production Ready (104/104 tests passing)**