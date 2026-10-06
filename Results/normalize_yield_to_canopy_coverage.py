#!/usr/bin/env python3
"""
Normalize soybean plot yield to equivalent canopy coverage, with optional
spatial/environmental adjustment, using the registered 480-plot field dataset.

Primary model (common coverage response):
    Yield = Genotype + CoverageDeviation + Block + spatial polynomial + error

Interaction diagnostic:
    Yield = Genotype * CoverageDeviation + Block + spatial polynomial + error

The script reports two plot-level adjusted yields:
1) Yield_coverage_normalized:
   observed yield standardized to the field-median canopy coverage, leaving
   block/spatial effects untouched.

2) Yield_coverage_spatial_normalized:
   observed yield standardized to the common coverage AND to a common
   environmental reference. The common reference is the center of the field,
   averaged over all blocks, while retaining each plot's genotype and residual.

No raw observations are overwritten.

Inputs
------
--canopy   plot_canopy_density.csv
--harvest  harvest_experimental_20x24.csv

Outputs
-------
plot_yield_normalized.csv
genotype_yield_normalized_summary.csv
genotype_yield_interaction_standardized_summary.csv
model_diagnostics.txt
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--canopy", required=True)
    p.add_argument("--harvest", required=True)
    p.add_argument("--out", default="soybean_yield_normalized")
    p.add_argument(
        "--response",
        choices=["Weight_kg_analysis", "Yield_kg_ha"],
        default="Yield_kg_ha",
        help="Response used for the normalization model."
    )
    return p.parse_args()


def merge_inputs(canopy, harvest):
    keys = ["EW_pass_1_east_to_20_west", "NS_range_1_north_to_24_south"]
    out = canopy.merge(
        harvest,
        on=keys,
        how="left",
        validate="one_to_one",
        suffixes=("", "_harvest")
    )
    if len(out) != 480:
        raise RuntimeError(f"Expected 480 merged experimental plots; found {len(out)}")
    return out


def prepare_analysis(df):
    d = df.copy()

    # Yield per ground area. Area_m2 comes from the registered plot polygon.
    d["Yield_kg_m2"] = d["Weight_kg_analysis"] / d["Area_m2"]
    d["Yield_kg_ha"] = d["Yield_kg_m2"] * 10000.0

    # Common canopy target: median among plots with usable yield.
    ok = d["Weight_kg_analysis"].notna() & d["CanopyCoverFraction"].notna()
    cstar = float(d.loc[ok, "CanopyCoverFraction"].median())
    d["CoverageReference"] = cstar
    d["CoverageDeviation"] = d["CanopyCoverFraction"] - cstar

    # Continuous spatial coordinates centered/scaled for numerical stability.
    for src, dst in [
        ("Centroid_Easting_m", "X_spatial"),
        ("Centroid_Northing_m", "Y_spatial"),
    ]:
        m = float(d.loc[ok, src].mean())
        s = float(d.loc[ok, src].std(ddof=0))
        if s == 0:
            s = 1.0
        d[dst] = (d[src] - m) / s

    return d, cstar


def fit_models(d, response):
    a = d[
        d[response].notna()
        & d["CoverageDeviation"].notna()
        & d["Label"].notna()
        & d["Block"].notna()
    ].copy()

    # Low-order smooth spatial surface. This is deliberately modest so that
    # canopy normalization is not swallowed by an over-flexible spatial fit.
    spatial = (
        "X_spatial + Y_spatial + "
        "I(X_spatial**2) + I(Y_spatial**2) + X_spatial:Y_spatial"
    )

    common_formula = (
        f"{response} ~ C(Label) + CoverageDeviation + C(Block) + {spatial}"
    )
    interaction_formula = (
        f"{response} ~ C(Label) * CoverageDeviation + C(Block) + {spatial}"
    )

    common = smf.ols(common_formula, data=a).fit(cov_type="HC3")
    interaction = smf.ols(interaction_formula, data=a).fit(cov_type="HC3")

    # For nested-model comparison, use ordinary OLS covariance because
    # compare_f_test assumes classical covariance.
    common_classical = smf.ols(common_formula, data=a).fit()
    interaction_classical = smf.ols(interaction_formula, data=a).fit()
    f_stat, f_p, df_diff = interaction_classical.compare_f_test(common_classical)

    return a, common, interaction, common_classical, interaction_classical, f_stat, f_p, df_diff


def predict_reference_average_blocks(model, rows, cstar):
    """
    Predict each row at reference coverage, field center, averaged across all
    observed blocks. Genotype is retained. Returns one prediction per row.
    """
    blocks = sorted(rows["Block"].dropna().unique())
    preds = []
    for block in blocks:
        z = rows.copy()
        z["CoverageDeviation"] = 0.0
        z["X_spatial"] = 0.0
        z["Y_spatial"] = 0.0
        z["Block"] = block
        preds.append(np.asarray(model.predict(z), dtype=float))
    return np.mean(np.vstack(preds), axis=0)


def add_normalized_yields(d, fit_rows, common_model, interaction_model, response):
    out = d.copy()

    # Common-slope coverage-only correction.
    beta = float(common_model.params["CoverageDeviation"])
    out[f"{response}_coverage_normalized"] = (
        out[response] - beta * out["CoverageDeviation"]
    )

    # Common-slope full environmental standardization:
    # preserve each plot residual while moving its fitted environment to
    # coverage reference + field center + average block.
    usable = out[response].notna()
    obs_rows = out.loc[usable].copy()

    pred_obs = np.asarray(common_model.predict(obs_rows), dtype=float)
    pred_ref = predict_reference_average_blocks(common_model, obs_rows, float(out["CoverageReference"].iloc[0]))
    out.loc[usable, "PredictedYield_observed_environment"] = pred_obs
    out.loc[usable, "PredictedYield_reference_environment"] = pred_ref
    out.loc[usable, f"{response}_coverage_spatial_normalized"] = (
        out.loc[usable, response].to_numpy(float) + (pred_ref - pred_obs)
    )
    out.loc[usable, "EnvironmentalAdjustment"] = pred_ref - pred_obs

    # Genotype-specific coverage response model.
    pred_obs_i = np.asarray(interaction_model.predict(obs_rows), dtype=float)
    pred_ref_i = predict_reference_average_blocks(interaction_model, obs_rows, float(out["CoverageReference"].iloc[0]))
    out.loc[usable, f"{response}_interaction_normalized"] = (
        out.loc[usable, response].to_numpy(float) + (pred_ref_i - pred_obs_i)
    )

    return out, beta


def genotype_summary(out, response):
    common_col = f"{response}_coverage_spatial_normalized"
    interaction_col = f"{response}_interaction_normalized"

    g = (
        out.groupby("Label", dropna=False)
        .agg(
            n_plots=("PlotID", "size"),
            n_yield=(response, "count"),
            mean_raw_yield=(response, "mean"),
            sd_raw_yield=(response, "std"),
            mean_canopy_cover=("CanopyCoverFraction", "mean"),
            sd_canopy_cover=("CanopyCoverFraction", "std"),
            mean_coverage_normalized=(f"{response}_coverage_normalized", "mean"),
            mean_coverage_spatial_normalized=(common_col, "mean"),
            sd_coverage_spatial_normalized=(common_col, "std"),
            mean_interaction_normalized=(interaction_col, "mean"),
            sd_interaction_normalized=(interaction_col, "std"),
        )
        .reset_index()
    )
    return g


def interaction_standardized_means(interaction_model, analysis_rows):
    """
    Model-based genotype means at the common coverage, field center, averaged
    across blocks. These are standardized means, not raw arithmetic means.
    """
    labels = sorted(analysis_rows["Label"].dropna().unique())
    blocks = sorted(analysis_rows["Block"].dropna().unique())
    rows = []
    for label in labels:
        pp = []
        for block in blocks:
            z = pd.DataFrame({
                "Label": [label],
                "CoverageDeviation": [0.0],
                "Block": [block],
                "X_spatial": [0.0],
                "Y_spatial": [0.0],
            })
            pp.append(float(interaction_model.predict(z).iloc[0]))
        rows.append({
            "Label": label,
            "StandardizedYield_at_reference_coverage": float(np.mean(pp))
        })
    return pd.DataFrame(rows)


def main():
    a = parse_args()
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    canopy = pd.read_csv(a.canopy)
    harvest = pd.read_csv(a.harvest)

    merged = merge_inputs(canopy, harvest)
    merged, cstar = prepare_analysis(merged)

    (
        analysis_rows,
        common,
        interaction,
        common_classical,
        interaction_classical,
        f_stat,
        f_p,
        df_diff,
    ) = fit_models(merged, a.response)

    normalized, beta = add_normalized_yields(
        merged, analysis_rows, common, interaction, a.response
    )

    summary = genotype_summary(normalized, a.response)
    interaction_means = interaction_standardized_means(
        interaction, analysis_rows
    )

    normalized.to_csv(outdir / "plot_yield_normalized.csv", index=False)
    summary.to_csv(outdir / "genotype_yield_normalized_summary.csv", index=False)
    interaction_means.to_csv(
        outdir / "genotype_yield_interaction_standardized_summary.csv",
        index=False
    )

    # Compact diagnostics for deciding whether genotype-specific slopes matter.
    with open(outdir / "model_diagnostics.txt", "w") as f:
        f.write("Yield normalization diagnostics\n")
        f.write("===============================\n\n")
        f.write(f"Response: {a.response}\n")
        f.write(f"Usable yield plots: {len(analysis_rows)} / {len(merged)}\n")
        f.write(f"Reference canopy coverage (field median): {cstar:.6f} ({100*cstar:.2f}%)\n")
        f.write(f"Common canopy slope: {beta:.6f} response-units per 1.0 canopy fraction\n")
        f.write(f"Common canopy slope per +10 percentage points coverage: {0.10*beta:.6f}\n\n")

        f.write("Common-slope model\n")
        f.write("------------------\n")
        f.write(f"R2: {common_classical.rsquared:.6f}\n")
        f.write(f"Adjusted R2: {common_classical.rsquared_adj:.6f}\n")
        f.write(f"AIC: {common_classical.aic:.3f}\n")
        f.write(f"BIC: {common_classical.bic:.3f}\n")
        f.write(f"Coverage coefficient HC3 p-value: {common.pvalues.get('CoverageDeviation', np.nan):.6g}\n\n")

        f.write("Genotype x coverage interaction model\n")
        f.write("-------------------------------------\n")
        f.write(f"R2: {interaction_classical.rsquared:.6f}\n")
        f.write(f"Adjusted R2: {interaction_classical.rsquared_adj:.6f}\n")
        f.write(f"AIC: {interaction_classical.aic:.3f}\n")
        f.write(f"BIC: {interaction_classical.bic:.3f}\n\n")

        f.write("Nested interaction test\n")
        f.write("-----------------------\n")
        f.write(f"F statistic: {f_stat:.6f}\n")
        f.write(f"df difference: {df_diff:.0f}\n")
        f.write(f"p-value: {f_p:.6g}\n\n")

        f.write("Interpretation note\n")
        f.write("-------------------\n")
        f.write(
            "plot_yield_normalized.csv retains all raw values. "
            f"{a.response}_coverage_normalized applies only the common canopy correction. "
            f"{a.response}_coverage_spatial_normalized additionally moves plots to the "
            "field-center/average-block reference while preserving genotype and residual. "
            f"{a.response}_interaction_normalized allows genotype-specific canopy responses.\n"
        )

    print(f"Reference canopy coverage: {cstar:.4f} ({100*cstar:.2f}%)")
    print(f"Usable yield plots: {len(analysis_rows)} / {len(merged)}")
    print(f"Common canopy slope: {beta:.4f} {a.response} per 1.0 coverage fraction")
    print(f"Slope per +10 percentage points canopy: {0.10*beta:.4f}")
    print(f"Genotype x coverage nested-model p-value: {f_p:.6g}")
    print(f"Outputs written to: {outdir}")


if __name__ == "__main__":
    main()
