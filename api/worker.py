"""Background worker for running the Phase A pipeline."""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Dict

from sqlmodel import Session, select

from api.database import engine
from api.models import Job, Land, utc_now
from api.assessment_mapper import map_land_response
from farmtrust_core.ingest.pipeline import PipelineCancelledError
from farmtrust_core.io.paths import (
    aoi_dir,
    assessment_dir,
    preprocess_dir,
    quality_metrics_path,
    run_metadata_path,
    season_windows_path,
    seasonal_dir,
    smoothed_timeseries_path,
    timeseries_path,
)
from farmtrust_core.preprocess import build_preprocess_artifacts, write_preprocess_outputs
from farmtrust_core.scoring import build_land_assessment, write_land_assessment
from farmtrust_core.seasonal import build_season_payload, write_season_payload


PHASE_PROGRESS = {
    None: 0,
    "aoi_validation": 5,
    "satellite_fetch": 25,
    "vegetation_analysis": 55,
    "risk_modeling": 80,
    "report_generation": 95,
}

# In-memory cancel flags: job_id → threading.Event
_cancel_flags: Dict[str, threading.Event] = {}
_cancel_lock = threading.Lock()


def request_cancel(job_id: str) -> bool:
    """Signal the running worker for job_id to stop. Returns True if flag found."""
    with _cancel_lock:
        event = _cancel_flags.get(job_id)
    if event:
        event.set()
        return True
    return False


def _is_cancelled(job_id: str) -> bool:
    with _cancel_lock:
        event = _cancel_flags.get(job_id)
    return event is not None and event.is_set()


def progress_for_job(job: Job) -> int:
    if job.status == "succeeded":
        return 100
    if job.status in ("failed", "cancelled"):
        return max(PHASE_PROGRESS.get(job.phase, 0), 1)
    if job.status == "queued":
        return 0
    # Running: if we have scene progress during satellite_fetch, interpolate
    if job.status == "running" and job.phase == "satellite_fetch" and job.scene_total:
        phase_start = PHASE_PROGRESS.get("aoi_validation", 5)
        phase_end = PHASE_PROGRESS.get("vegetation_analysis", 55)
        fraction = job.scene_done / job.scene_total if job.scene_done else 0.0
        return int(phase_start + fraction * (phase_end - phase_start))
    return PHASE_PROGRESS.get(job.phase, 10)


def _append_log(session: Session, job: Job, message: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {message}"
    job.logs = f"{job.logs}\n{line}".strip()
    job.updated_at = utc_now()
    session.add(job)
    session.commit()
    session.refresh(job)


def _set_job(session: Session, job: Job, *, status: str | None = None, phase: str | None = None, error: str | None = None) -> None:
    if status is not None:
        job.status = status
    if phase is not None:
        job.phase = phase
    if error is not None:
        job.error = error
    job.updated_at = utc_now()
    if status == "running" and job.started_at is None:
        job.started_at = utc_now()
    if status in {"succeeded", "failed", "cancelled"}:
        job.completed_at = utc_now()
    session.add(job)
    session.commit()
    session.refresh(job)


def _on_scene_progress(job_id: str, done: int, total: int) -> None:
    """Update scene progress counters in the DB; called from worker thread."""
    with Session(engine) as s:
        job = s.get(Job, job_id)
        if job:
            job.scene_done = done
            job.scene_total = total
            job.updated_at = utc_now()
            s.add(job)
            s.commit()


def _run_job(job_id: str, land_id: str) -> None:
    # Register cancel flag
    cancel_event = threading.Event()
    with _cancel_lock:
        _cancel_flags[job_id] = cancel_event

    try:
        with Session(engine) as session:
            job = session.get(Job, job_id)
            land = session.get(Land, land_id)
            if job is None or land is None:
                return

            lookback_days: int = land.lookback_days or 730

            try:
                geometry = json.loads(land.geometry)
                end = date.today()
                start = end - timedelta(days=lookback_days)

                _set_job(session, job, status="running", phase="aoi_validation")
                _append_log(session, job, "[INFO] AOI geometry received and validated")

                _set_job(session, job, phase="satellite_fetch")
                _append_log(
                    session, job,
                    f"[INFO] Fetching Sentinel-2 scenes from {start.isoformat()} "
                    f"to {end.isoformat()} ({lookback_days} days lookback)"
                )
                from farmtrust_core.ingest.pipeline import write_outputs

                write_outputs(
                    output_dir=aoi_dir(land.aoi_id),
                    aoi_id=land.aoi_id,
                    bbox=[0, 0, 0, 0],
                    geometry=geometry,
                    start_date=start.isoformat(),
                    end_date=end.isoformat(),
                    max_cloud=30.0,
                    force_rerun=False,
                    limit_items=None,
                    log_signed_hrefs=False,
                    on_progress=lambda done, total: _on_scene_progress(job_id, done, total),
                    cancel_check=lambda: _is_cancelled(job_id),
                )

                _set_job(session, job, phase="vegetation_analysis")
                _append_log(session, job, "[INFO] Building smoothed vegetation time series")
                preprocess = build_preprocess_artifacts(
                    csv_path=timeseries_path(land.aoi_id),
                    metadata_path=run_metadata_path(land.aoi_id),
                )
                write_preprocess_outputs(
                    output_dir=preprocess_dir(land.aoi_id),
                    processed_observations=preprocess["processed_observations"],
                    quality_metrics=preprocess["quality_metrics"],
                )

                _append_log(session, job, "[INFO] Detecting season windows")
                season_payload = build_season_payload(
                    smoothed_csv_path=smoothed_timeseries_path(land.aoi_id),
                    quality_metrics_path=quality_metrics_path(land.aoi_id),
                )
                write_season_payload(output_dir=seasonal_dir(land.aoi_id), payload=season_payload)

                _set_job(session, job, phase="risk_modeling")
                _append_log(session, job, "[INFO] Running rule-based land assessment")
                assessment = build_land_assessment(
                    run_metadata_path=run_metadata_path(land.aoi_id),
                    smoothed_csv_path=smoothed_timeseries_path(land.aoi_id),
                    quality_metrics_path=quality_metrics_path(land.aoi_id),
                    season_payload_path=season_windows_path(land.aoi_id),
                )
                write_land_assessment(output_dir=assessment_dir(land.aoi_id), payload=assessment)

                _set_job(session, job, phase="report_generation")
                mapped = map_land_response(land, job)
                land.land_status = mapped.land_status
                land.trend_2y = mapped.trend_2y
                land.season_performance = mapped.season_performance
                land.risk_tier = mapped.risk_tier
                session.add(land)
                session.commit()

                _append_log(session, job, "[INFO] Analysis succeeded")
                _set_job(session, job, status="succeeded", phase="report_generation")

            except PipelineCancelledError:
                _set_job(session, job, status="cancelled")
                _append_log(session, job, "[INFO] Job cancelled by user")

            except Exception as exc:
                _set_job(session, job, status="failed", error=str(exc))
                _append_log(session, job, f"[ERROR] {exc}")

    finally:
        with _cancel_lock:
            _cancel_flags.pop(job_id, None)


def start_job(job_id: str, land_id: str) -> None:
    thread = threading.Thread(target=_run_job, args=(job_id, land_id), daemon=True)
    thread.start()
