#!/usr/bin/env python3
# Pixel-level enhancement: decode the raw Sentinel-2 cube (Zarr v3, zstd) WITHOUT zarr/xarray,
# validate against the CSV, and map the field's internal structure (the wheat/berseem split).
import subprocess, os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

AOI="/sessions/friendly-clever-keller/mnt/aoi_demo_01"
OUT="/sessions/friendly-clever-keller/mnt/outputs"; FIG=os.path.join(OUT,"figs"); os.makedirs(FIG,exist_ok=True)
BASE=np.datetime64("2024-06-21"); INVALID={0,1,3,7,8,9,10,11}; NT,NY,NX=262,6,18

def de(path,dtype,shape):
    raw=subprocess.run(["unzstd","-c",os.path.join(AOI,path)],capture_output=True).stdout
    return np.frombuffer(raw,dtype=dtype).reshape(shape)
def band(b,dt="<u2"): return np.stack([de(f"cube.zarr/{b}/c/{t}/0/0",dt,(NY,NX)) for t in range(NT)]).astype(float)

T=de("cube.zarr/time/c/0","<i8",(NT,)); dates=BASE+T.astype("timedelta64[D]")
b04=band("B04"); b08=band("B08"); scl=np.stack([de(f"cube.zarr/SCL/c/{t}/0/0","<u1",(NY,NX)) for t in range(NT)])
refl=lambda dn:(dn-1000.0)/10000.0
valid=(~np.isin(scl,list(INVALID)))&(b04>0)&(b08>0)
ndvi=np.where(valid,(refl(b08)-refl(b04))/(refl(b08)+refl(b04)+1e-9),np.nan)

def window(d0,d1): return (dates>=np.datetime64(d0))&(dates<=np.datetime64(d1))
def nearest(dt):
    i=int(np.argmin(np.abs(dates-np.datetime64(dt)))); return i
def field_mean(arr2d_stack,sel): return np.nanmean(arr2d_stack[sel].reshape(sel.sum(),-1),axis=1)

# ---- validation vs CSV ----
fm=np.nanmean(ndvi.reshape(NT,-1),axis=1)
csv=pd.read_csv(os.path.join(AOI,"indices_timeseries.csv")); csv["date"]=pd.to_datetime(csv["solar_day"]).values.astype("datetime64[D]")
mrg=pd.merge(pd.DataFrame({"date":dates,"cube":fm}),csv[["date","ndvi_mean"]],on="date").dropna()
r=mrg["cube"].corr(mrg["ndvi_mean"]); bias=(mrg["cube"]-mrg["ndvi_mean"]).mean()
print("VALIDATION corr=%.3f bias=%.4f n=%d"%(r,bias,len(mrg)))

plt.rcParams.update({"figure.dpi":130,"font.size":10,"figure.facecolor":"white","axes.facecolor":"white"})
GREEN=plt.get_cmap("RdYlGn").copy(); GREEN.set_bad("#d9d9d9")
VAR=plt.get_cmap("magma").copy(); VAR.set_bad("#d9d9d9")

def mapax(ax,data,vmin,vmax,cmap,title,cbar="NDVI"):
    im=ax.imshow(data,cmap=cmap,vmin=vmin,vmax=vmax,aspect="equal")
    ax.set_title(title,fontsize=9.5,fontweight="bold"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_edgecolor("#999")
    cb=plt.colorbar(im,ax=ax,fraction=0.06,pad=0.03); cb.ax.tick_params(labelsize=7); cb.set_label(cbar,fontsize=7)
    return im

# ---- F7: spatial NDVI at each cycle peak ----
peaks=[("2024-07-06","C1  Corn  Jul 2024"),("2025-02-05","C2  Wheat+Berseem  Feb 2025"),
       ("2025-07-28","C3  Corn  Jul 2025"),("2026-03-14","C4  Berseem  Mar 2026")]
fig,axes=plt.subplots(1,4,figsize=(15,3.2))
for ax,(d,lab) in zip(axes,peaks):
    mapax(ax,ndvi[nearest(d)],0.2,0.9,GREEN,lab)
fig.suptitle("The field from space at each crop peak  (top=North, left=West; ~180 m x 60 m, 10 m pixels)",fontsize=11,fontweight="bold",y=1.04)
fig.savefig(os.path.join(FIG,"f7_spatial_peaks.png"),bbox_inches="tight"); plt.close(fig)

# ---- F8: winter has two zones, summer is one ----
WS=window("2024-11-01","2025-04-15"); SS=window("2025-06-15","2025-09-13")
wmean=np.nanmean(ndvi[WS],axis=0); wstd=np.nanstd(ndvi[WS],axis=0); smean=np.nanmean(ndvi[SS],axis=0)
fig,axes=plt.subplots(1,3,figsize=(15,3.3))
mapax(axes[0],wmean,0.6,0.9,GREEN,"Winter 2024/25  -  mean NDVI")
mapax(axes[1],wstd,0.04,0.19,VAR,"Winter 2024/25  -  temporal variability\n(high = berseem cuttings)","std")
mapax(axes[2],smean,0.45,0.7,GREEN,"Summer 2025 corn  -  mean NDVI\n(one uniform crop)")
fig.suptitle("Inside the winter field: two zones (steady wheat vs cut-driven berseem) - the half/half split, seen from orbit. Summer corn is uniform.",fontsize=10.5,fontweight="bold",y=1.05)
fig.savefig(os.path.join(FIG,"f8_zones.png"),bbox_inches="tight"); plt.close(fig)

# ---- F9: validation overlay ----
fig,ax=plt.subplots(figsize=(14,3.4))
ax.plot(mrg["date"],mrg["ndvi_mean"],lw=2.2,color="#1b7837",label="CSV ndvi_mean (delivered)")
ax.plot(mrg["date"],mrg["cube"],lw=1.1,color="#ef6c00",ls="--",label="Recomputed from raw cube pixels")
ax.set_ylim(0,1); ax.set_ylabel("NDVI"); ax.legend(fontsize=9,loc="lower left")
ax.set_title("Validation: the delivered CSV reproduced from raw bands  (r=%.3f, bias=%.3f, n=%d)"%(r,bias,len(mrg)),fontsize=11,fontweight="bold")
fig.savefig(os.path.join(FIG,"f9_validation.png"),bbox_inches="tight"); plt.close(fig)

print("WROTE f7_spatial_peaks.png f8_zones.png f9_validation.png")
# zone fraction
feat=np.stack([wmean.ravel(),wstd.ravel()*3],axis=1); good=~np.isnan(feat).any(1); X=feat[good]
rng=np.random.default_rng(0); C=X[rng.choice(len(X),2,replace=False)]
for _ in range(60):
    lab=np.linalg.norm(X[:,None]-C[None],axis=2).argmin(1)
    nC=np.array([X[lab==k].mean(0) if (lab==k).any() else C[k] for k in range(2)])
    if np.allclose(nC,C): break
    C=nC
hi=int((lab==(0 if C[0,1]>C[1,1] else 1)).sum())
print("winter zones: variable(berseem-like)=%d steady(wheat-like)=%d of %d valid px (~%.0f%% / %.0f%%)"%(hi,good.sum()-hi,good.sum(),100*hi/good.sum(),100*(good.sum()-hi)/good.sum()))

# ---- F10: berseem cutting / fodder-harvest log ----
import matplotlib.dates as mdates
gridnp=np.arange(dates.min(),dates.max()+1,dtype="datetime64[D]"); M=len(gridnp); GI={d:i for i,d in enumerate(gridnp)}
def whit1(y,w,lam=60,d=2):
    n=len(y); D=np.diff(np.eye(n),d,axis=0); return np.linalg.solve(np.diag(w)+lam*(D.T@D),w*y)
def daily(s):
    y=np.zeros(M); w=np.zeros(M)
    for k,dd in enumerate(dates):
        if not np.isnan(s[k]): y[GI[dd]]=s[k]; w[GI[dd]]=1.0
    return whit1(y,w)
def dips(z,d0,d1,prom=0.06,dist=18):
    sel=(gridnp>=np.datetime64(d0))&(gridnp<=np.datetime64(d1)); idx=np.where(sel)[0]; seg=z[idx]; tr=[]
    for i in range(1,len(seg)-1):
        if seg[i]<seg[i-1] and seg[i]<=seg[i+1]:
            p=min(seg[max(0,i-dist):i+1].max(),seg[i:i+dist+1].max())-seg[i]
            if p>=prom: tr.append((idx[i],p))
    tr.sort(key=lambda x:-x[1]); keep=[]; taken=np.zeros(M,bool)
    for ti,p in tr:
        if not taken[max(0,ti-dist):ti+dist+1].any(): keep.append(ti); taken[ti]=True
    return sorted(keep)
bmask=wstd>np.nanpercentile(wstd,55)
zser=lambda mask: np.nanmean(ndvi.reshape(NT,-1)[:,mask.ravel()],axis=1)
z2425=daily(zser(bmask)); z2526=daily(zser(np.ones((NY,NX),bool)))
c2425=dips(z2425,"2024-11-01","2025-05-10"); c2526=dips(z2526,"2025-10-20","2026-05-25")
pc=[]
for px in range(NX*NY):
    s=ndvi.reshape(NT,-1)[:,px]
    if not np.isnan(s).all(): pc.append(len(dips(daily(s),"2025-10-20","2026-05-25",prom=0.07,dist=20)))
med=int(np.median(pc))
fig,axes=plt.subplots(2,1,figsize=(14,6.2))
panels=[(z2425,c2425,"2024-10-01","2025-05-31",bmask,"Winter 2024/25 - berseem zone (half the field)"),
        (z2526,c2526,"2025-10-01","2026-06-10",np.ones((NY,NX),bool),"Winter 2025/26 - berseem (whole field)")]
for ax,(z,cuts,d0,d1,mask,title) in zip(axes,panels):
    sel=(gridnp>=np.datetime64(d0))&(gridnp<=np.datetime64(d1))
    om=(dates>=np.datetime64(d0))&(dates<=np.datetime64(d1))
    ax.scatter(dates[om],zser(mask)[om],s=14,c="#9bbf9b",zorder=2,label="zone-mean NDVI (obs)")
    ax.plot(gridnp[sel],z[sel],color="#1b7837",lw=2.2,zorder=3,label="smoothed")
    for ci in cuts:
        ax.annotate("cut",(gridnp[ci],z[ci]),textcoords="offset points",xytext=(0,-18),ha="center",fontsize=8,color="#c0392b",
            arrowprops=dict(arrowstyle="->",color="#c0392b",lw=1.3))
    ax.set_ylim(0,1); ax.set_ylabel("NDVI"); ax.set_title(title,fontsize=10.5,fontweight="bold")
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y")); ax.legend(fontsize=8,loc="lower left")
axes[1].text(0.99,0.06,"per-pixel median ≈ %d cuts (range %d-%d)"%(med,min(pc),max(pc)),transform=axes[1].transAxes,ha="right",fontsize=9,color="#c0392b",fontweight="bold")
fig.suptitle("Berseem fodder-harvest log - each dip = a cut for animal feed. Satellite resolves the synchronized early cuts; later staggered cuts blur in the field mean.",fontsize=10.3,fontweight="bold",y=1.005)
fig.tight_layout(); fig.savefig(os.path.join(FIG,"f10_cuts.png"),bbox_inches="tight"); plt.close(fig)
print("CUTS field-mean 24/25 zone:",len(c2425),"| 25/26 field:",len(c2526),"| 25/26 per-pixel median:",med,"range",min(pc),"-",max(pc))
