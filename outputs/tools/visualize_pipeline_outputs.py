"""Render a self-contained HTML visualization of the pipeline outputs for one AOI.

Shows, for one AOI:
  * raw Sentinel-2 observations (scatter, colored by usable / valid_fraction),
  * the linear-fill interpolation and the Whittaker smoothed daily curve,
  * per-point hover detail (raw / filled / smoothed / weight / usable),
  * the detected activity cycles (shaded spans + SOS/POS/EOS markers),
  * the HMM cross-check (state band + cycles) and the comparison metrics.

The output is one offline HTML file (no CDN, no runtime dependency) written to
``outputs/diagnostics/<aoi>/pipeline_visualization.html``. Deterministic.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from farmtrust_core.ingest.utils import safe_write_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def _read_observations(smoothed_csv: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with smoothed_csv.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if not row.get("ndvi_smoothed", "").strip():
                continue
            rows.append(
                {
                    "d": row["timestamp"][:10],
                    "raw": _maybe_float(row.get("ndvi_raw")),
                    "filled": _maybe_float(row.get("ndvi_filled")),
                    "smoothed": _maybe_float(row.get("ndvi_smoothed")),
                    "w": _maybe_float(row.get("valid_fraction")),
                    "usable": str(row.get("is_usable", "")).strip().lower() == "true",
                }
            )
    return rows


def _read_curve(curve_csv: Path) -> dict[str, Any]:
    dates: list[str] = []
    ndvi: list[float] = []
    with curve_csv.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            dates.append(row["date"])
            ndvi.append(float(row["ndvi_curve"]))
    return {"start": dates[0] if dates else None, "ndvi": ndvi}


def _maybe_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _sanitize(obj: Any) -> Any:
    """Replace non-finite floats with None so the embedded JSON is always valid.

    Python's json.dumps emits bare ``NaN`` / ``Infinity`` tokens which break
    browser ``JSON.parse``; fully-clouded rows can carry NaN raw values.
    """
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {key: _sanitize(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(value) for value in obj]
    return obj


def build_payload(
    aoi_id: str,
    smoothed_csv: Path,
    curve_csv: Path,
    season_windows: Path,
    hmm_json: Path | None,
) -> dict[str, Any]:
    seasons_doc = json.loads(season_windows.read_text(encoding="utf-8"))
    seasons = [
        {
            "id": s["season_id"],
            "start": s["start_date"],
            "peak": s["peak_date"],
            "end": s["end_date"],
            "lifecycle": s.get("lifecycle_status", "complete"),
            "detection": s.get("detection_status", "confirmed"),
            "quality": s.get("quality_label", ""),
            "amplitude": s.get("amplitude_ndvi"),
            "calendar": s.get("season_calendar_label", "unknown"),
            "peak_ndvi": s.get("peak_ndvi"),
            "duration": s.get("duration_days"),
        }
        for s in seasons_doc.get("seasons", [])
    ]
    hmm = None
    if hmm_json is not None and hmm_json.exists():
        doc = json.loads(hmm_json.read_text(encoding="utf-8"))
        hmm = {"cycles": doc.get("hmm_cycles", []), "comparison": doc.get("comparison", {})}

    model = seasons_doc.get("activity_detection_model", {})
    return {
        "aoi_id": aoi_id,
        "method": model.get("method", ""),
        "observations": _read_observations(smoothed_csv),
        "curve": _read_curve(curve_csv),
        "cycles": seasons,
        "hmm": hmm,
    }


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FarmTrust pipeline — __AOI__</title>
<style>
  :root { --bg:#ffffff; --ink:#1f2937; --muted:#6b7280; --line:#e5e7eb;
          --curve:#1b7837; --filled:#9ca3af; --raw-ok:#2e7d32; --raw-bad:#ef6c00;
          --sos:#2e7d32; --pos:#ef6c00; --eos:#8d6e63; --span:#3a7bd5;
          --low:#d6d3cd; --rising:#a5d6a7; --high:#1b7837; --declining:#c8a36b; }
  * { box-sizing:border-box; }
  body { font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); background:var(--bg); margin:0; padding:24px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:var(--muted); font-size:13px; margin-bottom:16px; }
  .card { border:1px solid var(--line); border-radius:10px; padding:16px; margin-bottom:18px; }
  .legend { display:flex; flex-wrap:wrap; gap:14px; font-size:12px; color:var(--muted); margin-top:8px; }
  .legend span { display:inline-flex; align-items:center; gap:6px; }
  .swatch { width:14px; height:3px; border-radius:2px; display:inline-block; }
  .dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
  table { border-collapse:collapse; width:100%; font-size:13px; }
  th,td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--line); }
  th { color:var(--muted); font-weight:600; }
  #tip { position:fixed; pointer-events:none; background:#111827; color:#fff; font-size:12px;
         padding:6px 8px; border-radius:6px; opacity:0; transform:translate(-50%,-120%); white-space:nowrap; }
  .pill { padding:1px 7px; border-radius:999px; font-size:11px; background:#eef2ff; color:#3730a3; }
  .foot { color:var(--muted); font-size:12px; line-height:1.5; }
</style>
</head>
<body>
<h1>FarmTrust pipeline visualization — __AOI__</h1>
<div class="sub" id="subline"></div>

<div class="card">
  <svg id="chart" viewBox="0 0 1100 460" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block" role="img"></svg>
  <div class="legend">
    <span><span class="swatch" style="background:var(--curve)"></span>Whittaker smoothed curve</span>
    <span><span class="swatch" style="background:var(--filled);height:0;border-top:2px dashed var(--filled)"></span>linear interpolation</span>
    <span><span class="dot" style="background:var(--raw-ok)"></span>raw obs (usable)</span>
    <span><span class="dot" style="background:var(--raw-bad)"></span>raw obs (low quality)</span>
    <span><span class="swatch" style="background:var(--span);opacity:.4"></span>detected cycle</span>
    <span>HMM phase band: <span class="dot" style="background:var(--rising)"></span>rising <span class="dot" style="background:var(--high)"></span>high <span class="dot" style="background:var(--declining)"></span>declining</span>
  </div>
</div>

<div class="card">
  <h3 style="margin-top:0">Detected activity cycles</h3>
  <table id="cycles"></table>
</div>

<div class="card" id="hmmcard">
  <h3 style="margin-top:0">HMM cross-check (research diagnostic — not production)</h3>
  <div id="hmmsummary" class="sub"></div>
  <table id="hmm"></table>
</div>

<div class="foot">
  Method: <code id="method"></code>. The daily curve is a <b>model-derived</b> analysis
  signal (weighted Whittaker), not direct evidence; gap/confidence is computed on real usable
  observations. The HMM panel is an independent research cross-check and never changes production output.
</div>

<div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const PAL={line:"#e5e7eb",muted:"#6b7280",curve:"#1b7837",filled:"#9ca3af",rawOk:"#2e7d32",
           rawBad:"#ef6c00",sos:"#2e7d32",eos:"#8d6e63",pos:"#ef6c00",span:"#3a7bd5",
           rising:"#a5d6a7",high:"#1b7837",declining:"#c8a36b"};
const W=1100,H=460,M={l:46,r:16,t:18,b:46}, IW=W-M.l-M.r, IH=H-M.t-M.b-26, BAND=18;
const SVGNS="http://www.w3.org/2000/svg";
const svg=document.getElementById("chart");
function el(n,a){const e=document.createElementNS(SVGNS,n);for(const k in a)e.setAttribute(k,a[k]);return e;}
function fmt(v){ return v==null?"—":(+v).toFixed(3); }
const day = d => Date.parse(d)/86400000;

try {
  const ndvi = DATA.curve.ndvi || [];
  const startISO = DATA.curve.start || (DATA.observations[0]&&DATA.observations[0].d);
  const x0 = day(startISO);
  const xmax = Math.max(ndvi.length?ndvi.length-1:1, ...DATA.observations.map(o=>day(o.d)-x0), 1);
  const X = off => M.l + (off/xmax)*IW;
  const Y = v => M.t + (1-Math.max(0,Math.min(1,v)))*IH;

  // y gridlines + labels
  for(let g=0; g<=1.0001; g+=0.25){ svg.appendChild(el("line",{x1:M.l,y1:Y(g),x2:W-M.r,y2:Y(g),stroke:PAL.line}));
    const t=el("text",{x:M.l-8,y:Y(g)+4,"text-anchor":"end",fill:PAL.muted,"font-size":11}); t.textContent=g.toFixed(2); svg.appendChild(t); }
  // month ticks (UTC; guarded against runaway loops)
  const sd=new Date(x0*86400000); let mk=new Date(Date.UTC(sd.getUTCFullYear(),sd.getUTCMonth(),1)), guard=0;
  while(((mk.getTime()/86400000)-x0)<=xmax && guard++<400){ const off=(mk.getTime()/86400000)-x0;
    if(off>=0){ svg.appendChild(el("line",{x1:X(off),y1:M.t,x2:X(off),y2:M.t+IH,stroke:PAL.line}));
      const t=el("text",{x:X(off),y:M.t+IH+16,"text-anchor":"middle",fill:PAL.muted,"font-size":10}); t.textContent=mk.toLocaleString("en",{month:"short",timeZone:"UTC"})+(mk.getUTCMonth()==0?" "+mk.getUTCFullYear():""); svg.appendChild(t);}
    mk.setUTCMonth(mk.getUTCMonth()+(xmax>500?2:1)); }

  // cycle spans + markers
  const colorFor = c => c.detection==="confirmed" ? PAL.span : "#b08968";
  DATA.cycles.forEach(c=>{ const a=X(day(c.start)-x0), b=X(day(c.end)-x0);
    svg.appendChild(el("rect",{x:a,y:M.t,width:Math.max(b-a,1),height:IH,fill:colorFor(c),opacity:0.10}));
    [["start",PAL.sos],["end",PAL.eos]].forEach(([k,col])=>{ svg.appendChild(el("line",{x1:X(day(c[k])-x0),y1:M.t,x2:X(day(c[k])-x0),y2:M.t+IH,stroke:col,"stroke-dasharray":"3,3","stroke-width":1,opacity:.7})); });
    const px=X(day(c.peak)-x0), py=Y(c.peak_ndvi||0.8);
    svg.appendChild(el("path",{d:`M${px} ${py-7} l6 11 l-12 0 z`,fill:PAL.pos}));
    const lab=el("text",{x:px,y:M.t-4,"text-anchor":"middle","font-size":10,"font-weight":700,fill:"#374151"}); lab.textContent=c.id.replace("season_","C")+(c.lifecycle!=="complete"?"*":""); svg.appendChild(lab);
  });

  // HMM phase band
  if(DATA.hmm && DATA.hmm.cycles && DATA.hmm.cycles.length){ const by=M.t+IH+24;
    DATA.hmm.cycles.forEach(h=>{ const a=X(day(h.sos_date)-x0), b=X(day(h.eos_date)-x0), p=X(day(h.pos_date)-x0);
      svg.appendChild(el("rect",{x:a,y:by,width:Math.max(p-a,1),height:BAND,fill:PAL.rising,opacity:.8}));
      svg.appendChild(el("rect",{x:p,y:by,width:Math.max(b-p,1),height:BAND,fill:PAL.declining,opacity:.8}));
      svg.appendChild(el("rect",{x:p-2,y:by,width:4,height:BAND,fill:PAL.high})); });
    const t=el("text",{x:M.l-8,y:by+13,"text-anchor":"end","font-size":10,fill:PAL.muted}); t.textContent="HMM"; svg.appendChild(t);
  }

  // filled (interp) line
  const fpts=DATA.observations.filter(o=>o.filled!=null).map(o=>`${X(day(o.d)-x0)},${Y(o.filled)}`).join(" ");
  if(fpts) svg.appendChild(el("polyline",{points:fpts,fill:"none",stroke:PAL.filled,"stroke-width":1.2,"stroke-dasharray":"4,4",opacity:.85}));
  // smoothed daily curve
  const cpts=ndvi.map((v,i)=>`${X(i)},${Y(v)}`).join(" ");
  if(cpts) svg.appendChild(el("polyline",{points:cpts,fill:"none",stroke:PAL.curve,"stroke-width":2.4}));
  // raw points
  DATA.observations.forEach(o=>{ if(o.raw==null)return; svg.appendChild(el("circle",{cx:X(day(o.d)-x0),cy:Y(o.raw),r:3,fill:o.usable?PAL.rawOk:PAL.rawBad,opacity:.85})); });

  // hover
  const tip=document.getElementById("tip"); const guide=el("line",{y1:M.t,y2:M.t+IH,stroke:"#9ca3af","stroke-width":1,opacity:0}); svg.appendChild(guide);
  const hi=el("circle",{r:5,fill:"none",stroke:"#111827","stroke-width":1.5,opacity:0}); svg.appendChild(hi);
  const overlay=el("rect",{x:M.l,y:M.t,width:IW,height:IH,fill:"transparent"}); svg.appendChild(overlay);
  overlay.addEventListener("mousemove",ev=>{ const r=svg.getBoundingClientRect(); const sx=(ev.clientX-r.left)*(W/r.width);
    const off=((sx-M.l)/IW)*xmax; let best=null,bd=1e9;
    DATA.observations.forEach(o=>{ const d=Math.abs((day(o.d)-x0)-off); if(d<bd){bd=d;best=o;} });
    if(!best)return; const bx=X(day(best.d)-x0); guide.setAttribute("x1",bx);guide.setAttribute("x2",bx);guide.setAttribute("opacity",.6);
    hi.setAttribute("cx",bx);hi.setAttribute("cy",Y(best.smoothed!=null?best.smoothed:best.raw));hi.setAttribute("opacity",1);
    tip.style.opacity=1; tip.style.left=ev.clientX+"px"; tip.style.top=ev.clientY+"px";
    tip.innerHTML=`<b>${best.d}</b> &nbsp; raw ${fmt(best.raw)} · filled ${fmt(best.filled)} · smoothed ${fmt(best.smoothed)}<br>valid_fraction ${fmt(best.w)} · ${best.usable?"usable":"low quality"}`; });
  overlay.addEventListener("mouseleave",()=>{ tip.style.opacity=0; guide.setAttribute("opacity",0); hi.setAttribute("opacity",0); });
} catch(err){
  const t=el("text",{x:20,y:30,fill:"#b91c1c","font-size":13}); t.textContent="visualization error: "+(err&&err.message?err.message:err); svg.appendChild(t);
  if(typeof console!=="undefined") console.error(err);
}

// text + tables (always populated)
document.getElementById("method").textContent=DATA.method;
document.getElementById("subline").textContent=`${DATA.observations.length} observations · ${(DATA.curve.ndvi||[]).length} daily curve points · ${DATA.cycles.length} detected cycle(s)`;
const ct=document.getElementById("cycles");
ct.innerHTML="<tr><th>cycle</th><th>start (SOS)</th><th>peak (POS)</th><th>end (EOS)</th><th>lifecycle</th><th>detection</th><th>quality</th><th>amplitude</th><th>calendar</th></tr>"+
  DATA.cycles.map(c=>`<tr><td>${c.id}</td><td>${c.start}</td><td>${c.peak}</td><td>${c.end}</td><td>${c.lifecycle}</td><td>${c.detection}</td><td>${c.quality}</td><td>${fmt(c.amplitude)}</td><td><span class="pill">${c.calendar}</span></td></tr>`).join("");
const hc=document.getElementById("hmmcard");
if(DATA.hmm){ const cmp=DATA.hmm.comparison||{};
  document.getElementById("hmmsummary").textContent=`Detector ${cmp.prod_cycle_count} vs HMM ${cmp.hmm_cycle_count} cycles · matched ${cmp.matched_count} · mean |peak Δ| ${cmp.mean_abs_pos_delta_days}d · agreement ${cmp.agreement_within_tolerance}`;
  const ht=document.getElementById("hmm");
  ht.innerHTML="<tr><th>HMM cycle</th><th>SOS</th><th>POS</th><th>EOS</th><th>lifecycle</th></tr>"+
    (DATA.hmm.cycles||[]).map((h,i)=>`<tr><td>H${i+1}</td><td>${h.sos_date}</td><td>${h.pos_date}</td><td>${h.eos_date}</td><td>${h.lifecycle_status}</td></tr>`).join("");
} else { hc.style.display="none"; }
</script>
</body>
</html>
"""


def render_html(payload: dict[str, Any]) -> str:
    data = json.dumps(_sanitize(payload), separators=(",", ":"), allow_nan=False)
    return (
        HTML_TEMPLATE.replace("__AOI__", payload["aoi_id"]).replace("__DATA__", data)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the pipeline visualization HTML for one AOI.")
    parser.add_argument("--aoi-id", required=True)
    parser.add_argument("--preprocess-dir", default=None, help="default: data/preprocess/<aoi-id>")
    parser.add_argument("--seasonal-dir", default=None, help="default: data/seasonal/<aoi-id>")
    parser.add_argument("--comparison-dir", default=None, help="default: outputs/diagnostics/<aoi-id>")
    parser.add_argument("--output", default=None, help="default: <comparison-dir>/pipeline_visualization.html")
    args = parser.parse_args()

    preprocess_dir = Path(args.preprocess_dir) if args.preprocess_dir else Path("data") / "preprocess" / args.aoi_id
    seasonal_dir = Path(args.seasonal_dir) if args.seasonal_dir else Path("data") / "seasonal" / args.aoi_id
    comparison_dir = Path(args.comparison_dir) if args.comparison_dir else Path("outputs") / "diagnostics" / args.aoi_id
    output = Path(args.output) if args.output else comparison_dir / "pipeline_visualization.html"

    payload = build_payload(
        aoi_id=args.aoi_id,
        smoothed_csv=preprocess_dir / "ndvi_smoothed.csv",
        curve_csv=preprocess_dir / "season_analysis_curve.csv",
        season_windows=seasonal_dir / "season_windows.json",
        hmm_json=comparison_dir / "hmm_cross_check.json",
    )
    safe_write_text(output, render_html(payload))
    logging.info("Wrote visualization to: %s", output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
