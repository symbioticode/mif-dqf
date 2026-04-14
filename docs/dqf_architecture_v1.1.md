
## Architecture DQF v1.1 — Document de référence pour implémentation

**Usage** : Ce document est la source de vérité pour Claude Code. Il décrit précisément ce qui change, ce qui reste, et dans quel ordre implémenter.

---

### Vue d'ensemble du delta

```
dqf/
├── __init__.py                  (modifier : exports publics)
├── core/
│   ├── config.py                (modifier : ajouter DQFMode)
│   ├── validator.py             (modifier : mode obligatoire, routing CORE/ADVISORY)
│   ├── report.py                (modifier : nouveau schéma MIF-Lite)
│   └── prod_envelope.py         (NOUVEAU : remplace check_7_logging)
├── checks/
│   ├── base.py                  (modifier : émettre interventions pour MPI)
│   ├── check_1_source.py        (inchangé — devient ADVISORY)
│   ├── check_2_integrity.py     (modifier : émettre compteurs interventions)
│   ├── check_3_calendar.py      (modifier : bifurcation mode CERT/DIAG)
│   ├── check_4_ffill.py         (modifier : émettre compteurs interventions)
│   ├── check_5_trace.py         (inchangé — reste CORE)
│   ├── check_6_sanity.py        (SUPPRIMER)
│   └── check_7_logging.py       (SUPPRIMER — remplacé par prod_envelope.py)
└── utils/
    ├── calendar.py              (inchangé)
    └── mpi.py                   (NOUVEAU : calcul MIF Purity Index)
```

---

### Session 1 — Fondations (le plus simple, zéro risque)

**Fichier : `dqf/core/config.py`**

Ajouter `DQFMode` et mettre à jour `DQFConfig` pour l'accepter comme paramètre obligatoire.

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import yaml

class DQFMode(Enum):
    CERTIFICATION = "CERTIFICATION"
    DIAGNOSTIC    = "DIAGNOSTIC"

@dataclass
class DQFConfig:
    """
    Configuration DQF v1.1.
    
    Le mode est OBLIGATOIRE. Il n'y a pas de défaut.
    CERTIFICATION : checks CORE non-bypassables, calendrier explicite requis.
    DIAGNOSTIC    : checks ADVISORY configurables, auto-détection calendrier permise.
    """
    mode: DQFMode  # Pas de valeur par défaut — volontaire

    # Advisory thresholds (configurables en DIAGNOSTIC, enregistrés en CERTIFICATION)
    c4_max_consecutive_ffill: int = 3
    c4_warn_threshold: int = 2

    # C1 : actif seulement quand DAL est connecté
    # En Phase 1, toujours SKIP — documenté explicitement
    c1_enabled: bool = False  # DAL-pending

    def __post_init__(self):
        if not isinstance(self.mode, DQFMode):
            raise TypeError(
                f"mode must be DQFMode.CERTIFICATION or DQFMode.DIAGNOSTIC, "
                f"got {type(self.mode).__name__}"
            )

    @classmethod
    def from_yaml(cls, path: str) -> "DQFConfig":
        with open(path) as f:
            data = yaml.safe_load(f)
        mode_str = data.pop("mode", None)
        if mode_str is None:
            raise ValueError("config.yaml must declare 'mode: CERTIFICATION|DIAGNOSTIC'")
        data["mode"] = DQFMode(mode_str)
        return cls(**data)
```

**Fichier : `dqf/utils/mpi.py`** — nouveau, autonome, testable isolément.

```python
"""
MIF Purity Index (MPI) — DQF v1.1
Mesure le coût d'intervention de DQF sur les données brutes.

MPI = 100 × (1 - Σ(interventions_i × gravity_i) / N_total_points)

Gravity weights (spec v1.1) :
  physical_correction : 1.0  (H < L corrigé, etc.)
  forward_fill        : 0.5  (missing data interpolé)
  calendar_removal    : 0.2  (point hors calendrier supprimé)
"""
from dataclasses import dataclass, field

GRAVITY = {
    "physical_correction": 1.0,
    "forward_fill":        0.5,
    "calendar_removal":    0.2,
}

@dataclass
class InterventionLog:
    """Accumulateur d'interventions émis par chaque check."""
    physical_corrections: int = 0
    forward_fills:        int = 0
    calendar_removals:    int = 0

    def add(self, intervention_type: str, count: int = 1):
        if intervention_type == "physical_correction":
            self.physical_corrections += count
        elif intervention_type == "forward_fill":
            self.forward_fills += count
        elif intervention_type == "calendar_removal":
            self.calendar_removals += count
        else:
            raise ValueError(f"Unknown intervention type: {intervention_type}")

    def total_weighted(self) -> float:
        return (
            self.physical_corrections * GRAVITY["physical_correction"]
            + self.forward_fills        * GRAVITY["forward_fill"]
            + self.calendar_removals    * GRAVITY["calendar_removal"]
        )

def compute_mpi(log: InterventionLog, n_total_points: int) -> float:
    """
    Retourne MPI dans [0.0, 100.0].
    MPI = 100 si zéro intervention.
    
    Args:
        log: InterventionLog agrégé de tous les checks.
        n_total_points: Nombre de points OHLCV dans le dataset (rows × 5).
    
    Raises:
        ValueError: Si n_total_points <= 0.
    """
    if n_total_points <= 0:
        raise ValueError(f"n_total_points must be > 0, got {n_total_points}")
    
    weighted = log.total_weighted()
    mpi = 100.0 * (1.0 - weighted / n_total_points)
    return max(0.0, min(100.0, mpi))  # Borner [0, 100]
```

---

### Session 2 — PROD Envelope (nouveau composant central)

**Fichier : `dqf/core/prod_envelope.py`** — remplace `check_7_logging.py`.

Ce composant n'est pas un check. C'est le sceau de sortie. Il est appelé par `DQFValidator` après tous les checks, uniquement si aucun CORE n'a retourné VOID.

```python
"""
PROD Envelope — DQF v1.1
Provenance & Reliability Operational Data.

Produit le manifeste MIF-Lite (.mif.json).
N'est PAS un check de données — c'est le mécanisme de confiance de sortie.

Phase 1 : SHA-256 provisoire (sig_type: "sha256_provisional").
Phase 2 : Ed25519 (sig_type: "ed25519") — schéma inchangé, champ "value" remplacé.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass

from dqf.core.config import DQFMode
from dqf.utils.mpi import InterventionLog, compute_mpi

# Valeurs possibles pour status.overall
STATUS_CERTIFIED = "CERTIFIED"    # Tous CORE PASS
STATUS_WARNING   = "WARNING"      # CORE PASS, au moins 1 ADVISORY WARN
STATUS_VOID      = "VOID"         # Au moins 1 CORE FAIL ou bypass
STATUS_FAIL      = "FAIL"         # Erreur inattendue dans le pipeline

# Mapping status → precondition_gate (spec §7)
PRECONDITION_GATE = {
    STATUS_CERTIFIED: 1.0,
    STATUS_WARNING:   0.8,   # MPI-based cap, max 0.8
    STATUS_FAIL:      0.2,
    STATUS_VOID:      0.0,
}

# Mapping MPI → D-SIG vitality score (linéaire)
def _mpi_to_vitality_score(mpi: float, overall_status: str) -> int:
    if overall_status == STATUS_VOID:
        return 0
    if overall_status == STATUS_FAIL:
        return 10
    # CERTIFIED ou WARNING : score proportionnel au MPI
    return int(mpi)

def _vitality_label(score: int) -> str:
    """Mapping D-SIG v0.5 natif."""
    if score >= 85: return "EXCELLENT"
    if score >= 60: return "GOOD"
    if score >= 35: return "DEGRADED"
    return "CRITICAL"

@dataclass
class PRODEnvelope:
    """
    Construit et signe le manifeste MIF-Lite.
    
    Args:
        mode         : DQFMode (CERTIFICATION ou DIAGNOSTIC)
        core_results : Dict[check_id, status_str] — résultats checks CORE
        advisory_results : Dict[check_id, status_str] — résultats checks ADVISORY  
        raw_data_hash: SHA-256 des données brutes (hex string)
        dqf_version  : Version DQF (ex: "1.1.0")
        calendar     : Calendrier déclaré (ex: "NYSE")
        intervention_log : InterventionLog agrégé
        n_total_points   : Nombre de points OHLCV
    """
    mode: DQFMode
    core_results: dict
    advisory_results: dict
    raw_data_hash: str
    dqf_version: str
    calendar: str
    intervention_log: InterventionLog
    n_total_points: int

    def _compute_overall_status(self) -> str:
        # Un seul CORE FAIL → VOID (spec §3.1)
        if any(v in ("FAIL", "ERROR") for v in self.core_results.values()):
            return STATUS_VOID
        # ADVISORY WARN → WARNING (non-bloquant)
        if any(v == "WARN" for v in self.advisory_results.values()):
            return STATUS_WARNING
        return STATUS_CERTIFIED

    def _compute_mif_uid(self, dqf_version: str, overall_status: str) -> str:
        """
        MIF-UID = SHA-256(raw_data_hash || dqf_version || calendar || mode)
        Spec §6 — décision architecturale : calculé sur données brutes.
        """
        payload = (
            self.raw_data_hash
            + dqf_version
            + self.calendar
            + self.mode.value
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(payload).hexdigest()

    def _compute_source_sig(self, mif_uid: str) -> str:
        """
        Phase 1 : SHA-256 du MIF-UID comme signature provisoire.
        Phase 2 : Remplacer par Ed25519(private_key, mif_uid).
        Le champ 'type' dans le manifeste signale explicitement le niveau.
        """
        return hashlib.sha256(mif_uid.encode()).hexdigest()

    def build(self) -> dict:
        """Retourne le manifeste MIF-Lite comme dictionnaire Python."""
        overall_status = self._compute_overall_status()
        mpi = compute_mpi(self.intervention_log, self.n_total_points)
        mif_uid = self._compute_mif_uid(self.dqf_version, overall_status)
        source_sig = self._compute_source_sig(mif_uid)
        gate = PRECONDITION_GATE.get(overall_status, 0.0)

        # Cap gate sur MPI si WARNING (spec §7)
        if overall_status == STATUS_WARNING:
            gate = min(gate, mpi / 100.0)

        vitality_score = _mpi_to_vitality_score(mpi, overall_status)

        return {
            "@context": "https://mif.dev/v1",
            "@type": "DataCertification",
            "mif_uid": mif_uid,
            "status": {
                "overall": overall_status,
                "precondition_gate": round(gate, 4),
                "purity_index": round(mpi, 2),
            },
            "checks": {
                "core": self.core_results,
                "advisory": self.advisory_results,
            },
            "vitality_signal": {
                "score": vitality_score,
                "label": _vitality_label(vitality_score),
                "trend": "STABLE",  # Phase 1 : statique. Phase 2 : comparaison historique.
            },
            "provenance": {
                "dqf_version": self.dqf_version,
                "mode": self.mode.value,
                "source_hash": self.raw_data_hash,
                "calendar": self.calendar,
                "cleaning_log_uri": None,  # Phase 2 : URI Parquet
            },
            "signature": {
                "type": "sha256_provisional",
                "value": source_sig,
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.build(), indent=indent, ensure_ascii=False)
```

---

### Session 3 — Modifications des checks existants

**`dqf/checks/base.py`** — une seule modification : ajouter `intervention_log` optionnel dans `CheckResult`.

```python
# Ajouter au dataclass CheckResult existant :
@dataclass
class CheckResult:
    status: str           # 'PASS', 'FAIL', 'WARN', 'SKIP', 'ERROR'
    severity: str         # 'INFO', 'WARNING', 'CRITICAL'
    message: str
    details: Optional[dict] = None
    # NOUVEAU v1.1 — interventions effectuées par ce check
    interventions: Optional["InterventionLog"] = None
```

**`dqf/checks/check_3_calendar.py`** — bifurcation mode.

```python
# Logique à ajouter dans run() :
def run(self, df, mode: DQFMode, calendar: Optional[str] = None, **kwargs):
    if mode == DQFMode.CERTIFICATION:
        if calendar is None:
            # Spec §4 C3 : ERROR_MISSING_METADATA
            return self._create_result(
                status="FAIL",
                severity="CRITICAL",
                message="ERROR_MISSING_METADATA: calendar must be explicitly "
                        "declared in CERTIFICATION mode. "
                        "Accepted: NYSE, LSE, EURONEXT, CRYPTO_247, FOREX_245"
            )
        # Valider contre le calendrier déclaré (logique existante)
        return self._validate_against_declared(df, calendar)
    else:
        # DIAGNOSTIC : auto-détection permise (logique existante v1.0)
        detected = self._auto_detect_calendar(df)
        result = self._validate_against_declared(df, detected)
        result.details = result.details or {}
        result.details["calendar_source"] = "INFERRED_CALENDAR"
        return result
```

**`dqf/checks/check_2_integrity.py`** et **`check_4_ffill.py`** — ajouter émission d'interventions.

```python
# Dans check_2_integrity.py, après correction d'une violation physique :
if result.interventions is None:
    result.interventions = InterventionLog()
result.interventions.add("physical_correction", count=n_violations_corrected)

# Dans check_4_ffill.py, après détection ffill :
if result.interventions is None:
    result.interventions = InterventionLog()
result.interventions.add("forward_fill", count=n_ffill_sequences)

# Dans check_3_calendar.py, après suppression de points hors-calendrier :
if result.interventions is None:
    result.interventions = InterventionLog()
result.interventions.add("calendar_removal", count=n_points_removed)
```

---

### Session 4 — DQFValidator et DQFReport (orchestration)

**`dqf/core/validator.py`** — le changement le plus impactant sur l'API publique.

```python
class DQFValidator:
    
    # Mapping check_id → CORE ou ADVISORY (spec §3)
    CORE_CHECKS     = {"PROD", "C2", "C3", "C5"}
    ADVISORY_CHECKS = {"C1", "C4"}

    def __init__(self, config: DQFConfig):
        # config.mode est maintenant obligatoire — DQFConfig.__post_init__ valide
        self.config = config
        self._init_checks()

    def _init_checks(self):
        # Checks CORE : toujours actifs en CERTIFICATION
        self.checks = {
            "C2": OHLCVIntegrityCheck("C2", "OHLCV Physics"),
            "C3": CalendarAlignmentCheck("C3", "Calendar Alignment"),
            "C5": IndexTraceabilityCheck("C5", "Index Traceability"),
        }
        # C1 : SKIP en Phase 1 (DAL-pending)
        if self.config.c1_enabled:
            self.checks["C1"] = StreamIntegrityCheck("C1", "Stream Integrity")
        # C4 : toujours actif
        self.checks["C4"] = ForwardFillCheck("C4", "Forward-Fill Limits")
        # Check 6 supprimé — MIF Layer 1
        # Check 7 supprimé — remplacé par PROD envelope

    def validate(
        self,
        df: pd.DataFrame,
        calendar: Optional[str] = None,
        raw_data_hash: Optional[str] = None,
    ) -> "DQFReport":
        """
        Lance la validation complète et retourne un DQFReport v1.1.
        
        Args:
            df            : DataFrame OHLCV à valider.
            calendar      : Calendrier déclaré. Obligatoire en CERTIFICATION.
            raw_data_hash : SHA-256 des données brutes. Si None, calculé ici.
        
        Returns:
            DQFReport contenant le manifeste MIF-Lite.
        
        Raises:
            TypeError  : Si df n'est pas un DataFrame.
            ValueError : Si mode CERTIFICATION et calendar absent.
        """
        # Calculer hash données brutes si non fourni
        if raw_data_hash is None:
            raw_data_hash = self._hash_dataframe(df)

        core_results     = {}
        advisory_results = {}
        aggregated_log   = InterventionLog()

        for check_id, check in self.checks.items():
            try:
                result = check.run(
                    df,
                    mode=self.config.mode,
                    calendar=calendar,
                    config=self.config,
                )
                # Agréger interventions pour MPI
                if result.interventions:
                    aggregated_log.physical_corrections += result.interventions.physical_corrections
                    aggregated_log.forward_fills        += result.interventions.forward_fills
                    aggregated_log.calendar_removals    += result.interventions.calendar_removals

            except Exception as e:
                result = CheckResult(
                    status="ERROR", severity="CRITICAL",
                    message=f"Check {check_id} crashed: {e}"
                )
            
            if check_id in self.CORE_CHECKS:
                core_results[check_id] = result.status
            else:
                advisory_results[check_id] = result.status

        # C1 absent en Phase 1 → SKIP explicite
        if "C1" not in advisory_results:
            advisory_results["C1"] = "SKIP"

        # PROD envelope — calcule MIF-UID, MPI, manifeste
        n_total = df.shape[0] * 5  # rows × OHLCV columns
        envelope = PRODEnvelope(
            mode=self.config.mode,
            core_results=core_results,
            advisory_results=advisory_results,
            raw_data_hash=raw_data_hash,
            dqf_version=DQF_VERSION,
            calendar=calendar or "UNKNOWN",
            intervention_log=aggregated_log,
            n_total_points=n_total,
        )
        manifest = envelope.build()

        return DQFReport(manifest=manifest, cleaned_data=df)

    @staticmethod
    def _hash_dataframe(df: pd.DataFrame) -> str:
        """SHA-256 déterministe sur les données brutes."""
        import hashlib
        return "sha256:" + hashlib.sha256(
            pd.util.hash_pandas_object(df, index=True).values.tobytes()
        ).hexdigest()
```

**`dqf/core/report.py`** — interface publique simplifiée autour du manifeste.

```python
@dataclass
class DQFReport:
    """
    Résultat v1.1 d'une validation DQF.
    
    Le manifeste MIF-Lite est la source de vérité.
    Les propriétés sont des accesseurs sur ce manifeste.
    """
    manifest: dict          # Le .mif.json complet
    cleaned_data: pd.DataFrame

    @property
    def overall_status(self) -> str:
        return self.manifest["status"]["overall"]

    @property
    def precondition_gate(self) -> float:
        return self.manifest["status"]["precondition_gate"]

    @property
    def purity_index(self) -> float:
        return self.manifest["status"]["purity_index"]

    @property
    def mif_uid(self) -> str:
        return self.manifest["mif_uid"]

    @property
    def is_certified(self) -> bool:
        return self.overall_status == "CERTIFIED"

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.manifest, indent=indent, ensure_ascii=False)

    def to_yaml(self) -> str:
        return yaml.dump(self.manifest, default_flow_style=False, allow_unicode=True)

    def print_summary(self):
        s = self.manifest["status"]
        v = self.manifest["vitality_signal"]
        print(f"DQF v1.1 — {self.manifest['provenance']['mode']}")
        print(f"  Status : {s['overall']}")
        print(f"  MPI    : {s['purity_index']:.1f}/100")
        print(f"  Gate   : {s['precondition_gate']}")
        print(f"  Signal : {v['label']} ({v['score']}) — {v['trend']}")
        print(f"  UID    : {self.mif_uid[:40]}...")
```

---

### Résumé pour Claude Code

**Ce document est auto-suffisant.** Claude Code peut implémenter dans cet ordre :

| Session | Fichiers | Risque | Tests nouveaux |
|---|---|---|---|
| 1 | `config.py`, `utils/mpi.py` | Minimal | ~15 tests unitaires MPI |
| 2 | `core/prod_envelope.py` | Faible | ~20 tests manifeste |
| 3 | `checks/base.py`, C2, C3, C4 | Moyen | ~15 tests delta par check |
| 4 | `core/validator.py`, `core/report.py` | Élevé | ~20 tests intégration |
| Cleanup | Supprimer C6, C7, mettre à jour `__init__.py`, exemples | Minimal | Mise à jour tests existants |

**Invariants à respecter** (Claude Code doit les vérifier) :
- `DQFConfig` sans `mode` → `TypeError` immédiat
- CORE FAIL → `overall_status = "VOID"` → `precondition_gate = 0.0`
- `mif_uid` calculé sur données brutes, pas nettoyées
- `sig_type = "sha256_provisional"` toujours présent en Phase 1
- `cleaning_log_uri = null` toujours présent comme placeholder
- `vitality_signal.label` toujours dans `{EXCELLENT, GOOD, DEGRADED, CRITICAL}`