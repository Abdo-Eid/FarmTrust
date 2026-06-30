#!/usr/bin/env python3
# Regenerate all pixel-level figures (F7-F12) from the CLEAN mount, dates aligned to the CSV.
import subprocess, os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
AOI="/sessions/friendly-clever-keller/mnt/work--aoi_demo_01"; FIG="/sessions/friendly-clever-keller/mnt/outputs/figs"
INV={0,1,3,7,8,9,10,11}
csv=pd.read_csv(AOI+"/indices_timeseries.csv"); csv["date"]=pd.to_datetime(csv["solar_day"])
dates=np.array(csv["date"].values,dtype="datetime64[D]"); NT=len(dates)
de=lambda p,dt,sh: np.frombuffer(subprocess.run(["unzstd","-c",p],capture_output=True).stdout,dtype=dt).reshape(sh)
s10=lambda b: np.stack([de(f"{AOI}/cube.zarr/{b}/c/{t}/0/0","<u2",(6,18)) for t in range(NT)]).astype(float)
s20=lambda b: np.stack([de(f"{AOI}/cube.zarr/20m/{b}/c/{t}/0/0","<u2",(3,10)) for t in range(NT)]).astype(float)
r=lambda x:(x-1000.)/10000.
b04=s10("B04"); b08=s10("B08"); b05=s20("B05"); b8a=s20("B8A")
scl=np.stack([de(f"{AOI}/cube.zarr/20m/SCL/c/{t}/0/0","<u1",(3,10)) for t in range(NT)])
ndvi=np.where((b04>0)&(b08>0),(r(b08)-r(b04))/(r(b08)+r(b04)+1e-9),np.nan)
m20=(~np.isin(scl,list(INV)))&(b05>0)&(b8a>0)
ndre=np.where(m20,(r(b8a)-r(b05))/(r(b8a)+r(b05)+1e-9),np.nan)
plt.rcParams.update({"figure.dpi":130,"font.size":10,"figure.facecolor":"white","axes.facecolor":"white"})
G=plt.get_cmap("RdYlGn").copy(); G.set_bad("#d9d9d9"); VAR=plt.get_cmap("magma").copy(); VAR.set_bad("#d9d9d9")
nearest=lambda d:int(np.argmin(np.abs(dates-np.datetime64(d))))
win=lambda a,b:(dates>=np.datetime64(a))&(dates<=np.datetime64(b))
def cell(ax,d,t,vmin,vmax,cmap=G,cb="NDVI"):
    im=ax.imshow(d,cmap=cmap,vmin=vmin,vmax=vmax,aspect="equal"); ax.set_title(t,fontsize=9.3,fontweight="bold")
    ax.set_xticks([]);ax.set_yticks([])
    for s in ax.spines.values(): s.set_edgecolor("#999")
    c=plt.colorbar(im,ax=ax,fraction=0.06,pad=0.03); c.ax.tick_params(labelsize=7); c.set_label(cb,fontsize=7); return im

# F7 spatial at peaks
peaks=[("2024-07-10","C1 Corn  Jul 2024"),("2025-02-01","C2 Wheat+Berseem  Feb 2025"),("2025-07-28","C3 Corn  Jul 2025"),("2026-03-17","C4 Berseem  Mar 2026")]
fig,ax=plt.subplots(1,4,figsize=(15,3.2))
for a,(d,l) in zip(ax,peaks): cell(a,ndvi[nearest(d)],l,0.2,0.9)
fig.suptitle("The field from space at each crop peak (top=North, left=West; ~180 x 60 m, 10 m)",fontsize=11,fontweight="bold",y=1.04)
fig.savefig(FIG+"/f7_spatial_peaks.png",bbox_inches="tight"); plt.close(fig)

# F8 winter zones
WS=win("2024-11-01","2025-04-15"); SS=win("2025-06-15","2025-09-11")
wmean=np.nanmean(ndvi[WS],axis=0); wstd=np.nanstd(ndvi[WS],axis=0); smean=np.nanmean(ndvi[SS],axis=0)
fig,ax=plt.subplots(1,3,figsize=(15,3.3))
cell(ax[0],wmean,"Winter 2024/25 - mean NDVI",0.6,0.9)
i2=ax[1].imshow(wstd,cmap=VAR,vmin=0.04,vmax=0.19,aspect="equal"); ax[1].set_title("Winter 2024/25 - temporal variability\n(driven by berseem cutting, not a crop line)",fontsize=9.3,fontweight="bold"); ax[1].set_xticks([]);ax[1].set_yticks([]); plt.colorbar(i2,ax=ax[1],fraction=0.06,pad=0.03).set_label("std",fontsize=7)
cell(ax[2],smean,"Summer 2025 corn - mean NDVI\n(one uniform crop)",0.45,0.7)
fig.suptitle("Inside the field: the winter variability is the berseem CUTTING pattern (a moving cut-front), not a clean wheat/berseem boundary. Summer corn is uniform.",fontsize=10.2,fontweight="bold",y=1.05)
fig.savefig(FIG+"/f8_zones.png",bbox_inches="tight"); plt.close(fig)

# daily smoother for cut log + validation
grid=np.arange(dates.min(),dates.max()+1,dtype="datetime64[D]"); M=len(grid); GI={d:i for i,d in enumerate(grid)}
def whit(y,w,lam,d=2):
    n=len(y);D=np.diff(np.eye(n),d,axis=0);return np.linalg.solve(np.diag(w)+lam*(D.T@D),w*y)
def daily(fm,lam):
    y=np.zeros(M);w=np.zeros(M)
    for k,dd in enumerate(dates):
        if not np.isnan(fm[k]): y[GI[dd]]=fm[k];w[GI[dd]]=1.0
    return whit(y,w,lam)
ndvi_fm=np.nanmean(ndvi.reshape(NT,-1),axis=1); ndre_fm=np.nanmean(ndre.reshape(NT,-1),axis=1)

# F9 validation
mrg=pd.merge(pd.DataFrame({"date":dates,"cube":ndvi_fm}),csv[["date","ndvi_mean"]].assign(date=lambda d:d["date"].values.astype("datetime64[D]")),on="date").dropna()
rr=mrg["cube"].corr(mrg["ndvi_mean"]); bias=(mrg["cube"]-mrg["ndvi_mean"]).mean()
fig,ax=plt.subplots(figsize=(14,3.4))
ax.plot(mrg["date"],mrg["ndvi_mean"],lw=2.2,color="#1b7837",label="CSV ndvi_mean (delivered)")
ax.plot(mrg["date"],mrg["cube"],lw=1.1,color="#ef6c00",ls="--",label="Recomputed from raw cube pixels")
ax.set_ylim(0,1); ax.set_ylabel("NDVI"); ax.legend(fontsize=9,loc="lower left")
ax.set_title("Validation: delivered CSV reproduced from raw bands (r=%.3f, bias=%.3f, n=%d)"%(rr,bias,len(mrg)),fontsize=11,fontweight="bold")
fig.savefig(FIG+"/f9_validation.png",bbox_inches="tight"); plt.close(fig)

# F10 cut log
def dips(z,d0,d1,prom=0.06,dist=18):
    sel=(grid>=np.datetime64(d0))&(grid<=np.datetime64(d1)); idx=np.where(sel)[0]; seg=z[idx]; tr=[]
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
z2425=daily(zser(bmask),60); z2526=daily(zser(np.ones((6,18),bool)),60)
c2425=dips(z2425,"2024-11-01","2025-05-10"); c2526=dips(z2526,"2025-10-20","2026-05-25")
pc=[len(dips(daily(ndvi.reshape(NT,-1)[:,px],60),"2025-10-20","2026-05-25",0.07,20)) for px in range(108) if not np.isnan(ndvi.reshape(NT,-1)[:,px]).all()]
med=int(np.median(pc))
fig,axes=plt.subplots(2,1,figsize=(14,6.2))
for ax,(z,cuts,d0,d1,mask,title) in zip(axes,[(z2425,c2425,"2024-10-01","2025-05-31",bmask,"Winter 2024/25 - berseem zone (half the field)"),(z2526,c2526,"2025-10-01","2026-06-10",np.ones((6,18),bool),"Winter 2025/26 - berseem (whole field)")]):
    sel=(grid>=np.datetime64(d0))&(grid<=np.datetime64(d1)); om=(dates>=np.datetime64(d0))&(dates<=np.datetime64(d1))
    ax.scatter(dates[om],zser(mask)[om],s=14,c="#9bbf9b",zorder=2,label="zone-mean NDVI (obs)")
    ax.plot(grid[sel],z[sel],color="#1b7837",lw=2.2,zorder=3,label="smoothed")
    for ci in cuts: ax.annotate("cut",(grid[ci],z[ci]),textcoords="offset points",xytext=(0,-18),ha="center",fontsize=8,color="#c0392b",arrowprops=dict(arrowstyle="->",color="#c0392b",lw=1.3))
    ax.set_ylim(0,1); ax.set_ylabel("NDVI"); ax.set_title(title,fontsize=10.5,fontweight="bold")
    ax.xaxis.set_major_locator(mdates.MonthLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y")); ax.legend(fontsize=8,loc="lower left")
axes[1].text(0.99,0.07,"per-pixel median ~ %d cuts (range %d-%d)"%(med,min(pc),max(pc)),transform=axes[1].transAxes,ha="right",fontsize=9,color="#c0392b",fontweight="bold")
fig.suptitle("Berseem fodder-harvest log - each dip = a cut for animal feed. Satellite catches synchronized early cuts; later staggered cuts blur in the field mean.",fontsize=10.2,fontweight="bold",y=1.005)
fig.tight_layout(); fig.savefig(FIG+"/f10_cuts.png",bbox_inches="tight"); plt.close(fig)

# F11 sweep
w=np.where((dates>=np.datetime64("2025-11-10"))&(dates<=np.datetime64("2025-12-25")))[0]
valid=[i for i in w if (not np.isnan(ndvi[i]).all()) and np.nanmean(ndvi[i])>0.45]
pick=[valid[int(round(x))] for x in np.linspace(0,len(valid)-1,6)]
fig,axes=plt.subplots(2,3,figsize=(13,5))
for ax,i in zip(axes.ravel(),pick): im=cell(ax,ndvi[i],"%s   field-mean %.2f"%(str(dates[i]),np.nanmean(ndvi[i])),0.2,0.9)
fig.suptitle("The berseem cutting sweep - a freshly-cut strip (red/orange) appears, moves to another part days later, then regrows (top=North, left=West)",fontsize=10.5,fontweight="bold",y=1.02)
fig.savefig(FIG+"/f11_sweep.png",bbox_inches="tight"); plt.close(fig)

# F12 NDRE
Sv=daily(ndvi_fm,3000); Sr=daily(ndre_fm,3000)
mask=~np.isnan(Sv)&~np.isnan(Sr); r2=np.corrcoef(Sv[mask],Sr[mask])[0,1]
doy=np.array([pd.Timestamp(d).dayofyear for d in grid]); yr=np.array([pd.Timestamp(d).year for d in grid])
fig,(ax,ax2)=plt.subplots(2,1,figsize=(14,7.4))
ax.plot(grid,Sv,color="#1b7837",lw=2.3,label="NDVI (greenness, 10 m)")
ax.plot(grid,Sr,color="#7e57c2",lw=2.1,label="NDRE (red-edge, 20 m)")
ax.axhline(0.89,color="#1b7837",ls=":",lw=1,alpha=.6); ax.text(grid[30],0.905,"NDVI saturates ~0.89 in dense winter crop",fontsize=8.5,color="#1b7837")
ax.set_ylim(0,1); ax.set_ylabel("index"); ax.legend(loc="lower right",fontsize=9)
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax.set_title("NDVI vs NDRE - move together (r=%.3f); NDRE's value is headroom where NDVI saturates"%r2,fontsize=11.5,fontweight="bold")
for y,c,l in [(2024,"#9e9e9e","2024"),(2025,"#1b7837","2025 (FAW)")]:
    s=(yr==y)&(doy>=150)&(doy<=270); ax2.plot(doy[s],Sv[s],color=c,lw=2.3,label="corn %s NDVI"%l); ax2.plot(doy[s],Sr[s],color=c,lw=1.5,ls="--",label="corn %s NDRE"%l)
ax2.axvspan(166,205,color="#e57373",alpha=.10); ax2.text(185,0.06,"whorl / FAW window",ha="center",fontsize=8.5,color="#c0392b")
ax2.set_xlim(150,270); ax2.set_ylim(0,1); ax2.set_ylabel("index"); ax2.set_xticks([152,182,213,244]); ax2.set_xticklabels(["1 Jun","1 Jul","1 Aug","1 Sep"])
ax2.set_title("Corn 2024 vs 2025 - 2025 sits a touch lower in both indices (consistent with the FAW year, small + confounded)",fontsize=10.6,fontweight="bold"); ax2.legend(fontsize=8,ncol=2,loc="upper right")
fig.tight_layout(); fig.savefig(FIG+"/f12_ndre.png",bbox_inches="tight"); plt.close(fig)
print("REGEN OK | F9 r=%.3f n=%d | cuts 24/25=%d 25/26=%d permed=%d | F12 r=%.3f | dates %s..%s NT=%d"%(rr,len(mrg),len(c2425),len(c2526),med,r2,dates[0],dates[-1],NT))
