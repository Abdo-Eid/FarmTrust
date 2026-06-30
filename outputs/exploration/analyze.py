#!/usr/bin/env python3
# Menofia parcel: compute phenology + indices and SAVE FIGURES + a values file.
# This script does the MATH and CHARTS only. The HTML is authored separately as a template.
import os, glob, base64, json, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
warnings.filterwarnings("ignore")

OUT="/sessions/friendly-clever-keller/mnt/outputs"; FIG=os.path.join(OUT,"figs"); os.makedirs(FIG,exist_ok=True)
_LIVE=next((p for p in ["/sessions/friendly-clever-keller/mnt/work--aoi_demo_01/indices_timeseries.csv","/sessions/friendly-clever-keller/mnt/aoi_demo_01/indices_timeseries.csv"] if os.path.exists(p)), None)
SRC=_LIVE if _LIVE else glob.glob("/sessions/friendly-clever-keller/mnt/uploads/*indices_timeseries.csv")[0]
# --- preflight: refuse to build on a CSV that is stale/mismatched vs the cube (mirrors ingestion validation) ---
def _preflight(csv_path):
    import sys
    _CUBE=os.path.join(os.path.dirname(csv_path),"cube.zarr")
    n_csv=sum(1 for _ in open(csv_path,encoding="utf-8"))-1
    if not os.path.exists(_CUBE):
        print(f"PREFLIGHT: no cube alongside CSV; proceeding on CSV ({n_csv} rows) without cube cross-check."); return
    try:
        root_nt=json.load(open(_CUBE+"/time/zarr.json"))["shape"][0]
        nat_nt=json.load(open(_CUBE+"/20m/time/zarr.json"))["shape"][0]
    except Exception as e:
        print(f"PREFLIGHT FAIL: cube time metadata unreadable ({e}). Artifact partial/corrupt in this session — refusing to build. Re-sync the folder, then re-run."); sys.exit(2)
    if not (n_csv==root_nt==nat_nt):
        print(f"PREFLIGHT FAIL: CSV rows ({n_csv}) != cube time (root {root_nt}, 20m {nat_nt}). Stale/partial artifact — refusing to build a wrong report. Re-sync, then re-run."); sys.exit(2)
    print(f"PREFLIGHT OK: CSV {n_csv} rows == cube time {root_nt} (root==20m).")
_preflight(SRC)
LAMBDA=3000; PK_HEIGHT,PK_PROM,PK_DIST=0.40,0.18,55; TR_PROM,TR_DIST=0.08,40; AMP_FRAC=0.20
C_NDVI="#1b7837"; C_RAW="#9bbf9b"; C_EVI="#7fb069"; C_NDMI="#1565c0"
C_SOS="#2e7d32"; C_POS="#ef6c00"; C_EOS="#8d6e63"; WIN_TINT="#3a7bd5"; SUM_TINT="#e8a33d"
plt.rcParams.update({"figure.dpi":130,"font.size":11,"axes.edgecolor":"#888","axes.grid":True,
    "grid.color":"#e6e6e6","grid.linewidth":0.8,"axes.facecolor":"white","figure.facecolor":"white"})

# ---------- load + QA ----------
df=pd.read_csv(SRC); df["date"]=pd.to_datetime(df["solar_day"]); df=df.sort_values("date").reset_index(drop=True)
N_RAW=len(df)
df=df.dropna(subset=["ndvi_mean"]).copy(); df["valid_fraction"]=df["valid_fraction"].fillna(0.0)
qa=df[df["valid_fraction"]>=0.5].groupby("date",as_index=False).mean(numeric_only=True); N_QA=len(qa)
start,end=qa["date"].min(),qa["date"].max()
grid=pd.date_range(start,end,freq="D"); gi=pd.Series(np.arange(len(grid)),index=grid); m=len(grid)

# ---------- weighted Whittaker smoother ----------
def whittaker(v,w,lam,d=2):
    n=len(v); D=np.diff(np.eye(n),d,axis=0); return np.linalg.solve(np.diag(w)+lam*(D.T@D),w*v)
def fit(col,lam=LAMBDA):
    y=np.zeros(m); w=np.zeros(m); s=qa[["date",col]].dropna(); idx=gi.loc[s["date"]].values
    y[idx]=s[col].values; w[idx]=np.clip(qa.set_index("date").loc[s["date"],"valid_fraction"].values,0.1,1.0)
    return whittaker(y,w,lam)
S={c:fit(c) for c in ["ndvi_mean","ndvi_p95","evi_mean","ndmi_mean","mndwi_mean"]}; z=S["ndvi_mean"]

# ---------- peaks ----------
try:
    from scipy.signal import find_peaks
    def peaks(y,height=None,prominence=None,distance=None):
        p,_=find_peaks(y,height=height,prominence=prominence,distance=distance); return p
    ENGINE="scipy"
except Exception:
    ENGINE="numpy"
    def peaks(y,height=None,prominence=None,distance=None):
        n=len(y); cand=[i for i in range(1,n-1) if y[i]>y[i-1] and y[i]>=y[i+1]]
        if height is not None: cand=[i for i in cand if y[i]>=height]
        def prom(i):
            l=i;lm=y[i]
            while l>0 and y[l-1]<=y[i]: l-=1;lm=min(lm,y[l])
            r=i;rm=y[i]
            while r<n-1 and y[r+1]<=y[i]: r+=1;rm=min(rm,y[r])
            return y[i]-max(lm,rm)
        if prominence is not None: cand=[i for i in cand if prom(i)>=prominence]
        if distance is not None and cand:
            taken=np.zeros(n,bool); keep=[]
            for i in sorted(cand,key=lambda k:y[k],reverse=True):
                a,b=max(0,i-distance),min(n,i+distance+1)
                if not taken[a:b].any(): keep.append(i); taken[i]=True
            cand=sorted(keep)
        return np.array(cand,dtype=int)
pk=peaks(z,height=PK_HEIGHT,prominence=PK_PROM,distance=PK_DIST); tr=peaks(-z,prominence=TR_PROM,distance=TR_DIST)

# ---------- crop labels (from grower's field notes) ----------
def season_of(month): return "Summer" if month in (5,6,7,8,9) else "Winter"
def crop_full(c):
    y,s=c["pos_date"].year,c["season"]
    if s=="Summer": return "corn (maize)"
    return "wheat + berseem (half / half)" if y==2025 else ("berseem (clover)" if y==2026 else "wheat or berseem")
def crop_short(c):
    y,s=c["pos_date"].year,c["season"]
    if s=="Summer": return "corn"
    return "wheat+berseem" if y==2025 else ("berseem" if y==2026 else "wheat/berseem")

def build_cycle(p,lt,rt,trunc_start=False,trunc_end=False):
    base=min(z[lt],z[rt]); amp=z[p]-base; thr=base+AMP_FRAC*amp
    up=np.where(z[lt:p+1]>=thr)[0]; dn=np.where(z[p:rt+1]<=thr)[0]
    sos=lt+up[0] if (len(up) and not trunc_start) else lt
    eos=p+dn[0] if (len(dn) and not trunc_end) else rt
    integ=float(np.trapz(np.clip(z[sos:eos+1]-base,0,None)))
    return dict(p=int(p),sos=int(sos),eos=int(eos),base=float(base),amp=float(amp),peak=float(z[p]),integ=integ,
        season=season_of(grid[p].month),pos_date=grid[p],sos_date=grid[sos],eos_date=grid[eos],
        dur=int(eos-sos),trunc_start=trunc_start,trunc_end=trunc_end)

cycles=[]
for p in pk:
    lt=tr[tr<p].max() if (tr<p).any() else 0; rt=tr[tr>p].min() if (tr>p).any() else m-1
    cycles.append(build_cycle(p,lt,rt,trunc_start=not (tr<p).any() and z[0]>z[lt]+0.2,
                                       trunc_end=not (tr>p).any() and z[m-1]>z[rt]+0.2))
if len(tr):
    ft=tr.min()
    if z[0]>z[ft]+0.20 and z[0]>0.45:
        plead=int(np.argmax(z[:ft+1]))
        if not any(c["p"]==plead for c in cycles): cycles.append(build_cycle(plead,0,ft,trunc_start=True))
    ltt=tr.max()
    if z[m-1]>z[ltt]+0.20 and z[m-1]>0.45:
        ptail=int(ltt+np.argmax(z[ltt:]))
        if not any(c["p"]==ptail for c in cycles): cycles.append(build_cycle(ptail,ltt,m-1,trunc_end=True))
cycles=[c for c in cycles if c["amp"]>=PK_PROM*0.8]; cycles.sort(key=lambda c:c["pos_date"])
for c in cycles:
    a,b=c["sos"],c["p"]; c["estab_gap"]=float(np.mean(S["ndvi_p95"][a:b]-S["ndvi_mean"][a:b])) if b>a else 0.0
patchy=max(cycles,key=lambda c:c["estab_gap"]) if cycles else None
span_years=(end-start).days/365.25; intensity=len(cycles)/span_years
winters=[c for c in cycles if c["season"]=="Winter"]; summers=[c for c in cycles if c["season"]=="Summer"]
ws=sorted(winters,key=lambda c:c["pos_date"]); ss=sorted(summers,key=lambda c:c["pos_date"])
peak_overall=float(np.max(z)); min_overall=float(np.min(z)); active_pct=100*float((z>0.6).sum())/m
mndwi_max=float(np.max(S["mndwi_mean"]))

print(f"engine={ENGINE} qa={N_QA} cycles={len(cycles)} intensity={intensity:.2f}/yr")
for i,c in enumerate(cycles,1):
    print(f"  C{i} {c['season']:7s} {crop_short(c):14s} SOS {c['sos_date'].date()} POS {c['pos_date'].date()} "
          f"EOS {c['eos_date'].date()} dur {c['dur']:3d} peak {c['peak']:.2f} gap {c['estab_gap']:.3f}")

# ---------- figures ----------
def save(fig,name): p=os.path.join(FIG,name); fig.savefig(p,bbox_inches="tight"); plt.close(fig); return p
def uri(path): return "data:image/png;base64,"+base64.b64encode(open(path,"rb").read()).decode()
def tint(s): return WIN_TINT if s=="Winter" else SUM_TINT
def fmt(ax): ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
FIGS={}

fig,ax=plt.subplots(figsize=(14,5.6))
ax.scatter(qa["date"],qa["ndvi_mean"],s=16,c=C_RAW,alpha=.7,zorder=2); ax.plot(grid,z,color=C_NDVI,lw=2.4,zorder=3)
for i,c in enumerate(cycles,1):
    ax.axvspan(c["sos_date"],c["eos_date"],color=tint(c["season"]),alpha=.10,zorder=1)
    if not c["trunc_start"]: ax.axvline(c["sos_date"],color=C_SOS,ls="--",lw=1,alpha=.7)
    if not c["trunc_end"]:   ax.axvline(c["eos_date"],color=C_EOS,ls="--",lw=1,alpha=.7)
    ax.scatter([c["pos_date"]],[c["peak"]],marker="*",s=170,color=C_POS,zorder=5,edgecolor="white",linewidth=.6)
    lbl="C%d - %s\npeak %.2f%s"%(i,crop_short(c),c["peak"]," (partial)" if (c["trunc_start"] or c["trunc_end"]) else "")
    ax.annotate(lbl,(c["pos_date"],c["peak"]),textcoords="offset points",xytext=(0,12),ha="center",fontsize=8.5,
        fontweight="bold",color="#333",bbox=dict(boxstyle="round,pad=0.2",fc="white",ec=tint(c["season"]),alpha=.9))
ax.set_ylim(0,1); ax.set_ylabel("NDVI"); fmt(ax)
ax.set_title("Crop phenology timeline - green-up (SOS) to peak (star) to harvest/senescence (EOS)",fontsize=12,fontweight="bold")
ax.legend(handles=[Line2D([0],[0],color=C_NDVI,lw=2.4,label="Smoothed NDVI"),
    Line2D([0],[0],marker="o",color="none",mfc=C_RAW,markersize=7,label="Raw Sentinel-2"),
    Line2D([0],[0],marker="*",color="none",mfc=C_POS,markersize=12,label="Peak of season"),
    Line2D([0],[0],color=C_SOS,ls="--",label="Start of season"),
    Line2D([0],[0],color=C_EOS,ls="--",label="End of season"),
    Line2D([0],[0],marker="s",color="none",mfc=WIN_TINT,alpha=.4,markersize=9,label="Winter (wheat/berseem)"),
    Line2D([0],[0],marker="s",color="none",mfc=SUM_TINT,alpha=.5,markersize=9,label="Summer (corn)")],
    loc="lower left",ncol=4,fontsize=8.3,framealpha=.95)
FIGS["FIG1"]=uri(save(fig,"f1_timeline.png"))

fig,(a1,a2)=plt.subplots(1,2,figsize=(14,3.4),gridspec_kw={"width_ratios":[3,1]})
sc=a1.scatter(qa["date"],qa["valid_fraction"],c=qa["min_cloud_cover"],cmap="YlOrBr",s=22,vmin=0,vmax=30)
a1.set_ylabel("valid pixel fraction"); a1.set_ylim(-0.03,1.05); fmt(a1)
a1.set_title("Acquisition quality (color = % cloud)",fontsize=11,fontweight="bold"); plt.colorbar(sc,ax=a1,label="cloud %",pad=.01)
a2.hist(df["valid_fraction"],bins=20,color="#5a9bd4",edgecolor="white"); a2.axvline(0.5,color="#c0392b",ls="--",lw=1.2)
a2.set_title("Valid-fraction histogram",fontsize=11,fontweight="bold"); a2.set_xlabel("valid fraction"); a2.set_ylabel("# scenes")
FIGS["FIG2"]=uri(save(fig,"f2_quality.png"))

fig,ax=plt.subplots(figsize=(14,4.6))
for c in cycles: ax.axvspan(c["sos_date"],c["eos_date"],color=tint(c["season"]),alpha=.07)
ax.plot(grid,S["ndvi_mean"],color=C_NDVI,lw=2.2,label="NDVI (greenness)")
ax.plot(grid,S["evi_mean"],color=C_EVI,lw=1.7,label="EVI (dense-canopy greenness)")
ax.plot(grid,S["ndmi_mean"],color=C_NDMI,lw=1.8,label="NDMI (canopy moisture)")
ax.axhline(0,color="#bbb",lw=.8); ax.set_ylabel("index value"); fmt(ax)
ax.set_title("Greenness vs canopy moisture - NDMI falling while NDVI holds = water stress (watch summer corn)",fontsize=11.5,fontweight="bold")
ax.legend(loc="upper right",ncol=3,fontsize=9); FIGS["FIG3"]=uri(save(fig,"f3_veg.png"))

fig,ax=plt.subplots(figsize=(14,4.2))
g=pd.DataFrame({"date":grid,"ndvi":z}); g["doy"]=g["date"].dt.dayofyear; g["yr"]=g["date"].dt.year
for yr,col in zip(sorted(g["yr"].unique()),["#9e9e9e","#1b7837","#ef6c00"]):
    s=g[g["yr"]==yr]; ax.plot(s["doy"],s["ndvi"],lw=2.2,color=col,label=str(yr))
ax.set_xlabel("day of year"); ax.set_ylabel("NDVI"); ax.set_ylim(0,1)
ax.set_xticks([1,32,60,91,121,152,182,213,244,274,305,335]); ax.set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])
ax.set_title("Year-over-year NDVI - compare planting timing and vigour across seasons",fontsize=11.5,fontweight="bold")
ax.legend(title="year",fontsize=9); FIGS["FIG4"]=uri(save(fig,"f4_yoy.png"))

fig,ax=plt.subplots(figsize=(14,3.8))
ax.fill_between(grid,S["ndvi_mean"],S["ndvi_p95"],color="#1b7837",alpha=.18,label="within-field spread")
ax.plot(grid,S["ndvi_p95"],color="#2e7d32",lw=1.3,ls="--",label="NDVI p95 (greenest pixels)")
ax.plot(grid,S["ndvi_mean"],color=C_NDVI,lw=2.0,label="NDVI mean")
ax.set_ylim(0,1); ax.set_ylabel("NDVI"); fmt(ax)
ax.set_title("Field uniformity - a wide mean vs p95 gap means patchy / mixed stand",fontsize=11.5,fontweight="bold")
ax.legend(loc="lower left",fontsize=9); FIGS["FIG5"]=uri(save(fig,"f5_hetero.png"))

fig,ax=plt.subplots(figsize=(14,4.4))
gc=pd.DataFrame({"date":grid,"ndvi":z,"ndmi":S["ndmi_mean"]}); gc["doy"]=gc["date"].dt.dayofyear; gc["yr"]=gc["date"].dt.year
ax.axvspan(165,210,color="#e57373",alpha=.10)
ax.text(187,0.06,"whorl / vegetative stage\n(Fall Armyworm strike window)",ha="center",fontsize=8.5,color="#c0392b")
for yr,col,lab in [(2024,"#9e9e9e","2024"),(2025,"#1b7837","2025 (unsprayed)")]:
    s=gc[(gc["yr"]==yr)&(gc["doy"]>=150)&(gc["doy"]<=272)]
    ax.plot(s["doy"],s["ndvi"],lw=2.4,color=col,label="corn %s - NDVI"%lab)
    ax.plot(s["doy"],s["ndmi"],lw=1.4,color=col,ls=":",alpha=.85,label="corn %s - NDMI"%lab)
    if len(s):
        p=s.loc[s["ndvi"].idxmax()]; ax.scatter([p["doy"]],[p["ndvi"]],marker="*",s=150,color=col,edgecolor="white",zorder=5)
        ax.annotate("peak %.2f"%p["ndvi"],(p["doy"],p["ndvi"]),textcoords="offset points",xytext=(0,9),ha="center",fontsize=8.5,color=col)
ax.set_xlim(150,272); ax.set_ylim(0,1)
ax.set_xticks([152,166,182,196,213,227,244,258]); ax.set_xticklabels(["1 Jun","15 Jun","1 Jul","15 Jul","1 Aug","15 Aug","1 Sep","15 Sep"])
ax.set_ylabel("index value")
ax.set_title("Corn seasons compared - NDVI peaks ~0.80 and stays uniform: no clear Fall Armyworm fingerprint",fontsize=11.3,fontweight="bold")
ax.legend(fontsize=8.3,ncol=2,loc="upper right"); FIGS["FIG6"]=uri(save(fig,"f6_corn.png"))

# pixel-level figures from cube_explore.py (if present)
for k,fn in [("FIG7","f7_spatial_peaks.png"),("FIG8","f8_zones.png"),("FIG9","f9_validation.png"),("FIG10","f10_cuts.png"),("FIG11","f11_sweep.png"),("FIG12","f12_ndre.png"),("FIG13","msavi_vs_ndvi.png"),("FIG14","f14_hmm.png")]:
    p=os.path.join(FIG,fn)
    if os.path.exists(p): FIGS[k]=uri(p)

# ---------- dynamic HTML fragments (small, safe) ----------
def esc(s): return s.replace("&","&amp;")
rows=[]
for i,c in enumerate(cycles,1):
    badge='<span class="pill %s">%s</span>'%(c["season"].lower(),c["season"])
    sos="-" if c["trunc_start"] else c["sos_date"].strftime("%d %b %Y")
    eos="-" if c["trunc_end"] else c["eos_date"].strftime("%d %b %Y")
    dur="-" if (c["trunc_start"] or c["trunc_end"]) else str(c["dur"])
    if c["trunc_start"]: plant="- (standing before record starts)"
    else: plant=(c["sos_date"]-pd.Timedelta(days=21)).strftime("%d %b")+" to "+(c["sos_date"]-pd.Timedelta(days=7)).strftime("%d %b %Y")
    note=[]
    if c["trunc_start"]: note.append('<span class="flag">partial start</span>')
    if c["trunc_end"]: note.append('<span class="flag">partial end</span>')
    rows.append("<tr><td class='c'>C%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='c'>%s</td>"
        "<td class='c'>%.2f</td><td class='c'>%.2f</td><td class='c'>%.0f</td><td>%s</td><td style='font-size:12px'>%s</td><td>%s</td></tr>"
        %(i,badge,sos,c["pos_date"].strftime("%d %b %Y"),eos,dur,c["peak"],c["amp"],c["integ"],crop_full(c),plant," ".join(note)))
ROWS="\n".join(rows)

ins=[]
ins.append("<b>Double-cropped, ~%.1f cycles/year.</b> <i>What led to this:</i> the curve shows two complete green-up to harvest waves every year - a winter crop (Oct-May), then corn (Jun-Sep) - so the field touches bare soil (NDVI ~ %.2f) only briefly at each turnover."%(intensity,min_overall))
ins.append("<b>2024/25 winter was your half-wheat / half-berseem field - and the satellite caught the split.</b> <i>What led to this:</i> during establishment the greenest half ran about <b>%.2f NDVI</b> above the field average - the widest such gap in the whole record. That gap <i>is</i> two crops growing at different speeds on one parcel; your notes confirm it. Not a crop failure."%patchy["estab_gap"])
if len(ws)>=2:
    sh=ws[-1]["pos_date"].dayofyear-ws[0]["pos_date"].dayofyear
    ins.append("<b>2025/26 winter was berseem only - and its shape said so before you told me.</b> <i>What led to this:</i> it peaked about <b>%d days later</b> (March vs Feb), stayed green ~%d days longer, and carried the flat, multi-cut plateau clover gives."%(sh,ws[-1]["dur"]-ws[0]["dur"]))
ins.append("<b>Last year's corn (2025), left unsprayed for Fall Armyworm, looks normal in NDVI</b> - clean, uniform, peak %.2f. <i>What led to this:</i> a 10 m greenness index cannot see FAW (it averages out patchy whorl damage, saturates near 0.8, and FAW hits yield/ears more than canopy green). See the corn section - a limitation, not a contradiction."%max(c["peak"] for c in ss))
ins.append("<b>You're planting corn now (2026).</b> <i>What led to this:</i> the record ends 19 June at berseem senescence (NDVI falling through 0.25), so this season sits just past the data's edge - the moment to start tracking it, ideally with a red-edge index this time.")
ins.append("<b>No rice, confirmed both ways.</b> You've never flooded, and the data agrees: MNDWI never rises above <b>%.2f</b> all year - nowhere near standing-water values."%mndwi_max)
INSIGHTS="\n".join("<li>%s</li>"%x for x in ins)

cards=[("Observations",str(N_QA),"clean scenes of %d"%N_RAW),("Time span","%.1f yr"%span_years,start.strftime("%b %Y")+" - "+end.strftime("%b %Y")),
       ("Crop cycles",str(len(cycles)),"~%.1f/yr - double-crop"%intensity),("Peak NDVI","%.2f"%peak_overall,"dense canopy"),
       ("Active canopy","%.0f%%"%active_pct,"of days NDVI &gt; 0.6"),("Sensor","S-2 10 m","tiles 36RTU/36RUU")]
CARDS="".join('<div class="card"><div class="k">%s</div><div class="t">%s</div><div class="s">%s</div></div>'%(v,t,s) for t,v,s in cards)

# ---------- inject into the directly-authored template ----------
tpl=open(os.path.join(OUT,"report_template.html")).read()
repl={"@@CARDS@@":CARDS,"@@INSIGHTS@@":INSIGHTS,"@@ROWS@@":ROWS,"@@NQA@@":str(N_QA),"@@NRAW@@":str(N_RAW),
      "@@DROPPED@@":str(N_RAW-N_QA),"@@LAMBDA@@":str(LAMBDA),"@@AMP@@":str(int(AMP_FRAC*100)),"@@ENGINE@@":ENGINE}
repl.update({"@@%s@@"%k:v for k,v in FIGS.items()})
for k,v in repl.items(): tpl=tpl.replace(k,v)
with open(os.path.join(OUT,"menofia_ndvi_report.html"),"w") as f: f.write(tpl)
print("WROTE report", len(tpl), "bytes")
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        