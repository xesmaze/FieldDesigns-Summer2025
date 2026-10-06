#!/usr/bin/env python3
"""
Estimate soybean plot canopy/stand density from a registered orthophoto grid.

IMPORTANT
---------
At ~3.6 cm/pixel and with overlapping soybean canopies, individual plants are
not reliably separable in this orthophoto. Therefore the default workflow does
NOT claim that connected components or watershed regions are individual plants.

Default outputs are defensible image-derived density traits:
    - canopy cover fraction
    - green canopy area (m2)
    - green canopy area per plot area
    - gap fraction
    - ExG intensity/texture
    - relative canopy-density index

Absolute plants/m2 can be estimated ONLY if a calibration CSV containing
ground-truth plant density/counts is supplied. The calibration model is then
trained from image features to observed density.

Inputs
------
1) Original RGB orthophoto GeoTIFF
2) soybean_plot_boundaries_pixel_georef.csv
3) Optional calibration CSV with PlotID and one of:
       Plants_m2_observed
       PlantCount_observed

Outputs
-------
plot_canopy_density.csv
plot_density_calibrated.csv        (only with calibration data)
calibration_predictions.csv        (only with calibration data)
canopy_density_qc_map.png
qc_samples/*.png
"""

from __future__ import annotations
import argparse, math, warnings
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

CORNER_COLS = {
    "UL": ("UL_x_px", "UL_y_px"),
    "UR": ("UR_x_px", "UR_y_px"),
    "LR": ("LR_x_px", "LR_y_px"),
    "LL": ("LL_x_px", "LL_y_px"),
}

FEATURE_COLUMNS = [
    "CanopyCoverFraction",
    "MeanExG",
    "MedianExG",
    "StdExG",
    "ExGP90",
    "GreenComponentDensity_m2",
    "MeanGreenComponentArea_m2",
    "GapComponentDensity_m2",
    "LargeGapFraction",
]

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--tif", required=True)
    p.add_argument("--boundaries", required=True)
    p.add_argument("--out", default="soybean_density_output_v2")
    p.add_argument("--edge-buffer", type=float, default=0.04)
    p.add_argument("--min-green-component-px", type=int, default=6)
    p.add_argument("--min-gap-component-px", type=int, default=8)
    p.add_argument("--calibration-csv", default=None,
                   help="Optional CSV with PlotID plus Plants_m2_observed or PlantCount_observed")
    p.add_argument("--save-qc-samples", type=int, default=24)
    return p.parse_args()

def polygon_from_row(row):
    return np.array([
        [row["UL_x_px"], row["UL_y_px"]],
        [row["UR_x_px"], row["UR_y_px"]],
        [row["LR_x_px"], row["LR_y_px"]],
        [row["LL_x_px"], row["LL_y_px"]],
    ], dtype=np.float32)

def shrink_polygon(poly, frac):
    if frac <= 0:
        return poly.copy()
    c = poly.mean(axis=0)
    return c + (poly - c) * max(0.5, 1.0 - 2.0 * frac)

def read_plot_crop(src, poly):
    x0 = max(0, int(np.floor(poly[:,0].min())) - 2)
    x1 = min(src.width, int(np.ceil(poly[:,0].max())) + 3)
    y0 = max(0, int(np.floor(poly[:,1].min())) - 2)
    y1 = min(src.height, int(np.ceil(poly[:,1].max())) + 3)
    w, h = x1-x0, y1-y0
    arr = src.read([1,2,3], window=Window(x0,y0,w,h))
    rgb = np.moveaxis(arr,0,-1)
    if rgb.dtype != np.uint8:
        lo, hi = np.nanpercentile(rgb,[1,99])
        rgb = np.clip((rgb-lo)/max(hi-lo,1e-9)*255,0,255).astype(np.uint8)
    p = poly.copy()
    p[:,0] -= x0
    p[:,1] -= y0
    mask = np.zeros((h,w), np.uint8)
    cv2.fillPoly(mask,[np.round(p).astype(np.int32)],255)
    return rgb, mask

def exg_index(rgb):
    f = rgb.astype(np.float32)/255.0
    r,g,b = f[...,0],f[...,1],f[...,2]
    s = r+g+b+1e-6
    return 2*g/s-r/s-b/s

def vegetation_mask(rgb, plot_mask, min_component_px):
    exg = exg_index(rgb)
    vals = exg[plot_mask>0]
    vals = vals[np.isfinite(vals)]
    if vals.size < 20:
        return np.zeros_like(plot_mask), exg, np.nan

    vmin,vmax=np.percentile(vals,[2,98])
    scaled=np.clip((exg-vmin)/max(vmax-vmin,1e-6)*255,0,255).astype(np.uint8)
    vv=scaled[plot_mask>0]
    t,_=cv2.threshold(vv.reshape(-1,1),0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    thr=vmin+(float(t)/255)*(vmax-vmin)
    # avoid pathological per-plot thresholds
    thr=float(np.clip(thr,np.percentile(vals,25),np.percentile(vals,75)))

    veg=((exg>thr)&(plot_mask>0)).astype(np.uint8)*255
    kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3))
    veg=cv2.morphologyEx(veg,cv2.MORPH_OPEN,kernel,iterations=1)
    veg=cv2.morphologyEx(veg,cv2.MORPH_CLOSE,kernel,iterations=1)

    n,labs,stats,_=cv2.connectedComponentsWithStats(veg,8)
    clean=np.zeros_like(veg)
    for lab in range(1,n):
        if stats[lab,cv2.CC_STAT_AREA] >= min_component_px:
            clean[labs==lab]=255
    return clean, exg, thr

def component_stats(binary, min_px):
    n,labs,stats,_=cv2.connectedComponentsWithStats(binary.astype(np.uint8),8)
    areas=[]
    for lab in range(1,n):
        a=int(stats[lab,cv2.CC_STAT_AREA])
        if a>=min_px:
            areas.append(a)
    return np.asarray(areas,dtype=float)

def save_qc(path,rgb,mask,veg,title):
    h,w=rgb.shape[:2]
    panel=np.zeros((h,3*w,3),dtype=np.uint8)
    panel[:,:w]=rgb
    masked=rgb.copy(); masked[mask==0]=0
    panel[:,w:2*w]=masked
    vm=np.zeros_like(rgb); vm[...,1]=veg
    panel[:,2*w:]=vm
    scale=max(3, int(500/max(h,w)))
    panel=cv2.resize(panel,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST)
    strip=36
    canvas=np.full((panel.shape[0]+strip,panel.shape[1],3),255,np.uint8)
    canvas[strip:]=panel
    cv2.putText(canvas,title[:130],(8,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,0),1,cv2.LINE_AA)
    cv2.imwrite(str(path),cv2.cvtColor(canvas,cv2.COLOR_RGB2BGR))

def fit_calibration(features, calibration, output_dir):
    from sklearn.compose import TransformedTargetRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import LeaveOneOut, cross_val_predict
    from sklearn.metrics import mean_absolute_error, r2_score

    cal=calibration.copy()
    if "Plants_m2_observed" in cal.columns:
        target="Plants_m2_observed"
    elif "PlantCount_observed" in cal.columns:
        # convert using each plot's effective area after merge
        target="Plants_m2_observed"
        cal[target]=np.nan
    else:
        raise ValueError("Calibration CSV must contain Plants_m2_observed or PlantCount_observed")

    m=features.merge(cal,on="PlotID",how="inner",suffixes=("","_cal"))
    if "PlantCount_observed" in m.columns and m[target].isna().all():
        m[target]=pd.to_numeric(m["PlantCount_observed"],errors="coerce")/m["EffectiveArea_m2"]

    m=m[np.isfinite(pd.to_numeric(m[target],errors="coerce"))].copy()
    if len(m)<8:
        raise ValueError(f"Need at least 8 calibration plots; found {len(m)}")

    X=m[FEATURE_COLUMNS]
    y=pd.to_numeric(m[target],errors="coerce").to_numpy(float)

    model=Pipeline([
        ("impute",SimpleImputer(strategy="median")),
        ("scale",StandardScaler()),
        ("ridge",RidgeCV(alphas=np.logspace(-3,3,25)))
    ])

    pred_cv=cross_val_predict(model,X,y,cv=LeaveOneOut())
    m["Plants_m2_predicted_LOO"]=pred_cv
    mae=mean_absolute_error(y,pred_cv)
    r2=r2_score(y,pred_cv)

    model.fit(X,y)
    pred=np.maximum(0,model.predict(features[FEATURE_COLUMNS]))
    out=features.copy()
    out["Plants_m2_est"]=pred
    out["PlantCount_est"]=pred*out["EffectiveArea_m2"]
    out["Calibration_n"]=len(m)
    out["Calibration_LOO_MAE_plants_m2"]=mae
    out["Calibration_LOO_R2"]=r2

    m.to_csv(output_dir/"calibration_predictions.csv",index=False)
    out.to_csv(output_dir/"plot_density_calibrated.csv",index=False)

    with open(output_dir/"calibration_report.txt","w") as f:
        f.write(f"Calibration plots: {len(m)}\n")
        f.write(f"Leave-one-out MAE: {mae:.4f} plants/m2\n")
        f.write(f"Leave-one-out R2: {r2:.4f}\n")
        f.write("Features:\n")
        for c in FEATURE_COLUMNS:
            f.write(f"  {c}\n")
    return out, mae, r2, len(m)

def main():
    a=parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    b=pd.read_csv(a.boundaries)

    required=["PlotID","Block","Row","Col","Label","Area_m2",
              "EW_pass_1_east_to_20_west","NS_range_1_north_to_24_south"]
    for x,y in CORNER_COLS.values():
        required += [x,y]
    miss=[c for c in required if c not in b.columns]
    if miss: raise ValueError(f"Missing columns: {miss}")

    qc_n=min(max(a.save_qc_samples,0),len(b))
    qc_idx=set(np.linspace(0,len(b)-1,qc_n,dtype=int)) if qc_n else set()
    qc_dir=out/"qc_samples"
    if qc_n: qc_dir.mkdir(exist_ok=True)

    rows=[]
    with rasterio.open(a.tif) as src:
        pixel_area_m2=abs(src.transform.a*src.transform.e-src.transform.b*src.transform.d)
        for idx,row in b.iterrows():
            poly=shrink_polygon(polygon_from_row(row),a.edge_buffer)
            rgb,mask=read_plot_crop(src,poly)
            veg,exg,thr=vegetation_mask(rgb,mask,a.min_green_component_px)

            mask_n=int((mask>0).sum())
            veg_n=int((veg>0).sum())
            area=float(row["Area_m2"])
            eff_area=area*(1-2*a.edge_buffer)**2
            cover=veg_n/mask_n if mask_n else np.nan
            canopy_area=cover*eff_area

            ev=exg[mask>0]
            green_areas_px=component_stats(veg>0,a.min_green_component_px)

            gaps=((mask>0)&(veg==0)).astype(np.uint8)
            gap_areas_px=component_stats(gaps,a.min_gap_component_px)
            large_gap_px=gap_areas_px[gap_areas_px>=25].sum() if len(gap_areas_px) else 0
            large_gap_fraction=(large_gap_px/mask_n) if mask_n else np.nan

            rec=row.to_dict()
            rec.update({
                "EffectiveArea_m2":eff_area,
                "CanopyCoverFraction":cover,
                "CanopyArea_m2":canopy_area,
                "GapFraction":1-cover if np.isfinite(cover) else np.nan,
                "MeanExG":float(np.mean(ev)) if ev.size else np.nan,
                "MedianExG":float(np.median(ev)) if ev.size else np.nan,
                "StdExG":float(np.std(ev)) if ev.size else np.nan,
                "ExGP90":float(np.percentile(ev,90)) if ev.size else np.nan,
                "ExGThreshold":float(thr) if np.isfinite(thr) else np.nan,
                "GreenComponentCount":int(len(green_areas_px)),
                "GreenComponentDensity_m2":len(green_areas_px)/eff_area,
                "MeanGreenComponentArea_m2":(
                    float(green_areas_px.mean()*pixel_area_m2) if len(green_areas_px) else 0.0
                ),
                "GapComponentCount":int(len(gap_areas_px)),
                "GapComponentDensity_m2":len(gap_areas_px)/eff_area,
                "LargeGapFraction":large_gap_fraction,
                "PlotMaskPixels":mask_n,
                "VegetationPixels":veg_n,
            })
            rows.append(rec)

            if idx in qc_idx:
                save_qc(qc_dir/f"{idx:03d}_{row['PlotID']}_{row['Label']}.png",
                        rgb,mask,veg,
                        f"{row['PlotID']} {row['Label']} canopy={cover:.3f}")

    res=pd.DataFrame(rows)
    # Relative density index centered on the field median (=1.0).
    med=res["CanopyCoverFraction"].median()
    res["RelativeCanopyDensityIndex"]=res["CanopyCoverFraction"]/med if med>0 else np.nan
    res["CanopyCoverPercent"]=100*res["CanopyCoverFraction"]

    res=res.sort_values(["EW_pass_1_east_to_20_west",
                         "NS_range_1_north_to_24_south"]).reset_index(drop=True)
    res.to_csv(out/"plot_canopy_density.csv",index=False)

    # genotype-level descriptive summary
    summary=(res.groupby("Label",dropna=False)
             .agg(n_plots=("PlotID","size"),
                  mean_canopy_cover=("CanopyCoverFraction","mean"),
                  sd_canopy_cover=("CanopyCoverFraction","std"),
                  mean_relative_density=("RelativeCanopyDensityIndex","mean"),
                  mean_large_gap_fraction=("LargeGapFraction","mean"))
             .reset_index())
    summary.to_csv(out/"canopy_density_by_genotype_summary.csv",index=False)

    # Simple QC map using plot centroids and canopy cover.
    W,H=1200,1600
    canvas=np.full((H,W,3),255,np.uint8)
    x=res["Centroid_x_px"].to_numpy(float)
    y=res["Centroid_y_px"].to_numpy(float)
    xmin,xmax=np.nanmin(x),np.nanmax(x)
    ymin,ymax=np.nanmin(y),np.nanmax(y)
    vals=res["CanopyCoverFraction"].to_numpy(float)
    lo,hi=np.nanpercentile(vals,[5,95])
    for _,r in res.iterrows():
        px=int(50+(r["Centroid_x_px"]-xmin)/max(xmax-xmin,1e-9)*(W-100))
        py=int(50+(r["Centroid_y_px"]-ymin)/max(ymax-ymin,1e-9)*(H-100))
        t=float(np.clip((r["CanopyCoverFraction"]-lo)/max(hi-lo,1e-9),0,1))
        hue=int((1-t)*120)
        col=cv2.cvtColor(np.uint8([[[hue,220,220]]]),cv2.COLOR_HSV2BGR)[0,0].tolist()
        cv2.circle(canvas,(px,py),10,col,-1)
    cv2.putText(canvas,"Canopy-density QC map (north top; east right)",
                (25,30),cv2.FONT_HERSHEY_SIMPLEX,.72,(0,0,0),2,cv2.LINE_AA)
    cv2.imwrite(str(out/"canopy_density_qc_map.png"),canvas)

    if a.calibration_csv:
        cal=pd.read_csv(a.calibration_csv)
        calibrated,mae,r2,n=fit_calibration(res,cal,out)
        print(f"Calibration: n={n}, LOO MAE={mae:.3f} plants/m2, LOO R2={r2:.3f}")

    print(f"Processed {len(res)} plots")
    print(f"Median canopy cover: {res['CanopyCoverFraction'].median():.3f}")
    print(f"Output: {out/'plot_canopy_density.csv'}")
    if not a.calibration_csv:
        print("No plant-count calibration supplied: absolute plants/m2 were intentionally NOT reported.")

if __name__=="__main__":
    main()
