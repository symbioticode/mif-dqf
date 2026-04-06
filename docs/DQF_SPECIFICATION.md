# DQF Specification v1.1
**Status**: Canonical — supersedes ARCHITECTURE.md for design decisions  
**Last Updated**: 2026-04-06  
**Authors**: dravitch, Claude (Anthropic)

---

## 1. Purpose and Scope

DQF (Data Quality First) is the foundational validation layer of the MIF
ecosystem. Its single responsibility: **guarantee that data entering any MIF
computation is physically valid and traceable**.

DQF does not evaluate strategies. It does not judge market probability. It
enforces the laws of OHLCV physics and the integrity of the data stream. Any
layer above DQF (DAL, MIF Layer 1–5) may assume these guarantees hold.

DQF is published as an **independent Python package**. It has no dependency on
MIF or DAL. MIF and DAL depend on DQF.

---

## 2. Operational Modes

DQF operates in two distinct modes. The mode must be explicitly declared at
instantiation. There is no default.

### 2.1 Certification Mode

Used by MIF to certify a metric under controlled conditions.

- All MIF-CORE checks are active and non-bypassable.
- The trading calendar must be **explicitly declared** in stream metadata.
  Auto-detection is forbidden. Missing calendar metadata returns
  `ERROR_MISSING_METADATA` and halts validation.
- The transformation algorithm (Phase 2 active data cleaning) is a **pure,
  versioned function**. Its output is deterministic across machines and
  environments for a given DQF version.
- The MIF-UID is computed as:
  ```
  MIF-UID = SHA-256(raw_data_hash + dqf_version)
  ```
  Any change to DQF's cleaning algorithm increments the major version and
  invalidates prior certifications for strict comparison.
- Certification is recorded as: `Validated under DQF v1.1.0-Stable`.

### 2.2 Diagnostic Mode

Used by practitioners (traders, quants) to assess their own data against the
MIF standard.

- MIF-ADVISORY checks are active with configurable thresholds.
- Calendar auto-detection is permitted.
- The MPI score (Section 5) is emitted as an informational signal.
- Results carry the annotation: `DIAGNOSTIC — not eligible for MIF
  certification`.

---

## 3. Check Classification

### 3.1 MIF-CORE (Non-negotiable)

These checks cannot be disabled in Certification Mode. Failure or bypass
returns `STATUS: VOID` — the certification is immediately invalidated.

| Check | Name | What it enforces |
|-------|------|-----------------|
| PROD  | Stream Identity | Unique source_id, timestamp, signature |
| C2    | OHLCV Physics | H≥L≥0, H≥O/C, L≤O/C, V≥0, no NaN in OHLCV |
| C3    | Calendar Alignment | Declared calendar respected; no inferred calendar |
| C5    | Index Traceability | Unique timestamps, chronological, timezone-aware |

### 3.2 MIF-ADVISORY (Configurable)

Active by default. Configurable via `DQFConfig`. Deviations from Gold Standard
thresholds are recorded in the MIF-UID metadata and surfaced to the end user.

| Check | Name | Default threshold | What it measures |
|-------|------|------------------|-----------------|
| C1    | Stream Integrity | — | Logical source consistency post-DAL assembly |
| C4    | Forward-Fill Limits | max 3 consecutive | Interpolation density |

> **Note**: Check 6 (Statistical Sanity) has been migrated to MIF Layer 1.
> DQF scope ends at physical data laws. Market probability belongs to the
> analytical layer.

---

## 4. The DQF Pipeline

### PROD — Stream Identity & Signature

Replaces the former Check 7 (Comprehensive Logging).

Every DQF validation session produces a signed identity envelope attached to
the output signal. This is not a data check — it is the output format's trust
mechanism.

Required fields:
```json
{
  "source_id": "<stable identifier, never tied to ephemeral hardware>",
  "dqf_version": "1.1.0",
  "timestamp": "<ISO 8601>",
  "ttl": 86400,
  "mode": "CERTIFICATION | DIAGNOSTIC",
  "source_sig": "<Ed25519 base64, required in Certification Mode>"
}
```

A signal without a valid PROD envelope is rejected by DAL and MIF as
unverifiable.

### C1 — Stream Integrity

**Scope**: Validates that the unified stream delivered by DAL has not been
altered after assembly. DQF does not validate the fusion logic (that is DAL's
responsibility). DQF validates the **integrity of the finished product**.

Specifically: the stream must carry a unique logical source identifier
(PROD-01) and must contain no data injected after the DAL handoff timestamp.

**CORE in**: neither — this is ADVISORY because DAL is trusted to produce
well-formed output. C1 is an integrity cross-check, not a physical law.

### C2 — OHLCV Physics [CORE]

Enforces market physics. These constraints are universal and non-negotiable:

- High ≥ Low ≥ 0
- High ≥ Open, High ≥ Close
- Low ≤ Open, Low ≤ Close
- Volume ≥ 0
- No NaN in Open, High, Low, Close, Volume

A single violation marks C2 as FAIL in Certification Mode. No violation rate
tolerance applies.

### C3 — Calendar Alignment [CORE]

In **Certification Mode**: the `market_calendar` field must be present in
stream metadata. Accepted values: `NYSE`, `LSE`, `EURONEXT`, `CRYPTO_247`,
`FOREX_245`. No value → `ERROR_MISSING_METADATA`.

In **Diagnostic Mode**: auto-detection is permitted using existing heuristics
(symbol pattern, weekend ratio). Result is flagged `INFERRED_CALENDAR`.

### C4 — Forward-Fill Limits [ADVISORY]

Detects excessive interpolation in the input stream. Configurable via
`max_consecutive_ffill` (default: 3) and `warn_threshold` (default: 2).

In Certification Mode: any deviation from Gold Standard thresholds is recorded
in the PROD envelope as a metadata flag, visible in the MIF-UID audit trail.

### C5 — Index Traceability [CORE]

- DatetimeIndex required
- No duplicate timestamps
- Strictly chronological (ascending)
- Timezone-aware (tz-naive index rejected in Certification Mode)

---

## 5. MIF Purity Index (MPI)

The MPI is a score (0–100) measuring how much DQF had to intervene to produce
the certified canonical dataset. A score of 100 means zero intervention; the
raw data was already canonical.

### Formula

```
MPI = 100 × (1 - Σ(interventions_i × gravity_i) / N_total_points)
```

Where:

| Intervention type | Gravity |
|------------------|---------|
| Physical correction (e.g. H < L fixed) | 1.0 |
| Forward-fill applied (missing data) | 0.5 |
| Calendar alignment (point removed) | 0.2 |

`N_total_points` = total number of OHLCV data points in the dataset.

### Interpretation

| MPI | Meaning |
|-----|---------|
| 100 | Raw data was canonical. Zero intervention. |
| 80–99 | Minor interpolation. Certification reliable. |
| 60–79 | Moderate intervention. Advisory: review source quality. |
| < 60 | Heavy reconstruction. Certification valid but data provenance is weak. |

The MPI is emitted as part of the PROD envelope and surfaced in diagnostic
reports. In Certification Mode, MPI < 60 triggers a `LOW_PURITY_WARNING` flag
(non-blocking).

---

## 6. MIF-UID and Version Policy

The MIF-UID uniquely identifies a certification event:

```
MIF-UID = SHA-256(raw_data_hash || dqf_version || calendar || mode)
```

**Version policy**:

- **Patch** (1.1.x): bug fixes that do not alter check logic or cleaning
  algorithm. Prior certifications remain comparable.
- **Minor** (1.x.0): new advisory checks or threshold changes. Prior
  certifications remain valid but carry a version mismatch flag.
- **Major** (x.0.0): any change to CORE check logic or the Phase 2 cleaning
  algorithm. All prior MIF-UIDs are **invalidated for strict comparison**. A
  new certification run is required.

---

## 7. MIF Integration — precondition_gate

DQF acts as the `precondition_gate` for all MIF layers.

```
MIF_score = f(metric_logic) × precondition_gate(DQF)

precondition_gate(DQF) = {
    1.0   if DQF.overall_status == PASS
    cap   if DQF.overall_status == WARNING  (MPI-based, max 0.8)
    0.2   if DQF.overall_status == FAIL
    0.0   if DQF.overall_status == VOID
}
```

A `VOID` status (CORE check bypassed or signature invalid) sets the MIF score
to zero regardless of metric quality. The certification cannot proceed.

DAL exposes two interfaces to enforce this separation:

```python
dal.get_certified_data(symbol, calendar="NYSE")
# → calls DQF in CERTIFICATION mode, raises if DQF status is VOID or FAIL

dal.get_raw_data(symbol)
# → returns data without DQF; downstream MIF results carry DIAGNOSTIC annotation
```

---

## 8. Deprecations

| Removed | Reason | Replacement |
|---------|--------|-------------|
| Check 7 (Logging) | Infrastructure concern, not a data check | PROD envelope |
| Check 6 (Sanity Tests) | Statistical judgment, not physical law | MIF Layer 1 |
| Calendar auto-detection in Certification Mode | Non-deterministic | Mandatory metadata declaration |
| Configurable CORE checks | Breaks contractual guarantee | MIF-CORE checks are hardcoded |

---

## 9. Open Questions (Layer 1 Scope)

The following items are explicitly deferred to MIF Layer 1 (DAL) design:

- Statistical sanity tests (extreme returns, volatility spikes, zero-volume
  days) — moved from DQF Check 6
- Multi-source fusion validation — DAL responsibility before DQF handoff
- Cross-asset consistency checks

---

*This specification is the single source of truth for DQF design decisions.
Implementation details are in the source code. For the evolution history, see
`DQF_PROJECT.md`.*
