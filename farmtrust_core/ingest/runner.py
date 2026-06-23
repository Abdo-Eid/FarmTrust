"""Loader-agnostic ingestion seam.

Callers (API worker, CLI) depend on this stable interface instead of a concrete
loader. Swapping or adding an ingestion implementation changes only the dispatch
table here — never the callers.

Public surface:
  - run_ingestion(...)   single entry point; selects a loader by name
  - IngestCancelled      uniform cancellation signal callers catch, regardless
                         of which loader raised internally
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from farmtrust_core.ingest.cube_pipeline import (
    CubePipelineCancelledError,
    write_cube_outputs,
)


class IngestCancelled(Exception):
    """Raised when an in-progress ingestion run is cancelled by the caller.

    Loader-neutral: the runner translates each loader's own cancellation
    exception into this type so callers catch one thing.
    """


DEFAULT_LOADER = "odc"
SUPPORTED_LOADERS = ("odc",)


def run_ingestion(
    *,
    loader: str = DEFAULT_LOADER,
    output_dir: Path,
    aoi_id: str,
    bbox: List[float],
    start_date: str,
    end_date: str,
    max_cloud: float,
    geometry: Optional[Dict[str, Any]] = None,
    force_rerun: bool = False,
    limit_items: Optional[int] = None,
    log_signed_hrefs: bool = False,
    on_progress: Optional[Callable[[int, int], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    **loader_options: Any,
) -> None:
    """Run ingestion for one AOI through the selected loader.

    The keyword arguments above are the stable contract every loader honors.
    Loader-specific knobs (e.g. odc: ``resolution``, ``crs``, ``max_workers``)
    pass through ``loader_options`` so the contract does not churn when an
    implementation exposes extra dials.

    Raises:
        IngestCancelled: if ``cancel_check`` signalled mid-run.
        ValueError: if ``loader`` is not supported.
    """
    if loader not in SUPPORTED_LOADERS:
        raise ValueError(
            f"Unknown ingestion loader {loader!r}; supported: {SUPPORTED_LOADERS}"
        )

    try:
        write_cube_outputs(
            output_dir=output_dir,
            aoi_id=aoi_id,
            bbox=bbox,
            start_date=start_date,
            end_date=end_date,
            max_cloud=max_cloud,
            force_rerun=force_rerun,
            limit_items=limit_items,
            log_signed_hrefs=log_signed_hrefs,
            geometry=geometry,
            on_progress=on_progress,
            cancel_check=cancel_check,
            **loader_options,
        )
    except CubePipelineCancelledError as exc:
        raise IngestCancelled(str(exc)) from exc
