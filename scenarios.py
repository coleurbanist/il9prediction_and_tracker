"""
precinct_scenario_runner.py
===========================
Wraps the win_probability_precinct.py pipeline so it can be driven by an
external baseline (e.g. a median-win or closest-win scenario from
win_scenarios.json) instead of the polling average.

The five pipeline steps (apply_crosstab_modeling, calibrate_to_baseline,
allocate_undecideds_crosstab_based, final_calibrate, run_precinct_monte_carlo)
are imported directly from win_probability_precinct so there is no code
duplication.  Only the target numbers passed into those steps change.

Usage (standalone)
------------------
    python precinct_scenario_runner.py
    → reads win_scenarios.json, runs all 14 scenario × candidate combos,
      writes IL09_scenario_map.html

Usage (imported)
----------------
    from precinct_scenario_runner import run_scenario_mode, load_scenarios
    df = run_scenario_mode('Biss', 'median_win')
"""

import json
import os
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── Import the precinct pipeline functions directly ───────────────────────────
# win_probability_precinct.py must be on the path (same directory)
sys.path.insert(0, os.path.dirname(__file__))
import win_probability_precinct as _prec

CANDIDATES = _prec.CANDIDATES
SCENARIOS_JSON  = 'win_scenarios.json'
OUTPUT_HTML     = 'IL09_scenario_map.html'
MAPBOX_STYLE    = 'carto-positron'

COLORS = {
    'Fine':        '#2ca02c',
    'Abughazaleh': '#ff7f0e',
    'Biss':        '#9467bd',
    'Amiwala':     '#17becf',
    'Simmons':     '#e377c2',
    'Andrew':      '#d62728',
    'Huynh':       '#7f7f7f',
}

SCENARIO_LABELS = {
    'median_win':  'Median Win',
    'closest_win': 'Closest Win (Squeaker)',
}


# ============================================================================
# LOAD SCENARIOS
# ============================================================================

def load_scenarios(path: str = SCENARIOS_JSON) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found — run win_probability_simulator.py first "
            "(with the winning_simulations changes applied)."
        )
    with open(path) as f:
        data = json.load(f)
    print(f"✓ Loaded win scenarios from {path} (generated {data['generated_at']})")
    return data['scenarios']


# ============================================================================
# CORE: RUN PRECINCT PIPELINE FOR ONE SCENARIO
# ============================================================================

def run_scenario_mode(
    candidate: str,
    scenario_type: str,          # 'median_win' or 'closest_win'
    scenarios: dict | None = None,
) -> pd.DataFrame:
    """
    Run the full precinct-level pipeline using a scenario's district-wide
    vote shares as the baseline instead of the polling average.

    Returns a GeoDataFrame-ready DataFrame with win_prob_{cand} and
    median_pct_{cand} columns, same schema as IL_09_precinct_probabilities.csv.

    Parameters
    ----------
    candidate     : e.g. 'Biss'
    scenario_type : 'median_win' or 'closest_win'
    scenarios     : pre-loaded scenarios dict (loads from JSON if None)
    """
    if scenarios is None:
        scenarios = load_scenarios()

    cand_data = scenarios.get(candidate)
    if cand_data is None:
        raise ValueError(f"No scenario data for {candidate} — they may have 0 winning sims.")

    scenario = cand_data.get(scenario_type)
    if scenario is None:
        raise ValueError(f"Scenario type '{scenario_type}' not found for {candidate}.")

    vote_shares = scenario['vote_shares']   # {candidate: pct} summing to ~100
    margin      = scenario['winner_margin']

    label = f"{candidate} — {SCENARIO_LABELS[scenario_type]} (+{margin:.1f}%)"
    print(f"\n{'='*70}")
    print(f"SCENARIO: {label}")
    print(f"{'='*70}")
    for c in sorted(vote_shares, key=vote_shares.get, reverse=True):
        marker = ' ◄' if c == candidate else ''
        print(f"  {c:<16}: {vote_shares[c]:.1f}%{marker}")

    # ── Load precinct data (same as _prec.load_data but we override baselines) ─
    df, _, _, avg_moe, scaled_crosstabs, crosstab_moes, senate_crosstabs = \
        _prec.load_data()

    # Override both calibration targets with the scenario's vote shares
    scenario_baseline = {c: vote_shares.get(c, 0.0) for c in CANDIDATES}

    # Senate district weights (spatial join — same as normal pipeline)
    df = _prec.build_senate_district_weights(df)

    # Step 1: demographic modeling (crosstab geography stays intact)
    df = _prec.apply_crosstab_modeling(df, scenario_baseline, scaled_crosstabs, senate_crosstabs)

    # Step 2: calibrate adjusted shares to scenario baseline
    df = _prec.calibrate_to_baseline(df, scenario_baseline)

    # Step 3: undecided allocation (geographic pattern preserved)
    df = _prec.allocate_undecideds_crosstab_based(
        df, scaled_crosstabs, scenario_baseline, senate_crosstabs
    )

    # Step 4: final calibration — target IS the scenario baseline (no separate
    #         target_median here; the scenario shares are the ground truth)
    df = _prec.final_calibrate(df, scenario_baseline)

    # Step 5: Monte Carlo
    df = _prec.run_precinct_monte_carlo(df, avg_moe)

    # Tag the DataFrame so the map builder knows which scenario it came from
    df['_scenario_candidate'] = candidate
    df['_scenario_type']      = scenario_type
    df['_scenario_label']     = label
    df['_winner_margin']      = margin

    return df


# ============================================================================
# MAP HELPERS
# ============================================================================

def assign_region(row):
    if row.get('in_chicago', 0) == 1:   return 'Chicago'
    if row.get('in_evanston', 0) == 1:  return 'Evanston'
    if row.get('in_lake', 0) == 1:      return 'Lake County'
    if row.get('in_mchenry', 0) == 1:   return 'McHenry County'
    if row.get('in_cook', 0) == 1:      return 'Suburban Cook'
    return 'Other'


def get_precinct_winner(row):
    """Return the candidate with the highest win_prob in this precinct."""
    return max(CANDIDATES, key=lambda c: row[f'win_prob_{c}'])


def build_hover(row, scenario_cand, scenario_label):
    """
    Hover card for a precinct in a scenario map.
    Shows the precinct winner prominently, then all candidates ranked by win prob.
    scenario_cand is the candidate whose scenario we're viewing (for context line).
    """
    precinct = row.get('precinct_name',
                       row.get('JoinField_csv',
                               row.get('JoinField_shape', 'Unknown')))
    region  = row.get('region', 'Unknown')
    winner  = row['_precinct_winner']
    turnout = int(row.get('estimated_turnout', 0))
    margin  = row['_winner_margin_pct']

    ranked = sorted(CANDIDATES, key=lambda c: row[f'win_prob_{c}'], reverse=True)

    lines = [
        f"<b>{precinct}</b>  <i>({region})</i><br>",
        f"<i style='font-size:11px'>{scenario_label}</i><br>",
        f"<b style='color:{COLORS[winner]}'>Projected winner: {winner} "
        f"(+{margin:.1f}% margin)</b><br>",
        "<br><span style='font-family:monospace;font-size:11px'>",
        "Candidate       WinP%  Vote%<br>",
        "─────────────────────────────<br>",
    ]
    for c in ranked:
        wp  = row[f'win_prob_{c}'] * 100
        pct = row[f'median_pct_{c}']
        b0  = "<b>" if c == winner else ""
        b1  = "</b>" if c == winner else ""
        lines.append(f"{b0}{c:<14} {wp:>5.1f}  {pct:>5.1f}{b1}<br>")
    lines += [
        "─────────────────────────────<br>",
        f"Scenario: {scenario_cand} wins district<br>",
        f"Est. turnout: {turnout:,}",
        "</span>",
    ]
    return "".join(lines)


# ============================================================================
# LOAD SHAPEFILE AND MERGE WITH A SCENARIO DATAFRAME
# ============================================================================

def merge_with_shapefile(df_scenario: pd.DataFrame) -> gpd.GeoDataFrame:
    """Merge scenario precinct DataFrame with the IL-09 shapefile."""
    shapefile_path     = _prec.SHAPEFILE_PATH if hasattr(_prec, 'SHAPEFILE_PATH') \
                         else 'data/shapefile/IL24/IL24.shp'
    congress_path      = 'data/shapefile/congressional_districts.shp'

    gdf = gpd.read_file(shapefile_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Clip to IL-09
    if os.path.exists(congress_path):
        gdf_cong = gpd.read_file(congress_path)
        if gdf_cong.crs != gdf.crs:
            gdf_cong = gdf_cong.to_crs(gdf.crs)
        for col in ['DISTRICT', 'CD', 'CONG_DIST', 'DIST_NUM', 'NAME', 'NAMELSAD']:
            if col in gdf_cong.columns:
                mask = (
                    (gdf_cong[col] == '09') | (gdf_cong[col] == '9') |
                    (gdf_cong[col] == 9)   |
                    gdf_cong[col].astype(str).str.contains('09', na=False)
                )
                if mask.sum() > 0:
                    il09 = gdf_cong[mask].geometry.unary_union
                    gdf['geometry'] = gdf.geometry.intersection(il09)
                    gdf = gdf[~gdf.geometry.is_empty].copy()
                    break

    # Fix invalid geometries
    invalid = ~gdf.geometry.is_valid
    if invalid.sum():
        gdf.loc[invalid, 'geometry'] = gdf.loc[invalid, 'geometry'].buffer(0)
    gdf = gdf[~gdf.geometry.is_empty]

    # Normalise join keys
    gdf['JoinField_norm'] = gdf['JoinField'].astype(str).str.upper()
    df_scenario = df_scenario.copy()
    df_scenario['JoinField_norm'] = df_scenario['JoinField'].astype(str).str.upper()

    gdf_merged = gdf.merge(df_scenario, on='JoinField_norm', how='inner',
                           suffixes=('_shape', '_csv'))

    # Fallback join strategies
    for right_col in ['JoinField2_norm', 'JoinFieldAlt_norm']:
        if right_col not in df_scenario.columns:
            continue
        unmatched_shape = gdf[~gdf['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]
        unmatched_csv   = df_scenario[~df_scenario['JoinField_norm'].isin(
                              gdf_merged['JoinField_norm'])]
        if len(unmatched_shape) and len(unmatched_csv):
            extra = unmatched_shape.merge(
                unmatched_csv, left_on='JoinField_norm', right_on=right_col,
                how='inner', suffixes=('_shape', '_csv'),
            )
            if len(extra):
                gdf_merged = pd.concat([gdf_merged, extra], ignore_index=True)

    gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry', crs='EPSG:4326')
    gdf_merged['region'] = gdf_merged.apply(assign_region, axis=1)
    print(f"  ✓ Merged {len(gdf_merged)} precincts with shapefile")
    return gdf_merged


# ============================================================================
# BUILD THE SCENARIO MAP
# ============================================================================

def build_scenario_map(scenarios: dict) -> go.Figure:
    """
    Builds one Plotly figure with exactly 14 traces (one per scenario).
    Each trace covers ALL precincts, colored by projected winner using a
    discrete colorscale — no subset splitting, so no missing precincts.

    UI: a single flat 14-item dropdown listing every scenario.

    Color strategy: map each precinct's winner to an integer index, use a
    stepped colorscale with one color band per candidate.  Plotly discrete
    coloring via a stepped colorscale avoids the per-subset trace approach
    that caused the missing-precinct bug.
    """
    fig = go.Figure()

    SCENARIO_TYPES = ['median_win', 'closest_win']
    DEFAULT_CAND   = 'Biss'
    DEFAULT_SCEN   = 'median_win'

    # Map candidate → integer index for the colorscale
    cand_to_idx = {c: i for i, c in enumerate(CANDIDATES)}
    n_cands     = len(CANDIDATES)

    # Build a stepped discrete colorscale:
    # candidate i occupies the band [i/n, (i+1)/n] and is painted its color.
    def make_discrete_colorscale():
        cs = []
        for i, cand in enumerate(CANDIDATES):
            lo = i / n_cands
            hi = (i + 1) / n_cands
            cs.append([lo, COLORS[cand]])
            cs.append([hi, COLORS[cand]])
        return cs

    discrete_colorscale = make_discrete_colorscale()

    # Ordered list of (scen_cand, scen_type) to build buttons in the same order
    scenario_order = []
    trace_index    = {}   # (scen_cand, scen_type) → trace index
    trace_count    = 0

    for scen_cand in CANDIDATES:
        if scenarios.get(scen_cand) is None:
            print(f"  ⚠ Skipping {scen_cand} — no winning simulations")
            continue

        for scen_type in SCENARIO_TYPES:
            label_short = (
                f"{scen_cand} — {SCENARIO_LABELS[scen_type]}"
            )
            print(f"  Building trace: {label_short} …")

            df_scenario = run_scenario_mode(scen_cand, scen_type, scenarios)
            gdf         = merge_with_shapefile(df_scenario)

            label = df_scenario['_scenario_label'].iloc[0]

            # ── Precinct winner & margin ──────────────────────────────────
            gdf['_precinct_winner'] = gdf.apply(get_precinct_winner, axis=1)
            gdf['_winner_margin_pct'] = gdf.apply(
                lambda row: (
                    row[f'win_prob_{row["_precinct_winner"]}'] * 100
                    - sorted(
                        [row[f'win_prob_{c}'] * 100 for c in CANDIDATES],
                        reverse=True
                    )[1]
                ),
                axis=1,
            )

            # ── Convert winner → numeric index for colorscale ─────────────
            gdf['_winner_idx'] = gdf['_precinct_winner'].map(cand_to_idx)
            # Scale to [0, 1] placing each winner at the CENTER of its band
            gdf['_z'] = (gdf['_winner_idx'] + 0.5) / n_cands

            # ── Hover text ────────────────────────────────────────────────
            gdf['_hover'] = gdf.apply(
                lambda row, sc=scen_cand, l=label: build_hover(row, sc, l),
                axis=1,
            )

            gdf['_id'] = range(len(gdf))
            is_default = (scen_cand == DEFAULT_CAND and scen_type == DEFAULT_SCEN)

            fig.add_trace(
                go.Choroplethmapbox(
                    name=label_short,
                    geojson=gdf.__geo_interface__,
                    locations=gdf['_id'],
                    z=gdf['_z'],
                    colorscale=discrete_colorscale,
                    zmin=0,
                    zmax=1,
                    showscale=False,
                    marker_opacity=0.75,
                    marker_line_width=0.4,
                    marker_line_color='#555',
                    text=gdf['_hover'],
                    hoverinfo='text',
                    visible=is_default,
                )
            )
            key = (scen_cand, scen_type)
            trace_index[key] = trace_count
            scenario_order.append(key)
            trace_count += 1

    n_traces = trace_count

    # ── Single flat 14-item dropdown ──────────────────────────────────────
    def visibility_for(target_key):
        return [i == trace_index[target_key] for i in range(n_traces)]

    default_key = (DEFAULT_CAND, DEFAULT_SCEN)
    default_active = scenario_order.index(default_key)

    buttons = []
    for key in scenario_order:
        scen_cand, scen_type = key
        label_btn = f"{scen_cand} — {SCENARIO_LABELS[scen_type]}"
        buttons.append(dict(
            label=label_btn,
            method='update',
            args=[
                {'visible': visibility_for(key)},
                {'title': f'IL-09 Precinct Map | {label_btn}'},
            ],
        ))

    # ── Static color-key annotation ───────────────────────────────────────
    color_key = '   '.join(
        f"<span style='color:{COLORS[c]};font-size:16px'>■</span> {c}"
        for c in CANDIDATES
    )

    fig.update_layout(
        title=dict(
            text=f'IL-09 Precinct Map | {DEFAULT_CAND} — {SCENARIO_LABELS[DEFAULT_SCEN]}',
            x=0.5,
            xanchor='center',
            font=dict(size=15),
        ),
        mapbox=dict(
            style=MAPBOX_STYLE,
            center=dict(lat=42.03, lon=-87.72),
            zoom=10.2,
        ),
        updatemenus=[
            dict(
                type='dropdown',
                direction='down',
                x=0.01, xanchor='left',
                y=0.99, yanchor='top',
                buttons=buttons,
                bgcolor='white',
                bordercolor='#ccc',
                font=dict(size=12),
                showactive=True,
                active=default_active,
            ),
        ],
        annotations=[
            dict(
                text='<b>Scenario:</b>',
                x=0.01, y=1.052,
                xref='paper', yref='paper',
                xanchor='left', yanchor='bottom',
                showarrow=False,
                font=dict(size=12),
            ),
            dict(
                text=f'<b>Precinct winner:</b>  {color_key}',
                x=0.5, y=0.01,
                xref='paper', yref='paper',
                xanchor='center', yanchor='bottom',
                showarrow=False,
                font=dict(size=12),
                bgcolor='rgba(255,255,255,0.8)',
            ),
        ],
        margin=dict(l=0, r=0, t=60, b=40),
        height=750,
        paper_bgcolor='white',
    )

    return fig


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("IL-09 WIN SCENARIO PRECINCT MAP")
    print("Median Win + Closest Win, per candidate")
    print("=" * 70)

    scenarios = load_scenarios()

    print("\nBuilding 14 scenario traces (one per scenario, all precincts)…")
    print("This will run the full precinct pipeline 14 times — may take a few minutes.")

    fig = build_scenario_map(scenarios)

    fig.write_html(OUTPUT_HTML, include_plotlyjs='cdn', full_html=True)
    print(f"\n✓ Scenario map saved → {OUTPUT_HTML}")
    print("  Single dropdown top-left — 14 scenarios, precincts colored by projected winner")


if __name__ == '__main__':
    main()