"""Report evidence packet (T-11 Layer 5).

Aggregate the already-written per-AOI pipeline artifacts (land assessment,
season windows, quality metrics, run metadata) into a single grounded
``report_evidence_packet.json`` organised as an
``Observed -> Interpreted -> Confidence -> Watch`` evidence structure.

This is the *correctness* layer the polished report (Layer 6) and the bounded
assistant (T-04) consume. It invents no new evidence: every field is a
deterministic projection or template over fields already computed upstream.

Claim discipline (T-11 decisions):

* cautious land-status vocabulary -- one good cycle is "active" with limited
  history, never "single/double-cropped", "stable", or "trending";
* no crop identity -- ``season_calendar_label`` is a broad summer/winter
  calendar descriptor only, never a crop name;
* no yield / income / price / pest / legal claims except inside the fixed
  ``boundaries`` ("what this does NOT tell you") block, where they appear as
  explicit *exclusions*;
* no monitoring or neighbour-baseline sections (Decision Point 11);
* no wall-clock timestamp, so the artifact is byte-deterministic for tests.

Per-claim provenance (``claim_type``, ``provenance_level``, ``source``,
``method``, ``allowed_use``, ``restriction``) is attached by ``_apply_provenance``
as a deterministic post-pass over the built claims (T-04 foundation). The
bounded report assistant consumes these fields to keep its claim typing honest;
the Layer 6 report card ignores them, so they are additive (packet v1.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from farmtrust_core.ingest.utils import safe_write_text

PACKET_VERSION = "1.1"
PACKET_SCHEMA = "farmtrust_report_evidence_packet"
SEASONS_FOR_CERTIFIABLE_TREND = 5
# Parcel area is measured in feddan (the project unit; 1 feddan ~= 0.42 ha). Below ~0.7 feddan
# (~0.3 ha) the field-mean greenness gets unreliable near the Sentinel-2 10 m pixel grid.
SMALL_PARCEL_FEDDAN = 0.7
LAYERS = ("observed", "interpreted", "confidence", "watch")

SOURCE_ARTIFACTS = (
    "land_assessment.json",
    "season_windows.json",
    "quality_metrics.json",
    "run_metadata.json",
)

# Fixed hard-exclusion list ("what this does NOT tell you"). Never derived,
# never omitted: the only place yield/income/legal terms may appear.
BOUNDARIES = (
    "Harvested yield, tonnage, or output volume",
    "Price, revenue, input costs, or net income",
    "Water rights or allocation",
    "Ownership, title, or legal status",
    "Crop identity (not proven from satellite)",
    "Pest, disease, or in-field damage",
)

INDICATOR_NOTES = {
    "ndvi_peak": "Peak canopy greenness. A vigour signal, not a yield or income measure.",
    "ndvi_p95_peak": "Greenness of the densest pixels. Reads canopy density, not output.",
    "ndvi_spread_median": "Within-field greenness spread. A field-uniformity signal, not a crop-split proof.",
    "evi_peak": "Enhanced vegetation index peak. Corroborates the NDVI cycle.",
    "ndmi_median": "Canopy-moisture signal. Context only, not an irrigation or water-right claim.",
    "mndwi_median": "Surface-water signal. Staying low rules out a standing-water/flood read.",
}

# assessment confidence.level -> per-claim strength vocabulary.
_LEVEL_TO_STRENGTH = {"high": "strong", "medium": "moderate", "low": "limited"}
# risk-flag severity -> per-claim strength (how strongly a caveat applies).
_SEVERITY_TO_STRENGTH = {"high": "strong", "moderate": "moderate", "low": "limited"}
_TREND_TO_STATUS = {
    "improving": "improving",
    "declining": "declining",
    "stable": "stable",
    "uncertain": "too_soon_to_tell",
}

# --------------------------------------------------------------------------
# Per-claim provenance (T-04 foundation, packet v1.1)
# --------------------------------------------------------------------------
#
# A small, fixed typing vocabulary. Higher provenance_level == closer to a
# direct measurement; lower == more inferred. The assistant uses claim_type +
# restriction to keep its narration grounded and to refuse crop/yield claims.
CLAIM_TYPES = (
    "measured_observation",          # a number read off the data
    "deterministic_pipeline_result", # a rule/detector output over measurements
    "model_derived_analysis",        # derived from the smoothed/model curve
    "interpretation",                # an inferred pattern (confidence-gated)
    "boundary_exclusion",            # a statement of what is NOT observable
    "user_provided_local_context",   # context, not automatic truth
    "unknown",                       # provenance not established
)
_PROVENANCE_LEVEL = {
    "measured_observation": 4,
    "deterministic_pipeline_result": 4,
    "model_derived_analysis": 3,
    "interpretation": 2,
    "boundary_exclusion": 4,
    "user_provided_local_context": 1,
    "unknown": 0,
}
ALLOWED_USE = ("report", "chat", "status_explanation")
DEFAULT_RESTRICTION = "do_not_infer_crop_identity_or_yield"

# claim id -> (claim_type, source artifact, method). watch_<risk-code> ids are
# handled dynamically below; anything unmapped falls back to per-layer defaults.
CLAIM_PROVENANCE: dict[str, tuple[str, str, str]] = {
    "observation_coverage": ("measured_observation", "quality_metrics.json", "usable-observation coverage ratio"),
    "activity_cycles_observed": ("deterministic_pipeline_result", "season_windows.json", "peak/trough cycle detection"),
    "cycle_lifecycle_observed": ("model_derived_analysis", "season_windows.json", "crossing-reachability on the smoothed daily curve"),
    "calendar_pattern_observed": ("model_derived_analysis", "season_windows.json", "peak-month to broad-calendar mapping"),
    "no_cycle_observed": ("deterministic_pipeline_result", "land_assessment.json", "absence assessment"),
    "worked_field_interpreted": ("interpretation", "land_assessment.json", "land-status rule basis"),
    "intensity_interpreted": ("model_derived_analysis", "land_assessment.json", "complete-cycle per-year rate"),
    "intermittent_interpreted": ("interpretation", "land_assessment.json", "land-status rule basis"),
    "idle_interpreted": ("interpretation", "land_assessment.json", "absence assessment"),
    "unclear_interpreted": ("interpretation", "land_assessment.json", "absence assessment"),
    "not_assessed_interpreted": ("interpretation", "land_assessment.json", "assessment-status gate"),
    "conf_active_cultivation": ("deterministic_pipeline_result", "land_assessment.json", "coverage + usable-look count"),
    "conf_activity_rhythm": ("model_derived_analysis", "season_windows.json", "peak/trough detection on the smoothed curve"),
    "conf_stability": ("model_derived_analysis", "land_assessment.json", "trend over the observed record"),
    "conf_crop_identity": ("boundary_exclusion", "n/a", "crop identity is out of satellite scope"),
    "conf_yield": ("boundary_exclusion", "n/a", "yield/output is out of satellite scope"),
    "watch_short_record": ("measured_observation", "land_assessment.json", "history-coverage record length"),
    "watch_key_stage_gaps": ("measured_observation", "season_windows.json", "gap overlap vs real observation timestamps"),
    "watch_open_cycle": ("model_derived_analysis", "season_windows.json", "window-edge lifecycle status"),
    "watch_yield_invisible": ("boundary_exclusion", "n/a", "yield is not observable from greenness"),
}
# yield/crop-specific lines get a tighter restriction than the generic default.
_YIELD_RESTRICTION_IDS = {"conf_yield", "watch_yield_invisible"}
_CROP_RESTRICTION_IDS = {"conf_crop_identity"}
# Fallback claim_type by layer for any id not in CLAIM_PROVENANCE.
_LAYER_DEFAULT_TYPE = {
    "observed": "measured_observation",
    "interpreted": "interpretation",
    "confidence": "deterministic_pipeline_result",
    "watch": "deterministic_pipeline_result",
}


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN
        return None
    return result


def _humanize(code: str) -> str:
    return str(code).replace("_", " ").strip().capitalize()


def _claim(claim_id: str, layer: str, claim: str, confidence: str, rests_on: str) -> dict[str, Any]:
    return {
        "id": claim_id,
        "layer": layer,
        "claim": claim,
        "confidence": confidence,
        "rests_on": rests_on,
    }


def _interval_years(assessment: dict[str, Any]) -> Optional[float]:
    days = _coerce_float(assessment.get("history_coverage", {}).get("assessment_interval_days"))
    if days is None or days <= 0:
        return None
    return days / 365.25


def _duration_phrase(assessment: dict[str, Any]) -> str:
    years = _interval_years(assessment)
    if years is None:
        return "observed"
    if years >= 1.0:
        return f"{years:.1f}-year"
    days = assessment.get("history_coverage", {}).get("assessment_interval_days")
    return f"{int(days)}-day" if days else "observed"


def _parcel_area_feddan(run_metadata: dict[str, Any]) -> Optional[float]:
    # Fallback only: the worker passes Land.area_feddan straight into the builder. This probe
    # covers callers that don't (run_metadata.json does not currently carry area, so there it
    # returns None and the small-parcel limitation simply does not fire).
    for key in ("area_feddan", "aoi_area_feddan"):
        area = _coerce_float(run_metadata.get(key))
        if area is not None and area > 0:
            return area
    return None


# --------------------------------------------------------------------------
# Headline
# --------------------------------------------------------------------------


def _state_label(assessment: dict[str, Any]) -> str:
    if assessment.get("assessment_status") == "manual_review_required" or assessment.get("land_status") is None:
        return "Not assessed — satellite evidence insufficient"
    land_status = assessment["land_status"]
    history = assessment.get("history_coverage", {}).get("status")
    absence = assessment.get("absence_assessment", {}).get("status")
    if land_status == "active":
        if history == "sufficient_history":
            return "Active — multiple cycles observed"
        if history == "limited_history":
            return "Active — limited history"
        return "Active"
    if land_status == "intermittent":
        return "Intermittent activity"
    if land_status == "inactive":
        if absence == "absence_supported":
            return "Low activity — absence-gated"
        return "Activity unclear — insufficient evidence"
    return _humanize(land_status)


def _cropping_intensity(assessment: dict[str, Any]) -> Optional[str]:
    history = assessment.get("history_coverage", {})
    if history.get("status") == "insufficient_history":
        return None
    complete = _coerce_float(history.get("complete_activity_cycle_count")) or 0.0
    if complete <= 0:
        return None
    complete_int = int(complete)
    years = _interval_years(assessment)
    if years is not None and years >= 0.75:
        per_year = complete_int / years
        return f"{complete_int} complete cycle(s) over {years:.1f} yr (~{per_year:.1f}/yr, provisional)"
    return f"{complete_int} complete cycle(s) observed (provisional)"


def _headline(assessment: dict[str, Any]) -> dict[str, Any]:
    state_label = _state_label(assessment)
    season_count = int(_coerce_float(assessment.get("season_count")) or 0)
    duration = _duration_phrase(assessment)
    confidence_level = assessment.get("confidence", {}).get("level", "low")
    summary = (
        f"{state_label}. "
        f"{season_count} vegetation activity cycle(s) detected over the {duration} window "
        f"at {confidence_level} overall confidence. "
        "Evidence is satellite greenness only — not crop identity, yield, or financial outcome."
    )
    return {
        "state_label": state_label,
        "cropping_intensity": _cropping_intensity(assessment),
        "overall_confidence": confidence_level,
        "summary": summary,
    }


# --------------------------------------------------------------------------
# Claims (Observed / Interpreted / Confidence / Watch)
# --------------------------------------------------------------------------


def _key_stage_gap_season_ids(seasons: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for season in seasons:
        stage = season.get("gap_overlap_stage")
        risk = season.get("gap_overlap_risk")
        if stage in ("onset", "peak") or risk == "high":
            season_id = season.get("season_id")
            if season_id:
                ids.append(str(season_id))
    return ids


def _build_claims(assessment: dict[str, Any], season_payload: dict[str, Any]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []

    season_count = int(_coerce_float(assessment.get("season_count")) or 0)
    metrics = assessment.get("metrics_summary", {})
    usable = int(_coerce_float(metrics.get("usable_observation_count")) or 0)
    gap_risk = metrics.get("gap_risk", "unknown")
    coverage = assessment.get("satellite_evidence_coverage", {})
    coverage_status = coverage.get("status", "unknown")
    confidence_level = assessment.get("confidence", {}).get("level", "low")
    base_strength = _LEVEL_TO_STRENGTH.get(confidence_level, "limited")
    history = assessment.get("history_coverage", {})
    history_status = history.get("status")
    absence = assessment.get("absence_assessment", {})
    land_status = assessment.get("land_status")
    duration = _duration_phrase(assessment)
    evidence = assessment.get("evidence", {})
    land_status_basis = evidence.get("land_status_basis", "")

    seasons = season_payload.get("seasons", [])
    complete = int(_coerce_float(season_payload.get("complete_window_count")) or 0)
    open_count = int(_coerce_float(season_payload.get("open_window_count")) or 0)

    # --- Observed -----------------------------------------------------------
    claims.append(
        _claim(
            "observation_coverage",
            "observed",
            f"Satellite observation coverage over the {duration} window is {coverage_status}.",
            base_strength,
            coverage.get("rationale", ""),
        )
    )
    if season_count > 0:
        claims.append(
            _claim(
                "activity_cycles_observed",
                "observed",
                f"Greenness completed {season_count} vegetation activity cycle(s), each rising from and "
                "returning toward a low baseline.",
                "strong" if coverage_status in ("good", "fair") else "moderate",
                f"{usable} usable observations; gap risk {gap_risk}.",
            )
        )
        claims.append(
            _claim(
                "cycle_lifecycle_observed",
                "observed",
                f"{complete} cycle(s) are fully observed start to end; {open_count} reach a window edge.",
                "moderate",
                "Lifecycle assigned by crossing-reachability on the smoothed analysis curve.",
            )
        )
        labels = sorted({s.get("season_calendar_label") for s in seasons if s.get("season_calendar_label")})
        if labels:
            claims.append(
                _claim(
                    "calendar_pattern_observed",
                    "observed",
                    f"Cycle peaks fall in {', '.join(labels)} months of the year.",
                    "moderate",
                    "Peak-month mapping to a broad regional calendar; a summer/winter descriptor only, "
                    "not a crop label.",
                )
            )
    else:
        claims.append(
            _claim(
                "no_cycle_observed",
                "observed",
                "No vegetation activity cycle was detected in the observed window.",
                base_strength,
                absence.get("rationale", ""),
            )
        )

    # --- Interpreted --------------------------------------------------------
    if land_status == "active" and season_count >= 1:
        claims.append(
            _claim(
                "worked_field_interpreted",
                "interpreted",
                "The greenness rhythm is consistent with a worked, actively cropped field — not idle or "
                "abandoned ground.",
                "moderate",
                land_status_basis,
            )
        )
        years = _interval_years(assessment)
        per_year = complete / years if (years is not None and years >= 1.0) else None
        # Only call out multi-cycle cropping when the *rate* supports it (>= ~1.8 cycles/yr).
        # A raw count of 2 spread over ~2 years is ~1/yr — single-cropping, not intensive —
        # so gate on the per-year rate, not the total count (T-11 Point 5).
        if history_status == "sufficient_history" and per_year is not None and per_year >= 1.8:
            claims.append(
                _claim(
                    "intensity_interpreted",
                    "interpreted",
                    f"Roughly {per_year:.1f} complete vegetation cycles per year were observed — a "
                    "multi-cycle cropping rhythm (provisional; crop identity not inferred).",
                    "moderate",
                    f"{complete} complete cycles over {years:.1f} yr.",
                )
            )
    elif land_status == "intermittent":
        claims.append(
            _claim(
                "intermittent_interpreted",
                "interpreted",
                "Activity appears intermittent across the window rather than continuous.",
                base_strength,
                land_status_basis,
            )
        )
    elif land_status == "inactive":
        if absence.get("status") == "absence_supported":
            claims.append(
                _claim(
                    "idle_interpreted",
                    "interpreted",
                    "Sustained low greenness with adequate observation density is consistent with idle or "
                    "fallow ground — which is not the same as abandonment.",
                    base_strength,
                    absence.get("rationale", ""),
                )
            )
        else:
            claims.append(
                _claim(
                    "unclear_interpreted",
                    "interpreted",
                    "Evidence is insufficient to interpret land use; absence of activity is not established.",
                    "limited",
                    absence.get("rationale", ""),
                )
            )
    else:
        claims.append(
            _claim(
                "not_assessed_interpreted",
                "interpreted",
                "Land use is not interpreted: satellite evidence did not meet the automated assessment "
                "threshold.",
                "limited",
                land_status_basis,
            )
        )

    # --- Confidence breakdown ----------------------------------------------
    if land_status in ("active", "intermittent"):
        claims.append(
            _claim(
                "conf_active_cultivation",
                "confidence",
                "Confidence that the land is actively cultivated.",
                base_strength,
                f"{usable} usable looks; {coverage_status} coverage.",
            )
        )
    if season_count >= 1:
        claims.append(
            _claim(
                "conf_activity_rhythm",
                "confidence",
                "Confidence in the detected number and timing of activity cycles.",
                "moderate",
                "Peak/trough detection on the smoothed daily curve.",
            )
        )
    stability_strength = "moderate" if history_status == "sufficient_history" else "provisional"
    claims.append(
        _claim(
            "conf_stability",
            "confidence",
            "Confidence in multi-year stability or trend.",
            stability_strength,
            evidence.get("trend_basis")
            or "Track record is short; treat stability as provisional until a longer record accrues.",
        )
    )
    claims.append(
        _claim(
            "conf_crop_identity",
            "confidence",
            "Confidence in specific crop identity.",
            "none",
            "Crop identity is not inferred from the satellite signal.",
        )
    )
    claims.append(
        _claim(
            "conf_yield",
            "confidence",
            "Confidence in yield, output, or income.",
            "none",
            "Greenness is not yield; output and income are outside satellite scope.",
        )
    )

    # --- Watch --------------------------------------------------------------
    for flag in assessment.get("risk_flags", []):
        code = str(flag.get("code", "risk"))
        claims.append(
            _claim(
                f"watch_{code}",
                "watch",
                str(flag.get("reason", "")),
                _SEVERITY_TO_STRENGTH.get(flag.get("severity"), "moderate"),
                f"Risk flag: {code} (severity {flag.get('severity', 'unknown')}).",
            )
        )
    if history_status in ("limited_history", "insufficient_history"):
        claims.append(
            _claim(
                "watch_short_record",
                "watch",
                "The satellite track record is short, so one atypical season is hard to separate from "
                "normal year-to-year variation.",
                "moderate",
                history.get("rationale", ""),
            )
        )
    gap_ids = _key_stage_gap_season_ids(seasons)
    if gap_ids:
        claims.append(
            _claim(
                "watch_key_stage_gaps",
                "watch",
                f"Observation gaps touch the onset or peak of cycle(s) {', '.join(gap_ids)}, weakening "
                "their boundary dates.",
                "moderate",
                "Gap overlap measured against real usable observation timestamps.",
            )
        )
    if any(season.get("is_open") for season in seasons):
        claims.append(
            _claim(
                "watch_open_cycle",
                "watch",
                "The most recent cycle is still open at the window edge; its completion is not yet observed.",
                "moderate",
                "The observation window ends mid-cycle.",
            )
        )
    if season_count > 0:
        claims.append(
            _claim(
                "watch_yield_invisible",
                "watch",
                "Yield, crop health, and pest or disease damage are not observable from greenness — a "
                "vigorous canopy can still under-yield.",
                "none",
                "Satellite greenness is a canopy signal, not an output measure.",
            )
        )

    return claims


def _provenance_for(claim_id: str, layer: str) -> dict[str, Any]:
    if claim_id in CLAIM_PROVENANCE:
        claim_type, source, method = CLAIM_PROVENANCE[claim_id]
    elif claim_id.startswith("watch_"):
        # dynamic watch item from a rule-based risk flag
        claim_type, source, method = (
            "deterministic_pipeline_result",
            "land_assessment.json",
            "rule-based risk flag",
        )
    else:
        claim_type = _LAYER_DEFAULT_TYPE.get(layer, "unknown")
        source, method = "land_assessment.json", "unspecified"
    if claim_id in _YIELD_RESTRICTION_IDS:
        restriction = "yield_not_observable"
    elif claim_id in _CROP_RESTRICTION_IDS:
        restriction = "crop_identity_not_observable"
    else:
        restriction = DEFAULT_RESTRICTION
    return {
        "claim_type": claim_type,
        "provenance_level": _PROVENANCE_LEVEL[claim_type],
        "source": source,
        "method": method,
        "allowed_use": list(ALLOWED_USE),
        "restriction": restriction,
    }


def _apply_provenance(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach per-claim provenance metadata in place (T-04 foundation).

    A deterministic post-pass over the already-built claims, so the ~14
    ``_claim()`` call sites stay focused on the human-readable fields.
    """
    for claim in claims:
        claim.update(_provenance_for(claim["id"], claim["layer"]))
    return claims


def _layer_index(claims: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {layer: [] for layer in LAYERS}
    for claim in claims:
        index.setdefault(claim["layer"], []).append(claim["id"])
    return index


# --------------------------------------------------------------------------
# Activity record / track record / risk register / indicators
# --------------------------------------------------------------------------


def _activity_record(season_payload: dict[str, Any]) -> dict[str, Any]:
    cycles = [
        {
            "season_id": season.get("season_id"),
            "start_date": season.get("start_date"),
            "peak_date": season.get("peak_date"),
            "end_date": season.get("end_date"),
            "season_calendar_label": season.get("season_calendar_label"),
            "lifecycle_status": season.get("lifecycle_status"),
            "is_open": season.get("is_open"),
            "peak_ndvi": season.get("peak_ndvi"),
            "duration_days": season.get("duration_days"),
            "detection_status": season.get("detection_status"),
            "cycle_split_merged": season.get("cycle_split_merged"),
        }
        for season in season_payload.get("seasons", [])
    ]
    return {
        "cycles": cycles,
        "complete_window_count": int(_coerce_float(season_payload.get("complete_window_count")) or 0),
        "open_window_count": int(_coerce_float(season_payload.get("open_window_count")) or 0),
        "borderline_window_count": int(_coerce_float(season_payload.get("borderline_window_count")) or 0),
    }


def _track_record(assessment: dict[str, Any]) -> dict[str, Any]:
    history = assessment.get("history_coverage", {})
    # complete_activity_cycle_count is the authoritative counter (complete cycles only);
    # season_count is only a degraded fallback for an assessment dict missing history_coverage.
    observed = _coerce_float(history.get("complete_activity_cycle_count"))
    if observed is None:
        observed = _coerce_float(assessment.get("season_count")) or 0.0
    observed_int = int(observed)
    fraction = round(min(observed_int / SEASONS_FOR_CERTIFIABLE_TREND, 1.0), 3)
    status = _TREND_TO_STATUS.get(assessment.get("trend_2y"), "too_soon_to_tell")
    # status_so_far ("stable"/"improving"/...) must never be read as a settled verdict on a short
    # record: surface an explicit provisional flag so a renderer/assistant can gate it (T-11 Point 5).
    provisional = (
        observed_int < SEASONS_FOR_CERTIFIABLE_TREND
        or history.get("status") != "sufficient_history"
    )
    note = (
        f"{observed_int} of ~{SEASONS_FOR_CERTIFIABLE_TREND} seasons toward a certifiable use-stability "
        "claim; treat stability as provisional until a longer record accrues."
    )
    return {
        "seasons_observed": observed_int,
        "seasons_for_certifiable_trend": SEASONS_FOR_CERTIFIABLE_TREND,
        "fraction": fraction,
        "status_so_far": status,
        "provisional": provisional,
        "note": note,
    }


def _risk_register(
    assessment: dict[str, Any],
    season_payload: dict[str, Any],
    *,
    area_feddan: Optional[float],
) -> list[dict[str, Any]]:
    register: list[dict[str, Any]] = []

    for flag in assessment.get("risk_flags", []):
        register.append(
            {
                "item": _humanize(flag.get("code", "risk")),
                "kind": "land_risk",
                "severity": flag.get("severity", "moderate"),
                "reason": flag.get("reason", ""),
                "code": flag.get("code"),
            }
        )

    history = assessment.get("history_coverage", {})
    history_status = history.get("status")
    if history_status in ("limited_history", "insufficient_history"):
        register.append(
            {
                "item": "Short satellite record",
                "kind": "evidence_limitation",
                "severity": "moderate" if history_status == "insufficient_history" else "low",
                "reason": history.get("rationale", "Track record is too short for a long-term claim."),
            }
        )

    gap_ids = _key_stage_gap_season_ids(season_payload.get("seasons", []))
    if gap_ids:
        register.append(
            {
                "item": "Gaps at key cycle stages",
                "kind": "evidence_limitation",
                "severity": "moderate",
                "reason": f"Observation gaps touch the onset or peak of cycle(s) {', '.join(gap_ids)}.",
            }
        )

    if area_feddan is not None and area_feddan < SMALL_PARCEL_FEDDAN:
        register.append(
            {
                "item": "Small parcel near pixel resolution",
                "kind": "evidence_limitation",
                "severity": "moderate",
                "reason": (
                    f"Parcel ~{area_feddan:.2f} feddan; field-mean greenness is less reliable below "
                    f"~{SMALL_PARCEL_FEDDAN} feddan."
                ),
            }
        )

    return register


def _limitations(assessment: dict[str, Any], season_payload: dict[str, Any]) -> list[str]:
    items = [
        "Cycle boundary dates are model-derived from a smoothed daily curve, not direct observations "
        "(the nearest real observation is recorded per cycle).",
        "Findings are from a single parcel's own history; there is no peer or neighbour baseline.",
        "Crop identity, rotation, and management are not inferred from the satellite signal alone.",
    ]
    if any(season.get("is_open") for season in season_payload.get("seasons", [])):
        items.append("The most recent cycle is incomplete at the window edge.")
    return items


def _indicators(assessment: dict[str, Any]) -> dict[str, Any]:
    metrics = assessment.get("metrics_summary", {})
    values = {
        "ndvi_peak": metrics.get("interval_max_ndvi"),
        "ndvi_p95_peak": metrics.get("interval_max_ndvi_p95"),
        "ndvi_spread_median": metrics.get("interval_median_ndvi_spread"),
        "evi_peak": metrics.get("interval_max_evi"),
        "ndmi_median": metrics.get("interval_median_ndmi"),
        "mndwi_median": metrics.get("interval_median_mndwi"),
    }
    return {"values": values, "interpretation_notes": dict(INDICATOR_NOTES)}


# --------------------------------------------------------------------------
# Public entry points
# --------------------------------------------------------------------------


def build_report_evidence_packet(
    *,
    assessment_path: Path,
    season_payload_path: Path,
    quality_metrics_path: Path,
    run_metadata_path: Path,
    area_feddan: Optional[float] = None,
) -> dict[str, Any]:
    """Build the grounded report evidence packet from written pipeline artifacts.

    ``area_feddan`` (the parcel size, e.g. ``Land.area_feddan``) is an optional caller-supplied
    value that drives the small-parcel evidence limitation; when omitted it is probed from
    run_metadata. No network, no wall-clock -- same inputs -> byte-identical packet.
    """
    assessment = _load_json(assessment_path)
    season_payload = _load_json(season_payload_path)
    # quality_metrics / run_metadata are supplementary; tolerate absence.
    quality_metrics = _load_json(quality_metrics_path) if quality_metrics_path.exists() else {}
    run_metadata = _load_json(run_metadata_path) if run_metadata_path.exists() else {}

    area = area_feddan if (area_feddan is not None and area_feddan > 0) else _parcel_area_feddan(run_metadata)
    claims = _apply_provenance(_build_claims(assessment, season_payload))

    interval = assessment.get("interval", {})
    duration_days = assessment.get("history_coverage", {}).get("assessment_interval_days")

    return {
        "packet_version": PACKET_VERSION,
        "schema": PACKET_SCHEMA,
        "aoi_id": assessment.get("aoi_id") or str(quality_metrics.get("aoi_id", "")),
        "assessment_status": assessment.get("assessment_status"),
        "source_artifacts": list(SOURCE_ARTIFACTS),
        "interval": {
            "start_date": interval.get("start_date"),
            "end_date": interval.get("end_date"),
            "duration_days": int(duration_days) if _coerce_float(duration_days) is not None else None,
        },
        "headline": _headline(assessment),
        "claims": claims,
        "layers": _layer_index(claims),
        "activity_record": _activity_record(season_payload),
        "track_record": _track_record(assessment),
        "risk_register": _risk_register(assessment, season_payload, area_feddan=area),
        "limitations": _limitations(assessment, season_payload),
        "boundaries": list(BOUNDARIES),
        "indicators": _indicators(assessment),
        "local_context": [],
    }


def write_report_evidence_packet(output_dir: Path, packet: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "report_evidence_packet.json"
    safe_write_text(output_path, json.dumps(packet, indent=2, sort_keys=True))
    return output_path
